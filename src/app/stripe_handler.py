"""Stripe payment integration."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

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
    metadata = {"phone": phone, "plan": plan_key}
    is_subscription = bool(plan["unlimited"])

    line_item = {
        "price_data": {
            "currency": "eur",
            "unit_amount": plan["price_cents"],
            "product_data": {"name": plan["name"]},
        },
        "quantity": 1,
    }
    if is_subscription:
        line_item["price_data"]["recurring"] = {"interval": "month"}  # type: ignore[index]

    params: dict[str, Any] = {
        "payment_method_types": ["card"],
        "line_items": [line_item],
        "mode": "subscription" if is_subscription else "payment",
        "success_url": settings.stripe_success_url,
        "cancel_url": settings.stripe_cancel_url,
        "metadata": metadata,
        "client_reference_id": phone,
    }
    if is_subscription:
        # Required so customer.subscription.* webhooks carry user metadata.
        params["subscription_data"] = {"metadata": metadata}

    session = stripe.checkout.Session.create(
        **params,
    )
    return session.url  # type: ignore[return-value]


def _parse_utc_from_unix(value: Any) -> dt.datetime | None:
    try:
        if value is None:
            return None
        return dt.datetime.utcfromtimestamp(int(value))
    except (TypeError, ValueError, OSError):
        return None


def _extract_subscription_id(session: dict[str, Any]) -> str | None:
    subscription = session.get("subscription")
    if isinstance(subscription, str):
        return subscription
    if isinstance(subscription, dict):
        sid = subscription.get("id")
        if isinstance(sid, str):
            return sid
    return None


def _get_subscription_period_end(session: dict[str, Any]) -> dt.datetime | None:
    subscription_id = _extract_subscription_id(session)
    if not subscription_id:
        return None
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
    except Exception:
        logger.exception("Failed to fetch Stripe subscription %s", subscription_id)
        return None
    return _parse_utc_from_unix(subscription.get("current_period_end"))


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
    amount: int = int(session.get("amount_total") or 0)

    if not phone or not plan_key or plan_key not in PLANS:
        logger.error("Invalid checkout session metadata: %s", session.get("metadata"))
        return None

    plan = PLANS[plan_key]
    unlimited_until: dt.datetime | None = None
    if plan["unlimited"]:
        # Elite is monthly recurring: set entitlement to current billing period end.
        unlimited_until = _get_subscription_period_end(session)
        if not unlimited_until:
            unlimited_until = dt.datetime.utcnow() + dt.timedelta(days=30)
            logger.warning(
                "Missing subscription period end for session %s, fallback +30 days",
                session_id,
            )

    processed_phone, duplicate = await db.record_payment_and_apply_plan(
        phone=phone,
        stripe_session_id=session_id,
        amount=amount,
        plan=plan_key,
        credits_added=plan["credits"],
        unlimited_until=unlimited_until,
    )

    if processed_phone is None:
        logger.error("User not found for phone %s after payment", phone)
        return None
    if duplicate:
        logger.warning("Duplicate webhook for session %s — skipping", session_id)
        return None
    return processed_phone


async def handle_subscription_event(event_type: str, subscription: dict[str, Any]) -> str | None:
    """Apply entitlement updates from customer.subscription.* webhooks."""
    metadata = subscription.get("metadata", {}) or {}
    phone = metadata.get("phone")
    plan_key = metadata.get("plan", "elite")
    subscription_id = subscription.get("id")

    if not phone:
        logger.warning(
            "Ignoring %s for subscription %s: missing phone metadata",
            event_type,
            subscription_id,
        )
        return None

    plan = PLANS.get(plan_key)
    if not plan or not plan.get("unlimited"):
        logger.info(
            "Ignoring %s for non-unlimited plan %s (subscription %s)",
            event_type,
            plan_key,
            subscription_id,
        )
        return None

    user = await db.get_user_by_phone(phone)
    if not user:
        logger.warning(
            "Ignoring %s for subscription %s: user not found for phone %s",
            event_type,
            subscription_id,
            phone,
        )
        return None

    if event_type == "customer.subscription.deleted":
        await db.disable_unlimited(user.id)
        logger.info("Unlimited disabled for phone %s (subscription %s)", phone, subscription_id)
        return phone

    period_end = _parse_utc_from_unix(subscription.get("current_period_end"))
    if not period_end:
        period_end = dt.datetime.utcnow() + dt.timedelta(days=30)
        logger.warning(
            "Subscription %s missing current_period_end on %s, fallback +30 days",
            subscription_id,
            event_type,
        )

    await db.set_unlimited_until(user.id, period_end)
    logger.info(
        "Unlimited updated for phone %s until %s (subscription %s, event %s)",
        phone,
        period_end.isoformat(),
        subscription_id,
        event_type,
    )
    return phone


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Verify and construct a Stripe webhook event."""
    return stripe.Webhook.construct_event(
        payload,
        sig_header,
        settings.stripe_webhook_secret,
    )
