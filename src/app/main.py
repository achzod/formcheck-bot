"""FastAPI application — Twilio WhatsApp webhook + Stripe webhook + media serving."""

from __future__ import annotations

import logging

import stripe
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse

from app.config import settings
from app.database import init_db
from app.handlers import handle_incoming_message, handle_payment_success
from app.media_handler import get_media_path
from app.stripe_handler import PLANS, construct_webhook_event, handle_checkout_completed
from app.report_server import router as report_router
from app.whatsapp import parse_incoming

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
    """Receive incoming WhatsApp messages from Twilio."""
    form = await request.form()
    body = dict(form)
    
    # Log for debugging (remove in production)
    if settings.debug:
        logger.debug("Twilio webhook body: %s", {k: v for k, v in body.items() if k != "Body"})
    
    data = parse_incoming(body)

    if data:
        # Fire-and-forget: respond to Twilio IMMEDIATELY, process in background
        # This prevents Twilio timeouts (15s limit) from killing the handler
        import asyncio
        asyncio.create_task(_safe_handle(data))

    # Twilio expects a TwiML response (empty is fine for async replies)
    return PlainTextResponse(
        '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="text/xml",
    )


async def _safe_handle(data: dict) -> None:
    """Handle message in background with error protection."""
    try:
        await handle_incoming_message(data)
    except Exception:
        logger.exception("Error handling WhatsApp message from %s", data.get("from", "unknown"))


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
