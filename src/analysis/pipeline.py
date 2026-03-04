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

import numpy as np

from analysis.angle_calculator import AngleResult, angles_to_dict, compute_angles
from analysis.confidence import AnalysisConfidence, compute_confidence
from analysis.exercise_detector import (
    DetectionResult,
    Exercise,
    _get_candidate_exercises,
    detect_by_pattern,
    detect_exercise,
)
from analysis.fusion_utils import (
    apply_gemini_vision_consensus_override,
    disambiguate_upper_pull_exercise,
    estimate_intensity_from_fused_count,
    select_reference_rep_count,
)
from analysis.frame_annotator import annotate_key_frames
from analysis.minimax_motion_coach import MiniMaxAnalysis, run_minimax_motion_coach
from analysis.pose_extractor import (
    ExtractionResult,
    extract_pose,
    extraction_to_json,
    save_extraction_json,
)
from analysis.rep_segmenter import PRIMARY_ANGLE_MAP, RepSegmentation, segment_reps
from analysis.report_generator import Report, generate_report, report_to_dict
from analysis.rules_db import resolve_to_supported_exercise, suggest_supported_exercises
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


def _minimax_user_message(error_text: str) -> str:
    raw = (error_text or "").strip().lower()
    if not raw:
        return _USER_ERRORS["report_failed"]
    if "not enough credits" in raw or "1400010161" in raw:
        return (
            "MiniMax a refuse l'analyse: credits insuffisants sur le compte MiniMax. "
            "Recharge les credits puis renvoie la video."
        )
    if "configuration incomplete" in raw:
        return (
            "MiniMax n'est pas configure correctement (token/user/chat). "
            "Mets a jour les variables MINIMAX_* puis relance."
        )
    if "forbidden" in raw or "403" in raw:
        return (
            "MiniMax a refuse l'acces (403). "
            "Reconnecte le compte MiniMax ou verifie token/cookie, puis reessaie."
        )
    if "timeout" in raw:
        return (
            "MiniMax n'a pas repondu a temps. "
            "Reessaie avec une video plus courte ou un peu plus tard."
        )
    return _USER_ERRORS["report_failed"]


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
    # Provider
    use_minimax_motion_coach: bool = False
    minimax_fallback_to_local: bool = False

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


def _map_model_exercise_name(raw_name: str | None) -> str:
    """Normalize model exercise labels to supported enum values when possible."""
    name = _normalize_exercise_name(raw_name)
    if not name:
        return ""

    if name in _GEMINI_EXERCISE_ALIASES:
        return _GEMINI_EXERCISE_ALIASES[name]

    # Generic normalizations for common LLM variants.
    if "bulgarian" in name and ("split" in name or "lunge" in name or "squat" in name):
        return "bulgarian_split_squat"
    if "walking" in name and "lunge" in name:
        return "walking_lunge"
    if "reverse" in name and "lunge" in name:
        return "lunge"
    if ("romanian" in name or "stiff_leg" in name) and "deadlift" in name:
        return "rdl"

    if "straight_arm" in name and ("pulldown" in name or "pull_down" in name):
        return "cable_pullover"
    if "pullover" in name and "cable" in name:
        return "cable_pullover"
    if "lat" in name and ("pulldown" in name or "pull_down" in name):
        return "lat_pulldown"
    if "tirage_vertical" in name or "vertical_pull" in name:
        return "lat_pulldown"

    if "upright" in name and "row" in name:
        return "upright_row"
    if "tirage_menton" in name:
        return "upright_row"

    if (
        "military_press" in name
        or "overhead_press" in name
        or "shoulder_press" in name
        or ("smith" in name and "press" in name)
    ):
        return "ohp"

    if "tricep" in name and ("pushdown" in name or "push_down" in name):
        return "tricep_extension"
    if "overhead" in name and "tricep" in name:
        return "overhead_tricep"

    # Open-vocabulary fallback via scraped rules DB (500+ names => internal families).
    try:
        mapped, meta = resolve_to_supported_exercise(name)
        if mapped:
            logger.info(
                "Rules DB mapped model exercise '%s' -> '%s' (score=%.3f, pattern=%s)",
                name,
                mapped,
                float(meta.get("score", 0.0) or 0.0),
                str(meta.get("pattern", "")),
            )
            return mapped
    except Exception as exc:
        logger.debug("Rules DB mapping failed for '%s': %s", name, exc)

    # Last-resort generic remaps for unseen labels.
    if "squat" in name:
        return "squat"
    if "lunge" in name or "split_squat" in name:
        return "lunge"
    if "deadlift" in name:
        return "deadlift"
    if "press" in name and ("overhead" in name or "shoulder" in name):
        return "ohp"
    if "press" in name or "bench" in name:
        return "bench_press"
    if "pulldown" in name or "pull_down" in name:
        return "lat_pulldown"
    if "row" in name:
        return "barbell_row"
    if "curl" in name:
        return "curl"
    if "raise" in name:
        return "lateral_raise"

    return name


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

_DYNAMIC_LOWER_EXERCISES: set[Exercise] = {
    Exercise.SQUAT,
    Exercise.FRONT_SQUAT,
    Exercise.GOBLET_SQUAT,
    Exercise.HACK_SQUAT,
    Exercise.SISSY_SQUAT,
    Exercise.BULGARIAN_SPLIT_SQUAT,
    Exercise.LUNGE,
    Exercise.WALKING_LUNGE,
    Exercise.STEP_UP,
    Exercise.DEADLIFT,
    Exercise.SUMO_DEADLIFT,
    Exercise.RDL,
    Exercise.SINGLE_LEG_RDL,
    Exercise.GOOD_MORNING,
    Exercise.KETTLEBELL_SWING,
}


