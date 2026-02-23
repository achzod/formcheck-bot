"""Analyse biomécanique avancée — métriques expertes.

Calcule des métriques avancées à partir des landmarks MediaPipe :
- Détection de compensations (hip shift, butt wink, trunk lean…)
- Analyse du rachis (flexion, rotation)
- Dorsiflexion de cheville
- Centre de masse approximé
- Trajectoire de barre estimée
- Analyse de fatigue inter-reps
- Time Under Tension
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

logger = logging.getLogger("formcheck.biomechanics_advanced")

# ── Helpers ──────────────────────────────────────────────────────────────────


def _lm(landmarks: list[dict[str, float]], name: str) -> dict[str, float] | None:
    """Récupère un landmark par nom."""
    for lm in landmarks:
        if lm["name"] == name:
            return lm
    return None


def _pt2(lm: dict[str, float]) -> np.ndarray:
    return np.array([lm["x"], lm["y"]], dtype=np.float64)


def _pt3(lm: dict[str, float]) -> np.ndarray:
    return np.array([lm["x"], lm["y"], lm["z"]], dtype=np.float64)


def _mid2(a: dict[str, float], b: dict[str, float]) -> np.ndarray:
    return (_pt2(a) + _pt2(b)) / 2.0


def _mid3(a: dict[str, float], b: dict[str, float]) -> np.ndarray:
    return (_pt3(a) + _pt3(b)) / 2.0


def _angle_vec_vertical_2d(vec: np.ndarray) -> float:
    """Angle (degrés) entre un vecteur 2D et la verticale descendante [0,1]."""
    vert = np.array([0.0, 1.0])
    mag = np.linalg.norm(vec)
    if mag < 1e-8:
        return 0.0
    cos_a = np.clip(np.dot(vec, vert) / mag, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_a)))


def _angle_between_2d(v1: np.ndarray, v2: np.ndarray) -> float:
    """Angle non-signé entre deux vecteurs 2D, en degrés."""
    m1 = np.linalg.norm(v1)
    m2 = np.linalg.norm(v2)
    if m1 < 1e-8 or m2 < 1e-8:
        return 0.0
    cos_a = np.clip(np.dot(v1, v2) / (m1 * m2), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_a)))


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if abs(b) > 1e-8 else default


# ── Dataclasses ──────────────────────────────────────────────────────────────


@dataclass
class CompensationMetrics:
    hip_shift_per_frame: list[float] = field(default_factory=list)
    max_hip_shift: float = 0.0
    avg_hip_shift: float = 0.0
    hip_shift_side: str = "neutre"

    butt_wink_detected: bool = False
    butt_wink_degrees: float = 0.0
    butt_wink_frame: int = 0

    pelvic_tilt_change: float = 0.0

    shoulder_elevation_left: float = 1.0
    shoulder_elevation_right: float = 1.0

    lateral_lean_per_frame: list[float] = field(default_factory=list)
    max_lateral_lean: float = 0.0
    lateral_lean_side: str = "neutre"

    def to_dict(self) -> dict[str, Any]:
        return {
            "hip_shift_per_frame": [round(v, 4) for v in self.hip_shift_per_frame],
            "max_hip_shift": round(self.max_hip_shift, 4),
            "avg_hip_shift": round(self.avg_hip_shift, 4),
            "hip_shift_side": self.hip_shift_side,
            "butt_wink_detected": self.butt_wink_detected,
            "butt_wink_degrees": round(self.butt_wink_degrees, 1),
            "butt_wink_frame": self.butt_wink_frame,
            "pelvic_tilt_change": round(self.pelvic_tilt_change, 1),
            "shoulder_elevation_left": round(self.shoulder_elevation_left, 3),
            "shoulder_elevation_right": round(self.shoulder_elevation_right, 3),
            "lateral_lean_per_frame": [round(v, 2) for v in self.lateral_lean_per_frame],
            "max_lateral_lean": round(self.max_lateral_lean, 2),
            "lateral_lean_side": self.lateral_lean_side,
        }


@dataclass
class SpineAnalysis:
    spine_flexion_per_frame: list[float] = field(default_factory=list)
    max_spine_flexion: float = 0.0
    min_spine_flexion: float = 0.0
    spine_neutral_deviation: float = 0.0

    trunk_rotation_per_frame: list[float] = field(default_factory=list)
    max_trunk_rotation: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "spine_flexion_per_frame": [round(v, 2) for v in self.spine_flexion_per_frame],
            "max_spine_flexion": round(self.max_spine_flexion, 2),
            "min_spine_flexion": round(self.min_spine_flexion, 2),
            "spine_neutral_deviation": round(self.spine_neutral_deviation, 2),
            "trunk_rotation_per_frame": [round(v, 2) for v in self.trunk_rotation_per_frame],
            "max_trunk_rotation": round(self.max_trunk_rotation, 2),
        }


@dataclass
class AnkleDorsiflexion:
    left_dorsiflexion_per_frame: list[float] = field(default_factory=list)
    right_dorsiflexion_per_frame: list[float] = field(default_factory=list)
    left_max: float = 0.0
    right_max: float = 0.0
    left_mean: float = 0.0
    right_mean: float = 0.0
    asymmetry: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_dorsiflexion_per_frame": [round(v, 2) for v in self.left_dorsiflexion_per_frame],
            "right_dorsiflexion_per_frame": [round(v, 2) for v in self.right_dorsiflexion_per_frame],
            "left_max": round(self.left_max, 2),
            "right_max": round(self.right_max, 2),
            "left_mean": round(self.left_mean, 2),
            "right_mean": round(self.right_mean, 2),
            "asymmetry": round(self.asymmetry, 2),
        }


@dataclass
class CenterOfMass:
    com_x_per_frame: list[float] = field(default_factory=list)
    com_y_per_frame: list[float] = field(default_factory=list)
    com_lateral_deviation: float = 0.0
    com_anteroposterior_range: float = 0.0
    com_over_base_of_support: list[bool] = field(default_factory=list)
    stability_score: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "com_x_per_frame": [round(v, 5) for v in self.com_x_per_frame],
            "com_y_per_frame": [round(v, 5) for v in self.com_y_per_frame],
            "com_lateral_deviation": round(self.com_lateral_deviation, 5),
            "com_anteroposterior_range": round(self.com_anteroposterior_range, 5),
            "com_over_base_of_support": self.com_over_base_of_support,
            "stability_score": round(self.stability_score, 3),
        }


@dataclass
class BarPathAnalysis:
    bar_x_per_frame: list[float] = field(default_factory=list)
    bar_y_per_frame: list[float] = field(default_factory=list)
    vertical_deviation: float = 0.0
    path_efficiency: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "bar_x_per_frame": [round(v, 5) for v in self.bar_x_per_frame],
            "bar_y_per_frame": [round(v, 5) for v in self.bar_y_per_frame],
            "vertical_deviation": round(self.vertical_deviation, 5),
            "path_efficiency": round(self.path_efficiency, 3),
        }


@dataclass
class FatigueAnalysis:
    rom_degradation: float = 0.0
    tempo_degradation: float = 0.0
    symmetry_degradation: float = 0.0
    compensation_increase: float = 0.0
    first_rep_quality: float = 1.0
    last_rep_quality: float = 1.0
    fatigue_index: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rom_degradation": round(self.rom_degradation, 3),
            "tempo_degradation": round(self.tempo_degradation, 3),
            "symmetry_degradation": round(self.symmetry_degradation, 3),
            "compensation_increase": round(self.compensation_increase, 3),
            "first_rep_quality": round(self.first_rep_quality, 3),
            "last_rep_quality": round(self.last_rep_quality, 3),
            "fatigue_index": round(self.fatigue_index, 3),
        }


@dataclass
class TimeUnderTension:
    total_tut_ms: float = 0.0
    eccentric_tut_ms: float = 0.0
    concentric_tut_ms: float = 0.0
    isometric_tut_ms: float = 0.0
    avg_rep_tut_ms: float = 0.0
    tut_per_rep: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tut_ms": round(self.total_tut_ms, 0),
            "eccentric_tut_ms": round(self.eccentric_tut_ms, 0),
            "concentric_tut_ms": round(self.concentric_tut_ms, 0),
            "isometric_tut_ms": round(self.isometric_tut_ms, 0),
            "avg_rep_tut_ms": round(self.avg_rep_tut_ms, 0),
            "tut_per_rep": [round(v, 0) for v in self.tut_per_rep],
        }


@dataclass
class AdvancedBiomechanics:
    compensations: CompensationMetrics = field(default_factory=CompensationMetrics)
    spine: SpineAnalysis = field(default_factory=SpineAnalysis)
    ankle: AnkleDorsiflexion = field(default_factory=AnkleDorsiflexion)
    center_of_mass: CenterOfMass = field(default_factory=CenterOfMass)
    bar_path: BarPathAnalysis = field(default_factory=BarPathAnalysis)
    fatigue: FatigueAnalysis = field(default_factory=FatigueAnalysis)
    time_under_tension: TimeUnderTension = field(default_factory=TimeUnderTension)

    def to_dict(self) -> dict[str, Any]:
        return {
            "compensations": self.compensations.to_dict(),
            "spine": self.spine.to_dict(),
            "ankle": self.ankle.to_dict(),
            "center_of_mass": self.center_of_mass.to_dict(),
            "bar_path": self.bar_path.to_dict(),
            "fatigue": self.fatigue.to_dict(),
            "time_under_tension": self.time_under_tension.to_dict(),
        }


# ── Computation helpers ──────────────────────────────────────────────────────


def _build_landmark_arrays(frames: list[FrameLandmarks]) -> dict[str, np.ndarray]:
    """Pré-construit des arrays numpy (N, 3) par landmark pour vectoriser les calculs."""
    if not frames:
        return {}
    names = [lm["name"] for lm in frames[0].landmarks]
    arrays: dict[str, np.ndarray] = {}
    n = len(frames)
    for name in names:
        arr = np.zeros((n, 3), dtype=np.float64)
        for i, f in enumerate(frames):
            lm = _lm(f.landmarks, name)
            if lm:
                arr[i] = [lm["x"], lm["y"], lm["z"]]
        arrays[name] = arr
    return arrays


def _compute_compensations(
    arrs: dict[str, np.ndarray],
    frames: list[FrameLandmarks],
    reps: RepSegmentation,
) -> CompensationMetrics:
    """Calcule toutes les métriques de compensation."""
    c = CompensationMetrics()
    n = len(frames)
    if n == 0:
        return c

    try:
        lh = arrs["left_hip"]
        rh = arrs["right_hip"]
        la = arrs["left_ankle"]
        ra = arrs["right_ankle"]
        ls = arrs["left_shoulder"]
        rs = arrs["right_shoulder"]

        # ── Hip Shift ────────────────────────────────────────────────────
        mid_hip_x = (lh[:, 0] + rh[:, 0]) / 2.0
        mid_ankle_x = (la[:, 0] + ra[:, 0]) / 2.0
        hip_width = np.abs(lh[:, 0] - rh[:, 0])
        hip_width = np.where(hip_width < 1e-6, 1e-6, hip_width)
        shifts = (mid_hip_x - mid_ankle_x) / hip_width
        c.hip_shift_per_frame = shifts.tolist()
        c.max_hip_shift = float(np.max(np.abs(shifts)))
        c.avg_hip_shift = float(np.mean(np.abs(shifts)))
        mean_shift = float(np.mean(shifts))
        if mean_shift > 0.05:
            c.hip_shift_side = "droite"
        elif mean_shift < -0.05:
            c.hip_shift_side = "gauche"
        else:
            c.hip_shift_side = "neutre"

        # ── Lateral Trunk Lean ───────────────────────────────────────────
        mid_shoulder = (ls[:, :2] + rs[:, :2]) / 2.0
        mid_hip_2d = (lh[:, :2] + rh[:, :2]) / 2.0
        trunk_vec = mid_shoulder - mid_hip_2d  # from hip to shoulder
        # angle with vertical (0, -1) since y increases downward, shoulder is above hip
        # vertical upward in image = (0, -1)
        lean_angles = np.zeros(n)
        for i in range(n):
            vx, vy = trunk_vec[i]
            # angle with vertical upward [0, -1]
            mag = math.sqrt(vx * vx + vy * vy)
            if mag > 1e-8:
                # signed angle: positive = lean right (trunk shifted right)
                lean_angles[i] = math.degrees(math.asin(np.clip(vx / mag, -1, 1)))
        c.lateral_lean_per_frame = lean_angles.tolist()
        abs_lean = np.abs(lean_angles)
        c.max_lateral_lean = float(np.max(abs_lean))
        idx_max_lean = int(np.argmax(abs_lean))
        if lean_angles[idx_max_lean] > 2.0:
            c.lateral_lean_side = "droite"
        elif lean_angles[idx_max_lean] < -2.0:
            c.lateral_lean_side = "gauche"
        else:
            c.lateral_lean_side = "neutre"

        # ── Butt Wink (per rep) ──────────────────────────────────────────
        # Pelvic angle = angle of mid_hip→mid_shoulder vs vertical
        mid_hip_3 = (lh + rh) / 2.0
        mid_shoulder_3 = (ls + rs) / 2.0
        trunk_up = mid_shoulder_3[:, :2] - mid_hip_3[:, :2]
        pelvic_angles = np.zeros(n)
        for i in range(n):
            pelvic_angles[i] = _angle_vec_vertical_2d(trunk_up[i])

        worst_bw = 0.0
        worst_frame = 0
        if reps.reps:
            frame_idx_list = [f.frame_index for f in frames]
            for rep in reps.reps:
                # find array indices for start and bottom
                start_arr = _closest_idx(frame_idx_list, rep.start_frame)
                bottom_arr = _closest_idx(frame_idx_list, rep.bottom_frame)
                if start_arr is not None and bottom_arr is not None:
                    diff = pelvic_angles[bottom_arr] - pelvic_angles[start_arr]
                    if abs(diff) > abs(worst_bw):
                        worst_bw = diff
                        worst_frame = frames[bottom_arr].frame_index
        c.butt_wink_degrees = float(abs(worst_bw))
        c.butt_wink_detected = c.butt_wink_degrees > 15.0
        c.butt_wink_frame = worst_frame

        # ── Pelvic Tilt Change ───────────────────────────────────────────
        if n > 1:
            c.pelvic_tilt_change = float(pelvic_angles[-1] - pelvic_angles[0])
            # Better: compare first frame vs frame with max hip-y (deepest)
            mid_hip_y = (lh[:, 1] + rh[:, 1]) / 2.0
            deepest = int(np.argmax(mid_hip_y))  # y increases downward
            c.pelvic_tilt_change = float(pelvic_angles[deepest] - pelvic_angles[0])

        # ── Scapular Elevation ───────────────────────────────────────────
        le = arrs.get("left_ear")
        re = arrs.get("right_ear")
        if le is not None and re is not None:
            left_ear_shoulder_dist = np.abs(le[:, 1] - ls[:, 1])
            right_ear_shoulder_dist = np.abs(re[:, 1] - rs[:, 1])
            # ratio: neutral (frame 0) vs min during movement
            if left_ear_shoulder_dist[0] > 1e-6:
                c.shoulder_elevation_left = float(
                    np.min(left_ear_shoulder_dist) / left_ear_shoulder_dist[0]
                )
            if right_ear_shoulder_dist[0] > 1e-6:
                c.shoulder_elevation_right = float(
                    np.min(right_ear_shoulder_dist) / right_ear_shoulder_dist[0]
                )
    except Exception as e:
        logger.error("Erreur calcul compensations: %s", e)

    return c


def _closest_idx(frame_indices: list[int], target: int) -> int | None:
    """Trouve l'indice de tableau le plus proche d'un frame_index cible."""
    if not frame_indices:
        return None
    arr = np.array(frame_indices)
    idx = int(np.argmin(np.abs(arr - target)))
    return idx


def _compute_spine(arrs: dict[str, np.ndarray], n: int) -> SpineAnalysis:
    """Analyse du rachis."""
    s = SpineAnalysis()
    if n == 0:
        return s
    try:
        ls = arrs["left_shoulder"]
        rs = arrs["right_shoulder"]
        lh = arrs["left_hip"]
        rh = arrs["right_hip"]

        mid_shoulder = (ls + rh * 0 + rs) / 2.0  # fix: just (ls+rs)/2
        mid_shoulder = (ls + rs) / 2.0
        mid_hip = (lh + rh) / 2.0
        mid_trunk = (mid_shoulder + mid_hip) / 2.0

        # Spine flexion: angle at mid_trunk between upper (shoulder) and lower (hip) segments
        flexion = np.zeros(n)
        for i in range(n):
            upper = mid_shoulder[i, :2] - mid_trunk[i, :2]
            lower = mid_hip[i, :2] - mid_trunk[i, :2]
            flexion[i] = _angle_between_2d(upper, lower)

        s.spine_flexion_per_frame = flexion.tolist()
        s.max_spine_flexion = float(np.max(flexion))
        s.min_spine_flexion = float(np.min(flexion))
        if len(flexion) > 0:
            s.spine_neutral_deviation = float(np.mean(np.abs(flexion - flexion[0])))

        # Trunk rotation: z-depth difference between shoulders
        rotation = (ls[:, 2] - rs[:, 2])  # positive = left shoulder closer (rotation right)
        # Convert to approximate degrees (z is normalized, rough ~60° per 0.1 unit)
        rotation_deg = rotation * 600.0  # rough scale
        s.trunk_rotation_per_frame = rotation_deg.tolist()
        s.max_trunk_rotation = float(np.max(np.abs(rotation_deg)))

    except Exception as e:
        logger.error("Erreur calcul spine: %s", e)
    return s


def _compute_ankle_dorsiflexion(arrs: dict[str, np.ndarray], n: int) -> AnkleDorsiflexion:
    """Dorsiflexion de cheville."""
    a = AnkleDorsiflexion()
    if n == 0:
        return a
    try:
        lk = arrs["left_knee"]
        rk = arrs["right_knee"]
        lan = arrs["left_ankle"]
        ran = arrs["right_ankle"]

        left_df = np.zeros(n)
        right_df = np.zeros(n)
        vertical = np.array([0.0, -1.0])  # upward

        for i in range(n):
            # tibia vector: knee - ankle (points upward from ankle)
            l_tibia = lk[i, :2] - lan[i, :2]
            r_tibia = rk[i, :2] - ran[i, :2]
            left_df[i] = _angle_between_2d(l_tibia, vertical)
            right_df[i] = _angle_between_2d(r_tibia, vertical)

        a.left_dorsiflexion_per_frame = left_df.tolist()
        a.right_dorsiflexion_per_frame = right_df.tolist()
        a.left_max = float(np.max(left_df))
        a.right_max = float(np.max(right_df))
        a.left_mean = float(np.mean(left_df))
        a.right_mean = float(np.mean(right_df))
        a.asymmetry = abs(a.left_mean - a.right_mean)

    except Exception as e:
        logger.error("Erreur calcul dorsiflexion: %s", e)
    return a


def _compute_center_of_mass(arrs: dict[str, np.ndarray], n: int) -> CenterOfMass:
    """Approximation du centre de masse."""
    com = CenterOfMass()
    if n == 0:
        return com
    try:
        ls = arrs["left_shoulder"]
        rs = arrs["right_shoulder"]
        lh = arrs["left_hip"]
        rh = arrs["right_hip"]
        lk = arrs["left_knee"]
        rk = arrs["right_knee"]
        lan = arrs["left_ankle"]
        ran = arrs["right_ankle"]
        le = arrs["left_elbow"]
        re = arrs["right_elbow"]
        lw = arrs["left_wrist"]
        rw = arrs["right_wrist"]
        nose = arrs["nose"]

        # Weighted segments
        trunk = ((ls + rs) / 2.0 + (lh + rh) / 2.0) / 2.0  # mid-trunk
        thighs = ((lh + rh) / 2.0 + (lk + rk) / 2.0) / 2.0
        legs = ((lk + rk) / 2.0 + (lan + ran) / 2.0) / 2.0
        arms = ((ls + rs) / 2.0 + (le + re) / 2.0 + (lw + rw) / 2.0) / 3.0
        head = nose

        # Weighted average
        com_pos = (trunk * 0.50 + thighs * 0.20 + legs * 0.12 + arms * 0.10 + head * 0.08)

        com.com_x_per_frame = com_pos[:, 0].tolist()
        com.com_y_per_frame = com_pos[:, 1].tolist()

        # Base of support: x range of ankles
        bos_left = np.minimum(lan[:, 0], ran[:, 0])
        bos_right = np.maximum(lan[:, 0], ran[:, 0])
        margin = (bos_right - bos_left) * 0.1  # 10% margin

        com_x = com_pos[:, 0]
        com.com_over_base_of_support = (
            (com_x >= bos_left - margin) & (com_x <= bos_right + margin)
        ).tolist()

        # Lateral deviation from initial position
        if n > 0:
            com.com_lateral_deviation = float(np.max(np.abs(com_x - com_x[0])))

        # Anteroposterior range (y-axis movement)
        com_y = com_pos[:, 1]
        com.com_anteroposterior_range = float(np.max(com_y) - np.min(com_y))

        # Stability score: 1 - normalized std of CoM position
        std_x = float(np.std(com_x))
        std_y = float(np.std(com_y))
        # Normalize: typical body width ~0.2 in normalized coords
        variability = math.sqrt(std_x ** 2 + std_y ** 2)
        com.stability_score = max(0.0, min(1.0, 1.0 - variability * 10.0))

    except Exception as e:
        logger.error("Erreur calcul CoM: %s", e)
    return com


def _compute_bar_path(arrs: dict[str, np.ndarray], n: int, exercise: str) -> BarPathAnalysis:
    """Estimation de la trajectoire de barre via les poignets."""
    bp = BarPathAnalysis()
    if n == 0:
        return bp
    try:
        lw = arrs["left_wrist"]
        rw = arrs["right_wrist"]

        bar = (lw + rw) / 2.0
        bp.bar_x_per_frame = bar[:, 0].tolist()
        bp.bar_y_per_frame = bar[:, 1].tolist()

        if n > 1:
            # Vertical deviation: max lateral displacement from starting x
            x = bar[:, 0]
            bp.vertical_deviation = float(np.max(np.abs(x - x[0])))

            # Path efficiency: straight-line distance / actual path distance
            diffs = np.diff(bar[:, :2], axis=0)
            actual_dist = float(np.sum(np.sqrt(np.sum(diffs ** 2, axis=1))))
            straight_dist = float(np.linalg.norm(bar[-1, :2] - bar[0, :2]))
            # For reps, the bar comes back to start, so use total vertical travel
            y = bar[:, 1]
            total_vertical = float(np.sum(np.abs(np.diff(y))))
            if actual_dist > 1e-8:
                bp.path_efficiency = min(1.0, total_vertical / actual_dist)
            else:
                bp.path_efficiency = 1.0

    except Exception as e:
        logger.error("Erreur calcul bar path: %s", e)
    return bp


def _compute_fatigue(
    reps: RepSegmentation,
    frames: list[FrameLandmarks],
    arrs: dict[str, np.ndarray],
) -> FatigueAnalysis:
    """Analyse de fatigue inter-reps."""
    fa = FatigueAnalysis()
    rep_list = reps.reps
    if len(rep_list) < 2:
        return fa

    try:
        # ROM degradation
        first_rom = rep_list[0].rom
        last_rom = rep_list[-1].rom
        if first_rom > 1e-3:
            fa.rom_degradation = (first_rom - last_rom) / first_rom

        # Tempo degradation
        first_total = rep_list[0].eccentric_duration_ms + rep_list[0].concentric_duration_ms
        last_total = rep_list[-1].eccentric_duration_ms + rep_list[-1].concentric_duration_ms
        if first_total > 1e-3:
            fa.tempo_degradation = abs(last_total - first_total) / first_total

        # Symmetry degradation: would need per-rep symmetry; approximate via hip shift
        frame_idx_list = [f.frame_index for f in frames]
        n = len(frames)
        if n > 0 and len(arrs) > 0:
            lh = arrs.get("left_hip")
            rh = arrs.get("right_hip")
            la = arrs.get("left_ankle")
            ra = arrs.get("right_ankle")
            if lh is not None and rh is not None and la is not None and ra is not None:
                mid_hip_x = (lh[:, 0] + rh[:, 0]) / 2.0
                mid_ankle_x = (la[:, 0] + ra[:, 0]) / 2.0
                hip_w = np.abs(lh[:, 0] - rh[:, 0])
                hip_w = np.where(hip_w < 1e-6, 1e-6, hip_w)
                shifts = np.abs((mid_hip_x - mid_ankle_x) / hip_w)

                # Average shift for first vs last rep
                first_start = _closest_idx(frame_idx_list, rep_list[0].start_frame)
                first_end = _closest_idx(frame_idx_list, rep_list[0].end_frame)
                last_start = _closest_idx(frame_idx_list, rep_list[-1].start_frame)
                last_end = _closest_idx(frame_idx_list, rep_list[-1].end_frame)

                if all(v is not None for v in [first_start, first_end, last_start, last_end]):
                    first_shift = float(np.mean(shifts[first_start:first_end + 1]))
                    last_shift = float(np.mean(shifts[last_start:last_end + 1]))
                    if first_shift > 1e-6:
                        fa.compensation_increase = (last_shift - first_shift) / first_shift
                    fa.symmetry_degradation = abs(last_shift - first_shift)

        # Quality proxy: ROM * tempo_consistency-proxy
        fa.first_rep_quality = min(1.0, first_rom / 90.0) if first_rom > 0 else 0.5
        fa.last_rep_quality = min(1.0, last_rom / 90.0) if last_rom > 0 else 0.5

        # Fatigue index: weighted combination
        fa.fatigue_index = min(1.0, max(0.0,
            abs(fa.rom_degradation) * 0.4 +
            fa.tempo_degradation * 0.3 +
            abs(fa.compensation_increase) * 0.2 +
            fa.symmetry_degradation * 0.1
        ))

    except Exception as e:
        logger.error("Erreur calcul fatigue: %s", e)
    return fa


def _compute_tut(
    reps: RepSegmentation,
    angles: AngleResult,
    fps: float,
) -> TimeUnderTension:
    """Time Under Tension."""
    tut = TimeUnderTension()
    rep_list = reps.reps
    if not rep_list or fps <= 0:
        return tut

    try:
        total_ecc = 0.0
        total_conc = 0.0
        total_iso = 0.0
        tut_per_rep: list[float] = []

        # Build angle signal for isometric detection
        angle_vals = []
        angle_frames_idx = []
        for f in angles.frames:
            val = f.left_knee_flexion or f.left_hip_flexion or f.left_elbow_flexion
            if val is not None:
                angle_vals.append(val)
                angle_frames_idx.append(f.frame_index)
        angle_arr = np.array(angle_vals) if angle_vals else np.array([])
        frame_arr = np.array(angle_frames_idx) if angle_frames_idx else np.array([])

        for rep in rep_list:
            ecc = rep.eccentric_duration_ms
            conc = rep.concentric_duration_ms

            # Detect isometric pauses: frames where angular velocity < threshold
            iso_ms = 0.0
            if len(angle_arr) > 1 and len(frame_arr) > 1:
                mask = (frame_arr >= rep.start_frame) & (frame_arr <= rep.end_frame)
                rep_angles = angle_arr[mask]
                if len(rep_angles) > 2:
                    velocities = np.abs(np.diff(rep_angles)) * fps
                    iso_frames = np.sum(velocities < 5.0)  # < 5°/s = isometric
                    iso_ms = float(iso_frames) / fps * 1000.0

            total_ecc += ecc
            total_conc += conc
            total_iso += iso_ms
            rep_tut = ecc + conc  # iso is within ecc/conc
            tut_per_rep.append(rep_tut)

        tut.eccentric_tut_ms = total_ecc
        tut.concentric_tut_ms = total_conc
        tut.isometric_tut_ms = total_iso
        tut.total_tut_ms = total_ecc + total_conc
        tut.tut_per_rep = tut_per_rep
        if tut_per_rep:
            tut.avg_rep_tut_ms = float(np.mean(tut_per_rep))

    except Exception as e:
        logger.error("Erreur calcul TUT: %s", e)
    return tut


# ── Main ─────────────────────────────────────────────────────────────────────


def compute_advanced_biomechanics(
    extraction: ExtractionResult,
    angles: AngleResult,
    reps: RepSegmentation,
    exercise: str,
) -> AdvancedBiomechanics:
    """Calcule toutes les métriques bioméchaniques avancées."""
    frames = extraction.frames
    n = len(frames)

    if n == 0:
        logger.warning("Aucune frame disponible pour l'analyse avancée.")
        return AdvancedBiomechanics()

    # Pre-build arrays for vectorized computation
    arrs = _build_landmark_arrays(frames)

    return AdvancedBiomechanics(
        compensations=_compute_compensations(arrs, frames, reps),
        spine=_compute_spine(arrs, n),
        ankle=_compute_ankle_dorsiflexion(arrs, n),
        center_of_mass=_compute_center_of_mass(arrs, n),
        bar_path=_compute_bar_path(arrs, n, exercise),
        fatigue=_compute_fatigue(reps, frames, arrs),
        time_under_tension=_compute_tut(reps, angles, extraction.fps),
    )
