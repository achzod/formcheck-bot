"""Validation vidéo avant analyse biomécanique.

Vérifie la résolution, durée, FPS, luminosité et présence d'une personne.
Retourne un score de qualité et des warnings/erreurs bloquantes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger("formcheck.video_validator")


@dataclass
class VideoValidation:
    """Résultat de la validation vidéo."""
    is_valid: bool = True
    quality_score: int = 0
    resolution: tuple[int, int] = (0, 0)
    fps: float = 0.0
    duration: float = 0.0
    brightness: float = 0.0
    person_detected: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "quality_score": self.quality_score,
            "resolution": list(self.resolution),
            "fps": round(self.fps, 1),
            "duration": round(self.duration, 1),
            "brightness": round(self.brightness, 1),
            "person_detected": self.person_detected,
            "warnings": self.warnings,
            "blocking_errors": self.blocking_errors,
        }


def _sample_frames(cap: cv2.VideoCapture, total_frames: int, n: int = 3) -> list[np.ndarray]:
    """Échantillonne n frames réparties uniformément."""
    indices = [int(total_frames * i / (n + 1)) for i in range(1, n + 1)]
    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)
    return frames


def _check_brightness(frames: list[np.ndarray]) -> float:
    """Calcule la luminosité moyenne sur les frames échantillonnées."""
    if not frames:
        return 0.0
    brightnesses = []
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightnesses.append(float(np.mean(gray)))
    return float(np.mean(brightnesses))


def _check_person(frames: list[np.ndarray]) -> bool:
    """Détecte la présence d'au moins une personne via MediaPipe Pose rapide."""
    try:
        import mediapipe as mp
        mp_pose = mp.solutions.pose
        with mp_pose.Pose(
            static_image_mode=True,
            model_complexity=0,
            min_detection_confidence=0.3,
        ) as pose:
            for frame in frames:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb)
                if results.pose_landmarks:
                    return True
        return False
    except Exception as e:
        logger.warning("Détection personne échouée: %s", e)
        return False


def validate_video(
    video_path: str,
    min_duration: float = 3.0,
    max_duration: float = 180.0,
    min_brightness: float = 40.0,
    min_resolution: int = 720,
    min_fps: float = 15.0,
) -> VideoValidation:
    """Valide une vidéo avant analyse biomécanique.

    Args:
        video_path: Chemin vers la vidéo.
        min_duration: Durée minimum en secondes.
        max_duration: Durée maximum en secondes.
        min_brightness: Luminosité minimum (moyenne pixels 0-255).
        min_resolution: Hauteur minimum en pixels pour warning.
        min_fps: FPS minimum pour warning.

    Returns:
        VideoValidation avec résultats et score qualité.
    """
    result = VideoValidation()

    # Ouvrir la vidéo
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        result.is_valid = False
        result.blocking_errors.append("Impossible d'ouvrir la vidéo. Format non supporté ou fichier corrompu.")
        return result

    # Métadonnées
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0.0

    result.resolution = (width, height)
    result.fps = fps
    result.duration = duration

    score = 100

    # Durée
    if duration < min_duration:
        result.blocking_errors.append(
            f"Vidéo trop courte ({duration:.1f}s). Minimum {min_duration:.0f} secondes. "
            "Filme au moins 2-3 répétitions complètes."
        )
        score -= 40
    elif duration > max_duration:
        result.blocking_errors.append(
            f"Vidéo trop longue ({duration:.1f}s). Maximum {max_duration:.0f} secondes. "
            "Envoie uniquement ta série, pas toute la séance."
        )
        score -= 30

    # Résolution
    if height < min_resolution:
        result.warnings.append(
            f"Résolution basse ({width}x{height}). 720p minimum recommandé pour une analyse précise."
        )
        score -= 15
    if height >= 1080:
        score += 0  # pas de bonus, déjà à 100

    # FPS
    if fps < min_fps:
        result.warnings.append(
            f"FPS bas ({fps:.0f}). 15 FPS minimum recommandé. "
            "Vérifie les paramètres de ta caméra."
        )
        score -= 10

    # Échantillonner des frames pour checks visuels
    sample = _sample_frames(cap, total_frames, n=3)

    # Luminosité
    brightness = _check_brightness(sample)
    result.brightness = brightness
    if brightness < min_brightness:
        result.blocking_errors.append(
            f"Vidéo trop sombre (luminosité: {brightness:.0f}/255). "
            "Assure-toi d'avoir un bon éclairage. Évite le contre-jour."
        )
        score -= 25
    elif brightness < 60:
        result.warnings.append(
            f"Luminosité faible ({brightness:.0f}/255). L'analyse sera moins précise."
        )
        score -= 10

    # Détection personne (non-bloquant — le pipeline principal vérifie aussi)
    person_detected = _check_person(sample)
    result.person_detected = person_detected
    if not person_detected:
        result.warnings.append(
            "Personne difficile à détecter sur les frames échantillonnées. "
            "L'analyse continue mais pourrait être moins précise."
        )
        score -= 10

    cap.release()

    # Score final
    result.quality_score = max(0, min(100, score))
    result.is_valid = len(result.blocking_errors) == 0

    return result
