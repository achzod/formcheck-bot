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

# Track active analyses to prevent spam (phone -> timestamp when started)
# Auto-expires after 5 minutes to prevent deadlocks
_active_analyses: dict[str, float] = {}
_ANALYSIS_TIMEOUT = 300  # 5 minutes max per analysis

# Morpho flow states are now persisted in DB (morpho_flow_state table).
# Legacy in-memory dicts removed — use db.get_morpho_flow_state() etc.

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

    if not phone:
        logger.warning("No phone number in message data")
        return

    # Ensure user exists
    try:
        user, is_new = await db.get_or_create_user(phone, name)
    except Exception:
        logger.exception("Failed to get/create user for %s", phone)
        await wa.send_text(phone, msg.ERROR_GENERIC)
        return

    if is_new:
        await wa.send_text(phone, msg.WELCOME)
        # Proposer le profil morpho au nouveau client
        await wa.send_text(phone, msg.MORPHO_WELCOME)
        await db.set_morpho_flow_state(phone, "waiting_front")
        return

    msg_type: str = data["type"]

    # Si le client est dans le flow morpho (persisté en DB)
    morpho_flow = await db.get_morpho_flow_state(phone)
    if morpho_flow:
        if msg_type == "text":
            text = data.get("text", "").strip().lower()
            if text == "skip":
                await db.delete_morpho_flow_state(phone)
                await wa.send_text(phone, msg.MORPHO_SKIPPED)
                return
            # Allow "menu", "aide" etc. even during morpho flow
            if text in ("aide", "help", "?", "menu", "credits", "crédits", "solde", "forfaits", "plans"):
                await db.delete_morpho_flow_state(phone)
                await handle_text(user, data)
                return
        if msg_type == "image":
            await handle_morpho_photo(user, data)
            return
        if msg_type == "video":
            # User sent video during morpho flow — cancel morpho, process video
            await db.delete_morpho_flow_state(phone)
            await handle_video(user, data)
            return
        # Texte non-skip pendant le flow morpho → rappeler les instructions
        state = morpho_flow.state
        if state == "waiting_front":
            await wa.send_text(phone, msg.MORPHO_INSTRUCTIONS_FRONT)
        elif state == "waiting_side":
            await wa.send_text(phone, msg.MORPHO_INSTRUCTIONS_SIDE)
        elif state == "waiting_back":
            await wa.send_text(phone, msg.MORPHO_INSTRUCTIONS_BACK)
        return

    if msg_type == "video":
        await handle_video(user, data)
    elif msg_type == "image":
        # Image hors flow morpho → verifier si c'est pour un reset morpho
        await wa.send_text(
            phone,
            "Envoie-moi une *video* pour l'analyse biomecanique.\n"
            "Pour le profil morpho, tape *morpho*.",
        )
    elif msg_type == "text":
        await handle_text(user, data)
    else:
        await wa.send_text(phone, msg.UNSUPPORTED_MESSAGE)


