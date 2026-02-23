"""Calcul des angles articulaires à partir des landmarks MediaPipe.

Angles calculés :
- Genou (flexion)
- Hanche (flexion)
- Tronc (inclinaison vs verticale)
- Coude (flexion)
- Épaule (abduction, flexion)
- Valgus dynamique (déviation médiale du genou)
- Symétrie gauche/droite
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from analysis.pose_extractor import ExtractionResult, FrameLandmarks


# ── Types ────────────────────────────────────────────────────────────────────

@dataclass
class FrameAngles:
    """Tous les angles articulaires pour une frame donnée."""
    frame_index: int
    timestamp_ms: float
    # Flexions
    left_knee_flexion: float | None = None
    right_knee_flexion: float | None = None
    left_hip_flexion: float | None = None
    right_hip_flexion: float | None = None
    left_elbow_flexion: float | None = None
    right_elbow_flexion: float | None = None
    # Tronc
    trunk_inclination: float | None = None       # vs verticale
    # Épaule
    left_shoulder_abduction: float | None = None
    right_shoulder_abduction: float | None = None
    left_shoulder_flexion: float | None = None
    right_shoulder_flexion: float | None = None
    # Valgus
    left_knee_valgus: float | None = None        # déviation médiale (°)
    right_knee_valgus: float | None = None
    # Symétrie
    knee_flexion_symmetry: float | None = None    # ratio G/D (1.0 = parfait)
    hip_flexion_symmetry: float | None = None
    shoulder_abduction_symmetry: float | None = None


@dataclass
class AngleStats:
    """Statistiques min/max/moyenne pour un angle."""
    min_value: float
    max_value: float
    mean_value: float
    range_of_motion: float  # max - min


@dataclass
class AngleResult:
    """Résultat complet du calcul d'angles."""
    frames: list[FrameAngles] = field(default_factory=list)
    stats: dict[str, AngleStats] = field(default_factory=dict)


# ── Helpers géométriques ─────────────────────────────────────────────────────

def _get_landmark(
    landmarks: list[dict[str, float]], name: str
) -> dict[str, float] | None:
    """Récupère un landmark par son nom."""
    for lm in landmarks:
        if lm["name"] == name:
            return lm
    return None


def _point_2d(lm: dict[str, float]) -> np.ndarray:
    """Coordonnées 2D (x, y) d'un landmark."""
    return np.array([lm["x"], lm["y"]])


def _point_3d(lm: dict[str, float]) -> np.ndarray:
    """Coordonnées 3D (x, y, z) d'un landmark."""
    return np.array([lm["x"], lm["y"], lm["z"]])


def angle_between_three_points(
    a: np.ndarray, b: np.ndarray, c: np.ndarray
) -> float:
    """Calcule l'angle en degrés au point B formé par les segments BA et BC.

    Utilise le produit scalaire : angle = arccos((BA · BC) / (|BA| × |BC|))
    """
    ba = a - b
    bc = c - b
    dot = np.dot(ba, bc)
    mag_ba = np.linalg.norm(ba)
    mag_bc = np.linalg.norm(bc)
    if mag_ba < 1e-8 or mag_bc < 1e-8:
        return 0.0
    cos_angle = np.clip(dot / (mag_ba * mag_bc), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))


def angle_with_vertical(a: np.ndarray, b: np.ndarray) -> float:
    """Angle du segment AB par rapport à la verticale (axe y descendant).

    Retourne un angle entre 0° (vertical) et 180°.
    """
    vec = b - a
    vertical = np.array([0.0, 1.0])  # y pointe vers le bas en MediaPipe
    dot = np.dot(vec[:2], vertical)
    mag = np.linalg.norm(vec[:2])
    if mag < 1e-8:
        return 0.0
    cos_angle = np.clip(dot / mag, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))


def _symmetry_ratio(left: float | None, right: float | None) -> float | None:
    """Ratio de symétrie : min(G,D) / max(G,D). 1.0 = parfait."""
    if left is None or right is None:
        return None
    if max(abs(left), abs(right)) < 1e-3:
        return 1.0
    return round(min(abs(left), abs(right)) / max(abs(left), abs(right)), 3)


# ── Calculs d'angles spécifiques ─────────────────────────────────────────────

def compute_knee_flexion(
    landmarks: list[dict[str, float]], side: str
) -> float | None:
    """Angle de flexion du genou (hanche-genou-cheville)."""
    hip = _get_landmark(landmarks, f"{side}_hip")
    knee = _get_landmark(landmarks, f"{side}_knee")
    ankle = _get_landmark(landmarks, f"{side}_ankle")
    if not all([hip, knee, ankle]):
        return None
    return angle_between_three_points(
        _point_3d(hip), _point_3d(knee), _point_3d(ankle)
    )


