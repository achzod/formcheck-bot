"""Détection automatique de l'exercice à partir des patterns de mouvement.

Analyse les ROM (Range of Motion) et les variations d'angles articulaires
pour classifier l'exercice. Utilise GPT-4 Vision comme backup/confirmation
sur la frame du milieu.

Couvre 91 exercices via pattern matching + GPT-4o Vision + visual reference matching.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from analysis.angle_calculator import AngleResult, AngleStats

logger = logging.getLogger(__name__)

# ── Reference DB loading ──────────────────────────────────────────────────────

_REFERENCE_DB: dict[str, Any] | None = None
_REFERENCE_DB_PATH = Path(__file__).parent / "exercise_refs" / "reference_db.json"


def _load_reference_db() -> dict[str, Any] | None:
    """Charge la base de données de référence des exercices au premier appel."""
    global _REFERENCE_DB
    if _REFERENCE_DB is not None:
        return _REFERENCE_DB
    try:
        if _REFERENCE_DB_PATH.exists():
            with open(_REFERENCE_DB_PATH, "r", encoding="utf-8") as f:
                _REFERENCE_DB = json.load(f)
            logger.info(
                "Reference DB loaded: %d exercises",
                len(_REFERENCE_DB.get("exercises", {})),
            )
        else:
            logger.warning("Reference DB not found at %s", _REFERENCE_DB_PATH)
            _REFERENCE_DB = {}
    except Exception as exc:
        logger.error("Failed to load reference DB: %s", exc)
        _REFERENCE_DB = {}
    return _REFERENCE_DB


def _get_exercise_tags(exercise_name: str) -> dict[str, Any]:
    """Retourne les tags d'un exercice depuis la base de référence."""
    db = _load_reference_db()
    if not db:
        return {}
    exercises = db.get("exercises", {})
    return exercises.get(exercise_name, {}).get("tags", {})


def _get_candidate_exercises(
    pattern_result: "DetectionResult",
    n: int = 10,
) -> list[str]:
    """Retourne les N exercices candidats les plus probables pour le visual matching.

    Utilise le résultat du pattern matching pour filtrer intelligemment.
    Si le pattern matching a trouvé quelque chose avec une bonne confiance,
    on priorise les exercices de la même catégorie.
    """
    db = _load_reference_db()
    if not db:
        # Fallback: retourner les exercices les plus communs
        return [
            "squat", "deadlift", "bench_press", "ohp", "barbell_row",
            "pullup", "curl", "lat_pulldown", "rdl", "hip_thrust",
        ]

    exercises = db.get("exercises", {})
    best_exercise = pattern_result.exercise.value

    # Trouver la catégorie du meilleur exercice pattern
    best_tags = exercises.get(best_exercise, {}).get("tags", {})
    best_category = best_tags.get("category", "")

    # Score chaque exercice selon sa proximité avec le résultat pattern
    scored: list[tuple[str, float]] = []
    for ex_name, ex_data in exercises.items():
        if ex_name == "unknown":
            continue
        tags = ex_data.get("tags", {})
        score = 0.0

        # Même exercice que le pattern → score max
        if ex_name == best_exercise:
            score = 1.0
        # Même catégorie → score élevé
        elif tags.get("category") == best_category and best_category:
            score = 0.6
        # Même groupe musculaire → score moyen
        else:
            best_muscles = set(best_tags.get("muscle_group", []))
            ex_muscles = set(tags.get("muscle_group", []))
            overlap = len(best_muscles & ex_muscles)
            if overlap > 0:
                score = 0.3 + (overlap * 0.1)

        # Bonus si même equipment
        best_equip = set(best_tags.get("equipment", []))
        ex_equip = set(tags.get("equipment", []))
        if best_equip & ex_equip:
            score += 0.1

        scored.append((ex_name, score))

    # Trier par score décroissant, prendre les N premiers
    scored.sort(key=lambda x: x[1], reverse=True)
    candidates = [name for name, _ in scored[:n]]

    logger.debug("Candidates for visual matching: %s", candidates)
    return candidates


