"""Exercise Phase Database — Surgical mapping of each exercise's movement phases.

For each exercise, defines:
- Which MediaPipe landmark(s) to track for key frame detection
- Direction of peak contraction (min_y = top, max_y = bottom)
- Phase descriptions for report labels

This replaces the naive hip_y-for-everything approach with biomechanically
correct landmark tracking per exercise.

MediaPipe landmark indices:
  11=left_shoulder, 12=right_shoulder
  13=left_elbow, 14=right_elbow
  15=left_wrist, 16=right_wrist
  23=left_hip, 24=right_hip
  25=left_knee, 26=right_knee
  27=left_ankle, 28=right_ankle
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ExercisePhase:
    """Defines how to detect key frames for an exercise."""
    # MediaPipe landmark indices to track (averaged if multiple)
    tracking_landmarks: tuple[int, ...]
    # Direction of peak contraction in image Y coordinates:
    #   "min_y" = landmark goes UP (e.g. bar at chin in upright row)
    #   "max_y" = landmark goes DOWN (e.g. deep squat)
    peak_direction: Literal["min_y", "max_y"]
    # Human-readable labels
    peak_label: str  # e.g. "Barre au menton"
    return_label: str  # e.g. "Barre en bas"


# Landmark indices
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28

# Average of left+right
HIPS = (L_HIP, R_HIP)
KNEES = (L_KNEE, R_KNEE)
SHOULDERS = (L_SHOULDER, R_SHOULDER)
ELBOWS = (L_ELBOW, R_ELBOW)
WRISTS = (L_WRIST, R_WRIST)


# ═══════════════════════════════════════════════════════════════════════════
# EXERCISE PHASE DATABASE
# ═══════════════════════════════════════════════════════════════════════════

EXERCISE_PHASES: dict[str, ExercisePhase] = {

    # ── SQUAT FAMILY ──────────────────────────────────────────────────────
    # Peak = hips at lowest point (max_y), return = standing
    "squat": ExercisePhase(HIPS, "max_y", "Point bas du squat", "Lockout debout"),
    "front_squat": ExercisePhase(HIPS, "max_y", "Point bas du front squat", "Lockout debout"),
    "goblet_squat": ExercisePhase(HIPS, "max_y", "Point bas", "Lockout debout"),
    "hack_squat": ExercisePhase(HIPS, "max_y", "Point bas", "Lockout"),
    "sissy_squat": ExercisePhase(KNEES, "max_y", "Genoux en avant max", "Retour"),
    "bulgarian_split_squat": ExercisePhase(HIPS, "max_y", "Point bas", "Lockout"),

    # ── LUNGE FAMILY ──────────────────────────────────────────────────────
    "lunge": ExercisePhase(HIPS, "max_y", "Point bas de la fente", "Retour debout"),
    "walking_lunge": ExercisePhase(HIPS, "max_y", "Point bas", "Retour debout"),
    "step_up": ExercisePhase(HIPS, "min_y", "Position haute sur le step", "Pied au sol"),

    # ── DEADLIFT FAMILY ───────────────────────────────────────────────────
    # Peak = hips lowest (bending over), return = standing tall
    "deadlift": ExercisePhase(HIPS, "max_y", "Barre au sol", "Lockout hanches verouillees"),
    "sumo_deadlift": ExercisePhase(HIPS, "max_y", "Barre au sol", "Lockout"),
    "trap_bar_deadlift": ExercisePhase(HIPS, "max_y", "Point bas", "Lockout"),
    "rdl": ExercisePhase(HIPS, "max_y", "Stretch ischio max", "Lockout hanches"),
    "single_leg_rdl": ExercisePhase(HIPS, "max_y", "Stretch max", "Retour debout"),
    "good_morning": ExercisePhase(HIPS, "max_y", "Flexion max", "Retour"),
    "kettlebell_swing": ExercisePhase(WRISTS, "min_y", "Kettlebell en haut", "Kettlebell entre les jambes"),

    # ── HIP THRUST / GLUTE ────────────────────────────────────────────────
    # Peak = hips at HIGHEST point (min_y), return = hips down
    "hip_thrust": ExercisePhase(HIPS, "min_y", "Extension de hanche max", "Retour bas"),
    "glute_bridge": ExercisePhase(HIPS, "min_y", "Extension max", "Retour bas"),
    "cable_kickback": ExercisePhase(L_ANKLE, "min_y", "Extension max", "Retour"),
    "glute_ham_raise": ExercisePhase(SHOULDERS, "max_y", "Point bas", "Retour haut"),

    # ── LEG MACHINES ──────────────────────────────────────────────────────
    "leg_press": ExercisePhase(KNEES, "max_y", "Genoux flechis max", "Extension"),
    "leg_extension": ExercisePhase(L_ANKLE, "min_y", "Jambes tendues", "Retour"),
    "leg_curl": ExercisePhase(L_ANKLE, "min_y", "Talons aux fessiers", "Retour"),

    # ── BENCH PRESS FAMILY ────────────────────────────────────────────────
    # Peak = bar at chest (elbows low = max_y), return = arms extended
    "bench_press": ExercisePhase(ELBOWS, "max_y", "Barre sur la poitrine", "Lockout bras tendus"),
    "incline_bench": ExercisePhase(ELBOWS, "max_y", "Barre sur le haut pec", "Lockout"),
    "decline_bench": ExercisePhase(ELBOWS, "max_y", "Barre sur le bas pec", "Lockout"),
    "dumbbell_bench": ExercisePhase(ELBOWS, "max_y", "Halteres en bas", "Lockout"),
    "dumbbell_incline": ExercisePhase(ELBOWS, "max_y", "Halteres en bas", "Lockout"),
    "close_grip_bench": ExercisePhase(ELBOWS, "max_y", "Barre en bas", "Lockout"),
    "machine_chest_press": ExercisePhase(ELBOWS, "max_y", "Poignees en arriere", "Extension"),

    # ── OVERHEAD PRESS FAMILY ─────────────────────────────────────────────
    # Peak = bar overhead (wrists high = min_y), return = bar at shoulders
    "ohp": ExercisePhase(WRISTS, "min_y", "Barre au-dessus de la tete", "Barre aux epaules"),
    "dumbbell_ohp": ExercisePhase(WRISTS, "min_y", "Halteres au-dessus", "Halteres aux epaules"),
    "arnold_press": ExercisePhase(WRISTS, "min_y", "Halteres au-dessus", "Rotation en bas"),
    "landmine_press": ExercisePhase(WRISTS, "min_y", "Barre en haut", "Barre a l'epaule"),

    # ── PUSH-UP / DIP ─────────────────────────────────────────────────────
    "push_up": ExercisePhase(SHOULDERS, "max_y", "Poitrine au sol", "Bras tendus"),
    "diamond_pushup": ExercisePhase(SHOULDERS, "max_y", "Poitrine au sol", "Bras tendus"),
    "dip": ExercisePhase(SHOULDERS, "max_y", "Point bas", "Lockout bras tendus"),
    "chest_dip": ExercisePhase(SHOULDERS, "max_y", "Point bas", "Lockout"),

    # ── CURL FAMILY ───────────────────────────────────────────────────────
    # Peak = wrists at shoulder level (min_y), return = arms extended
    "curl": ExercisePhase(WRISTS, "min_y", "Contraction biceps max", "Bras tendus"),
    "dumbbell_curl": ExercisePhase(WRISTS, "min_y", "Contraction max", "Bras tendus"),
    "hammer_curl": ExercisePhase(WRISTS, "min_y", "Contraction max", "Bras tendus"),
    "preacher_curl": ExercisePhase(WRISTS, "min_y", "Contraction max", "Bras tendus"),
    "cable_curl": ExercisePhase(WRISTS, "min_y", "Contraction max", "Bras tendus"),
    "incline_curl": ExercisePhase(WRISTS, "min_y", "Contraction max", "Bras tendus en arriere"),
    "concentration_curl": ExercisePhase(WRISTS, "min_y", "Contraction max", "Bras tendu"),
    "spider_curl": ExercisePhase(WRISTS, "min_y", "Contraction max", "Bras tendus"),

    # ── TRICEP FAMILY ─────────────────────────────────────────────────────
    # Varies by exercise
    "tricep_extension": ExercisePhase(WRISTS, "max_y", "Bras flechis max", "Extension complete"),
    "skull_crusher": ExercisePhase(WRISTS, "max_y", "Barre au front", "Bras tendus"),
    "overhead_tricep": ExercisePhase(WRISTS, "max_y", "Etirement max derriere la tete", "Extension"),
    "kickback": ExercisePhase(WRISTS, "min_y", "Bras tendu derriere", "Bras flechi"),
    "cable_overhead_tricep": ExercisePhase(WRISTS, "max_y", "Etirement max", "Extension"),

    # ── ROW FAMILY ────────────────────────────────────────────────────────
    # Peak = elbows pulled back (wrists near torso), return = arms extended
    "barbell_row": ExercisePhase(ELBOWS, "min_y", "Barre au torse", "Bras tendus"),
    "dumbbell_row": ExercisePhase(ELBOWS, "min_y", "Haltere au torse", "Bras tendu"),
    "pendlay_row": ExercisePhase(ELBOWS, "min_y", "Barre au torse", "Barre au sol"),
    "cable_row": ExercisePhase(ELBOWS, "min_y", "Poignee au torse", "Bras tendus"),
    "tbar_row": ExercisePhase(ELBOWS, "min_y", "Barre au torse", "Bras tendus"),
    "seal_row": ExercisePhase(ELBOWS, "min_y", "Barre au banc", "Bras tendus"),

    # ── PULL-UP / LAT PULLDOWN ────────────────────────────────────────────
    # Peak = chin above bar / bar at chest (shoulders low/elbows back)
    "pullup": ExercisePhase(SHOULDERS, "min_y", "Menton au-dessus de la barre", "Bras tendus"),
    "chinup": ExercisePhase(SHOULDERS, "min_y", "Menton au-dessus", "Bras tendus"),
    "lat_pulldown": ExercisePhase(WRISTS, "max_y", "Barre a la poitrine", "Bras tendus en haut"),
    "close_grip_pulldown": ExercisePhase(WRISTS, "max_y", "Barre a la poitrine", "Bras tendus"),

    # ── SHOULDER RAISES / FLYES ───────────────────────────────────────────
    # Peak = arms raised (wrists high = min_y)
    "lateral_raise": ExercisePhase(WRISTS, "min_y", "Bras a l'horizontale", "Bras le long du corps"),
    "cable_lateral_raise": ExercisePhase(WRISTS, "min_y", "Bras a l'horizontale", "Bras en bas"),
    "front_raise": ExercisePhase(WRISTS, "min_y", "Bras a l'horizontale devant", "Bras en bas"),
    "face_pull": ExercisePhase(WRISTS, "min_y", "Mains aux oreilles", "Bras tendus devant"),
    "reverse_fly": ExercisePhase(WRISTS, "min_y", "Bras ouverts", "Bras devant"),  # Tricky - horizontal
    "rear_delt_fly": ExercisePhase(WRISTS, "min_y", "Bras ouverts", "Bras devant"),
    "lu_raise": ExercisePhase(WRISTS, "min_y", "Bras en Y", "Bras en bas"),

    # ── UPRIGHT ROW / SHRUG ───────────────────────────────────────────────
    "upright_row": ExercisePhase(WRISTS, "min_y", "Barre au menton coudes hauts", "Barre en bas bras tendus"),
    "shrug": ExercisePhase(SHOULDERS, "min_y", "Epaules aux oreilles", "Epaules relachees"),

    # ── CHEST FLY / CABLE ─────────────────────────────────────────────────
    "chest_fly": ExercisePhase(WRISTS, "min_y", "Mains jointes au-dessus", "Bras ouverts"),
    "cable_crossover": ExercisePhase(WRISTS, "max_y", "Mains jointes en bas", "Bras ouverts en haut"),
    "cable_pullover": ExercisePhase(WRISTS, "max_y", "Bras en bas", "Bras en haut"),
    "pullover": ExercisePhase(WRISTS, "max_y", "Haltere derriere la tete", "Haltere au-dessus"),
    "svend_press": ExercisePhase(WRISTS, "min_y", "Bras tendus devant", "Mains a la poitrine"),

    # ── CALVES ────────────────────────────────────────────────────────────
    "calf_raise": ExercisePhase(HIPS, "min_y", "Sur la pointe des pieds", "Talons au sol"),
    "seated_calf_raise": ExercisePhase(KNEES, "min_y", "Sur la pointe", "Talons baisses"),

    # ── CORE ──────────────────────────────────────────────────────────────
    "crunch": ExercisePhase(SHOULDERS, "max_y", "Contraction abdos max", "Dos au sol"),
    "cable_crunch": ExercisePhase(SHOULDERS, "max_y", "Flexion max", "Retour"),
    "hanging_leg_raise": ExercisePhase(L_ANKLE, "min_y", "Jambes a l'horizontale", "Jambes en bas"),
    "ab_wheel": ExercisePhase(SHOULDERS, "max_y", "Extension max", "Retour"),
    "woodchop": ExercisePhase(WRISTS, "max_y", "Rotation basse", "Rotation haute"),

    # ── NORDIC / GHR ──────────────────────────────────────────────────────
    "nordic_curl": ExercisePhase(SHOULDERS, "max_y", "Poitrine au sol", "Retour vertical"),

    # ── OLYMPIC / FULL BODY ───────────────────────────────────────────────
    "clean": ExercisePhase(WRISTS, "min_y", "Barre aux epaules", "Barre au sol"),
    "snatch": ExercisePhase(WRISTS, "min_y", "Barre au-dessus", "Barre au sol"),
    "thruster": ExercisePhase(WRISTS, "min_y", "Barre au-dessus", "Barre aux epaules + squat"),
    "battle_rope": ExercisePhase(WRISTS, "min_y", "Bras en haut", "Bras en bas"),
}


def get_phase(exercise: str) -> ExercisePhase | None:
    """Get the phase definition for an exercise."""
    return EXERCISE_PHASES.get(exercise)


def get_tracking_y(
    landmarks: list[dict[str, float]],
    phase: ExercisePhase,
) -> float:
    """Get the Y position of the tracked landmark(s) for an exercise.
    
    Averages Y of all tracking landmarks (e.g. left+right wrist).
    """
    y_vals = []
    indices = phase.tracking_landmarks
    # Handle single int (e.g. L_ANKLE = 27) vs tuple
    if isinstance(indices, int):
        indices = (indices,)
    for idx in indices:
        if idx < len(landmarks):
            vis = landmarks[idx].get("visibility", 0.0)
            if vis > 0.1:
                y_vals.append(landmarks[idx]["y"])
    if y_vals:
        return sum(y_vals) / len(y_vals)
    return 0.5  # default center if not visible
