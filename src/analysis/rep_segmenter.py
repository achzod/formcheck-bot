"""Détection automatique des répétitions individuelles.

Segmente le signal angulaire principal en reps via détection
de pics et vallées, puis calcule tempo, ROM, vitesse, fatigue
et détection de triche pour chaque rep.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from analysis.angle_calculator import AngleResult, FrameAngles

try:
    from app.debug_log import log_error as _debug_log
except ImportError:
    def _debug_log(context: str, error: str, extra: dict | None = None) -> None:
        pass

logger = logging.getLogger("formcheck.rep_segmenter")

# ═══════════════════════════════════════════════════════════════════════════
# PRIMARY_ANGLE_MAP — angle principal pour la segmentation de chaque exercice
# ═══════════════════════════════════════════════════════════════════════════

PRIMARY_ANGLE_MAP: dict[str, str] = {
    # ── Knee-dominant (squats, lunges, leg press, etc.) ──
    "squat": "left_knee_flexion",
    "front_squat": "left_knee_flexion",
    "goblet_squat": "left_knee_flexion",
    "bulgarian_split_squat": "left_knee_flexion",
    "lunge": "left_knee_flexion",
    "walking_lunge": "left_knee_flexion",
    "leg_press": "left_knee_flexion",
    "leg_extension": "left_knee_flexion",
    "leg_curl": "left_knee_flexion",
    "hack_squat": "left_knee_flexion",
    "sissy_squat": "left_knee_flexion",
    "step_up": "left_knee_flexion",
    "nordic_curl": "left_knee_flexion",
    "thruster": "left_knee_flexion",

    # ── Hip-dominant (deadlifts, RDL, good morning, hip thrust, etc.) ──
    "deadlift": "left_hip_flexion",
    "sumo_deadlift": "left_hip_flexion",
    "trap_bar_deadlift": "left_hip_flexion",
    "rdl": "left_hip_flexion",
    "single_leg_rdl": "left_hip_flexion",
    "hip_thrust": "left_hip_flexion",
    "glute_bridge": "left_hip_flexion",
    "good_morning": "left_hip_flexion",
    "kettlebell_swing": "left_hip_flexion",
    "cable_kickback": "left_hip_flexion",
    "glute_ham_raise": "left_hip_flexion",

    # ── Elbow-dominant (pressing, rowing, curls, extensions, pulls) ──
    "bench_press": "left_elbow_flexion",
    "incline_bench": "left_elbow_flexion",
    "decline_bench": "left_elbow_flexion",
    "dumbbell_bench": "left_elbow_flexion",
    "dumbbell_incline": "left_elbow_flexion",
    "close_grip_bench": "left_elbow_flexion",
    "machine_chest_press": "left_elbow_flexion",
    "ohp": "left_elbow_flexion",
    "dumbbell_ohp": "left_elbow_flexion",
    "arnold_press": "left_elbow_flexion",
    "landmine_press": "left_elbow_flexion",
    "push_up": "left_elbow_flexion",
    "diamond_pushup": "left_elbow_flexion",
    "dip": "left_elbow_flexion",
    "chest_dip": "left_elbow_flexion",
    "curl": "left_elbow_flexion",
    "dumbbell_curl": "left_elbow_flexion",
    "hammer_curl": "left_elbow_flexion",
    "preacher_curl": "left_elbow_flexion",
    "cable_curl": "left_elbow_flexion",
    "incline_curl": "left_elbow_flexion",
    "concentration_curl": "left_elbow_flexion",
    "spider_curl": "left_elbow_flexion",
    "tricep_extension": "left_elbow_flexion",
    "skull_crusher": "left_elbow_flexion",
    "overhead_tricep": "left_elbow_flexion",
    "kickback": "left_elbow_flexion",
    "cable_overhead_tricep": "left_elbow_flexion",
    "barbell_row": "left_elbow_flexion",
    "dumbbell_row": "left_elbow_flexion",
    "pendlay_row": "left_elbow_flexion",
    "cable_row": "left_elbow_flexion",
    "tbar_row": "left_elbow_flexion",
    "seal_row": "left_elbow_flexion",
    "pullup": "left_elbow_flexion",
    "chinup": "left_elbow_flexion",
    "lat_pulldown": "left_elbow_flexion",
    "close_grip_pulldown": "left_elbow_flexion",
    "svend_press": "left_elbow_flexion",

    # ── Shoulder-dominant (raises, face pulls, flyes, shrugs) ──
    "lateral_raise": "left_shoulder_abduction",
    "cable_lateral_raise": "left_shoulder_abduction",
    "front_raise": "left_shoulder_flexion",
    "face_pull": "left_shoulder_abduction",
    "reverse_fly": "left_shoulder_abduction",
    "rear_delt_fly": "left_shoulder_abduction",
    "upright_row": "left_shoulder_abduction",
    "lu_raise": "left_shoulder_abduction",
    "shrug": "left_shoulder_abduction",
    "chest_fly": "left_shoulder_abduction",
    "cable_crossover": "left_shoulder_abduction",
    "cable_pullover": "left_shoulder_flexion",
    "pullover": "left_shoulder_flexion",

    # ── Torso / core ──
    "crunch": "trunk_inclination",
    "cable_crunch": "trunk_inclination",
    "hanging_leg_raise": "left_hip_flexion",
    "ab_wheel": "trunk_inclination",
    "plank": "trunk_inclination",
    "woodchop": "trunk_inclination",

    # ── Mollets ──
    "calf_raise": "left_knee_flexion",
    "seated_calf_raise": "left_knee_flexion",

    # ── Full body / olympiques ──
    "clean": "left_hip_flexion",
    "snatch": "left_hip_flexion",
    "battle_rope": "left_shoulder_flexion",
}

# ═══════════════════════════════════════════════════════════════════════════
# SLOW_EXERCISES — détection adaptative avec prominence réduite
# ═══════════════════════════════════════════════════════════════════════════

SLOW_EXERCISES: set[str] = {
    # Isolation lente
    "rdl", "single_leg_rdl", "hip_thrust", "glute_bridge",
    "leg_curl", "leg_extension", "good_morning",
    "lateral_raise", "cable_lateral_raise", "front_raise",
    "face_pull", "reverse_fly", "rear_delt_fly", "lu_raise",
    "tricep_extension", "skull_crusher", "kickback",
    "overhead_tricep", "cable_overhead_tricep",
    "preacher_curl", "concentration_curl", "spider_curl", "incline_curl",
    "chest_fly", "cable_crossover", "svend_press",
    "cable_pullover", "pullover",
    "cable_kickback", "glute_ham_raise",
    "calf_raise", "seated_calf_raise",
    "shrug",
    # Core (tempos lents)
    "crunch", "cable_crunch", "ab_wheel", "plank",
    "hanging_leg_raise", "woodchop",
    # Nordic (excentrique tres lent)
    "nordic_curl",
}

# ═══════════════════════════════════════════════════════════════════════════
# CHEAT_ANGLE_MAP — angle de triche (mouvement parasite du tronc)
# ═══════════════════════════════════════════════════════════════════════════

CHEAT_ANGLE_MAP: dict[str, str] = {
    # Curls — le swing du tronc est la triche #1
    "curl": "trunk_inclination",
    "dumbbell_curl": "trunk_inclination",
    "hammer_curl": "trunk_inclination",
    "cable_curl": "trunk_inclination",
    "preacher_curl": "trunk_inclination",
    "incline_curl": "trunk_inclination",
    "concentration_curl": "trunk_inclination",
    "spider_curl": "trunk_inclination",
    # Rows — le tronc ne doit pas bouger
    "barbell_row": "trunk_inclination",
    "dumbbell_row": "trunk_inclination",
    "pendlay_row": "trunk_inclination",
    "tbar_row": "trunk_inclination",
    "cable_row": "trunk_inclination",
    # Presses debout — cambrure lombaire
    "ohp": "trunk_inclination",
    "dumbbell_ohp": "trunk_inclination",
    "arnold_press": "trunk_inclination",
    "landmine_press": "trunk_inclination",
    # Raises — compensation du tronc
    "lateral_raise": "trunk_inclination",
    "cable_lateral_raise": "trunk_inclination",
    "front_raise": "trunk_inclination",
    "upright_row": "trunk_inclination",
    "face_pull": "trunk_inclination",
    # Triceps — lean forward
    "tricep_extension": "trunk_inclination",
    "overhead_tricep": "trunk_inclination",
    "cable_overhead_tricep": "trunk_inclination",
    # Squats/deadlifts — inclinaison excessive
    "squat": "trunk_inclination",
    "front_squat": "trunk_inclination",
    "goblet_squat": "trunk_inclination",
    "deadlift": "trunk_inclination",
    "sumo_deadlift": "trunk_inclination",
    "trap_bar_deadlift": "trunk_inclination",
    # Bench — arching excessif
    "bench_press": "trunk_inclination",
    "incline_bench": "trunk_inclination",
    "decline_bench": "trunk_inclination",
}

# Seuils de triche : variation max acceptable du tronc pendant une rep (degrés)
CHEAT_THRESHOLD: dict[str, float] = {
    # Curls — strict, le tronc ne bouge pas
    "curl": 10.0,
    "dumbbell_curl": 10.0,
    "hammer_curl": 10.0,
    "cable_curl": 8.0,
    "preacher_curl": 5.0,
    "incline_curl": 5.0,
    "concentration_curl": 5.0,
    "spider_curl": 5.0,
    # Rows
    "barbell_row": 12.0,
    "dumbbell_row": 12.0,
    "pendlay_row": 8.0,
    "tbar_row": 12.0,
    "cable_row": 8.0,
    # Presses debout
    "ohp": 8.0,
    "dumbbell_ohp": 8.0,
    "arnold_press": 8.0,
    "landmine_press": 10.0,
    # Raises
    "lateral_raise": 8.0,
    "cable_lateral_raise": 6.0,
    "front_raise": 8.0,
    "upright_row": 8.0,
    "face_pull": 6.0,
    # Triceps
    "tricep_extension": 8.0,
    "overhead_tricep": 10.0,
    "cable_overhead_tricep": 10.0,
    # Squats
    "squat": 15.0,
    "front_squat": 12.0,
    "goblet_squat": 10.0,
    # Deadlifts — le tronc bouge naturellement, seuils plus larges
    "deadlift": 20.0,
    "sumo_deadlift": 18.0,
    "trap_bar_deadlift": 18.0,
    # Bench
    "bench_press": 5.0,
    "incline_bench": 5.0,
    "decline_bench": 5.0,
}

# ═══════════════════════════════════════════════════════════════════════════
# MIN_ROM_THRESHOLD — ROM minimum (degrés) pour compter une rep valide
# ═══════════════════════════════════════════════════════════════════════════

MIN_ROM_THRESHOLD: dict[str, float] = {
    # Squats / lunges — au moins 30 deg de flexion du genou
    "squat": 30.0,
    "front_squat": 30.0,
    "goblet_squat": 25.0,
    "hack_squat": 30.0,
    "bulgarian_split_squat": 25.0,
    "lunge": 20.0,
    "walking_lunge": 20.0,
    "leg_press": 30.0,
    "sissy_squat": 20.0,
    "step_up": 20.0,
    # Leg isolation
    "leg_extension": 25.0,
    "leg_curl": 20.0,
    # Hip hinge
    "deadlift": 25.0,
    "sumo_deadlift": 20.0,
    "trap_bar_deadlift": 25.0,
    "rdl": 20.0,
    "single_leg_rdl": 15.0,
    "good_morning": 15.0,
    "hip_thrust": 15.0,
    "glute_bridge": 10.0,
    "kettlebell_swing": 15.0,
    # Pressing
    "bench_press": 25.0,
    "incline_bench": 25.0,
    "decline_bench": 25.0,
    "dumbbell_bench": 25.0,
    "dumbbell_incline": 25.0,
    "close_grip_bench": 25.0,
    "machine_chest_press": 25.0,
    "ohp": 25.0,
    "dumbbell_ohp": 25.0,
    "arnold_press": 25.0,
    "push_up": 25.0,
    "diamond_pushup": 20.0,
    "dip": 20.0,
    "chest_dip": 20.0,
    # Curls
    "curl": 30.0,
    "dumbbell_curl": 30.0,
    "hammer_curl": 30.0,
    "preacher_curl": 25.0,
    "cable_curl": 25.0,
    "incline_curl": 25.0,
    "concentration_curl": 25.0,
    "spider_curl": 25.0,
    # Triceps
    "tricep_extension": 25.0,
    "skull_crusher": 25.0,
    "overhead_tricep": 25.0,
    "kickback": 20.0,
    "cable_overhead_tricep": 25.0,
    # Rows / pulls
    "barbell_row": 20.0,
    "dumbbell_row": 20.0,
    "pendlay_row": 20.0,
    "cable_row": 20.0,
    "tbar_row": 20.0,
    "seal_row": 20.0,
    "pullup": 20.0,
    "chinup": 20.0,
    "lat_pulldown": 25.0,
    "close_grip_pulldown": 25.0,
    # Raises — faible ROM par nature
    "lateral_raise": 15.0,
    "cable_lateral_raise": 12.0,
    "front_raise": 15.0,
    "face_pull": 10.0,
    "reverse_fly": 10.0,
    "rear_delt_fly": 10.0,
    "upright_row": 15.0,
    "lu_raise": 15.0,
    "shrug": 5.0,
    # Chest isolation
    "chest_fly": 15.0,
    "cable_crossover": 15.0,
    # Pullovers
    "cable_pullover": 15.0,
    "pullover": 15.0,
    "svend_press": 15.0,
    "landmine_press": 20.0,
    # Core
    "crunch": 5.0,
    "cable_crunch": 5.0,
    "hanging_leg_raise": 10.0,
    "ab_wheel": 10.0,
    "woodchop": 10.0,
    # Mollets
    "calf_raise": 5.0,
    "seated_calf_raise": 5.0,
    # Autres
    "nordic_curl": 15.0,
    "glute_ham_raise": 15.0,
    "cable_kickback": 10.0,
    "thruster": 25.0,
    "clean": 20.0,
    "snatch": 20.0,
    "battle_rope": 10.0,
    "plank": 0.0,  # isometrique, pas de ROM
}


def _attr_group(attr: str) -> str:
    if "knee" in attr or "hip" in attr:
        return "lower"
    if "elbow" in attr or "shoulder" in attr:
        return "upper"
    if "trunk" in attr:
        return "core"
    return "mixed"


def _exercise_motion_group(exercise: str) -> str:
    preferred = PRIMARY_ANGLE_MAP.get(exercise, "")
    if preferred:
        return _attr_group(preferred)
    return "mixed"


def _joint_names_for_exercise(exercise: str) -> set[str]:
    group = _exercise_motion_group(exercise)
    if group == "lower":
        return {
            "left_hip", "right_hip",
            "left_knee", "right_knee",
            "left_ankle", "right_ankle",
        }
    if group == "upper":
        return {
            "left_shoulder", "right_shoulder",
            "left_elbow", "right_elbow",
            "left_wrist", "right_wrist",
        }
    if group == "core":
        return {
            "left_shoulder", "right_shoulder",
            "left_hip", "right_hip",
        }
    return set(_JOINT_INDICES.keys())


@dataclass
class Rep:
    """Une répétition individuelle."""
    rep_number: int = 0
    start_frame: int = 0
    end_frame: int = 0
    bottom_frame: int = 0
    eccentric_frames: tuple[int, int] = (0, 0)
    concentric_frames: tuple[int, int] = (0, 0)
    eccentric_duration_ms: float = 0.0
    concentric_duration_ms: float = 0.0
    tempo_ratio: float = 0.0
    rom: float = 0.0
    peak_velocity: float = 0.0
    is_partial: bool = False
    # Fatigue
    fatigue_index: float = 0.0  # 0 = frais, 1 = fatigue significative
    rom_vs_first: float = 1.0  # ratio ROM cette rep / rep 1
    velocity_vs_first: float = 1.0  # ratio vitesse / rep 1
    # Triche / momentum
    cheat_detected: bool = False
    cheat_score: float = 0.0  # 0 = clean, 1 = triche flagrante
    cheat_details: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = {
            "rep_number": self.rep_number,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "bottom_frame": self.bottom_frame,
            "eccentric_frames": list(self.eccentric_frames),
            "concentric_frames": list(self.concentric_frames),
            "rom": round(self.rom, 1),
            "peak_velocity": round(self.peak_velocity, 1),
            "fatigue_index": round(self.fatigue_index, 3),
            "rom_vs_first": round(self.rom_vs_first, 3),
            "velocity_vs_first": round(self.velocity_vs_first, 3),
        }
        if self.is_partial:
            d["is_partial"] = True
        if self.cheat_detected:
            d["cheat_detected"] = True
            d["cheat_score"] = round(self.cheat_score, 2)
            d["cheat_details"] = self.cheat_details
        return d


@dataclass
class RepSegmentation:
    """Résultat de la segmentation en répétitions."""
    reps: list[Rep] = field(default_factory=list)
    total_reps: int = 0
    complete_reps: int = 0
    partial_reps: int = 0
    avg_tempo: str = "0:0:0"
    tempo_consistency: float = 0.0
    set_complete: bool = False
    # Fatigue globale
    avg_rom: float = 0.0
    rom_degradation: float = 0.0  # % perte ROM entre première et dernière rep
    velocity_degradation: float = 0.0  # % perte vitesse concentrique
    fatigue_onset_rep: int = 0  # rep où la fatigue commence (ROM < 90% de rep 1)
    fatigue_index_last_rep: float = 0.0  # fatigue de la dernière rep
    # Triche globale
    cheat_reps: list[int] = field(default_factory=list)
    cheat_percentage: float = 0.0  # % de reps avec triche détectée
    # Debug / fusion multi-méthode
    peak_count: int = 0
    autocorr_count: int = 0
    zerocross_count: int = 0
    extrema_count: int = 0
    robust_count: int = 0
    robust_reliable: bool = False
    count_method: str = "peak"
    segmentation_signal: str = ""
    auto_signal_selected: bool = False
    # Intensite de serie (densite = repos inter-reps)
    avg_inter_rep_rest_s: float = 0.0
    median_inter_rep_rest_s: float = 0.0
    max_inter_rep_rest_s: float = 0.0
    rest_consistency: float = 0.0  # 0-1 (1 = repos tres regulier)
    set_duration_s: float = 0.0
    reps_per_min: float = 0.0
    intensity_score: int = 0  # 0-100
    intensity_label: str = "indeterminee"
    intensity_confidence: str = "faible"
    rest_measure_method: str = "frame_gap"
    movement_start_frame: int = 0
    movement_end_frame: int = 0
    movement_duration_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = {
            "reps": [r.to_dict() for r in self.reps],
            "total_reps": self.total_reps,
            "complete_reps": self.complete_reps,
            "partial_reps": self.partial_reps,
            "count_method": self.count_method,
            "count_debug": {
                "peak_count": self.peak_count,
                "autocorr_count": self.autocorr_count,
                "zerocross_count": self.zerocross_count,
                "extrema_count": self.extrema_count,
                "robust_count": self.robust_count,
                "robust_reliable": self.robust_reliable,
                "segmentation_signal": self.segmentation_signal,
                "auto_signal_selected": self.auto_signal_selected,
            },
            "intensity": {
                "score": self.intensity_score,
                "label": self.intensity_label,
                "confidence": self.intensity_confidence,
                "rest_measure_method": self.rest_measure_method,
                "avg_inter_rep_rest_s": round(self.avg_inter_rep_rest_s, 2),
                "median_inter_rep_rest_s": round(self.median_inter_rep_rest_s, 2),
                "max_inter_rep_rest_s": round(self.max_inter_rep_rest_s, 2),
                "rest_consistency": round(self.rest_consistency, 3),
                "set_duration_s": round(self.set_duration_s, 2),
                "reps_per_min": round(self.reps_per_min, 1),
            },
            "movement": {
                "start_frame": self.movement_start_frame,
                "end_frame": self.movement_end_frame,
                "duration_s": round(self.movement_duration_s, 2),
            },
            "avg_tempo": "NON DISPONIBLE — mesure automatique non fiable",
            "tempo_consistency": "NON DISPONIBLE — mesure automatique non fiable",
            "set_complete": self.set_complete,
            "avg_rom": round(self.avg_rom, 1),
            "rom_degradation": round(self.rom_degradation, 1),
            "velocity_degradation": round(self.velocity_degradation, 1),
            "fatigue_onset_rep": self.fatigue_onset_rep,
            "fatigue_index_last_rep": round(self.fatigue_index_last_rep, 3),
        }
        if self.cheat_reps:
            d["cheat_reps"] = self.cheat_reps
            d["cheat_percentage"] = round(self.cheat_percentage, 1)
        return d


def _get_signal(
    angle_frames: list[FrameAngles],
    attr: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Extrait le signal d'un angle et les indices de frames correspondants."""
    values = []
    indices = []
    for f in angle_frames:
        val = getattr(f, attr, None)
        if val is not None:
            values.append(val)
            indices.append(f.frame_index)
    return np.array(values), np.array(indices)


