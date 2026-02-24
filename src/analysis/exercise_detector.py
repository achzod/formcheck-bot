"""Détection automatique de l'exercice à partir des patterns de mouvement.

Analyse les ROM (Range of Motion) et les variations d'angles articulaires
pour classifier l'exercice. Utilise GPT-4 Vision comme backup/confirmation
sur la frame du milieu.

Exercices supportés :
- squat, deadlift, bench_press, ohp (overhead press),
  barbell_row, hip_thrust, curl, lateral_raise
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from analysis.angle_calculator import AngleResult, AngleStats


class Exercise(str, Enum):
    """Exercices supportes."""
    SQUAT = "squat"
    FRONT_SQUAT = "front_squat"
    BULGARIAN_SPLIT_SQUAT = "bulgarian_split_squat"
    LUNGE = "lunge"
    DEADLIFT = "deadlift"
    SUMO_DEADLIFT = "sumo_deadlift"
    RDL = "rdl"
    BENCH_PRESS = "bench_press"
    INCLINE_BENCH = "incline_bench"
    OHP = "ohp"
    BARBELL_ROW = "barbell_row"
    DUMBBELL_ROW = "dumbbell_row"
    HIP_THRUST = "hip_thrust"
    CURL = "curl"
    TRICEP_EXTENSION = "tricep_extension"
    LATERAL_RAISE = "lateral_raise"
    FACE_PULL = "face_pull"
    PULLUP = "pullup"
    LAT_PULLDOWN = "lat_pulldown"
    LEG_PRESS = "leg_press"
    LEG_EXTENSION = "leg_extension"
    LEG_CURL = "leg_curl"
    GOBLET_SQUAT = "goblet_squat"
    UPRIGHT_ROW = "upright_row"
    CABLE_ROW = "cable_row"
    CABLE_CURL = "cable_curl"
    PULLOVER = "pullover"
    CABLE_PULLOVER = "cable_pullover"
    DIP = "dip"
    SHRUG = "shrug"
    CALF_RAISE = "calf_raise"
    HACK_SQUAT = "hack_squat"
    PENDLAY_ROW = "pendlay_row"
    TBAR_ROW = "tbar_row"
    CHEST_FLY = "chest_fly"
    CABLE_CROSSOVER = "cable_crossover"
    REVERSE_FLY = "reverse_fly"
    HAMMER_CURL = "hammer_curl"
    PREACHER_CURL = "preacher_curl"
    SKULL_CRUSHER = "skull_crusher"
    GOOD_MORNING = "good_morning"
    STEP_UP = "step_up"
    SISSY_SQUAT = "sissy_squat"
    UNKNOWN = "unknown"


# Noms affichables pour les rapports
EXERCISE_DISPLAY_NAMES: dict[str, str] = {
    "squat": "Back Squat",
    "front_squat": "Front Squat",
    "goblet_squat": "Goblet Squat",
    "bulgarian_split_squat": "Fente Bulgare (Bulgarian Split Squat)",
    "lunge": "Fente (Lunge)",
    "deadlift": "Deadlift Conventionnel",
    "sumo_deadlift": "Sumo Deadlift",
    "rdl": "Romanian Deadlift (RDL)",
    "bench_press": "Bench Press",
    "incline_bench": "Developpe Incline (Incline Bench Press)",
    "ohp": "Overhead Press (Developpe Militaire)",
    "barbell_row": "Barbell Row (Rowing Barre)",
    "dumbbell_row": "Dumbbell Row (Rowing Haltere)",
    "hip_thrust": "Hip Thrust",
    "curl": "Curl Biceps",
    "tricep_extension": "Extension Triceps",
    "lateral_raise": "Elevations Laterales",
    "face_pull": "Face Pull",
    "pullup": "Pull-Up / Traction",
    "lat_pulldown": "Lat Pulldown (Tirage Vertical)",
    "leg_press": "Leg Press",
    "leg_extension": "Leg Extension",
    "leg_curl": "Leg Curl",
    "upright_row": "Tirage Menton (Upright Row)",
    "cable_row": "Tirage Poulie Basse (Seated Cable Row)",
    "cable_curl": "Curl Cable",
    "pullover": "Pullover (Haltere)",
    "cable_pullover": "Pullover Poulie Haute (Straight-Arm Pulldown)",
    "dip": "Dips",
    "shrug": "Shrugs (Haussements d'Epaules)",
    "calf_raise": "Mollets (Calf Raise)",
    "hack_squat": "Hack Squat",
    "pendlay_row": "Pendlay Row",
    "tbar_row": "T-Bar Row (Rowing en T)",
    "chest_fly": "Ecarte Pectoraux (Chest Fly)",
    "cable_crossover": "Cable Crossover (Vis-a-Vis)",
    "reverse_fly": "Oiseau (Reverse Fly)",
    "hammer_curl": "Curl Marteau (Hammer Curl)",
    "preacher_curl": "Curl Pupitre (Preacher Curl)",
    "skull_crusher": "Barre au Front (Skull Crusher)",
    "good_morning": "Good Morning",
    "step_up": "Step-Up",
    "sissy_squat": "Sissy Squat",
    "unknown": "Exercice non identifie",
}


@dataclass
class DetectionResult:
    """Résultat de la détection d'exercice."""
    exercise: Exercise
    confidence: float              # 0.0-1.0 confiance du détecteur par pattern
    reasoning: str                 # Explication de la classification
    vision_exercise: Exercise | None = None   # Résultat GPT-4 Vision si utilisé
    vision_confidence: float = 0.0
    display_name: str = ""

    def __post_init__(self) -> None:
        if not self.display_name:
            self.display_name = EXERCISE_DISPLAY_NAMES.get(
                self.exercise.value, self.exercise.value
            )


