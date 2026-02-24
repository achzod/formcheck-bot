"""Endpoint FastAPI pour servir les rapports HTML premium.

Les rapports sont sauvegardés dans media/reports/{analysis_id}.html
avec un token de protection dans l'URL.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter()

REPORTS_DIR = Path("media/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Token store: {analysis_id: token}
_TOKENS_FILE = REPORTS_DIR / ".tokens.json"


def _load_tokens() -> dict[str, str]:
    if _TOKENS_FILE.exists():
        try:
            return json.loads(_TOKENS_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_tokens(tokens: dict[str, str]) -> None:
    _TOKENS_FILE.write_text(json.dumps(tokens))


def save_report(analysis_id: str, token: str, html_content: str) -> Path:
    """Sauvegarde un rapport HTML et enregistre son token.

    Returns:
        Path du fichier sauvegardé.
    """
    filepath = REPORTS_DIR / f"{analysis_id}.html"
    filepath.write_text(html_content, encoding="utf-8")

    tokens = _load_tokens()
    tokens[analysis_id] = token
    _save_tokens(tokens)

    logger.info("Rapport sauvegardé: %s", filepath)
    return filepath


def get_report_url(base_url: str, analysis_id: str, token: str) -> str:
    """Construit l'URL publique du rapport."""
    return f"{base_url.rstrip('/')}/report/{analysis_id}?t={token}"


@router.get("/report/{analysis_id}", response_class=HTMLResponse)
async def serve_report(analysis_id: str, t: str = Query("")) -> HTMLResponse:
    """Sert le rapport HTML avec vérification du token."""
    # Sanitize
    if "/" in analysis_id or "\\" in analysis_id or ".." in analysis_id:
        raise HTTPException(400, "Invalid ID")

    tokens = _load_tokens()
    expected = tokens.get(analysis_id)
    if not expected or t != expected:
        raise HTTPException(403, "Lien invalide ou expiré")

    filepath = REPORTS_DIR / f"{analysis_id}.html"
    if not filepath.exists():
        raise HTTPException(404, "Rapport introuvable")

    return HTMLResponse(
        content=filepath.read_text(encoding="utf-8"),
        headers={"Cache-Control": "public, max-age=86400"},
    )