def _mirror_attr(attr: str) -> str:
    if attr.startswith("left_"):
        return "right_" + attr[len("left_"):]
    if attr.startswith("right_"):
        return "left_" + attr[len("right_"):]
    return attr


def _signal_quality(signal: np.ndarray, fps: float) -> float:
    """Heuristic quality score for rep segmentation suitability."""
    if len(signal) < 10:
        return 0.0
    p95 = float(np.percentile(signal, 95))
    p05 = float(np.percentile(signal, 5))
    rom = max(0.0, p95 - p05)
    if rom <= 0.5:
        return 0.0
    smoothed = _smooth_signal(signal, window=max(3, min(5, int(fps * 0.1))))
    motion = float(np.mean(np.abs(np.diff(smoothed)))) * max(1.0, fps)
    density_bonus = min(len(signal), 240) / 120.0
    return rom + (motion * 0.05) + density_bonus


def _default_min_rom_for_attr(attr: str) -> float:
    if "knee" in attr:
        return 20.0
    if "hip" in attr:
        return 15.0
    if "elbow" in attr:
        return 18.0
    if "shoulder" in attr:
        return 12.0
    if "trunk" in attr:
        return 8.0
    return 10.0


def _select_segmentation_signal(
    angle_frames: list[FrameAngles],
    exercise: str,
    fps: float,
) -> tuple[str, np.ndarray, np.ndarray, bool]:
    """Select the best angle signal for rep segmentation.

    Starts from the exercise-specific primary angle, but can auto-fallback
    to a more informative signal when detection is likely wrong or one side
    is poorly tracked.
    """
    preferred = PRIMARY_ANGLE_MAP.get(exercise, "left_knee_flexion")
    target_group = _exercise_motion_group(exercise)
    group_candidates: dict[str, list[str]] = {
        "lower": [
            "left_knee_flexion",
            "right_knee_flexion",
            "left_hip_flexion",
            "right_hip_flexion",
            "trunk_inclination",
        ],
        "upper": [
            "left_elbow_flexion",
            "right_elbow_flexion",
            "left_shoulder_flexion",
            "right_shoulder_flexion",
            "left_shoulder_abduction",
            "right_shoulder_abduction",
            "trunk_inclination",
        ],
        "core": [
            "trunk_inclination",
            "left_hip_flexion",
            "right_hip_flexion",
        ],
    }
    fallback_all = [
        "left_knee_flexion",
        "right_knee_flexion",
        "left_hip_flexion",
        "right_hip_flexion",
        "left_elbow_flexion",
        "right_elbow_flexion",
        "left_shoulder_flexion",
        "right_shoulder_flexion",
        "left_shoulder_abduction",
        "right_shoulder_abduction",
        "trunk_inclination",
    ]
    if target_group in group_candidates:
        candidates = [preferred, _mirror_attr(preferred)] + group_candidates[target_group]
    else:
        candidates = [preferred, _mirror_attr(preferred)] + fallback_all

    seen: set[str] = set()
    ordered: list[str] = []
    for attr in candidates:
        if attr and attr not in seen:
            ordered.append(attr)
            seen.add(attr)

    best_attr = preferred
    best_signal = np.array([])
    best_indices = np.array([])
    best_score = -1.0

    for attr in ordered:
        signal, indices = _get_signal(angle_frames, attr)
        score = _signal_quality(signal, fps)
        if score > best_score:
            best_score = score
            best_attr = attr
            best_signal = signal
            best_indices = indices

    auto_selected = best_attr != preferred and best_score > 0
    return best_attr, best_signal, best_indices, auto_selected


