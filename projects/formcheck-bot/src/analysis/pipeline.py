"""Pipeline d'analyse biomécanique complet.

Orchestre les étapes :
1. Validation vidéo
2. Extraction de pose (MediaPipe)
3. Lissage des landmarks
4. Calcul des angles articulaires
5. Segmentation des répétitions
6. Détection automatique de l'exercice
7. Calcul du score de confiance
8. Génération du rapport (LLM)
9. Annotation des frames clés
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
from typing import Any

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

    # Sortie
    output_dir: str | None = None
    save_json: bool = True
    save_annotated_frames: bool = True


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
    # Fichiers générés
    annotated_frames: dict[str, str] = field(default_factory=dict)
    json_path: str | None = None
    # Timing
    timings: dict[str, float] = field(default_factory=dict)
    # Erreurs
    errors: list[str] = field(default_factory=list)
    success: bool = False


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

    video = Path(video_path)
    out_dir = Path(cfg.output_dir) if cfg.output_dir else video.parent / "formcheck_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    result = PipelineResult(video_path=str(video), output_dir=str(out_dir))

    # ── Étape 1 : Validation vidéo ──────────────────────────────────────
    if not cfg.skip_validation:
        logger.info("Étape 1/9 : Validation vidéo...")
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
                result.errors.extend(validation.blocking_errors)
                logger.error("Validation échouée: %s", validation.blocking_errors)
                return result
        except Exception as e:
            result.errors.append(f"Validation échouée: {e}")
            logger.error("Validation échouée: %s", e)
            # Continuer quand même si la validation crash

    # ── Étape 2 : Extraction de pose ─────────────────────────────────────
    logger.info("Étape 2/9 : Extraction des landmarks de pose...")
    t0 = time.monotonic()
    try:
        extraction = extract_pose(
            video_path=str(video),
            output_dir=str(out_dir),
            model_complexity=cfg.model_complexity,
            min_detection_confidence=cfg.min_detection_confidence,
            min_tracking_confidence=cfg.min_tracking_confidence,
            sample_every_n=cfg.sample_every_n,
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
        logger.error("Extraction échouée: %s", e)
        return result

    if not extraction.frames:
        result.errors.append("Aucune frame avec landmarks détectés.")
        logger.error("Aucune frame avec landmarks.")
        return result

    # ── Étape 3 : Lissage des landmarks ──────────────────────────────────
    if cfg.smoothing_enabled:
        logger.info("Étape 3/9 : Lissage temporel des landmarks...")
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
    logger.info("Étape 4/9 : Calcul des angles articulaires...")
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
        logger.error("Calcul d'angles échoué: %s", e)
        return result

    # ── Étape 5 : Détection de l'exercice ────────────────────────────────
    logger.info("Étape 5/9 : Détection de l'exercice...")
    t0 = time.monotonic()
    try:
        mid_frame_path = extraction.key_frame_images.get("mid")
        detection = detect_exercise(
            angles=angles,
            mid_frame_path=mid_frame_path,
            use_vision_backup=cfg.use_vision_backup,
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
        logger.error("Détection échouée: %s", e)
        return result

    # ── Étape 6 : Segmentation des répétitions ───────────────────────────
    logger.info("Étape 6/9 : Segmentation des répétitions...")
    t0 = time.monotonic()
    try:
        rep_seg = segment_reps(
            angles=angles,
            exercise=detection.exercise.value,
            fps=extraction.fps,
        )
        result.reps = rep_seg
        result.timings["rep_segmentation"] = time.monotonic() - t0
        logger.info(
            "  → %d reps détectées, tempo: %s (%.1fs)",
            rep_seg.total_reps, rep_seg.avg_tempo,
            result.timings["rep_segmentation"],
        )
    except Exception as e:
        result.errors.append(f"Segmentation reps échouée: {e}")
        logger.error("Segmentation reps échouée: %s", e)
        result.reps = RepSegmentation()

    # ── Étape 5b : Analyse biomécanique avancée ──────────────────────────
    logger.info("Étape 5b/9 : Analyse biomécanique avancée...")
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

    # ── Étape 5c : Analyse bras de levier et morphologie ────────────────
    logger.info("Étape 5c : Bras de levier, anthropométrie, séquençage...")
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

    # ── Étape 7 : Score de confiance ─────────────────────────────────────
    logger.info("Étape 7/9 : Calcul du score de confiance...")
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
            "  → Confiance: %d/100 (%s) (%.1fs)",
            confidence.overall_score, confidence.reliability,
            result.timings["confidence"],
        )
    except Exception as e:
        result.errors.append(f"Calcul confiance échoué: {e}")
        logger.error("Confiance échouée: %s", e)

    # ── Étape 8 : Génération du rapport ──────────────────────────────────
    logger.info("Étape 8/9 : Génération du rapport biomécanique...")
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
        logger.error("Rapport échoué: %s", e)
        # On continue même sans rapport — les annotations restent utiles

    # ── Étape 9 : Annotation des frames clés ─────────────────────────────
    if cfg.save_annotated_frames:
        logger.info("Étape 9/9 : Annotation des frames clés...")
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

    result.success = result.report is not None
    total_time = sum(result.timings.values())
    logger.info("Pipeline terminé en %.1fs (succès: %s)", total_time, result.success)

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
        "timings": {k: round(v, 2) for k, v in result.timings.items()},
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

    return data
