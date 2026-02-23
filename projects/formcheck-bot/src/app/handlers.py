"""Business logic — routes incoming WhatsApp messages to the right handler."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from app import database as db
from app import messages as msg
from app import whatsapp as wa
from app.media_handler import (
    cleanup_video,
    publish_annotated_frames,
    save_video,
)
from app.stripe_handler import create_all_checkout_urls
from analysis.html_report import generate_html_report
from analysis.pipeline import PipelineConfig, PipelineResult, run_pipeline_async
from app.report_server import get_report_url, save_report

logger = logging.getLogger(__name__)

# Track active analyses to prevent spam (phone -> True if analysis running)
_active_analyses: dict[str, bool] = {}

# Labels humains pour les frames annotées
_FRAME_LABELS: dict[str, str] = {
    "start": "📸 Début du mouvement",
    "mid": "📸 Point bas (milieu)",
    "end": "📸 Fin du mouvement",
}


async def handle_incoming_message(data: dict) -> None:
    """Top-level dispatcher for every incoming WhatsApp message."""
    phone: str = data["from"]
    name: str | None = data.get("name")

    # Ensure user exists
    user, is_new = await db.get_or_create_user(phone, name)
    if is_new:
        await wa.send_text(phone, msg.WELCOME)
        return

    msg_type: str = data["type"]

    if msg_type == "video":
        await handle_video(user, data)
    elif msg_type == "text":
        await handle_text(user, data)
    else:
        await wa.send_text(phone, msg.UNSUPPORTED_MESSAGE)


async def handle_text(user: db.User, data: dict) -> None:
    """Handle a text message (commands: aide, menu, crédits, forfaits)."""
    text = data.get("text", "").strip().lower()
    phone = user.phone

    if text in ("aide", "help", "?", "menu"):
        await wa.send_text(phone, msg.MENU_TEXT)
    elif text in ("guide", "tournage", "filmer", "comment filmer"):
        await wa.send_text(phone, msg.FILMING_GUIDE)
    elif text in ("crédits", "credits", "solde"):
        await _send_credits_status(user)
    elif text in ("forfaits", "plans", "acheter", "buy"):
        await handle_no_credits(user)
    else:
        await wa.send_text(phone, msg.HELP_TEXT)


async def handle_video(user: db.User, data: dict) -> None:
    """Handle an incoming video: check credits, download via Twilio, analyse."""
    phone = user.phone

    # Refresh user data (prevent stale credit count)
    user_fresh = await db.get_user_by_phone(phone)
    if not user_fresh:
        return
    user = user_fresh

    if not await db.has_credits(user):
        await handle_no_credits(user)
        return

    # Rate limit — one analysis at a time per user
    if _active_analyses.get(phone):
        await wa.send_text(phone, msg.RATE_LIMIT)
        return
    _active_analyses[phone] = True

    # Acknowledge
    await wa.send_text(phone, msg.VIDEO_RECEIVED)

    # Download video from Twilio (media_url from webhook)
    media_url: str = data.get("media_url", "")
    if not media_url:
        logger.error("No media_url in video message data")
        await wa.send_text(phone, msg.ERROR_GENERIC)
        return

    try:
        video_bytes = await wa.download_media(media_url)
    except Exception:
        logger.exception("Failed to download video from Twilio")
        await wa.send_text(phone, msg.ERROR_GENERIC)
        return

    # Validate video size (max 25MB — WhatsApp limit)
    MAX_VIDEO_SIZE = 25 * 1024 * 1024
    if len(video_bytes) > MAX_VIDEO_SIZE:
        await wa.send_text(phone, msg.ERROR_VIDEO_TOO_LARGE)
        return

    if len(video_bytes) < 10_000:  # < 10KB = probably corrupt
        await wa.send_text(phone, msg.ERROR_VIDEO_TOO_SHORT)
        return

    # Save locally
    video_path = save_video(video_bytes)

    # Create analysis record
    analysis = await db.create_analysis(user_id=user.id, video_path=str(video_path))

    # Launch async analysis in background
    asyncio.create_task(
        _run_analysis(phone, user.id, analysis.id, str(video_path))
    )


async def _run_analysis(
    phone: str,
    user_id: int,
    analysis_id: int,
    video_path: str,
) -> None:
    """Run the full CV pipeline async and send results via WhatsApp."""
    try:
        # Run pipeline in thread pool (CPU-bound)
        config = PipelineConfig(
            save_annotated_frames=True,
            save_json=True,
        )
        result: PipelineResult = await run_pipeline_async(video_path, config)

        if not result.success or not result.report:
            logger.error(
                "Pipeline failed for analysis_id=%s errors=%s",
                analysis_id, result.errors,
            )
            await wa.send_text(phone, msg.ERROR_ANALYSIS_FAILED)
            cleanup_video(video_path)
            return

        # Update DB
        await db.update_analysis(
            analysis_id,
            exercise=result.report.exercise_display,
            score=result.report.score,
            report=result.report.report_text,
        )

        # Decrement credit AFTER successful analysis
        await db.decrement_credit(user_id)

        # Generate HTML report
        from app.config import settings
        html_content, report_id, report_token = generate_html_report(
            report=result.report,
            annotated_frames=result.annotated_frames,
            analysis_id=str(analysis_id),
        )
        save_report(report_id, report_token, html_content)
        report_url = get_report_url(settings.base_url, report_id, report_token)

        # Send short WhatsApp message with link
        score = result.report.score
        exercise = result.report.exercise_display
        short_msg = (
            f"🏋️ *FORMCHECK — {exercise}*\n"
            f"📊 Score : *{score}/100*\n\n"
            f"🔗 Ton rapport complet :\n{report_url}\n\n"
            f"🔄 _Corrige et renvoie une vidéo pour voir ta progression !_\n"
            f"⚡ _FORMCHECK by ACHZOD_"
        )
        await wa.send_text(phone, short_msg)

        # Send remaining credits info
        user_updated = await db.get_user_by_phone(phone)
        if user_updated and not user_updated.is_unlimited:
            if user_updated.credits > 0:
                await wa.send_text(phone, f"📊 Il te reste *{user_updated.credits} analyse(s)*.")
            else:
                await wa.send_text(phone, "📊 C'était ta dernière analyse ! Tape *forfaits* pour recharger.")

        # Send 2-3 best annotated frames via WhatsApp
        if result.annotated_frames:
            # Prioritize mid > start > end, max 3
            priority = ["mid", "start", "end"]
            sent = 0
            published = publish_annotated_frames(result.annotated_frames)
            for target_label in priority:
                if sent >= 3:
                    break
                for label, filename, url in published:
                    if label == target_label:
                        caption = _FRAME_LABELS.get(label, f"📸 {label}")
                        try:
                            await wa.send_image(phone, url, caption=caption)
                            sent += 1
                        except Exception:
                            logger.exception("Failed to send annotated frame %s", label)
                        break

        # Cleanup temp video
        cleanup_video(video_path)

    except Exception:
        logger.exception("Analysis failed for analysis_id=%s", analysis_id)
        await wa.send_text(phone, msg.ERROR_GENERIC)
    finally:
        # Always release the rate limit lock
        _active_analyses.pop(phone, None)


async def handle_no_credits(user: db.User) -> None:
    """Send the pricing plans with Stripe checkout links."""
    phone = user.phone
    try:
        checkout_urls = await create_all_checkout_urls(phone)
        await wa.send_plan_buttons(phone, msg.NO_CREDITS, checkout_urls)
    except Exception:
        logger.exception("Failed to create checkout sessions")
        await wa.send_text(phone, msg.ERROR_GENERIC)


async def handle_payment_success(phone: str, plan_key: str, credits: int) -> None:
    """Send a payment confirmation message to the user."""
    from app.stripe_handler import PLANS

    plan = PLANS.get(plan_key, {})
    if plan.get("unlimited"):
        await wa.send_text(phone, msg.PAYMENT_CONFIRMED_UNLIMITED)
    else:
        await wa.send_text(phone, msg.PAYMENT_CONFIRMED_CREDITS.format(credits=credits))


async def _send_credits_status(user: db.User) -> None:
    # Refresh to get latest count
    fresh = await db.get_user_by_phone(user.phone)
    if not fresh:
        return
    if fresh.is_unlimited:
        await wa.send_text(fresh.phone, msg.CREDITS_UNLIMITED)
    elif fresh.credits > 0:
        await wa.send_text(fresh.phone, msg.CREDITS_STATUS.format(credits=fresh.credits))
    else:
        await wa.send_text(fresh.phone, "📊 Tu n'as plus de crédits. Tape *forfaits* pour recharger !")


def _split_message(text: str, max_len: int = 3900) -> list[str]:
    """Split a long message into chunks at newline boundaries."""
    chunks: list[str] = []
    while len(text) > max_len:
        split_at = text.rfind("\n", 0, max_len)
        if split_at <= 0:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks
