"""Gemini 2.0 Flash video-based exercise detection and rep counting.

Sends the FULL video to Gemini, which understands temporal movement
and can identify exercises + count reps far more accurately than
static frame analysis.
"""

import json
import logging
import os
import time
from pathlib import Path

from google import genai
from google.genai import types

_logger = logging.getLogger("formcheck.gemini_detector")


def detect_exercise_gemini(
    video_path: str,
    candidate_exercises: list[str] | None = None,
) -> dict:
    """Detect exercise and count reps using Gemini 2.0 Flash video understanding.
    
    Args:
        video_path: Path to the video file (mp4, mov, etc.)
        candidate_exercises: Optional list of candidate exercise names to help detection
        
    Returns:
        dict with keys: exercise, confidence, reasoning, rep_count
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    
    client = genai.Client(api_key=api_key)
    
    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    file_size_mb = video_file.stat().st_size / (1024 * 1024)
    _logger.info("Uploading video to Gemini: %s (%.1f MB)", video_path, file_size_mb)
    
    # Upload the video file
    uploaded_file = client.files.upload(
        file=video_path,
        config=types.UploadFileConfig(
            mime_type=_get_mime_type(video_path),
            display_name=video_file.name,
        ),
    )
    
    _logger.info("File uploaded: %s, state: %s", uploaded_file.name, uploaded_file.state)
    
    # Wait for processing
    max_wait = 120
    waited = 0
    while uploaded_file.state.name == "PROCESSING" and waited < max_wait:
        time.sleep(2)
        waited += 2
        uploaded_file = client.files.get(name=uploaded_file.name)
    
    if uploaded_file.state.name != "ACTIVE":
        raise RuntimeError(f"Video processing failed: state={uploaded_file.state.name}")
    
    _logger.info("Video ready for analysis (waited %ds)", waited)
    
    # Build the prompt
    candidates_text = ""
    if candidate_exercises:
        candidates_text = (
            "\n\nVoici une liste d'exercices possibles (mais l'exercice peut ne pas être dans cette liste) :\n"
            + ", ".join(candidate_exercises[:30])
        )
    
    prompt = f"""Tu es un expert en musculation et biomécanique. Analyse cette vidéo d'exercice de musculation.

TÂCHE 1 — IDENTIFICATION DE L'EXERCICE :
Regarde attentivement le MOUVEMENT COMPLET dans la vidéo. Identifie l'exercice exact.
ATTENTION : regarde ce que la personne TIENT DANS SES MAINS (barre libre, haltères, câble avec poulie, machine, poids de corps).
Ne te fie PAS au décor ou aux machines visibles en arrière-plan. Regarde UNIQUEMENT l'équipement utilisé par la personne.

TÂCHE 2 — COMPTAGE DES RÉPÉTITIONS :
Compte CHAQUE répétition complète visible dans la vidéo.
Une répétition = un cycle complet du mouvement (phase concentrique + phase excentrique).
Compte précisément. Si tu vois 8 reps, dis 8, pas 3.
{candidates_text}

Réponds UNIQUEMENT avec ce JSON :
{{
    "exercise": "<nom_exercice_en_snake_case>",
    "exercise_fr": "<nom en français>",
    "equipment": "<ce que la personne tient dans ses mains>",
    "confidence": <0.0-1.0>,
    "rep_count": <nombre exact de répétitions complètes>,
    "reasoning": "<explication courte de ce que tu vois>"
}}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=uploaded_file.uri,
                        mime_type=uploaded_file.mime_type,
                    ),
                    types.Part.from_text(text=prompt),
                ],
            ),
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=1000,
            thinking_config=types.ThinkingConfig(
                thinking_budget=0,
            ),
        ),
    )
    
    raw = response.text or ""
    _logger.info("Gemini FULL response: %s", raw)
    
    # Parse JSON — strip markdown code fences if present
    clean = raw.strip()
    if clean.startswith("```"):
        # Remove ```json ... ```
        first_newline = clean.find("\n")
        last_fence = clean.rfind("```")
        if first_newline > 0 and last_fence > first_newline:
            clean = clean[first_newline + 1:last_fence].strip()
    
    start = clean.find("{")
    end = clean.rfind("}") + 1
    if start >= 0 and end > start:
        data = json.loads(clean[start:end])
        result = {
            "exercise": data.get("exercise", "unknown").lower().replace(" ", "_").replace("-", "_"),
            "exercise_fr": data.get("exercise_fr", ""),
            "equipment": data.get("equipment", ""),
            "confidence": float(data.get("confidence", 0.5)),
            "rep_count": int(data.get("rep_count", 0)),
            "reasoning": data.get("reasoning", ""),
        }
        _logger.info(
            "Gemini detected: %s (conf=%.2f, reps=%d, equipment=%s)",
            result["exercise"], result["confidence"], result["rep_count"], result["equipment"],
        )
        
        # Cleanup uploaded file
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception:
            pass
        
        return result
    
    raise ValueError(f"Gemini response not parseable: {clean[:200]}")


def _get_mime_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    mime_map = {
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
        ".3gp": "video/3gpp",
    }
    return mime_map.get(ext, "video/mp4")


# ── Quick test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python gemini_detector.py <video_path>")
        sys.exit(1)
    
    logging.basicConfig(level=logging.INFO)
    result = detect_exercise_gemini(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
