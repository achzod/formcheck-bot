"""Analyse biomécanique — bras de levier, anthropométrie, sticking point, lockout, depth, séquençage, tête/cou, distribution du poids.

Module complémentaire à biomechanics_advanced.py.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from analysis.pose_extractor import ExtractionResult, FrameLandmarks
from analysis.angle_calculator import AngleResult, FrameAngles
from analysis.rep_segmenter import RepSegmentation, Rep

logger = logging.getLogger("formcheck.biomechanics_levers")

# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_landmark(landmarks: list[dict], name: str) -> dict | None:
    for lm in landmarks:
        if lm["name"] == name:
            return lm
    return None


def _distance_2d(a: dict, b: dict) -> float:
    return math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2)


def _mid_point(a: dict, b: dict) -> dict:
    return {
        "x": (a["x"] + b["x"]) / 2,
        "y": (a["y"] + b["y"]) / 2,
        "z": (a.get("z", 0) + b.get("z", 0)) / 2,
    }


def _safe_div(num: float, den: float, default: float = 0.0) -> float:
    return num / den if abs(den) > 1e-9 else default


def _standing_frame(extraction: ExtractionResult) -> FrameLandmarks | None:
    """Frame la plus 'debout' — hauteur hanche-cheville maximale."""
    best: FrameLandmarks | None = None
    best_h = -1.0
    for f in extraction.frames:
        lh = _get_landmark(f.landmarks, "left_hip")
        rh = _get_landmark(f.landmarks, "right_hip")
        la = _get_landmark(f.landmarks, "left_ankle")
        ra = _get_landmark(f.landmarks, "right_ankle")
        if not all([lh, rh, la, ra]):
            continue
        mid_hip_y = (lh["y"] + rh["y"]) / 2
        mid_ankle_y = (la["y"] + ra["y"]) / 2
        h = mid_ankle_y - mid_hip_y  # y descend en MediaPipe
        if h > best_h:
            best_h = h
            best = f
    return best


def _estimate_standing_height(landmarks: list[dict]) -> float:
    """Hauteur approximative du sujet (nose → mid_ankle) en coords normalisées."""
    nose = _get_landmark(landmarks, "nose")
    la = _get_landmark(landmarks, "left_ankle")
    ra = _get_landmark(landmarks, "right_ankle")
    if not nose or not (la or ra):
        return 1.0  # fallback
    ankle_y = la["y"] if la else ra["y"]
    if la and ra:
        ankle_y = (la["y"] + ra["y"]) / 2
    h = abs(ankle_y - nose["y"])
    return max(h, 0.01)


def _frame_index_to_angle_map(angles: AngleResult) -> dict[int, FrameAngles]:
    return {fa.frame_index: fa for fa in angles.frames}


def _get_primary_angle_attr(exercise: str) -> tuple[str, str]:
    """Return (knee_attr, hip_attr) for the exercise."""
    return "left_knee_flexion", "left_hip_flexion"


# ── Dataclasses ──────────────────────────────────────────────────────────────


@dataclass
class LeverArmMetrics:
    left_knee_lever_per_frame: list[float] = field(default_factory=list)
    right_knee_lever_per_frame: list[float] = field(default_factory=list)
    max_knee_lever_left: float = 0.0
    max_knee_lever_right: float = 0.0
    left_hip_lever_per_frame: list[float] = field(default_factory=list)
    right_hip_lever_per_frame: list[float] = field(default_factory=list)
    max_hip_lever_left: float = 0.0
    max_hip_lever_right: float = 0.0
    spine_lever_per_frame: list[float] = field(default_factory=list)
    max_spine_lever: float = 0.0
    dominant_joint: str = "genou"
    knee_hip_lever_ratio: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_knee_lever_per_frame": [round(v, 4) for v in self.left_knee_lever_per_frame],
            "right_knee_lever_per_frame": [round(v, 4) for v in self.right_knee_lever_per_frame],
            "max_knee_lever_left": round(self.max_knee_lever_left, 4),
            "max_knee_lever_right": round(self.max_knee_lever_right, 4),
            "left_hip_lever_per_frame": [round(v, 4) for v in self.left_hip_lever_per_frame],
            "right_hip_lever_per_frame": [round(v, 4) for v in self.right_hip_lever_per_frame],
            "max_hip_lever_left": round(self.max_hip_lever_left, 4),
            "max_hip_lever_right": round(self.max_hip_lever_right, 4),
            "spine_lever_per_frame": [round(v, 4) for v in self.spine_lever_per_frame],
            "max_spine_lever": round(self.max_spine_lever, 4),
            "dominant_joint": self.dominant_joint,
            "knee_hip_lever_ratio": round(self.knee_hip_lever_ratio, 3),
        }


@dataclass
class AnthropometricAnalysis:
    femur_length: float = 0.0
    tibia_length: float = 0.0
    torso_length: float = 0.0
    upper_arm_length: float = 0.0
    forearm_length: float = 0.0
    shoulder_width: float = 0.0
    hip_width: float = 0.0
    femur_tibia_ratio: float = 1.0
    torso_femur_ratio: float = 1.0
    arm_torso_ratio: float = 1.0
    shoulder_hip_ratio: float = 1.0
    upper_arm_forearm_ratio: float = 1.0
    squat_type: str = "balanced"
    deadlift_type: str = "conventional"
    bench_grip: str = "moyen"
    morphology_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "femur_length": round(self.femur_length, 4),
            "tibia_length": round(self.tibia_length, 4),
            "torso_length": round(self.torso_length, 4),
            "upper_arm_length": round(self.upper_arm_length, 4),
            "forearm_length": round(self.forearm_length, 4),
            "shoulder_width": round(self.shoulder_width, 4),
            "hip_width": round(self.hip_width, 4),
            "femur_tibia_ratio": round(self.femur_tibia_ratio, 3),
            "torso_femur_ratio": round(self.torso_femur_ratio, 3),
            "arm_torso_ratio": round(self.arm_torso_ratio, 3),
            "shoulder_hip_ratio": round(self.shoulder_hip_ratio, 3),
            "upper_arm_forearm_ratio": round(self.upper_arm_forearm_ratio, 3),
            "squat_type": self.squat_type,
            "deadlift_type": self.deadlift_type,
            "bench_grip": self.bench_grip,
            "morphology_note": self.morphology_note,
        }


@dataclass
class StickingPointAnalysis:
    sticking_point_angle: float = 0.0
    sticking_point_frame: int = 0
    sticking_point_depth_pct: float = 0.0
    min_velocity_at_sticking: float = 0.0
    avg_velocity_concentric: float = 0.0
    velocity_ratio: float = 1.0
    sticking_points_per_rep: list[float] = field(default_factory=list)
    sticking_consistency: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "sticking_point_angle": round(self.sticking_point_angle, 1),
            "sticking_point_frame": self.sticking_point_frame,
            "sticking_point_depth_pct": round(self.sticking_point_depth_pct, 1),
            "min_velocity_at_sticking": round(self.min_velocity_at_sticking, 1),
            "avg_velocity_concentric": round(self.avg_velocity_concentric, 1),
            "velocity_ratio": round(self.velocity_ratio, 3),
            "sticking_points_per_rep": [round(v, 1) for v in self.sticking_points_per_rep],
            "sticking_consistency": round(self.sticking_consistency, 3),
        }


@dataclass
class LockoutAnalysis:
    left_knee_at_top: float = 0.0
    right_knee_at_top: float = 0.0
    knee_lockout_complete: bool = False
    knee_hyperextension: bool = False
    left_hip_at_top: float = 0.0
    right_hip_at_top: float = 0.0
    hip_lockout_complete: bool = False
    left_shoulder_at_top: float = 0.0
    right_shoulder_at_top: float = 0.0
    overhead_lockout_complete: bool = False
    lockout_consistency: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_knee_at_top": round(self.left_knee_at_top, 1),
            "right_knee_at_top": round(self.right_knee_at_top, 1),
            "knee_lockout_complete": self.knee_lockout_complete,
            "knee_hyperextension": self.knee_hyperextension,
            "left_hip_at_top": round(self.left_hip_at_top, 1),
            "right_hip_at_top": round(self.right_hip_at_top, 1),
            "hip_lockout_complete": self.hip_lockout_complete,
            "left_shoulder_at_top": round(self.left_shoulder_at_top, 1),
            "right_shoulder_at_top": round(self.right_shoulder_at_top, 1),
            "overhead_lockout_complete": self.overhead_lockout_complete,
            "lockout_consistency": round(self.lockout_consistency, 3),
        }


@dataclass
class DepthAnalysis:
    hip_below_knee: bool = False
    depth_margin: float = 0.0
    deepest_frame: int = 0
    depth_per_rep: list[float] = field(default_factory=list)
    depth_consistency: float = 0.0
    max_knee_flexion: float = 0.0
    max_hip_flexion: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hip_below_knee": self.hip_below_knee,
            "depth_margin": round(self.depth_margin, 2),
            "deepest_frame": self.deepest_frame,
            "depth_per_rep": [round(v, 2) for v in self.depth_per_rep],
            "depth_consistency": round(self.depth_consistency, 3),
            "max_knee_flexion": round(self.max_knee_flexion, 1),
            "max_hip_flexion": round(self.max_hip_flexion, 1),
        }


@dataclass
class MovementSequencing:
    knee_rate_per_frame: list[float] = field(default_factory=list)
    hip_rate_per_frame: list[float] = field(default_factory=list)
    knee_hip_rate_ratio: list[float] = field(default_factory=list)
    avg_knee_rate_concentric: float = 0.0
    avg_hip_rate_concentric: float = 0.0
    sequencing_ratio: float = 1.0
    pattern: str = "synchronise"
    pattern_severity: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "knee_rate_per_frame": [round(v, 1) for v in self.knee_rate_per_frame],
            "hip_rate_per_frame": [round(v, 1) for v in self.hip_rate_per_frame],
            "knee_hip_rate_ratio": [round(v, 3) for v in self.knee_hip_rate_ratio],
            "avg_knee_rate_concentric": round(self.avg_knee_rate_concentric, 1),
            "avg_hip_rate_concentric": round(self.avg_hip_rate_concentric, 1),
            "sequencing_ratio": round(self.sequencing_ratio, 3),
            "pattern": self.pattern,
            "pattern_severity": round(self.pattern_severity, 3),
        }


@dataclass
class HeadNeckAnalysis:
    forward_head_distance: float = 0.0
    forward_head_per_frame: list[float] = field(default_factory=list)
    cervical_angle_per_frame: list[float] = field(default_factory=list)
    max_cervical_extension: float = 0.0
    cervical_neutral: bool = True
    head_stability: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "forward_head_distance": round(self.forward_head_distance, 4),
            "forward_head_per_frame": [round(v, 4) for v in self.forward_head_per_frame],
            "cervical_angle_per_frame": [round(v, 1) for v in self.cervical_angle_per_frame],
            "max_cervical_extension": round(self.max_cervical_extension, 1),
            "cervical_neutral": self.cervical_neutral,
            "head_stability": round(self.head_stability, 3),
        }


@dataclass
class WeightDistribution:
    heel_rise_detected: bool = False
    heel_rise_frames: list[int] = field(default_factory=list)
    heel_rise_magnitude: float = 0.0
    weight_anterior_pct: float = 50.0
    weight_posterior_pct: float = 50.0
    weight_left_pct: float = 50.0
    weight_right_pct: float = 50.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "heel_rise_detected": self.heel_rise_detected,
            "heel_rise_frames": self.heel_rise_frames,
            "heel_rise_magnitude": round(self.heel_rise_magnitude, 4),
            "weight_anterior_pct": round(self.weight_anterior_pct, 1),
            "weight_posterior_pct": round(self.weight_posterior_pct, 1),
            "weight_left_pct": round(self.weight_left_pct, 1),
            "weight_right_pct": round(self.weight_right_pct, 1),
        }


@dataclass
class LeverBiomechanics:
    levers: LeverArmMetrics = field(default_factory=LeverArmMetrics)
    anthropometry: AnthropometricAnalysis = field(default_factory=AnthropometricAnalysis)
    sticking_point: StickingPointAnalysis = field(default_factory=StickingPointAnalysis)
    lockout: LockoutAnalysis = field(default_factory=LockoutAnalysis)
    depth: DepthAnalysis | None = None
    sequencing: MovementSequencing = field(default_factory=MovementSequencing)
    head_neck: HeadNeckAnalysis = field(default_factory=HeadNeckAnalysis)
    weight_distribution: WeightDistribution = field(default_factory=WeightDistribution)

    def to_dict(self) -> dict[str, Any]:
        return {
            "levers": self.levers.to_dict(),
            "anthropometry": self.anthropometry.to_dict(),
            "sticking_point": self.sticking_point.to_dict(),
            "lockout": self.lockout.to_dict(),
            "depth": self.depth.to_dict() if self.depth else None,
            "sequencing": self.sequencing.to_dict(),
            "head_neck": self.head_neck.to_dict(),
            "weight_distribution": self.weight_distribution.to_dict(),
        }


# ── Compute functions ────────────────────────────────────────────────────────


def _compute_levers(extraction: ExtractionResult) -> LeverArmMetrics:
    m = LeverArmMetrics()
    for f in extraction.frames:
        lms = f.landmarks
        height = _estimate_standing_height(lms)

        # Knee levers
        lk = _get_landmark(lms, "left_knee")
        rk = _get_landmark(lms, "right_knee")
        la = _get_landmark(lms, "left_ankle")
        ra = _get_landmark(lms, "right_ankle")

        lk_lever = _safe_div(abs(lk["x"] - la["x"]), height) if lk and la else 0.0
        rk_lever = _safe_div(abs(rk["x"] - ra["x"]), height) if rk and ra else 0.0
        m.left_knee_lever_per_frame.append(lk_lever)
        m.right_knee_lever_per_frame.append(rk_lever)

        # Hip levers — distance horizontale hanche vs milieu des pieds
        lh = _get_landmark(lms, "left_hip")
        rh = _get_landmark(lms, "right_hip")
        lfi = _get_landmark(lms, "left_foot_index")
        rfi = _get_landmark(lms, "right_foot_index")
        lheel = _get_landmark(lms, "left_heel")
        rheel = _get_landmark(lms, "right_heel")

        mid_foot_x = 0.5
        foot_pts = [p for p in [la, ra, lfi, rfi, lheel, rheel] if p]
        if foot_pts:
            mid_foot_x = sum(p["x"] for p in foot_pts) / len(foot_pts)

        lh_lever = _safe_div(abs(lh["x"] - mid_foot_x), height) if lh else 0.0
        rh_lever = _safe_div(abs(rh["x"] - mid_foot_x), height) if rh else 0.0
        m.left_hip_lever_per_frame.append(lh_lever)
        m.right_hip_lever_per_frame.append(rh_lever)

        # Spine lever
        ls = _get_landmark(lms, "left_shoulder")
        rs = _get_landmark(lms, "right_shoulder")
        if ls and rs and lh and rh:
            mid_sh_x = (ls["x"] + rs["x"]) / 2
            mid_hip_x = (lh["x"] + rh["x"]) / 2
            sp_lever = _safe_div(abs(mid_sh_x - mid_hip_x), height)
        else:
            sp_lever = 0.0
        m.spine_lever_per_frame.append(sp_lever)

    m.max_knee_lever_left = max(m.left_knee_lever_per_frame) if m.left_knee_lever_per_frame else 0.0
    m.max_knee_lever_right = max(m.right_knee_lever_per_frame) if m.right_knee_lever_per_frame else 0.0
    m.max_hip_lever_left = max(m.left_hip_lever_per_frame) if m.left_hip_lever_per_frame else 0.0
    m.max_hip_lever_right = max(m.right_hip_lever_per_frame) if m.right_hip_lever_per_frame else 0.0
    m.max_spine_lever = max(m.spine_lever_per_frame) if m.spine_lever_per_frame else 0.0

    avg_knee = (m.max_knee_lever_left + m.max_knee_lever_right) / 2
    avg_hip = (m.max_hip_lever_left + m.max_hip_lever_right) / 2
    m.knee_hip_lever_ratio = _safe_div(avg_knee, avg_hip, 1.0)

    max_vals = {"genou": avg_knee, "hanche": avg_hip, "rachis": m.max_spine_lever}
    m.dominant_joint = max(max_vals, key=max_vals.get)  # type: ignore[arg-type]

    return m


def _compute_anthropometry(extraction: ExtractionResult) -> AnthropometricAnalysis:
    a = AnthropometricAnalysis()
    sf = _standing_frame(extraction)
    if sf is None:
        a.morphology_note = "Impossible d'estimer la morphologie — aucune frame debout détectée."
        return a

    lms = sf.landmarks
    height = _estimate_standing_height(lms)

    lh = _get_landmark(lms, "left_hip")
    rh = _get_landmark(lms, "right_hip")
    lk = _get_landmark(lms, "left_knee")
    rk = _get_landmark(lms, "right_knee")
    la = _get_landmark(lms, "left_ankle")
    ra = _get_landmark(lms, "right_ankle")
    ls = _get_landmark(lms, "left_shoulder")
    rs = _get_landmark(lms, "right_shoulder")
    le = _get_landmark(lms, "left_elbow")
    re = _get_landmark(lms, "right_elbow")
    lw = _get_landmark(lms, "left_wrist")
    rw = _get_landmark(lms, "right_wrist")

    def avg_dist(a1: dict | None, a2: dict | None, b1: dict | None, b2: dict | None) -> float:
        dists = []
        if a1 and b1:
            dists.append(_distance_2d(a1, b1))
        if a2 and b2:
            dists.append(_distance_2d(a2, b2))
        return (sum(dists) / len(dists)) if dists else 0.0

    femur_raw = avg_dist(lh, rh, lk, rk)
    tibia_raw = avg_dist(lk, rk, la, ra)
    upper_arm_raw = avg_dist(ls, rs, le, re)
    forearm_raw = avg_dist(le, re, lw, rw)

    # Torso = mid_hip → mid_shoulder
    if lh and rh and ls and rs:
        mid_hip = _mid_point(lh, rh)
        mid_sh = _mid_point(ls, rs)
        torso_raw = _distance_2d(mid_hip, mid_sh)
    else:
        torso_raw = 0.0

    a.femur_length = _safe_div(femur_raw, height)
    a.tibia_length = _safe_div(tibia_raw, height)
    a.torso_length = _safe_div(torso_raw, height)
    a.upper_arm_length = _safe_div(upper_arm_raw, height)
    a.forearm_length = _safe_div(forearm_raw, height)

    # Shoulder width
    if ls and rs:
        a.shoulder_width = _safe_div(_distance_2d(ls, rs), height)
    # Hip width
    if lh and rh:
        a.hip_width = _safe_div(_distance_2d(lh, rh), height)

    a.femur_tibia_ratio = _safe_div(a.femur_length, a.tibia_length, 1.0)
    a.torso_femur_ratio = _safe_div(a.torso_length, a.femur_length, 1.0)
    total_arm = a.upper_arm_length + a.forearm_length
    a.arm_torso_ratio = _safe_div(total_arm, a.torso_length, 1.0)
    a.shoulder_hip_ratio = _safe_div(a.shoulder_width, a.hip_width, 1.0)
    a.upper_arm_forearm_ratio = _safe_div(a.upper_arm_length, a.forearm_length, 1.0)

    # Deadlift type
    if a.hip_width > 0.19 and a.femur_tibia_ratio < 1.05:
        a.deadlift_type = "sumo"
    else:
        a.deadlift_type = "conventional"

    # Bench grip
    if a.shoulder_width > 0.24:
        a.bench_grip = "large"
    elif a.shoulder_width < 0.2:
        a.bench_grip = "etroit"
    else:
        a.bench_grip = "moyen"

    # Interprétation
    if a.femur_tibia_ratio > 1.1 and a.torso_femur_ratio < 0.95:
        a.squat_type = "hip_dominant"
        a.morphology_note = (
            "Fémur long avec torse court — inclinaison du tronc naturellement "
            "plus prononcée. Ce n'est pas une erreur technique mais une adaptation morphologique."
        )
    elif a.torso_femur_ratio > 1.1:
        a.squat_type = "quad_dominant"
        a.morphology_note = (
            "Torse long par rapport au fémur — position de squat plus verticale naturellement. "
            "Avantage pour le squat, facilite un tronc droit."
        )
    else:
        a.squat_type = "balanced"
        a.morphology_note = "Proportions équilibrées — pas de biais morphologique marqué."

    return a


def _compute_sticking_point(
    angles: AngleResult,
    reps: RepSegmentation,
    exercise: str,
    fps: float,
) -> StickingPointAnalysis:
    sp = StickingPointAnalysis()
    if not reps.reps:
        return sp

    knee_attr, hip_attr = _get_primary_angle_attr(exercise)
    # Choose primary angle based on exercise
    primary_attr = hip_attr if exercise in ("deadlift", "rdl", "hip_thrust") else knee_attr

    angle_map = _frame_index_to_angle_map(angles)
    all_sp_angles: list[float] = []

    global_min_vel = float("inf")
    global_sp_angle = 0.0
    global_sp_frame = 0
    total_conc_vel: list[float] = []

    for rep in reps.reps:
        conc_start, conc_end = rep.concentric_frames
        # Collect angles in concentric phase
        conc_angles: list[tuple[int, float]] = []
        for fa in angles.frames:
            if conc_start <= fa.frame_index <= conc_end:
                val = getattr(fa, primary_attr, None)
                if val is not None:
                    conc_angles.append((fa.frame_index, val))

        if len(conc_angles) < 3:
            continue

        # Angular velocity (°/frame → °/s)
        velocities: list[float] = []
        for i in range(1, len(conc_angles)):
            dt_frames = conc_angles[i][0] - conc_angles[i - 1][0]
            if dt_frames == 0:
                dt_frames = 1
            vel = abs(conc_angles[i][1] - conc_angles[i - 1][1]) / dt_frames * fps
            velocities.append(vel)

        if not velocities:
            continue

        total_conc_vel.extend(velocities)

        # Skip first/last 10% to avoid transition artifacts
        margin = max(1, len(velocities) // 10)
        search = velocities[margin: len(velocities) - margin] if len(velocities) > 2 * margin else velocities
        if not search:
            search = velocities

        local_min_idx = int(np.argmin(search)) + margin if len(velocities) > 2 * margin else int(np.argmin(search))
        local_min_vel = velocities[local_min_idx] if local_min_idx < len(velocities) else velocities[0]

        # Angle at sticking point (index offset +1 because velocity is between frames)
        sp_idx = min(local_min_idx + 1, len(conc_angles) - 1)
        sp_angle = conc_angles[sp_idx][1]
        all_sp_angles.append(sp_angle)

        if local_min_vel < global_min_vel:
            global_min_vel = local_min_vel
            global_sp_angle = sp_angle
            global_sp_frame = conc_angles[sp_idx][0]

    sp.sticking_point_angle = global_sp_angle
    sp.sticking_point_frame = global_sp_frame
    sp.min_velocity_at_sticking = global_min_vel if global_min_vel != float("inf") else 0.0
    sp.avg_velocity_concentric = float(np.mean(total_conc_vel)) if total_conc_vel else 0.0
    sp.velocity_ratio = _safe_div(sp.min_velocity_at_sticking, sp.avg_velocity_concentric, 1.0)
    sp.sticking_points_per_rep = all_sp_angles

    # Depth % of ROM at sticking point
    if reps.reps:
        first_rep = reps.reps[0]
        rom = first_rep.rom
        if rom > 0 and all_sp_angles:
            # Approximate: sticking_point_angle relative to bottom
            bottom_fa = angle_map.get(first_rep.bottom_frame)
            if bottom_fa:
                bottom_val = getattr(bottom_fa, primary_attr, None)
                if bottom_val is not None:
                    sp.sticking_point_depth_pct = min(100.0, max(0.0, _safe_div(abs(global_sp_angle - bottom_val), rom) * 100))

    # Consistency
    if len(all_sp_angles) > 1:
        std = float(np.std(all_sp_angles))
        mean = float(np.mean(all_sp_angles))
        cv = _safe_div(std, mean, 1.0)
        sp.sticking_consistency = max(0.0, min(1.0, 1.0 - cv))

    return sp


def _compute_lockout(
    angles: AngleResult,
    reps: RepSegmentation,
    exercise: str,
) -> LockoutAnalysis:
    lo = LockoutAnalysis()
    if not reps.reps:
        # Use first/last frame as fallback
        if angles.frames:
            fa = angles.frames[-1]
            lo.left_knee_at_top = fa.left_knee_flexion or 0.0
            lo.right_knee_at_top = fa.right_knee_flexion or 0.0
            lo.left_hip_at_top = fa.left_hip_flexion or 0.0
            lo.right_hip_at_top = fa.right_hip_flexion or 0.0
        return lo

    angle_map = _frame_index_to_angle_map(angles)

    knee_tops_l: list[float] = []
    knee_tops_r: list[float] = []
    hip_tops_l: list[float] = []
    hip_tops_r: list[float] = []
    shoulder_tops_l: list[float] = []
    shoulder_tops_r: list[float] = []

    for rep in reps.reps:
        end_fa = angle_map.get(rep.end_frame)
        if not end_fa:
            continue
        if end_fa.left_knee_flexion is not None:
            knee_tops_l.append(end_fa.left_knee_flexion)
        if end_fa.right_knee_flexion is not None:
            knee_tops_r.append(end_fa.right_knee_flexion)
        if end_fa.left_hip_flexion is not None:
            hip_tops_l.append(end_fa.left_hip_flexion)
        if end_fa.right_hip_flexion is not None:
            hip_tops_r.append(end_fa.right_hip_flexion)
        if end_fa.left_shoulder_flexion is not None:
            shoulder_tops_l.append(end_fa.left_shoulder_flexion)
        if end_fa.right_shoulder_flexion is not None:
            shoulder_tops_r.append(end_fa.right_shoulder_flexion)

    lo.left_knee_at_top = float(np.mean(knee_tops_l)) if knee_tops_l else 0.0
    lo.right_knee_at_top = float(np.mean(knee_tops_r)) if knee_tops_r else 0.0
    lo.left_hip_at_top = float(np.mean(hip_tops_l)) if hip_tops_l else 0.0
    lo.right_hip_at_top = float(np.mean(hip_tops_r)) if hip_tops_r else 0.0
    lo.left_shoulder_at_top = float(np.mean(shoulder_tops_l)) if shoulder_tops_l else 0.0
    lo.right_shoulder_at_top = float(np.mean(shoulder_tops_r)) if shoulder_tops_r else 0.0

    avg_knee_top = (lo.left_knee_at_top + lo.right_knee_at_top) / 2
    lo.knee_lockout_complete = avg_knee_top > 165.0
    lo.knee_hyperextension = avg_knee_top > 180.0

    avg_hip_top = (lo.left_hip_at_top + lo.right_hip_at_top) / 2
    lo.hip_lockout_complete = avg_hip_top > 170.0

    avg_shoulder_top = (lo.left_shoulder_at_top + lo.right_shoulder_at_top) / 2
    lo.overhead_lockout_complete = avg_shoulder_top > 165.0

    # Consistency across reps
    all_tops = knee_tops_l + knee_tops_r + hip_tops_l + hip_tops_r
    if len(all_tops) > 1:
        std = float(np.std(all_tops))
        mean = float(np.mean(all_tops))
        cv = _safe_div(std, mean, 1.0)
        lo.lockout_consistency = max(0.0, min(1.0, 1.0 - cv))

    return lo


def _compute_depth(
    extraction: ExtractionResult,
    angles: AngleResult,
    reps: RepSegmentation,
    exercise: str,
) -> DepthAnalysis | None:
    squat_exercises = {"squat", "front_squat", "bulgarian_split_squat"}
    if exercise not in squat_exercises:
        return None

    d = DepthAnalysis()
    angle_map = _frame_index_to_angle_map(angles)

    best_margin = -999.0
    best_frame = 0
    rep_margins: list[float] = []

    # Find standing femur length for normalization
    sf = _standing_frame(extraction)
    femur_norm = 1.0
    if sf:
        lh = _get_landmark(sf.landmarks, "left_hip")
        lk = _get_landmark(sf.landmarks, "left_knee")
        if lh and lk:
            femur_norm = max(_distance_2d(lh, lk), 0.01)

    def _depth_at_frame(f: FrameLandmarks) -> float:
        """Positive = below parallel, negative = above."""
        lh = _get_landmark(f.landmarks, "left_hip")
        rh = _get_landmark(f.landmarks, "right_hip")
        lk = _get_landmark(f.landmarks, "left_knee")
        rk = _get_landmark(f.landmarks, "right_knee")
        if not (lh and rh and lk and rk):
            return -999.0
        mid_hip_y = (lh["y"] + rh["y"]) / 2
        mid_knee_y = (lk["y"] + rk["y"]) / 2
        # In MediaPipe, y increases downward → hip_y > knee_y means hip is below knee
        return (mid_hip_y - mid_knee_y) / femur_norm * 100  # % of femur

    # Frame index → FrameLandmarks map
    frame_map = {f.frame_index: f for f in extraction.frames}

    if reps.reps:
        for rep in reps.reps:
            bottom_f = frame_map.get(rep.bottom_frame)
            if bottom_f:
                margin = _depth_at_frame(bottom_f)
                rep_margins.append(margin)
                if margin > best_margin:
                    best_margin = margin
                    best_frame = rep.bottom_frame
    else:
        # No reps — scan all frames
        for f in extraction.frames:
            margin = _depth_at_frame(f)
            if margin > best_margin:
                best_margin = margin
                best_frame = f.frame_index

    d.hip_below_knee = best_margin > 0
    d.depth_margin = best_margin if best_margin > -999.0 else 0.0
    d.deepest_frame = best_frame
    d.depth_per_rep = rep_margins

    if len(rep_margins) > 1:
        std = float(np.std(rep_margins))
        mean_abs = float(np.mean([abs(m) for m in rep_margins]))
        cv = _safe_div(std, mean_abs, 1.0)
        d.depth_consistency = max(0.0, min(1.0, 1.0 - cv))
    elif rep_margins:
        d.depth_consistency = 1.0

    # Max flexion angles
    knee_vals = [fa.left_knee_flexion for fa in angles.frames if fa.left_knee_flexion is not None]
    hip_vals = [fa.left_hip_flexion for fa in angles.frames if fa.left_hip_flexion is not None]
    # For flexion, min angle = max flexion (knee goes from ~180 to ~60 at bottom)
    d.max_knee_flexion = min(knee_vals) if knee_vals else 0.0
    d.max_hip_flexion = min(hip_vals) if hip_vals else 0.0

    return d


def _compute_sequencing(
    angles: AngleResult,
    reps: RepSegmentation,
    exercise: str,
    fps: float,
) -> MovementSequencing:
    seq = MovementSequencing()
    angle_map = _frame_index_to_angle_map(angles)

    # Collect all concentric frames
    conc_knee_rates: list[float] = []
    conc_hip_rates: list[float] = []
    all_ratios: list[float] = []

    prev_knee: float | None = None
    prev_hip: float | None = None
    prev_fi: int | None = None

    # Determine if frame is in concentric phase
    conc_ranges: list[tuple[int, int]] = []
    for rep in reps.reps:
        conc_ranges.append(rep.concentric_frames)

    def _in_concentric(fi: int) -> bool:
        return any(s <= fi <= e for s, e in conc_ranges)

    for fa in angles.frames:
        knee_val = fa.left_knee_flexion
        hip_val = fa.left_hip_flexion

        if knee_val is not None and hip_val is not None and prev_knee is not None and prev_hip is not None and prev_fi is not None:
            dt = (fa.frame_index - prev_fi)
            if dt == 0:
                dt = 1
            kr = (knee_val - prev_knee) / dt * fps
            hr = (hip_val - prev_hip) / dt * fps

            seq.knee_rate_per_frame.append(kr)
            seq.hip_rate_per_frame.append(hr)

            ratio = _safe_div(abs(kr), abs(hr), 1.0) if (abs(kr) > 0.5 or abs(hr) > 0.5) else 1.0
            seq.knee_hip_rate_ratio.append(ratio)

            if _in_concentric(fa.frame_index):
                conc_knee_rates.append(abs(kr))
                conc_hip_rates.append(abs(hr))
                all_ratios.append(ratio)

        prev_knee = knee_val
        prev_hip = hip_val
        prev_fi = fa.frame_index

    seq.avg_knee_rate_concentric = float(np.mean(conc_knee_rates)) if conc_knee_rates else 0.0
    seq.avg_hip_rate_concentric = float(np.mean(conc_hip_rates)) if conc_hip_rates else 0.0
    seq.sequencing_ratio = float(np.mean(all_ratios)) if all_ratios else 1.0

    # Classify pattern
    r = seq.sequencing_ratio
    if 0.7 <= r <= 1.4:
        seq.pattern = "synchronise"
        seq.pattern_severity = max(0.0, (abs(r - 1.0) - 0.1) / 0.3)
    elif r > 1.4:
        seq.pattern = "squat_morning"
        seq.pattern_severity = min(1.0, (r - 1.4) / 1.0)
    else:
        seq.pattern = "good_morning"
        seq.pattern_severity = min(1.0, (0.7 - r) / 0.5)

    seq.pattern_severity = max(0.0, min(1.0, seq.pattern_severity))
    return seq


def _compute_head_neck(extraction: ExtractionResult) -> HeadNeckAnalysis:
    hn = HeadNeckAnalysis()
    fwd_distances: list[float] = []
    cerv_angles: list[float] = []

    for f in extraction.frames:
        lms = f.landmarks
        height = _estimate_standing_height(lms)
        nose = _get_landmark(lms, "nose")
        ls = _get_landmark(lms, "left_shoulder")
        rs = _get_landmark(lms, "right_shoulder")
        le = _get_landmark(lms, "left_ear")
        re = _get_landmark(lms, "right_ear")

        # Forward head distance
        if nose and ls and rs:
            mid_sh_x = (ls["x"] + rs["x"]) / 2
            fwd = _safe_div(nose["x"] - mid_sh_x, height)  # signed: positive = forward (depends on facing)
            fwd_distances.append(fwd)
            hn.forward_head_per_frame.append(fwd)
        else:
            hn.forward_head_per_frame.append(0.0)

        # Cervical angle: ear→shoulder vs vertical
        ear = le or re
        shoulder = ls or rs
        if ear and shoulder:
            dx = ear["x"] - shoulder["x"]
            dy = ear["y"] - shoulder["y"]
            # Angle with vertical (dy is along vertical in MediaPipe, y down)
            angle = math.degrees(math.atan2(abs(dx), abs(dy))) if abs(dy) > 1e-6 else 0.0
            cerv_angles.append(angle)
            hn.cervical_angle_per_frame.append(angle)
        else:
            hn.cervical_angle_per_frame.append(0.0)

    if fwd_distances:
        abs_fwd = [abs(v) for v in fwd_distances]
        hn.forward_head_distance = float(np.mean(abs_fwd))

    if cerv_angles:
        hn.max_cervical_extension = max(cerv_angles)
        hn.cervical_neutral = hn.max_cervical_extension < 15.0

    # Head stability: 1 - normalized std of forward_head
    if len(fwd_distances) > 1:
        std = float(np.std(fwd_distances))
        # Low std = stable
        hn.head_stability = max(0.0, min(1.0, 1.0 - std * 20))  # scale factor

    return hn


def _compute_weight_distribution(extraction: ExtractionResult) -> WeightDistribution:
    wd = WeightDistribution()

    anterior_count = 0
    posterior_count = 0
    left_shifts: list[float] = []
    heel_rise_magnitudes: list[float] = []
    total = 0

    # Baseline heel-toe relationship from standing frame
    sf = _standing_frame(extraction)
    baseline_heel_toe_diff = 0.0
    if sf:
        lheel = _get_landmark(sf.landmarks, "left_heel")
        lfi = _get_landmark(sf.landmarks, "left_foot_index")
        if lheel and lfi:
            baseline_heel_toe_diff = lheel["y"] - lfi["y"]

    for f in extraction.frames:
        lms = f.landmarks
        lheel = _get_landmark(lms, "left_heel")
        rheel = _get_landmark(lms, "right_heel")
        lfi = _get_landmark(lms, "left_foot_index")
        rfi = _get_landmark(lms, "right_foot_index")
        lh = _get_landmark(lms, "left_hip")
        rh = _get_landmark(lms, "right_hip")
        la = _get_landmark(lms, "left_ankle")
        ra = _get_landmark(lms, "right_ankle")

        # Heel rise detection
        heel_pts = [p for p in [lheel, rheel] if p]
        toe_pts = [p for p in [lfi, rfi] if p]
        if heel_pts and toe_pts:
            avg_heel_y = sum(p["y"] for p in heel_pts) / len(heel_pts)
            avg_toe_y = sum(p["y"] for p in toe_pts) / len(toe_pts)
            diff = avg_heel_y - avg_toe_y
            # If heel rises, diff decreases (heel y moves up = smaller)
            rise = baseline_heel_toe_diff - diff
            if rise > 0.005:  # threshold
                wd.heel_rise_frames.append(f.frame_index)
                heel_rise_magnitudes.append(rise)

        # Anterior/posterior via CoM approximation (use mid_hip as CoM proxy)
        foot_all = [p for p in [la, ra, lfi, rfi, lheel, rheel] if p]
        if lh and rh and foot_all:
            com_x = (lh["x"] + rh["x"]) / 2
            mid_foot_x = sum(p["x"] for p in foot_all) / len(foot_all)
            total += 1
            if com_x < mid_foot_x:
                anterior_count += 1
            else:
                posterior_count += 1

        # Left/right shift via hip position
        if lh and rh and la and ra:
            mid_hip_x = (lh["x"] + rh["x"]) / 2
            mid_ankle_x = (la["x"] + ra["x"]) / 2
            shift = mid_hip_x - mid_ankle_x  # positive = shifted toward higher x
            left_shifts.append(shift)

    wd.heel_rise_detected = len(wd.heel_rise_frames) > 0
    wd.heel_rise_magnitude = float(np.mean(heel_rise_magnitudes)) if heel_rise_magnitudes else 0.0

    if total > 0:
        wd.weight_anterior_pct = anterior_count / total * 100
        wd.weight_posterior_pct = posterior_count / total * 100

    if left_shifts:
        mean_shift = float(np.mean(left_shifts))
        # Positive shift = one direction; interpret as left/right based on sign
        # This is approximate — camera angle matters
        if mean_shift > 0.005:
            wd.weight_right_pct = 50 + min(50, abs(mean_shift) * 500)
            wd.weight_left_pct = 100 - wd.weight_right_pct
        elif mean_shift < -0.005:
            wd.weight_left_pct = 50 + min(50, abs(mean_shift) * 500)
            wd.weight_right_pct = 100 - wd.weight_left_pct

    return wd


# ── Main entry point ─────────────────────────────────────────────────────────


def compute_lever_biomechanics(
    extraction: ExtractionResult,
    angles: AngleResult,
    reps: RepSegmentation,
    exercise: str,
) -> LeverBiomechanics:
    """Calcule les métriques de bras de levier et analyse morphologique."""
    try:
        fps = extraction.fps if extraction.fps > 0 else 30.0

        levers = _compute_levers(extraction)
        anthropometry = _compute_anthropometry(extraction)
        sticking_point = _compute_sticking_point(angles, reps, exercise, fps)
        lockout = _compute_lockout(angles, reps, exercise)
        depth = _compute_depth(extraction, angles, reps, exercise)
        sequencing = _compute_sequencing(angles, reps, exercise, fps)
        head_neck = _compute_head_neck(extraction)
        weight_dist = _compute_weight_distribution(extraction)

        return LeverBiomechanics(
            levers=levers,
            anthropometry=anthropometry,
            sticking_point=sticking_point,
            lockout=lockout,
            depth=depth,
            sequencing=sequencing,
            head_neck=head_neck,
            weight_distribution=weight_dist,
        )
    except Exception:
        logger.exception("Erreur dans compute_lever_biomechanics")
        return LeverBiomechanics()
