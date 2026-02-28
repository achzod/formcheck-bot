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
    n_frames: int = 0,
    fps: float = 30.0,
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
    
    # Auto-calculate number of frames based on video duration
    # Target: ~3 frames per expected rep (~1 frame per second of video)
    if n_frames <= 0:
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_fps = cap.get(cv2.CAP_PROP_FPS) or fps
        cap.release()
        duration_s = total_frames / video_fps if video_fps > 0 else 10
        # ~2 frames per second for short videos (<15s), ~1.5/s for medium, ~1/s for long
        # Fast exercises (curls, lateral raises) need more temporal resolution
        if duration_s <= 10:
            n_frames = max(12, min(20, int(duration_s * 2.5)))
        elif duration_s <= 20:
            n_frames = max(15, min(20, int(duration_s * 1.5)))
        else:
            n_frames = 20  # cap at 20 for cost
        logger.info("Auto frames: %.1fs video → %d frames", duration_s, n_frames)
    
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
        "Tu es un expert en analyse biomecanique du mouvement avec 15 ans d'experience. "
        "On te montre une sequence de frames extraites d'une video d'exercice de musculation. "
        "Les frames sont dans l'ORDRE CHRONOLOGIQUE, uniformement espacees dans la video. "
        "Ta tache : compter le nombre EXACT de repetitions COMPLETES. "
        "\n\n"
        "REGLES DE COMPTAGE :\n"
        "- Une repetition = un cycle complet (phase excentrique + phase concentrique)\n"
        "- Cherche les CHANGEMENTS DE POSITION entre frames successives\n"
        "- Les frames ou le sujet est dans la meme position = meme phase\n"
        "- Les frames ou le sujet alterne entre 2 positions = repetitions\n"
        "- Ne compte PAS la mise en place ni le rerack\n"
        "- ATTENTION : les exercices rapides (curls, lateral raises, shrugs) ont des reps de 1-2 secondes. "
        "En 8-10 secondes il peut y avoir 8-12 reps !\n"
        "- Chaque fois que tu vois le bras/jambe revenir a la position de depart = 1 rep de plus\n"
        "- Un set typique contient entre 5 et 20 reps. 3 reps ou moins est TRES rare.\n"
        "- En cas de doute, compte CHAQUE alternance de position clairement visible\n"
        "\n"
        "Reponds UNIQUEMENT avec un JSON: {\"rep_count\": <nombre>, \"reasoning\": \"<description frame par frame: F1=bras bas, F2=bras haut=R1, F3=bras bas, F4=bras haut=R2, etc.>\"}"
    )
    
    # Calculate duration for the prompt
    _cap = cv2.VideoCapture(video_path)
    _total = int(_cap.get(cv2.CAP_PROP_FRAME_COUNT))
    _vfps = _cap.get(cv2.CAP_PROP_FPS) or fps
    _cap.release()
    _duration = _total / _vfps if _vfps > 0 else 10
    
    user_text = (
        "Voici {n} frames extraites uniformement d'une video de {duration:.0f} secondes."
        "{hint} "
        "Les frames couvrent toute la duree de la video. "
        "Compte le nombre EXACT de repetitions COMPLETES en observant "
        "les alternances de position du sujet entre les frames."
    ).format(n=len(frames_b64), hint=exercise_hint, duration=_duration)
    
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
