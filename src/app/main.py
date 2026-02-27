"""FastAPI application — Twilio WhatsApp webhook + Stripe webhook + media serving."""

from __future__ import annotations

import sys
print(f"[STARTUP] Python {sys.version}", flush=True)
print("[STARTUP] Starting imports...", flush=True)

import logging

import stripe
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
print("[STARTUP] FastAPI imports OK", flush=True)

from app.config import settings
print("[STARTUP] config OK", flush=True)
from app.database import init_db
print("[STARTUP] database OK", flush=True)
from app.debug_log import log_error, get_errors
print("[STARTUP] debug_log OK", flush=True)
from app.handlers import handle_incoming_message, handle_payment_success
print("[STARTUP] handlers OK", flush=True)
from app.media_handler import get_media_path
print("[STARTUP] media_handler OK", flush=True)
from app.stripe_handler import PLANS, construct_webhook_event, handle_checkout_completed
print("[STARTUP] stripe_handler OK", flush=True)
from app.report_server import router as report_router
print("[STARTUP] report_server OK", flush=True)
from app.whatsapp import parse_incoming
print("[STARTUP] All imports OK", flush=True)

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="FORMCHECK by ACHZOD", version="0.2.0")

app.include_router(report_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    await init_db()
    logger.info("FORMCHECK bot started 🔥")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "formcheck"}


@app.get("/health/debug")
async def health_debug() -> dict:
    """Debug health with version info — no auth required."""
    import sys
    return {
        "status": "ok",
        "python": sys.version,
        "commit": "aad8969",
        "test_mode_free": settings.test_mode_free,
    }


# ── Debug endpoint (last errors + system info) ──────────────────────────

@app.get("/debug/errors")
async def debug_errors(token: str = "") -> dict:
    """Return last errors for debugging. Protected by simple token."""
    if token != settings.render_api_key:
        raise HTTPException(status_code=403, detail="Invalid token")
    import sys
    return {
        "errors": get_errors(),
        "python": sys.version,
        "settings": {
            "test_mode": settings.test_mode,
            "test_mode_free": settings.test_mode_free,
            "debug": settings.debug,
            "base_url": settings.base_url,
        },
    }


# ── Media serving (annotated frames) ────────────────────────────────────


@app.get("/media/{filename}")
async def serve_media(filename: str) -> FileResponse:
    """Serve annotated images so Twilio can fetch them for WhatsApp delivery."""
    # Security: prevent path traversal
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


# ── Twilio WhatsApp webhook ─────────────────────────────────────────────


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request) -> PlainTextResponse:
    """Receive incoming WhatsApp messages from Twilio.
    
    Key design:
    - Return 200 to Twilio in <3s to prevent retries (Twilio retries after 15s)
    - Deduplicate using MessageSid (Twilio resends on timeout/error)
    - All processing happens in background tasks
    """
    form = await request.form()
    body = dict(form)
    
    if settings.debug:
        logger.debug("Twilio webhook body: %s", {k: v for k, v in body.items() if k != "Body"})
    
    # Deduplicate: Twilio retries with same MessageSid
    message_sid = body.get("MessageSid", "")
    if message_sid and message_sid in _processed_sids:
        logger.info("Duplicate MessageSid %s — skipping", message_sid)
        return PlainTextResponse(
            '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="text/xml",
        )
    if message_sid:
        _processed_sids[message_sid] = True
        # Evict old entries to prevent memory leak (keep last 500)
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


# Dedup cache: MessageSid -> True (keeps last 500)
_processed_sids: dict[str, bool] = {}


async def _safe_handle(data: dict) -> None:
    """Handle message in background with error protection."""
    try:
        await handle_incoming_message(data)
    except Exception as exc:
        logger.exception("Error handling WhatsApp message from %s", data.get("from", "unknown"))
        log_error("safe_handle_exception", str(exc), {
            "phone": data.get("from", "unknown"),
            "type": data.get("type", "?"),
        })
        # Try to send error message to user
        try:
            from app.whatsapp import send_text
            from app.messages import ERROR_GENERIC
            await send_text(data.get("from", ""), ERROR_GENERIC)
        except Exception:
            pass


# ── Stripe webhook ──────────────────────────────────────────────────────


@app.post("/webhook/stripe")
async def stripe_webhook(request: Request) -> dict[str, str]:
    """Receive Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = construct_webhook_event(payload, sig_header)
    except stripe.SignatureVerificationError:
        logger.warning("Invalid Stripe webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        phone = await handle_checkout_completed(session)
        if phone:
            plan_key = session.get("metadata", {}).get("plan", "")
            plan = PLANS.get(plan_key, {})
            credits = plan.get("credits", 0)
            await handle_payment_success(phone, plan_key, credits)

    return {"status": "ok"}
