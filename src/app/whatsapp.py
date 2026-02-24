"""Twilio WhatsApp client — send messages, images, download media."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from base64 import b64encode

from app.config import settings

logger = logging.getLogger(__name__)

TWILIO_API = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}"
MESSAGES_URL = f"{TWILIO_API}/Messages.json"

def _auth_header() -> dict[str, str]:
    creds = b64encode(f"{settings.twilio_account_sid}:{settings.twilio_auth_token}".encode()).decode()
    return {"Authorization": f"Basic {creds}"}


async def _send_with_retry(client: httpx.AsyncClient, data: dict, max_retries: int = 3) -> httpx.Response:
    """Send a Twilio request with retry on 429 rate limit."""
    for attempt in range(max_retries):
        resp = await client.post(MESSAGES_URL, headers=_auth_header(), data=data)
        if resp.status_code == 429:
            wait = min(5 * (attempt + 1), 15)  # 5s, 10s, 15s
            logger.warning("Twilio 429 rate limit, retry %d/%d in %ds", attempt + 1, max_retries, wait)
            await asyncio.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    # Last attempt — raise if still 429
    resp.raise_for_status()
    return resp


async def send_text(to: str, body: str) -> dict[str, Any]:
    """Send a plain text WhatsApp message via Twilio."""
    MAX_LEN = 1500  # Sandbox safe limit
    chunks = _split_message(body, MAX_LEN)
    result = None
    async with httpx.AsyncClient(timeout=30) as client:
        for i, chunk in enumerate(chunks):
            if i > 0:
                await asyncio.sleep(1.5)  # Rate limit spacing between chunks
            resp = await _send_with_retry(client, {
                "From": f"whatsapp:{settings.twilio_whatsapp_number}",
                "To": f"whatsapp:{to}",
                "Body": chunk,
            })
            result = resp.json()
    return result


def _split_message(text: str, max_len: int) -> list[str]:
    """Split a message into chunks, preferring paragraph breaks."""
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Find best split point: double newline > single newline > space
        cut = text.rfind("\n\n", 0, max_len)
        if cut < max_len // 3:
            cut = text.rfind("\n", 0, max_len)
        if cut < max_len // 3:
            cut = text.rfind(" ", 0, max_len)
        if cut < max_len // 3:
            cut = max_len
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    return chunks


async def send_image(to: str, image_url: str, caption: str | None = None) -> dict[str, Any]:
    """Send an image via Twilio WhatsApp."""
    data: dict[str, str] = {
        "From": f"whatsapp:{settings.twilio_whatsapp_number}",
        "To": f"whatsapp:{to}",
        "MediaUrl": image_url,
    }
    if caption:
        data["Body"] = caption
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await _send_with_retry(client, data)
        return resp.json()


async def send_plan_buttons(to: str, body: str, checkout_urls: dict[str, str]) -> dict[str, Any]:
    """Send forfait options as text with Stripe links."""
    lines = [
        body,
        "",
        f"1️⃣ *Starter* — 5 analyses (29.99€)\n{checkout_urls['starter']}",
        "",
        f"2️⃣ *Pro* — 20 analyses (59.99€)\n{checkout_urls['pro']}",
        "",
        f"3️⃣ *Illimité* — 1 an (99.99€)\n{checkout_urls['unlimited']}",
    ]
    return await send_text(to, "\n".join(lines))


async def download_media(media_url: str) -> bytes:
    """Download media from Twilio (direct URL from webhook)."""
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        resp = await client.get(media_url, headers=_auth_header())
        resp.raise_for_status()
        return resp.content


def parse_incoming(body: dict[str, Any]) -> dict[str, Any] | None:
    """Parse Twilio WhatsApp webhook (form data converted to dict).

    Twilio sends POST form data with fields:
    - From: whatsapp:+XXXXXXXXXXX
    - Body: text content
    - NumMedia: number of media attachments
    - MediaUrl0, MediaContentType0: first media
    """
    try:
        from_number = body.get("From", "").replace("whatsapp:", "")
        if not from_number:
            return None

        result: dict[str, Any] = {
            "from": from_number,
            "name": body.get("ProfileName"),
            "message_id": body.get("MessageSid", ""),
            "timestamp": None,
        }

        num_media = int(body.get("NumMedia", "0"))

        if num_media > 0:
            media_url = body.get("MediaUrl0", "")
            content_type = body.get("MediaContentType0", "")
            if "video" in content_type:
                result["type"] = "video"
                result["media_url"] = media_url
                result["mime_type"] = content_type
            elif "image" in content_type:
                result["type"] = "image"
                result["media_url"] = media_url
                result["mime_type"] = content_type
            else:
                result["type"] = "unsupported"
        else:
            result["type"] = "text"
            result["text"] = body.get("Body", "")

        return result
    except Exception:
        logger.exception("Failed to parse Twilio WhatsApp webhook")
        return None