# ── Détection par patterns de mouvement ──────────────────────────────────────

def _rom(stats: dict[str, AngleStats], key: str) -> float:
    """Retourne le ROM d'un angle, ou 0 si absent."""
    s = stats.get(key)
    return s.range_of_motion if s else 0.0


def _mean(stats: dict[str, AngleStats], key: str) -> float:
    """Retourne la moyenne d'un angle, ou 0 si absent."""
    s = stats.get(key)
    return s.mean_value if s else 0.0


def _min(stats: dict[str, AngleStats], key: str) -> float:
    """Retourne le min d'un angle, ou 0 si absent."""
    s = stats.get(key)
    return s.min_value if s else 0.0


def _max(stats: dict[str, AngleStats], key: str) -> float:
    """Retourne le max d'un angle, ou 999 si absent."""
    s = stats.get(key)
    return s.max_value if s else 999.0


def _knee_asymmetry(stats: dict[str, AngleStats]) -> float:
    """Retourne le ratio d'asymétrie du ROM genou G/D (0=symétrique, 1=très asymétrique)."""
    left = _rom(stats, "left_knee_flexion")
    right = _rom(stats, "right_knee_flexion")
    if max(left, right) < 5:
        return 0.0
    return abs(left - right) / max(left, right)


def _hip_asymmetry(stats: dict[str, AngleStats]) -> float:
    """Retourne le ratio d'asymétrie du ROM hanche G/D."""
    left = _rom(stats, "left_hip_flexion")
    right = _rom(stats, "right_hip_flexion")
    if max(left, right) < 5:
        return 0.0
    return abs(left - right) / max(left, right)


