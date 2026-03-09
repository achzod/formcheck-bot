"""Business logic — routes incoming WhatsApp messages to the right handler."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
import os
from pathlib import Path
import re
import time
import uuid

from app import database as db
from app import messages as msg
from app import whatsapp as wa
from app.config import settings as app_settings
from app.media_handler import (
    VIDEOS_DIR,
    cleanup_video,
    save_video,
)
from app.stripe_handler import create_all_checkout_urls
from analysis.html_report import generate_html_report
from analysis.minimax_motion_coach import (
    MiniMaxAnalysis,
    _analysis_from_payload,
)
from analysis.pipeline import (
    PipelineConfig,
    PipelineResult,
    _apply_minimax_analysis_to_result,
    run_pipeline_async,
)
from app.report_server import get_report_url, save_report

logger = logging.getLogger(__name__)

# Track active analyses to prevent spam (phone -> timestamp when started)
# Auto-expires after 5 minutes to prevent deadlocks
_active_analyses: dict[str, float] = {}
_ANALYSIS_TIMEOUT = 300  # 5 minutes max per analysis

# Morpho flow states are now persisted in DB (morpho_flow_state table).
# Legacy in-memory dicts removed — use db.get_morpho_flow_state() etc.

_LOCAL_VIDEO_MAX_BYTES = 24 * 1024 * 1024
_CLIP_BATCH_TIMEOUT_S = 30 * 60
_MAX_CLIPS_PER_BATCH = 6
_CLIP_HINT_TTL_S = 180
_CLIP_HINT_PATTERNS = (
    re.compile(r"\b([1-9]\d?)\s*/\s*([1-9]\d?)\b"),
    re.compile(r"\b([1-9]\d?)\s+sur\s+([1-9]\d?)\b"),
)


@dataclass
class ClipBatch:
    total_clips: int
    clips: dict[int, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


_pending_clip_batches: dict[str, ClipBatch] = {}
_pending_clip_hints: dict[str, tuple[int, int, float]] = {}


def _is_remote_worker_mode_enabled() -> bool:
    strict_minimax_source = bool(
        app_settings.minimax_enabled and app_settings.minimax_strict_source
    )
    fallback_local_enabled = bool(
        app_settings.minimax_enabled and app_settings.minimax_fallback_to_local
    )
    return bool(
        app_settings.minimax_enabled
        and app_settings.minimax_remote_worker_enabled
        and strict_minimax_source
        and not fallback_local_enabled
    )


def _queue_eta_minutes(position: int) -> int | None:
    avg_job_s = max(30, int(app_settings.minimax_remote_avg_job_seconds or 150))
    if position <= 1:
        return 1
    return int(round(((position - 1) * avg_job_s) / 60.0))


async def _send_existing_queue_status(phone: str) -> None:
    open_job = await db.get_open_minimax_remote_job_for_phone(phone)
    if not open_job:
        await wa.send_text(phone, msg.RATE_LIMIT)
        return
    position = await db.get_minimax_remote_job_position(open_job.id)
    await wa.send_text(
        phone,
        msg.remote_queue_status(position=max(1, position), eta_minutes=_queue_eta_minutes(position)),
    )


def _is_analysis_locked(phone: str) -> bool:
    active_since = _active_analyses.get(phone, 0.0)
    return bool(active_since and (time.time() - active_since) < _ANALYSIS_TIMEOUT)


def _acquire_analysis_lock(phone: str) -> bool:
    if _is_analysis_locked(phone):
        return False
    _active_analyses[phone] = time.time()
    return True


def _ticket_message_from_text(raw_text: str) -> str:
    text = (raw_text or "").strip()
    lowered = text.lower()
    prefixes = ("sav ", "support ", "ticket ")
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return text[len(prefix):].strip()
    return text.strip()


def _ticket_subject_from_message(message: str) -> str:
    clean = " ".join((message or "").split())
    if not clean:
        return "Demande SAV"
    first_chunk = clean.split(".")[0].strip()
    if len(first_chunk) > 90:
        first_chunk = first_chunk[:90].rstrip()
    return first_chunk or "Demande SAV"


def _ticket_meta_from_message(message: str) -> tuple[str, str]:
    low = (message or "").lower()
    if any(k in low for k in ("paiement", "facture", "commande", "abonnement", "stripe")):
        return "billing", "high"
    if any(k in low for k in ("bug", "erreur", "crash", "rapport", "video")):
        return "technical", "high"
    if any(k in low for k in ("conseil", "analyse", "exo", "biomecanique")):
        return "coaching", "normal"
    return "general", "normal"


def _schedule_inbound_message_log(
    *,
    phone: str,
    user_id: int,
    data: dict,
) -> None:
    msg_type = str(data.get("type", "text") or "text")
    inbound_text = str(data.get("text", "") or "")
    if msg_type in {"video", "image"} and not inbound_text.strip():
        inbound_text = "[{}]".format(msg_type)

    async def _runner() -> None:
        try:
            await db.log_whatsapp_message(
                phone=phone,
                direction="inbound",
                message_type=msg_type,
                content=inbound_text,
                provider_message_id=str(data.get("message_id", "") or ""),
                raw_payload=data,
                user_id=user_id,
            )
        except Exception:
            logger.debug("Inbound WhatsApp log write failed", exc_info=True)

    try:
        asyncio.create_task(_runner())
    except Exception:
        logger.debug("Inbound log scheduling failed", exc_info=True)


async def _send_orders_status(user: db.User) -> None:
    orders = await db.get_recent_customer_orders(user.phone, limit=3)
    if not orders:
        await wa.send_text(
            user.phone,
            "Aucune commande enregistree pour le moment.\n"
            "Tape *forfaits* pour voir les plans.",
        )
        return

    lines = ["*Etat commandes*"]
    for idx, order in enumerate(orders, start=1):
        amount_eur = (float(order.amount or 0) / 100.0) if order.amount else 0.0
        plan_label = (order.plan_key or "plan_inconnu").replace("_", " ")
        created = order.created_at.strftime("%d/%m %H:%M") if order.created_at else "date inconnue"
        lines.append(
            "{idx}. {plan} | {status} | {amount:.2f} {currency} | {date}".format(
                idx=idx,
                plan=plan_label,
                status=(order.status or "pending"),
                amount=amount_eur,
                currency=(order.currency or "eur").upper(),
                date=created,
            )
        )
    await wa.send_text(user.phone, "\n".join(lines))


async def _send_customer_history(user: db.User) -> None:
    analyses = await db.get_user_analyses(user.id)
    total_analyses = await db.count_user_analyses(user.id)
    orders = await db.get_recent_customer_orders(user.phone, limit=2)
    tickets = await db.get_recent_support_tickets(user.phone, limit=2)

    lines = ["*Historique client*"]
    lines.append("Analyses total: {}".format(total_analyses))
    if analyses:
        top = analyses[:3]
        lines.append("Dernieres analyses:")
        for idx, row in enumerate(top, start=1):
            created = row.created_at.strftime("%d/%m %H:%M") if row.created_at else "date inconnue"
            lines.append(
                "{}. {} | {}/100 | {}".format(
                    idx,
                    row.exercise or "exercice inconnu",
                    int(row.score or 0),
                    created,
                )
            )
    else:
        lines.append("Dernieres analyses: aucune")

    if orders:
        lines.append("Dernieres commandes:")
        for idx, order in enumerate(orders, start=1):
            amount_eur = (float(order.amount or 0) / 100.0) if order.amount else 0.0
            lines.append(
                "{}. {} | {} | {:.2f} {}".format(
                    idx,
                    (order.plan_key or "plan_inconnu").replace("_", " "),
                    order.status or "pending",
                    amount_eur,
                    (order.currency or "eur").upper(),
                )
            )
    else:
        lines.append("Dernieres commandes: aucune")

    if tickets:
        lines.append("SAV:")
        for ticket in tickets:
            lines.append(
                "#{} | {} | {}".format(
                    ticket.id,
                    ticket.status,
                    ticket.subject,
                )
            )
    else:
        lines.append("SAV: aucun ticket")

    await wa.send_text(user.phone, "\n".join(lines))


async def _open_or_append_support_ticket(user: db.User, raw_text: str) -> None:
    body = _ticket_message_from_text(raw_text)
    if not body:
        await wa.send_text(user.phone, msg.SUPPORT_HELP)
        return

    open_ticket = await db.get_open_support_ticket_for_phone(user.phone)
    if open_ticket:
        await db.add_support_ticket_message(
            open_ticket.id,
            author="client",
            content=body,
        )
        await wa.send_text(
            user.phone,
            msg.support_ticket_updated(open_ticket.id, open_ticket.status or "open"),
        )
        return

    category, priority = _ticket_meta_from_message(body)
    ticket = await db.create_support_ticket(
        phone=user.phone,
        user_id=user.id,
        subject=_ticket_subject_from_message(body),
        description=body,
        category=category,
        priority=priority,
    )
    if not ticket:
        await wa.send_text(user.phone, msg.ERROR_GENERIC)
        return
    await wa.send_text(user.phone, msg.support_ticket_created(ticket.id))


async def _close_open_support_ticket(user: db.User) -> None:
    open_ticket = await db.get_open_support_ticket_for_phone(user.phone)
    if not open_ticket:
        await wa.send_text(user.phone, msg.SUPPORT_NO_OPEN_TICKET)
        return
    await db.set_support_ticket_status(open_ticket.id, "resolved")
    await wa.send_text(user.phone, msg.support_ticket_closed(open_ticket.id))


def _parse_clip_hint(text: str) -> tuple[int, int] | None:
    cleaned = (text or "").strip().lower()
    if not cleaned:
        return None
    for pattern in _CLIP_HINT_PATTERNS:
        match = pattern.search(cleaned)
        if not match:
            continue
        clip_index = int(match.group(1))
        clip_total = int(match.group(2))
        if clip_total < 2 or clip_total > _MAX_CLIPS_PER_BATCH:
            return None
        if clip_index < 1 or clip_index > clip_total:
            return None
        return clip_index, clip_total
    return None


def _infer_video_extension(mime_type: str | None) -> str:
    mt = (mime_type or "").lower()
    if "quicktime" in mt:
        return ".mov"
    if "webm" in mt:
        return ".webm"
    if "x-matroska" in mt or "mkv" in mt:
        return ".mkv"
    if "avi" in mt:
        return ".avi"
    if "mp4" in mt:
        return ".mp4"
    return ".mp4"


def _cleanup_clip_batch(batch: ClipBatch) -> None:
    for clip_path in batch.clips.values():
        cleanup_video(clip_path)


def _cleanup_stale_clip_batches() -> None:
    now = time.time()
    stale_phones: list[str] = []
    for phone, batch in _pending_clip_batches.items():
        if (now - batch.updated_at) > _CLIP_BATCH_TIMEOUT_S:
            stale_phones.append(phone)
    for phone in stale_phones:
        batch = _pending_clip_batches.pop(phone, None)
        if batch:
            _cleanup_clip_batch(batch)


def _register_clip(phone: str, clip_index: int, clip_total: int, clip_path: str) -> tuple[ClipBatch, bool]:
    _cleanup_stale_clip_batches()
    batch = _pending_clip_batches.get(phone)

    if batch is None or batch.total_clips != clip_total:
        if batch is not None:
            _cleanup_clip_batch(batch)
        batch = ClipBatch(total_clips=clip_total)
        _pending_clip_batches[phone] = batch

    previous_path = batch.clips.get(clip_index)
    if previous_path:
        cleanup_video(previous_path)

    batch.clips[clip_index] = clip_path
    batch.updated_at = time.time()

    is_complete = all(i in batch.clips for i in range(1, batch.total_clips + 1))
    return batch, is_complete


def _store_pending_clip_hint(phone: str, clip_index: int, clip_total: int) -> None:
    _pending_clip_hints[phone] = (clip_index, clip_total, time.time())


def _consume_pending_clip_hint(phone: str) -> tuple[int, int] | None:
    hint = _pending_clip_hints.pop(phone, None)
    if not hint:
        return None
    clip_index, clip_total, ts = hint
    if (time.time() - ts) > _CLIP_HINT_TTL_S:
        return None
    return clip_index, clip_total


async def _merge_clips_to_video(clip_paths: list[str]) -> str:
    if not clip_paths:
        raise ValueError("no_clip_paths")
    if len(clip_paths) == 1:
        return clip_paths[0]

    out_path = VIDEOS_DIR / "{}_merged.mp4".format(uuid.uuid4())
    inputs: list[str] = []
    normalize_filters: list[str] = []
    concat_inputs: list[str] = []
    for idx, clip_path in enumerate(clip_paths):
        inputs.extend(["-i", clip_path])
        normalize_filters.append(
            "[{i}:v:0]scale=trunc(iw/2)*2:trunc(ih/2)*2,"
            "setsar=1,fps=30,format=yuv420p[v{i}]".format(i=idx)
        )
        concat_inputs.append("[v{}]".format(idx))
    filter_complex = "{};{}concat=n={}:v=1:a=0[vout]".format(
        ";".join(normalize_filters),
        "".join(concat_inputs),
        len(clip_paths),
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-movflags",
        "+faststart",
        str(out_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await asyncio.wait_for(proc.communicate(), timeout=240)
    if proc.returncode != 0:
        cleanup_video(str(out_path))
        error_tail = stderr.decode("utf-8", errors="ignore")[-1600:]
        raise RuntimeError("ffmpeg_merge_failed: {}".format(error_tail))
    return str(out_path)


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

    _schedule_inbound_message_log(
        phone=phone,
        user_id=user.id,
        data=data,
    )

    if is_new:
        await wa.send_text(phone, msg.WELCOME)
        return

    msg_type = str(data.get("type", "") or "text")

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

    clip_hint = _parse_clip_hint(text)
    if clip_hint is not None:
        clip_index, clip_total = clip_hint
        _store_pending_clip_hint(phone, clip_index, clip_total)
        await wa.send_text(
            phone,
            "OK, envoie maintenant la video du clip {}/{}.".format(
                clip_index,
                clip_total,
            ),
        )
        return

    if text in ("aide", "help", "?", "menu"):
        await wa.send_text(phone, msg.MENU_TEXT)
    elif text in ("sav", "support", "ticket", "aide sav", "help sav"):
        await wa.send_text(phone, msg.SUPPORT_HELP)
    elif text in ("sav close", "sav clos", "ticket close", "ticket resolu", "ticket résolu"):
        await _close_open_support_ticket(user)
    elif text.startswith(("sav ", "support ", "ticket ")):
        await _open_or_append_support_ticket(user, data.get("text", ""))
    elif text in ("commande", "commandes", "order", "orders"):
        await _send_orders_status(user)
    elif text in ("historique", "history", "mon historique"):
        await _send_customer_history(user)
    elif text in ("guide", "tournage", "filmer", "comment filmer"):
        await wa.send_text(phone, msg.FILMING_GUIDE)
    elif text in ("clips", "clip", "multi clips", "multiclips", "multi-clip"):
        await wa.send_text(phone, msg.CLIPS_INSTRUCTIONS)
    elif text in ("upload", "video longue", "video lourde", "grosse video", "gros fichier", "longue", "lourde"):
        await wa.send_text(phone, msg.UPLOAD_INSTRUCTIONS)
    elif text in ("crédits", "credits", "solde"):
        await _send_credits_status(user)
    elif text in ("forfaits", "plans", "acheter", "buy"):
        await handle_no_credits(user)
    elif text in ("morpho", "profil", "profil morpho", "morphologie"):
        await _start_morpho_flow(user)
    elif text in ("morpho reset", "reset morpho"):
        # Forcer un nouveau profil morpho
        await db.delete_morpho_flow_state(phone)
        await wa.send_text(phone, msg.MORPHO_WELCOME)
        await db.set_morpho_flow_state(phone, "waiting_front")
    elif text in ("salut", "hello", "bonjour", "yo", "hey", "hi", "coucou", "slt"):
        await wa.send_text(
            phone,
            "Yo ! Envoie-moi une *video* de ton exercice (max 16 MB sur WhatsApp) pour une analyse biomecanique.\n"
            "Si ta video est plus lourde, coupe-la en 2-4 clips (1/3, 2/3, 3/3).\n"
            "Tape *menu* pour voir toutes les options.",
        )
    else:
        await wa.send_text(phone, msg.HELP_TEXT)


async def handle_video(user: db.User, data: dict) -> None:
    """Handle an incoming video: check credits, download via Twilio, analyse."""
    phone = user.phone
    lock_acquired = False
    analysis_dispatched = False
    saved_video_path: str | None = None
    keep_saved_video = False

    try:
        # Refresh user data (prevent stale credit count)
        user_fresh = await db.get_user_by_phone(phone)
        if not user_fresh:
            return
        user = user_fresh

        if not app_settings.test_mode and not app_settings.test_mode_free and not await db.has_credits(user):
            await handle_no_credits(user)
            return

        if _is_remote_worker_mode_enabled():
            existing_job = await db.get_open_minimax_remote_job_for_phone(phone)
            if existing_job:
                await _send_existing_queue_status(phone)
                return

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

        # Local safeguard limit (Twilio may deliver slightly above 16MB).
        if len(video_bytes) > _LOCAL_VIDEO_MAX_BYTES:
            await wa.send_text(phone, msg.ERROR_VIDEO_TOO_LARGE)
            return

        if len(video_bytes) < 10_000:  # < 10KB = probably corrupt
            await wa.send_text(phone, msg.ERROR_VIDEO_TOO_SHORT)
            return

        clip_hint = _parse_clip_hint(data.get("text", ""))
        if clip_hint is None:
            clip_hint = _consume_pending_clip_hint(phone)
        extension = _infer_video_extension(data.get("mime_type"))
        saved_video_path = str(save_video(video_bytes, extension=extension))

        # Multi-clips mode (caption like 1/3, 2/3, 3/3).
        if clip_hint is not None:
            clip_index, clip_total = clip_hint
            batch, is_complete = _register_clip(
                phone=phone,
                clip_index=clip_index,
                clip_total=clip_total,
                clip_path=saved_video_path,
            )
            keep_saved_video = True

            if not is_complete:
                await wa.send_text(
                    phone,
                    "Clip {idx}/{total} recu ({received}/{total}). "
                    "Envoie le clip suivant.".format(
                        idx=clip_index,
                        total=clip_total,
                        received=len(batch.clips),
                    ),
                )
                return

            if not _acquire_analysis_lock(phone):
                await wa.send_text(phone, msg.RATE_LIMIT)
                return
            lock_acquired = True

            has_morpho = await db.has_morpho_profile(user.id)
            if not has_morpho:
                await wa.send_text(phone, msg.MORPHO_OPTIONAL_NUDGE)

            await wa.send_text(
                phone,
                "Clips recus ({}/{}). Fusion puis analyse en cours...".format(
                    batch.total_clips,
                    batch.total_clips,
                ),
            )
            ordered_clip_paths = [
                batch.clips[i] for i in range(1, batch.total_clips + 1)
            ]
            try:
                merged_video_path = await _merge_clips_to_video(ordered_clip_paths)
            except Exception:
                logger.exception("Clip fusion failed for %s", phone)
                await wa.send_text(phone, msg.ERROR_GENERIC)
                _cleanup_clip_batch(batch)
                _pending_clip_batches.pop(phone, None)
                keep_saved_video = False
                return

            _cleanup_clip_batch(batch)
            _pending_clip_batches.pop(phone, None)
            keep_saved_video = False

            analysis = await db.create_analysis(user_id=user.id, video_path=merged_video_path)
            asyncio.create_task(
                _run_analysis(phone, user.id, analysis.id, merged_video_path)
            )
            analysis_dispatched = True
            return

        # If user started a clip batch but forgot x/y syntax on next clip.
        existing_batch = _pending_clip_batches.get(phone)
        if existing_batch:
            keep_saved_video = False
            await wa.send_text(
                phone,
                "J'attends un format clip (ex: 2/{}). "
                "Renvoie ce clip avec sa numerotation.".format(existing_batch.total_clips),
            )
            return

        if not _acquire_analysis_lock(phone):
            await wa.send_text(phone, msg.RATE_LIMIT)
            return
        lock_acquired = True

        # Suggerer le profil morpho si le client n'en a pas (une seule fois).
        has_morpho = await db.has_morpho_profile(user.id)
        if not has_morpho:
            await wa.send_text(phone, msg.MORPHO_OPTIONAL_NUDGE)

        await wa.send_text(phone, msg.VIDEO_RECEIVED)

        keep_saved_video = True
        analysis = await db.create_analysis(user_id=user.id, video_path=saved_video_path)
        asyncio.create_task(
            _run_analysis(phone, user.id, analysis.id, saved_video_path)
        )
        analysis_dispatched = True
    finally:
        if saved_video_path and not analysis_dispatched and not keep_saved_video:
            cleanup_video(saved_video_path)
        # If analysis never started, release lock immediately (avoid 5min stale lock).
        if lock_acquired and not analysis_dispatched:
            _active_analyses.pop(phone, None)


async def enqueue_uploaded_video(phone: str, video_path: str) -> tuple[bool, str]:
    """Queue analysis for a video uploaded via web form (outside WhatsApp limits)."""
    lock_acquired = False
    analysis_dispatched = False
    try:
        user = await db.get_user_by_phone(phone)
        if not user:
            user, _ = await db.get_or_create_user(phone, None)

        if not app_settings.test_mode and not app_settings.test_mode_free and not await db.has_credits(user):
            await handle_no_credits(user)
            return False, "no_credits"

        if _is_remote_worker_mode_enabled():
            existing_job = await db.get_open_minimax_remote_job_for_phone(phone)
            if existing_job:
                await _send_existing_queue_status(phone)
                return False, "already_queued"

        has_morpho = await db.has_morpho_profile(user.id)
        if not has_morpho:
            await wa.send_text(phone, msg.MORPHO_OPTIONAL_NUDGE)

        import time
        active_since = _active_analyses.get(phone, 0)
        if active_since and (time.time() - active_since) < _ANALYSIS_TIMEOUT:
            await wa.send_text(phone, msg.RATE_LIMIT)
            return False, "rate_limited"
        _active_analyses[phone] = time.time()
        lock_acquired = True

        await wa.send_text(
            phone,
            "Video lourde recue via upload. Analyse en cours...",
        )
        analysis = await db.create_analysis(user_id=user.id, video_path=video_path)
        asyncio.create_task(_run_analysis(phone, user.id, analysis.id, video_path))
        analysis_dispatched = True
        return True, "queued"
    except Exception:
        logger.exception("Failed to queue uploaded video for %s", phone)
        try:
            await wa.send_text(phone, msg.ERROR_GENERIC)
        except Exception:
            pass
        return False, "error"
    finally:
        if not analysis_dispatched:
            cleanup_video(video_path)
        if lock_acquired and not analysis_dispatched:
            _active_analyses.pop(phone, None)


async def _deliver_pipeline_success(
    *,
    phone: str,
    user_id: int,
    analysis_id: int,
    video_path: str,
    result: PipelineResult,
    include_annotated_frames: bool,
    strict_minimax_source: bool,
    fallback_local_enabled: bool,
    preview_frame_path: str | None = None,
) -> None:
    await db.update_analysis(
        analysis_id,
        exercise=result.report.exercise_display,
        score=result.report.score,
        report=result.report.report_text,
    )

    if not app_settings.test_mode and not app_settings.test_mode_free:
        await db.decrement_credit(user_id)

    user_updated = await db.get_user_by_phone(phone)

    html_content, report_id, report_token = generate_html_report(
        report=result.report,
        annotated_frames=(result.annotated_frames if include_annotated_frames else {}),
        analysis_id=str(analysis_id),
        pipeline_result=result,
        client_name=(user_updated.name if user_updated else None),
    )
    save_report(report_id, report_token, html_content)
    report_url = get_report_url(app_settings.base_url, report_id, report_token)

    score = result.report.score
    exercise = result.report.exercise_display
    reps = result.reps.total_reps if result.reps else 0
    intensity_line = ""
    if result.reps and result.reps.total_reps >= 2 and result.reps.intensity_score > 0:
        intensity_line = (
            "\nIntensite: {score}/100 ({label}) — repos moyen {rest:.2f}s"
        ).format(
            score=result.reps.intensity_score,
            label=result.reps.intensity_label,
            rest=result.reps.avg_inter_rep_rest_s,
        )
    elif result.reps and result.reps.total_reps >= 2:
        intensity_line = "\nIntensite: estimation limitee sur cette video."

    credits_line = ""
    if user_updated and not user_updated.is_unlimited:
        if user_updated.credits > 0:
            credits_line = "\n_{} analyse(s) restante(s)_".format(user_updated.credits)
        else:
            credits_line = "\n_Derniere analyse ! Tape *forfaits* pour recharger._"

    short_msg = (
        "*{exercise}* — *{score}/100*"
        "{reps_line}"
        "{intensity_line}\n\n"
        "Rapport HTML:\n"
        "{report_url}"
        "{credits_line}"
    ).format(
        exercise=exercise,
        score=score,
        reps_line=" — {} reps".format(reps) if reps > 0 else "",
        intensity_line=intensity_line,
        report_url=report_url,
        credits_line=credits_line,
    )
    try:
        await wa.send_text(phone, short_msg)
    except Exception:
        logger.exception(
            "Primary WhatsApp report message failed (analysis_id=%s). Retrying minimal link message.",
            analysis_id,
        )
        minimal_msg = (
            "*{exercise}* — *{score}/100*\n\n"
            "Rapport HTML:\n{report_url}"
        ).format(
            exercise=exercise,
            score=score,
            report_url=report_url,
        )
        await wa.send_text(phone, minimal_msg)

    analysis_model = str(result.report.model_used or "").strip() if result.report else ""
    detection_source = ""
    if result.detection and result.detection.top_candidates:
        detection_source = str(
            result.detection.top_candidates[0].get("source", "")
        ).strip()
    if not detection_source and result.detection:
        detection_source = "local_pipeline"
    if not analysis_model:
        analysis_model = "unknown"
    if not detection_source:
        detection_source = "unknown"

    logger.info(
        "Analysis source resolved (analysis_id=%s model=%s detection_source=%s strict=%s fallback=%s)",
        analysis_id,
        analysis_model,
        detection_source,
        strict_minimax_source,
        fallback_local_enabled,
    )
    try:
        from app.debug_log import log_error as _log_dbg

        _log_dbg(
            "analysis_source",
            analysis_model,
            {
                "analysis_id": analysis_id,
                "detection_source": detection_source,
                "strict_minimax_source": strict_minimax_source,
                "fallback_local_enabled": fallback_local_enabled,
            },
        )
    except Exception:
        pass

    cleanup_video(video_path)
    if preview_frame_path:
        try:
            Path(preview_frame_path).unlink(missing_ok=True)
        except Exception:
            pass


async def complete_remote_minimax_job(job_id: int, analysis_payload: str) -> bool:
    job = await db.get_minimax_remote_job(job_id)
    if not job:
        return False
    analysis = _analysis_from_payload(analysis_payload)
    if analysis is None:
        raise ValueError("invalid MiniMax analysis payload")

    result = PipelineResult(
        video_path=job.video_path,
        output_dir=str(Path(job.video_path).parent / "formcheck_output"),
    )
    result = _apply_minimax_analysis_to_result(result, analysis)
    result.success = result.report is not None
    if not result.success or result.report is None:
        raise RuntimeError("remote MiniMax payload did not produce a valid report")
    logger.info(
        "Remote MiniMax payload mapped (job_id=%s raw_slug=%s raw_display=%s mapped_exercise=%s score=%s reps=%s)",
        job_id,
        analysis.exercise_slug,
        analysis.exercise_display,
        result.report.exercise,
        result.report.score,
        result.reps.total_reps if result.reps else 0,
    )

    await _deliver_pipeline_success(
        phone=job.phone,
        user_id=job.user_id,
        analysis_id=job.analysis_id,
        video_path=job.video_path,
        result=result,
        include_annotated_frames=bool(app_settings.report_include_annotated_frames),
        strict_minimax_source=True,
        fallback_local_enabled=False,
    )
    await db.complete_minimax_remote_job(job_id, analysis_payload)
    _active_analyses.pop(job.phone, None)
    return True


async def fail_remote_minimax_job(job_id: int, error: str) -> bool:
    job = await db.fail_minimax_remote_job(job_id, error)
    if not job:
        return False
    await wa.send_text(job.phone, msg.ERROR_MINIMAX_UNAVAILABLE)
    cleanup_video(job.video_path)
    _active_analyses.pop(job.phone, None)
    return True


async def _run_analysis(
    phone: str,
    user_id: int,
    analysis_id: int,
    video_path: str,
) -> None:
    """Run the full CV pipeline async and send results via WhatsApp."""
    keep_lock_after_return = False
    try:
        # Extraire une frame preview AVANT le pipeline (pour fallback GPT-4o garanti)
        preview_frame_path = None
        try:
            import cv2
            _cap = cv2.VideoCapture(video_path)
            _total = int(_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            _cap.set(cv2.CAP_PROP_POS_FRAMES, _total // 2)
            _ret, _frame = _cap.read()
            _cap.release()
            if _ret and _frame is not None:
                preview_frame_path = video_path + "_preview.jpg"
                cv2.imwrite(preview_frame_path, _frame)
        except Exception:
            logger.warning("Could not extract preview frame")

        # Charger le profil morpho depuis la DB si disponible
        morpho_data = await db.get_morpho_profile_dict(user_id)

        # Progress callback — envoie des messages WhatsApp pendant l'analyse
        # IMPORTANT: le callback est appelé depuis un thread pool (run_in_executor)
        # On doit capturer le loop ici (contexte async) et utiliser call_soon_threadsafe
        import time as _time
        _main_loop = asyncio.get_running_loop()
        _last_progress_ts = [0.0]  # mutable pour closure
        # Step descriptions (used only for logging, not sent to user)
        _PROGRESS_SHORT = {
            1: "Validation", 2: "Extraction", 3: "Lissage",
            4: "Angles", 5: "Detection", 6: "Reps",
            7: "Biomecanique", 8: "Morpho", 9: "Confiance",
            10: "Rapport", 11: "Annotation",
        }

        def _progress_cb(step: int, total: int, desc: str) -> None:
            # Only send progress at key milestones — no spam
            # Step 5 = detection done, Step 10 = report generating
            if step not in (5, 10):
                return
            now = _time.time()
            if now - _last_progress_ts[0] < 15.0:
                return
            _last_progress_ts[0] = now
            if step == 5:
                progress_msg = "Exercice detecte. Generation du rapport..."
            elif step == 10:
                progress_msg = "Rapport en cours de finalisation..."
            else:
                return
            try:
                _main_loop.call_soon_threadsafe(
                    asyncio.ensure_future,
                    wa.send_text(phone, progress_msg),
                )
            except Exception:
                pass

        # Run pipeline in thread pool (CPU-bound)
        include_annotated_frames = bool(app_settings.report_include_annotated_frames)
        strict_minimax_source = bool(
            app_settings.minimax_enabled and app_settings.minimax_strict_source
        )
        # Respect runtime policy from env:
        # - if False: strict MiniMax-only (no local rescue path)
        # - if True: local deterministic rescue allowed when MiniMax fails
        fallback_local_enabled = bool(
            app_settings.minimax_enabled and app_settings.minimax_fallback_to_local
        )
        remote_worker_enabled = _is_remote_worker_mode_enabled()

        if remote_worker_enabled:
            pending_jobs = await db.count_pending_minimax_remote_jobs()
            max_pending_jobs = max(5, int(app_settings.minimax_remote_max_pending_jobs or 40))
            if pending_jobs >= max_pending_jobs:
                await wa.send_text(phone, msg.remote_queue_saturated(max_pending_jobs))
                cleanup_video(video_path)
                if preview_frame_path:
                    try:
                        Path(preview_frame_path).unlink(missing_ok=True)
                    except Exception:
                        pass
                _active_analyses.pop(phone, None)
                return

            await db.create_minimax_remote_job(
                analysis_id=analysis_id,
                user_id=user_id,
                phone=phone,
                video_path=video_path,
            )
            queued_job = await db.get_open_minimax_remote_job_for_phone(phone)
            queue_position = 1
            if queued_job:
                queue_position = max(1, await db.get_minimax_remote_job_position(queued_job.id))
            await wa.send_text(
                phone,
                msg.remote_queue_status(
                    position=queue_position,
                    eta_minutes=_queue_eta_minutes(queue_position),
                ),
            )
            keep_lock_after_return = True
            if preview_frame_path:
                try:
                    Path(preview_frame_path).unlink(missing_ok=True)
                except Exception:
                    pass
            logger.info(
                "MiniMax remote worker job queued (analysis_id=%s phone=%s)",
                analysis_id,
                phone,
            )
            return

        config = PipelineConfig(
            save_annotated_frames=include_annotated_frames,
            save_json=True,
            morpho_profile=morpho_data,
            progress_callback=_progress_cb,
            use_minimax_motion_coach=app_settings.minimax_enabled,
            minimax_fallback_to_local=fallback_local_enabled,
            minimax_strict_source=strict_minimax_source,
            # Mode strict demande: analyse MiniMax pure (pas de surcouche locale)
            # quand MiniMax repond.
            minimax_local_augmentation=False,
        )
        result: PipelineResult = await run_pipeline_async(video_path, config)

        # En mode non-strict seulement: filet de securite local si MiniMax indisponible.
        if (
            (not result.success or not result.report)
            and app_settings.minimax_enabled
            and fallback_local_enabled
        ):
            try:
                local_config = PipelineConfig(
                    save_annotated_frames=include_annotated_frames,
                    save_json=True,
                    morpho_profile=morpho_data,
                    progress_callback=_progress_cb,
                    use_minimax_motion_coach=False,
                    minimax_fallback_to_local=False,
                    minimax_strict_source=False,
                    minimax_local_augmentation=False,
                )
                local_result: PipelineResult = await run_pipeline_async(video_path, local_config)
                if local_result.success and local_result.report:
                    logger.warning(
                        "Deterministic local rescue succeeded (analysis_id=%s)",
                        analysis_id,
                    )
                    try:
                        from app.debug_log import log_error as _log_dbg

                        _log_dbg(
                            "analysis_source_override",
                            "local_rescue_after_minimax_failure",
                            {
                                "analysis_id": analysis_id,
                                "strict_minimax_source": strict_minimax_source,
                                "fallback_local_enabled": fallback_local_enabled,
                            },
                        )
                    except Exception:
                        pass
                    result = local_result
                else:
                    logger.error(
                        "Deterministic local rescue failed (analysis_id=%s errors=%s)",
                        analysis_id,
                        local_result.errors,
                    )
            except Exception:
                logger.exception(
                    "Deterministic local rescue exception (analysis_id=%s)",
                    analysis_id,
                )

        if not result.success or not result.report:
            logger.error(
                "Pipeline failed for analysis_id=%s errors=%s",
                analysis_id, result.errors,
            )
            # Log pour debug endpoint
            try:
                from app.debug_log import log_error
                log_error("pipeline_failed", str(result.errors), {
                    "analysis_id": analysis_id,
                    "phone": phone,
                    "video_path": video_path,
                    "timings": str(result.timings),
                    "strict_minimax_source": strict_minimax_source,
                    "fallback_local_enabled": fallback_local_enabled,
                })
            except Exception:
                pass
            if strict_minimax_source and not fallback_local_enabled:
                # Source stricte MiniMax: aucun fallback local/GPT.
                if result.user_messages:
                    await wa.send_text(phone, result.user_messages[0])
                else:
                    await wa.send_text(phone, msg.ERROR_MINIMAX_UNAVAILABLE)
                cleanup_video(video_path)
                if preview_frame_path:
                    try:
                        Path(preview_frame_path).unlink(missing_ok=True)
                    except Exception:
                        pass
                _active_analyses.pop(phone, None)
                return

            # Fallback non-strict : analyse visuelle GPT-4o même si MediaPipe a failli
            fallback_sent = False
            try:
                # Chercher la meilleure frame disponible : extraction > preview
                mid_frame = None
                if result.extraction:
                    mid_frame = result.extraction.key_frame_images.get("mid")
                if not mid_frame or not Path(mid_frame).exists():
                    mid_frame = preview_frame_path
                if mid_frame and Path(mid_frame).exists():
                    import openai, base64, os as _os
                    _key = _os.environ.get("OPENAI_API_KEY", "")
                    if _key:
                        _client = openai.OpenAI(api_key=_key)
                        with open(mid_frame, "rb") as _f:
                            _b64 = base64.b64encode(_f.read()).decode()
                        _resp = _client.chat.completions.create(
                            model="gpt-4o",
                            messages=[{
                                "role": "user",
                                "content": [
                                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{}".format(_b64), "detail": "high"}},
                                    {"type": "text", "text": (
                                        "Tu es un coach expert. Analyse cette video de musculation. "
                                        "Dis en 3-4 phrases : 1) l'exercice effectue, "
                                        "2) les points positifs, 3) les corrections principales. "
                                        "Reponds en francais, ton direct de coach."
                                    )},
                                ],
                            }],
                            max_tokens=300,
                        )
                        _feedback = _resp.choices[0].message.content or ""
                        if _feedback:
                            await wa.send_text(phone, "Analyse rapide (mode secours) :\n\n" + _feedback)
                            fallback_sent = True
            except Exception:
                logger.exception("Fallback GPT-4o vision failed")

            if not fallback_sent:
                await wa.send_text(phone, msg.ERROR_ANALYSIS_FAILED)
            cleanup_video(video_path)
            # Cleanup preview frame
            if preview_frame_path:
                try:
                    Path(preview_frame_path).unlink(missing_ok=True)
                except Exception:
                    pass
            _active_analyses.pop(phone, None)
            return

        if include_annotated_frames:
            conf_score = result.confidence.overall_score if result.confidence else 0
            logger.info(
                "Confidence score: %d — annotated frame %s",
                conf_score,
                "SENT" if conf_score >= 75 else "HIDDEN",
            )

        await _deliver_pipeline_success(
            phone=phone,
            user_id=user_id,
            analysis_id=analysis_id,
            video_path=video_path,
            result=result,
            include_annotated_frames=include_annotated_frames,
            strict_minimax_source=strict_minimax_source,
            fallback_local_enabled=fallback_local_enabled,
            preview_frame_path=preview_frame_path,
        )

    except Exception as exc:
        logger.exception("Analysis failed for analysis_id=%s", analysis_id)
        try:
            from app.debug_log import log_error as _log_err
            _log_err("analysis_exception", str(exc), {
                "analysis_id": analysis_id,
                "phone": phone,
            })
        except Exception:
            pass
        await wa.send_text(phone, msg.ERROR_GENERIC)
    finally:
        # Always release the rate limit lock
        if not keep_lock_after_return:
            _active_analyses.pop(phone, None)


async def _start_morpho_flow(user: db.User) -> None:
    """Demarre le flow de profil morphologique."""
    phone = user.phone
    has_profile = await db.has_morpho_profile(user.id)
    if has_profile:
        await wa.send_text(phone, msg.MORPHO_ALREADY_EXISTS)
        return
    await wa.send_text(phone, msg.MORPHO_WELCOME)
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
        await wa.send_text(fresh.phone, "Tu n'as plus de credits. Tape *forfaits* pour recharger.")


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
