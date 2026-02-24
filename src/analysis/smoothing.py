"""Lissage temporel des keypoints avant calcul d'angles.

Applique un filtre Savitzky-Golay sur chaque coordonnée (x, y, z)
de chaque landmark pour réduire le bruit de MediaPipe.
Interpole les frames manquantes par interpolation linéaire.
"""

from __future__ import annotations

import copy
import logging
from typing import Sequence

import numpy as np

from analysis.pose_extractor import FrameLandmarks

logger = logging.getLogger("formcheck.smoothing")

# Paramètres Savitzky-Golay
DEFAULT_WINDOW = 7
DEFAULT_POLYORDER = 2


def _savgol_filter(signal: np.ndarray, window: int, polyorder: int) -> np.ndarray:
    """Applique Savitzky-Golay, fallback sur moyenne mobile."""
    if len(signal) < window:
        return signal
    try:
        from scipy.signal import savgol_filter
        return savgol_filter(signal, window, polyorder)
    except ImportError:
        logger.warning("scipy non disponible, fallback sur moyenne mobile.")
        kernel = np.ones(window) / window
        # Pad pour conserver la longueur
        padded = np.pad(signal, (window // 2, window // 2), mode="edge")
        return np.convolve(padded, kernel, mode="valid")[:len(signal)]


def _interpolate_missing(
    frames: list[FrameLandmarks],
    landmark_count: int = 33,
) -> list[FrameLandmarks]:
    """Interpole les landmarks absents ou à faible visibilité.

    Si un landmark a visibility < 0.1 sur quelques frames isolées,
    interpole linéairement depuis les frames voisines.
    """
    if len(frames) < 3:
        return frames

    frames = [copy.deepcopy(f) for f in frames]

    for lm_idx in range(min(landmark_count, len(frames[0].landmarks))):
        visibilities = [f.landmarks[lm_idx]["visibility"] for f in frames]

        for coord in ("x", "y", "z"):
            values = np.array([f.landmarks[lm_idx][coord] for f in frames])
            vis = np.array(visibilities)

            # Masquer les points à très faible visibilité
            bad_mask = vis < 0.1
            if not np.any(bad_mask) or np.all(bad_mask):
                continue

            good_indices = np.where(~bad_mask)[0]
            bad_indices = np.where(bad_mask)[0]

            # Interpolation linéaire
            interpolated = np.interp(bad_indices, good_indices, values[good_indices])
            for i, bi in enumerate(bad_indices):
                frames[bi].landmarks[lm_idx][coord] = float(interpolated[i])

    return frames


def smooth_landmarks(
    frames: list[FrameLandmarks],
    window: int = DEFAULT_WINDOW,
    polyorder: int = DEFAULT_POLYORDER,
) -> list[FrameLandmarks]:
    """Lisse les keypoints temporellement.

    1. Interpole les landmarks manquants
    2. Applique Savitzky-Golay sur chaque coordonnée

    Args:
        frames: Liste de FrameLandmarks extraits par pose_extractor.
        window: Taille de la fenêtre Savitzky-Golay (impair).
        polyorder: Ordre du polynôme.

    Returns:
        Nouvelle liste de FrameLandmarks avec keypoints lissés.
    """
    if len(frames) < window:
        logger.warning("Pas assez de frames (%d) pour le lissage (window=%d).", len(frames), window)
        return [copy.deepcopy(f) for f in frames]

    # Étape 1 : interpolation
    smoothed = _interpolate_missing(frames)

    # Étape 2 : Savitzky-Golay par landmark et par coordonnée
    landmark_count = len(smoothed[0].landmarks) if smoothed else 0

    for lm_idx in range(landmark_count):
        for coord in ("x", "y", "z"):
            signal = np.array([f.landmarks[lm_idx][coord] for f in smoothed])
            filtered = _savgol_filter(signal, window, polyorder)
            for i, f in enumerate(smoothed):
                f.landmarks[lm_idx][coord] = float(filtered[i])

    logger.info("Lissage appliqué sur %d frames, %d landmarks.", len(smoothed), landmark_count)
    return smoothed