def _build_reference_grid_text(candidates: list[str]) -> str:
    """Construit un texte descriptif des exercices candidats pour le prompt GPT-4o."""
    db = _load_reference_db()
    if not db:
        return ""

    exercises = db.get("exercises", {})
    lines = ["EXERCICES CANDIDATS (images de référence ci-dessous) :"]

    for i, ex_name in enumerate(candidates, 1):
        ex_data = exercises.get(ex_name, {})
        display = ex_data.get("display_name", ex_name)
        key_cues = ex_data.get("key_cues", "")
        tags = ex_data.get("tags", {})
        equip = ", ".join(tags.get("equipment", []))
        position = ", ".join(tags.get("body_position", []))
        line = "{i}. {name} ({display}): {cues} [equipement: {equip}, position: {pos}]".format(
            i=i,
            name=ex_name,
            display=display,
            cues=key_cues,
            equip=equip,
            pos=position,
        )
        lines.append(line)

    return "\n".join(lines)


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
    # ── Pectoraux (nouveaux) ──
    DECLINE_BENCH = "decline_bench"
    DUMBBELL_BENCH = "dumbbell_bench"
    DUMBBELL_INCLINE = "dumbbell_incline"
    CHEST_DIP = "chest_dip"
    PUSH_UP = "push_up"
    MACHINE_CHEST_PRESS = "machine_chest_press"
    SVEND_PRESS = "svend_press"
    LANDMINE_PRESS = "landmine_press"
    # ── Dos (nouveaux) ──
    CHINUP = "chinup"
    CLOSE_GRIP_PULLDOWN = "close_grip_pulldown"
    SEAL_ROW = "seal_row"
    # ── Épaules (nouveaux) ──
    DUMBBELL_OHP = "dumbbell_ohp"
    ARNOLD_PRESS = "arnold_press"
    CABLE_LATERAL_RAISE = "cable_lateral_raise"
    FRONT_RAISE = "front_raise"
    REAR_DELT_FLY = "rear_delt_fly"
    LU_RAISE = "lu_raise"
    # ── Biceps (nouveaux) ──
    DUMBBELL_CURL = "dumbbell_curl"
    INCLINE_CURL = "incline_curl"
    CONCENTRATION_CURL = "concentration_curl"
    SPIDER_CURL = "spider_curl"
    # ── Triceps (nouveaux) ──
    OVERHEAD_TRICEP = "overhead_tricep"
    KICKBACK = "kickback"
    CLOSE_GRIP_BENCH = "close_grip_bench"
    DIAMOND_PUSHUP = "diamond_pushup"
    CABLE_OVERHEAD_TRICEP = "cable_overhead_tricep"
    # ── Quadriceps (nouveaux) ──
    WALKING_LUNGE = "walking_lunge"
    # ── Ischio-jambiers (nouveaux) ──
    NORDIC_CURL = "nordic_curl"
    SINGLE_LEG_RDL = "single_leg_rdl"
    GLUTE_HAM_RAISE = "glute_ham_raise"
    # ── Fessiers (nouveaux) ──
    CABLE_KICKBACK = "cable_kickback"
    GLUTE_BRIDGE = "glute_bridge"
    # ── Deadlift (nouveaux) ──
    TRAP_BAR_DEADLIFT = "trap_bar_deadlift"
    # ── Mollets (nouveaux) ──
    SEATED_CALF_RAISE = "seated_calf_raise"
    # ── Abdos ──
    CRUNCH = "crunch"
    CABLE_CRUNCH = "cable_crunch"
    HANGING_LEG_RAISE = "hanging_leg_raise"
    AB_WHEEL = "ab_wheel"
    PLANK = "plank"
    WOODCHOP = "woodchop"
    # ── Full body / Fonctionnel ──
    CLEAN = "clean"
    SNATCH = "snatch"
    THRUSTER = "thruster"
    KETTLEBELL_SWING = "kettlebell_swing"
    BATTLE_ROPE = "battle_rope"
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
    "decline_bench": "Developpe Decline (Decline Bench Press)",
    "dumbbell_bench": "Developpe Couche Halteres",
    "dumbbell_incline": "Developpe Incline Halteres",
    "chest_dip": "Dips Pectoraux",
    "push_up": "Pompes (Push-Up)",
    "machine_chest_press": "Presse Pectorale Machine",
    "svend_press": "Svend Press",
    "landmine_press": "Landmine Press",
    "chinup": "Traction Supination (Chin-Up)",
    "close_grip_pulldown": "Tirage Vertical Prise Serree",
    "seal_row": "Seal Row",
    "dumbbell_ohp": "Developpe Halteres (Epaules)",
    "arnold_press": "Arnold Press",
    "cable_lateral_raise": "Elevations Laterales Poulie",
    "front_raise": "Elevations Frontales",
    "rear_delt_fly": "Oiseau Arriere (Rear Delt Fly)",
    "lu_raise": "Lu Raise / Y-Raise",
    "dumbbell_curl": "Curl Halteres Alternes",
    "incline_curl": "Curl Incline",
    "concentration_curl": "Curl Concentration",
    "spider_curl": "Spider Curl",
    "overhead_tricep": "Extension Triceps au-dessus de la Tete",
    "kickback": "Kickback Triceps",
    "close_grip_bench": "Developpe Couche Prise Serree",
    "diamond_pushup": "Pompes Diamant",
    "cable_overhead_tricep": "Extension Triceps Poulie Basse (Overhead)",
    "walking_lunge": "Fente Marchee (Walking Lunge)",
    "nordic_curl": "Nordic Curl",
    "single_leg_rdl": "RDL Unilateral",
    "glute_ham_raise": "GHR (Glute Ham Raise)",
    "cable_kickback": "Kickback Fessier Poulie",
    "glute_bridge": "Pont Fessier (Glute Bridge)",
    "trap_bar_deadlift": "Trap Bar Deadlift",
    "seated_calf_raise": "Mollets Assis (Seated Calf Raise)",
    "crunch": "Crunch",
    "cable_crunch": "Crunch Poulie Haute",
    "hanging_leg_raise": "Releve de Jambes Suspendu",
    "ab_wheel": "Ab Wheel (Roue Abdominale)",
    "plank": "Planche (Gainage)",
    "woodchop": "Woodchop Poulie",
    "clean": "Epaule (Clean)",
    "snatch": "Arrache (Snatch)",
    "thruster": "Thruster",
    "kettlebell_swing": "Kettlebell Swing",
    "battle_rope": "Battle Rope",
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
    vision_rep_count: int = 0                # Nombre de reps détectées par Vision
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
        reasons.append("ROM genou ({:.0f} deg)".format(knee_rom))
    if hip_rom > 30:
        score += 0.25
        reasons.append("ROM hanche ({:.0f} deg)".format(hip_rom))
    if trunk_mean < 20:
        score += 0.3
        reasons.append("Tronc tres vertical ({:.0f} deg) -- typique goblet squat".format(trunk_mean))
    if elbow_rom < 15:
        score += 0.2
        reasons.append("Coudes stables ({:.0f} deg) -- charge contre le torse".format(elbow_rom))

    return score, "; ".join(reasons) if reasons else "Pas de pattern goblet squat"


