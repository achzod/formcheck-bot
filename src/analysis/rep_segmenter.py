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
            "eccentric_duration_ms": round(self.eccentric_duration_ms, 0),
            "concentric_duration_ms": round(self.concentric_duration_ms, 0),
            "tempo_ratio": round(self.tempo_ratio, 2),
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

    def to_dict(self) -> dict[str, Any]:
        d = {
            "reps": [r.to_dict() for r in self.reps],
            "total_reps": self.total_reps,
            "complete_reps": self.complete_reps,
            "partial_reps": self.partial_reps,
            "avg_tempo": self.avg_tempo,
            "tempo_consistency": round(self.tempo_consistency, 3),
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
        # Fenêtre de lissage plus large pour les mouvements lents
        smooth_window = min(11, max(7, int(fps * 0.4)))
        # Prominence réduite — les pics sont moins marqués
        min_prominence = max(rom_total * 0.10, 2.5)
        # Distance plus grande entre pics — reps plus longues
        min_distance = max(6, int(fps * 0.5))
    else:
        smooth_window = min(7, max(5, int(fps * 0.2)))
        min_prominence = max(rom_total * 0.15, 4.0)
        min_distance = max(4, int(fps * 0.25))

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


def segment_reps(
    angles: AngleResult,
    exercise: str,
    fps: float = 30.0,
) -> RepSegmentation:
    """Segmente les répétitions à partir du signal angulaire.

    Args:
        angles: Résultat du calcul d'angles.
        exercise: Nom de l'exercice (valeur de l'enum Exercise).
        fps: FPS de la vidéo pour calculer les durées.

    Returns:
        RepSegmentation avec les reps détectées, fatigue et triche.
    """
    result = RepSegmentation()

    # Déterminer l'angle principal
    attr = PRIMARY_ANGLE_MAP.get(exercise)
    if not attr:
        logger.warning("Exercice '%s' non mappe, essai avec left_knee_flexion.", exercise)
        attr = "left_knee_flexion"

    signal, frame_indices = _get_signal(angles.frames, attr)
    if len(signal) < 10:
        logger.warning("Signal trop court (%d points) pour detecter des reps.", len(signal))
        return result

    # Paramètres adaptatifs selon l'exercice
    params = _adaptive_params(exercise, signal, fps)

    # Lisser le signal
    smoothed = _smooth_signal(signal, window=int(params["smooth_window"]))

    # Détecter pics et vallées
    peaks, valleys = _find_peaks_valleys(
        smoothed,
        min_prominence=params["min_prominence"],
        min_distance=int(params["min_distance"]),
    )

    if len(valleys) < 2:
        # Pas assez de vallées pour segmenter
        # Essayer avec les pics comme délimiteurs
        if len(peaks) >= 2:
            valleys, peaks = peaks, valleys
        else:
            # Dernier recours : réduire la prominence de 60% et distance de 50%
            logger.info("Pas assez de points, reduction prominence 60%% + distance 50%%.")
            reduced_prom = params["min_prominence"] * 0.4
            peaks, valleys = _find_peaks_valleys(
                smoothed,
                min_prominence=reduced_prom,
                min_distance=max(3, int(params["min_distance"] * 0.5)),
            )
            if len(valleys) < 2 and len(peaks) >= 2:
                valleys, peaks = peaks, valleys
            elif len(valleys) < 2:
                logger.warning("Pas assez de points caracteristiques pour segmenter.")
                return result

    # ROM minimum pour cet exercice
    min_rom = MIN_ROM_THRESHOLD.get(exercise, 10.0)

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

        # Durées
        ecc_ms = (bf - sf) / fps * 1000 if fps > 0 else 0
        conc_ms = (ef - bf) / fps * 1000 if fps > 0 else 0

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

        # Tempo ratio
        tempo_ratio = ecc_ms / conc_ms if conc_ms > 0 else 0.0

        rep = Rep(
            rep_number=len(reps) + 1,
            start_frame=sf,
            end_frame=ef,
            bottom_frame=bf,
            eccentric_frames=(sf, bf),
            concentric_frames=(bf, ef),
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

    logger.info(
        "Segmentation: %d reps (%d completes, %d partielles), "
        "tempo=%s, ROM_deg=%.0f%%, fatigue_onset=rep%d, triche=%d%%, set_complete=%s",
        result.total_reps, result.complete_reps, result.partial_reps,
        result.avg_tempo, result.rom_degradation, result.fatigue_onset_rep,
        result.cheat_percentage, result.set_complete,
    )
    return result
