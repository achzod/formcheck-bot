"""Gestion du stockage temporaire des médias (vidéos reçues, images annotées).

Les images annotées doivent être accessibles par URL pour que Twilio puisse
les envoyer via WhatsApp. On les stocke localement et on les sert via un
endpoint FastAPI `/media/{filename}`.
"""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path
from typing import Sequence

from app.config import settings

logger = logging.getLogger(__name__)

# Répertoires de stockage
MEDIA_DIR = Path("media")
VIDEOS_DIR = MEDIA_DIR / "videos"
ANNOTATED_DIR = MEDIA_DIR / "annotated"

# Créer les dossiers au chargement du module
for _dir in (VIDEOS_DIR, ANNOTATED_DIR):
    _dir.mkdir(parents=True, exist_ok=True)


def save_video(data: bytes, extension: str = ".mp4") -> Path:
    """Sauvegarde une vidéo reçue et retourne le chemin.

    Args:
        data: Contenu binaire de la vidéo.
        extension: Extension du fichier (par défaut .mp4).

    Returns:
        Path vers le fichier sauvegardé.
    """
    filename = f"{uuid.uuid4()}{extension}"
    filepath = VIDEOS_DIR / filename
    filepath.write_bytes(data)
    logger.info("Vidéo sauvegardée : %s (%d bytes)", filepath, len(data))
    return filepath


def copy_annotated_image(source_path: str) -> tuple[str, str]:
    """Copie une image annotée dans le dossier media et retourne (filename, public_url).

    Args:
        source_path: Chemin local de l'image annotée (sortie du pipeline).

    Returns:
        Tuple (filename, url publique accessible par Twilio).
    """
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"Image annotée introuvable : {source_path}")

    filename = f"{uuid.uuid4()}_{src.name}"
    dest = ANNOTATED_DIR / filename
    shutil.copy2(src, dest)

    public_url = f"{settings.base_url.rstrip('/')}/media/{filename}"
    logger.info("Image annotée copiée : %s → %s", src.name, public_url)
    return filename, public_url


def publish_annotated_frames(annotated_frames: dict[str, str]) -> list[tuple[str, str, str]]:
    """Publie toutes les images annotées et retourne les URLs.

    Args:
        annotated_frames: Dict {label: chemin_local} issu du pipeline.

    Returns:
        Liste de tuples (label, filename, public_url).
    """
    results: list[tuple[str, str, str]] = []
    for label, path in annotated_frames.items():
        try:
            filename, url = copy_annotated_image(path)
            results.append((label, filename, url))
        except Exception:
            logger.exception("Erreur publication image annotée %s", label)
    return results


def get_media_path(filename: str) -> Path | None:
    """Retourne le chemin d'un fichier media s'il existe.

    Cherche dans le dossier annotated (cas principal).

    Args:
        filename: Nom du fichier.

    Returns:
        Path ou None si introuvable.
    """
    path = ANNOTATED_DIR / filename
    if path.exists():
        return path
    return None


def cleanup_video(video_path: str) -> None:
    """Supprime une vidéo temporaire après traitement."""
    try:
        p = Path(video_path)
        if p.exists():
            p.unlink()
            logger.info("Vidéo temporaire supprimée : %s", video_path)
    except Exception:
        logger.exception("Erreur suppression vidéo %s", video_path)
