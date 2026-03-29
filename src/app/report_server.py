"""Endpoint FastAPI pour servir les rapports HTML premium.

Les rapports sont sauvegardés en DB (persistent) et en fichier (cache).
La DB est la source de vérité — les fichiers sont un fallback rapide.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter()

REPORTS_DIR = Path("media/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

_TOKENS_FILE = REPORTS_DIR / ".tokens.json"


def _load_tokens() -> dict[str, str]:
    if _TOKENS_FILE.exists():
        try:
            return json.loads(_TOKENS_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_tokens(tokens: dict[str, str]) -> None:
    tmp = _TOKENS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(tokens), encoding="utf-8")
    tmp.replace(_TOKENS_FILE)


def _token_sidecar_path(analysis_id: str) -> Path:
    return REPORTS_DIR / ".{}.token".format(analysis_id)


def _resolve_base_url(base_url: str) -> str:
    candidates = [
        base_url,
        os.environ.get("BASE_URL", ""),
        os.environ.get("RENDER_EXTERNAL_URL", ""),
        "https://formcheck.achzodcoaching.com",
    ]
    for candidate in candidates:
        value = (candidate or "").strip()
        if value.startswith("https://") or value.startswith("http://"):
            return value.rstrip("/")
    return "https://formcheck.achzodcoaching.com"


def save_report(analysis_id: str, token: str, html_content: str) -> Path:
    """Sauvegarde un rapport HTML en fichier + en DB."""
    # File (cache)
    filepath = REPORTS_DIR / f"{analysis_id}.html"
    html_tmp = filepath.with_suffix(".html.tmp")
    html_tmp.write_text(html_content, encoding="utf-8")
    html_tmp.replace(filepath)

    sidecar_path = _token_sidecar_path(analysis_id)
    sidecar_tmp = Path(str(sidecar_path) + ".tmp")
    sidecar_tmp.write_text(token, encoding="utf-8")
    sidecar_tmp.replace(sidecar_path)

    tokens = _load_tokens()
    tokens[analysis_id] = token
    _save_tokens(tokens)

    # DB (persistent — survives redeploys)
    try:
        import asyncio
        from app.database import save_report_to_db
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(save_report_to_db(analysis_id, token, html_content))
        else:
            loop.run_until_complete(save_report_to_db(analysis_id, token, html_content))
    except Exception:
        logger.exception("Failed to save report to DB (analysis_id=%s) — file fallback only", analysis_id)

    logger.info("Rapport sauvegardé: %s", filepath)
    return filepath


def get_report_url(base_url: str, analysis_id: str, token: str) -> str:
    """Construit l'URL publique du rapport."""
    resolved = _resolve_base_url(base_url)
    return f"{resolved}/report/{analysis_id}?t={token}"


@router.get("/report/{analysis_id}", response_class=HTMLResponse)
async def serve_report(analysis_id: str, t: str = Query("")) -> HTMLResponse:
    """Sert le rapport HTML — fichier d'abord, DB en fallback. Jamais d'expiration."""
    if "/" in analysis_id or "\\" in analysis_id or ".." in analysis_id:
        raise HTTPException(400, "Invalid ID")

    # 1. Try file system (fast)
    filepath = REPORTS_DIR / f"{analysis_id}.html"
    expected = ""
    sidecar = _token_sidecar_path(analysis_id)
    if sidecar.exists():
        try:
            expected = sidecar.read_text(encoding="utf-8").strip()
        except Exception:
            expected = ""
    if not expected:
        tokens = _load_tokens()
        expected = tokens.get(analysis_id, "")

    if expected and t == expected and filepath.exists():
        return HTMLResponse(
            content=filepath.read_text(encoding="utf-8"),
            headers={"Cache-Control": "public, max-age=86400"},
        )

    # 2. Fallback to DB (persistent — survives redeploys)
    try:
        from app.database import get_report_from_db
        report = await get_report_from_db(analysis_id)
        if report and t == report.token:
            # Restore file cache for next time
            try:
                filepath.write_text(report.html_content, encoding="utf-8")
                _token_sidecar_path(analysis_id).write_text(report.token, encoding="utf-8")
            except Exception:
                pass
            return HTMLResponse(
                content=report.html_content,
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except Exception:
        logger.exception("DB fallback failed for report %s", analysis_id)

    raise HTTPException(403, "Lien invalide ou expiré")
