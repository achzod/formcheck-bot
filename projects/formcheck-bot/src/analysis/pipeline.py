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
from analysis.exercise_detector import (
    DetectionResult,
    Exercise,
    _get_candidate_exercises,
    detect_by_pattern,
    detect_exercise,
)
from analysis.frame_annotator import annotate_key_frames
from analysis.pose_extractor import (
    ExtractionResult,
    extract_pose,
    extraction_to_json,
    save_extraction_json,
)
from analysis.rep_segmenter import PRIMARY_ANGLE_MAP, RepSegmentation, segment_reps
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

_GEMINI_EXERCISE_ALIASES: dict[str, str] = {
    "dumbbell_bicep_curl": "dumbbell_curl",
    "dumbbell_biceps_curl": "dumbbell_curl",
    "barbell_bicep_curl": "curl",
    "barbell_biceps_curl": "curl",
    "barbell_curl": "curl",
    "bicep_curl": "curl",
    "biceps_curl": "curl",
    "ez_bar_curl": "curl",
    "cable_bicep_curl": "cable_curl",
    "cable_biceps_curl": "cable_curl",
    "dumbbell_bicep_curl_with_supination": "dumbbell_curl",
    "dumbbell_shoulder_press": "ohp",
    "overhead_press": "ohp",
    "military_press": "ohp",
    "barbell_bench_press": "bench_press",
    "flat_bench_press": "bench_press",
    "incline_dumbbell_press": "incline_bench",
    "barbell_squat": "squat",
    "back_squat": "squat",
    "conventional_deadlift": "deadlift",
    "barbell_row": "barbell_row",
    "bent_over_row": "barbell_row",
    "barre_au_torse": "barbell_row",
    "tirage_horizontal_barre": "barbell_row",
    "pull_up": "pullup",
    "chin_up": "pullup",
    "lat_pull_down": "lat_pulldown",
    "dumbbell_lateral_raise": "lateral_raise",
    "dumbbell_front_raise": "front_raise",
    "tricep_pushdown": "tricep_extension",
    "rope_pushdown": "tricep_extension",
    "face_pull": "face_pull",
    "hip_thrust": "hip_thrust",
    "barbell_hip_thrust": "hip_thrust",
    "leg_press": "leg_press",
    "leg_extension": "leg_extension",
    "leg_curl": "leg_curl",
    "calf_raise": "calf_raise",
    "standing_calf_raise": "calf_raise",
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


def _normalize_exercise_name(name: str | None) -> str:
    return (name or "").strip().lower().replace(" ", "_").replace("-", "_")


def _exercise_group(exercise_name: str) -> str:
    """Retourne la famille biomécanique principale d'un exercice."""
    attr = PRIMARY_ANGLE_MAP.get(exercise_name, "")
    if "knee" in attr or "hip" in attr:
        return "lower"
    if "elbow" in attr or "shoulder" in attr:
        return "upper"
    if "trunk" in attr:
        return "core"
    return "mixed"


_UNILATERAL_LOWER_EXERCISES: set[Exercise] = {
    Exercise.BULGARIAN_SPLIT_SQUAT,
    Exercise.LUNGE,
    Exercise.WALKING_LUNGE,
    Exercise.STEP_UP,
    Exercise.SINGLE_LEG_RDL,
}

_BILATERAL_SQUAT_EXERCISES: set[Exercise] = {
    Exercise.SQUAT,
    Exercise.FRONT_SQUAT,
    Exercise.GOBLET_SQUAT,
    Exercise.HACK_SQUAT,
    Exercise.SISSY_SQUAT,
}


def _motion_profile(angles: AngleResult) -> dict[str, float | str]:
    """Déduit la famille de mouvement dominante depuis les ROM articulaires."""
    stats = getattr(angles, "stats", {}) or {}

    def _rom(key: str) -> float:
        s = stats.get(key)
        if not s:
            return 0.0
        return float(getattr(s, "range_of_motion", 0.0) or 0.0)

    knee = max(_rom("left_knee_flexion"), _rom("right_knee_flexion"))
    hip = max(_rom("left_hip_flexion"), _rom("right_hip_flexion"))
    elbow = max(_rom("left_elbow_flexion"), _rom("right_elbow_flexion"))
    shoulder = max(
        _rom("left_shoulder_flexion"),
        _rom("right_shoulder_flexion"),
        _rom("left_shoulder_abduction"),
        _rom("right_shoulder_abduction"),
    )
    trunk = _rom("trunk_inclination")

    lower_total = knee + hip
    upper_total = elbow + shoulder
    dominant = "mixed"
    if lower_total >= max(25.0, upper_total * 1.25):
        dominant = "lower"
    elif upper_total >= max(20.0, lower_total * 1.25):
        dominant = "upper"
    elif trunk >= max(18.0, lower_total * 0.8, upper_total * 0.8):
        dominant = "core"

    return {
        "dominant": dominant,
        "knee_rom": round(knee, 1),
        "hip_rom": round(hip, 1),
        "elbow_rom": round(elbow, 1),
        "shoulder_rom": round(shoulder, 1),
        "trunk_rom": round(trunk, 1),
        "lower_total": round(lower_total, 1),
        "upper_total": round(upper_total, 1),
    }


def _compute_unilateral_profile(angles: AngleResult) -> dict[str, float | bool]:
    """Profile asymétrie G/D pour distinguer bilatéral vs unilatéral."""
    stats = getattr(angles, "stats", {}) or {}

    def _rom(key: str) -> float:
        item = stats.get(key)
        if not item:
            return 0.0
        return float(getattr(item, "range_of_motion", 0.0) or 0.0)

    left_knee = _rom("left_knee_flexion")
    right_knee = _rom("right_knee_flexion")
    left_hip = _rom("left_hip_flexion")
    right_hip = _rom("right_hip_flexion")

    knee_max = max(left_knee, right_knee)
    hip_max = max(left_hip, right_hip)
    knee_asym = abs(left_knee - right_knee) / knee_max if knee_max > 5.0 else 0.0
    hip_asym = abs(left_hip - right_hip) / hip_max if hip_max > 5.0 else 0.0

    unilateral_signal = max(
        knee_asym,
        hip_asym * 0.9,
        (knee_asym * 0.65) + (hip_asym * 0.35),
    )
    strong_unilateral = bool(
        unilateral_signal >= 0.24 and (knee_asym >= 0.22 or hip_asym >= 0.20)
    )

    return {
        "left_knee_rom": round(left_knee, 1),
        "right_knee_rom": round(right_knee, 1),
        "left_hip_rom": round(left_hip, 1),
        "right_hip_rom": round(right_hip, 1),
        "knee_asym": round(knee_asym, 3),
        "hip_asym": round(hip_asym, 3),
        "unilateral_signal": round(unilateral_signal, 3),
        "strong_unilateral_signal": strong_unilateral,
    }


def _stat_value(stats: dict[str, Any], key: str, field: str) -> float:
    item = stats.get(key)
    if not item:
        return 0.0
    return float(getattr(item, field, 0.0) or 0.0)


def _compute_press_profile(
    extraction: ExtractionResult,
    angles: AngleResult,
) -> dict[str, float | bool]:
    """Profile biomécanique pour distinguer OHP vs upright row.

    OHP attendu:
    - poignets passent souvent au-dessus des épaules (overhead)
    - lockout coude visible sur une partie du cycle

    Upright row attendu:
    - poignets restent plutôt sous/sur ligne d'épaule
    - peu/pas de lockout coude overhead
    """
    overhead_deltas: list[float] = []
    for frame in extraction.frames:
        by_name = {lm.get("name"): lm for lm in frame.landmarks}
        side_deltas: list[float] = []
        for side in ("left", "right"):
            shoulder = by_name.get("{}_shoulder".format(side))
            wrist = by_name.get("{}_wrist".format(side))
            if not shoulder or not wrist:
                continue
            if (
                float(shoulder.get("visibility", 0.0)) < 0.2
                or float(wrist.get("visibility", 0.0)) < 0.2
            ):
                continue
            # y MediaPipe: plus petit = plus haut dans l'image.
            # delta > 0 => poignet au-dessus de l'épaule.
            side_deltas.append(float(shoulder["y"]) - float(wrist["y"]))
        if side_deltas:
            overhead_deltas.append(max(side_deltas))

    overhead_ratio = 0.0
    wrist_travel = 0.0
    if overhead_deltas:
        arr = sorted(overhead_deltas)
        overhead_ratio = sum(1 for d in arr if d > 0.02) / len(arr)
        low = arr[int(0.05 * (len(arr) - 1))]
        high = arr[int(0.95 * (len(arr) - 1))]
        wrist_travel = max(0.0, high - low)

    elbow_series: list[float] = []
    for frame in angles.frames:
        values = [
            float(v)
            for v in (frame.left_elbow_flexion, frame.right_elbow_flexion)
            if v is not None
        ]
        if values:
            elbow_series.append(max(values))

    elbow_lockout_ratio = 0.0
    if elbow_series:
        elbow_lockout_ratio = sum(1 for v in elbow_series if v >= 155.0) / len(elbow_series)

    stats = getattr(angles, "stats", {}) or {}
    elbow_max = max(
        _stat_value(stats, "left_elbow_flexion", "max_value"),
        _stat_value(stats, "right_elbow_flexion", "max_value"),
    )
    elbow_rom = max(
        _stat_value(stats, "left_elbow_flexion", "range_of_motion"),
        _stat_value(stats, "right_elbow_flexion", "range_of_motion"),
    )
    shoulder_abd_rom = max(
        _stat_value(stats, "left_shoulder_abduction", "range_of_motion"),
        _stat_value(stats, "right_shoulder_abduction", "range_of_motion"),
    )
    shoulder_flex_rom = max(
        _stat_value(stats, "left_shoulder_flexion", "range_of_motion"),
        _stat_value(stats, "right_shoulder_flexion", "range_of_motion"),
    )

    ohp_signal = 0.0
    if overhead_ratio >= 0.20:
        ohp_signal += 0.42
    elif overhead_ratio >= 0.12:
        ohp_signal += 0.28
    elif overhead_ratio >= 0.08:
        ohp_signal += 0.16

    if elbow_lockout_ratio >= 0.20 or elbow_max >= 155.0:
        ohp_signal += 0.30
    elif elbow_max >= 148.0:
        ohp_signal += 0.18

    if elbow_rom >= 20.0:
        ohp_signal += 0.14
    if wrist_travel >= 0.05:
        ohp_signal += 0.12
    if shoulder_flex_rom >= max(15.0, shoulder_abd_rom - 5.0):
        ohp_signal += 0.06
    ohp_signal = max(0.0, min(1.0, ohp_signal))

    upright_signal = 0.0
    if overhead_ratio <= 0.06:
        upright_signal += 0.34
    elif overhead_ratio <= 0.10:
        upright_signal += 0.20

    if elbow_max <= 145.0:
        upright_signal += 0.25
    if elbow_lockout_ratio <= 0.08:
        upright_signal += 0.12
    if shoulder_abd_rom >= 20.0:
        upright_signal += 0.16
    if wrist_travel <= 0.04:
        upright_signal += 0.12
    upright_signal = max(0.0, min(1.0, upright_signal))

    strong_ohp_signal = bool(
        ohp_signal >= 0.62 and overhead_ratio >= 0.10 and elbow_max >= 148.0
    )
    strong_upright_signal = bool(
        upright_signal >= 0.62 and overhead_ratio <= 0.08 and elbow_max <= 148.0
    )

    return {
        "overhead_ratio": round(overhead_ratio, 3),
        "wrist_travel": round(wrist_travel, 3),
        "elbow_lockout_ratio": round(elbow_lockout_ratio, 3),
        "elbow_max": round(elbow_max, 1),
        "elbow_rom": round(elbow_rom, 1),
        "shoulder_abd_rom": round(shoulder_abd_rom, 1),
        "shoulder_flex_rom": round(shoulder_flex_rom, 1),
        "ohp_signal": round(ohp_signal, 3),
        "upright_signal": round(upright_signal, 3),
        "strong_ohp_signal": strong_ohp_signal,
        "strong_upright_signal": strong_upright_signal,
    }


def _detection_candidate_score(
    candidate: DetectionResult,
    pattern_result: DetectionResult,
    motion: dict[str, float | str],
    press_profile: dict[str, float | bool] | None = None,
    unilateral_profile: dict[str, float | bool] | None = None,
) -> float:
    """Score une hypothèse d'exercice avec cohérence biomécanique."""
    score = float(candidate.confidence)
    dominant = str(motion.get("dominant", "mixed"))
    group = _exercise_group(candidate.exercise.value)

    if dominant in {"lower", "upper", "core"}:
        if group == dominant:
            score += 0.24
        elif group != "mixed":
            score -= 0.22

    if pattern_result.exercise != Exercise.UNKNOWN:
        if candidate.exercise == pattern_result.exercise:
            score += 0.05 + (0.05 * max(0.0, min(1.0, pattern_result.confidence)))
        elif pattern_result.confidence >= 0.75:
            score -= 0.05

    if press_profile:
        ohp_signal = float(press_profile.get("ohp_signal", 0.0) or 0.0)
        upright_signal = float(press_profile.get("upright_signal", 0.0) or 0.0)
        strong_ohp = bool(press_profile.get("strong_ohp_signal", False))

        if candidate.exercise in {Exercise.OHP, Exercise.DUMBBELL_OHP}:
            score += 0.32 * ohp_signal
            score -= 0.35 * upright_signal
        elif candidate.exercise == Exercise.UPRIGHT_ROW:
            score += 0.20 * upright_signal
            score -= 0.45 * ohp_signal
            if strong_ohp:
                score -= 0.25

    if unilateral_profile:
        unilateral_signal = float(unilateral_profile.get("unilateral_signal", 0.0) or 0.0)
        strong_unilateral = bool(unilateral_profile.get("strong_unilateral_signal", False))

        if candidate.exercise in _UNILATERAL_LOWER_EXERCISES:
            score += 0.42 * unilateral_signal
            if strong_unilateral:
                score += 0.12
            if unilateral_signal < 0.12:
                score -= 0.10
        elif candidate.exercise in _BILATERAL_SQUAT_EXERCISES:
            score -= 0.48 * unilateral_signal
            if strong_unilateral:
                score -= 0.18

    return score


def _needs_detection_crosscheck(
    gemini_detection: DetectionResult,
    pattern_result: DetectionResult,
    motion: dict[str, float | str],
    press_profile: dict[str, float | bool] | None = None,
    unilateral_profile: dict[str, float | bool] | None = None,
) -> bool:
    """Détermine si la détection Gemini doit être contre-vérifiée."""
    if gemini_detection.confidence < 0.72:
        return True

    dominant = str(motion.get("dominant", "mixed"))
    gemini_group = _exercise_group(gemini_detection.exercise.value)
    if dominant in {"lower", "upper", "core"} and gemini_group not in {dominant, "mixed"}:
        return True

    if (
        pattern_result.exercise != Exercise.UNKNOWN
        and pattern_result.exercise != gemini_detection.exercise
        and pattern_result.confidence >= 0.60
    ):
        pattern_group = _exercise_group(pattern_result.exercise.value)
        if pattern_group == dominant or pattern_result.confidence >= 0.75:
            return True

    if press_profile:
        if (
            gemini_detection.exercise == Exercise.UPRIGHT_ROW
            and bool(press_profile.get("strong_ohp_signal", False))
        ):
            return True
        if (
            gemini_detection.exercise in {Exercise.OHP, Exercise.DUMBBELL_OHP}
            and bool(press_profile.get("strong_upright_signal", False))
        ):
            return True

    if unilateral_profile:
        strong_unilateral = bool(unilateral_profile.get("strong_unilateral_signal", False))
        unilateral_signal = float(unilateral_profile.get("unilateral_signal", 0.0) or 0.0)
        if strong_unilateral and gemini_detection.exercise in _BILATERAL_SQUAT_EXERCISES:
            return True
        if (
            gemini_detection.exercise in _UNILATERAL_LOWER_EXERCISES
            and unilateral_signal < 0.10
            and gemini_detection.confidence < 0.90
        ):
            return True

    return False


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
        _total_frames = int(_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        _cap.release()
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
    # PRIMARY: Gemini 2.5 Flash video analysis
    # CROSS-CHECK: Pattern + GPT-4o Vision when Gemini is uncertain/incoherent
    _notify_progress(cfg, 5, "Détection de l'exercice")
    logger.info("Étape 5/%d : Détection de l'exercice...", TOTAL_STEPS)
    t0 = time.monotonic()

    gemini_rep_count = 0
    pattern_seed = detect_by_pattern(angles)
    motion = _motion_profile(angles)
    press_profile = _compute_press_profile(extraction, angles)
    unilateral_profile = _compute_unilateral_profile(angles)
    logger.info(
        "  → Pattern seed: %s (conf=%.2f) | motion=%s | press_profile=%s | unilateral=%s",
        pattern_seed.exercise.value,
        pattern_seed.confidence,
        motion,
        press_profile,
        unilateral_profile,
    )

    # Pré-extraire 3 frames pour cross-check vision (réutilisées si Gemini douteux).
    det_frames: dict[str, str] = {}
    try:
        import cv2 as _cv2_det

        _det_cap = _cv2_det.VideoCapture(str(video))
        _det_total = int(_det_cap.get(_cv2_det.CAP_PROP_FRAME_COUNT))
        for _pct, _lbl in [(0.25, "start"), (0.50, "mid"), (0.75, "end")]:
            _fidx = int(_det_total * _pct)
            _det_cap.set(_cv2_det.CAP_PROP_POS_FRAMES, _fidx)
            _ret, _frm = _det_cap.read()
            if _ret and _frm is not None:
                _det_path = out_dir / "detect_frame_{}.jpg".format(_lbl)
                _cv2_det.imwrite(str(_det_path), _frm)
                det_frames[_lbl] = str(_det_path)
        _det_cap.release()
    except Exception as _det_err:
        logger.warning("Detection frame extraction failed: %s", _det_err)

    mid_frame_path = det_frames.get("mid") or extraction.key_frame_images.get("mid")
    start_frame_path = det_frames.get("start") or extraction.key_frame_images.get("start")
    end_frame_path = det_frames.get("end") or extraction.key_frame_images.get("end")

    def _run_vision_detection(*, fail_hard: bool) -> DetectionResult | None:
        try:
            det = detect_exercise(
                angles=angles,
                mid_frame_path=mid_frame_path,
                use_vision_backup=cfg.use_vision_backup,
                start_frame_path=start_frame_path,
                end_frame_path=end_frame_path,
            )
            logger.info(
                "  → Vision/pattern detection: %s (conf=%.2f, vision_reps=%d)",
                det.exercise.value,
                det.confidence,
                int(getattr(det, "vision_rep_count", 0) or 0),
            )
            return det
        except Exception as det_err:
            if fail_hard:
                raise det_err
            logger.warning("Vision cross-check failed (non bloquant): %s", det_err)
            return None

    gemini_detection: DetectionResult | None = None

    try:
        import os as _os_det

        if not _os_det.environ.get("GEMINI_API_KEY", "").strip():
            raise ValueError("GEMINI_API_KEY not set — forcing fallback")

        logger.info("  → Using Gemini 2.5 Flash (video analysis)...")
        from analysis.gemini_detector import detect_exercise_gemini

        candidate_exercises = _get_candidate_exercises(pattern_seed, n=18)
        gemini_result = detect_exercise_gemini(
            video_path=str(video),
            candidate_exercises=candidate_exercises,
        )

        exercise_name = _normalize_exercise_name(gemini_result.get("exercise"))
        mapped_name = _GEMINI_EXERCISE_ALIASES.get(exercise_name, exercise_name)
        try:
            exercise_enum = Exercise(mapped_name)
        except ValueError as map_err:
            raise ValueError(
                "Gemini returned unsupported exercise '{}' (mapped '{}')".format(
                    exercise_name,
                    mapped_name,
                )
            ) from map_err

        if exercise_enum == Exercise.UNKNOWN:
            raise ValueError("Gemini returned UNKNOWN exercise, forcing fallback")

        gemini_detection = DetectionResult(
            exercise=exercise_enum,
            confidence=float(gemini_result.get("confidence", 0.0) or 0.0),
            reasoning="[Gemini Video] Equipment: {}. {}".format(
                gemini_result.get("equipment", "?"),
                gemini_result.get("reasoning", ""),
            ),
        )
        gemini_rep_count = int(gemini_result.get("rep_count", 0) or 0)
        logger.info(
            "  → Gemini raw: %s (conf=%.2f, reps=%d)",
            gemini_detection.exercise.value,
            gemini_detection.confidence,
            gemini_rep_count,
        )
    except Exception as gemini_err:
        logger.error("Gemini detection FAILED: %s", gemini_err, exc_info=True)
        try:
            from app.debug_log import log_error as _dbg_gem

            _dbg_gem(
                "gemini_detection_error",
                str(gemini_err),
                {"traceback": str(gemini_err)},
            )
        except Exception:
            pass

    fallback_detection: DetectionResult | None = None
    if gemini_detection is None:
        logger.warning("Falling back to GPT-4o Vision/pattern (Gemini indisponible)")
        try:
            fallback_detection = _run_vision_detection(fail_hard=True)
        except Exception as e:
            result.errors.append(f"Détection d'exercice échouée: {e}")
            result.user_messages.append(_USER_ERRORS["detection_failed"])
            logger.error("Détection échouée: %s", e)
            return result
        detection = fallback_detection
        gemini_rep_count = 0
    else:
        if _needs_detection_crosscheck(
            gemini_detection,
            pattern_seed,
            motion,
            press_profile=press_profile,
            unilateral_profile=unilateral_profile,
        ):
            logger.warning(
                "Gemini flagged for cross-check (gemini=%s conf=%.2f, pattern=%s conf=%.2f)",
                gemini_detection.exercise.value,
                gemini_detection.confidence,
                pattern_seed.exercise.value,
                pattern_seed.confidence,
            )
            fallback_detection = _run_vision_detection(fail_hard=False)

        candidates: list[tuple[str, DetectionResult]] = [("gemini", gemini_detection)]
        if fallback_detection and fallback_detection.exercise != Exercise.UNKNOWN:
            candidates.append(("vision", fallback_detection))
        if pattern_seed.exercise != Exercise.UNKNOWN and pattern_seed.confidence >= 0.45:
            pattern_vote = DetectionResult(
                exercise=pattern_seed.exercise,
                confidence=min(0.95, max(0.45, pattern_seed.confidence)),
                reasoning="[Pattern biomecanique] {}".format(pattern_seed.reasoning),
            )
            candidates.append(("pattern", pattern_vote))

        scored_candidates: list[tuple[str, DetectionResult, float]] = []
        for src_name, cand in candidates:
            cand_score = _detection_candidate_score(
                cand,
                pattern_seed,
                motion,
                press_profile=press_profile,
                unilateral_profile=unilateral_profile,
            )
            scored_candidates.append((src_name, cand, cand_score))

        source, detection, winning_score = max(scored_candidates, key=lambda item: item[2])
        logger.info(
            "  → Detection fusion winner: %s (source=%s, conf=%.2f, score=%.3f)",
            detection.exercise.value,
            source,
            detection.confidence,
            winning_score,
        )

        # Garde-fou critique:
        # si le mouvement montre clairement un overhead press, empêcher la confusion
        # vers upright_row même en cas de pattern agressif.
        if (
            detection.exercise == Exercise.UPRIGHT_ROW
            and bool(press_profile.get("strong_ohp_signal", False))
        ):
            best_ohp: tuple[str, DetectionResult] | None = None
            for src_name, cand in candidates:
                if cand.exercise in {Exercise.OHP, Exercise.DUMBBELL_OHP}:
                    if best_ohp is None or cand.confidence > best_ohp[1].confidence:
                        best_ohp = (src_name, cand)
            if best_ohp and best_ohp[1].confidence >= 0.55:
                logger.warning(
                    "Press disambiguation override: upright_row -> %s (source=%s, ohp_signal=%.3f, overhead_ratio=%.3f)",
                    best_ohp[1].exercise.value,
                    best_ohp[0],
                    float(press_profile.get("ohp_signal", 0.0) or 0.0),
                    float(press_profile.get("overhead_ratio", 0.0) or 0.0),
                )
                source, detection = best_ohp

        # Garde-fou unilatéral:
        # éviter qu'un pattern "squat" écrase une fente bulgare/lunge claire.
        if (
            detection.exercise in _BILATERAL_SQUAT_EXERCISES
            and gemini_detection is not None
            and gemini_detection.exercise in _UNILATERAL_LOWER_EXERCISES
            and gemini_detection.confidence >= 0.70
            and bool(unilateral_profile.get("strong_unilateral_signal", False))
        ):
            logger.warning(
                "Unilateral disambiguation override: %s -> %s (knee_asym=%.3f, hip_asym=%.3f, gemini_conf=%.2f)",
                detection.exercise.value,
                gemini_detection.exercise.value,
                float(unilateral_profile.get("knee_asym", 0.0) or 0.0),
                float(unilateral_profile.get("hip_asym", 0.0) or 0.0),
                gemini_detection.confidence,
            )
            source = "gemini_unilateral_override"
            detection = gemini_detection

        # Si Gemini n'est pas retenu, ne pas propager son rep_count (souvent corrélé à sa mauvaise classe).
        if not source.startswith("gemini"):
            gemini_rep_count = 0

        try:
            from app.debug_log import log_error as _dbg_det
            _dbg_det("exercise_fusion", "Detection fusion result", {
                "winner_exercise": detection.exercise.value,
                "winner_source": source,
                "winner_confidence": round(float(detection.confidence), 3),
                "pattern_exercise": pattern_seed.exercise.value,
                "pattern_confidence": round(float(pattern_seed.confidence), 3),
                "gemini_exercise": gemini_detection.exercise.value if gemini_detection else "none",
                "gemini_confidence": round(float(gemini_detection.confidence), 3) if gemini_detection else 0.0,
                "vision_exercise": fallback_detection.exercise.value if fallback_detection else "none",
                "vision_confidence": round(float(fallback_detection.confidence), 3) if fallback_detection else 0.0,
                "press_profile": press_profile,
                "unilateral_profile": unilateral_profile,
                "candidate_scores": ";".join(
                    "{}:{}:{:.3f}".format(src_name, cand.exercise.value, cand_score)
                    for src_name, cand, cand_score in scored_candidates
                ),
            })
        except Exception:
            pass

    result.detection = detection
    result.timings["detection"] = time.monotonic() - t0
    logger.info(
        "  → Exercice final: %s (confiance: %.0f%%) (%.1fs)",
        detection.display_name,
        detection.confidence * 100,
        result.timings["detection"],
    )

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

    # ── Étape 6b : Fusion rep counting (signal robuste + Gemini/Vision plausibilisés) ──
    # Important: ne jamais écraser brutalement un comptage robuste par un compteur externe
    # sous-échantillonné (ex: vidéos longues avec peu de frames LLM).
    signal_rep_count = result.reps.total_reps if result.reps else 0
    robust_rep_count = int(getattr(result.reps, "robust_count", 0) or 0) if result.reps else 0
    reference_rep_count = robust_rep_count if robust_rep_count > 0 else signal_rep_count
    duration_s = (
        float(extraction.total_frames) / float(extraction.fps)
        if extraction and extraction.fps and extraction.fps > 0
        else 0.0
    )
    vision_rep_count = 0

    def _is_plausible_external_count(candidate: int, reference: int, duration: float) -> bool:
        if candidate <= 0:
            return False
        if reference <= 0:
            return True
        # Longer videos are more likely to be under-sampled by LLM frame counting.
        lower_ratio = 0.60 if duration <= 25.0 else 0.50
        upper_ratio = 2.20 if duration <= 25.0 else 1.80
        lower = max(1, int(reference * lower_ratio))
        upper = max(reference + 3, int(reference * upper_ratio))
        return lower <= candidate <= upper

    # Run GPT-4o Vision when Gemini is absent or disagrees strongly with robust signal.
    run_vision = gemini_rep_count <= 0
    if gemini_rep_count > 0 and reference_rep_count > 0:
        if abs(gemini_rep_count - reference_rep_count) > max(2, int(reference_rep_count * 0.35)):
            run_vision = True

    if run_vision:
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
        except Exception as e:
            logger.error("Vision rep counting failed: %s", e)
            vision_rep_count = 0

    plausible_external: list[tuple[str, int]] = []
    if _is_plausible_external_count(gemini_rep_count, reference_rep_count, duration_s):
        plausible_external.append(("gemini", gemini_rep_count))
    elif gemini_rep_count > 0 and reference_rep_count > 0:
        logger.warning(
            "Ignoring Gemini rep outlier: gemini=%d, reference=%d, duration=%.1fs",
            gemini_rep_count, reference_rep_count, duration_s,
        )

    if _is_plausible_external_count(vision_rep_count, reference_rep_count, duration_s):
        plausible_external.append(("vision", vision_rep_count))
    elif vision_rep_count > 0 and reference_rep_count > 0:
        logger.warning(
            "Ignoring Vision rep outlier: vision=%d, reference=%d, duration=%.1fs",
            vision_rep_count, reference_rep_count, duration_s,
        )

    final_rep_count = reference_rep_count
    if reference_rep_count <= 0:
        if plausible_external:
            final_rep_count = max(v for _, v in plausible_external)
        else:
            detection_reps = int(getattr(detection, "vision_rep_count", 0) or 0)
            if detection_reps > 0:
                final_rep_count = detection_reps
    elif plausible_external:
        values = [reference_rep_count] + [v for _, v in plausible_external]
        values.sort()
        # Median vote reduces impact of one noisy method.
        final_rep_count = values[len(values) // 2]
        if len(plausible_external) == 1:
            ext_val = plausible_external[0][1]
            if abs(ext_val - reference_rep_count) <= max(1, int(reference_rep_count * 0.20)):
                final_rep_count = round((reference_rep_count + ext_val) / 2)

    if result.reps and final_rep_count > 0:
        if final_rep_count != result.reps.total_reps:
            logger.info(
                "Rep fusion override: signal=%d, robust=%d, gemini=%d, vision=%d -> final=%d",
                signal_rep_count,
                robust_rep_count,
                gemini_rep_count,
                vision_rep_count,
                final_rep_count,
            )
            result.reps.total_reps = final_rep_count
            result.reps.complete_reps = min(result.reps.complete_reps, final_rep_count)
            result.reps.partial_reps = max(0, final_rep_count - result.reps.complete_reps)

    # Debug log for visibility in /debug/errors endpoint.
    try:
        from app.debug_log import log_error as _dbg
        _dbg("rep_count_fusion", "Rep count fusion result", {
            "signal_rep_count": signal_rep_count,
            "robust_rep_count": robust_rep_count,
            "reference_rep_count": reference_rep_count,
            "gemini_rep_count": gemini_rep_count,
            "vision_rep_count": vision_rep_count,
            "final_rep_count": result.reps.total_reps if result.reps else 0,
            "duration_s": round(duration_s, 2),
            "run_vision": run_vision,
            "plausible_external": ",".join("{}:{}".format(k, v) for k, v in plausible_external),
        })
    except Exception:
        pass

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

    # Extract 8 evenly-spaced raw frames for GPT-4o Vision report
    _report_frames = []
    try:
        import cv2 as _cv2_rpt
        _rpt_cap = _cv2_rpt.VideoCapture(str(video))
        _rpt_total = int(_rpt_cap.get(_cv2_rpt.CAP_PROP_FRAME_COUNT))
        _n_report_frames = min(8, max(5, _rpt_total // 30))  # 5-8 frames
        for _ri in range(_n_report_frames):
            _rfidx = int(_rpt_total * (_ri + 0.5) / _n_report_frames)
            _rpt_cap.set(_cv2_rpt.CAP_PROP_POS_FRAMES, _rfidx)
            _rret, _rfrm = _rpt_cap.read()
            if _rret and _rfrm is not None:
                _rpath = out_dir / "report_frame_{}.jpg".format(_ri)
                # Resize to max 512px wide for cost efficiency
                _rh, _rw = _rfrm.shape[:2]
                if _rw > 512:
                    _scale = 512.0 / _rw
                    _rfrm = _cv2_rpt.resize(_rfrm, (512, int(_rh * _scale)))
                _cv2_rpt.imwrite(str(_rpath), _rfrm, [_cv2_rpt.IMWRITE_JPEG_QUALITY, 75])
                _report_frames.append(str(_rpath))
        _rpt_cap.release()
        logger.info("Extracted %d frames for report generation", len(_report_frames))
    except Exception as _rfe:
        logger.warning("Failed to extract report frames: %s", _rfe)

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
            video_frames=_report_frames if _report_frames else None,
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
