"""Détection automatique des répétitions individuelles.

Segmente le signal angulaire principal en reps via détection
de pics et vallées, puis calcule tempo, ROM et vitesse pour chaque rep.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from analysis.angle_calculator import AngleResult, FrameAngles

logger = logging.getLogger("formcheck.rep_segmenter")

# Mapping exercice → attribut d'angle principal
PRIMARY_ANGLE_MAP: dict[str, str] = {
    "squat": "left_knee_flexion",
    "front_squat": "left_knee_flexion",
    "bulgarian_split_squat": "left_knee_flexion",
    "lunge": "left_knee_flexion",
    "leg_press": "left_knee_flexion",
    "deadlift": "left_hip_flexion",
    "rdl": "left_hip_flexion",
    "bench_press": "left_elbow_flexion",
    "ohp": "left_elbow_flexion",
    "curl": "left_elbow_flexion",
    "hip_thrust": "left_hip_flexion",
    "lateral_raise": "left_shoulder_abduction",
    "barbell_row": "left_elbow_flexion",
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

    def to_dict(self) -> dict[str, Any]:
        return {
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
        }


@dataclass
class RepSegmentation:
    """Résultat de la segmentation en répétitions."""
    reps: list[Rep] = field(default_factory=list)
    total_reps: int = 0
    avg_tempo: str = "0:0:0"
    tempo_consistency: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "reps": [r.to_dict() for r in self.reps],
            "total_reps": self.total_reps,
            "avg_tempo": self.avg_tempo,
            "tempo_consistency": round(self.tempo_consistency, 3),
        }


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


def _find_peaks_valleys(signal: np.ndarray, min_prominence: float = 10.0):
    """Trouve les pics et vallées du signal."""
    try:
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(signal, prominence=min_prominence, distance=5)
        valleys, _ = find_peaks(-signal, prominence=min_prominence, distance=5)
        return peaks, valleys
    except ImportError:
        logger.warning("scipy non disponible, détection manuelle des pics.")
        return _manual_find_peaks(signal, min_prominence)


def _manual_find_peaks(signal: np.ndarray, min_prominence: float):
    """Détection manuelle des pics/vallées sans scipy."""
    peaks = []
    valleys = []
    for i in range(1, len(signal) - 1):
        if signal[i] > signal[i - 1] and signal[i] > signal[i + 1]:
            peaks.append(i)
        elif signal[i] < signal[i - 1] and signal[i] < signal[i + 1]:
            valleys.append(i)
    return np.array(peaks), np.array(valleys)


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
        RepSegmentation avec les reps détectées.
    """
    result = RepSegmentation()

    # Déterminer l'angle principal
    attr = PRIMARY_ANGLE_MAP.get(exercise)
    if not attr:
        logger.warning("Exercice '%s' non mappé, essai avec left_knee_flexion.", exercise)
        attr = "left_knee_flexion"

    signal, frame_indices = _get_signal(angles.frames, attr)
    if len(signal) < 10:
        logger.warning("Signal trop court (%d points) pour détecter des reps.", len(signal))
        return result

    # Lisser le signal
    smoothed = _smooth_signal(signal)

    # Détecter pics et vallées
    # Pour les exercices de flexion, les vallées = point bas (angle min)
    rom_total = float(np.max(smoothed) - np.min(smoothed))
    min_prominence = max(rom_total * 0.2, 5.0)

    peaks, valleys = _find_peaks_valleys(smoothed, min_prominence)

    if len(valleys) < 2:
        # Pas assez de vallées pour segmenter
        # Essayer avec les pics comme délimiteurs
        if len(peaks) >= 2:
            # Inverser : chaque pic→valley→pic = 1 rep
            valleys, peaks = peaks, valleys
        else:
            logger.warning("Pas assez de points caractéristiques pour segmenter.")
            return result

    # Construire les reps : valley[i] → bottom (peak entre) → valley[i+1]
    reps: list[Rep] = []

    for i in range(len(valleys) - 1):
        v_start = valleys[i]
        v_end = valleys[i + 1]

        # Trouver le pic (bottom) entre les deux vallées
        between_peaks = peaks[(peaks > v_start) & (peaks < v_end)]
        if len(between_peaks) == 0:
            # Prendre le min/max du signal entre les vallées
            segment = smoothed[v_start:v_end + 1]
            bottom_local = int(np.argmin(segment)) if np.mean(smoothed[peaks]) < np.mean(smoothed[valleys]) else int(np.argmax(segment))
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

        # ROM de cette rep
        rep_signal = smoothed[v_start:v_end + 1]
        rep_rom = float(np.max(rep_signal) - np.min(rep_signal))

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
            rep_number=i + 1,
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
        )
        reps.append(rep)

    result.reps = reps
    result.total_reps = len(reps)

    # Tempo moyen
    if reps:
        avg_ecc = np.mean([r.eccentric_duration_ms for r in reps]) / 1000
        avg_conc = np.mean([r.concentric_duration_ms for r in reps]) / 1000
        result.avg_tempo = f"{avg_ecc:.0f}:0:{avg_conc:.0f}"

        # Consistance du tempo (1 = parfait, 0 = très variable)
        if len(reps) > 1:
            ratios = [r.tempo_ratio for r in reps if r.tempo_ratio > 0]
            if ratios:
                std = float(np.std(ratios))
                mean = float(np.mean(ratios))
                cv = std / mean if mean > 0 else 1.0
                result.tempo_consistency = max(0.0, min(1.0, 1.0 - cv))

    logger.info("Segmentation: %d reps détectées, tempo moyen: %s", result.total_reps, result.avg_tempo)
    return result
