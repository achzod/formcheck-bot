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
    """Utilise GPT-4 Vision pour identifier l'exercice sur la frame du milieu.

    Args:
        mid_frame_path: Chemin vers l'image de la frame du milieu.
        api_key: Clé API OpenAI. Si None, utilise OPENAI_API_KEY.

    Returns:
        Tuple (exercise, confidence, reasoning).
    """
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return Exercise.UNKNOWN, 0.0, "Pas de clé API OpenAI configurée."

    if not Path(mid_frame_path).exists():
        return Exercise.UNKNOWN, 0.0, f"Image introuvable: {mid_frame_path}"

    try:
        import openai

        client = openai.OpenAI(api_key=key)
        b64_image = _encode_image_base64(mid_frame_path)

        exercises_list = ", ".join(
            [f"{e.value} ({EXERCISE_DISPLAY_NAMES[e.value]})" for e in Exercise if e != Exercise.UNKNOWN]
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un expert en musculation. Identifie l'exercice "
                        "sur cette image. Réponds UNIQUEMENT avec un JSON: "
                        '{"exercise": "<nom>", "confidence": <0.0-1.0>, "reasoning": "<explication>"}. '
                        f"Exercices possibles: {exercises_list}."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_image}",
                                "detail": "low",
                            },
                        },
                        {
                            "type": "text",
                            "text": "Quel exercice de musculation est effectué sur cette image ?",
                        },
                    ],
                },
            ],
            max_tokens=200,
            temperature=0.1,
        )

        import json
        content = response.choices[0].message.content or ""
        # Extraire le JSON de la réponse
        # Chercher le premier { et le dernier }
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(content[start:end])
            ex_name = data.get("exercise", "unknown").lower().replace(" ", "_")
            # Mapper vers l'enum
            try:
                exercise = Exercise(ex_name)
            except ValueError:
                exercise = Exercise.UNKNOWN
            return (
                exercise,
                float(data.get("confidence", 0.5)),
                data.get("reasoning", ""),
            )

        return Exercise.UNKNOWN, 0.0, f"Réponse non parseable: {content}"

    except Exception as e:
        return Exercise.UNKNOWN, 0.0, f"Erreur GPT-4 Vision: {e}"


def detect_exercise(
    angles: AngleResult,
    mid_frame_path: str | None = None,
    use_vision_backup: bool = True,
) -> DetectionResult:
    """Détecte l'exercice en combinant pattern matching et vision.

    1. Détection par patterns de mouvement (ROM, angles)
    2. Si la confiance est faible (<0.6) et qu'une image est disponible,
       utilise GPT-4 Vision comme backup/confirmation.

    Args:
        angles: Résultat du calcul d'angles.
        mid_frame_path: Chemin vers l'image de la frame du milieu.
        use_vision_backup: Activer la confirmation par vision.

    Returns:
        DetectionResult avec l'exercice détecté et les métadonnées.
    """
    result = detect_by_pattern(angles)

    # TOUJOURS utiliser la vision si une image est disponible
    # La vision est meilleure que le pattern matching pour les variantes
    if use_vision_backup and mid_frame_path:
        vision_ex, vision_conf, vision_reason = detect_by_vision(mid_frame_path)
        result.vision_exercise = vision_ex
        result.vision_confidence = vision_conf

        if vision_ex != Exercise.UNKNOWN and vision_conf > 0.5:
            # Si pattern et vision sont d'accord → boost confiance
            if vision_ex == result.exercise:
                result.confidence = min(1.0, result.confidence + 0.2)
                result.reasoning += f" | [Vision confirme: {vision_reason}]"
            # Si vision contredit le pattern ET vision a bonne confiance → vision gagne
            elif vision_conf > 0.6:
                result.exercise = vision_ex
                result.confidence = vision_conf
                result.reasoning = f"[Vision override] {vision_reason} (pattern disait: {result.exercise.value})"
                result.display_name = EXERCISE_DISPLAY_NAMES.get(
                    vision_ex.value, vision_ex.value
                )

    return result
