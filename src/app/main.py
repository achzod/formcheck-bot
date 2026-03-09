"""FastAPI application — Twilio WhatsApp webhook + Stripe webhook + media serving."""

from __future__ import annotations

import asyncio
import contextlib
import html
import re
import sys
import time
import traceback
import uuid
from pathlib import Path
from urllib.parse import quote

# Minimal FastAPI import first
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

app = FastAPI(title="FORMCHECK by ACHZOD", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track import errors
_import_errors: list[str] = []


# Health check always works
@app.get("/", response_class=HTMLResponse)
async def home() -> HTMLResponse:
    return HTMLResponse(
        """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>FORMCHECK by ACHZOD</title>
  <meta name="description" content="Analyse biomecanique de mouvements de musculation sur WhatsApp. Envoie ta video, recois un rapport clair, utile et actionnable.">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Space+Grotesk:wght@400;500;700&display=swap');
    :root {
      --bg: #f6f1e8;
      --paper: rgba(255,255,255,0.78);
      --ink: #111111;
      --muted: #514b45;
      --line: rgba(17,17,17,0.12);
      --brand: #bf5a36;
      --brand-dark: #7a3018;
      --accent: #d8b35d;
      --shadow: 0 24px 80px rgba(70, 38, 18, 0.12);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(216,179,93,0.34), transparent 28%),
        radial-gradient(circle at 85% 15%, rgba(191,90,54,0.20), transparent 24%),
        linear-gradient(180deg, #efe3d0 0%, var(--bg) 38%, #f3eee4 100%);
      font-family: "Space Grotesk", sans-serif;
    }
    a { color: inherit; text-decoration: none; }
    .shell {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 24px 0 64px;
    }
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 28px;
    }
    .brand {
      display: inline-flex;
      align-items: center;
      gap: 12px;
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }
    .brand-mark {
      width: 14px;
      height: 14px;
      border-radius: 999px;
      background: linear-gradient(135deg, var(--brand), var(--accent));
      box-shadow: 0 0 0 6px rgba(191,90,54,0.10);
    }
    .toplink {
      padding: 12px 16px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255,255,255,0.56);
      font-size: 14px;
      font-weight: 600;
    }
    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
      gap: 24px;
      align-items: stretch;
    }
    .hero-main,
    .hero-side,
    .panel,
    .quote {
      border: 1px solid var(--line);
      border-radius: 28px;
      background: var(--paper);
      backdrop-filter: blur(18px);
      box-shadow: var(--shadow);
    }
    .hero-main {
      padding: 28px;
      position: relative;
      overflow: hidden;
    }
    .hero-main::after {
      content: "";
      position: absolute;
      inset: auto -40px -60px auto;
      width: 220px;
      height: 220px;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(216,179,93,0.45), rgba(216,179,93,0));
      pointer-events: none;
    }
    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(17,17,17,0.05);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    h1 {
      margin: 18px 0 14px;
      font-family: "Fraunces", serif;
      font-size: clamp(42px, 7vw, 82px);
      line-height: 0.96;
      letter-spacing: -0.05em;
      max-width: 10ch;
    }
    .lead {
      max-width: 62ch;
      color: var(--muted);
      font-size: 18px;
      line-height: 1.65;
      margin-bottom: 22px;
    }
    .cta-row {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 22px;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      min-height: 48px;
      padding: 0 18px;
      border-radius: 999px;
      font-size: 14px;
      font-weight: 700;
      border: 1px solid transparent;
    }
    .btn-primary {
      background: linear-gradient(135deg, var(--brand), var(--brand-dark));
      color: #fff7f0;
    }
    .btn-secondary {
      background: rgba(255,255,255,0.62);
      border-color: var(--line);
      color: var(--ink);
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .stat {
      padding: 16px;
      border-radius: 20px;
      background: rgba(17,17,17,0.04);
      border: 1px solid rgba(17,17,17,0.05);
    }
    .stat b {
      display: block;
      font-size: 22px;
      margin-bottom: 6px;
    }
    .stat span {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }
    .hero-side {
      padding: 24px;
      display: grid;
      gap: 14px;
      align-content: start;
      background:
        linear-gradient(160deg, rgba(17,17,17,0.96), rgba(56,34,22,0.92));
      color: #f8f1e8;
    }
    .side-kicker {
      color: rgba(248,241,232,0.72);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-weight: 700;
    }
    .side-score {
      font-family: "Fraunces", serif;
      font-size: clamp(44px, 7vw, 76px);
      line-height: 1;
      letter-spacing: -0.05em;
      margin: 0;
    }
    .side-copy {
      color: rgba(248,241,232,0.76);
      line-height: 1.65;
      margin: 0;
    }
    .mini-card {
      padding: 16px;
      border-radius: 20px;
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.12);
    }
    .mini-card strong {
      display: block;
      margin-bottom: 6px;
      font-size: 15px;
    }
    .section-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
      margin-top: 18px;
    }
    .panel {
      padding: 22px;
    }
    .panel h2,
    .quote h2 {
      margin: 0 0 10px;
      font-family: "Fraunces", serif;
      font-size: 28px;
      line-height: 1.05;
      letter-spacing: -0.04em;
    }
    .panel p,
    .quote p {
      margin: 0;
      color: var(--muted);
      line-height: 1.65;
      font-size: 15px;
    }
    .steps {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-top: 18px;
    }
    .step {
      padding: 18px;
      border-radius: 22px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.58);
    }
    .step-index {
      display: inline-flex;
      width: 32px;
      height: 32px;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      margin-bottom: 12px;
      background: rgba(191,90,54,0.12);
      color: var(--brand-dark);
      font-weight: 700;
    }
    .step h3 {
      margin: 0 0 8px;
      font-size: 17px;
    }
    .step p {
      margin: 0;
      color: var(--muted);
      line-height: 1.55;
      font-size: 14px;
    }
    .quote {
      margin-top: 18px;
      padding: 24px;
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 18px;
      align-items: center;
    }
    .quote-box {
      padding: 18px;
      border-radius: 22px;
      background: rgba(191,90,54,0.08);
      border: 1px solid rgba(191,90,54,0.14);
      color: var(--ink);
      font-size: 15px;
      line-height: 1.7;
    }
    .footer-note {
      margin-top: 18px;
      padding: 18px 20px;
      border-radius: 20px;
      background: rgba(17,17,17,0.05);
      color: var(--muted);
      font-size: 14px;
      line-height: 1.6;
    }
    @media (max-width: 980px) {
      .hero,
      .quote,
      .section-grid,
      .steps {
        grid-template-columns: 1fr;
      }
      h1 { max-width: none; }
      .stats { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <div class="topbar">
      <div class="brand">
        <span class="brand-mark"></span>
        <span>FORMCHECK by ACHZOD</span>
      </div>
      <a class="toplink" href="/health">Etat API</a>
    </div>

    <section class="hero">
      <article class="hero-main">
        <div class="eyebrow">Analyse biomecanique sur WhatsApp</div>
        <h1>Ton execution, pas juste un avis.</h1>
        <p class="lead">
          Envoie ta video de musculation sur WhatsApp. Le bot detecte l'exercice,
          relit la serie, estime les reps, le tempo, l'intensite et te renvoie
          un rapport HTML clair, orienté terrain, directement exploitable.
        </p>
        <div class="cta-row">
          <a class="btn btn-primary" href="#process">Voir le process</a>
          <a class="btn btn-secondary" href="#rapport">Ce que contient le rapport</a>
        </div>
        <div class="stats">
          <div class="stat">
            <b>100% WhatsApp</b>
            <span>Aucun upload externe requis dans le flow normal.</span>
          </div>
          <div class="stat">
            <b>Rapport HTML</b>
            <span>Sections lisibles, score, points forts, corrections prioritaires.</span>
          </div>
          <div class="stat">
            <b>Coach-first</b>
            <span>Le retour est pense pour corriger un mouvement, pas pour faire joli.</span>
          </div>
        </div>
      </article>

      <aside class="hero-side">
        <div class="side-kicker">Sortie cible</div>
        <p class="side-score">Score, reps, tempo, intensite.</p>
        <p class="side-copy">
          Le service est concu pour transformer une video brute en feedback utile:
          execution, rythme de serie, repos inter-reps, axes de correction et message clair au client.
        </p>
        <div class="mini-card">
          <strong>Commandes rapides</strong>
          <span><code>menu</code>, <code>guide</code>, <code>clips</code></span>
        </div>
        <div class="mini-card">
          <strong>Usage ideal</strong>
          <span>Camera stable, mouvement entier visible, angle coherent sur toute la serie.</span>
        </div>
        <div class="mini-card">
          <strong>Livrable</strong>
          <span>Resume direct + lien de rapport + media d'analyse selon le cas.</span>
        </div>
      </aside>
    </section>

    <section class="section-grid" id="rapport">
      <article class="panel">
        <h2>Ce que le bot lit</h2>
        <p>
          Exercice probable, nombre de reps, reps completes ou partielles, rythme
          de la serie, densite d'effort, variations de controle et points de rupture visibles.
        </p>
      </article>
      <article class="panel">
        <h2>Ce que le rapport renvoie</h2>
        <p>
          Score global, points positifs, corrections prioritaires, lecture du tempo,
          amplitude, intensite de serie et recommandations de capture pour la prochaine video.
        </p>
      </article>
      <article class="panel">
        <h2>Ce que tu gardes</h2>
        <p>
          Un rendu propre pour le client final, exploitable en coaching, sans noyer
          l'information sous des overlays inutiles ou des formulations vagues.
        </p>
      </article>
    </section>

    <section class="steps" id="process">
      <article class="step">
        <div class="step-index">1</div>
        <h3>Tu filmes</h3>
        <p>Serie complete, cadre stable, mouvement entier visible, angle utile.</p>
      </article>
      <article class="step">
        <div class="step-index">2</div>
        <h3>Tu envoies sur WhatsApp</h3>
        <p>Le bot prend la video, la met en file, puis lance l'analyse automatiquement.</p>
      </article>
      <article class="step">
        <div class="step-index">3</div>
        <h3>Le bot analyse</h3>
        <p>Detection du mouvement, structure de serie, tempo, intensite et synthese biomecanique.</p>
      </article>
      <article class="step">
        <div class="step-index">4</div>
        <h3>Le client recoit le retour</h3>
        <p>Message court sur WhatsApp + lien de rapport HTML detaille et presentable.</p>
      </article>
    </section>

    <section class="quote">
      <div>
        <h2>Le bon usage</h2>
        <p>
          Cette page n'est pas l'interface d'analyse. Le produit vit sur WhatsApp.
          Le site sert de vitrine produit et de point de verification technique.
        </p>
      </div>
      <div class="quote-box">
        <strong>Conseil capture</strong><br>
        Garde la camera fixe, evite les coupes, montre tout le corps et l'amplitude
        complete de la machine ou de la charge. Une meilleure prise donne un meilleur rapport.
      </div>
    </section>

    <div class="footer-note">
      FORMCHECK by ACHZOD. Analyse de mouvements de musculation sur WhatsApp.
      Etat technique disponible sur <a href="/health"><strong>/health</strong></a>.
    </div>
  </main>
</body>
</html>"""
    )


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok" if not _import_errors else "degraded",
        "service": "formcheck",
        "python": sys.version,
        "import_errors": _import_errors[:5] if _import_errors else None,
    }


