"""Pipeline d'analyse biomécanique complet.

Orchestre les étapes :
1. Validation vidéo (gracieuse — analyse quand même si possible)
2. Extraction de pose (MediaPipe)
3. Lissage des landmarks
4. Calcul des angles articulaires
5. Détection automatique de l'exercice
6. Segmentation des répétitions (+ fatigue + triche)
7. Analyse biomécanique avancée
8. Analyse bras de levier / morphologie
9. Calcul du score de confiance
10. Génération du rapport (LLM)
11. Annotation des frames clés
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any, Callable

from analysis.angle_calculator import AngleResult, angles_to_dict, compute_angles
from analysis.confidence import AnalysisConfidence, compute_confidence
from analysis.exercise_detector import DetectionResult, Exercise, detect_exercise
from analysis.frame_annotator import annotate_key_frames
from analysis.pose_extractor import (
    ExtractionResult,
    extract_pose,
    extraction_to_json,
    save_extraction_json,
)
from analysis.rep_segmenter import RepSegmentation, segment_reps
from analysis.report_generator import Report, generate_report, report_to_dict
from analysis.smoothing import smooth_landmarks
from analysis.video_validator import VideoValidation, validate_video

logger = logging.getLogger("formcheck.pipeline")

# Thread pool dédié au traitement CV (CPU-bound)
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="formcheck-cv")

# Messages d'erreur user-friendly (français)
_USER_ERRORS = {
    "extraction_failed": (
        "Je n'ai pas réussi à détecter ton corps dans la vidéo. "
        "Assure-toi d'être entièrement visible, des pieds à la tête, "
        "avec un bon éclairage et un arrière-plan dégagé."
    ),
    "no_frames": (
        "Aucune position n'a pu être détectée. "
        "Vérifie que tu es bien visible dans toute la vidéo. "
        "Évite le contre-jour et les vêtements trop amples."
    ),
    "angles_failed": (
        "Erreur lors de l'analyse des angles articulaires. "
        "La vidéo est peut-être de trop basse qualité. "
        "Essaie de filmer en 720p minimum avec un bon éclairage."
    ),
    "detection_failed": (
        "Je n'ai pas réussi à identifier l'exercice automatiquement. "
        "Assure-toi que le mouvement est bien visible de la tête aux pieds."
    ),
    "report_failed": (
        "L'analyse est terminée mais la génération du rapport a échoué. "
        "Réessaie dans quelques instants — si le problème persiste, "
        "contacte le support."
    ),
}

# Nombre total d'étapes pour le suivi de progression
TOTAL_STEPS = 11


@dataclass
class PipelineConfig:
    """Configuration du pipeline."""
    # Validation
    skip_validation: bool = False
    min_duration: float = 3.0
    max_duration: float = 180.0
    min_brightness: float = 40.0

    # Extraction
    model_complexity: int = 2
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    sample_every_n: int = 3  # Process every 3rd frame — 3x faster, still accurate

    # Lissage
    smoothing_enabled: bool = True
    smoothing_window: int = 7
    smoothing_polyorder: int = 2

    # Détection
    use_vision_backup: bool = True

    # Rapport
    llm_provider: str = "auto"  # "auto", "anthropic" ou "openai"
    knowledge_path: str | None = None

    # Profil morphologique (dict depuis MorphoProfile.to_dict() ou DB)
    morpho_profile: dict[str, Any] | None = None

    # Sortie
    output_dir: str | None = None
    save_json: bool = True
    save_annotated_frames: bool = True

    # Callback de progression (step_num, total_steps, description)
    progress_callback: Callable[[int, int, str], None] | None = None


@dataclass
class PipelineResult:
    """Résultat complet du pipeline."""
    video_path: str
    output_dir: str
    # Résultats intermédiaires
    validation: VideoValidation | None = None
    extraction: ExtractionResult | None = None
    angles: AngleResult | None = None
    detection: DetectionResult | None = None
    reps: RepSegmentation | None = None
    advanced: Any | None = None  # AdvancedBiomechanics
    levers: Any | None = None  # LeverBiomechanics
    confidence: AnalysisConfidence | None = None
    report: Report | None = None
    # Profil morphologique
    morpho_profile: dict[str, Any] | None = None
    adapted_thresholds: dict[str, float] | None = None
    # Fichiers générés
    annotated_frames: dict[str, str] = field(default_factory=dict)
    json_path: str | None = None
    # Timing
    timings: dict[str, float] = field(default_factory=dict)
    total_time: float = 0.0
    # Erreurs (techniques pour les logs)
    errors: list[str] = field(default_factory=list)
    # Messages user-friendly (pour WhatsApp)
    user_messages: list[str] = field(default_factory=list)
    # Indicateurs
    success: bool = False
    low_quality: bool = False  # True si analyse faite malgré qualité faible


def _notify_progress(cfg: PipelineConfig, step: int, desc: str) -> None:
    """Notifie la progression si un callback est configuré."""
    if cfg.progress_callback:
        try:
            cfg.progress_callback(step, TOTAL_STEPS, desc)
        except Exception:
            pass  # Le callback de progression ne doit jamais bloquer le pipeline


def run_pipeline(
    video_path: str,
    config: PipelineConfig | None = None,
) -> PipelineResult:
    """Exécute le pipeline complet d'analyse biomécanique (synchrone).

    Args:
        video_path: Chemin vers la vidéo à analyser.
        config: Configuration du pipeline. Si None, utilise les valeurs par défaut.

    Returns:
        PipelineResult avec tous les résultats.
    """
    cfg = config or PipelineConfig()
    pipeline_start = time.monotonic()

    video = Path(video_path)
    out_dir = Path(cfg.output_dir) if cfg.output_dir else video.parent / "formcheck_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    result = PipelineResult(video_path=str(video), output_dir=str(out_dir))

    # ── Étape 1 : Validation vidéo ──────────────────────────────────────
    if not cfg.skip_validation:
        _notify_progress(cfg, 1, "Validation vidéo")
        logger.info("Étape 1/%d : Validation vidéo...", TOTAL_STEPS)
        t0 = time.monotonic()
        try:
            validation = validate_video(
                video_path=str(video),
                min_duration=cfg.min_duration,
                max_duration=cfg.max_duration,
                min_brightness=cfg.min_brightness,
            )
            result.validation = validation
            result.timings["validation"] = time.monotonic() - t0
            logger.info(
                "  → Qualité: %d/100, valide: %s (%.1fs)",
                validation.quality_score, validation.is_valid,
                result.timings["validation"],
            )

            if not validation.is_valid:
                # Erreurs bloquantes (vidéo corrompue, noire...)
                result.errors.extend(validation.blocking_errors)
                result.user_messages.extend(validation.blocking_errors)
                if validation.suggestions:
                    result.user_messages.append(
                        "Conseils : " + " | ".join(validation.suggestions)
                    )
                logger.error("Validation bloquante: %s", validation.blocking_errors)
                return result

            # Qualifier la vidéo comme low_quality si nécessaire
            if getattr(validation, "low_quality_disclaimer", False):
                result.low_quality = True
                logger.info("  → Qualité faible — analyse avec disclaimer")

        except Exception as e:
            result.errors.append(f"Validation échouée: {e}")
            logger.error("Validation échouée: %s", e)
            # Continuer quand même si la validation crash

    # ── Étape 2 : Extraction de pose ─────────────────────────────────────
    _notify_progress(cfg, 2, "Extraction de pose")
    logger.info("Étape 2/%d : Extraction des landmarks de pose...", TOTAL_STEPS)
    t0 = time.monotonic()
    try:
        # Calcul adaptatif de sample_every_n basé sur le FPS réel
        import cv2
        _cap = cv2.VideoCapture(str(video))
        _fps = _cap.get(cv2.CAP_PROP_FPS) or 30.0
        _cap.release()
        _total_frames = int(_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        adaptive_sample_n = max(1, round(_fps / 10))
        # Limiter à max 600 frames analysées pour éviter OOM sur Render (512MB)
        max_frames_target = 600
        if _total_frames > 0 and _total_frames / adaptive_sample_n > max_frames_target:
            adaptive_sample_n = max(adaptive_sample_n, _total_frames // max_frames_target)
        logger.info(
            "  FPS vidéo: %.1f → sample_every_n adaptatif: %d (total frames: %d)",
            _fps, adaptive_sample_n, _total_frames,
        )

        extraction = extract_pose(
            video_path=str(video),
            output_dir=str(out_dir),
            model_complexity=cfg.model_complexity,
            min_detection_confidence=cfg.min_detection_confidence,
            min_tracking_confidence=cfg.min_tracking_confidence,
            sample_every_n=adaptive_sample_n,
        )
        result.extraction = extraction
        result.timings["extraction"] = time.monotonic() - t0
        logger.info(
            "  → %d frames extraites sur %d (%.1fs)",
            len(extraction.frames), extraction.total_frames,
            result.timings["extraction"],
        )
    except Exception as e:
        result.errors.append(f"Extraction échouée: {e}")
        result.user_messages.append(_USER_ERRORS["extraction_failed"])
        logger.error("Extraction échouée: %s", e)
        return result

    if not extraction.frames:
        result.errors.append("Aucune frame avec landmarks détectés.")
        result.user_messages.append(_USER_ERRORS["no_frames"])
        logger.error("Aucune frame avec landmarks.")
        return result

    # ── Étape 3 : Lissage des landmarks ──────────────────────────────────
    if cfg.smoothing_enabled:
        _notify_progress(cfg, 3, "Lissage des données")
        logger.info("Étape 3/%d : Lissage temporel des landmarks...", TOTAL_STEPS)
        t0 = time.monotonic()
        try:
            extraction.frames = smooth_landmarks(
                extraction.frames,
                window=cfg.smoothing_window,
                polyorder=cfg.smoothing_polyorder,
            )
            result.timings["smoothing"] = time.monotonic() - t0
            logger.info("  → Lissage appliqué (%.1fs)", result.timings["smoothing"])
        except Exception as e:
            result.errors.append(f"Lissage échoué: {e}")
            logger.error("Lissage échoué: %s — on continue sans.", e)

    # ── Étape 4 : Calcul des angles articulaires ─────────────────────────
    _notify_progress(cfg, 4, "Calcul des angles")
    logger.info("Étape 4/%d : Calcul des angles articulaires...", TOTAL_STEPS)
    t0 = time.monotonic()
    try:
        angles = compute_angles(extraction)
        result.angles = angles
        result.timings["angles"] = time.monotonic() - t0
        logger.info(
            "  → %d frames analysées, %d angles trackés (%.1fs)",
            len(angles.frames), len(angles.stats),
            result.timings["angles"],
        )
    except Exception as e:
        result.errors.append(f"Calcul d'angles échoué: {e}")
        result.user_messages.append(_USER_ERRORS["angles_failed"])
        logger.error("Calcul d'angles échoué: %s", e)
        return result

    # ── Étape 5 : Détection de l'exercice ────────────────────────────────
    _notify_progress(cfg, 5, "Détection de l'exercice")
    logger.info("Étape 5/%d : Détection de l'exercice...", TOTAL_STEPS)
    t0 = time.monotonic()
    try:
        mid_frame_path = extraction.key_frame_images.get("mid")
        start_frame_path = extraction.key_frame_images.get("start")
        end_frame_path = extraction.key_frame_images.get("end")
        detection = detect_exercise(
            angles=angles,
            mid_frame_path=mid_frame_path,
            use_vision_backup=cfg.use_vision_backup,
            start_frame_path=start_frame_path,
            end_frame_path=end_frame_path,
        )
        result.detection = detection
        result.timings["detection"] = time.monotonic() - t0
        logger.info(
            "  → %s (confiance: %.0f%%) (%.1fs)",
            detection.display_name, detection.confidence * 100,
            result.timings["detection"],
        )
    except Exception as e:
        result.errors.append(f"Détection d'exercice échouée: {e}")
        result.user_messages.append(_USER_ERRORS["detection_failed"])
        logger.error("Détection échouée: %s", e)
        return result

    # ── Étape 5a-bis : Recalculer key frames avec l'exercice détecté ──
    # Maintenant qu'on connaît l'exercice, on peut choisir la bonne frame
    # (peak contraction en haut pour hip thrust/curl, en bas pour squat/deadlift)
    try:
        from analysis.pose_extractor import _detect_key_frames, _save_key_frame
        new_indices = _detect_key_frames(extraction.frames, detection.exercise.value)
        if new_indices != extraction.key_frame_indices:
            extraction.key_frame_indices = new_indices
            # Re-save key frame images
            out_dir = Path(extraction.video_path).parent
            for lbl, fidx in new_indices.items():
                old_path = extraction.key_frame_images.get(lbl)
                new_path = _save_key_frame(str(extraction.video_path), fidx, lbl, out_dir)
                if new_path:
                    extraction.key_frame_images[lbl] = new_path
            logger.info("  → Key frames recalculated for %s", detection.exercise.value)
    except Exception as e:
        logger.warning("Key frame recalc failed: %s", e)

    # ── Étape 5b : Chargement profil morphologique ─────────────────────
    # Si un profil morpho est fourni dans la config, on l'utilise
    morpho_profile = cfg.morpho_profile
    if morpho_profile:
        result.morpho_profile = morpho_profile
        logger.info("  → Profil morpho charge (type: %s)", morpho_profile.get("morpho_type", "?"))

        # Calculer les seuils adaptes
        try:
            from analysis.angle_calculator import get_adapted_thresholds
            adapted = get_adapted_thresholds(
                detection.exercise.value, morpho_profile
            )
            result.adapted_thresholds = adapted
            logger.info("  → Seuils adaptes au profil morpho: %s", adapted)
        except Exception as e:
            logger.error("Calcul seuils adaptes echoue: %s", e)

    # ── Étape 6 : Segmentation des répétitions ───────────────────────────
    _notify_progress(cfg, 6, "Segmentation des reps")
    logger.info("Étape 6/%d : Segmentation des répétitions...", TOTAL_STEPS)
    t0 = time.monotonic()
    try:
        rep_seg = segment_reps(
            angles=angles,
            exercise=detection.exercise.value,
            fps=extraction.fps,
            raw_frames=extraction.frames,
        )
        result.reps = rep_seg
        result.timings["rep_segmentation"] = time.monotonic() - t0
        logger.info(
            "  → %d reps, tempo=%s, fatigue=%.0f%%, triche=%d%% (%.1fs)",
            rep_seg.total_reps, rep_seg.avg_tempo,
            rep_seg.rom_degradation, rep_seg.cheat_percentage,
            result.timings["rep_segmentation"],
        )
    except Exception as e:
        result.errors.append(f"Segmentation reps échouée: {e}")
        logger.error("Segmentation reps échouée: %s", e)
        result.reps = RepSegmentation()

    # ── Étape 6b : GPT-4o Vision rep counting (PRIMARY, most reliable) ──
    try:
        from analysis.vision_rep_counter import count_reps_by_vision
        t0_vision = time.monotonic()
        vision_rep_count = count_reps_by_vision(
            video_path=str(extraction.video_path),
            exercise_name=detection.exercise.value,
            fps=extraction.fps,
        )
        logger.info(
            "  → Vision rep count: %d (%.1fs)",
            vision_rep_count, time.monotonic() - t0_vision,
        )
        # Vision count is AUTHORITATIVE — always use it when available
        # GPT-4o sees the actual video frames and understands movement.
        # Signal processing (MediaPipe) is unreliable in both directions:
        # it can undercount (missing reps) AND overcount (noise as reps).
        if vision_rep_count > 0:
            logger.info(
                "Vision AUTHORITATIVE: signal_processing=%d → vision=%d",
                result.reps.total_reps, vision_rep_count,
            )
            result.reps.total_reps = vision_rep_count
            result.reps.complete_reps = vision_rep_count
    except Exception as e:
        logger.error("Vision rep counting failed: %s", e)
        vision_rep_count = 0

    # Log vision count for debug
    try:
        from app.debug_log import log_error as _dbg
        _dbg("vision_rep_count", "Vision rep counting result", {
            "vision_rep_count": vision_rep_count,
            "signal_processing_count": result.reps.total_reps if result.reps else 0,
        })
    except Exception:
        pass

    # Fallback: detection-time vision count (from exercise detection call)
    if vision_rep_count == 0:
        detection_reps = getattr(detection, 'vision_rep_count', 0)
        if detection_reps > 0 and detection_reps > result.reps.total_reps:
            logger.info(
                "Detection-time vision override: %d → %d",
                result.reps.total_reps, detection_reps,
            )
            result.reps.total_reps = detection_reps

    # ── Étape 7 : Analyse biomécanique avancée ───────────────────────────
    _notify_progress(cfg, 7, "Analyse biomécanique avancée")
    logger.info("Étape 7/%d : Analyse biomécanique avancée...", TOTAL_STEPS)
    t0 = time.monotonic()
    try:
        from analysis.biomechanics_advanced import compute_advanced_biomechanics
        advanced = compute_advanced_biomechanics(
            extraction=extraction,
            angles=angles,
            reps=result.reps or RepSegmentation(),
            exercise=detection.exercise.value,
        )
        result.advanced = advanced
        result.timings["advanced_biomechanics"] = time.monotonic() - t0
        logger.info("  → Analyse avancée terminée (%.1fs)", result.timings["advanced_biomechanics"])
    except Exception as e:
        result.errors.append(f"Analyse avancée échouée: {e}")
        logger.error("Analyse avancée échouée: %s", e)

    # ── Étape 8 : Analyse bras de levier et morphologie ──────────────────
    _notify_progress(cfg, 8, "Analyse morphologique")
    logger.info("Étape 8/%d : Bras de levier, anthropométrie, séquençage...", TOTAL_STEPS)
    t0 = time.monotonic()
    try:
        from analysis.biomechanics_levers import compute_lever_biomechanics
        levers = compute_lever_biomechanics(
            extraction=extraction,
            angles=angles,
            reps=result.reps or RepSegmentation(),
            exercise=detection.exercise.value,
        )
        result.levers = levers
        result.timings["lever_biomechanics"] = time.monotonic() - t0
        logger.info("  → Analyse levers terminée (%.1fs)", result.timings["lever_biomechanics"])
    except Exception as e:
        result.errors.append(f"Analyse levers échouée: {e}")
        logger.error("Analyse levers échouée: %s", e)

    # ── Étape 9 : Score de confiance ─────────────────────────────────────
    _notify_progress(cfg, 9, "Score de confiance")
    logger.info("Étape 9/%d : Calcul du score de confiance...", TOTAL_STEPS)
    t0 = time.monotonic()
    try:
        validation_for_confidence = result.validation or VideoValidation(quality_score=70)
        confidence = compute_confidence(
            extraction=extraction,
            validation=validation_for_confidence,
            reps=result.reps or RepSegmentation(),
        )
        result.confidence = confidence
        result.timings["confidence"] = time.monotonic() - t0
        logger.info(
            "  → Confiance: %d/100 (%s) — camera=%s (%.1fs)",
            confidence.overall_score, confidence.reliability,
            confidence.camera_angle,
            result.timings["confidence"],
        )
    except Exception as e:
        result.errors.append(f"Calcul confiance échoué: {e}")
        logger.error("Confiance échouée: %s", e)

    # ── Étape 10 : Génération du rapport ─────────────────────────────────
    _notify_progress(cfg, 10, "Génération du rapport")
    logger.info("Étape 10/%d : Génération du rapport biomécanique...", TOTAL_STEPS)
    t0 = time.monotonic()
    try:
        report = generate_report(
            exercise=detection,
            angles=angles,
            reps=result.reps,
            confidence=result.confidence,
            advanced=result.advanced,
            levers=result.levers,
            knowledge_path=cfg.knowledge_path,
            provider=cfg.llm_provider,
            morpho_profile=result.morpho_profile,
            adapted_thresholds=result.adapted_thresholds,
        )
        result.report = report
        result.timings["report"] = time.monotonic() - t0
        logger.info(
            "  → Score: %d/100 (modèle: %s) (%.1fs)",
            report.score, report.model_used,
            result.timings["report"],
        )
    except Exception as e:
        result.errors.append(f"Génération du rapport échouée: {e}")
        result.user_messages.append(_USER_ERRORS["report_failed"])
        logger.error("Rapport échoué: %s", e)

    # ── Étape 11 : Annotation des frames clés ────────────────────────────
    if cfg.save_annotated_frames:
        _notify_progress(cfg, 11, "Annotation des frames")
        logger.info("Étape 11/%d : Annotation des frames clés...", TOTAL_STEPS)
        t0 = time.monotonic()
        try:
            annotated = annotate_key_frames(
                extraction=extraction,
                angles=angles,
                exercise=detection.exercise.value,
                output_dir=str(out_dir),
            )
            result.annotated_frames = annotated
            result.timings["annotation"] = time.monotonic() - t0
            logger.info(
                "  → %d frames annotées (%.1fs)",
                len(annotated), result.timings["annotation"],
            )
        except Exception as e:
            result.errors.append(f"Annotation échouée: {e}")
            logger.error("Annotation échouée: %s", e)

    # ── Sauvegarde JSON ──────────────────────────────────────────────────
    if cfg.save_json:
        try:
            json_data = pipeline_result_to_dict(result)
            json_path = out_dir / "analysis_result.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            result.json_path = str(json_path)
            logger.info("  → Résultat sauvegardé: %s", json_path)
        except Exception as e:
            result.errors.append(f"Sauvegarde JSON échouée: {e}")

    # ── Finalisation ─────────────────────────────────────────────────────
    result.success = result.report is not None
    result.total_time = time.monotonic() - pipeline_start
    total_step_time = sum(result.timings.values())

    logger.info(
        "Pipeline terminé en %.1fs (steps: %.1fs, succès: %s, erreurs: %d)",
        result.total_time, total_step_time, result.success, len(result.errors),
    )

    # Ajouter les suggestions de confiance aux user_messages si pertinent
    if result.confidence and result.confidence.suggestions:
        # Uniquement si la confiance est limitée
        if result.confidence.overall_score < 60:
            result.user_messages.append(
                "Pour améliorer la précision de l'analyse : "
                + " | ".join(result.confidence.suggestions[:2])
            )

    return result


async def run_pipeline_async(
    video_path: str,
    config: PipelineConfig | None = None,
) -> PipelineResult:
    """Wrapper async du pipeline — lance le traitement CPU-bound dans un thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _executor,
        partial(run_pipeline, video_path, config),
    )