def _derive_key_frames_from_reps(
    reps: RepSegmentation | None,
    total_frames: int,
    exercise_name: str = "",
    extraction_frames: list[Any] | None = None,
) -> dict[str, int] | None:
    """Derive start/mid/end key frames from segmented reps."""
    if reps is None or not reps.reps:
        return None

    valid_reps = [rep for rep in reps.reps if rep.end_frame > rep.start_frame]
    if not valid_reps:
        return None

    complete_reps = [rep for rep in valid_reps if not getattr(rep, "is_partial", False)] or valid_reps
    median_rep_number = (len(complete_reps) + 1) / 2.0

    def _rep_rank(rep: Any) -> tuple[float, float]:
        rom = float(getattr(rep, "rom", 0.0) or 0.0)
        centrality = abs(float(getattr(rep, "rep_number", 0) or 0.0) - median_rep_number)
        return rom, -centrality

    reference_rep = max(complete_reps, key=_rep_rank)
    first_rep = complete_reps[0]
    last_rep = complete_reps[-1]

    max_frame = max(0, int(total_frames) - 1)

    def _clamp(frame_idx: int) -> int:
        return max(0, min(max_frame, int(frame_idx)))

    mid_frame = int(getattr(reference_rep, "bottom_frame", first_rep.start_frame))
    if extraction_frames and exercise_name:
        try:
            from analysis.exercise_phases import get_phase, get_tracking_y

            phase = get_phase(exercise_name)
            if phase:
                ref_start = int(getattr(reference_rep, "start_frame", 0) or 0)
                ref_end = int(getattr(reference_rep, "end_frame", ref_start) or ref_start)
                rep_frames = [
                    f for f in extraction_frames
                    if ref_start <= int(getattr(f, "frame_index", -1)) <= ref_end
                ]
                if rep_frames:
                    y_vals = [float(get_tracking_y(f.landmarks, phase)) for f in rep_frames]
                    if y_vals:
                        local_idx = int(np.argmin(y_vals)) if phase.peak_direction == "min_y" else int(np.argmax(y_vals))
                        mid_frame = int(getattr(rep_frames[local_idx], "frame_index", mid_frame))
        except Exception:
            pass

    return {
        "start": _clamp(int(first_rep.start_frame)),
        "mid": _clamp(mid_frame),
        "end": _clamp(int(last_rep.end_frame)),
    }


def _persist_key_frames(extraction: ExtractionResult, key_indices: dict[str, int]) -> None:
    """Persist key frame indices/images to extraction result."""
    from analysis.pose_extractor import _save_key_frame

    extraction.key_frame_indices = key_indices
    out_dir = Path(extraction.video_path).parent
    for lbl, fidx in key_indices.items():
        new_path = _save_key_frame(str(extraction.video_path), int(fidx), lbl, out_dir)
        if new_path:
            extraction.key_frame_images[lbl] = new_path


def _motion_profile(angles: AngleResult) -> dict[str, float | str]:
    """Déduit la famille de mouvement dominante depuis les ROM articulaires."""
    stats = getattr(angles, "stats", {}) or {}

    def _rom(key: str) -> float:
        s = stats.get(key)
        if not s:
            return 0.0
        return float(getattr(s, "range_of_motion", 0.0) or 0.0)

    def _mean(key: str) -> float:
        s = stats.get(key)
        if not s:
            return 0.0
        return float(getattr(s, "mean_value", 0.0) or 0.0)

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
    trunk_mean = _mean("trunk_inclination")

    lower_total = knee + hip
    upper_total = elbow + shoulder
    total_motion = max(1e-6, lower_total + upper_total)
    dominant = "mixed"
    if lower_total >= max(25.0, upper_total * 1.25):
        dominant = "lower"
    elif upper_total >= max(20.0, lower_total * 1.25):
        dominant = "upper"
    elif trunk >= max(18.0, lower_total * 0.8, upper_total * 0.8):
        dominant = "core"

    knee_static = max(0.0, min(1.0, (18.0 - knee) / 18.0))
    hip_static = max(0.0, min(1.0, (20.0 - hip) / 20.0))
    lower_static_signal = (knee_static * 0.55) + (hip_static * 0.45)
    if trunk_mean > 55.0:
        # Lying movements (bench/skull crusher) keep lower body static by design.
        lower_static_signal = max(lower_static_signal, 0.70)

    return {
        "dominant": dominant,
        "knee_rom": round(knee, 1),
        "hip_rom": round(hip, 1),
        "elbow_rom": round(elbow, 1),
        "shoulder_rom": round(shoulder, 1),
        "trunk_rom": round(trunk, 1),
        "trunk_mean": round(trunk_mean, 1),
        "lower_total": round(lower_total, 1),
        "upper_total": round(upper_total, 1),
        "upper_bias": round(upper_total / total_motion, 3),
        "lower_bias": round(lower_total / total_motion, 3),
        "lower_static_signal": round(lower_static_signal, 3),
    }