async def handle_text(user: db.User, data: dict) -> None:
    """Handle a text message (commands: aide, menu, crédits, forfaits, morpho)."""
    text = data.get("text", "").strip().lower()
    phone = user.phone

    if not text:
        await wa.send_text(phone, msg.HELP_TEXT)
        return

    if text in ("aide", "help", "?", "menu"):
        await wa.send_text(phone, msg.MENU_TEXT)
    elif text in ("guide", "tournage", "filmer", "comment filmer"):
        await wa.send_text(phone, msg.FILMING_GUIDE)
    elif text in ("crédits", "credits", "solde"):
        await _send_credits_status(user)
    elif text in ("forfaits", "plans", "acheter", "buy"):
        await handle_no_credits(user)
    elif text in ("morpho", "profil", "profil morpho", "morphologie"):
        await _start_morpho_flow(user)
    elif text in ("morpho reset", "reset morpho"):
        # Forcer un nouveau profil morpho
        await db.delete_morpho_flow_state(phone)
        await wa.send_text(phone, msg.MORPHO_INSTRUCTIONS_FRONT)
        await db.set_morpho_flow_state(phone, "waiting_front")
    elif text in ("salut", "hello", "bonjour", "yo", "hey", "hi", "coucou", "slt"):
        await wa.send_text(
            phone,
            "Yo ! Envoie-moi une *video* de ton exercice pour une analyse biomecanique.\n"
            "Tape *menu* pour voir toutes les options.",
        )
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

    from app.config import settings as app_settings
    if not app_settings.test_mode and not app_settings.test_mode_free and not await db.has_credits(user):
        await handle_no_credits(user)
        return

    # Suggerer le profil morpho si le client n'en a pas (une seule fois)
    has_morpho = await db.has_morpho_profile(user.id)
    if not has_morpho:
        await wa.send_text(
            phone,
            "Tu n'as pas encore de profil morphologique. "
            "L'analyse utilisera des seuils generiques.\n"
            "Tape *morpho* apres cette analyse pour creer ton profil "
            "et avoir des analyses personnalisees.",
        )

    # Rate limit — one analysis at a time per user (with auto-expiry)
    import time
    active_since = _active_analyses.get(phone, 0)
    if active_since and (time.time() - active_since) < _ANALYSIS_TIMEOUT:
        await wa.send_text(phone, msg.RATE_LIMIT)
        return
    _active_analyses[phone] = time.time()

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
        # Charger le profil morpho depuis la DB si disponible
        morpho_data = await db.get_morpho_profile_dict(user_id)

        # Progress callback — envoie des messages WhatsApp pendant l'analyse
        import time as _time
        _last_progress_ts = [0.0]  # mutable pour closure
        _PROGRESS_EMOJIS = {
            1: "🔍", 2: "🦴", 3: "📏", 4: "📐",
            5: "🎯", 6: "🔄", 7: "💪", 8: "📊",
            9: "✅", 10: "✍️", 11: "🖼️",
        }
        _PROGRESS_SHORT = {
            1: "Validation", 2: "Extraction", 3: "Lissage",
            4: "Angles", 5: "Détection", 6: "Reps",
            7: "Biomécanique", 8: "Morpho", 9: "Confiance",
            10: "Rapport", 11: "Annotation",
        }

        def _progress_cb(step: int, total: int, desc: str) -> None:
            now = _time.time()
            # Throttle: 1 message max toutes les 10 secondes
            if now - _last_progress_ts[0] < 10.0 and step != total:
                return
            _last_progress_ts[0] = now
            emoji = _PROGRESS_EMOJIS.get(step, "⚙️")
            short = _PROGRESS_SHORT.get(step, desc)
            progress_msg = "{} {} ({}/{})".format(emoji, short, step, total)
            # Fire-and-forget (non-blocking)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(wa.send_text(phone, progress_msg))
            except Exception:
                pass

        # Run pipeline in thread pool (CPU-bound)
        config = PipelineConfig(
            save_annotated_frames=True,
            save_json=True,
            morpho_profile=morpho_data,
            progress_callback=_progress_cb,
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

        # Decrement credit AFTER successful analysis (skip in test/free mode)
        from app.config import settings as app_settings
        if not app_settings.test_mode and not app_settings.test_mode_free:
            await db.decrement_credit(user_id)

        # Generate HTML report
        from app.config import settings
        html_content, report_id, report_token = generate_html_report(
            report=result.report,
            annotated_frames=result.annotated_frames,
            analysis_id=str(analysis_id),
            pipeline_result=result,
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


async def _start_morpho_flow(user: db.User) -> None:
    """Demarre le flow de profil morphologique."""
    phone = user.phone
    has_profile = await db.has_morpho_profile(user.id)
    if has_profile:
        await wa.send_text(phone, msg.MORPHO_ALREADY_EXISTS)
        return
    await wa.send_text(phone, msg.MORPHO_INSTRUCTIONS_FRONT)
    await db.set_morpho_flow_state(phone, "waiting_front")


async def handle_morpho_photo(user: db.User, data: dict) -> None:
    """Recoit une photo pour le profil morphologique (etat persiste en DB)."""
    phone = user.phone
    flow = await db.get_morpho_flow_state(phone)
    if not flow:
        return
    state = flow.state

    # Telecharger l'image
    media_url: str = data.get("media_url", "")
    if not media_url:
        await wa.send_text(phone, msg.MORPHO_ERROR)
        return

    try:
        image_bytes = await wa.download_media(media_url)
    except Exception:
        logger.exception("Failed to download morpho photo from Twilio")
        await wa.send_text(phone, msg.MORPHO_ERROR)
        return

    # Sauvegarder temporairement
    media_dir = Path("media/morpho")
    media_dir.mkdir(parents=True, exist_ok=True)

    if state == "waiting_front":
        photo_path = media_dir / "{}_front.jpg".format(phone)
        photo_path.write_bytes(image_bytes)
        await db.set_morpho_flow_state(phone, "waiting_side", front_path=str(photo_path))
        await wa.send_text(
            phone,
            msg.MORPHO_PHOTO_RECEIVED.format(
                step=1, next_instruction="Maintenant, envoie ta photo de *profil* (cote)."
            ),
        )
        await wa.send_text(phone, msg.MORPHO_INSTRUCTIONS_SIDE)

    elif state == "waiting_side":
        photo_path = media_dir / "{}_side.jpg".format(phone)
        photo_path.write_bytes(image_bytes)
        await db.set_morpho_flow_state(phone, "waiting_back", side_path=str(photo_path))
        await wa.send_text(
            phone,
            msg.MORPHO_PHOTO_RECEIVED.format(
                step=2, next_instruction="Derniere photo : envoie ta photo de *dos*."
            ),
        )
        await wa.send_text(phone, msg.MORPHO_INSTRUCTIONS_BACK)

    elif state == "waiting_back":
        photo_path = media_dir / "{}_back.jpg".format(phone)
        photo_path.write_bytes(image_bytes)

        # Toutes les photos recues → recuperer les chemins depuis la DB
        photos = await db.get_morpho_flow_photos(phone)
        photos["back"] = str(photo_path)

        # Supprimer l'etat flow
        await db.delete_morpho_flow_state(phone)
        await wa.send_text(phone, msg.MORPHO_ANALYZING)

        # Lancer l'analyse en background
        asyncio.create_task(
            _run_morpho_analysis(phone, user.id, photos)
        )


async def _run_morpho_analysis(
    phone: str,
    user_id: int,
    photos: dict[str, str],
) -> None:
    """Lance l'analyse morphologique et envoie les resultats."""
    try:
        from analysis.morpho_profiler import analyze_morphology

        loop = asyncio.get_running_loop()
        # CPU-bound → thread pool
        profile = await loop.run_in_executor(
            None,
            lambda: analyze_morphology(
                front_image_path=photos.get("front"),
                side_image_path=photos.get("side"),
                back_image_path=photos.get("back"),
            ),
        )

        # Sauvegarder en DB
        morpho_data = profile.to_dict()
        await db.save_morpho_profile(user_id, morpho_data)

        # Envoyer le resultat au client
        result_msg = msg.MORPHO_PROFILE_RESULT.format(
            morpho_type=profile.morpho_type.capitalize(),
            squat_type=profile.squat_type.replace("_", " "),
            deadlift_type=profile.deadlift_type,
            bench_grip=profile.bench_grip,
            femur_tibia_ratio=f"{profile.femur_tibia_ratio:.2f}",
            torso_femur_ratio=f"{profile.torso_femur_ratio:.2f}",
            shoulder_hip_ratio=f"{profile.shoulder_hip_ratio:.2f}",
            summary=profile.summary,
        )
        await wa.send_text(phone, result_msg)

        # Envoyer le bilan postural
        if profile.posture.summary:
            recs_text = "\n".join(
                f"{i+1}. {r}" for i, r in enumerate(profile.recommendations[:5])
            )
            posture_msg = msg.MORPHO_POSTURE_REPORT.format(
                posture_summary=profile.posture.summary,
                recommendations=recs_text if recs_text else "Aucune correction posturale necessaire.",
            )
            await wa.send_text(phone, posture_msg)

        logger.info(
            "Morpho profile created for user_id=%s type=%s quality=%.0f%%",
            user_id, profile.morpho_type, profile.analysis_quality * 100,
        )

    except Exception:
        logger.exception("Morpho analysis failed for user_id=%s", user_id)
        await wa.send_text(phone, msg.ERROR_GENERIC)
    finally:
        # Cleanup photos temporaires
        for path in photos.values():
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass


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
