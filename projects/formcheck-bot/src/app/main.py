"""FastAPI application — Twilio WhatsApp webhook + Stripe webhook + media serving."""

from __future__ import annotations

import sys
import traceback

# Minimal FastAPI import first
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse

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
    from app.handlers import handle_incoming_message, handle_payment_success
    from app.media_handler import get_media_path
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

    @app.on_event("startup")
    async def startup() -> None:
        await init_db()
        logger.info("FORMCHECK bot started 🔥")

    @app.get("/health/debug")
    async def health_debug() -> dict:
        return {
            "status": "ok",
            "python": sys.version,
            "test_mode_free": settings.test_mode_free,
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