def _compute_unilateral_profile(
    angles: AngleResult,
    extraction: ExtractionResult | None = None,
) -> dict[str, float | bool]:
    """Profile asymétrie G/D pour distinguer bilatéral vs unilatéral.

    Combine:
    - asymétrie ROM genou/hanche
    - split stance persistant (distance horizontale chevilles)
    - asymétrie de hauteur des chevilles (pied arrière surélevé, typique bulgare)
    """
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

    split_stance_ratio = 0.0
    ankle_height_asym_ratio = 0.0
    ankle_height_p75 = 0.0
    ankle_width_median = 0.0
    if extraction and extraction.frames:
        ankle_dx: list[float] = []
        ankle_dy: list[float] = []
        for frame in extraction.frames:
            by_name = {lm.get("name"): lm for lm in frame.landmarks}
            left_ankle = by_name.get("left_ankle")
            right_ankle = by_name.get("right_ankle")
            if not left_ankle or not right_ankle:
                continue
            left_vis = float(left_ankle.get("visibility", 0.0))
            right_vis = float(right_ankle.get("visibility", 0.0))
            if left_vis < 0.20 or right_vis < 0.20:
                continue
            ankle_dx.append(abs(float(left_ankle.get("x", 0.0)) - float(right_ankle.get("x", 0.0))))
            ankle_dy.append(abs(float(left_ankle.get("y", 0.0)) - float(right_ankle.get("y", 0.0))))
        if ankle_dx:
            dx = np.array(ankle_dx, dtype=float)
            dy = np.array(ankle_dy, dtype=float)
            split_stance_ratio = float(np.mean(dx >= 0.15))
            ankle_height_asym_ratio = float(np.mean(dy >= 0.06))
            ankle_height_p75 = float(np.percentile(dy, 75))
            ankle_width_median = float(np.median(dx))

    ankle_height_signal = min(1.0, ankle_height_p75 / 0.10) * 0.75

    unilateral_signal = max(
        knee_asym,
        hip_asym * 0.9,
        (knee_asym * 0.65) + (hip_asym * 0.35),
        split_stance_ratio * 0.85,
        ankle_height_asym_ratio * 0.95,
        ankle_height_signal,
    )
    strong_unilateral = bool(
        unilateral_signal >= 0.18
        and (
            knee_asym >= 0.14
            or hip_asym >= 0.14
            or split_stance_ratio >= 0.28
            or ankle_height_asym_ratio >= 0.22
            or ankle_height_p75 >= 0.045
        )
    )

    return {
        "left_knee_rom": round(left_knee, 1),
        "right_knee_rom": round(right_knee, 1),
        "left_hip_rom": round(left_hip, 1),
        "right_hip_rom": round(right_hip, 1),
        "knee_asym": round(knee_asym, 3),
        "hip_asym": round(hip_asym, 3),
        "split_stance_ratio": round(split_stance_ratio, 3),
        "ankle_height_asym_ratio": round(ankle_height_asym_ratio, 3),
        "ankle_height_p75": round(ankle_height_p75, 3),
        "ankle_width_median": round(ankle_width_median, 3),
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
    if overhead_ratio >= 0.32:
        ohp_signal += 0.45
    elif overhead_ratio >= 0.24:
        ohp_signal += 0.32
    elif overhead_ratio >= 0.18:
        ohp_signal += 0.18

    if elbow_lockout_ratio >= 0.24 or elbow_max >= 162.0:
        ohp_signal += 0.24
    elif elbow_lockout_ratio >= 0.14 or elbow_max >= 154.0:
        ohp_signal += 0.14

    if elbow_rom >= 28.0:
        ohp_signal += 0.10
    if wrist_travel >= 0.07:
        ohp_signal += 0.10
    if shoulder_flex_rom >= max(18.0, shoulder_abd_rom - 3.0) and overhead_ratio >= 0.16:
        ohp_signal += 0.05
    if overhead_ratio < 0.12:
        ohp_signal -= 0.12
    ohp_signal = max(0.0, min(1.0, ohp_signal))

    upright_signal = 0.0
    if overhead_ratio <= 0.05:
        upright_signal += 0.36
    elif overhead_ratio <= 0.10:
        upright_signal += 0.24
    elif overhead_ratio <= 0.16:
        upright_signal += 0.10

    if elbow_max <= 145.0:
        upright_signal += 0.22
    if elbow_lockout_ratio <= 0.08:
        upright_signal += 0.14
    if shoulder_abd_rom >= 24.0:
        upright_signal += 0.14
    if wrist_travel <= 0.045:
        upright_signal += 0.12
    if overhead_ratio >= 0.24:
        upright_signal -= 0.12
    upright_signal = max(0.0, min(1.0, upright_signal))

    strong_ohp_signal = bool(
        ohp_signal >= 0.66
        and overhead_ratio >= 0.22
        and (elbow_lockout_ratio >= 0.14 or elbow_max >= 154.0)
        and wrist_travel >= 0.05
    )
    strong_upright_signal = bool(
        upright_signal >= 0.64
        and overhead_ratio <= 0.12
        and elbow_max <= 150.0
        and elbow_lockout_ratio <= 0.12
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


def _compute_upper_pull_profile(
    extraction: ExtractionResult,
    angles: AngleResult,
) -> dict[str, float]:
    """Profile pour distinguer lat pulldown vs cable pullover."""
    torso_lean_values: list[float] = []
    for frame in extraction.frames:
        by_name = {lm.get("name"): lm for lm in frame.landmarks}
        side_leans: list[float] = []
        for side in ("left", "right"):
            shoulder = by_name.get("{}_shoulder".format(side))
            hip = by_name.get("{}_hip".format(side))
            if not shoulder or not hip:
                continue
            if (
                float(shoulder.get("visibility", 0.0)) < 0.2
                or float(hip.get("visibility", 0.0)) < 0.2
            ):
                continue
            dx = float(shoulder["x"]) - float(hip["x"])
            dy = float(hip["y"]) - float(shoulder["y"])
            if abs(dy) < 1e-6:
                continue
            lean_deg = float(np.degrees(np.arctan2(abs(dx), abs(dy))))
            side_leans.append(lean_deg)
        if side_leans:
            torso_lean_values.append(float(np.median(side_leans)))

    torso_lean_median = float(np.median(torso_lean_values)) if torso_lean_values else 0.0

    stats = getattr(angles, "stats", {}) or {}
    elbow_min = min(
        _stat_value(stats, "left_elbow_flexion", "min_value"),
        _stat_value(stats, "right_elbow_flexion", "min_value"),
    )
    elbow_rom = max(
        _stat_value(stats, "left_elbow_flexion", "range_of_motion"),
        _stat_value(stats, "right_elbow_flexion", "range_of_motion"),
    )
    shoulder_flex_rom = max(
        _stat_value(stats, "left_shoulder_flexion", "range_of_motion"),
        _stat_value(stats, "right_shoulder_flexion", "range_of_motion"),
    )
    knee_rom = max(
        _stat_value(stats, "left_knee_flexion", "range_of_motion"),
        _stat_value(stats, "right_knee_flexion", "range_of_motion"),
    )

    pullover_signal = 0.0
    lat_signal = 0.0

    if torso_lean_median >= 32.0:
        pullover_signal += 0.40
    elif torso_lean_median >= 24.0:
        pullover_signal += 0.24
    elif torso_lean_median <= 16.0:
        lat_signal += 0.30
    elif torso_lean_median <= 22.0:
        lat_signal += 0.16

    if elbow_min >= 95.0:
        pullover_signal += 0.22
    elif elbow_min <= 80.0:
        lat_signal += 0.18

    if elbow_rom <= 70.0:
        pullover_signal += 0.18
    elif elbow_rom >= 85.0:
        lat_signal += 0.20

    if shoulder_flex_rom >= 55.0:
        pullover_signal += 0.10
        lat_signal += 0.10

    if knee_rom <= 55.0:
        pullover_signal += 0.10
    elif knee_rom >= 75.0:
        lat_signal += 0.08

    pullover_signal = max(0.0, min(1.0, pullover_signal))
    lat_signal = max(0.0, min(1.0, lat_signal))

    return {
        "torso_lean_median_deg": round(torso_lean_median, 2),
        "elbow_min": round(elbow_min, 1),
        "elbow_rom": round(elbow_rom, 1),
        "shoulder_flex_rom": round(shoulder_flex_rom, 1),
        "knee_rom": round(knee_rom, 1),
        "pullover_signal": round(pullover_signal, 3),
        "lat_pulldown_signal": round(lat_signal, 3),
    }


def _detection_candidate_score(
    candidate: DetectionResult,
    pattern_result: DetectionResult,
    motion: dict[str, float | str],
    press_profile: dict[str, float | bool] | None = None,
    upper_pull_profile: dict[str, float | bool] | None = None,
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

    lower_static_signal = float(motion.get("lower_static_signal", 0.0) or 0.0)
    if lower_static_signal >= 0.55:
        if candidate.exercise in _DYNAMIC_LOWER_EXERCISES:
            score -= 0.30 * lower_static_signal
        elif group == "upper":
            score += 0.12 * lower_static_signal
    if dominant == "upper" and candidate.exercise in _DYNAMIC_LOWER_EXERCISES:
        score -= 0.08
        if lower_static_signal >= 0.45:
            score -= 0.10 + (0.18 * lower_static_signal)

    if pattern_result.exercise != Exercise.UNKNOWN:
        if candidate.exercise == pattern_result.exercise:
            score += 0.02 + (0.03 * max(0.0, min(1.0, pattern_result.confidence)))
        elif pattern_result.confidence >= 0.75:
            score -= 0.02

    if press_profile:
        ohp_signal = float(press_profile.get("ohp_signal", 0.0) or 0.0)
        upright_signal = float(press_profile.get("upright_signal", 0.0) or 0.0)
        strong_ohp = bool(press_profile.get("strong_ohp_signal", False))
        overhead_ratio = float(press_profile.get("overhead_ratio", 0.0) or 0.0)

        if candidate.exercise in {Exercise.OHP, Exercise.DUMBBELL_OHP}:
            score += 0.20 * ohp_signal
            score -= 0.30 * upright_signal
            if overhead_ratio < 0.18:
                score -= 0.22
        elif candidate.exercise == Exercise.UPRIGHT_ROW:
            score += 0.16 * upright_signal
            score -= 0.32 * ohp_signal
            if strong_ohp:
                score -= 0.25
        elif candidate.exercise in {Exercise.LATERAL_RAISE, Exercise.FRONT_RAISE}:
            if overhead_ratio <= 0.22:
                score += 0.10
            elif overhead_ratio >= 0.30:
                score -= 0.10

    if upper_pull_profile:
        pullover_signal = float(upper_pull_profile.get("pullover_signal", 0.0) or 0.0)
        lat_signal = float(upper_pull_profile.get("lat_pulldown_signal", 0.0) or 0.0)
        pull_signal = max(pullover_signal, lat_signal)
        if candidate.exercise in {
            Exercise.LAT_PULLDOWN,
            Exercise.CLOSE_GRIP_PULLDOWN,
            Exercise.CABLE_PULLOVER,
            Exercise.PULLOVER,
        }:
            score += 0.20 * pull_signal
            if candidate.exercise in {Exercise.CABLE_PULLOVER, Exercise.PULLOVER}:
                score += 0.08 * max(0.0, pullover_signal - lat_signal)
            else:
                score += 0.08 * max(0.0, lat_signal - pullover_signal)
        elif candidate.exercise in _DYNAMIC_LOWER_EXERCISES and pull_signal >= 0.56:
            score -= 0.22 * pull_signal

    if unilateral_profile:
        unilateral_signal = float(unilateral_profile.get("unilateral_signal", 0.0) or 0.0)
        strong_unilateral = bool(unilateral_profile.get("strong_unilateral_signal", False))
        split_stance_ratio = float(unilateral_profile.get("split_stance_ratio", 0.0) or 0.0)
        ankle_height_ratio = float(unilateral_profile.get("ankle_height_asym_ratio", 0.0) or 0.0)

        if candidate.exercise in _UNILATERAL_LOWER_EXERCISES:
            score += 0.50 * unilateral_signal
            score += 0.20 * split_stance_ratio
            score += 0.22 * ankle_height_ratio
            if strong_unilateral:
                score += 0.14
            if unilateral_signal < 0.12:
                score -= 0.10
        elif candidate.exercise in _BILATERAL_SQUAT_EXERCISES:
            score -= 0.56 * unilateral_signal
            score -= 0.26 * split_stance_ratio
            score -= 0.30 * ankle_height_ratio
            if strong_unilateral:
                score -= 0.20

    return score


def _needs_detection_crosscheck(
    gemini_detection: DetectionResult,
    pattern_result: DetectionResult,
    motion: dict[str, float | str],
    press_profile: dict[str, float | bool] | None = None,
    upper_pull_profile: dict[str, float | bool] | None = None,
    unilateral_profile: dict[str, float | bool] | None = None,
) -> bool:
    """Détermine si la détection Gemini doit être contre-vérifiée."""
    if gemini_detection.confidence < 0.72:
        return True

    lower_static_signal = float(motion.get("lower_static_signal", 0.0) or 0.0)
    if (
        lower_static_signal >= 0.68
        and gemini_detection.exercise in _DYNAMIC_LOWER_EXERCISES
    ):
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

    if upper_pull_profile:
        pull_signal = max(
            float(upper_pull_profile.get("pullover_signal", 0.0) or 0.0),
            float(upper_pull_profile.get("lat_pulldown_signal", 0.0) or 0.0),
        )
        if pull_signal >= 0.62 and gemini_detection.exercise in _DYNAMIC_LOWER_EXERCISES:
            return True

    if unilateral_profile:
        strong_unilateral = bool(unilateral_profile.get("strong_unilateral_signal", False))
        unilateral_signal = float(unilateral_profile.get("unilateral_signal", 0.0) or 0.0)
        split_stance_ratio = float(unilateral_profile.get("split_stance_ratio", 0.0) or 0.0)
        ankle_height_ratio = float(unilateral_profile.get("ankle_height_asym_ratio", 0.0) or 0.0)
        if strong_unilateral and gemini_detection.exercise in _BILATERAL_SQUAT_EXERCISES:
            return True
        if (
            gemini_detection.exercise in _BILATERAL_SQUAT_EXERCISES
            and (split_stance_ratio >= 0.32 or ankle_height_ratio >= 0.24)
        ):
            return True
        if (
            gemini_detection.exercise in _UNILATERAL_LOWER_EXERCISES
            and unilateral_signal < 0.10
            and gemini_detection.confidence < 0.90
        ):
            return True

    return False


def _apply_lower_static_upper_override(
    source: str,
    detection: DetectionResult,
    winning_score: float,
    scored_candidates: list[tuple[str, DetectionResult, float]],
    motion: dict[str, float | str],
) -> tuple[str, DetectionResult, float]:
    """Prevent dynamic lower-body false positives when lower body is static.

    Typical failure mode:
    - true exercise is upper-body (lat pulldown / shoulder press)
    - noisy pattern detector votes lunge/squat
    """
    lower_static_signal = float(motion.get("lower_static_signal", 0.0) or 0.0)
    dominant = str(motion.get("dominant", "mixed"))
    if dominant != "upper" or lower_static_signal < 0.68:
        return source, detection, winning_score
    if detection.exercise not in _DYNAMIC_LOWER_EXERCISES:
        return source, detection, winning_score

    upper_candidates = [
        (src, cand, score)
        for src, cand, score in scored_candidates
        if _exercise_group(cand.exercise.value) == "upper"
    ]
    if not upper_candidates:
        return source, detection, winning_score

    best_src, best_det, best_score = max(upper_candidates, key=lambda item: item[2])
    if best_det.confidence >= 0.72 or (best_score + 0.10) >= winning_score:
        return "upper_static_override:{}".format(best_src), best_det, best_score
    return source, detection, winning_score


def _build_top_detection_candidates(
    *,
    scored_candidates: list[tuple[str, DetectionResult, float]],
    winner: DetectionResult,
    winner_source: str,
    winner_score: float,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Construit une short-list stable de candidats pour debug/report."""
    merged: dict[str, dict[str, Any]] = {}
    for source, cand, score in scored_candidates:
        key = cand.exercise.value
        payload = {
            "exercise": key,
            "display_name": cand.display_name,
            "source": source,
            "confidence": round(float(cand.confidence), 3),
            "score": round(float(score), 3),
        }
        existing = merged.get(key)
        if existing is None or float(payload["score"]) > float(existing["score"]):
            merged[key] = payload

    ranked = sorted(
        merged.values(),
        key=lambda item: (float(item.get("score", 0.0)), float(item.get("confidence", 0.0))),
        reverse=True,
    )
    winner_entry = {
        "exercise": winner.exercise.value,
        "display_name": winner.display_name,
        "source": winner_source,
        "confidence": round(float(winner.confidence), 3),
        "score": round(float(winner_score), 3),
    }
    out: list[dict[str, Any]] = [winner_entry]
    for item in ranked:
        if item["exercise"] == winner_entry["exercise"]:
            continue
        out.append(item)
        if len(out) >= max(1, int(limit)):
            break
    return out[: max(1, int(limit))]


def _append_rules_db_detection_candidates(
    detection: DetectionResult,
    *,
    raw_hint: str | None,
    limit: int = 5,
) -> None:
    """Enrichit la liste de candidats avec suggestions rules-db si disponible."""
    hint = (raw_hint or "").strip()
    if not hint:
        return
    suggestions = suggest_supported_exercises(hint, limit=limit)
    if not suggestions:
        return

    existing = {
        str(item.get("exercise", ""))
        for item in detection.top_candidates
    }
    for item in suggestions:
        ex = str(item.get("exercise", "")).strip()
        if not ex or ex in existing:
            continue
        detection.top_candidates.append(
            {
                "exercise": ex,
                "display_name": ex.replace("_", " ").title(),
                "source": "rules_db_suggest",
                "confidence": round(float(item.get("rule_confidence", 0.0) or 0.0), 3),
                "score": round(float(item.get("score", 0.0) or 0.0), 3),
            }
        )
        existing.add(ex)
        if len(detection.top_candidates) >= max(1, int(limit)):
            break
    detection.top_candidates = detection.top_candidates[: max(1, int(limit))]


def _apply_minimax_analysis_to_result(
    result: PipelineResult,
    analysis: MiniMaxAnalysis,
) -> PipelineResult:
    """Map MiniMax structured output to the internal PipelineResult schema."""
    raw_name = analysis.exercise_slug or analysis.exercise_display
    mapped_name = _map_model_exercise_name(raw_name)

    try:
        exercise_enum = Exercise(mapped_name)
    except ValueError:
        exercise_enum = Exercise.UNKNOWN

    detection = DetectionResult(
        exercise=exercise_enum,
        confidence=max(0.0, min(1.0, float(analysis.exercise_confidence or 0.0))),
        reasoning="[MiniMax Motion Coach] analyse vision complete",
    )
    detection.top_candidates = [
        {
            "exercise": exercise_enum.value,
            "display_name": analysis.exercise_display or detection.display_name,
            "source": "minimax_motion_coach",
            "confidence": round(float(detection.confidence), 3),
            "score": round(float(detection.confidence), 3),
        }
    ]
    result.detection = detection

    rep_seg = RepSegmentation()
    rep_seg.total_reps = max(0, int(analysis.reps_total or 0))
    rep_seg.complete_reps = max(0, int(analysis.reps_complete or rep_seg.total_reps))
    rep_seg.partial_reps = max(0, int(analysis.reps_partial or max(0, rep_seg.total_reps - rep_seg.complete_reps)))
    try:
        _intensity_score = int(float(analysis.intensity_score))
    except Exception:
        _intensity_score = 0
    rep_seg.intensity_score = max(0, min(100, _intensity_score))
    rep_seg.intensity_label = str(analysis.intensity_label or "indeterminee")
    rep_seg.avg_inter_rep_rest_s = max(0.0, float(analysis.avg_inter_rep_rest_s or 0.0))
    rep_seg.median_inter_rep_rest_s = rep_seg.avg_inter_rep_rest_s
    rep_seg.max_inter_rep_rest_s = rep_seg.avg_inter_rep_rest_s
    rep_seg.intensity_confidence = "moderee"
    rep_seg.rest_measure_method = "minimax_motion_coach"
    result.reps = rep_seg

    try:
        _score = int(float(analysis.score))
    except Exception:
        _score = 0
    score = max(0, min(100, _score))
    display_name = analysis.exercise_display or detection.display_name
    report_text = (analysis.report_text or analysis.raw_response or "").strip()
    if not report_text:
        report_text = "Analyse MiniMax terminee."

    corrective_exercises: list[str] = []
    for item in analysis.corrective_exercises:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "").strip()
        dosage = str(item.get("dosage", "") or "").strip()
        target = str(item.get("target", "") or "").strip()
        parts = [part for part in (name, dosage, target) if part]
        if parts:
            corrective_exercises.append(" — ".join(parts))

    result.report = Report(
        exercise=exercise_enum.value,
        exercise_display=display_name,
        score=score,
        report_text=report_text,
        positives=analysis.positives,
        corrections=analysis.corrections,
        corrective_exercises=corrective_exercises,
        score_breakdown=analysis.score_breakdown,
        raw_llm_response=analysis.raw_response,
        model_used=analysis.model_used,
    )
    return result


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

    # ── Provider prioritaire : MiniMax Motion Coach ─────────────────────
    if cfg.use_minimax_motion_coach:
        logger.info("Provider MiniMax Motion Coach active — tentative d'analyse externe.")
        _notify_progress(cfg, 5, "MiniMax Motion Coach: analyse")
        t0_minimax = time.monotonic()
        try:
            minimax_analysis = run_minimax_motion_coach(str(video))
            result = _apply_minimax_analysis_to_result(result, minimax_analysis)
            result.timings["minimax_motion_coach"] = time.monotonic() - t0_minimax
            _notify_progress(cfg, 10, "MiniMax Motion Coach: rapport")

            if cfg.save_json:
                try:
                    json_data = pipeline_result_to_dict(result)
                    json_path = out_dir / "analysis_result.json"
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)
                    result.json_path = str(json_path)
                except Exception as e:
                    result.errors.append(f"Sauvegarde JSON échouée: {e}")

            result.success = result.report is not None
            result.total_time = time.monotonic() - pipeline_start
            logger.info(
                "Pipeline MiniMax terminé en %.1fs (succès: %s)",
                result.total_time,
                result.success,
            )
            return result
        except Exception as e:
            result.errors.append(f"MiniMax Motion Coach échoué: {e}")
            logger.error("MiniMax Motion Coach échoué: %s", e, exc_info=True)
            if not cfg.minimax_fallback_to_local:
                result.user_messages.append(_minimax_user_message(str(e)))
                result.total_time = time.monotonic() - pipeline_start
                return result
            logger.warning("Fallback vers pipeline local après échec MiniMax.")

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
    gemini_raw_exercise_name = ""
    pattern_seed = detect_by_pattern(angles)
    motion = _motion_profile(angles)
    press_profile = _compute_press_profile(extraction, angles)
    upper_pull_profile = _compute_upper_pull_profile(extraction, angles)
    unilateral_profile = _compute_unilateral_profile(angles, extraction=extraction)
    logger.info(
        "  → Pattern seed: %s (conf=%.2f) | motion=%s | press_profile=%s | upper_pull=%s | unilateral=%s",
        pattern_seed.exercise.value,
        pattern_seed.confidence,
        motion,
        press_profile,
        upper_pull_profile,
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

        candidate_exercises = _get_candidate_exercises(pattern_seed, n=30)
        gemini_result = detect_exercise_gemini(
            video_path=str(video),
            candidate_exercises=candidate_exercises,
        )

        exercise_name = _normalize_exercise_name(gemini_result.get("exercise"))
        gemini_raw_exercise_name = str(gemini_result.get("exercise", "") or "")
        mapped_name = _map_model_exercise_name(exercise_name)
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
            upper_pull_profile=upper_pull_profile,
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
            pattern_conf = min(0.80, max(0.40, float(pattern_seed.confidence) * 0.86))
            pattern_vote = DetectionResult(
                exercise=pattern_seed.exercise,
                confidence=pattern_conf,
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
                upper_pull_profile=upper_pull_profile,
                unilateral_profile=unilateral_profile,
            )
            scored_candidates.append((src_name, cand, cand_score))

        source, detection, winning_score = max(scored_candidates, key=lambda item: item[2])
        source, detection, winning_score = apply_gemini_vision_consensus_override(
            source,
            detection,
            winning_score,
            scored_candidates,
            press_profile=press_profile,
        )
        source, detection, winning_score = _apply_lower_static_upper_override(
            source,
            detection,
            winning_score,
            scored_candidates,
            motion,
        )
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

        # Fallback unilatéral:
        # même si Gemini se trompe (squat), basculer vers la meilleure hypothèse
        # unilatérale quand le signal biomécanique est clairement split/elevated.
        if (
            detection.exercise in _BILATERAL_SQUAT_EXERCISES
            and bool(unilateral_profile.get("strong_unilateral_signal", False))
        ):
            best_unilateral: tuple[str, DetectionResult, float] | None = None
            for src_name, cand, cand_score in scored_candidates:
                if cand.exercise not in _UNILATERAL_LOWER_EXERCISES:
                    continue
                if best_unilateral is None or cand_score > best_unilateral[2]:
                    best_unilateral = (src_name, cand, cand_score)
            if best_unilateral is not None:
                split_stance_ratio = float(unilateral_profile.get("split_stance_ratio", 0.0) or 0.0)
                ankle_height_ratio = float(unilateral_profile.get("ankle_height_asym_ratio", 0.0) or 0.0)
                should_override = (
                    best_unilateral[2] + 0.04 >= winning_score
                    or best_unilateral[1].confidence >= 0.70
                    or split_stance_ratio >= 0.32
                    or ankle_height_ratio >= 0.24
                )
                if should_override:
                    logger.warning(
                        "Unilateral fallback override: %s -> %s (source=%s, score=%.3f, split=%.3f, ankle_height=%.3f)",
                        detection.exercise.value,
                        best_unilateral[1].exercise.value,
                        best_unilateral[0],
                        best_unilateral[2],
                        split_stance_ratio,
                        ankle_height_ratio,
                    )
                    source = "unilateral_fallback_override"
                    detection = best_unilateral[1]

        # Si Gemini n'est pas retenu, ne pas propager son rep_count (souvent corrélé à sa mauvaise classe).
        if not source.startswith("gemini"):
            gemini_rep_count = 0

        source, detection = disambiguate_upper_pull_exercise(
            source,
            detection,
            upper_pull_profile=upper_pull_profile,
        )
        if source == "upper_pull_disambiguation":
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
                "upper_pull_profile": upper_pull_profile,
                "unilateral_profile": unilateral_profile,
                "candidate_scores": ";".join(
                    "{}:{}:{:.3f}".format(src_name, cand.exercise.value, cand_score)
                    for src_name, cand, cand_score in scored_candidates
                ),
            })
        except Exception:
            pass

        detection.top_candidates = _build_top_detection_candidates(
            scored_candidates=scored_candidates,
            winner=detection,
            winner_source=source,
            winner_score=winning_score,
            limit=5,
        )
        _append_rules_db_detection_candidates(
            detection,
            raw_hint=gemini_raw_exercise_name or detection.exercise.value,
            limit=5,
        )

    if not detection.top_candidates:
        fallback_scored: list[tuple[str, DetectionResult, float]] = [
            ("final", detection, float(detection.confidence)),
        ]
        if pattern_seed.exercise != Exercise.UNKNOWN:
            fallback_scored.append(
                (
                    "pattern",
                    DetectionResult(
                        exercise=pattern_seed.exercise,
                        confidence=float(pattern_seed.confidence),
                        reasoning=pattern_seed.reasoning,
                    ),
                    float(pattern_seed.confidence),
                )
            )
        detection.top_candidates = _build_top_detection_candidates(
            scored_candidates=fallback_scored,
            winner=detection,
            winner_source="final",
            winner_score=float(detection.confidence),
            limit=5,
        )
        _append_rules_db_detection_candidates(
            detection,
            raw_hint=gemini_raw_exercise_name or detection.exercise.value,
            limit=5,
        )

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
        from analysis.pose_extractor import _detect_key_frames
        new_indices = _detect_key_frames(extraction.frames, detection.exercise.value)
        if new_indices != extraction.key_frame_indices:
            _persist_key_frames(extraction, new_indices)
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
    robust_reliable = bool(getattr(result.reps, "robust_reliable", False)) if result.reps else False
    reference_rep_count = select_reference_rep_count(
        signal_rep_count=signal_rep_count,
        robust_rep_count=robust_rep_count,
        robust_reliable=robust_reliable,
    )
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
            segmented_rep_count = len(result.reps.reps or [])
            logger.info(
                "Rep fusion override: signal=%d, robust=%d, gemini=%d, vision=%d -> final=%d",
                signal_rep_count,
                robust_rep_count,
                gemini_rep_count,
                vision_rep_count,
                final_rep_count,
            )
            result.reps.total_reps = final_rep_count
            if segmented_rep_count > final_rep_count and result.reps.reps:
                # Keep report-level coherence when segmentation overcounted noisy micro-cycles.
                result.reps.reps = result.reps.reps[:final_rep_count]
            if result.reps.reps:
                first_rep = result.reps.reps[0]
                last_rep = result.reps.reps[-1]
                result.reps.movement_start_frame = int(getattr(first_rep, "start_frame", 0) or 0)
                result.reps.movement_end_frame = int(getattr(last_rep, "end_frame", 0) or 0)
                if extraction.fps > 0:
                    result.reps.movement_duration_s = max(
                        0.0,
                        float(result.reps.movement_end_frame - result.reps.movement_start_frame) / float(extraction.fps),
                    )
            if result.reps.complete_reps <= 0:
                result.reps.complete_reps = final_rep_count
            else:
                result.reps.complete_reps = min(result.reps.complete_reps, final_rep_count)
            result.reps.partial_reps = max(0, final_rep_count - result.reps.complete_reps)

            duration_hint_s = float(getattr(result.reps, "set_duration_s", 0.0) or 0.0)
            if duration_hint_s <= 0:
                duration_hint_s = duration_s

            mismatch_after_fusion = abs(segmented_rep_count - final_rep_count)
            if mismatch_after_fusion >= max(2, int(final_rep_count * 0.20)):
                fused_intensity = estimate_intensity_from_fused_count(final_rep_count, duration_hint_s)
                result.reps.avg_inter_rep_rest_s = float(fused_intensity["avg_inter_rep_rest_s"])
                result.reps.median_inter_rep_rest_s = float(fused_intensity["median_inter_rep_rest_s"])
                result.reps.max_inter_rep_rest_s = float(fused_intensity["max_inter_rep_rest_s"])
                result.reps.rest_consistency = float(fused_intensity["rest_consistency"])
                result.reps.set_duration_s = float(fused_intensity["set_duration_s"])
                result.reps.reps_per_min = float(fused_intensity["reps_per_min"])
                result.reps.intensity_score = int(fused_intensity["intensity_score"])
                result.reps.intensity_label = str(fused_intensity["intensity_label"])
                result.reps.intensity_confidence = "limitee (fusion count)"
                result.reps.rest_measure_method = "estimate_from_fused_count"

    # Debug log for visibility in /debug/errors endpoint.
    try:
        from app.debug_log import log_error as _dbg
        _dbg("rep_count_fusion", "Rep count fusion result", {
            "signal_rep_count": signal_rep_count,
            "robust_rep_count": robust_rep_count,
            "robust_reliable": robust_reliable,
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

    # Align key frames with segmented reps (true movement start/peak/end) when possible.
    try:
        rep_keyframes = _derive_key_frames_from_reps(
            result.reps,
            extraction.total_frames,
            exercise_name=detection.exercise.value,
            extraction_frames=extraction.frames,
        )
        if rep_keyframes:
            _persist_key_frames(extraction, rep_keyframes)
            logger.info(
                "  → Key frames aligned to reps: start=%d mid=%d end=%d",
                rep_keyframes["start"],
                rep_keyframes["mid"],
                rep_keyframes["end"],
            )
    except Exception as e:
        logger.warning("Rep-based key frame alignment failed: %s", e)

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
            "top_candidates": result.detection.top_candidates[:5],
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