def _score_bulgarian_split_squat(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilité d'une fente bulgare."""
    score = 0.0
    reasons: list[str] = []

    knee_rom_max = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    hip_rom_max = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    knee_asym = _knee_asymmetry(stats)
    hip_asym = _hip_asymmetry(stats)
    trunk_mean = _mean(stats, "trunk_inclination")

    # CRITÈRE CLÉ : forte asymétrie genou G/D (un pied surélevé derrière)
    if knee_asym > 0.3:
        score += 0.4
        reasons.append(f"Forte asymétrie genou G/D ({knee_asym:.0%})")
    elif knee_asym > 0.15:
        score += 0.2
        reasons.append(f"Asymétrie genou modérée ({knee_asym:.0%})")

    # ROM genou important côté travail
    if knee_rom_max > 30:
        score += 0.2
        reasons.append(f"ROM genou significatif ({knee_rom_max:.0f}°)")

    # ROM hanche avec asymétrie
    if hip_rom_max > 20 and hip_asym > 0.15:
        score += 0.2
        reasons.append(f"ROM hanche asymétrique ({hip_asym:.0%})")

    # Tronc relativement vertical
    if trunk_mean < 40:
        score += 0.2
        reasons.append(f"Tronc vertical ({trunk_mean:.0f}°)")

    return score, "; ".join(reasons) if reasons else "Pas de pattern fente bulgare"


def _score_lunge(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilité d'une fente (lunge)."""
    score = 0.0
    reasons: list[str] = []

    knee_rom_max = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    knee_asym = _knee_asymmetry(stats)
    trunk_mean = _mean(stats, "trunk_inclination")

    # Asymétrie modérée (moins que bulgare)
    if 0.1 < knee_asym < 0.4:
        score += 0.3
        reasons.append(f"Asymétrie genou ({knee_asym:.0%})")
    # ROM genou
    if knee_rom_max > 25:
        score += 0.3
        reasons.append(f"ROM genou ({knee_rom_max:.0f}°)")
    # Tronc vertical
    if trunk_mean < 30:
        score += 0.2
        reasons.append(f"Tronc vertical ({trunk_mean:.0f}°)")
    # Mouvement hanche
    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    if hip_rom > 15:
        score += 0.2
        reasons.append(f"ROM hanche ({hip_rom:.0f}°)")

    return score, "; ".join(reasons) if reasons else "Pas de pattern lunge"


def _score_rdl(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilité d'un RDL."""
    score = 0.0
    reasons: list[str] = []

    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    trunk_rom = _rom(stats, "trunk_inclination")

    # Grand ROM hanche, faible ROM genou (jambes quasi tendues)
    if hip_rom > 30:
        score += 0.3
        reasons.append(f"Grand ROM hanche ({hip_rom:.0f}°)")
    if knee_rom < 25:
        score += 0.3
        reasons.append(f"Faible ROM genou ({knee_rom:.0f}°) — jambes quasi tendues")
    if trunk_rom > 20:
        score += 0.2
        reasons.append(f"ROM tronc important ({trunk_rom:.0f}°)")
    trunk_max = _max(stats, "trunk_inclination")
    if trunk_max > 40:
        score += 0.2
        reasons.append(f"Tronc très incliné ({trunk_max:.0f}°)")

    return score, "; ".join(reasons) if reasons else "Pas de pattern RDL"


def _score_front_squat(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilité d'un front squat."""
    score = 0.0
    reasons: list[str] = []

    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    trunk_mean = _mean(stats, "trunk_inclination")
    knee_asym = _knee_asymmetry(stats)

    # Comme squat mais tronc plus vertical
    if knee_rom > 30:
        score += 0.25
        reasons.append(f"ROM genou ({knee_rom:.0f}°)")
    if hip_rom > 30:
        score += 0.25
        reasons.append(f"ROM hanche ({hip_rom:.0f}°)")
    if trunk_mean < 25:
        score += 0.3
        reasons.append(f"Tronc très vertical ({trunk_mean:.0f}°) — typique front squat")
    if knee_asym < 0.1:
        score += 0.2
        reasons.append("Mouvement symétrique")

    return score, "; ".join(reasons) if reasons else "Pas de pattern front squat"


def _score_squat(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilité d'un back squat."""
    score = 0.0
    reasons: list[str] = []

    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    trunk_mean = _mean(stats, "trunk_inclination")
    knee_asym = _knee_asymmetry(stats)

    # Grand ROM genou + hanche
    if knee_rom > 30:
        score += 0.25
        reasons.append(f"ROM genou significatif ({knee_rom:.0f}°)")
    if hip_rom > 30:
        score += 0.25
        reasons.append(f"ROM hanche significatif ({hip_rom:.0f}°)")
    # Tronc modérément incliné (plus que front squat)
    if 15 < trunk_mean < 50:
        score += 0.2
        reasons.append(f"Inclinaison tronc modérée ({trunk_mean:.0f}°)")
    # SYMÉTRIQUE — pénaliser si asymétrique (sinon c'est une fente)
    if knee_asym < 0.15:
        score += 0.3
        reasons.append("Mouvement bilatéral symétrique")
    elif knee_asym < 0.25:
        score += 0.1
        reasons.append(f"Légère asymétrie ({knee_asym:.0%})")
    # Si très asymétrique, pénaliser fortement
    if knee_asym > 0.3:
        score -= 0.3
        reasons.append(f"⚠️ Forte asymétrie — probablement unilatéral ({knee_asym:.0%})")

    return score, "; ".join(reasons) if reasons else "Pas de pattern squat"


def _score_deadlift(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilité d'un deadlift."""
    score = 0.0
    reasons: list[str] = []

    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    trunk_rom = _rom(stats, "trunk_inclination")

    # Grand ROM hanche + ROM tronc important
    if hip_rom > 30:
        score += 0.3
        reasons.append(f"ROM hanche important ({hip_rom:.0f}°)")
    if trunk_rom > 20:
        score += 0.3
        reasons.append(f"ROM tronc important ({trunk_rom:.0f}°)")
    # ROM genou modéré (pas autant que squat)
    if 10 < knee_rom < 40:
        score += 0.2
        reasons.append(f"ROM genou modéré ({knee_rom:.0f}°)")
    # Tronc incliné (penché en avant)
    trunk_max = _max(stats, "trunk_inclination")
    if trunk_max > 40:
        score += 0.2
        reasons.append(f"Tronc très incliné au départ ({trunk_max:.0f}°)")

    return score, "; ".join(reasons) if reasons else "Pas de pattern deadlift"


def _score_bench_press(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilité d'un bench press."""
    score = 0.0
    reasons: list[str] = []

    elbow_rom = max(
        _rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion")
    )
    shoulder_rom = max(
        _rom(stats, "left_shoulder_flexion"), _rom(stats, "right_shoulder_flexion")
    )
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))

    # Grand ROM coude + épaule
    if elbow_rom > 30:
        score += 0.3
        reasons.append(f"ROM coude important ({elbow_rom:.0f}°)")
    if shoulder_rom > 20:
        score += 0.2
        reasons.append(f"ROM épaule ({shoulder_rom:.0f}°)")
    # Peu de mouvement des jambes
    if knee_rom < 15 and hip_rom < 15:
        score += 0.3
        reasons.append("Pas de mouvement des jambes (allongé)")
    # Tronc quasi horizontal
    trunk_mean = _mean(stats, "trunk_inclination")
    if trunk_mean > 60:
        score += 0.2
        reasons.append(f"Tronc quasi horizontal ({trunk_mean:.0f}°)")

    return score, "; ".join(reasons) if reasons else "Pas de pattern bench press"


def _score_ohp(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilité d'un overhead press."""
    score = 0.0
    reasons: list[str] = []

    elbow_rom = max(
        _rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion")
    )
    shoulder_abd_rom = max(
        _rom(stats, "left_shoulder_abduction"), _rom(stats, "right_shoulder_abduction")
    )
    shoulder_flex_rom = max(
        _rom(stats, "left_shoulder_flexion"), _rom(stats, "right_shoulder_flexion")
    )
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    trunk_mean = _mean(stats, "trunk_inclination")

    # Grand ROM coude + épaule avec tronc vertical
    if elbow_rom > 30:
        score += 0.25
        reasons.append(f"ROM coude ({elbow_rom:.0f}°)")
    if shoulder_flex_rom > 30 or shoulder_abd_rom > 30:
        score += 0.25
        reasons.append(f"ROM épaule flex/abd significatif")
    if trunk_mean < 20:
        score += 0.25
        reasons.append(f"Tronc vertical ({trunk_mean:.0f}°)")
    if knee_rom < 15:
        score += 0.25
        reasons.append("Jambes stables")

    return score, "; ".join(reasons) if reasons else "Pas de pattern OHP"


def _score_barbell_row(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilité d'un barbell row."""
    score = 0.0
    reasons: list[str] = []

    elbow_rom = max(
        _rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion")
    )
    trunk_mean = _mean(stats, "trunk_inclination")
    trunk_rom = _rom(stats, "trunk_inclination")
    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))

    # ROM coude (traction) avec tronc incliné et stable
    if elbow_rom > 25:
        score += 0.3
        reasons.append(f"ROM coude (traction) ({elbow_rom:.0f}°)")
    if 30 < trunk_mean < 70:
        score += 0.25
        reasons.append(f"Tronc incliné ({trunk_mean:.0f}°)")
    if trunk_rom < 15:
        score += 0.25
        reasons.append(f"Tronc stable (ROM {trunk_rom:.0f}°)")
    if hip_rom < 15:
        score += 0.2
        reasons.append("Hanches stables (hip hinge statique)")

    return score, "; ".join(reasons) if reasons else "Pas de pattern barbell row"


def _score_hip_thrust(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilité d'un hip thrust."""
    score = 0.0
    reasons: list[str] = []

    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    trunk_rom = _rom(stats, "trunk_inclination")
    trunk_mean = _mean(stats, "trunk_inclination")

    # Grand ROM hanche avec peu de ROM genou
    if hip_rom > 25:
        score += 0.3
        reasons.append(f"ROM hanche significatif ({hip_rom:.0f}°)")
    if knee_rom < 20:
        score += 0.25
        reasons.append(f"ROM genou faible ({knee_rom:.0f}°)")
    # Tronc relativement horizontal
    if trunk_mean > 40:
        score += 0.25
        reasons.append(f"Tronc horizontal ({trunk_mean:.0f}°)")
    if trunk_rom > 15:
        score += 0.2
        reasons.append(f"Mouvement d'extension du tronc ({trunk_rom:.0f}°)")

    return score, "; ".join(reasons) if reasons else "Pas de pattern hip thrust"


def _score_curl(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilité d'un curl biceps."""
    score = 0.0
    reasons: list[str] = []

    elbow_rom = max(
        _rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion")
    )
    shoulder_rom = max(
        _rom(stats, "left_shoulder_flexion"), _rom(stats, "right_shoulder_flexion")
    )
    trunk_rom = _rom(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))

    # Grand ROM coude, peu de mouvement ailleurs
    if elbow_rom > 40:
        score += 0.35
        reasons.append(f"Grand ROM coude ({elbow_rom:.0f}°)")
    if shoulder_rom < 20:
        score += 0.25
        reasons.append(f"Épaules stables ({shoulder_rom:.0f}°)")
    if trunk_rom < 10:
        score += 0.2
        reasons.append(f"Tronc stable ({trunk_rom:.0f}°)")
    if knee_rom < 10:
        score += 0.2
        reasons.append("Jambes immobiles")

    return score, "; ".join(reasons) if reasons else "Pas de pattern curl"


def _score_lateral_raise(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilité d'une élévation latérale."""
    score = 0.0
    reasons: list[str] = []

    shoulder_abd_rom = max(
        _rom(stats, "left_shoulder_abduction"),
        _rom(stats, "right_shoulder_abduction"),
    )
    elbow_rom = max(
        _rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion")
    )
    trunk_rom = _rom(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))

    # Grand ROM abduction épaule, peu de flexion coude
    if shoulder_abd_rom > 30:
        score += 0.35
        reasons.append(f"Grand ROM abduction épaule ({shoulder_abd_rom:.0f}°)")
    if elbow_rom < 20:
        score += 0.25
        reasons.append(f"Coudes quasi fixes ({elbow_rom:.0f}°)")
    if trunk_rom < 10:
        score += 0.2
        reasons.append(f"Tronc stable ({trunk_rom:.0f}°)")
    if knee_rom < 10:
        score += 0.2
        reasons.append("Jambes immobiles")

    return score, "; ".join(reasons) if reasons else "Pas de pattern lat raise"


def _score_tricep_extension(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'une extension triceps."""
    score = 0.0
    reasons: list[str] = []

    elbow_rom = max(
        _rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion")
    )
    shoulder_rom = max(
        _rom(stats, "left_shoulder_flexion"), _rom(stats, "right_shoulder_flexion")
    )
    trunk_rom = _rom(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))

    # Grand ROM coude, peu de mouvement epaule (contrairement au curl ou OHP)
    if elbow_rom > 40:
        score += 0.35
        reasons.append(f"Grand ROM coude ({elbow_rom:.0f} deg)")
    if shoulder_rom < 15:
        score += 0.25
        reasons.append(f"Epaules stables ({shoulder_rom:.0f} deg)")
    if trunk_rom < 10:
        score += 0.2
        reasons.append(f"Tronc stable ({trunk_rom:.0f} deg)")
    if knee_rom < 10:
        score += 0.2
        reasons.append("Jambes immobiles")

    return score, "; ".join(reasons) if reasons else "Pas de pattern tricep extension"


def _score_pullup(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un pull-up ou traction."""
    score = 0.0
    reasons: list[str] = []

    elbow_rom = max(
        _rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion")
    )
    shoulder_abd_rom = max(
        _rom(stats, "left_shoulder_abduction"), _rom(stats, "right_shoulder_abduction")
    )
    trunk_rom = _rom(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))

    # Grand ROM coude + mouvement epaule + pas de mouvement jambes
    if elbow_rom > 30:
        score += 0.3
        reasons.append(f"ROM coude important ({elbow_rom:.0f} deg)")
    if shoulder_abd_rom > 15:
        score += 0.2
        reasons.append(f"ROM epaule ({shoulder_abd_rom:.0f} deg)")
    if trunk_rom < 20:
        score += 0.25
        reasons.append(f"Tronc stable ({trunk_rom:.0f} deg)")
    if knee_rom < 10:
        score += 0.25
        reasons.append("Jambes stables (suspension)")

    return score, "; ".join(reasons) if reasons else "Pas de pattern pull-up"


def _score_upright_row(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un tirage menton (upright row) — barre, haltere ou poulie."""
    score = 0.0
    reasons: list[str] = []

    elbow_rom = max(
        _rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion")
    )
    shoulder_abd_rom = max(
        _rom(stats, "left_shoulder_abduction"), _rom(stats, "right_shoulder_abduction")
    )
    shoulder_flex_rom = max(
        _rom(stats, "left_shoulder_flexion"), _rom(stats, "right_shoulder_flexion")
    )
    trunk_rom = _rom(stats, "trunk_inclination")
    trunk_mean = _mean(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))

    # Coudes flechissent ET montent (ROM coude significatif)
    if elbow_rom > 25:
        score += 0.25
        reasons.append(f"ROM coude ({elbow_rom:.0f} deg)")

    # Epaules en abduction et/ou flexion (bras montent sur les cotes)
    shoulder_combined = max(shoulder_abd_rom, shoulder_flex_rom)
    if shoulder_combined > 20:
        score += 0.25
        reasons.append(f"ROM epaule significatif ({shoulder_combined:.0f} deg)")

    # CRITERE CLE : coudes ET epaules bougent ensemble (distingue du curl)
    if elbow_rom > 20 and shoulder_combined > 15:
        score += 0.2
        reasons.append("Coudes + epaules actifs simultanement — typique tirage menton")

    # Tronc vertical et stable
    if trunk_mean < 25 and trunk_rom < 12:
        score += 0.15
        reasons.append(f"Tronc vertical stable ({trunk_mean:.0f} deg)")

    # Jambes immobiles (debout)
    if knee_rom < 10:
        score += 0.15
        reasons.append("Jambes immobiles")

    return score, "; ".join(reasons) if reasons else "Pas de pattern tirage menton"


def _score_cable_row(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un tirage poulie basse (seated cable row)."""
    score = 0.0
    reasons: list[str] = []

    elbow_rom = max(
        _rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion")
    )
    shoulder_rom = max(
        _rom(stats, "left_shoulder_flexion"), _rom(stats, "right_shoulder_flexion")
    )
    trunk_rom = _rom(stats, "trunk_inclination")
    trunk_mean = _mean(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))

    # ROM coude (traction horizontale)
    if elbow_rom > 25:
        score += 0.3
        reasons.append(f"ROM coude (traction) ({elbow_rom:.0f} deg)")
    # Epaule bouge (retraction scapulaire)
    if shoulder_rom > 10:
        score += 0.2
        reasons.append(f"ROM epaule ({shoulder_rom:.0f} deg)")
    # Tronc relativement vertical avec leger mouvement (pas autant que barbell row)
    if trunk_mean < 35:
        score += 0.15
        reasons.append(f"Tronc quasi vertical ({trunk_mean:.0f} deg)")
    if 5 < trunk_rom < 20:
        score += 0.15
        reasons.append(f"Leger mouvement tronc ({trunk_rom:.0f} deg)")
    # Jambes stables (assis)
    if knee_rom < 10:
        score += 0.2
        reasons.append("Jambes stables (assis)")

    return score, "; ".join(reasons) if reasons else "Pas de pattern cable row"


def _score_cable_pullover(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un pullover poulie haute (straight-arm pulldown).

    Pattern cle : grand ROM epaule flexion/extension, coudes quasi fixes,
    tronc legerement penche et stable, jambes immobiles.
    """
    score = 0.0
    reasons: list[str] = []

    shoulder_flex_rom = max(
        _rom(stats, "left_shoulder_flexion"), _rom(stats, "right_shoulder_flexion")
    )
    shoulder_abd_rom = max(
        _rom(stats, "left_shoulder_abduction"), _rom(stats, "right_shoulder_abduction")
    )
    elbow_rom = max(
        _rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion")
    )
    trunk_mean = _mean(stats, "trunk_inclination")
    trunk_rom = _rom(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))

    # CRITERE CLE : grand ROM epaule (bras montent et descendent en arc)
    if shoulder_flex_rom > 25:
        score += 0.3
        reasons.append(f"Grand ROM epaule flexion ({shoulder_flex_rom:.0f} deg)")
    elif shoulder_abd_rom > 25:
        score += 0.25
        reasons.append(f"Grand ROM epaule abduction ({shoulder_abd_rom:.0f} deg)")

    # Coudes quasi fixes (bras tendus ou legerement flechis)
    if elbow_rom < 20:
        score += 0.25
        reasons.append(f"Coudes quasi fixes ({elbow_rom:.0f} deg) — bras tendus")
    elif elbow_rom < 30:
        score += 0.1
        reasons.append(f"Coudes peu mobiles ({elbow_rom:.0f} deg)")

    # Tronc legerement penche et stable
    if 5 < trunk_mean < 40 and trunk_rom < 15:
        score += 0.2
        reasons.append(f"Tronc stable legerement penche ({trunk_mean:.0f} deg)")

    # Jambes et hanches immobiles (debout)
    if knee_rom < 10 and hip_rom < 15:
        score += 0.25
        reasons.append("Jambes et hanches immobiles — debout face a la poulie")

    return score, "; ".join(reasons) if reasons else "Pas de pattern pullover poulie"


def _score_pullover(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un pullover haltere (allonge sur banc)."""
    score = 0.0
    reasons: list[str] = []

    shoulder_flex_rom = max(
        _rom(stats, "left_shoulder_flexion"), _rom(stats, "right_shoulder_flexion")
    )
    elbow_rom = max(
        _rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion")
    )
    trunk_mean = _mean(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))

    # Grand ROM epaule
    if shoulder_flex_rom > 30:
        score += 0.3
        reasons.append(f"Grand ROM epaule ({shoulder_flex_rom:.0f} deg)")
    # Coudes peu mobiles
    if elbow_rom < 25:
        score += 0.25
        reasons.append(f"Coudes quasi fixes ({elbow_rom:.0f} deg)")
    # Tronc horizontal (allonge)
    if trunk_mean > 50:
        score += 0.25
        reasons.append(f"Tronc horizontal ({trunk_mean:.0f} deg) — position allongee")
    # Jambes stables
    if knee_rom < 10:
        score += 0.2
        reasons.append("Jambes stables")

    return score, "; ".join(reasons) if reasons else "Pas de pattern pullover"


def _score_dip(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite de dips."""
    score = 0.0
    reasons: list[str] = []

    elbow_rom = max(
        _rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion")
    )
    shoulder_rom = max(
        _rom(stats, "left_shoulder_flexion"), _rom(stats, "right_shoulder_flexion")
    )
    trunk_rom = _rom(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))

    if elbow_rom > 30:
        score += 0.3
        reasons.append(f"ROM coude ({elbow_rom:.0f} deg)")
    if shoulder_rom > 15:
        score += 0.2
        reasons.append(f"ROM epaule ({shoulder_rom:.0f} deg)")
    if trunk_rom > 5 and trunk_rom < 25:
        score += 0.2
        reasons.append(f"Leger mouvement tronc ({trunk_rom:.0f} deg)")
    if knee_rom < 10:
        score += 0.3
        reasons.append("Jambes immobiles (suspension)")

    return score, "; ".join(reasons) if reasons else "Pas de pattern dips"


def _score_shrug(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite de shrugs."""
    score = 0.0
    reasons: list[str] = []

    shoulder_abd_rom = max(
        _rom(stats, "left_shoulder_abduction"), _rom(stats, "right_shoulder_abduction")
    )
    elbow_rom = max(
        _rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion")
    )
    trunk_rom = _rom(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))

    # Tres faible ROM partout SAUF epaules (haussement)
    if shoulder_abd_rom > 5 and shoulder_abd_rom < 25:
        score += 0.3
        reasons.append(f"Petit ROM epaule ({shoulder_abd_rom:.0f} deg) — haussement")
    if elbow_rom < 10:
        score += 0.3
        reasons.append(f"Coudes immobiles ({elbow_rom:.0f} deg)")
    if trunk_rom < 8:
        score += 0.2
        reasons.append(f"Tronc stable ({trunk_rom:.0f} deg)")
    if knee_rom < 8:
        score += 0.2
        reasons.append("Jambes immobiles")

    return score, "; ".join(reasons) if reasons else "Pas de pattern shrug"


def _score_goblet_squat(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un goblet squat (similaire au front squat, tronc tres vertical)."""
    score = 0.0
    reasons: list[str] = []

    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    trunk_mean = _mean(stats, "trunk_inclination")
    elbow_rom = max(_rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion"))

    if knee_rom > 30:
        score += 0.25
        reasons.append(f"ROM genou ({knee_rom:.0f} deg)")
    if hip_rom > 30:
        score += 0.25
        reasons.append(f"ROM hanche ({hip_rom:.0f} deg)")
    if trunk_mean < 20:
        score += 0.3
        reasons.append(f"Tronc tres vertical ({trunk_mean:.0f} deg) — typique goblet squat")
    if elbow_rom < 15:
        score += 0.2
        reasons.append(f"Coudes stables ({elbow_rom:.0f} deg) — charge contre le torse")

    return score, "; ".join(reasons) if reasons else "Pas de pattern goblet squat"


# Mapping exercice → fonction de scoring
_SCORERS: dict[Exercise, Any] = {
    Exercise.BULGARIAN_SPLIT_SQUAT: _score_bulgarian_split_squat,
    Exercise.LUNGE: _score_lunge,
    Exercise.FRONT_SQUAT: _score_front_squat,
    Exercise.GOBLET_SQUAT: _score_goblet_squat,
    Exercise.SQUAT: _score_squat,
    Exercise.RDL: _score_rdl,
    Exercise.DEADLIFT: _score_deadlift,
    Exercise.BENCH_PRESS: _score_bench_press,
    Exercise.OHP: _score_ohp,
    Exercise.BARBELL_ROW: _score_barbell_row,
    Exercise.HIP_THRUST: _score_hip_thrust,
    Exercise.CURL: _score_curl,
    Exercise.TRICEP_EXTENSION: _score_tricep_extension,
    Exercise.LATERAL_RAISE: _score_lateral_raise,
    Exercise.PULLUP: _score_pullup,
    Exercise.UPRIGHT_ROW: _score_upright_row,
    Exercise.CABLE_ROW: _score_cable_row,
    Exercise.CABLE_PULLOVER: _score_cable_pullover,
    Exercise.PULLOVER: _score_pullover,
    Exercise.DIP: _score_dip,
    Exercise.SHRUG: _score_shrug,
}


def detect_by_pattern(angles: AngleResult) -> DetectionResult:
    """Détecte l'exercice par analyse des patterns de mouvement.

    Compare les ROM et moyennes des angles à des profils connus
    pour chaque exercice.
    """
    if not angles.stats:
        return DetectionResult(
            exercise=Exercise.UNKNOWN,
            confidence=0.0,
            reasoning="Pas assez de données d'angles pour la détection.",
        )

    scores: list[tuple[Exercise, float, str]] = []
    for exercise, scorer in _SCORERS.items():
        score, reasoning = scorer(angles.stats)
        scores.append((exercise, score, reasoning))

    # Trier par score décroissant
    scores.sort(key=lambda x: x[1], reverse=True)
    best = scores[0]

    # Seuil minimum de confiance
    if best[1] < 0.3:
        return DetectionResult(
            exercise=Exercise.UNKNOWN,
            confidence=best[1],
            reasoning=f"Score trop faible ({best[1]:.2f}). Meilleur candidat: {best[0].value}. {best[2]}",
        )

    return DetectionResult(
        exercise=best[0],
        confidence=best[1],
        reasoning=best[2],
    )


# ── Confirmation via GPT-4 Vision ───────────────────────────────────────────

def _encode_image_base64(image_path: str) -> str:
    """Encode une image en base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def detect_by_vision(
    mid_frame_path: str,
    api_key: str | None = None,
) -> tuple[Exercise, float, str]:
    """Utilise GPT-4o Vision pour identifier l'exercice sur la frame du milieu.

    Architecture vision-first : cette fonction est le detecteur PRIMAIRE.
    Elle doit etre precise et fiable.

    Args:
        mid_frame_path: Chemin vers l'image de la frame du milieu.
        api_key: Cle API OpenAI. Si None, utilise OPENAI_API_KEY.

    Returns:
        Tuple (exercise, confidence, reasoning).
    """
    import logging
    logger = logging.getLogger(__name__)

    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return Exercise.UNKNOWN, 0.0, "Pas de cle API OpenAI configuree."

    if not Path(mid_frame_path).exists():
        return Exercise.UNKNOWN, 0.0, "Image introuvable"

    try:
        import openai

        client = openai.OpenAI(api_key=key)
        b64_image = _encode_image_base64(mid_frame_path)

        exercises_list = ", ".join(
            ["{} ({})".format(e.value, EXERCISE_DISPLAY_NAMES[e.value]) for e in Exercise if e != Exercise.UNKNOWN]
        )

        system_prompt = (
            "Tu es un coach de musculation expert avec 15 ans d'experience et "
            "des certifications NASM, ISSA, Pre-Script. Tu identifies les exercices "
            "de musculation avec precision.\n\n"
            "REGLES D'IDENTIFICATION :\n"
            "- Regarde la POSITION DU CORPS, l'EQUIPEMENT utilise (barre, halteres, "
            "poulie haute/basse, machine, poids de corps), et le PLAN DE MOUVEMENT.\n"
            "- Un pullover poulie haute (cable_pullover/straight-arm pulldown) = debout, "
            "bras tendus, tirant une poulie haute vers le bas en arc. NE PAS confondre "
            "avec lat_pulldown (assis, coudes flechis) ou barbell_row.\n"
            "- Un tirage menton (upright_row) = debout, barre/halteres/poulie monte le "
            "long du corps, coudes montent sur les cotes.\n"
            "- Distinguer squat (barre sur le dos) vs front_squat (barre devant) vs "
            "goblet_squat (haltere/kettlebell contre le torse).\n"
            "- Distinguer deadlift (depart sol) vs rdl (depart debout, jambes quasi tendues).\n"
            "- Si la personne est DEBOUT face a une poulie avec les bras qui bougent, "
            "c'est probablement un exercice de poulie (cable_pullover, face_pull, "
            "cable_row, tricep_extension, cable_curl, upright_row).\n\n"
            "Reponds UNIQUEMENT avec un JSON valide :\n"
            '{"exercise": "<nom_exact>", "confidence": <0.0-1.0>, '
            '"reasoning": "<explication courte>"}\n\n'
            "Exercices possibles (utilise EXACTEMENT un de ces noms) :\n"
            "{}".format(exercises_list)
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/jpeg;base64,{}".format(b64_image),
                                "detail": "high",
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Identifie precisement l'exercice de musculation "
                                "sur cette image. Regarde l'equipement, la position "
                                "du corps, et le plan de mouvement."
                            ),
                        },
                    ],
                },
            ],
            max_tokens=300,
            temperature=0.1,
        )

        import json
        content = response.choices[0].message.content or ""
        logger.info("Vision raw response: %s", content[:300])

        # Extraire le JSON de la reponse
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(content[start:end])
            ex_name = data.get("exercise", "unknown").lower().replace(" ", "_").replace("-", "_")

            # Gerer les aliases courants que GPT pourrait retourner
            _ALIASES = {
                "straight_arm_pulldown": "cable_pullover",
                "straight_arm_pushdown": "cable_pullover",
                "cable_straight_arm_pulldown": "cable_pullover",
                "pullover_poulie": "cable_pullover",
                "pullover_poulie_haute": "cable_pullover",
                "tirage_menton": "upright_row",
                "rowing_barre": "barbell_row",
                "rowing_haltere": "dumbbell_row",
                "developpe_couche": "bench_press",
                "developpe_incline": "incline_bench",
                "developpe_militaire": "ohp",
                "elevation_laterale": "lateral_raise",
                "elevations_laterales": "lateral_raise",
                "traction": "pullup",
                "tirage_vertical": "lat_pulldown",
                "tirage_poulie_basse": "cable_row",
                "seated_cable_row": "cable_row",
                "seated_row": "cable_row",
                "extension_triceps": "tricep_extension",
                "cable_tricep_extension": "tricep_extension",
                "pushdown": "tricep_extension",
                "tricep_pushdown": "tricep_extension",
                "fente_bulgare": "bulgarian_split_squat",
                "fente": "lunge",
                "souleve_de_terre": "deadlift",
                "hip_hinge": "rdl",
                "romanian_deadlift": "rdl",
                "haussement_epaules": "shrug",
                "mollets": "calf_raise",
                "ecarte": "chest_fly",
                "pec_fly": "chest_fly",
                "pec_deck": "chest_fly",
                "butterfly": "chest_fly",
                "vis_a_vis": "cable_crossover",
                "cable_fly": "cable_crossover",
                "oiseau": "reverse_fly",
                "rear_delt_fly": "reverse_fly",
                "rear_delt": "reverse_fly",
                "curl_marteau": "hammer_curl",
                "curl_pupitre": "preacher_curl",
                "barre_au_front": "skull_crusher",
                "lying_tricep_extension": "skull_crusher",
                "french_press": "skull_crusher",
                "t_bar_row": "tbar_row",
                "t_bar": "tbar_row",
                "hack_squat_machine": "hack_squat",
                "step_ups": "step_up",
            }
            ex_name = _ALIASES.get(ex_name, ex_name)

            try:
                exercise = Exercise(ex_name)
            except ValueError:
                logger.warning("Vision returned unknown exercise name: %s", ex_name)
                exercise = Exercise.UNKNOWN
            
            result = (
                exercise,
                float(data.get("confidence", 0.5)),
                data.get("reasoning", ""),
            )
            logger.info("Vision parsed: %s (conf=%.2f)", exercise.value, result[1])
            return result

        logger.warning("Vision response not parseable: %s", content[:200])
        return Exercise.UNKNOWN, 0.0, "Reponse non parseable: {}".format(content[:100])

    except Exception as e:
        logger.exception("Vision detection failed")
        return Exercise.UNKNOWN, 0.0, "Erreur GPT-4 Vision: {}".format(str(e))


def detect_exercise(
    angles: AngleResult,
    mid_frame_path: str | None = None,
    use_vision_backup: bool = True,
) -> DetectionResult:
    """Détecte l'exercice — VISION-FIRST, pattern matching en backup.

    Architecture :
    1. GPT-4o Vision identifie l'exercice sur la frame du milieu (primaire)
    2. Pattern matching par angles (backup si vision échoue)
    3. Si les deux sont d'accord → haute confiance

    Args:
        angles: Résultat du calcul d'angles.
        mid_frame_path: Chemin vers l'image de la frame du milieu.
        use_vision_backup: Activer la vision (désactiver uniquement pour tests).

    Returns:
        DetectionResult avec l'exercice détecté et les métadonnées.
    """
    import logging
    logger = logging.getLogger(__name__)

    pattern_result = detect_by_pattern(angles)
    logger.info(
        "Pattern detection: %s (conf=%.2f) — %s",
        pattern_result.exercise.value, pattern_result.confidence, pattern_result.reasoning,
    )

    # ── Vision-first : GPT-4o est meilleur pour identifier visuellement ──
    if use_vision_backup and mid_frame_path:
        vision_ex, vision_conf, vision_reason = detect_by_vision(mid_frame_path)
        logger.info(
            "Vision detection: %s (conf=%.2f) — %s",
            vision_ex.value, vision_conf, vision_reason,
        )

        if vision_ex != Exercise.UNKNOWN and vision_conf >= 0.4:
            # Vision a identifié quelque chose
            if vision_ex == pattern_result.exercise:
                # Accord vision + pattern → haute confiance
                return DetectionResult(
                    exercise=vision_ex,
                    confidence=min(1.0, vision_conf + 0.2),
                    reasoning=f"[Vision + Pattern d'accord] {vision_reason}",
                    vision_exercise=vision_ex,
                    vision_confidence=vision_conf,
                )
            else:
                # Désaccord → vision gagne (elle est plus fiable pour l'identification)
                logger.info(
                    "Vision override: %s -> %s",
                    pattern_result.exercise.value, vision_ex.value,
                )
                return DetectionResult(
                    exercise=vision_ex,
                    confidence=vision_conf,
                    reasoning=f"[Vision] {vision_reason} (pattern suggerait: {pattern_result.exercise.value})",
                    vision_exercise=vision_ex,
                    vision_confidence=vision_conf,
                )

    # ── Fallback : pattern matching seul (pas d'image ou vision a échoué) ──
    return pattern_result