def compute_hip_flexion(
    landmarks: list[dict[str, float]], side: str
) -> float | None:
    """Angle de flexion de la hanche (épaule-hanche-genou)."""
    shoulder = _get_landmark(landmarks, f"{side}_shoulder")
    hip = _get_landmark(landmarks, f"{side}_hip")
    knee = _get_landmark(landmarks, f"{side}_knee")
    if not all([shoulder, hip, knee]):
        return None
    return angle_between_three_points(
        _point_3d(shoulder), _point_3d(hip), _point_3d(knee)
    )


def compute_elbow_flexion(
    landmarks: list[dict[str, float]], side: str
) -> float | None:
    """Angle de flexion du coude (épaule-coude-poignet)."""
    shoulder = _get_landmark(landmarks, f"{side}_shoulder")
    elbow = _get_landmark(landmarks, f"{side}_elbow")
    wrist = _get_landmark(landmarks, f"{side}_wrist")
    if not all([shoulder, elbow, wrist]):
        return None
    return angle_between_three_points(
        _point_3d(shoulder), _point_3d(elbow), _point_3d(wrist)
    )


def compute_trunk_inclination(
    landmarks: list[dict[str, float]],
) -> float | None:
    """Inclinaison du tronc par rapport à la verticale.

    On utilise le milieu des épaules et le milieu des hanches pour définir
    l'axe du tronc.
    """
    ls = _get_landmark(landmarks, "left_shoulder")
    rs = _get_landmark(landmarks, "right_shoulder")
    lh = _get_landmark(landmarks, "left_hip")
    rh = _get_landmark(landmarks, "right_hip")
    if not all([ls, rs, lh, rh]):
        return None
    mid_shoulder = (_point_2d(ls) + _point_2d(rs)) / 2.0
    mid_hip = (_point_2d(lh) + _point_2d(rh)) / 2.0
    return angle_with_vertical(mid_shoulder, mid_hip)


def compute_shoulder_abduction(
    landmarks: list[dict[str, float]], side: str
) -> float | None:
    """Angle d'abduction de l'épaule (hanche-épaule-coude dans le plan frontal)."""
    hip = _get_landmark(landmarks, f"{side}_hip")
    shoulder = _get_landmark(landmarks, f"{side}_shoulder")
    elbow = _get_landmark(landmarks, f"{side}_elbow")
    if not all([hip, shoulder, elbow]):
        return None
    return angle_between_three_points(
        _point_3d(hip), _point_3d(shoulder), _point_3d(elbow)
    )


def compute_shoulder_flexion(
    landmarks: list[dict[str, float]], side: str
) -> float | None:
    """Angle de flexion de l'épaule (hanche-épaule-coude dans le plan sagittal).

    Similaire à l'abduction mais on s'intéresse au mouvement avant/arrière.
    On utilise les coordonnées 3D pour différencier.
    """
    hip = _get_landmark(landmarks, f"{side}_hip")
    shoulder = _get_landmark(landmarks, f"{side}_shoulder")
    elbow = _get_landmark(landmarks, f"{side}_elbow")
    if not all([hip, shoulder, elbow]):
        return None
    # Plan sagittal : on utilise x,y (profil)
    return angle_between_three_points(
        _point_3d(hip), _point_3d(shoulder), _point_3d(elbow)
    )


def compute_knee_valgus(
    landmarks: list[dict[str, float]], side: str
) -> float | None:
    """Valgus dynamique du genou : déviation médiale par rapport à la ligne hanche-cheville.

    Mesure l'angle entre la ligne hanche-cheville et la ligne hanche-genou
    dans le plan frontal (coordonnées x,y). Un angle positif indique une
    déviation médiale (valgus).
    """
    hip = _get_landmark(landmarks, f"{side}_hip")
    knee = _get_landmark(landmarks, f"{side}_knee")
    ankle = _get_landmark(landmarks, f"{side}_ankle")
    if not all([hip, knee, ankle]):
        return None

    hip_2d = _point_2d(hip)
    knee_2d = _point_2d(knee)
    ankle_2d = _point_2d(ankle)

    # Vecteur hanche→cheville (ligne de référence)
    ref_vec = ankle_2d - hip_2d
    # Vecteur hanche→genou
    knee_vec = knee_2d - hip_2d

    # Angle signé dans le plan frontal
    # Produit vectoriel 2D pour déterminer le côté
    cross = ref_vec[0] * knee_vec[1] - ref_vec[1] * knee_vec[0]
    dot = np.dot(ref_vec, knee_vec)
    angle = math.atan2(cross, dot)
    angle_deg = math.degrees(angle)

    # Convention : positif = déviation médiale (valgus)
    # Pour le côté gauche, la médiale est vers la droite (x+)
    # Pour le côté droit, la médiale est vers la gauche (x-)
    if side == "left":
        return -angle_deg  # Inverser pour que positif = valgus
    return angle_deg


