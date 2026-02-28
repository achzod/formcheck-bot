"""GPT-4o Vision-based rep counting.

Extracts N evenly-spaced frames from the video and sends them to GPT-4o
to count repetitions. This is exercise-agnostic and camera-agnostic.

Much more reliable than signal-processing on MediaPipe angles because:
- GPT-4o UNDERSTANDS what a rep looks like visually
- Works on ANY exercise, ANY camera angle
- Doesn't depend on landmark quality
- Tolerant to occlusions, bad lighting, etc.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path

import cv2

logger = logging.getLogger("formcheck.vision_rep_counter")


def _extract_evenly_spaced_frames(
    video_path: str,
    n_frames: int = 10,
    margin_pct: float = 0.05,
) -> list[str]:
    """Extract N evenly-spaced frames from video, skipping margins.
    
    Args:
        video_path: Path to video file.
        n_frames: Number of frames to extract.
        margin_pct: Percentage of total frames to skip at start/end (setup/walkaway).
    
    Returns:
        List of base64-encoded JPEG strings.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error("Cannot open video: %s", video_path)
        return []
    
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total < 5:
        cap.release()
        return []
    
    # Skip margins (setup at start, walkaway at end)
    start_frame = int(total * margin_pct)
    end_frame = int(total * (1.0 - margin_pct))
    usable = end_frame - start_frame
    
    if usable < n_frames:
        n_frames = max(3, usable)
    
    # Evenly space within usable range
    step = usable / n_frames
    frame_indices = [int(start_frame + i * step) for i in range(n_frames)]
    
    frames_b64 = []
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            # Resize to max 512px wide to reduce token cost
            h, w = frame.shape[:2]
            if w > 512:
                scale = 512 / w
                frame = cv2.resize(frame, (512, int(h * scale)))
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            frames_b64.append(base64.b64encode(buf).decode("utf-8"))
    
    cap.release()
    logger.info(
        "Extracted %d frames from video (%d total, indices: %s)",
        len(frames_b64), total, frame_indices,
    )
    return frames_b64


def count_reps_by_vision(
    video_path: str,
    exercise_name: str = "",
    n_frames: int = 10,
) -> int:
    """Count exercise reps using GPT-4o Vision.
    
    Sends N evenly-spaced frames to GPT-4o and asks it to count
    complete repetitions visible in the sequence.
    
    Args:
        video_path: Path to the video file.
        exercise_name: Detected exercise name (helps GPT-4o).
        n_frames: Number of frames to sample.
    
    Returns:
        Number of reps detected (0 if failed).
    """
    import os
    import json
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("No OpenAI API key — cannot count reps by vision.")
        return 0
    
    frames_b64 = _extract_evenly_spaced_frames(video_path, n_frames=n_frames)
    if len(frames_b64) < 3:
        logger.warning("Not enough frames extracted (%d).", len(frames_b64))
        return 0
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except Exception as e:
        logger.error("Failed to init OpenAI client: %s", e)
        return 0
    
    exercise_hint = ""
    if exercise_name:
        exercise_hint = " L'exercice detecte est: {}.".format(exercise_name.replace("_", " "))
    
    system_prompt = (
        "Tu es un expert en analyse biomecanique du mouvement. "
        "On te montre une sequence de frames extraites d'une video d'exercice de musculation. "
        "Les frames sont dans l'ordre chronologique, uniformement espacees dans la video. "
        "Compte le nombre EXACT de repetitions COMPLETES visibles. "
        "Une repetition = un cycle complet du mouvement (montee + descente ou descente + montee). "
        "Ne compte PAS les demi-reps, la mise en position, ou le rerack. "
        "Reponds UNIQUEMENT avec un JSON: {\"rep_count\": <nombre>, \"reasoning\": \"<explication courte>\"}"
    )
    
    user_text = (
        "Voici {n} frames extraites uniformement d'une video d'exercice."
        "{hint} "
        "Compte le nombre EXACT de repetitions COMPLETES. "
        "Regarde les changements de position entre les frames successives "
        "pour identifier chaque cycle complet du mouvement."
    ).format(n=len(frames_b64), hint=exercise_hint)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        *[
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "data:image/jpeg;base64,{}".format(b64),
                                    "detail": "low",  # low detail = fewer tokens
                                },
                            }
                            for b64 in frames_b64
                        ],
                        {"type": "text", "text": user_text},
                    ],
                },
            ],
            max_tokens=150,
            temperature=0.1,
        )
        
        content = response.choices[0].message.content or ""
        logger.info("Vision rep count raw response: %s", content[:200])
        
        # Parse JSON
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(content[start:end])
            count = int(data.get("rep_count", 0))
            reasoning = data.get("reasoning", "")
            logger.info("Vision rep count: %d reps — %s", count, reasoning)
            return max(0, count)
        
        logger.warning("Could not parse vision rep count response: %s", content[:200])
        return 0
        
    except Exception as e:
        logger.error("Vision rep counting failed: %s", e)
        return 0