def _score_sumo_deadlift(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un sumo deadlift."""
    score = 0.0
    reasons: list[str] = []

    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    trunk_rom = _rom(stats, "trunk_inclination")
    trunk_mean = _mean(stats, "trunk_inclination")

    # Sumo = plus de ROM genou que conventionnel, tronc plus vertical
    if hip_rom > 25:
        score += 0.25
        reasons.append("ROM hanche ({:.0f} deg)".format(hip_rom))
    if knee_rom > 20:
        score += 0.25
        reasons.append("ROM genou ({:.0f} deg) -- plus que conventionnel".format(knee_rom))
    if trunk_rom > 15:
        score += 0.2
        reasons.append("ROM tronc ({:.0f} deg)".format(trunk_rom))
    # Tronc plus vertical que conventionnel
    if trunk_mean < 45:
        score += 0.15
        reasons.append("Tronc plus vertical ({:.0f} deg)".format(trunk_mean))
    if trunk_mean > 20:
        score += 0.15
        reasons.append("Inclinaison significative ({:.0f} deg)".format(trunk_mean))

    return score, "; ".join(reasons) if reasons else "Pas de pattern sumo deadlift"


def _score_leg_press(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un leg press."""
    score = 0.0
    reasons: list[str] = []

    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    trunk_rom = _rom(stats, "trunk_inclination")
    elbow_rom = max(_rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion"))

    # Grand ROM genou, tronc fixe (assis dans la machine)
    if knee_rom > 30:
        score += 0.3
        reasons.append("Grand ROM genou ({:.0f} deg)".format(knee_rom))
    if hip_rom > 15:
        score += 0.2
        reasons.append("ROM hanche ({:.0f} deg)".format(hip_rom))
    if trunk_rom < 10:
        score += 0.25
        reasons.append("Tronc fixe ({:.0f} deg) -- assis".format(trunk_rom))
    if elbow_rom < 10:
        score += 0.25
        reasons.append("Bras immobiles ({:.0f} deg)".format(elbow_rom))

    return score, "; ".join(reasons) if reasons else "Pas de pattern leg press"


def _score_leg_extension(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un leg extension."""
    score = 0.0
    reasons: list[str] = []

    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    trunk_rom = _rom(stats, "trunk_inclination")
    elbow_rom = max(_rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion"))

    # Grand ROM genou, rien d'autre ne bouge
    if knee_rom > 30:
        score += 0.35
        reasons.append("Grand ROM genou ({:.0f} deg)".format(knee_rom))
    if hip_rom < 10:
        score += 0.25
        reasons.append("Hanches fixes ({:.0f} deg)".format(hip_rom))
    if trunk_rom < 8:
        score += 0.2
        reasons.append("Tronc fixe ({:.0f} deg)".format(trunk_rom))
    if elbow_rom < 10:
        score += 0.2
        reasons.append("Bras immobiles ({:.0f} deg)".format(elbow_rom))

    return score, "; ".join(reasons) if reasons else "Pas de pattern leg extension"


def _score_leg_curl(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un leg curl."""
    score = 0.0
    reasons: list[str] = []

    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    trunk_rom = _rom(stats, "trunk_inclination")
    trunk_mean = _mean(stats, "trunk_inclination")

    # Grand ROM genou, hanches fixes, tronc horizontal (allonge)
    if knee_rom > 25:
        score += 0.3
        reasons.append("Grand ROM genou ({:.0f} deg)".format(knee_rom))
    if hip_rom < 15:
        score += 0.25
        reasons.append("Hanches stables ({:.0f} deg)".format(hip_rom))
    if trunk_rom < 10:
        score += 0.2
        reasons.append("Tronc fixe ({:.0f} deg)".format(trunk_rom))
    if trunk_mean > 50:
        score += 0.25
        reasons.append("Tronc horizontal ({:.0f} deg) -- allonge".format(trunk_mean))

    return score, "; ".join(reasons) if reasons else "Pas de pattern leg curl"


def _score_lat_pulldown(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un lat pulldown."""
    score = 0.0
    reasons: list[str] = []

    elbow_rom = max(_rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion"))
    shoulder_abd_rom = max(_rom(stats, "left_shoulder_abduction"), _rom(stats, "right_shoulder_abduction"))
    trunk_rom = _rom(stats, "trunk_inclination")
    trunk_mean = _mean(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))

    # Grand ROM coude, epaule en adduction, tronc quasi vertical, assis
    if elbow_rom > 30:
        score += 0.3
        reasons.append("ROM coude ({:.0f} deg)".format(elbow_rom))
    if shoulder_abd_rom > 15:
        score += 0.2
        reasons.append("ROM epaule ({:.0f} deg)".format(shoulder_abd_rom))
    # Tronc quasi vertical avec leger recul
    if trunk_mean < 30:
        score += 0.15
        reasons.append("Tronc quasi vertical ({:.0f} deg)".format(trunk_mean))
    if trunk_rom < 15:
        score += 0.15
        reasons.append("Tronc stable ({:.0f} deg)".format(trunk_rom))
    if knee_rom < 10:
        score += 0.2
        reasons.append("Jambes stables (assis)".format())

    return score, "; ".join(reasons) if reasons else "Pas de pattern lat pulldown"


def _score_incline_bench(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un incline bench press."""
    score = 0.0
    reasons: list[str] = []

    elbow_rom = max(_rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion"))
    shoulder_rom = max(_rom(stats, "left_shoulder_flexion"), _rom(stats, "right_shoulder_flexion"))
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    trunk_mean = _mean(stats, "trunk_inclination")

    if elbow_rom > 30:
        score += 0.3
        reasons.append("ROM coude ({:.0f} deg)".format(elbow_rom))
    if shoulder_rom > 15:
        score += 0.2
        reasons.append("ROM epaule ({:.0f} deg)".format(shoulder_rom))
    if knee_rom < 15 and hip_rom < 15:
        score += 0.25
        reasons.append("Jambes immobiles")
    # Incline = tronc a ~30-60 deg (entre horizontal et vertical)
    if 20 < trunk_mean < 60:
        score += 0.25
        reasons.append("Tronc incline ({:.0f} deg) -- banc incline".format(trunk_mean))

    return score, "; ".join(reasons) if reasons else "Pas de pattern incline bench"


def _score_hack_squat(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un hack squat."""
    score = 0.0
    reasons: list[str] = []

    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    trunk_rom = _rom(stats, "trunk_inclination")
    elbow_rom = max(_rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion"))

    if knee_rom > 30:
        score += 0.3
        reasons.append("Grand ROM genou ({:.0f} deg)".format(knee_rom))
    if hip_rom > 15:
        score += 0.2
        reasons.append("ROM hanche ({:.0f} deg)".format(hip_rom))
    if trunk_rom < 15:
        score += 0.25
        reasons.append("Tronc stable ({:.0f} deg) -- guidage machine".format(trunk_rom))
    if elbow_rom < 10:
        score += 0.25
        reasons.append("Bras immobiles (poignees machine)".format())

    return score, "; ".join(reasons) if reasons else "Pas de pattern hack squat"


def _score_good_morning(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un good morning."""
    score = 0.0
    reasons: list[str] = []

    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    trunk_rom = _rom(stats, "trunk_inclination")
    trunk_max = _max(stats, "trunk_inclination")
    elbow_rom = max(_rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion"))

    # Hip hinge avec barre sur le dos: grand ROM hanche+tronc, faible genou, bras fixes
    if hip_rom > 25:
        score += 0.3
        reasons.append("Grand ROM hanche ({:.0f} deg)".format(hip_rom))
    if knee_rom < 20:
        score += 0.2
        reasons.append("Faible ROM genou ({:.0f} deg)".format(knee_rom))
    if trunk_rom > 20:
        score += 0.25
        reasons.append("ROM tronc ({:.0f} deg) -- hip hinge".format(trunk_rom))
    if elbow_rom < 10:
        score += 0.25
        reasons.append("Bras fixes (barre sur le dos)".format())

    return score, "; ".join(reasons) if reasons else "Pas de pattern good morning"


def _score_hammer_curl(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un hammer curl (similaire au curl mais check epaule)."""
    # Pattern identique au curl — la differentiation est visuelle (prise neutre)
    return _score_curl(stats)


def _score_chest_fly(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un chest fly / ecarte."""
    score = 0.0
    reasons: list[str] = []

    shoulder_abd_rom = max(
        _rom(stats, "left_shoulder_abduction"), _rom(stats, "right_shoulder_abduction")
    )
    elbow_rom = max(_rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion"))
    trunk_mean = _mean(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))

    # Grand ROM abduction epaule, coudes quasi fixes, allonge
    if shoulder_abd_rom > 20:
        score += 0.3
        reasons.append("ROM abduction epaule ({:.0f} deg)".format(shoulder_abd_rom))
    if elbow_rom < 20:
        score += 0.25
        reasons.append("Coudes quasi fixes ({:.0f} deg)".format(elbow_rom))
    if trunk_mean > 50:
        score += 0.25
        reasons.append("Tronc horizontal ({:.0f} deg) -- allonge".format(trunk_mean))
    if knee_rom < 10:
        score += 0.2
        reasons.append("Jambes immobiles".format())

    return score, "; ".join(reasons) if reasons else "Pas de pattern chest fly"


def _score_reverse_fly(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un reverse fly / oiseau."""
    score = 0.0
    reasons: list[str] = []

    shoulder_abd_rom = max(
        _rom(stats, "left_shoulder_abduction"), _rom(stats, "right_shoulder_abduction")
    )
    elbow_rom = max(_rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion"))
    trunk_mean = _mean(stats, "trunk_inclination")
    trunk_rom = _rom(stats, "trunk_inclination")

    # ROM abduction epaule, coudes fixes, tronc penche et fixe
    if shoulder_abd_rom > 15:
        score += 0.3
        reasons.append("ROM abduction epaule ({:.0f} deg)".format(shoulder_abd_rom))
    if elbow_rom < 15:
        score += 0.25
        reasons.append("Coudes fixes ({:.0f} deg)".format(elbow_rom))
    if trunk_mean > 30 and trunk_rom < 10:
        score += 0.25
        reasons.append("Tronc penche et stable ({:.0f} deg)".format(trunk_mean))
    if trunk_rom < 10:
        score += 0.2
        reasons.append("Tronc fixe ({:.0f} deg)".format(trunk_rom))

    return score, "; ".join(reasons) if reasons else "Pas de pattern reverse fly"


def _score_face_pull(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un face pull."""
    score = 0.0
    reasons: list[str] = []

    elbow_rom = max(_rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion"))
    shoulder_abd_rom = max(
        _rom(stats, "left_shoulder_abduction"), _rom(stats, "right_shoulder_abduction")
    )
    trunk_mean = _mean(stats, "trunk_inclination")
    trunk_rom = _rom(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))

    if elbow_rom > 15:
        score += 0.25
        reasons.append("ROM coude ({:.0f} deg)".format(elbow_rom))
    if shoulder_abd_rom > 15:
        score += 0.25
        reasons.append("ROM abduction epaule ({:.0f} deg)".format(shoulder_abd_rom))
    if trunk_mean < 20 and trunk_rom < 10:
        score += 0.25
        reasons.append("Tronc vertical stable ({:.0f} deg)".format(trunk_mean))
    if knee_rom < 10:
        score += 0.25
        reasons.append("Jambes immobiles".format())

    return score, "; ".join(reasons) if reasons else "Pas de pattern face pull"


def _score_front_raise(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un front raise."""
    score = 0.0
    reasons: list[str] = []

    shoulder_flex_rom = max(
        _rom(stats, "left_shoulder_flexion"), _rom(stats, "right_shoulder_flexion")
    )
    elbow_rom = max(_rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion"))
    trunk_rom = _rom(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))

    # Grand ROM flexion epaule, coudes quasi fixes, tronc stable
    if shoulder_flex_rom > 30:
        score += 0.35
        reasons.append("Grand ROM flexion epaule ({:.0f} deg)".format(shoulder_flex_rom))
    if elbow_rom < 15:
        score += 0.25
        reasons.append("Coudes quasi fixes ({:.0f} deg)".format(elbow_rom))
    if trunk_rom < 10:
        score += 0.2
        reasons.append("Tronc stable ({:.0f} deg)".format(trunk_rom))
    if knee_rom < 10:
        score += 0.2
        reasons.append("Jambes immobiles".format())

    return score, "; ".join(reasons) if reasons else "Pas de pattern front raise"


def _score_kettlebell_swing(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un kettlebell swing."""
    score = 0.0
    reasons: list[str] = []

    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    shoulder_flex_rom = max(
        _rom(stats, "left_shoulder_flexion"), _rom(stats, "right_shoulder_flexion")
    )
    trunk_rom = _rom(stats, "trunk_inclination")

    # Hip hinge + bras qui montent en avant
    if hip_rom > 25:
        score += 0.3
        reasons.append("Grand ROM hanche ({:.0f} deg) -- hip hinge".format(hip_rom))
    if shoulder_flex_rom > 30:
        score += 0.3
        reasons.append("Grand ROM flexion epaule ({:.0f} deg) -- bras montent".format(shoulder_flex_rom))
    if trunk_rom > 20:
        score += 0.2
        reasons.append("ROM tronc ({:.0f} deg)".format(trunk_rom))
    if knee_rom < 30:
        score += 0.2
        reasons.append("ROM genou modere ({:.0f} deg) -- pas un squat".format(knee_rom))

    return score, "; ".join(reasons) if reasons else "Pas de pattern kettlebell swing"


def _score_push_up(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite de push-ups."""
    score = 0.0
    reasons: list[str] = []

    elbow_rom = max(_rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion"))
    trunk_mean = _mean(stats, "trunk_inclination")
    trunk_rom = _rom(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))

    # ROM coude, tronc quasi horizontal et stable, pas de mouvement des jambes
    if elbow_rom > 30:
        score += 0.3
        reasons.append("ROM coude ({:.0f} deg)".format(elbow_rom))
    if trunk_rom < 15 and trunk_mean > 40:
        score += 0.25
        reasons.append("Tronc horizontal stable ({:.0f} deg)".format(trunk_mean))
    elif trunk_rom < 20:
        score += 0.15
        reasons.append("Tronc stable ({:.0f} deg)".format(trunk_rom))
    if knee_rom < 10:
        score += 0.25
        reasons.append("Jambes immobiles -- gainage".format())
    # Differentier du bench: tronc horizontal dynamique vs bench allonge passif
    if 30 < trunk_mean < 70:
        score += 0.2
        reasons.append("Position prone inclinee".format())

    return score, "; ".join(reasons) if reasons else "Pas de pattern push-up"


def _score_skull_crusher(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un skull crusher."""
    score = 0.0
    reasons: list[str] = []

    elbow_rom = max(_rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion"))
    shoulder_rom = max(_rom(stats, "left_shoulder_flexion"), _rom(stats, "right_shoulder_flexion"))
    trunk_mean = _mean(stats, "trunk_inclination")
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))

    # Grand ROM coude, epaule fixe, allonge
    if elbow_rom > 35:
        score += 0.35
        reasons.append("Grand ROM coude ({:.0f} deg)".format(elbow_rom))
    if shoulder_rom < 15:
        score += 0.25
        reasons.append("Epaules fixes ({:.0f} deg)".format(shoulder_rom))
    if trunk_mean > 60:
        score += 0.2
        reasons.append("Tronc horizontal ({:.0f} deg) -- allonge".format(trunk_mean))
    if knee_rom < 10:
        score += 0.2
        reasons.append("Jambes stables".format())

    return score, "; ".join(reasons) if reasons else "Pas de pattern skull crusher"


def _score_preacher_curl(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un preacher curl."""
    # Pattern similaire au curl mais avec tronc penche
    score = 0.0
    reasons: list[str] = []

    elbow_rom = max(_rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion"))
    shoulder_rom = max(_rom(stats, "left_shoulder_flexion"), _rom(stats, "right_shoulder_flexion"))
    trunk_mean = _mean(stats, "trunk_inclination")
    trunk_rom = _rom(stats, "trunk_inclination")

    if elbow_rom > 35:
        score += 0.35
        reasons.append("Grand ROM coude ({:.0f} deg)".format(elbow_rom))
    if shoulder_rom < 15:
        score += 0.2
        reasons.append("Epaules fixes ({:.0f} deg) -- appui pupitre".format(shoulder_rom))
    if trunk_rom < 10:
        score += 0.2
        reasons.append("Tronc fixe ({:.0f} deg)".format(trunk_rom))
    # Tronc penche en avant (pupitre)
    if 15 < trunk_mean < 50:
        score += 0.25
        reasons.append("Tronc penche ({:.0f} deg) -- pupitre".format(trunk_mean))

    return score, "; ".join(reasons) if reasons else "Pas de pattern preacher curl"


def _score_glute_bridge(stats: dict[str, AngleStats]) -> tuple[float, str]:
    """Score la probabilite d'un glute bridge."""
    score = 0.0
    reasons: list[str] = []

    hip_rom = max(_rom(stats, "left_hip_flexion"), _rom(stats, "right_hip_flexion"))
    knee_rom = max(_rom(stats, "left_knee_flexion"), _rom(stats, "right_knee_flexion"))
    trunk_mean = _mean(stats, "trunk_inclination")
    elbow_rom = max(_rom(stats, "left_elbow_flexion"), _rom(stats, "right_elbow_flexion"))

    if hip_rom > 15:
        score += 0.3
        reasons.append("ROM hanche ({:.0f} deg)".format(hip_rom))
    if knee_rom < 15:
        score += 0.25
        reasons.append("Genou stable ({:.0f} deg)".format(knee_rom))
    if trunk_mean > 50:
        score += 0.25
        reasons.append("Position allongee ({:.0f} deg)".format(trunk_mean))
    if elbow_rom < 10:
        score += 0.2
        reasons.append("Bras immobiles".format())

    return score, "; ".join(reasons) if reasons else "Pas de pattern glute bridge"


# Mapping exercice -> fonction de scoring
_SCORERS: dict[Exercise, Any] = {
    # Knee-dominant
    Exercise.BULGARIAN_SPLIT_SQUAT: _score_bulgarian_split_squat,
    Exercise.LUNGE: _score_lunge,
    Exercise.FRONT_SQUAT: _score_front_squat,
    Exercise.GOBLET_SQUAT: _score_goblet_squat,
    Exercise.SQUAT: _score_squat,
    Exercise.HACK_SQUAT: _score_hack_squat,
    Exercise.LEG_PRESS: _score_leg_press,
    Exercise.LEG_EXTENSION: _score_leg_extension,
    Exercise.LEG_CURL: _score_leg_curl,
    # Hip-dominant
    Exercise.RDL: _score_rdl,
    Exercise.DEADLIFT: _score_deadlift,
    Exercise.SUMO_DEADLIFT: _score_sumo_deadlift,
    Exercise.HIP_THRUST: _score_hip_thrust,
    Exercise.GOOD_MORNING: _score_good_morning,
    Exercise.GLUTE_BRIDGE: _score_glute_bridge,
    Exercise.KETTLEBELL_SWING: _score_kettlebell_swing,
    # Pressing
    Exercise.BENCH_PRESS: _score_bench_press,
    Exercise.INCLINE_BENCH: _score_incline_bench,
    Exercise.OHP: _score_ohp,
    Exercise.PUSH_UP: _score_push_up,
    Exercise.DIP: _score_dip,
    # Pulling
    Exercise.BARBELL_ROW: _score_barbell_row,
    Exercise.PULLUP: _score_pullup,
    Exercise.LAT_PULLDOWN: _score_lat_pulldown,
    Exercise.CABLE_ROW: _score_cable_row,
    Exercise.CABLE_PULLOVER: _score_cable_pullover,
    Exercise.PULLOVER: _score_pullover,
    # Curls
    Exercise.CURL: _score_curl,
    Exercise.HAMMER_CURL: _score_hammer_curl,
    Exercise.PREACHER_CURL: _score_preacher_curl,
    # Triceps
    Exercise.TRICEP_EXTENSION: _score_tricep_extension,
    Exercise.SKULL_CRUSHER: _score_skull_crusher,
    # Shoulders
    Exercise.LATERAL_RAISE: _score_lateral_raise,
    Exercise.FRONT_RAISE: _score_front_raise,
    Exercise.FACE_PULL: _score_face_pull,
    Exercise.REVERSE_FLY: _score_reverse_fly,
    Exercise.UPRIGHT_ROW: _score_upright_row,
    Exercise.SHRUG: _score_shrug,
    # Chest isolation
    Exercise.CHEST_FLY: _score_chest_fly,
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

    # Seuil minimum de confiance — abaissé à 0.25 pour réduire les faux "unknown"
    if best[1] < 0.25:
        return DetectionResult(
            exercise=Exercise.UNKNOWN,
            confidence=best[1],
            reasoning="Score trop faible ({:.2f}). Meilleur candidat: {}. {}".format(best[1], best[0].value, best[2]),
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
    start_frame_path: str | None = None,
    end_frame_path: str | None = None,
    pattern_result: "DetectionResult | None" = None,
) -> tuple[Exercise, float, str]:
    """Utilise GPT-4o Vision pour identifier l'exercice sur 1 a 3 frames.

    Architecture vision-first : cette fonction est le detecteur PRIMAIRE.
    Envoie jusqu'a 3 frames (debut, milieu, fin) + descriptions textuelles
    des 10 exercices candidats les plus probables (visual reference matching).

    Args:
        mid_frame_path: Chemin vers l'image de la frame du milieu (obligatoire).
        api_key: Cle API OpenAI. Si None, utilise OPENAI_API_KEY.
        start_frame_path: Chemin vers la frame de debut (optionnel).
        end_frame_path: Chemin vers la frame de fin (optionnel).
        pattern_result: Resultat du pattern matching pour pre-filtrer les candidats.

    Returns:
        Tuple (exercise, confidence, reasoning).
    """

    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return Exercise.UNKNOWN, 0.0, "Pas de cle API OpenAI configuree.", 0

    if not Path(mid_frame_path).exists():
        return Exercise.UNKNOWN, 0.0, "Image introuvable", 0

    try:
        import openai

        client = openai.OpenAI(api_key=key)

        # Encode toutes les frames disponibles
        frame_paths = []
        if start_frame_path and Path(start_frame_path).exists():
            frame_paths.append(start_frame_path)
        frame_paths.append(mid_frame_path)
        if end_frame_path and Path(end_frame_path).exists():
            frame_paths.append(end_frame_path)

        b64_images = [_encode_image_base64(p) for p in frame_paths]
        num_frames = len(b64_images)

        # ── Visual Reference Matching: build candidate list ──────────────────
        ref_db = _load_reference_db()
        candidate_exercises: list[str] = []
        candidate_text = ""

        if ref_db and ref_db.get("exercises"):
            # Use pattern result to pre-filter candidates if available
            if pattern_result is not None:
                candidate_exercises = _get_candidate_exercises(pattern_result, n=10)
            else:
                # No pattern result: use common exercises as candidates
                candidate_exercises = [
                    "squat", "deadlift", "bench_press", "ohp", "barbell_row",
                    "pullup", "curl", "lat_pulldown", "rdl", "hip_thrust",
                    "front_squat", "incline_bench", "dumbbell_row", "dip",
                    "tricep_extension", "lateral_raise", "push_up", "lunge",
                    "goblet_squat", "cable_row",
                ][:10]
            candidate_text = _build_reference_grid_text(candidate_exercises)
            logger.info(
                "Visual ref matching: %d candidates: %s",
                len(candidate_exercises),
                candidate_exercises,
            )

        # Build full exercises list for system prompt
        exercises_list = ", ".join(
            [
                "{} ({})".format(e.value, EXERCISE_DISPLAY_NAMES[e.value])
                for e in Exercise
                if e != Exercise.UNKNOWN
            ]
        )

        # Build system prompt with reference matching context
        ref_section = ""
        if candidate_text:
            ref_section = (
                "\n\nVISUAL REFERENCE MATCHING :\n"
                "Les {n} exercices candidats les plus probables sont listés ci-dessous "
                "avec leurs indices visuels clés. Compare SOIGNEUSEMENT la vidéo de "
                "l'utilisateur avec ces descriptions pour identifier le meilleur match :\n\n"
                "{candidates}\n\n"
                "MÉTHODE : Identifie lequel de ces {n} candidats correspond EXACTEMENT "
                "à ce que tu vois dans les frames. Si aucun ne correspond parfaitement, "
                "tu peux utiliser un autre exercice de la liste complète ci-dessous."
            ).format(n=len(candidate_exercises), candidates=candidate_text)

        system_prompt = (
            "Tu es un coach de musculation expert avec 15 ans d'experience et "
            "des certifications NASM, ISSA, Pre-Script. Tu identifies les exercices "
            "de musculation avec precision."
            "{ref_section}\n\n"
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
            "- Distinguer deadlift (depart sol, barre monte du sol au verrouillage debout, "
            "LE TORSE SE REDRESSE entre les frames) vs rdl (depart debout, jambes quasi tendues).\n"
            "- Distinguer barbell_row / dumbbell_row (buste penche RESTE FIXE, ce sont les BRAS "
            "qui bougent vers le torse entre les frames, les coudes montent en arriere) vs "
            "deadlift (le TORSE se redresse, les bras restent tendus et ne tirent pas). "
            "Si le torse reste a la meme inclinaison entre les frames = ROW. "
            "Si le torse change d'angle = DEADLIFT.\n"
            "- Distinguer sumo_deadlift (pieds tres ecartes, mains entre les jambes, "
            "torse se redresse) vs barbell_row (pieds largeur epaules, buste penche fixe, "
            "bras tirent vers le ventre).\n"
            "- Si la personne est DEBOUT face a une poulie avec les bras qui bougent, "
            "c'est probablement un exercice de poulie (cable_pullover, face_pull, "
            "cable_row, tricep_extension, cable_curl, upright_row).\n\n"
            "Reponds UNIQUEMENT avec un JSON valide :\n"
            '{{"exercise": "<nom_exact>", "confidence": <0.0-1.0>, '
            '"reasoning": "<explication courte>", '
            '"rep_count": <nombre de repetitions visibles dans les frames>}}\n\n'
            "Exercices possibles (utilise EXACTEMENT un de ces noms) :\n"
            "{exercises_list}"
        ).format(
            ref_section=ref_section,
            exercises_list=exercises_list,
        )

        user_text = (
            "Voici {n} frame(s) extraites d'une meme serie "
            "(debut, milieu, fin si disponibles). "
            "Identifie precisement l'exercice de musculation. "
            "IMPORTANT : Compare les frames entre elles pour voir "
            "CE QUI BOUGE. Si le torse reste fixe et les bras tirent "
            "= rowing. Si le torse se redresse = deadlift. "
            "Regarde l'equipement, la position du corps, "
            "et le plan de mouvement. "
            "Compte aussi le nombre de REPETITIONS visibles "
            "(chaque montee-descente complete = 1 rep). "
            "Si tu ne peux pas compter precisement, estime au mieux."
        ).format(n=num_frames)

        if candidate_exercises:
            user_text += (
                " Parmis les candidats: {candidates}. "
                "Lequel correspond le mieux a ce que tu vois ?"
            ).format(candidates=", ".join(candidate_exercises))

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
                        *[
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "data:image/jpeg;base64,{}".format(b64),
                                    "detail": "high",
                                },
                            }
                            for b64 in b64_images
                        ],
                        {
                            "type": "text",
                            "text": user_text,
                        },
                    ],
                },
            ],
            max_tokens=400,
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
                # Pectoraux
                "decline_bench_press": "decline_bench",
                "decline_press": "decline_bench",
                "developpe_decline": "decline_bench",
                "dumbbell_bench_press": "dumbbell_bench",
                "dumbbell_press": "dumbbell_bench",
                "developpe_couche_halteres": "dumbbell_bench",
                "dumbbell_incline_press": "dumbbell_incline",
                "incline_dumbbell_press": "dumbbell_incline",
                "developpe_incline_halteres": "dumbbell_incline",
                "chest_dips": "chest_dip",
                "dips_pectoraux": "chest_dip",
                "pushup": "push_up",
                "pushups": "push_up",
                "push_ups": "push_up",
                "pompes": "push_up",
                "chest_press_machine": "machine_chest_press",
                "machine_press": "machine_chest_press",
                "presse_pectorale": "machine_chest_press",
                "landmine": "landmine_press",
                # Dos
                "chin_up": "chinup",
                "chin_ups": "chinup",
                "supinated_pullup": "chinup",
                "traction_supination": "chinup",
                "close_grip_lat_pulldown": "close_grip_pulldown",
                "neutral_grip_pulldown": "close_grip_pulldown",
                "tirage_prise_serree": "close_grip_pulldown",
                "chest_supported_row": "seal_row",
                # Épaules
                "dumbbell_shoulder_press": "dumbbell_ohp",
                "seated_dumbbell_press": "dumbbell_ohp",
                "developpe_halteres": "dumbbell_ohp",
                "cable_lateral": "cable_lateral_raise",
                "cable_side_raise": "cable_lateral_raise",
                "front_delt_raise": "front_raise",
                "elevation_frontale": "front_raise",
                "elevations_frontales": "front_raise",
                "reverse_fly_machine": "rear_delt_fly",
                "rear_delt_machine": "rear_delt_fly",
                "oiseau_arriere": "rear_delt_fly",
                "lu_raises": "lu_raise",
                "y_raise": "lu_raise",
                # Biceps
                "alternating_curl": "dumbbell_curl",
                "curl_halteres": "dumbbell_curl",
                "incline_dumbbell_curl": "incline_curl",
                "curl_incline": "incline_curl",
                "curl_concentration": "concentration_curl",
                # Triceps
                "overhead_extension": "overhead_tricep",
                "overhead_tricep_extension": "overhead_tricep",
                "tricep_kickback": "kickback",
                "kickbacks": "kickback",
                "close_grip_press": "close_grip_bench",
                "close_grip_bench_press": "close_grip_bench",
                "diamond_push_up": "diamond_pushup",
                "pompes_diamant": "diamond_pushup",
                "cable_overhead_extension": "cable_overhead_tricep",
                # Jambes
                "walking_lunges": "walking_lunge",
                "fente_marchee": "walking_lunge",
                "nordic_ham_curl": "nordic_curl",
                "nordics": "nordic_curl",
                "single_leg_romanian_deadlift": "single_leg_rdl",
                "single_leg_deadlift": "single_leg_rdl",
                "rdl_unilateral": "single_leg_rdl",
                "ghr": "glute_ham_raise",
                "glute_ham": "glute_ham_raise",
                "cable_glute_kickback": "cable_kickback",
                "kickback_fessier": "cable_kickback",
                "glute_bridge_barbell": "glute_bridge",
                "pont_fessier": "glute_bridge",
                "hex_bar_deadlift": "trap_bar_deadlift",
                "trap_bar": "trap_bar_deadlift",
                # Mollets
                "seated_calf": "seated_calf_raise",
                "mollets_assis": "seated_calf_raise",
                "standing_calf_raise": "calf_raise",
                # Abdos
                "crunches": "crunch",
                "cable_crunches": "cable_crunch",
                "crunch_poulie": "cable_crunch",
                "hanging_leg_raises": "hanging_leg_raise",
                "leg_raise": "hanging_leg_raise",
                "releve_jambes": "hanging_leg_raise",
                "ab_rollout": "ab_wheel",
                "roue_abdominale": "ab_wheel",
                "gainage": "plank",
                "planche": "plank",
                "cable_woodchop": "woodchop",
                "wood_chop": "woodchop",
                # Full body
                "power_clean": "clean",
                "epaule": "clean",
                "power_snatch": "snatch",
                "arrache": "snatch",
                "thrusters": "thruster",
                "kb_swing": "kettlebell_swing",
                "kettlebell_swings": "kettlebell_swing",
                "battle_ropes": "battle_rope",
            }
            ex_name = _ALIASES.get(ex_name, ex_name)

            try:
                exercise = Exercise(ex_name)
            except ValueError:
                logger.warning("Vision returned unknown exercise name: %s", ex_name)
                exercise = Exercise.UNKNOWN
            
            rep_count = int(data.get("rep_count", 0))
            result = (
                exercise,
                float(data.get("confidence", 0.5)),
                data.get("reasoning", ""),
                rep_count,
            )
            logger.info("Vision parsed: %s (conf=%.2f, reps=%d)", exercise.value, result[1], rep_count)
            return result

        logger.warning("Vision response not parseable: %s", content[:200])
        return Exercise.UNKNOWN, 0.0, "Reponse non parseable: {}".format(content[:100]), 0

    except Exception as e:
        logger.exception("Vision detection failed")
        return Exercise.UNKNOWN, 0.0, "Erreur GPT-4 Vision: {}".format(str(e)), 0


def detect_exercise(
    angles: AngleResult,
    mid_frame_path: str | None = None,
    use_vision_backup: bool = True,
    start_frame_path: str | None = None,
    end_frame_path: str | None = None,
) -> DetectionResult:
    """Détecte l'exercice — VISION-FIRST, pattern matching en backup.

    Architecture :
    1. GPT-4o Vision identifie l'exercice sur 3 frames (primaire)
    2. Pattern matching par angles (backup si vision échoue)
    3. Si les deux sont d'accord → haute confiance

    Args:
        angles: Résultat du calcul d'angles.
        mid_frame_path: Chemin vers l'image de la frame du milieu.
        use_vision_backup: Activer la vision (désactiver uniquement pour tests).
        start_frame_path: Chemin vers la frame de debut (optionnel).
        end_frame_path: Chemin vers la frame de fin (optionnel).

    Returns:
        DetectionResult avec l'exercice détecté et les métadonnées.
    """
    pattern_result = detect_by_pattern(angles)
    logger.info(
        "Pattern detection: %s (conf=%.2f) — %s",
        pattern_result.exercise.value, pattern_result.confidence, pattern_result.reasoning,
    )

    # ── Vision-first : GPT-4o est meilleur pour identifier visuellement ──
    if use_vision_backup and mid_frame_path:
        vision_result = detect_by_vision(
            mid_frame_path,
            start_frame_path=start_frame_path,
            end_frame_path=end_frame_path,
            pattern_result=pattern_result,
        )
        vision_ex, vision_conf, vision_reason = vision_result[0], vision_result[1], vision_result[2]
        vision_reps = vision_result[3] if len(vision_result) > 3 else 0
        logger.info(
            "Vision detection: %s (conf=%.2f, reps=%d) — %s",
            vision_ex.value, vision_conf, vision_reps, vision_reason,
        )

        if vision_ex != Exercise.UNKNOWN and vision_conf >= 0.4:
            # Vision a identifié quelque chose
            if vision_ex == pattern_result.exercise:
                # Accord vision + pattern → haute confiance
                return DetectionResult(
                    exercise=vision_ex,
                    confidence=min(1.0, vision_conf + 0.2),
                    reasoning="[Vision + Pattern d'accord] {}".format(vision_reason),
                    vision_exercise=vision_ex,
                    vision_confidence=vision_conf,
                    vision_rep_count=vision_reps,
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
                    reasoning="[Vision] {} (pattern suggerait: {})".format(vision_reason, pattern_result.exercise.value),
                    vision_exercise=vision_ex,
                    vision_confidence=vision_conf,
                    vision_rep_count=vision_reps,
                )

    # ── Fallback : pattern matching seul (pas d'image ou vision a échoué) ──
    return pattern_result