# ── Pipeline principal ───────────────────────────────────────────────────────

def compute_all_angles(frame: FrameLandmarks) -> FrameAngles:
    """Calcule tous les angles articulaires pour une frame."""
    lms = frame.landmarks

    left_knee = compute_knee_flexion(lms, "left")
    right_knee = compute_knee_flexion(lms, "right")
    left_hip = compute_hip_flexion(lms, "left")
    right_hip = compute_hip_flexion(lms, "right")
    left_elbow = compute_elbow_flexion(lms, "left")
    right_elbow = compute_elbow_flexion(lms, "right")
    left_shoulder_abd = compute_shoulder_abduction(lms, "left")
    right_shoulder_abd = compute_shoulder_abduction(lms, "right")
    left_shoulder_flex = compute_shoulder_flexion(lms, "left")
    right_shoulder_flex = compute_shoulder_flexion(lms, "right")

    return FrameAngles(
        frame_index=frame.frame_index,
        timestamp_ms=frame.timestamp_ms,
        left_knee_flexion=_round(left_knee),
        right_knee_flexion=_round(right_knee),
        left_hip_flexion=_round(left_hip),
        right_hip_flexion=_round(right_hip),
        left_elbow_flexion=_round(left_elbow),
        right_elbow_flexion=_round(right_elbow),
        trunk_inclination=_round(compute_trunk_inclination(lms)),
        left_shoulder_abduction=_round(left_shoulder_abd),
        right_shoulder_abduction=_round(right_shoulder_abd),
        left_shoulder_flexion=_round(left_shoulder_flex),
        right_shoulder_flexion=_round(right_shoulder_flex),
        left_knee_valgus=_round(compute_knee_valgus(lms, "left")),
        right_knee_valgus=_round(compute_knee_valgus(lms, "right")),
        knee_flexion_symmetry=_symmetry_ratio(left_knee, right_knee),
        hip_flexion_symmetry=_symmetry_ratio(left_hip, right_hip),
        shoulder_abduction_symmetry=_symmetry_ratio(
            left_shoulder_abd, right_shoulder_abd
        ),
    )


def _round(val: float | None, decimals: int = 1) -> float | None:
    """Arrondit une valeur optionnelle."""
    return round(val, decimals) if val is not None else None


def _collect_values(
    frames: list[FrameAngles], attr: str
) -> list[float]:
    """Collecte les valeurs non-None d'un attribut sur toutes les frames."""
    return [
        getattr(f, attr)
        for f in frames
        if getattr(f, attr) is not None
    ]


def _compute_stats(values: list[float]) -> AngleStats | None:
    """Calcule les stats pour une série de valeurs."""
    if not values:
        return None
    return AngleStats(
        min_value=round(min(values), 1),
        max_value=round(max(values), 1),
        mean_value=round(float(np.mean(values)), 1),
        range_of_motion=round(max(values) - min(values), 1),
    )


# Attributs pour lesquels on calcule des stats
_ANGLE_ATTRS = [
    "left_knee_flexion", "right_knee_flexion",
    "left_hip_flexion", "right_hip_flexion",
    "left_elbow_flexion", "right_elbow_flexion",
    "trunk_inclination",
    "left_shoulder_abduction", "right_shoulder_abduction",
    "left_shoulder_flexion", "right_shoulder_flexion",
    "left_knee_valgus", "right_knee_valgus",
    "knee_flexion_symmetry", "hip_flexion_symmetry",
    "shoulder_abduction_symmetry",
]


def compute_angles(extraction: ExtractionResult) -> AngleResult:
    """Calcule tous les angles pour toutes les frames extraites.

    Args:
        extraction: Résultat de l'extraction de pose.

    Returns:
        AngleResult avec angles frame par frame et statistiques.
    """
    result = AngleResult()

    for frame in extraction.frames:
        angles = compute_all_angles(frame)
        result.frames.append(angles)

    # Statistiques par angle
    for attr in _ANGLE_ATTRS:
        values = _collect_values(result.frames, attr)
        stats = _compute_stats(values)
        if stats:
            result.stats[attr] = stats

    return result


def angles_to_dict(result: AngleResult) -> dict[str, Any]:
    """Convertit le résultat des angles en dict JSON-sérialisable."""
    frames_data = []
    for f in result.frames:
        frame_dict: dict[str, Any] = {
            "frame_index": f.frame_index,
            "timestamp_ms": round(f.timestamp_ms, 1),
        }
        for attr in _ANGLE_ATTRS:
            val = getattr(f, attr)
            frame_dict[attr] = val
        frames_data.append(frame_dict)

    stats_data = {}
    for name, s in result.stats.items():
        stats_data[name] = {
            "min": s.min_value,
            "max": s.max_value,
            "mean": s.mean_value,
            "rom": s.range_of_motion,
        }

    return {"frames": frames_data, "stats": stats_data}
