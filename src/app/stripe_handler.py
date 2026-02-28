"""Stripe payment integration."""

from __future__ import annotations

import logging

import stripe

from app.config import settings
from app import database as db

logger = logging.getLogger(__name__)

stripe.api_key = settings.stripe_secret_key

# ── Plans ───────────────────────────────────────────────────────────────

PLANS: dict[str, dict] = {
    "essentials": {
        "name": "FORMCHECK Essentials — 5 analyses",
        "price_cents": 1999,
        "credits": 5,
        "unlimited": False,
    },
    "performance": {
        "name": "FORMCHECK Performance — 15 analyses",
        "price_cents": 4999,
        "credits": 15,
        "unlimited": False,
    },
    "elite": {
        "name": "FORMCHECK Elite — Illimite (mensuel)",
        "price_cents": 2999,
        "credits": 0,
        "unlimited": True,
    },
}


async def create_checkout_session(plan_key: str, phone: str) -> str:
    """Create a Stripe Checkout Session and return its URL."""
    plan = PLANS[plan_key]

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "eur",
                    "unit_amount": plan["price_cents"],
                    "product_data": {"name": plan["name"]},
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=settings.stripe_success_url,
        cancel_url=settings.stripe_cancel_url,
        metadata={"phone": phone, "plan": plan_key},
    )
    return session.url  # type: ignore[return-value]


async def create_all_checkout_urls(phone: str) -> dict[str, str]:
    """Create checkout URLs for all three plans."""
    urls: dict[str, str] = {}
    for key in PLANS:
        urls[key] = await create_checkout_session(key, phone)
    return urls


async def handle_checkout_completed(session: dict) -> str | None:
    """Process a completed checkout session.

    Returns the phone number of the user so the caller can send a
    confirmation message, or None if processing fails.
    """
    phone: str | None = session.get("metadata", {}).get("phone")
    plan_key: str | None = session.get("metadata", {}).get("plan")
    session_id: str = session["id"]
    amount: int = session.get("amount_total", 0)

    if not phone or not plan_key or plan_key not in PLANS:
        logger.error("Invalid checkout session metadata: %s", session.get("metadata"))
        return None

    plan = PLANS[plan_key]
    user = await db.get_user_by_phone(phone)
    if not user:
        logger.error("User not found for phone %s after payment", phone)
        return None

    # Idempotency: check if this session_id was already processed
    existing = await db.get_payment_by_session_id(session_id)
    if existing:
        logger.warning("Duplicate webhook for session %s — skipping", session_id)
        return None

    # Record payment
    await db.create_payment(
        user_id=user.id,
        stripe_session_id=session_id,
        amount=amount,
        plan=plan_key,
        credits_added=plan["credits"],
    )

    # Credit the user
    if plan["unlimited"]:
        await db.set_unlimited(user.id)
    else:
        await db.add_credits(user.id, plan["credits"])

    return phone


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Verify and construct a Stripe webhook event."""
    return stripe.Webhook.construct_event(
        payload,
        sig_header,
        settings.stripe_webhook_secret,
    )
