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
