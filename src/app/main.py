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
  <title>FormCheck Bot</title>
  <style>
    body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif; background:#f8fafc; color:#0f172a; margin:0; }
    .box { max-width:720px; margin:48px auto; background:#fff; border:1px solid #e2e8f0; border-radius:12px; padding:24px; }
    h1 { margin:0 0 12px; font-size:26px; }
    p { line-height:1.5; color:#334155; }
    code { background:#f1f5f9; padding:2px 6px; border-radius:6px; }
  </style>
</head>
<body>
  <main class="box">
    <h1>FORMCHECK by ACHZOD</h1>
    <p>Service en ligne. L'analyse se fait sur WhatsApp, pas via ce site.</p>
    <p>Commandes utiles: <code>menu</code>, <code>guide</code>, <code>clips</code>.</p>
    <p>Etat API: <a href="/health">/health</a></p>
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
    from app.config import settings
    from app.database import init_db
    from app.debug_log import log_error, get_errors
    from app.handlers import (
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
                "timeout_s": int(settings.minimax_timeout_s or 0),
                "poll_interval_s": float(settings.minimax_poll_interval_s or 0.0),
            },
        }

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