def _smooth_signal(signal: np.ndarray, window: int = 5) -> np.ndarray:
    """Lissage simple par moyenne mobile."""
    if len(signal) < window:
        return signal
    kernel = np.ones(window) / window
    padded = np.pad(signal, (window // 2, window // 2), mode="edge")
    return np.convolve(padded, kernel, mode="valid")[:len(signal)]


def _adaptive_params(exercise: str, signal: np.ndarray, fps: float) -> dict[str, float]:
    """Paramètres adaptatifs selon le type d'exercice et la durée du signal.

    Les exercices lents (RDL, hip thrust, lateral raise...) ont des pics
    moins prononcés et des mouvements plus longs — on adapte le lissage,
    la prominence minimale et la distance minimale entre pics.
    """
    rom_total = float(np.max(signal) - np.min(signal))

    if exercise in SLOW_EXERCISES:
        # Light smoothing — heavy smoothing crushes real oscillations
        smooth_window = min(5, max(3, int(fps * 0.1)))
        # Low prominence — slow exercises have smaller amplitude oscillations
        min_prominence = max(rom_total * 0.06, 2.0)
        # Short distance — allow detecting reps as short as 0.4s
        min_distance = max(4, int(fps * 0.4))
    else:
        smooth_window = min(5, max(3, int(fps * 0.1)))
        min_prominence = max(rom_total * 0.08, 3.0)
        min_distance = max(3, int(fps * 0.25))

    # Si peu de signal (vidéo courte), réduire la distance
    if len(signal) < 40:
        min_distance = max(3, min_distance // 2)

    return {
        "smooth_window": smooth_window,
        "min_prominence": min_prominence,
        "min_distance": min_distance,
    }


def _find_peaks_valleys(
    signal: np.ndarray,
    min_prominence: float = 10.0,
    min_distance: int = 5,
):
    """Trouve les pics et vallées du signal."""
    try:
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(signal, prominence=min_prominence, distance=min_distance)
        valleys, _ = find_peaks(-signal, prominence=min_prominence, distance=min_distance)
        return peaks, valleys
    except ImportError:
        logger.warning("scipy non disponible, détection manuelle des pics.")
        return _manual_find_peaks(signal, min_prominence, min_distance)


def _manual_find_peaks(
    signal: np.ndarray,
    min_prominence: float,
    min_distance: int = 5,
):
    """Détection manuelle des pics/vallées sans scipy."""
    peaks = []
    valleys = []
    for i in range(1, len(signal) - 1):
        if signal[i] > signal[i - 1] and signal[i] > signal[i + 1]:
            # Vérifier distance avec le dernier pic
            if not peaks or (i - peaks[-1]) >= min_distance:
                peaks.append(i)
        elif signal[i] < signal[i - 1] and signal[i] < signal[i + 1]:
            if not valleys or (i - valleys[-1]) >= min_distance:
                valleys.append(i)
    return np.array(peaks), np.array(valleys)


def _detect_end_of_set(
    smoothed: np.ndarray,
    frame_indices: np.ndarray,
    fps: float,
    last_valley_idx: int,
) -> bool:
    """Détecte si la série est terminée (angle stabilisé après la dernière rep).

    Si le signal reste stable (faible variance) pendant > 1 seconde après la
    dernière vallée, le set est considéré comme terminé.
    """
    if last_valley_idx >= len(smoothed) - 1:
        return False

    tail = smoothed[last_valley_idx:]
    tail_frames = len(tail)
    frames_for_one_sec = max(1, int(fps))

    if tail_frames < frames_for_one_sec:
        return False

    # Vérifier la stabilité : variance faible sur la dernière seconde
    stable_segment = tail[-frames_for_one_sec:]
    variance = float(np.var(stable_segment))
    rom_range = float(np.max(stable_segment) - np.min(stable_segment))

    # Si l'angle varie de moins de 5 degrés sur 1 seconde, le set est fini
    if rom_range < 5.0 and variance < 10.0:
        logger.info(
            "End-of-set detecte: signal stable (range=%.1f deg, var=%.1f) "
            "sur les %d dernieres frames.",
            rom_range, variance, frames_for_one_sec,
        )
        return True

    return False


def _compute_fatigue(reps: list[Rep]) -> None:
    """Calcule les métriques de fatigue pour chaque rep (in-place).

    La fatigue se manifeste par :
    - Diminution du ROM (amplitude réduite)
    - Diminution de la vitesse concentrique (perte de puissance)
    - Augmentation du tempo concentrique (plus lent à remonter)
    """
    if len(reps) < 2:
        return

    first_rom = reps[0].rom if reps[0].rom > 0 else 1.0
    first_vel = reps[0].peak_velocity if reps[0].peak_velocity > 0 else 1.0
    first_conc = reps[0].concentric_duration_ms if reps[0].concentric_duration_ms > 0 else 1.0

    for rep in reps:
        # Ratios vs première rep
        rep.rom_vs_first = rep.rom / first_rom if first_rom > 0 else 1.0
        rep.velocity_vs_first = rep.peak_velocity / first_vel if first_vel > 0 else 1.0

        # Index de fatigue composite (0 = frais, 1 = épuisé)
        rom_loss = max(0.0, 1.0 - rep.rom_vs_first)
        vel_loss = max(0.0, 1.0 - rep.velocity_vs_first)
        conc_increase = max(0.0, (rep.concentric_duration_ms / first_conc) - 1.0) if first_conc > 0 else 0.0
        conc_increase = min(conc_increase, 1.0)  # Cap à 1.0

        # Pondération : ROM 40%, vitesse 35%, ralentissement concentrique 25%
        rep.fatigue_index = min(1.0, rom_loss * 0.40 + vel_loss * 0.35 + conc_increase * 0.25)


def _estimate_transition_rests(
    reps: list[Rep],
    smoothed_signal: np.ndarray,
    frame_indices: np.ndarray,
    fps: float,
) -> list[float]:
    """Estimate rest between reps from low-velocity plateaus around transitions."""
    if len(reps) < 2 or fps <= 0 or len(smoothed_signal) < 6 or len(frame_indices) < 6:
        return []

    velocities = np.abs(np.diff(smoothed_signal))
    if len(velocities) == 0:
        return []

    vel_threshold = float(np.percentile(velocities, 20))
    vel_threshold = max(vel_threshold, 1e-4)
    max_span = max(1, int(fps * 1.2))

    def _pause_seconds(anchor_frame: int) -> float:
        anchor = int(np.argmin(np.abs(frame_indices - int(anchor_frame))))
        left = anchor
        right = anchor

        while left > 0 and (anchor - left) < max_span:
            v = float(velocities[left - 1]) if left - 1 < len(velocities) else vel_threshold + 1.0
            if v > (vel_threshold * 1.25):
                break
            left -= 1

        while right < len(frame_indices) - 1 and (right - anchor) < max_span:
            v = float(velocities[right]) if right < len(velocities) else vel_threshold + 1.0
            if v > (vel_threshold * 1.25):
                break
            right += 1

        plateau_frames = max(0, int(frame_indices[right]) - int(frame_indices[left]))
        return plateau_frames / fps

    rests_s: list[float] = []
    for i in range(len(reps) - 1):
        transition_frame = int(reps[i].end_frame)
        next_start = int(reps[i + 1].start_frame)
        gap_frames = max(0, next_start - transition_frame)
        end_pause_s = _pause_seconds(transition_frame)
        start_pause_s = _pause_seconds(next_start)
        turnaround_pause_s = _pause_seconds(int(getattr(reps[i], "bottom_frame", transition_frame) or transition_frame))
        next_turnaround_pause_s = _pause_seconds(
            int(getattr(reps[i + 1], "bottom_frame", next_start) or next_start)
        )

        rests_s.append(
            max(
                gap_frames / fps,
                end_pause_s,
                start_pause_s,
                turnaround_pause_s,
                next_turnaround_pause_s * 0.8,
            )
        )

    return rests_s


def _map_rep_phases(
    *,
    sf: int,
    bf: int,
    ef: int,
    phase_direction: str,
) -> tuple[tuple[int, int], tuple[int, int], float, float]:
    """Map raw cycle phases to eccentric/concentric based on exercise phase direction."""
    phase_a = (sf, bf)
    phase_b = (bf, ef)
    phase_a_ms = max(0.0, float(bf - sf))
    phase_b_ms = max(0.0, float(ef - bf))

    if phase_direction == "min_y":
        # Peak contraction/lockout in the "high" position:
        # phase A (start->peak) is concentric, phase B (peak->return) is eccentric.
        ecc_frames = phase_b
        conc_frames = phase_a
        ecc_ms = phase_b_ms
        conc_ms = phase_a_ms
    else:
        # Peak in the "low" position (default): phase A is eccentric, phase B concentric.
        ecc_frames = phase_a
        conc_frames = phase_b
        ecc_ms = phase_a_ms
        conc_ms = phase_b_ms

    return ecc_frames, conc_frames, ecc_ms, conc_ms


def _compute_intensity_metrics(
    reps: list[Rep],
    fps: float,
    transition_rests_s: list[float] | None = None,
) -> dict[str, float | int | str]:
    """Estimate set intensity from rest between consecutive reps.

    Higher intensity = shorter and more regular inter-rep rests.
    """
    base = {
        "avg_inter_rep_rest_s": 0.0,
        "median_inter_rep_rest_s": 0.0,
        "max_inter_rep_rest_s": 0.0,
        "rest_consistency": 0.0,
        "set_duration_s": 0.0,
        "reps_per_min": 0.0,
        "intensity_score": 0,
        "intensity_label": "indeterminee",
    }
    if not reps or len(reps) < 2 or fps <= 0:
        return base

    rests_s: list[float] = []
    if transition_rests_s:
        rests_s = [max(0.0, float(r)) for r in transition_rests_s if np.isfinite(r)]

    if len(rests_s) < (len(reps) - 1):
        rests_s = []
        for i in range(len(reps) - 1):
            gap_frames = max(0, reps[i + 1].start_frame - reps[i].end_frame)
            rests_s.append(gap_frames / fps)

    if not rests_s:
        return base

    rests_arr = np.array(rests_s, dtype=float)
    avg_rest = float(np.mean(rests_arr))
    med_rest = float(np.median(rests_arr))
    max_rest = float(np.max(rests_arr))
    rest_std = float(np.std(rests_arr))
    rest_cv = (rest_std / avg_rest) if avg_rest > 1e-6 else 1.0
    rest_consistency = max(0.0, min(1.0, 1.0 - rest_cv))

    set_duration_s = max(0.0, (reps[-1].end_frame - reps[0].start_frame) / fps)
    reps_per_min = (len(reps) * 60.0 / set_duration_s) if set_duration_s > 0 else 0.0

    # Base score from average intra-set rest.
    if avg_rest <= 0.35:
        score = 96
    elif avg_rest <= 0.75:
        score = 90
    elif avg_rest <= 1.25:
        score = 80
    elif avg_rest <= 1.8:
        score = 70
    elif avg_rest <= 2.8:
        score = 58
    elif avg_rest <= 4.2:
        score = 45
    else:
        score = 30

    # Consistency adjustment (irregular pacing reduces usable intensity).
    if rest_cv > 0.7:
        score -= 12
    elif rest_cv > 0.5:
        score -= 8
    elif rest_cv > 0.35:
        score -= 4

    # Density adjustment from cadence.
    if reps_per_min >= 20:
        score += 4
    elif reps_per_min >= 14:
        score += 2
    elif reps_per_min < 8:
        score -= 6

    score = int(max(0, min(100, score)))

    if score >= 85:
        label = "tres elevee"
    elif score >= 70:
        label = "elevee"
    elif score >= 55:
        label = "moderee"
    elif score >= 40:
        label = "faible"
    else:
        label = "tres faible"

    return {
        "avg_inter_rep_rest_s": avg_rest,
        "median_inter_rep_rest_s": med_rest,
        "max_inter_rep_rest_s": max_rest,
        "rest_consistency": rest_consistency,
        "set_duration_s": set_duration_s,
        "reps_per_min": reps_per_min,
        "intensity_score": score,
        "intensity_label": label,
    }


def _estimate_intensity_from_count(
    rep_count: int,
    set_duration_s: float,
) -> dict[str, float | int | str]:
    """Fallback intensity estimate when per-rep segmentation is unavailable."""
    base = {
        "avg_inter_rep_rest_s": 0.0,
        "median_inter_rep_rest_s": 0.0,
        "max_inter_rep_rest_s": 0.0,
        "rest_consistency": 0.0,
        "set_duration_s": max(0.0, set_duration_s),
        "reps_per_min": 0.0,
        "intensity_score": 0,
        "intensity_label": "indeterminee",
    }
    if rep_count < 2 or set_duration_s <= 0:
        return base

    reps_per_min = (rep_count * 60.0 / set_duration_s) if set_duration_s > 0 else 0.0
    avg_cycle_s = set_duration_s / max(1, rep_count)
    # Heuristic: assume ~20% of each cycle is micro-pause between reps.
    avg_rest = max(0.0, avg_cycle_s * 0.20)

    if avg_rest <= 0.6:
        score = 84
    elif avg_rest <= 1.0:
        score = 76
    elif avg_rest <= 1.5:
        score = 66
    elif avg_rest <= 2.5:
        score = 54
    else:
        score = 42

    if reps_per_min >= 20:
        score += 4
    elif reps_per_min >= 14:
        score += 2
    elif reps_per_min < 8:
        score -= 6

    score = int(max(0, min(100, score)))
    if score >= 85:
        label = "tres elevee"
    elif score >= 70:
        label = "elevee"
    elif score >= 55:
        label = "moderee"
    elif score >= 40:
        label = "faible"
    else:
        label = "tres faible"

    return {
        "avg_inter_rep_rest_s": avg_rest,
        "median_inter_rep_rest_s": avg_rest,
        "max_inter_rep_rest_s": avg_rest * 1.4,
        "rest_consistency": 0.45,
        "set_duration_s": set_duration_s,
        "reps_per_min": reps_per_min,
        "intensity_score": score,
        "intensity_label": label,
    }


def _detect_cheat(
    reps: list[Rep],
    angle_frames: list[FrameAngles],
    frame_indices: np.ndarray,
    exercise: str,
) -> None:
    """Détecte la triche/momentum sur chaque rep (in-place).

    Analyse le mouvement parasite du tronc pendant la phase concentrique :
    - Curl : swing du torse pour aider à monter la barre
    - Row : extension excessive du tronc
    - Squat/deadlift : inclinaison excessive du buste
    """
    cheat_attr = CHEAT_ANGLE_MAP.get(exercise)
    if not cheat_attr:
        return

    threshold = CHEAT_THRESHOLD.get(exercise, 15.0)

    # Extraire le signal du tronc
    trunk_signal, trunk_indices = _get_signal(angle_frames, cheat_attr)
    if len(trunk_signal) < 5:
        return

    for rep in reps:
        # Trouver les frames du tronc correspondant à la phase concentrique
        conc_start, conc_end = rep.concentric_frames
        mask = (trunk_indices >= conc_start) & (trunk_indices <= conc_end)
        conc_trunk = trunk_signal[mask]

        if len(conc_trunk) < 2:
            continue

        # Variation du tronc pendant la concentrique
        trunk_range = float(np.max(conc_trunk) - np.min(conc_trunk))
        # Vitesse max de changement du tronc (° par frame)
        trunk_velocity = float(np.max(np.abs(np.diff(conc_trunk)))) if len(conc_trunk) > 1 else 0.0

        # Score de triche : combien le tronc bouge vs le seuil
        cheat_score = min(1.0, trunk_range / threshold) if threshold > 0 else 0.0

        # Bonus si la vitesse du tronc est élevée (mouvement explosif = momentum)
        if trunk_velocity > threshold * 0.3:
            cheat_score = min(1.0, cheat_score + 0.2)

        rep.cheat_score = cheat_score
        if cheat_score >= 0.5:
            rep.cheat_detected = True
            if cheat_score >= 0.8:
                rep.cheat_details = "Mouvement du tronc excessif ({:.0f} deg) -- momentum flagrant".format(trunk_range)
            elif cheat_score >= 0.6:
                rep.cheat_details = "Compensation du tronc ({:.0f} deg) -- charge probablement trop lourde".format(trunk_range)
            else:
                rep.cheat_details = "Legere compensation du tronc ({:.0f} deg)".format(trunk_range)


# ═══════════════════════════════════════════════════════════════════════════
# MULTI-JOINT Y SIGNAL — Robust rep counting via landmark positions
# ═══════════════════════════════════════════════════════════════════════════

# MediaPipe landmark indices for key joints
_JOINT_INDICES = {
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
}


def _extract_joint_y_signals(
    raw_frames: list,
    exercise: str = "",
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Extract Y position time-series for each key joint from raw landmarks.

    Returns dict of joint_name -> (y_values, frame_indices).
    Y in image coordinates (higher Y = lower position in image).
    """
    signals = {}
    selected_joints = _joint_names_for_exercise(exercise)
    vis_stats = {}
    for joint_name, lm_idx in _JOINT_INDICES.items():
        if joint_name not in selected_joints:
            continue
        values = []
        indices = []
        vis_values = []
        for frame in raw_frames:
            if lm_idx < len(frame.landmarks):
                lm = frame.landmarks[lm_idx]
                vis = lm.get("visibility", 0.0)
                vis_values.append(vis)
                # Very low threshold — even low-visibility landmarks give usable Y
                if vis > 0.1:
                    values.append(lm["y"])
                    indices.append(frame.frame_index)
        avg_vis = float(np.mean(vis_values)) if vis_values else 0.0
        vis_stats[joint_name] = (len(values), avg_vis)
        if len(values) >= 10:
            signals[joint_name] = (np.array(values), np.array(indices))

    logger.info(
        "Joint Y extraction: %d/%d joints usable (exercise=%s). Stats: %s",
        len(signals), len(selected_joints), exercise,
        {k: "{}pts/{:.2f}vis".format(v[0], v[1]) for k, v in vis_stats.items()},
    )
    return signals


def _build_combined_signal(
    joint_signals: dict[str, tuple[np.ndarray, np.ndarray]],
    fps: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a variance-weighted combined signal from multi-joint Y positions.

    1. For each joint, compute variance of its Y signal
    2. Select top joints by variance (= joints that move the most)
    3. Normalize each to [0,1]
    4. Combine as variance-weighted sum → single 1D signal

    This is robust because:
    - Averaging over multiple joints smooths out individual tracking errors
    - Variance weighting focuses on joints that actually participate in the movement
    - Y position is the most reliable coordinate from MediaPipe (less affected by depth errors)
    """
    if not joint_signals:
        return np.array([]), np.array([])

    # Find common frame indices (intersection of all joints)
    all_indices_sets = [set(idx.tolist()) for _, idx in joint_signals.values()]
    common_indices = sorted(set.intersection(*all_indices_sets)) if all_indices_sets else []

    if len(common_indices) < 10:
        # Fallback: use the joint with most frames
        best_joint = max(joint_signals.keys(), key=lambda k: len(joint_signals[k][0]))
        return joint_signals[best_joint]

    common_set = set(common_indices)

    # Align all signals to common indices
    aligned = {}
    for name, (vals, idxs) in joint_signals.items():
        mask = np.array([i in common_set for i in idxs.tolist()])
        if np.sum(mask) == len(common_indices):
            aligned[name] = vals[mask]
        else:
            # Rebuild by lookup
            idx_to_val = dict(zip(idxs.tolist(), vals.tolist()))
            aligned_vals = [idx_to_val[ci] for ci in common_indices if ci in idx_to_val]
            if len(aligned_vals) == len(common_indices):
                aligned[name] = np.array(aligned_vals)

    if not aligned:
        best_joint = max(joint_signals.keys(), key=lambda k: len(joint_signals[k][0]))
        return joint_signals[best_joint]

    # Compute variance for each joint signal
    variances = {}
    for name, vals in aligned.items():
        variances[name] = float(np.var(vals))

    total_var = sum(variances.values())
    if total_var < 1e-10:
        # No movement detected
        best_joint = max(joint_signals.keys(), key=lambda k: len(joint_signals[k][0]))
        return joint_signals[best_joint]

    # Select top joints by variance (at least 5% of total variance)
    threshold = total_var * 0.05
    selected = {n: v for n, v in aligned.items() if variances[n] >= threshold}

    if not selected:
        selected = aligned  # use all if none pass threshold

    logger.info(
        "Multi-joint signal: %d/%d joints selected by variance: %s",
        len(selected), len(aligned),
        [(n, round(variances.get(n, 0), 6)) for n in selected],
    )

    # Normalize each signal to [0, 1]
    normalized = {}
    for name, vals in selected.items():
        vmin, vmax = float(np.min(vals)), float(np.max(vals))
        if vmax - vmin > 1e-10:
            normalized[name] = (vals - vmin) / (vmax - vmin)
        else:
            normalized[name] = np.zeros_like(vals)

    # Variance-weighted combination
    weights = {n: variances[n] for n in normalized}
    w_total = sum(weights.values())
    combined = np.zeros(len(common_indices))
    for name, norm_vals in normalized.items():
        w = weights[name] / w_total
        combined += w * norm_vals

    return combined, np.array(common_indices)


def _trim_active_region(signal: np.ndarray, fps: float) -> np.ndarray:
    """Trim the signal to only the active (repetitive) region.

    Removes the setup phase at the start and the walkaway at the end
    by finding the region with the highest variance (= where reps happen).
    Uses a sliding window of ~1 second.
    """
    start, end = _active_region_bounds(signal, fps)
    trimmed = signal[start:end]
    logger.info(
        "Trimmed signal: %d -> %d frames (removed %d start, %d end)",
        len(signal), len(trimmed), start, len(signal) - end,
    )
    return trimmed


def _active_region_bounds(signal: np.ndarray, fps: float) -> tuple[int, int]:
    """Return [start, end) bounds of the most active movement window."""
    n = len(signal)
    if n <= 2:
        return 0, n

    window = max(5, int(fps * 1.0))
    if n <= window:
        return 0, n

    variances = []
    for i in range(n - window + 1):
        variances.append(float(np.var(signal[i:i + window])))
    variances_arr = np.array(variances, dtype=float)

    if len(variances_arr) == 0:
        return 0, n
    vmax = float(np.max(variances_arr))
    if vmax < 1e-10:
        return 0, n

    threshold = vmax * 0.20
    active_indices = np.where(variances_arr > threshold)[0]
    if len(active_indices) < 2:
        return 0, n

    pad = max(1, int(window * 0.20))
    start = max(0, int(active_indices[0]) - pad)
    end = min(n, int(active_indices[-1]) + window + pad)
    if (end - start) < 10:
        return 0, n
    return start, end


def _count_by_autocorrelation(signal: np.ndarray, fps: float) -> int:
    """Count repetitions using autocorrelation to find the dominant period.

    Autocorrelation finds periodicity in a signal by correlating it with
    time-shifted versions of itself. The first major peak after lag 0
    indicates the period (duration of one rep).
    """
    if len(signal) < 15:
        return 0

    # Trim to active region (remove setup/walkaway)
    sig = _trim_active_region(signal, fps)

    # Remove DC component (mean)
    sig = sig - np.mean(sig)

    # Compute autocorrelation via numpy
    n = len(sig)
    autocorr = np.correlate(sig, sig, mode='full')
    autocorr = autocorr[n - 1:]  # Keep positive lags only

    # Normalize
    if autocorr[0] > 0:
        autocorr = autocorr / autocorr[0]
    else:
        return 0

    # Find the first significant peak after lag 0
    # Min lag: at least 0.3 seconds per rep (very fast reps)
    # Max lag: at most 5 seconds per rep (slow controlled reps)
    min_lag = max(3, int(fps * 0.3))
    max_lag = min(len(autocorr) - 1, int(fps * 5.0))

    if min_lag >= max_lag:
        return 0

    search_region = autocorr[min_lag:max_lag + 1]
    if len(search_region) < 3:
        return 0

    # Find peaks in autocorrelation
    try:
        from scipy.signal import find_peaks as sp_find_peaks
        peaks, properties = sp_find_peaks(search_region, prominence=0.03, distance=max(2, int(fps * 0.2)))
    except ImportError:
        peaks = []
        for i in range(1, len(search_region) - 1):
            if search_region[i] > search_region[i-1] and search_region[i] > search_region[i+1]:
                if search_region[i] > 0.03:
                    peaks.append(i)

    if len(peaks) == 0:
        return 0

    # The first peak = dominant period
    period_frames = peaks[0] + min_lag

    # Validate: the autocorrelation at this peak should be reasonably high
    peak_value = autocorr[period_frames]
    if peak_value < 0.05:
        logger.info("Autocorrelation peak too weak (%.3f), unreliable.", peak_value)
        return 0

    # Count = total active duration / period
    rep_count = round(n / period_frames)

    logger.info(
        "Autocorrelation: period=%.1f frames (%.2fs), peak_value=%.3f, "
        "active_signal=%d frames, estimated_reps=%d",
        period_frames, period_frames / fps, peak_value, n, rep_count,
    )
    return max(1, rep_count)


def _count_by_extrema_cycles(signal: np.ndarray, fps: float = 30.0) -> int:
    """Count reps by turning points (peaks/valleys) on the active region."""
    if len(signal) < 8:
        return 0

    trimmed = _trim_active_region(signal, fps)
    if len(trimmed) < 8:
        return 0

    smoothed = _smooth_signal(trimmed, window=max(3, int(fps * 0.12)))
    p95 = float(np.percentile(smoothed, 95))
    p05 = float(np.percentile(smoothed, 5))
    rom = max(0.0, p95 - p05)
    if rom <= 1e-3:
        return 0

    prominence = max(rom * 0.10, 0.01)
    min_distance = max(3, int(fps * 0.25))
    peaks, valleys = _find_peaks_valleys(
        smoothed,
        min_prominence=prominence,
        min_distance=min_distance,
    )

    if len(peaks) == 0 and len(valleys) == 0:
        return 0

    turning_points = np.sort(np.concatenate([peaks, valleys]))
    if len(turning_points) < 3:
        count = max(0, max(len(peaks), len(valleys)) - 1)
    else:
        count = max(0, (len(turning_points) - 1) // 2)
        if len(valleys) >= 2:
            count = max(count, len(valleys) - 1)
        if len(peaks) >= 2:
            count = max(count, len(peaks) - 1)

    logger.info(
        "Extrema-cycle: peaks=%d valleys=%d turning=%d -> %d reps (trimmed %d->%d)",
        len(peaks), len(valleys), len(turning_points), count, len(signal), len(trimmed),
    )
    return count


def _best_robust_count(autocorr: int, zerocross: int, extrema: int = 0) -> int:
    """Pick robust rep count from multiple estimators.

    Uses robust aggregation biased against undercount outliers.
    """
    values = [v for v in (autocorr, zerocross, extrema) if v > 0]
    if not values:
        return 0
    if len(values) == 1:
        return values[0]

    values.sort()
    if len(values) == 2:
        if abs(values[1] - values[0]) <= 2:
            return round((values[0] + values[1]) / 2)
        # Large disagreement: avoid low undercount outliers.
        return values[1]

    # Three methods: if one low outlier, use the top-two mean.
    if values[2] - values[0] >= 4 and values[1] - values[0] >= 2:
        return round((values[1] + values[2]) / 2)

    # Otherwise median is stable.
    return values[1]


def _is_robust_count_reliable(autocorr: int, zerocross: int, extrema: int = 0) -> bool:
    values = sorted(v for v in (autocorr, zerocross, extrema) if v > 0)
    if len(values) < 2:
        return False
    if values[-1] - values[0] <= 2:
        return True
    if len(values) == 3 and abs(values[-1] - values[-2]) <= 2:
        return True
    return False


def _should_apply_robust_down_override(
    peak_count: int,
    robust_count: int,
    robust_reliable: bool,
) -> bool:
    """True when peak segmentation likely overcounted micro-oscillations."""
    if robust_count <= 0 or not robust_reliable:
        return False
    if peak_count < robust_count:
        return False
    if peak_count >= int(robust_count * 1.35) and (peak_count - robust_count) >= 4:
        return True
    return False


def _retune_extrema_for_target(
    smoothed: np.ndarray,
    fps: float,
    target_reps: int,
    base_prominence: float,
    base_min_distance: int,
) -> tuple[np.ndarray, np.ndarray, bool]:
    """Retry extrema extraction with target-driven params to recover missed reps."""
    if target_reps < 2 or len(smoothed) < 12:
        return np.array([]), np.array([]), False

    approx_period = max(3, int(len(smoothed) / max(1, target_reps)))
    distance_candidates = sorted(
        {
            max(3, int(approx_period * 0.65)),
            max(3, int(approx_period * 0.55)),
            max(3, int(approx_period * 0.45)),
            max(3, int(base_min_distance)),
            max(3, int(base_min_distance * 0.7)),
            max(3, int(base_min_distance * 0.5)),
        },
        reverse=True,
    )
    prominence_candidates = [
        max(0.01, base_prominence * mul)
        for mul in (0.90, 0.75, 0.60, 0.45, 0.35, 0.25, 0.18)
    ]

    best_peaks = np.array([])
    best_valleys = np.array([])
    best_error = 1_000_000

    for prom in prominence_candidates:
        for dist in distance_candidates:
            peaks, valleys = _find_peaks_valleys(
                smoothed,
                min_prominence=prom,
                min_distance=dist,
            )
            if len(valleys) < 2 and len(peaks) >= 2:
                valleys, peaks = peaks, valleys
            if len(valleys) < 2:
                continue
            candidate_reps = max(0, len(valleys) - 1)
            err = abs(candidate_reps - target_reps)
            if err < best_error:
                best_error = err
                best_peaks = peaks
                best_valleys = valleys
            if err <= 1:
                logger.info(
                    "Rescue extrema hit target: reps=%d target=%d prom=%.3f dist=%d",
                    candidate_reps, target_reps, prom, dist,
                )
                return peaks, valleys, True

    if len(best_valleys) >= 2:
        candidate_reps = max(0, len(best_valleys) - 1)
        if best_error <= max(2, int(target_reps * 0.30)):
            logger.info(
                "Rescue extrema close target: reps=%d target=%d err=%d",
                candidate_reps, target_reps, best_error,
            )
            return best_peaks, best_valleys, True

    return np.array([]), np.array([]), False


def _count_by_zero_crossing(signal: np.ndarray, fps: float = 30.0) -> int:
    """Count reps by zero-crossing: each full cycle (2 crossings) = 1 rep.

    Robust fallback: simply counts how many times the signal crosses
    its mean value. Less affected by amplitude variations than peak detection.
    """
    if len(signal) < 5:
        return 0

    # Trim to active region first
    trimmed = _trim_active_region(signal, fps)

    # Smooth slightly to avoid noise crossings
    smoothed = _smooth_signal(trimmed, window=max(3, int(fps * 0.1)))

    mean_val = np.mean(smoothed)
    centered = smoothed - mean_val

    # Count sign changes
    crossings = 0
    for i in range(1, len(centered)):
        if centered[i-1] * centered[i] < 0:
            crossings += 1

    # Each complete rep = 2 crossings (down + up or up + down)
    rep_count = crossings // 2

    logger.info("Zero-crossing: %d crossings → %d reps (trimmed %d→%d frames)",
                crossings, rep_count, len(signal), len(trimmed))
    return max(0, rep_count)


def segment_reps(
    angles: AngleResult,
    exercise: str,
    fps: float = 30.0,
    raw_frames: list | None = None,
) -> RepSegmentation:
    """Segmente les répétitions avec une architecture multi-méthode.

    Architecture de comptage (cascade) :
    1. Multi-joint Y signal + autocorrélation (le plus robuste)
    2. Zero-crossing sur le signal combiné (fallback)
    3. Peak detection sur angle primaire (fallback classique)

    La méthode 1 (autocorrélation) donne le nombre de reps le plus fiable.
    Si les méthodes divergent, on prend le maximum cohérent.

    La segmentation individuelle (tempo, fatigue, triche) utilise le signal
    angulaire classique car elle a besoin des positions exactes des pics/vallées.

    Args:
        angles: Résultat du calcul d'angles.
        exercise: Nom de l'exercice (valeur de l'enum Exercise).
        fps: FPS de la vidéo.
        raw_frames: FrameLandmarks brutes de l'extraction (pour multi-joint Y).

    Returns:
        RepSegmentation avec les reps détectées, fatigue et triche.
    """
    result = RepSegmentation()

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 1 : COMPTAGE ROBUSTE (multi-joint + autocorrélation + zero-crossing)
    # ══════════════════════════════════════════════════════════════════════

    autocorr_count = 0
    zerocross_count = 0
    extrema_count = 0
    combined_signal = None
    combined_indices = None
    combined_duration_s = 0.0
    params = {}
    signal = None
    smoothed = np.array([])
    frame_indices = np.array([])
    peaks = np.array([])
    valleys = np.array([])

    if raw_frames and len(raw_frames) >= 10:
        joint_signals = _extract_joint_y_signals(raw_frames, exercise=exercise)
        if joint_signals:
            combined_signal, combined_indices = _build_combined_signal(joint_signals, fps)

            if len(combined_signal) >= 15:
                if len(combined_indices) >= 2 and fps > 0:
                    combined_duration_s = max(
                        0.0,
                        float(combined_indices[-1] - combined_indices[0]) / fps,
                    )
                # Smooth the combined signal
                smooth_win = min(7, max(3, int(fps * 0.15)))
                smoothed_combined = _smooth_signal(combined_signal, window=smooth_win)

                # Method 1: Autocorrelation
                autocorr_count = _count_by_autocorrelation(smoothed_combined, fps)

                # Method 2: Zero-crossing
                zerocross_count = _count_by_zero_crossing(smoothed_combined, fps)

                # Method 3: turning points (helps when tempo varies)
                extrema_count = _count_by_extrema_cycles(smoothed_combined, fps)

                logger.info(
                    "Robust counting: autocorr=%d, zerocross=%d, extrema=%d",
                    autocorr_count, zerocross_count, extrema_count,
                )

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 2 : SEGMENTATION PAR PEAK DETECTION (pour tempo/fatigue/triche)
    # ══════════════════════════════════════════════════════════════════════

    # Déterminer le meilleur signal articulaire pour segmenter les reps.
    preferred_attr = PRIMARY_ANGLE_MAP.get(exercise, "left_knee_flexion")
    if exercise not in PRIMARY_ANGLE_MAP:
        logger.warning("Exercice '%s' non mappe, fallback %s.", exercise, preferred_attr)

    attr, signal, frame_indices, auto_signal = _select_segmentation_signal(
        angles.frames,
        exercise,
        fps,
    )
    result.segmentation_signal = attr
    result.auto_signal_selected = auto_signal
    if auto_signal:
        logger.warning(
            "Auto signal fallback: preferred=%s -> selected=%s (exercise=%s)",
            preferred_attr, attr, exercise,
        )

    # Trim to active movement region for reliable start/end and rep boundaries.
    active_start, active_end = _active_region_bounds(signal, fps)
    if active_end - active_start >= 10:
        if active_start > 0 or active_end < len(signal):
            logger.info(
                "Active window (angle signal): %d..%d on %d samples",
                active_start,
                active_end,
                len(signal),
            )
        signal = signal[active_start:active_end]
        frame_indices = frame_indices[active_start:active_end]

    if len(frame_indices) >= 2 and fps > 0:
        result.movement_start_frame = int(frame_indices[0])
        result.movement_end_frame = int(frame_indices[-1])
        result.movement_duration_s = max(
            0.0,
            float(result.movement_end_frame - result.movement_start_frame) / fps,
        )

    if len(signal) < 10:
        logger.info("Primary angle signal too short (%d pts).", len(signal))
        movement_indices = frame_indices
        if (
            (movement_indices is None or len(movement_indices) < 2)
            and combined_indices is not None
            and len(combined_indices) >= 2
        ):
            movement_indices = combined_indices
        if movement_indices is not None and len(movement_indices) >= 2 and fps > 0:
            result.movement_start_frame = int(movement_indices[0])
            result.movement_end_frame = int(movement_indices[-1])
            result.movement_duration_s = max(
                0.0,
                float(result.movement_end_frame - result.movement_start_frame) / fps,
            )
        # If we have a robust count but no angle signal, return count-only result
        robust_count = _best_robust_count(autocorr_count, zerocross_count, extrema_count)
        result.autocorr_count = autocorr_count
        result.zerocross_count = zerocross_count
        result.extrema_count = extrema_count
        result.robust_count = robust_count
        result.robust_reliable = _is_robust_count_reliable(autocorr_count, zerocross_count, extrema_count)
        if robust_count > 0:
            result.total_reps = robust_count
            result.complete_reps = robust_count
            result.peak_count = 0
            result.count_method = "robust_only_no_angle"
            duration_hint_s = combined_duration_s
            if duration_hint_s <= 0 and len(frame_indices) >= 2 and fps > 0:
                duration_hint_s = max(0.0, float(frame_indices[-1] - frame_indices[0]) / fps)
            intensity = _estimate_intensity_from_count(robust_count, duration_hint_s)
            result.avg_inter_rep_rest_s = float(intensity["avg_inter_rep_rest_s"])
            result.median_inter_rep_rest_s = float(intensity["median_inter_rep_rest_s"])
            result.max_inter_rep_rest_s = float(intensity["max_inter_rep_rest_s"])
            result.rest_consistency = float(intensity["rest_consistency"])
            result.set_duration_s = float(intensity["set_duration_s"])
            result.reps_per_min = float(intensity["reps_per_min"])
            result.intensity_score = int(intensity["intensity_score"])
            result.intensity_label = str(intensity["intensity_label"])
            result.intensity_confidence = "limitee"
            result.rest_measure_method = "estimate_from_count"
            logger.info("Using robust count only (no angle data): %d reps", robust_count)
            return result
        return result

    # Paramètres adaptatifs selon l'exercice
    params = _adaptive_params(exercise, signal, fps)

    # Lisser le signal
    smoothed = _smooth_signal(signal, window=int(params["smooth_window"]))

    robust_count_hint = _best_robust_count(autocorr_count, zerocross_count, extrema_count)
    robust_hint_reliable = _is_robust_count_reliable(autocorr_count, zerocross_count, extrema_count)

    # Détecter pics et vallées — try multiple prominence levels
    peaks, valleys = _find_peaks_valleys(
        smoothed,
        min_prominence=params["min_prominence"],
        min_distance=int(params["min_distance"]),
    )

    if len(valleys) < 2:
        if len(peaks) >= 2:
            valleys, peaks = peaks, valleys
        else:
            # Reduce prominence aggressively
            reduced_prom = params["min_prominence"] * 0.3
            peaks, valleys = _find_peaks_valleys(
                smoothed,
                min_prominence=reduced_prom,
                min_distance=max(3, int(params["min_distance"] * 0.4)),
            )
            if len(valleys) < 2 and len(peaks) >= 2:
                valleys, peaks = peaks, valleys
            elif len(valleys) < 2:
                # Peak detection failed — use robust count if available
                robust_count = _best_robust_count(autocorr_count, zerocross_count, extrema_count)
                result.autocorr_count = autocorr_count
                result.zerocross_count = zerocross_count
                result.extrema_count = extrema_count
                result.robust_count = robust_count
                result.robust_reliable = _is_robust_count_reliable(autocorr_count, zerocross_count, extrema_count)
                if robust_count > 0:
                    result.total_reps = robust_count
                    result.complete_reps = robust_count
                    result.peak_count = 0
                    result.count_method = "robust_only_peak_failed"
                    duration_hint_s = combined_duration_s
                    if duration_hint_s <= 0 and len(frame_indices) >= 2 and fps > 0:
                        duration_hint_s = max(0.0, float(frame_indices[-1] - frame_indices[0]) / fps)
                    intensity = _estimate_intensity_from_count(robust_count, duration_hint_s)
                    result.avg_inter_rep_rest_s = float(intensity["avg_inter_rep_rest_s"])
                    result.median_inter_rep_rest_s = float(intensity["median_inter_rep_rest_s"])
                    result.max_inter_rep_rest_s = float(intensity["max_inter_rep_rest_s"])
                    result.rest_consistency = float(intensity["rest_consistency"])
                    result.set_duration_s = float(intensity["set_duration_s"])
                    result.reps_per_min = float(intensity["reps_per_min"])
                    result.intensity_score = int(intensity["intensity_score"])
                    result.intensity_label = str(intensity["intensity_label"])
                    result.intensity_confidence = "limitee"
                    result.rest_measure_method = "estimate_from_count"
                    logger.info("Peak detection failed, using robust count: %d reps", robust_count)
                    return result
                logger.warning("All methods failed to detect reps.")
                return result

    # Rescue segmentation:
    # when robust periodic estimators agree on a higher count, retune extrema
    # parameters to recover missed cycles instead of accepting undercount.
    initial_cycle_count = max(0, len(valleys) - 1)
    if (
        robust_count_hint >= 3
        and robust_hint_reliable
        and initial_cycle_count < max(2, int(robust_count_hint * 0.70))
    ):
        rescue_peaks, rescue_valleys, rescued = _retune_extrema_for_target(
            smoothed=smoothed,
            fps=fps,
            target_reps=robust_count_hint,
            base_prominence=float(params["min_prominence"]),
            base_min_distance=int(params["min_distance"]),
        )
        if rescued and len(rescue_valleys) >= 2:
            logger.info(
                "Rescue segmentation override: valleys %d->%d (target=%d)",
                len(valleys),
                len(rescue_valleys),
                robust_count_hint,
            )
            peaks = rescue_peaks
            valleys = rescue_valleys

    # ROM minimum: exercice détecté + garde-fou si auto-signal différent.
    min_rom = MIN_ROM_THRESHOLD.get(exercise, _default_min_rom_for_attr(attr))
    if attr != preferred_attr:
        min_rom = min(min_rom, _default_min_rom_for_attr(attr))

    phase_direction = "max_y"
    try:
        from analysis.exercise_phases import get_phase
        phase = get_phase(exercise)
        if phase and getattr(phase, "peak_direction", "") in {"min_y", "max_y"}:
            phase_direction = str(phase.peak_direction)
    except Exception:
        pass

    # Construire les reps : valley[i] → bottom (peak entre) → valley[i+1]
    reps: list[Rep] = []

    for i in range(len(valleys) - 1):
        v_start = valleys[i]
        v_end = valleys[i + 1]

        # Trouver le pic (bottom) entre les deux vallées
        between_peaks = peaks[(peaks > v_start) & (peaks < v_end)]
        if len(between_peaks) == 0:
            segment = smoothed[v_start:v_end + 1]
            if len(peaks) > 0 and len(valleys) > 0:
                peaks_mean = float(np.mean(smoothed[peaks]))
                valleys_mean = float(np.mean(smoothed[valleys]))
            else:
                peaks_mean = 0.0
                valleys_mean = 1.0
            bottom_local = (
                int(np.argmin(segment))
                if peaks_mean < valleys_mean
                else int(np.argmax(segment))
            )
            bottom_idx = v_start + bottom_local
        else:
            bottom_idx = between_peaks[0]

        # Frames réelles
        sf = int(frame_indices[v_start])
        ef = int(frame_indices[v_end])
        bf = int(frame_indices[bottom_idx])

        # Durées: map to eccentric/concentric according to exercise phase direction.
        ecc_frames, conc_frames, ecc_ms_frames, conc_ms_frames = _map_rep_phases(
            sf=sf, bf=bf, ef=ef, phase_direction=phase_direction
        )
        ecc_ms = (ecc_ms_frames / fps * 1000.0) if fps > 0 else 0.0
        conc_ms = (conc_ms_frames / fps * 1000.0) if fps > 0 else 0.0

        # Filtrer les reps aberrantes (trop courtes ou trop longues)
        total_ms = ecc_ms + conc_ms
        if total_ms < 200:  # Rep < 200ms = bruit
            continue
        if total_ms > 15000:  # Rep > 15s = probablement deux reps fusionnées
            continue

        # ROM de cette rep
        rep_signal = smoothed[v_start:v_end + 1]
        rep_rom = float(np.max(rep_signal) - np.min(rep_signal))

        # Vérifier le ROM minimum — en-dessous, c'est une rep partielle
        is_partial = rep_rom < min_rom

        # Si le ROM est trop faible (< 50% du seuil minimum), ignorer complètement
        # Cela filtre le bruit et les micro-mouvements de repositionnement
        if rep_rom < min_rom * 0.5:
            logger.debug(
                "Rep ignoree: ROM %.1f deg < 50%% du seuil (%.1f deg).",
                rep_rom, min_rom * 0.5,
            )
            continue

        # Vitesse angulaire max en concentrique
        conc_signal = smoothed[bottom_idx:v_end + 1]
        if len(conc_signal) > 1:
            velocities = np.abs(np.diff(conc_signal)) * fps
            peak_vel = float(np.max(velocities))
        else:
            peak_vel = 0.0

        # Tempo ratio (clamped — values > 8 are measurement artifacts)
        raw_tempo = ecc_ms / conc_ms if conc_ms > 0 else 0.0
        tempo_ratio = min(raw_tempo, 8.0)

        rep = Rep(
            rep_number=len(reps) + 1,
            start_frame=sf,
            end_frame=ef,
            bottom_frame=bf,
            eccentric_frames=ecc_frames,
            concentric_frames=conc_frames,
            eccentric_duration_ms=ecc_ms,
            concentric_duration_ms=conc_ms,
            tempo_ratio=tempo_ratio,
            rom=rep_rom,
            peak_velocity=peak_vel,
            is_partial=is_partial,
        )
        reps.append(rep)

    # ── Détection fin de série ─────────────────────────────────────────
    if len(valleys) > 0:
        last_v = valleys[-1]
        result.set_complete = _detect_end_of_set(smoothed, frame_indices, fps, last_v)

    # ── Filtrer la dernière "rep" si c'est un hold post-set ────────────
    # Si le set est terminé et la dernière rep a un ROM très faible,
    # c'est probablement le repositionnement, pas une vraie rep.
    if result.set_complete and len(reps) >= 2:
        last_rep = reps[-1]
        avg_rom_others = float(np.mean([r.rom for r in reps[:-1]]))
        if avg_rom_others > 0 and last_rep.rom < avg_rom_others * 0.4:
            logger.info(
                "Derniere rep filtree (ROM %.1f deg < 40%% de la moyenne %.1f deg) "
                "— probablement un repositionnement post-set.",
                last_rep.rom, avg_rom_others,
            )
            reps.pop()

    # ── Analyse de fatigue ──────────────────────────────────────────────
    _compute_fatigue(reps)

    # ── Détection de triche ─────────────────────────────────────────────
    _detect_cheat(reps, angles.frames, frame_indices, exercise)

    result.reps = reps
    result.total_reps = len(reps)
    result.complete_reps = sum(1 for r in reps if not r.is_partial)
    result.partial_reps = sum(1 for r in reps if r.is_partial)

    # ── Métriques globales ──────────────────────────────────────────────
    if reps:
        # Tempo moyen
        avg_ecc = float(np.mean([r.eccentric_duration_ms for r in reps])) / 1000
        avg_conc = float(np.mean([r.concentric_duration_ms for r in reps])) / 1000
        result.avg_tempo = "{:.0f}:0:{:.0f}".format(avg_ecc, avg_conc)

        # Consistance du tempo
        if len(reps) > 1:
            ratios = [r.tempo_ratio for r in reps if r.tempo_ratio > 0]
            if ratios:
                std = float(np.std(ratios))
                mean = float(np.mean(ratios))
                cv = std / mean if mean > 0 else 1.0
                result.tempo_consistency = max(0.0, min(1.0, 1.0 - cv))

        # ROM moyen et dégradation
        roms = [r.rom for r in reps if r.rom > 0]
        if roms:
            result.avg_rom = float(np.mean(roms))
            if len(roms) >= 2:
                first_rom = roms[0]
                last_rom = roms[-1]
                if first_rom > 0:
                    result.rom_degradation = max(0.0, (1.0 - last_rom / first_rom) * 100)

        # Dégradation de vitesse
        vels = [r.peak_velocity for r in reps if r.peak_velocity > 0]
        if len(vels) >= 2:
            first_vel = vels[0]
            last_vel = vels[-1]
            if first_vel > 0:
                result.velocity_degradation = max(0.0, (1.0 - last_vel / first_vel) * 100)

        # Rep d'apparition de la fatigue (ROM < 90% de la première)
        if len(reps) >= 3:
            for rep in reps[1:]:
                if rep.rom_vs_first < 0.90:
                    result.fatigue_onset_rep = rep.rep_number
                    break

        # Fatigue de la dernière rep
        result.fatigue_index_last_rep = reps[-1].fatigue_index

        # Triche
        cheat_list = [r.rep_number for r in reps if r.cheat_detected]
        result.cheat_reps = cheat_list
        if reps:
            result.cheat_percentage = (len(cheat_list) / len(reps)) * 100

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 3 : RECONCILIATION — robust count overrides if peak detection undercount
    # ══════════════════════════════════════════════════════════════════════
    robust_count = _best_robust_count(autocorr_count, zerocross_count, extrema_count)
    peak_count = result.total_reps
    expected_group = _exercise_motion_group(exercise)
    selected_group = _attr_group(attr)
    group_mismatch = (
        expected_group in {"lower", "upper", "core"}
        and selected_group != expected_group
    )
    result.peak_count = peak_count
    result.autocorr_count = autocorr_count
    result.zerocross_count = zerocross_count
    result.extrema_count = extrema_count
    result.robust_count = robust_count
    robust_values = sorted(v for v in (autocorr_count, zerocross_count, extrema_count) if v > 0)
    robust_reliable = _is_robust_count_reliable(autocorr_count, zerocross_count, extrema_count)
    result.robust_reliable = robust_reliable

    if group_mismatch and robust_count > 0:
        logger.warning(
            "Group guard override: exercise=%s expects=%s, signal=%s (%s) -> robust=%d",
            exercise, expected_group, attr, selected_group, robust_count,
        )
        result.total_reps = robust_count
        result.complete_reps = min(result.complete_reps, robust_count) if result.complete_reps > 0 else robust_count
        result.partial_reps = max(0, robust_count - result.complete_reps)
        result.count_method = "robust_group_guard"
    elif robust_count > peak_count and robust_count > 0:
        if robust_reliable or (robust_count - peak_count) <= max(3, int(peak_count * 0.6) + 1):
            logger.info(
                "Robust up-override: peak=%d, autocorr=%d, zerocross=%d, extrema=%d -> %d",
                peak_count, autocorr_count, zerocross_count, extrema_count, robust_count,
            )
            result.total_reps = robust_count
            # Adjust complete/partial counts proportionally
            if peak_count > 0:
                extra = robust_count - peak_count
                result.complete_reps += extra
            else:
                result.complete_reps = robust_count
                result.partial_reps = 0
            result.count_method = "robust_up_override"
        else:
            logger.info(
                "Robust up override skipped (uncertain): peak=%d, robust=%d, values=%s",
                peak_count, robust_count, robust_values,
            )
            result.count_method = "peak_keep_robust_uncertain"
    elif _should_apply_robust_down_override(peak_count, robust_count, robust_reliable):
        # Peak detection can grossly overcount noisy micro-movements (common on long sets).
        # In that case, robust periodic estimators are more trustworthy.
        logger.info(
            "Robust down-override: peak=%d, autocorr=%d, zerocross=%d, extrema=%d -> %d",
            peak_count, autocorr_count, zerocross_count, extrema_count, robust_count,
        )
        result.total_reps = robust_count
        result.complete_reps = min(result.complete_reps, robust_count)
        result.partial_reps = max(0, robust_count - result.complete_reps)
        result.count_method = "robust_down_override"
    elif robust_count > 0:
        logger.info(
            "Counts aligned: peak=%d, robust=%d (reliable=%s) — keeping peak segmentation.",
            peak_count, robust_count, robust_reliable,
        )
        result.count_method = "peak_aligned_with_robust"
    else:
        result.count_method = "peak_only"

    # Movement start/end on segmented reps when available.
    if reps and fps > 0:
        result.movement_start_frame = int(reps[0].start_frame)
        result.movement_end_frame = int(reps[-1].end_frame)
        result.movement_duration_s = max(
            0.0,
            float(result.movement_end_frame - result.movement_start_frame) / fps,
        )
    elif result.movement_duration_s <= 0 and len(frame_indices) >= 2 and fps > 0:
        result.movement_start_frame = int(frame_indices[0])
        result.movement_end_frame = int(frame_indices[-1])
        result.movement_duration_s = max(
            0.0,
            float(result.movement_end_frame - result.movement_start_frame) / fps,
        )

    transition_rests = _estimate_transition_rests(reps, smoothed, frame_indices, fps)

    # Intensite de serie (densite des reps).
    rep_coverage_ok = abs(len(reps) - result.total_reps) <= max(1, int(result.total_reps * 0.25))
    use_rep_level_intensity = len(reps) >= 2 and not group_mismatch and rep_coverage_ok
    if use_rep_level_intensity:
        intensity = _compute_intensity_metrics(reps, fps, transition_rests_s=transition_rests)
        result.rest_measure_method = "transition_velocity" if transition_rests else "frame_gap"
        if abs(len(reps) - result.total_reps) <= 1:
            intensity_conf = "elevee"
        elif abs(len(reps) - result.total_reps) <= 3:
            intensity_conf = "moyenne"
        else:
            intensity_conf = "limitee"
    else:
        duration_hint_s = combined_duration_s
        if duration_hint_s <= 0 and len(frame_indices) >= 2 and fps > 0:
            duration_hint_s = max(0.0, float(frame_indices[-1] - frame_indices[0]) / fps)
        if duration_hint_s <= 0 and len(reps) >= 1 and fps > 0:
            duration_hint_s = max(0.0, float(reps[-1].end_frame - reps[0].start_frame) / fps)
        intensity = _estimate_intensity_from_count(result.total_reps, duration_hint_s)
        result.rest_measure_method = "estimate_from_count"
        intensity_conf = "limitee"
        if group_mismatch:
            intensity_conf = "limitee (signal non cohérent)"

    result.avg_inter_rep_rest_s = float(intensity["avg_inter_rep_rest_s"])
    result.median_inter_rep_rest_s = float(intensity["median_inter_rep_rest_s"])
    result.max_inter_rep_rest_s = float(intensity["max_inter_rep_rest_s"])
    result.rest_consistency = float(intensity["rest_consistency"])
    result.set_duration_s = float(intensity["set_duration_s"])
    result.reps_per_min = float(intensity["reps_per_min"])
    result.intensity_score = int(intensity["intensity_score"])
    result.intensity_label = str(intensity["intensity_label"])
    result.intensity_confidence = intensity_conf

    # Debug log for visibility in /debug/errors endpoint
    _debug_log("rep_counting", "Rep counting results", {
        "autocorr_count": autocorr_count,
        "zerocross_count": zerocross_count,
        "extrema_count": extrema_count,
        "peak_count": peak_count,
        "final_count": result.total_reps,
        "robust_count": robust_count,
        "robust_reliable": robust_reliable,
        "raw_frames_provided": raw_frames is not None,
        "raw_frames_count": len(raw_frames) if raw_frames else 0,
        "combined_signal_len": len(combined_signal) if combined_signal is not None else 0,
        "fps": fps,
        "exercise": exercise,
        "expected_group": expected_group,
        "selected_group": selected_group,
        "group_mismatch": group_mismatch,
        "segmentation_signal": attr,
        "auto_signal_selected": auto_signal,
        "angle_signal_len": len(signal) if signal is not None else 0,
        "num_peaks": len(peaks) if peaks is not None else 0,
        "num_valleys": len(valleys) if valleys is not None else 0,
        "smooth_window": params["smooth_window"] if params else 0,
        "min_prominence": round(params["min_prominence"], 2) if params else 0,
        "min_distance": params["min_distance"] if params else 0,
        "count_method": result.count_method,
        "rep_coverage_ok": rep_coverage_ok,
        "rest_measure_method": result.rest_measure_method,
        "phase_direction": phase_direction,
        "intensity_score": result.intensity_score,
        "avg_inter_rep_rest_s": round(result.avg_inter_rep_rest_s, 2),
        "reps_per_min": round(result.reps_per_min, 1),
        "movement_start_frame": result.movement_start_frame,
        "movement_end_frame": result.movement_end_frame,
        "movement_duration_s": round(result.movement_duration_s, 2),
    })

    logger.info(
        "Segmentation: %d reps (%d completes, %d partielles), "
        "tempo=%s, ROM_deg=%.0f%%, fatigue_onset=rep%d, triche=%d%%, set_complete=%s "
        "[signal=%s, auto=%s, autocorr=%d, zerocross=%d, extrema=%d]",
        result.total_reps, result.complete_reps, result.partial_reps,
        result.avg_tempo, result.rom_degradation, result.fatigue_onset_rep,
        result.cheat_percentage, result.set_complete,
        attr, auto_signal, autocorr_count, zerocross_count, extrema_count,
    )
    return result
