"""Validation vidéo avant analyse biomécanique.

Vérifie la résolution, durée, FPS, luminosité, stabilité et présence
d'une personne. Retourne un score de qualité, des warnings, des erreurs
bloquantes et des suggestions concrètes pour améliorer la vidéo.

Philosophie : rejeter le moins possible. On préfère analyser avec
un disclaimer plutôt que bloquer l'utilisateur.
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
    contrast: float = 0.0
    stability: float = 1.0  # 1 = stable, 0 = très instable
    person_detected: bool = False
    person_coverage: float = 0.0  # % de la frame occupée par la personne
    warnings: list[str] = field(default_factory=list)
    blocking_errors: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    # Indicateurs pour le pipeline
    low_quality_disclaimer: bool = False  # True si on analyse malgré qualité faible

    def to_dict(self) -> dict[str, Any]:
        d = {
            "is_valid": self.is_valid,
            "quality_score": self.quality_score,
            "resolution": list(self.resolution),
            "fps": round(self.fps, 1),
            "duration": round(self.duration, 1),
            "brightness": round(self.brightness, 1),
            "contrast": round(self.contrast, 1),
            "stability": round(self.stability, 2),
            "person_detected": self.person_detected,
            "person_coverage": round(self.person_coverage, 2),
            "warnings": self.warnings,
            "blocking_errors": self.blocking_errors,
            "suggestions": self.suggestions,
        }
        if self.low_quality_disclaimer:
            d["low_quality_disclaimer"] = True
        return d


def _sample_frames(cap: cv2.VideoCapture, total_frames: int, n: int = 5) -> list[np.ndarray]:
    """Échantillonne n frames réparties uniformément."""
    indices = [int(total_frames * i / (n + 1)) for i in range(1, n + 1)]
    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)
    return frames


def _check_brightness(frames: list[np.ndarray]) -> tuple[float, float]:
    """Calcule la luminosité et le contraste moyens."""
    if not frames:
        return 0.0, 0.0
    brightnesses = []
    contrasts = []
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightnesses.append(float(np.mean(gray)))
        contrasts.append(float(np.std(gray)))
    return float(np.mean(brightnesses)), float(np.mean(contrasts))


def _check_stability(frames: list[np.ndarray]) -> float:
    """Estime la stabilité de la caméra via l'histogramme inter-frames.

    Compare les histogrammes de frames consécutives. Un changement
    brutal indique un mouvement de caméra.
    """
    if len(frames) < 2:
        return 1.0

    correlations = []
    for i in range(len(frames) - 1):
        gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)
        hist1 = cv2.calcHist([gray1], [0], None, [64], [0, 256]).flatten()
        hist2 = cv2.calcHist([gray2], [0], None, [64], [0, 256]).flatten()
        # Normaliser
        hist1 = hist1 / (hist1.sum() + 1e-8)
        hist2 = hist2 / (hist2.sum() + 1e-8)
        corr = float(cv2.compareHist(
            hist1.astype(np.float32),
            hist2.astype(np.float32),
            cv2.HISTCMP_CORREL,
        ))
        correlations.append(corr)

    return float(np.mean(correlations))


def _check_person(frames: list[np.ndarray]) -> tuple[bool, float]:
    """Détecte la présence d'au moins une personne et estime la couverture.

    Returns:
        (person_detected, coverage_ratio)
    """
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
                    # Estimer la couverture (bounding box des landmarks)
                    xs = [lm.x for lm in results.pose_landmarks.landmark]
                    ys = [lm.y for lm in results.pose_landmarks.landmark]
                    width = max(xs) - min(xs)
                    height = max(ys) - min(ys)
                    coverage = width * height  # ratio de la frame
                    return True, float(coverage)
        return False, 0.0
    except Exception as e:
        logger.warning("Détection personne échouée: %s", e)
        return False, 0.0


def validate_video(
    video_path: str,
    min_duration: float = 3.0,
    max_duration: float = 180.0,
    min_brightness: float = 40.0,
    min_resolution: int = 720,
    min_fps: float = 15.0,
) -> VideoValidation:
    """Valide une vidéo avant analyse biomécanique.

    Philosophie : on bloque uniquement si la vidéo est inexploitable
    (corrompue, 0 seconde, totalement noire). Sinon on analyse avec
    un disclaimer et des suggestions concrètes.

    Args:
        video_path: Chemin vers la vidéo.
        min_duration: Durée minimum en secondes.
        max_duration: Durée maximum en secondes.
        min_brightness: Luminosité minimum (moyenne pixels 0-255).
        min_resolution: Hauteur minimum en pixels pour warning.
        min_fps: FPS minimum pour warning.

    Returns:
        VideoValidation avec résultats, score qualité et suggestions.
    """
    result = VideoValidation()

    # Ouvrir la vidéo
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        result.is_valid = False
        result.blocking_errors.append(
            "Impossible d'ouvrir la vidéo. Vérifie que le fichier n'est pas corrompu "
            "et qu'il est au format MP4, MOV ou AVI."
        )
        result.suggestions.append("Réenregistre la vidéo depuis ton téléphone et renvoie-la")
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

    # ── Durée ───────────────────────────────────────────────────────────
    if duration < 1.0:
        # Vraiment inexploitable
        result.blocking_errors.append(
            f"Vidéo trop courte ({duration:.1f}s). Il faut au moins 1 seconde de mouvement."
        )
        result.suggestions.append("Filme au moins 2-3 répétitions complètes")
        score -= 50
    elif duration < min_duration:
        # Court mais analysable — on continue avec disclaimer
        result.warnings.append(
            f"Vidéo courte ({duration:.1f}s). Idéalement 5-10 secondes avec 3-5 reps."
        )
        result.suggestions.append(
            "Pour une analyse complète avec fatigue et régularité, filme 5-8 reps"
        )
        result.low_quality_disclaimer = True
        score -= 20
    elif duration > max_duration:
        result.warnings.append(
            f"Vidéo longue ({duration:.0f}s). Envoie uniquement ta série, pas toute la séance."
        )
        result.suggestions.append(
            "Coupe la vidéo pour ne garder que ta série — l'analyse sera plus rapide et précise"
        )
        score -= 10  # Pas bloquant, juste plus lent à analyser

    # ── Résolution ──────────────────────────────────────────────────────
    max_dim = max(width, height)
    if max_dim < 480:
        result.warnings.append(
            f"Résolution très basse ({width}x{height}). L'analyse sera approximative."
        )
        result.suggestions.append(
            "Passe en 720p ou 1080p dans les réglages de ta caméra"
        )
        result.low_quality_disclaimer = True
        score -= 20
    elif max_dim < min_resolution:
        result.warnings.append(
            f"Résolution basse ({width}x{height}). 720p recommandé pour une analyse précise."
        )
        result.suggestions.append("Filme en 720p minimum pour de meilleurs résultats")
        score -= 10

    # ── FPS ──────────────────────────────────────────────────────────────
    if fps < 10:
        result.warnings.append(
            f"FPS très bas ({fps:.0f}). Les mouvements rapides seront mal captés."
        )
        result.suggestions.append(
            "Désactive le mode slow-motion si activé, ou filme en 30fps minimum"
        )
        result.low_quality_disclaimer = True
        score -= 15
    elif fps < min_fps:
        result.warnings.append(
            f"FPS bas ({fps:.0f}). 30fps recommandé pour capter le tempo précisément."
        )
        score -= 5

    # ── Échantillonner des frames pour checks visuels ───────────────────
    sample = _sample_frames(cap, total_frames, n=5)

    # ── Luminosité et contraste ─────────────────────────────────────────
    brightness, contrast = _check_brightness(sample)
    result.brightness = brightness
    result.contrast = contrast

    if brightness < 20:
        # Quasi noir — bloquant
        result.blocking_errors.append(
            "Vidéo quasi noire — impossible d'analyser. "
            "Assure-toi d'avoir un éclairage suffisant."
        )
        result.suggestions.append(
            "Allume les lumières de la salle et évite de filmer face à une fenêtre"
        )
        score -= 40
    elif brightness < min_brightness:
        result.warnings.append(
            f"Vidéo sombre (luminosité: {brightness:.0f}/255). "
            "L'analyse continue mais sera moins précise."
        )
        result.suggestions.append(
            "Pour la prochaine vidéo : éclairage face à toi, pas dans le dos"
        )
        result.low_quality_disclaimer = True
        score -= 15
    elif brightness < 60:
        result.warnings.append(
            f"Luminosité faible ({brightness:.0f}/255). Un meilleur éclairage améliorerait la précision."
        )
        score -= 5

    # Contraste faible (image "lavée")
    if contrast < 20 and brightness > 30:
        result.warnings.append(
            "Contraste faible — la personne se confond avec l'arrière-plan."
        )
        result.suggestions.append(
            "Porte des vêtements qui contrastent avec le fond de la salle"
        )
        score -= 5

    # ── Stabilité caméra ────────────────────────────────────────────────
    stability = _check_stability(sample)
    result.stability = stability

    if stability < 0.7:
        result.warnings.append(
            "Caméra instable — le tracking sera moins précis."
        )
        result.suggestions.append(
            "Pose ton téléphone sur un support stable (trépied, banc, rack) au lieu de le tenir"
        )
        score -= 10
    elif stability < 0.85:
        result.suggestions.append(
            "Un trépied ou un support fixe améliorerait la précision du tracking"
        )
        score -= 3

    # ── Détection personne ──────────────────────────────────────────────
    person_detected, coverage = _check_person(sample)
    result.person_detected = person_detected
    result.person_coverage = coverage

    if not person_detected:
        result.warnings.append(
            "Personne difficile à détecter sur les frames échantillonnées. "
            "L'analyse continue mais pourrait être moins précise."
        )
        result.suggestions.append(
            "Assure-toi d'être entièrement visible dans le cadre, des pieds à la tête"
        )
        score -= 10
    elif coverage < 0.05:
        result.warnings.append(
            "Tu es trop loin de la caméra — les articulations seront moins précises."
        )
        result.suggestions.append(
            "Rapproche la caméra à 2-3 mètres pour une meilleure détection"
        )
        score -= 5
    elif coverage > 0.6:
        result.warnings.append(
            "Tu es trop près de la caméra — certaines parties du corps sont coupées."
        )
        result.suggestions.append(
            "Recule la caméra pour que tout ton corps soit visible avec un peu de marge"
        )
        score -= 5

    cap.release()

    # ── Score final ─────────────────────────────────────────────────────
    result.quality_score = max(0, min(100, score))

    # Bloquant uniquement si erreurs critiques (vidéo corrompue ou noire)
    result.is_valid = len(result.blocking_errors) == 0

    # Si score très bas mais pas bloquant, on analyse quand même avec disclaimer
    if result.quality_score < 30 and result.is_valid:
        result.low_quality_disclaimer = True

    return result