# Try to import the rest
try:
    import logging
    import stripe
    from app import database as db
    from app.config import settings
    from app.database import init_db
    from app.debug_log import log_error, get_errors
    from app.handlers import (
        complete_remote_minimax_job,
        fail_remote_minimax_job,
        enqueue_uploaded_video,
        handle_incoming_message,
        handle_payment_success,
    )
    from app import messages as msg
    from app import whatsapp as wa
    from app.media_handler import VIDEOS_DIR, cleanup_video, get_media_path
    from app.stripe_handler import (
        PLANS,
        construct_webhook_event,
        handle_checkout_completed,
        handle_subscription_event,
    )
    from app.report_server import router as report_router
    from app.whatsapp import parse_incoming, validate_twilio_signature

    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    app.include_router(report_router)

    _upload_max_mb = max(50, int(settings.upload_max_mb or 0))
    _upload_chunk_mb = max(1, int(settings.upload_chunk_size_mb or 0))
    _UPLOAD_MAX_BYTES = _upload_max_mb * 1024 * 1024
    _UPLOAD_CHUNK_SIZE = _upload_chunk_mb * 1024 * 1024
    _ALLOWED_UPLOAD_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".webm", ".mkv"}
    _failed_media_sids_notified: set[str] = set()
    _failed_media_task: asyncio.Task | None = None
    _FAILED_SID_CACHE_MAX = 2000

    def _normalize_phone(raw: str) -> str:
        cleaned = (raw or "").strip().replace(" ", "").replace("-", "")
        if cleaned.startswith("00"):
            cleaned = "+" + cleaned[2:]
        if cleaned and not cleaned.startswith("+"):
            cleaned = "+" + cleaned
        if not re.match(r"^\+\d{8,15}$", cleaned):
            raise ValueError("invalid_phone")
        return cleaned

    def _build_upload_url(phone: str | None = None) -> str:
        base = settings.base_url.rstrip("/") + "/upload"
        if phone:
            return "{}?phone={}".format(base, quote(phone, safe=""))
        return base

    def _remember_failed_sid(sid: str) -> None:
        if not sid:
            return
        _failed_media_sids_notified.add(sid)
        if len(_failed_media_sids_notified) > _FAILED_SID_CACHE_MAX:
            for old_sid in list(_failed_media_sids_notified)[:-_FAILED_SID_CACHE_MAX]:
                _failed_media_sids_notified.discard(old_sid)

    async def _failed_media_watchdog_loop() -> None:
        poll_interval_s = max(30, int(settings.failed_media_poll_interval_s))
        max_age_s = max(60, int(settings.failed_media_max_age_minutes) * 60)

        while True:
            try:
                failures = await wa.list_failed_inbound_messages(
                    error_code=settings.failed_media_error_code,
                    page_size=80,
                )
                now = time.time()

                for item in sorted(
                    failures,
                    key=lambda x: float(x.get("timestamp") or 0.0),
                ):
                    sid = str(item.get("sid", "") or "")
                    phone = str(item.get("from", "") or "")
                    ts = item.get("timestamp")
                    if not sid or not phone or sid in _failed_media_sids_notified:
                        continue

                    # Ignore stale failures after restart to avoid surprise spam.
                    if ts and (now - float(ts)) > max_age_s:
                        _remember_failed_sid(sid)
                        continue

                    _remember_failed_sid(sid)
                    await wa.send_text(phone, msg.UPLOAD_AUTO_FALLBACK)
                    logger.info(
                        "Auto-fallback sent for failed inbound media sid=%s phone=%s",
                        sid,
                        phone,
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Failed-media watchdog loop error")

            await asyncio.sleep(poll_interval_s)

    def _render_upload_page(
        message: str = "",
        *,
        is_error: bool = False,
        phone_prefill: str = "",
    ) -> str:
        status_color = "#b42318" if is_error else "#027a48"
        status_html = ""
        if message:
            safe_message = html.escape(message, quote=True).replace("\n", "<br>")
            status_html = (
                "<p style='margin:16px 0;padding:12px;border-radius:8px;"
                "background:#f8f9fb;color:{};font-weight:600;'>{}</p>"
            ).format(status_color, safe_message)

        safe_phone = html.escape((phone_prefill or "").strip(), quote=True)
        max_mb = _UPLOAD_MAX_BYTES // (1024 * 1024)
        return """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>FormCheck Upload Video</title>
  <style>
    body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif; background:#f5f7fb; margin:0; }
    .box { max-width:680px; margin:40px auto; background:#fff; border:1px solid #e5e7eb; border-radius:12px; padding:24px; }
    h1 { margin:0 0 8px; font-size:24px; }
    p { color:#475467; line-height:1.45; }
    label { display:block; margin:14px 0 6px; font-weight:600; color:#101828; }
    input { width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid #d0d5dd; border-radius:8px; }
    button { margin-top:18px; width:100%; padding:12px 14px; background:#111827; color:#fff; border:none; border-radius:8px; font-weight:700; cursor:pointer; }
    .hint { font-size:14px; color:#667085; margin-top:8px; }
    .steps { margin-top:8px; color:#344054; }
  </style>
</head>
<body>
  <main class="box">
    <h1>Upload Video Lourde</h1>
    <p>Si ta video depasse 16 MB sur WhatsApp, upload-la ici puis je t'envoie le rapport sur WhatsApp.</p>
    __STATUS__
    <form action="/upload" method="post" enctype="multipart/form-data">
      <label for="phone">Numero WhatsApp (format +33...)</label>
      <input id="phone" name="phone" type="text" required placeholder="+33612345678" value="__PHONE__">

      <label for="video">Video</label>
      <input id="video" name="video" type="file" accept="video/*" required>
      <p class="hint">Max __MAX_MB__ MB. Recommande: 20 a 180 sec, 1080p.</p>

      <button type="submit">Lancer l'analyse</button>
    </form>
    <div class="steps">
      <p>Etapes: 1) Upload 2) Analyse automatique 3) Rapport envoye sur WhatsApp.</p>
    </div>
  </main>
</body>
</html>""".replace("__STATUS__", status_html).replace("__MAX_MB__", str(max_mb)).replace("__PHONE__", safe_phone)

    @app.on_event("startup")
    async def startup() -> None:
        global _failed_media_task
        await init_db()
        logger.info("FORMCHECK bot started 🔥")
        if (
            settings.failed_media_fallback_enabled
            and settings.twilio_account_sid
            and settings.twilio_auth_token
            and settings.twilio_whatsapp_number
        ):
            _failed_media_task = asyncio.create_task(_failed_media_watchdog_loop())
            logger.info(
                "Failed-media watchdog started (error_code=%s, interval=%ss)",
                settings.failed_media_error_code,
                max(30, int(settings.failed_media_poll_interval_s)),
            )

    @app.on_event("shutdown")
    async def shutdown() -> None:
        global _failed_media_task
        if _failed_media_task is not None:
            _failed_media_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await _failed_media_task
            _failed_media_task = None

    @app.get("/health/debug")
    async def health_debug() -> dict:
        return {
            "status": "ok",
            "python": sys.version,
            "test_mode_free": settings.test_mode_free,
            "minimax": {
                "enabled": bool(settings.minimax_enabled),
                "strict_source": bool(settings.minimax_strict_source),
                "fallback_to_local": bool(settings.minimax_fallback_to_local),
                "prefer_motion_coach_chat": bool(settings.minimax_prefer_motion_coach_chat),
                "require_motion_coach_chat": bool(settings.minimax_require_motion_coach_chat),
                "browser_refresh_enabled": bool(settings.minimax_browser_refresh_enabled),
                "browser_only": bool(settings.minimax_browser_only),
                "remote_worker_enabled": bool(settings.minimax_remote_worker_enabled),
                "timeout_s": int(settings.minimax_timeout_s or 0),
                "poll_interval_s": float(settings.minimax_poll_interval_s or 0.0),
            },
        }

    def _internal_worker_token() -> str:
        return str(
            settings.minimax_remote_worker_token
            or settings.render_api_key
            or ""
        ).strip()

    def _require_internal_worker_token(request: Request) -> None:
        expected = _internal_worker_token()
        if not settings.minimax_remote_worker_enabled or not expected:
            raise HTTPException(status_code=503, detail="Remote worker disabled")
        provided = (
            request.headers.get("X-Formcheck-Internal-Token", "")
            or request.query_params.get("token", "")
        ).strip()
        if provided != expected:
            raise HTTPException(status_code=403, detail="Invalid internal token")

    def _require_internal_admin_token(request: Request) -> None:
        expected = str(settings.render_api_key or _internal_worker_token() or "").strip()
        if not expected:
            raise HTTPException(status_code=503, detail="Internal admin token missing")
        provided = (
            request.headers.get("X-Formcheck-Internal-Token", "")
            or request.query_params.get("token", "")
        ).strip()
        if provided != expected:
            raise HTTPException(status_code=403, detail="Invalid internal token")

    @app.post("/internal/minimax/jobs/claim")
    async def claim_minimax_remote_job(request: Request) -> dict:
        _require_internal_worker_token(request)
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        worker_id = str((payload or {}).get("worker_id", "") or "").strip() or "worker"
        job = await db.claim_next_minimax_remote_job(worker_id)
        if not job:
            return {"job": None}
        return {
            "job": {
                "id": int(job.id),
                "analysis_id": int(job.analysis_id),
                "phone": str(job.phone),
                "video_url": "{}/internal/minimax/jobs/{}/video".format(
                    settings.base_url.rstrip("/"),
                    job.id,
                ),
            }
        }

    @app.get("/internal/minimax/jobs/{job_id}/video")
    async def minimax_remote_job_video(job_id: int, request: Request) -> FileResponse:
        _require_internal_worker_token(request)
        job = await db.get_minimax_remote_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        path = Path(job.video_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Video not found")
        return FileResponse(
            path=str(path),
            media_type="video/mp4",
            filename=path.name,
        )

    @app.post("/internal/minimax/jobs/{job_id}/complete")
    async def complete_minimax_job(job_id: int, request: Request) -> dict:
        _require_internal_worker_token(request)
        payload = await request.json()
        analysis_payload = str((payload or {}).get("analysis_payload", "") or "").strip()
        if not analysis_payload:
            raise HTTPException(status_code=400, detail="Missing analysis_payload")
        ok = await complete_remote_minimax_job(job_id, analysis_payload)
        if not ok:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"status": "ok"}

    @app.post("/internal/minimax/jobs/{job_id}/fail")
    async def fail_minimax_job(job_id: int, request: Request) -> dict:
        _require_internal_worker_token(request)
        payload = await request.json()
        error = str((payload or {}).get("error", "") or "").strip() or "Remote worker failed"
        ok = await fail_remote_minimax_job(job_id, error)
        if not ok:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"status": "ok"}

    @app.get("/internal/support/tickets/open")
    async def internal_open_support_tickets(request: Request, limit: int = 50) -> dict:
        _require_internal_admin_token(request)
        rows = await db.list_open_support_tickets(limit=limit)
        tickets = []
        for row in rows:
            tickets.append(
                {
                    "id": int(row.id),
                    "phone": row.phone,
                    "status": row.status,
                    "priority": row.priority,
                    "category": row.category,
                    "subject": row.subject,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
                }
            )
        return {"tickets": tickets}

    @app.get("/internal/customers/{phone}/history")
    async def internal_customer_history(phone: str, request: Request) -> dict:
        _require_internal_admin_token(request)
        user = await db.get_user_by_phone(phone)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        analyses = await db.get_user_analyses(user.id)
        orders = await db.get_recent_customer_orders(phone, limit=10)
        tickets = await db.get_recent_support_tickets(phone, limit=10)
        messages = await db.get_recent_whatsapp_messages(phone, limit=40)
        ticket_messages: dict[str, list[dict[str, str | int | None]]] = {}
        for ticket in tickets:
            history = await db.get_support_ticket_messages(ticket.id, limit=20)
            ticket_messages[str(ticket.id)] = [
                {
                    "id": int(item.id),
                    "author": item.author,
                    "content": item.content,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                }
                for item in history
            ]

        return {
            "customer": {
                "id": int(user.id),
                "phone": user.phone,
                "name": user.name,
                "credits": int(user.credits or 0),
                "is_unlimited": bool(user.is_unlimited),
                "unlimited_expires_at": (
                    user.unlimited_expires_at.isoformat()
                    if user.unlimited_expires_at
                    else None
                ),
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            "analyses": [
                {
                    "id": int(row.id),
                    "exercise": row.exercise,
                    "score": row.score,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in analyses[:30]
            ],
            "orders": [
                {
                    "id": int(row.id),
                    "source": row.source,
                    "external_id": row.external_id,
                    "order_type": row.order_type,
                    "plan_key": row.plan_key,
                    "amount": int(row.amount or 0),
                    "currency": row.currency,
                    "status": row.status,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
                for row in orders
            ],
            "support_tickets": [
                {
                    "id": int(row.id),
                    "status": row.status,
                    "priority": row.priority,
                    "category": row.category,
                    "subject": row.subject,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
                }
                for row in tickets
            ],
            "support_ticket_messages": ticket_messages,
            "messages": [
                {
                    "id": int(row.id),
                    "direction": row.direction,
                    "message_type": row.message_type,
                    "content": row.content,
                    "provider_message_id": row.provider_message_id,
                    "provider_status": row.provider_status,
                    "error_code": row.error_code,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in messages
            ],
        }

    @app.post("/internal/support/tickets/{ticket_id}/status")
    async def internal_update_support_ticket_status(ticket_id: int, request: Request) -> dict:
        _require_internal_admin_token(request)
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        status = str((payload or {}).get("status", "") or "").strip().lower()
        if status not in {"open", "in_progress", "resolved", "closed"}:
            raise HTTPException(status_code=400, detail="Invalid status")
        ticket = await db.set_support_ticket_status(ticket_id, status)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return {
            "status": "ok",
            "ticket": {
                "id": int(ticket.id),
                "status": ticket.status,
                "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            },
        }

    @app.get("/admin", response_class=HTMLResponse)
    async def admin_dashboard(request: Request) -> HTMLResponse:
        _require_internal_admin_token(request)
        html_page = """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>FORMCHECK Admin</title>
  <style>
    :root {
      --bg: #f5f0e8;
      --surface: #fff;
      --ink: #111;
      --muted: #555;
      --line: #ddd3c7;
      --accent: #bf5a36;
      --accent2: #2d5f7a;
      --ok: #2d7a4f;
      --warn: #c45a2d;
      --err: #c4302d;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
    }
    .wrap {
      width: min(1220px, calc(100% - 24px));
      margin: 14px auto 32px;
    }
    .top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--surface);
    }
    .title {
      font-size: 20px;
      font-weight: 800;
      letter-spacing: 0.3px;
    }
    .hint {
      color: var(--muted);
      font-size: 13px;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
    }
    @media (min-width: 1060px) {
      .grid {
        grid-template-columns: 0.9fr 1.1fr;
      }
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--surface);
      overflow: hidden;
    }
    .card-hd {
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .card-bd {
      padding: 12px 14px;
    }
    .controls {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }
    input[type="text"], select, button {
      height: 38px;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 0 10px;
      font-size: 14px;
      background: #fff;
      color: var(--ink);
    }
    button {
      background: #111;
      color: #fff;
      border-color: #111;
      cursor: pointer;
      font-weight: 700;
    }
    button.alt {
      background: #fff;
      color: #111;
      border-color: var(--line);
      font-weight: 600;
    }
    .kpis {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 10px;
    }
    @media (min-width: 740px) {
      .kpis { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    }
    .kpi {
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      background: #faf8f4;
    }
    .kpi .v {
      font-size: 18px;
      font-weight: 800;
      line-height: 1.1;
    }
    .kpi .l {
      font-size: 12px;
      color: var(--muted);
      margin-top: 2px;
    }
    .table-wrap {
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 10px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 640px;
      font-size: 13px;
    }
    th, td {
      border-bottom: 1px solid #eee6dc;
      text-align: left;
      padding: 8px 10px;
      vertical-align: top;
    }
    th {
      background: #f7f3ec;
      position: sticky;
      top: 0;
      z-index: 1;
      font-size: 12px;
      letter-spacing: 0.2px;
      color: #333;
    }
    .badge {
      display: inline-block;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 11px;
      border: 1px solid transparent;
      white-space: nowrap;
    }
    .s-open { background: #fff1eb; border-color: #ffd4c6; color: #8a3417; }
    .s-in_progress { background: #eef5ff; border-color: #cce0ff; color: #1f4b87; }
    .s-resolved { background: #ebf9ef; border-color: #c9ebd5; color: #1b5c38; }
    .s-closed { background: #f0f0f0; border-color: #dfdfdf; color: #555; }
    .muted { color: var(--muted); }
    .stack {
      display: grid;
      gap: 10px;
    }
    .ticket-thread {
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      background: #faf8f4;
    }
    .thread-row {
      margin-top: 7px;
      padding-top: 7px;
      border-top: 1px dashed #e2d8cb;
      font-size: 13px;
      line-height: 1.45;
    }
    .thread-row:first-child {
      margin-top: 0;
      padding-top: 0;
      border-top: none;
    }
    .ok { color: var(--ok); }
    .err { color: var(--err); }
    .toolbar-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      color: #444;
      background: #f7f3ec;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 4px 8px;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div>
        <div class="title">FORMCHECK Admin</div>
        <div class="hint">SAV, commandes, historique client</div>
      </div>
      <div class="toolbar-right">
        <span id="authState" class="mono">verification token...</span>
        <button id="refreshAllBtn" class="alt">Rafraichir</button>
      </div>
    </div>

    <div class="grid">
      <section class="card">
        <div class="card-hd">
          <span>Tickets SAV ouverts</span>
          <div class="controls">
            <select id="ticketLimit">
              <option value="20">20</option>
              <option value="50" selected>50</option>
              <option value="100">100</option>
            </select>
            <button id="refreshTicketsBtn" class="alt">Rafraichir</button>
          </div>
        </div>
        <div class="card-bd">
          <div class="table-wrap">
            <table id="ticketsTable">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Phone</th>
                  <th>Sujet</th>
                  <th>Statut</th>
                  <th>Priorite</th>
                  <th>Maj</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
          <div id="ticketsInfo" class="hint" style="margin-top:8px"></div>
        </div>
      </section>

      <section class="card">
        <div class="card-hd">
          <span>Recherche client</span>
          <div class="controls">
            <input id="phoneInput" type="text" placeholder="+33612345678" style="min-width:220px">
            <button id="loadCustomerBtn">Charger</button>
          </div>
        </div>
        <div class="card-bd">
          <div class="kpis">
            <div class="kpi"><div class="v" id="kpiCustomer">-</div><div class="l">Client</div></div>
            <div class="kpi"><div class="v" id="kpiAnalyses">0</div><div class="l">Analyses</div></div>
            <div class="kpi"><div class="v" id="kpiOrders">0</div><div class="l">Commandes</div></div>
            <div class="kpi"><div class="v" id="kpiTickets">0</div><div class="l">Tickets SAV</div></div>
          </div>

          <div class="stack" id="customerPanels">
            <div class="muted">Entre un numero WhatsApp pour afficher l'historique.</div>
          </div>
        </div>
      </section>
    </div>
  </div>

  <script>
    const qs = new URLSearchParams(window.location.search);
    const token = (qs.get("token") || "").trim();
    const authState = document.getElementById("authState");
    const ticketsInfo = document.getElementById("ticketsInfo");
    const ticketsBody = document.querySelector("#ticketsTable tbody");
    const phoneInput = document.getElementById("phoneInput");
    const customerPanels = document.getElementById("customerPanels");
    const kpiCustomer = document.getElementById("kpiCustomer");
    const kpiAnalyses = document.getElementById("kpiAnalyses");
    const kpiOrders = document.getElementById("kpiOrders");
    const kpiTickets = document.getElementById("kpiTickets");

    function esc(v) {
      return String(v ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function shortDate(iso) {
      if (!iso) return "-";
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return iso;
      return d.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
    }

    async function apiFetch(path, options = {}) {
      if (!token) {
        throw new Error("token manquant dans URL");
      }
      const sep = path.includes("?") ? "&" : "?";
      const url = `${path}${sep}token=${encodeURIComponent(token)}`;
      const baseOpts = { headers: { "Content-Type": "application/json" } };
      const res = await fetch(url, { ...baseOpts, ...options });
      if (!res.ok) {
        let detail = "";
        try {
          const payload = await res.json();
          detail = payload.detail || JSON.stringify(payload);
        } catch (_) {}
        throw new Error(`HTTP ${res.status}${detail ? " - " + detail : ""}`);
      }
      return res.json();
    }

    function statusBadge(status) {
      const safe = (status || "open").toLowerCase();
      return `<span class="badge s-${esc(safe)}">${esc(safe)}</span>`;
    }

    async function loadOpenTickets() {
      const limit = document.getElementById("ticketLimit").value || "50";
      ticketsInfo.textContent = "Chargement...";
      try {
        const data = await apiFetch(`/internal/support/tickets/open?limit=${encodeURIComponent(limit)}`);
        const rows = Array.isArray(data.tickets) ? data.tickets : [];
        ticketsBody.innerHTML = rows.map((t) => `
          <tr>
            <td>#${esc(t.id)}</td>
            <td><button class="alt" data-phone="${esc(t.phone)}" style="height:30px;padding:0 8px">${esc(t.phone)}</button></td>
            <td>${esc(t.subject || "")}<div class="muted">${esc(t.category || "")}</div></td>
            <td>${statusBadge(t.status)}</td>
            <td>${esc(t.priority || "-")}</td>
            <td>${shortDate(t.updated_at)}</td>
            <td>
              <select data-ticket-status="${esc(t.id)}" style="height:30px">
                <option value="open">open</option>
                <option value="in_progress">in_progress</option>
                <option value="resolved">resolved</option>
                <option value="closed">closed</option>
              </select>
              <button data-ticket-save="${esc(t.id)}" style="height:30px;padding:0 8px">OK</button>
            </td>
          </tr>
        `).join("");

        for (const row of rows) {
          const sel = document.querySelector(`select[data-ticket-status="${row.id}"]`);
          if (sel) sel.value = row.status || "open";
        }
        ticketsInfo.textContent = `${rows.length} ticket(s) ouvert(s).`;
      } catch (err) {
        ticketsBody.innerHTML = "";
        ticketsInfo.innerHTML = `<span class="err">Erreur: ${esc(err.message || err)}</span>`;
      }
    }

    function renderTable(headers, rows) {
      if (!rows.length) {
        return `<div class="muted">Aucune donnee</div>`;
      }
      const th = headers.map((h) => `<th>${esc(h)}</th>`).join("");
      const tr = rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("");
      return `<div class="table-wrap"><table><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table></div>`;
    }

    function renderCustomerPanels(payload) {
      const customer = payload.customer || {};
      const analyses = Array.isArray(payload.analyses) ? payload.analyses : [];
      const orders = Array.isArray(payload.orders) ? payload.orders : [];
      const tickets = Array.isArray(payload.support_tickets) ? payload.support_tickets : [];
      const messages = Array.isArray(payload.messages) ? payload.messages : [];
      const ticketMessages = payload.support_ticket_messages || {};

      kpiCustomer.textContent = customer.name || customer.phone || "-";
      kpiAnalyses.textContent = String(analyses.length);
      kpiOrders.textContent = String(orders.length);
      kpiTickets.textContent = String(tickets.length);

      const analysesHtml = renderTable(
        ["ID", "Exercice", "Score", "Date"],
        analyses.map((a) => [
          `#${esc(a.id)}`,
          esc(a.exercise || "-"),
          esc((a.score ?? 0) + "/100"),
          esc(shortDate(a.created_at)),
        ]),
      );

      const ordersHtml = renderTable(
        ["ID", "Plan", "Type", "Montant", "Statut", "Date"],
        orders.map((o) => [
          `#${esc(o.id)}`,
          esc(o.plan_key || "-"),
          esc(o.order_type || "-"),
          esc((((o.amount || 0) / 100).toFixed(2)) + " " + String(o.currency || "eur").toUpperCase()),
          statusBadge(o.status || "pending"),
          esc(shortDate(o.created_at)),
        ]),
      );

      const ticketCards = tickets.map((t) => {
        const thread = Array.isArray(ticketMessages[String(t.id)]) ? ticketMessages[String(t.id)] : [];
        const threadHtml = thread.length
          ? thread.map((m) => `
              <div class="thread-row">
                <strong>${esc(m.author || "client")}</strong>
                <span class="muted"> - ${esc(shortDate(m.created_at))}</span><br>
                ${esc(m.content || "")}
              </div>
            `).join("")
          : '<div class="muted">Pas de messages dans ce ticket.</div>';
        return `
          <div class="ticket-thread">
            <div><strong>#${esc(t.id)} - ${esc(t.subject || "")}</strong></div>
            <div class="muted">${statusBadge(t.status)} | ${esc(t.priority || "normal")} | ${esc(t.category || "general")}</div>
            <div style="margin-top:8px">${threadHtml}</div>
          </div>
        `;
      }).join("");

      const messagesHtml = renderTable(
        ["Date", "Sens", "Type", "Contenu"],
        messages.slice(0, 25).map((m) => [
          esc(shortDate(m.created_at)),
          esc(m.direction || "-"),
          esc(m.message_type || "-"),
          esc(m.content || ""),
        ]),
      );

      customerPanels.innerHTML = `
        <section class="card">
          <div class="card-hd">Profil client</div>
          <div class="card-bd">
            <div><strong>${esc(customer.name || "Sans nom")}</strong> <span class="muted">(${esc(customer.phone || "-")})</span></div>
            <div class="muted" style="margin-top:6px">Credits: ${esc(customer.credits ?? 0)} | Illimite: ${esc(customer.is_unlimited ? "oui" : "non")}</div>
            <div class="muted">Inscription: ${esc(shortDate(customer.created_at))}</div>
          </div>
        </section>
        <section class="card">
          <div class="card-hd">Commandes</div>
          <div class="card-bd">${ordersHtml}</div>
        </section>
        <section class="card">
          <div class="card-hd">Analyses</div>
          <div class="card-bd">${analysesHtml}</div>
        </section>
        <section class="card">
          <div class="card-hd">Tickets SAV</div>
          <div class="card-bd">
            ${ticketCards || '<div class="muted">Aucun ticket.</div>'}
          </div>
        </section>
        <section class="card">
          <div class="card-hd">Derniers messages WhatsApp</div>
          <div class="card-bd">${messagesHtml}</div>
        </section>
      `;
    }

    async function loadCustomer(phoneRaw) {
      const phone = (phoneRaw || "").trim();
      if (!phone) return;
      customerPanels.innerHTML = '<div class="muted">Chargement client...</div>';
      try {
        const data = await apiFetch(`/internal/customers/${encodeURIComponent(phone)}/history`);
        renderCustomerPanels(data);
      } catch (err) {
        customerPanels.innerHTML = `<div class="err">Erreur chargement client: ${esc(err.message || err)}</div>`;
      }
    }

    async function updateTicketStatus(ticketId, status) {
      await apiFetch(`/internal/support/tickets/${ticketId}/status`, {
        method: "POST",
        body: JSON.stringify({ status }),
      });
    }

    document.getElementById("refreshTicketsBtn").addEventListener("click", loadOpenTickets);
    document.getElementById("refreshAllBtn").addEventListener("click", async () => {
      await loadOpenTickets();
      const phone = phoneInput.value.trim();
      if (phone) await loadCustomer(phone);
    });
    document.getElementById("loadCustomerBtn").addEventListener("click", () => loadCustomer(phoneInput.value));
    phoneInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") loadCustomer(phoneInput.value);
    });

    document.body.addEventListener("click", async (e) => {
      const phoneBtn = e.target.closest("[data-phone]");
      if (phoneBtn) {
        const p = phoneBtn.getAttribute("data-phone") || "";
        phoneInput.value = p;
        await loadCustomer(p);
        return;
      }

      const saveBtn = e.target.closest("[data-ticket-save]");
      if (saveBtn) {
        const ticketId = saveBtn.getAttribute("data-ticket-save");
        const sel = document.querySelector(`select[data-ticket-status="${ticketId}"]`);
        const status = sel ? sel.value : "";
        if (!ticketId || !status) return;
        saveBtn.disabled = true;
        try {
          await updateTicketStatus(ticketId, status);
          await loadOpenTickets();
          const currentPhone = phoneInput.value.trim();
          if (currentPhone) await loadCustomer(currentPhone);
        } catch (err) {
          alert("Erreur update ticket: " + (err.message || err));
        } finally {
          saveBtn.disabled = false;
        }
      }
    });

    if (!token) {
      authState.textContent = "token manquant";
      authState.style.color = "#c4302d";
    } else {
      authState.textContent = "token ok";
      authState.style.color = "#2d7a4f";
      loadOpenTickets();
    }
  </script>
</body>
</html>
"""
        return HTMLResponse(html_page, headers={"Cache-Control": "no-store"})

    @app.get("/debug/errors")
    async def debug_errors(token: str = "") -> dict:
        if not settings.render_api_key:
            raise HTTPException(status_code=503, detail="Debug endpoint disabled")
        if token != settings.render_api_key:
            raise HTTPException(status_code=403, detail="Invalid token")
        return {
            "errors": get_errors(),
            "python": sys.version,
            "settings": {
                "test_mode": settings.test_mode,
                "test_mode_free": settings.test_mode_free,
                "debug": settings.debug,
                "minimax_enabled": bool(settings.minimax_enabled),
                "minimax_strict_source": bool(settings.minimax_strict_source),
                "minimax_fallback_to_local": bool(settings.minimax_fallback_to_local),
                "minimax_prefer_motion_coach_chat": bool(settings.minimax_prefer_motion_coach_chat),
                "minimax_require_motion_coach_chat": bool(settings.minimax_require_motion_coach_chat),
                "minimax_browser_refresh_enabled": bool(settings.minimax_browser_refresh_enabled),
                "minimax_browser_only": bool(settings.minimax_browser_only),
                "minimax_remote_worker_enabled": bool(settings.minimax_remote_worker_enabled),
                "minimax_timeout_s": int(settings.minimax_timeout_s or 0),
            },
        }

    @app.get("/media/{filename}")
    async def serve_media(filename: str) -> FileResponse:
        if "/" in filename or "\\" in filename or ".." in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        path = get_media_path(filename)
        if path is None:
            raise HTTPException(status_code=404, detail="Media not found")
        return FileResponse(
            path=str(path),
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    @app.get("/upload")
    async def upload_page(request: Request) -> HTMLResponse:
        return HTMLResponse(
            "<html><body><p>Mode upload externe desactive. Envoie tes videos uniquement sur WhatsApp.</p></body></html>",
            status_code=410,
        )

    @app.post("/upload")
    async def upload_video(phone: str = Form(""), video: UploadFile = File(...)) -> HTMLResponse:
        try:
            await video.close()
        except Exception:
            pass
        return HTMLResponse(
            "<html><body><p>Mode upload externe desactive. Envoie tes videos uniquement sur WhatsApp.</p></body></html>",
            status_code=410,
        )

    _processed_sids: dict[str, bool] = {}

    @app.post("/webhook/whatsapp")
    async def whatsapp_webhook(request: Request) -> PlainTextResponse:
        form = await request.form()
        body = dict(form)

        if settings.verify_twilio_signature:
            twilio_sig = request.headers.get("X-Twilio-Signature", "")
            if not twilio_sig:
                raise HTTPException(status_code=403, detail="Missing Twilio signature")

            # Twilio signs with the exact public webhook URL. Behind proxies/load balancers,
            # request.url may differ, so validate against a small set of likely public URLs.
            candidate_urls: list[str] = [str(request.url)]
            forwarded_proto = request.headers.get("x-forwarded-proto", "")
            forwarded_host = request.headers.get("x-forwarded-host", "")
            host = request.headers.get("host", "")
            path = request.url.path

            if forwarded_proto and forwarded_host:
                candidate_urls.append(f"{forwarded_proto}://{forwarded_host}{path}")
            if host:
                candidate_urls.append(f"https://{host}{path}")
                candidate_urls.append(f"http://{host}{path}")

            # Deduplicate while preserving order.
            checked = []
            for u in candidate_urls:
                if u and u not in checked:
                    checked.append(u)

            if not any(validate_twilio_signature(u, body, twilio_sig) for u in checked):
                logger.warning("Rejected WhatsApp webhook with invalid Twilio signature")
                raise HTTPException(status_code=403, detail="Invalid Twilio signature")
        
        message_sid = body.get("MessageSid", "")
        if message_sid and message_sid in _processed_sids:
            return PlainTextResponse(
                '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                media_type="text/xml",
            )
        if message_sid:
            _processed_sids[message_sid] = True
            if len(_processed_sids) > 500:
                oldest = list(_processed_sids.keys())[:-500]
                for k in oldest:
                    _processed_sids.pop(k, None)
        
        data = parse_incoming(body)
        if data:
            import asyncio
            asyncio.create_task(_safe_handle(data))

        return PlainTextResponse(
            '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="text/xml",
        )

    async def _safe_handle(data: dict) -> None:
        try:
            await handle_incoming_message(data)
        except Exception as exc:
            logger.exception("Error handling WhatsApp message")
            log_error("safe_handle_exception", str(exc), {"phone": data.get("from", "?")})
            try:
                from app.whatsapp import send_text
                from app.messages import ERROR_GENERIC
                await send_text(data.get("from", ""), ERROR_GENERIC)
            except Exception:
                pass

    @app.post("/webhook/stripe")
    async def stripe_webhook(request: Request) -> dict[str, str]:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature", "")
        try:
            event = construct_webhook_event(payload, sig_header)
        except stripe.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            phone = await handle_checkout_completed(session)
            if phone:
                plan_key = session.get("metadata", {}).get("plan", "")
                plan = PLANS.get(plan_key, {})
                credits = plan.get("credits", 0)
                await handle_payment_success(phone, plan_key, credits)
        elif event["type"] in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            await handle_subscription_event(event["type"], event["data"]["object"])

        return {"status": "ok"}

except Exception as e:
    _import_errors.append(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