def pipeline_result_to_dict(result: PipelineResult) -> dict[str, Any]:
    """Convertit le résultat du pipeline en dict JSON-sérialisable."""
    data: dict[str, Any] = {
        "video_path": result.video_path,
        "output_dir": result.output_dir,
        "success": result.success,
        "errors": result.errors,
        "user_messages": result.user_messages,
        "low_quality": result.low_quality,
        "timings": {k: round(v, 2) for k, v in result.timings.items()},
        "total_time": round(result.total_time, 2),
    }

    if result.validation:
        data["validation"] = result.validation.to_dict()

    if result.extraction:
        data["extraction"] = {
            "fps": result.extraction.fps,
            "total_frames": result.extraction.total_frames,
            "extracted_frames": len(result.extraction.frames),
            "resolution": {
                "width": result.extraction.width,
                "height": result.extraction.height,
            },
            "key_frame_indices": result.extraction.key_frame_indices,
            "key_frame_images": result.extraction.key_frame_images,
        }

    if result.angles:
        data["angles"] = angles_to_dict(result.angles)

    if result.detection:
        data["detection"] = {
            "exercise": result.detection.exercise.value,
            "display_name": result.detection.display_name,
            "confidence": round(result.detection.confidence, 3),
            "reasoning": result.detection.reasoning,
        }
        if result.detection.vision_exercise:
            data["detection"]["vision_backup"] = {
                "exercise": result.detection.vision_exercise.value,
                "confidence": round(result.detection.vision_confidence, 3),
            }

    if result.reps:
        data["reps"] = result.reps.to_dict()

    if result.advanced:
        data["advanced"] = result.advanced.to_dict()

    if result.levers:
        data["levers"] = result.levers.to_dict()

    if result.confidence:
        data["confidence"] = result.confidence.to_dict()

    if result.report:
        data["report"] = report_to_dict(result.report)

    if result.annotated_frames:
        data["annotated_frames"] = result.annotated_frames

    if result.morpho_profile:
        data["morpho_profile"] = result.morpho_profile

    if result.adapted_thresholds:
        data["adapted_thresholds"] = result.adapted_thresholds

    return data
