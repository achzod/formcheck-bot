"""MiniMax Motion Coach integration (video upload + chat analysis).

Supported transports:
- direct API (legacy): signed web API calls (upload + send + polling)
- browser-only (preferred when enabled): Playwright UI automation with AI Motion Coach
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import mimetypes
import os
import re
import sqlite3
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, field
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urlparse

import httpx

logger = logging.getLogger("formcheck.minimax")

_SIGNING_SECRET = "I*7Cf%WZ#S&%1RlZJ&C2"
_YY_SUFFIX = "ooui"
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)
_DEFAULT_BROWSER_VIEWPORT = {"width": 1728, "height": 1117}
_DEFAULT_BROWSER_LOCALE = "en-US"
_DEFAULT_BROWSER_TIMEZONE_ID = "Asia/Dubai"
_LABEL_NORMALIZATION_TABLE = str.maketrans(
    {
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "à": "a",
        "â": "a",
        "ä": "a",
        "î": "i",
        "ï": "i",
        "ô": "o",
        "ö": "o",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ç": "c",
        "&": "e",
    }
)
_REPORT_START_TAG = "<FORMCHECK_REPORT_MD>"
_REPORT_END_TAG = "</FORMCHECK_REPORT_MD>"

_DEFAULT_ANALYSIS_PROMPT = (
    "Analyse uniquement la video jointe comme AI Motion Coach expert en biomecanique de la musculation.\n"
    "Reponds UNIQUEMENT en francais.\n"
    "Pas de preambule. Pas de workflow. Pas de thinking process.\n"
    "Tu t'adresses directement au client, tu le tutoies, tu es critique, didactique, detaille, minutieux et precis.\n"
    "Ecris comme un coach humain: phrases concretes, directes, sans formules scolaires ou meta ('dans cette analyse', 'il est important de noter').\n"
    "Interdit: auto-commentaires ('je vais analyser', 'voici mon analyse'), disclaimers generiques et langue robotique.\n"
    "Detection exo: ne devine jamais. Utilise d'abord les indices visuels les plus discriminants: machine, banc, poulie, Smith, position du corps, segments qui bougent et trajectoire de charge.\n"
    "Nomme l'exercice exact observe, pas une famille generique. Exemple: `Presse Pectorale Machine`, `Lat Pulldown (Tirage Vertical)`, `Developpe Militaire a la Smith`, `Tirage Poulie Basse`, `Leg Press`, `Fente Bulgare`.\n"
    "Anti-confusion obligatoire: ne confonds pas chest press/developpe (bras qui poussent) avec leg press (jambes qui poussent), lat pulldown avec lunge/squat, shoulder press avec upright row, seated cable row avec barbell row.\n"
    "Si l'exercice est ambigu, mets Exercice: Exercice non identifie et Exercice slug: unknown.\n"
    "Le score global doit etre coherent avec les 4 sous-scores.\n"
    "Le message final doit etre UNIQUEMENT un rapport Markdown place entre les balises exactes suivantes:\n"
    "{start}\n"
    "...rapport markdown...\n"
    "{end}\n"
    "Ne mets rien avant {start} et rien apres {end}.\n"
    "Rapport Markdown attendu:\n"
    "# FORMCHECK\n"
    "- Exercice: nom exact en francais\n"
    "- Exercice slug: slug court et stable, le plus proche possible d'une famille interne classique (par exemple machine_chest_press, bench_press, incline_bench, decline_bench, ohp, lat_pulldown, cable_row, squat, leg_press, bulgarian_split_squat, deadlift, rdl, hip_thrust, curl, tricep_extension, lateral_raise, face_pull, pullover, leg_extension, leg_curl)\n"
    "- Confiance exercice: 0.00 a 1.00\n"
    "- Score global: 0/100\n"
    "- Repetitions detectees: 0\n"
    "- Repetitions completes: 0\n"
    "- Repetitions partielles: 0\n"
    "- Intensite: 0/100 (tres elevee|elevee|moderee|faible|tres faible)\n"
    "- Repos inter-reps moyen: 0.00 s\n"
    "## RESUME\n"
    "## POINTS POSITIFS\n"
    "## AMPLITUDE DE MOUVEMENT\n"
    "## CORRECTIONS PRIORITAIRES\n"
    "1. titre | pourquoi | impact | cue\n"
    "## ANALYSE DU TEMPO ET DES PHASES\n"
    "## ANALYSE REP PAR REP\n"
    "1. Rep 1 | 00:00 - 00:00 | commentaire bref, critique et concret\n"
    "Fais exactement une ligne numerotee par rep detectee, sans en sauter.\n"
    "Pour chaque rep, mentionne au minimum la plage temporelle, la vitesse relative, la proprete technique, "
    "la fatigue, les pauses notables entre reps et toute degradation de trajectoire, d'amplitude ou d'alignement.\n"
    "Si une pause entre deux reps depasse environ 1.5 seconde, signale-la explicitement.\n"
    "## INTENSITE DE SERIE\n"
    "## COMPENSATIONS ET BIOMECANIQUE AVANCEE\n"
    "## DECOMPOSITION DU SCORE\n"
    "- Securite: x/40\n"
    "- Efficacite technique: x/30\n"
    "- Controle et tempo: x/20\n"
    "- Symetrie: x/10\n"
    "## POINT BIOMECANIQUE\n"
    "## RECOMMANDATION POUR LA PROCHAINE VIDEO\n"
    "## PLAN ACTION\n"
    "- action 1\n"
    "- action 2\n"
    "- action 3\n"
    "Si une information est invisible, ecris NON MESURABLE."
).format(start=_REPORT_START_TAG, end=_REPORT_END_TAG)

_FALLBACK_ANALYSIS_PROMPT = (
    "Analyse uniquement la video jointe.\n"
    "Reponds UNIQUEMENT en francais, en tutoyant.\n"
    "Style coach humain direct, concret, sans meta-commentaire.\n"
    "Interdit: auto-commentaires ('je vais analyser', 'voici mon analyse') et phrases de template.\n"
    "Detection exo: ne devine jamais. Utilise d'abord les indices visuels les plus discriminants: machine, banc, poulie, Smith, position du corps, segments qui bougent et trajectoire de charge.\n"
    "Nomme l'exercice exact observe, pas une famille generique.\n"
    "Anti-confusion obligatoire: ne confonds pas chest press/developpe (bras qui poussent) avec leg press (jambes qui poussent), lat pulldown avec lunge/squat, shoulder press avec upright row, seated cable row avec barbell row.\n"
    "Si l'exercice est ambigu, mets Exercice: Exercice non identifie et Exercice slug: unknown.\n"
    "Retourne UNIQUEMENT un rapport Markdown entre {start} et {end}.\n"
    "Aucun thinking process. Aucun texte hors balises.\n"
    "# FORMCHECK\n"
    "- Exercice: nom exact en francais\n"
    "- Exercice slug: slug court et stable\n"
    "- Confiance exercice: 0.00 a 1.00\n"
    "- Score global: 0/100\n"
    "- Repetitions detectees: 0\n"
    "- Repetitions completes: 0\n"
    "- Repetitions partielles: 0\n"
    "- Intensite: 0/100 (tres elevee|elevee|moderee|faible|tres faible)\n"
    "- Repos inter-reps moyen: 0.00 s\n"
    "## RESUME\n"
    "## POINTS POSITIFS\n"
    "## AMPLITUDE DE MOUVEMENT\n"
    "## CORRECTIONS PRIORITAIRES\n"
    "## ANALYSE DU TEMPO ET DES PHASES\n"
    "## ANALYSE REP PAR REP\n"
    "Une ligne numerotee par repetition avec plage temporelle, vitesse, technique, fatigue et pauses.\n"
    "## INTENSITE DE SERIE\n"
    "## COMPENSATIONS ET BIOMECANIQUE AVANCEE\n"
    "## DECOMPOSITION DU SCORE\n"
    "- Securite: x/40\n"
    "- Efficacite technique: x/30\n"
    "- Controle et tempo: x/20\n"
    "- Symetrie: x/10\n"
    "## POINT BIOMECANIQUE\n"
    "## RECOMMANDATION POUR LA PROCHAINE VIDEO\n"
    "## PLAN ACTION\n"
    "Si une information est invisible, ecris NON MESURABLE."
).format(start=_REPORT_START_TAG, end=_REPORT_END_TAG)

_PROMPT_NON_NEGOTIABLE_SUFFIX = (
    "\n\nCONTRAINTES NON NEGOCIABLES FORMCHECK\n"
    "- Tu rapportes uniquement ce que tu observes sur la video. N'invente rien.\n"
    "- Le message final doit etre uniquement un rapport Markdown place entre {start} et {end}. "
    "Ne mets rien avant {start} et rien apres {end}.\n"
    "- N'utilise jamais de valeurs internes brutes non interpretees comme 0.01863, 0.931 ou 0.1423. "
    "Traduis-les en score, pourcentage, angle, temps lisible ou ne les affiche pas.\n"
    "- Evite toute phrase vide ou scolaire. Chaque phrase doit apporter une information utile au client.\n"
    "- Dans RESUME, commence directement par le diagnostic utile. Pas d'introduction generique.\n"
    "- Dans CORRECTIONS PRIORITAIRES, garde exactement le format `1. titre | observation | impact | cue`.\n"
    "- Dans ANALYSE REP PAR REP, garde exactement une ligne numerotee par rep detectee, au format "
    "`1. Rep 1 | 00:00 - 00:00 | commentaire`.\n"
    "- Signale explicitement les pauses visibles entre reps, les reps partielles et toute baisse de qualite.\n"
    "- Si une section a peu de matiere, ecris une phrase courte et concrete au lieu de meubler.\n"
    "- N'utilise ni separateurs `---`, ni JSON, ni blocs de code, ni anglais, ni texte chinois.\n"
).format(start=_REPORT_START_TAG, end=_REPORT_END_TAG)


def _compose_analysis_prompt(template: str | None = None, *, fallback: bool = False) -> str:
    base_prompt = str(
        template or (_FALLBACK_ANALYSIS_PROMPT if fallback else _DEFAULT_ANALYSIS_PROMPT)
    ).strip()
    if "CONTRAINTES NON NEGOCIABLES FORMCHECK" in base_prompt:
        return base_prompt
    return "{}{}".format(
        base_prompt,
        _PROMPT_NON_NEGOTIABLE_SUFFIX,
    ).strip()

_INTENSITY_LABELS = (
    ("tres elevee", 85),
    ("elevee", 70),
    ("moderee", 55),
    ("faible", 40),
    ("tres faible", 0),
)
_FINAL_OUTPUT_MARKERS = (
    "exercise:",
    "display_name_fr:",
    "confidence:",
    "score:",
    "reps_total:",
    "reps_complete:",
    "reps_partial:",
    "intensity_score:",
    "intensity_label:",
    "avg_inter_rep_rest_s:",
    "points_positifs:",
    "corrections_prioritaires:",
    "resume:",
    "amplitude_de_mouvement:",
    "analyse_du_tempo_et_des_phases:",
    "analyse_rep_par_rep:",
    "intensite_de_serie:",
    "compensations_et_biomecanique_avancee:",
    "decomposition_du_score:",
    "point_biomecanique:",
    "recommandation_pour_la_prochaine_video:",
    "plan_action:",
)
_PROCESS_MARKERS = (
    "thinking process",
    "current process",
    "completed skill",
    "ongoing command line execution",
    "completed command line execution",
    "completed glob",
    "ongoing glob",
    "invoke frame-extraction skill",
    "invoke motion-analysis skill",
    "invoke stickman-generation skill",
    "let me first",
    "let me check",
    "the user is asking me to",
    "the user wants me to",
    "they want me to",
    "i need to first",
    "script doesn't exist",
    "script path doesn't exist",
    "extract_frames.py",
    "skills directory",
    "ffmpeg directly",
    "i can use ffmpeg directly",
    "extract frames from the video",
    "search for the correct path",
    "extract keyframes",
    "l'utilisateur me demande",
    "regarder la video jointe",
    "analyser l'exercice en identifiant visuellement",
    "je vais analyser cette video",
    "je vais analyser cette vidéo",
)
_LABELED_HEADINGS = (
    "EXERCISE",
    "DISPLAY_NAME_FR",
    "DISPLAY_NAME",
    "DISPLAY NAME",
    "CONFIDENCE",
    "CONFIANCE",
    "SCORE",
    "TOTAL",
    "REPS_TOTAL",
    "TOTAL_REPS",
    "REPS_COMPLETE",
    "COMPLETE_REPS",
    "REPS_PARTIAL",
    "PARTIAL_REPS",
    "INTENSITY_SCORE",
    "INTENSITE_SCORE",
    "INTENSITY_LABEL",
    "INTENSITE_LABEL",
    "AVG_INTER_REP_REST_S",
    "REPOS_MOYEN_S",
    "AVG_REST_S",
    "POINTS_POSITIFS",
    "CORRECTIONS_PRIORITAIRES",
    "RESUME",
    "AMPLITUDE_DE_MOUVEMENT",
    "ANALYSE_DU_TEMPO_ET_DES_PHASES",
    "ANALYSE_REP_PAR_REP",
    "INTENSITE_DE_SERIE",
    "COMPENSATIONS_ET_BIOMECANIQUE_AVANCEE",
    "DECOMPOSITION_DU_SCORE",
    "POINT_BIOMECANIQUE",
    "RECOMMANDATION_POUR_LA_PROCHAINE_VIDEO",
    "PLAN_ACTION",
)
_RETRYABLE_HTTP_STATUSES = {403, 408, 409, 425, 429, 500, 502, 503, 504}
_CJK_CHAR_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]")


def _as_bool(raw: Any, default: bool = False) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _contains_cjk_characters(text: str) -> bool:
    return bool(_CJK_CHAR_PATTERN.search(str(text or "")))


def _load_settings():
    try:
        from app.config import settings as app_settings  # type: ignore

        return app_settings
    except Exception:
        class _FallbackSettings:
            minimax_enabled = _as_bool(os.getenv("MINIMAX_ENABLED"), True)
            minimax_base_url = os.getenv("MINIMAX_BASE_URL", "https://agent.minimax.io")
            minimax_token = os.getenv("MINIMAX_TOKEN", "")
            minimax_user_id = os.getenv("MINIMAX_USER_ID", "")
            minimax_device_id = os.getenv("MINIMAX_DEVICE_ID", "")
            minimax_uuid = os.getenv("MINIMAX_UUID", "")
            minimax_chat_id = os.getenv("MINIMAX_CHAT_ID", "")
            minimax_chat_type = int(os.getenv("MINIMAX_CHAT_TYPE", "2"))
            minimax_lang = os.getenv("MINIMAX_LANG", "en")
            minimax_browser_language = os.getenv("MINIMAX_BROWSER_LANGUAGE", "fr-FR")
            minimax_os_name = os.getenv("MINIMAX_OS_NAME", "Mac")
            minimax_browser_name = os.getenv("MINIMAX_BROWSER_NAME", "chrome")
            minimax_browser_channel = os.getenv("MINIMAX_BROWSER_CHANNEL", "")
            minimax_browser_platform = os.getenv("MINIMAX_BROWSER_PLATFORM", "MacIntel")
            minimax_device_memory = int(os.getenv("MINIMAX_DEVICE_MEMORY", "8"))
            minimax_cpu_core_num = int(os.getenv("MINIMAX_CPU_CORE_NUM", "8"))
            minimax_screen_width = int(os.getenv("MINIMAX_SCREEN_WIDTH", "1920"))
            minimax_screen_height = int(os.getenv("MINIMAX_SCREEN_HEIGHT", "1080"))
            minimax_app_id = int(os.getenv("MINIMAX_APP_ID", "3001"))
            minimax_version_code = int(os.getenv("MINIMAX_VERSION_CODE", "22201"))
            minimax_biz_id = int(os.getenv("MINIMAX_BIZ_ID", "3"))
            minimax_client = os.getenv("MINIMAX_CLIENT", "web")
            minimax_timezone_offset = int(os.getenv("MINIMAX_TIMEZONE_OFFSET", "0"))
            minimax_timeout_s = int(os.getenv("MINIMAX_TIMEOUT_S", "180"))
            minimax_poll_interval_s = float(os.getenv("MINIMAX_POLL_INTERVAL_S", "2"))
            minimax_model_option = int(os.getenv("MINIMAX_MODEL_OPTION", "0"))
            minimax_prompt_template = os.getenv("MINIMAX_PROMPT_TEMPLATE", "")
            minimax_prefer_motion_coach_chat = _as_bool(os.getenv("MINIMAX_PREFER_MOTION_COACH_CHAT"), True)
            minimax_require_motion_coach_chat = _as_bool(os.getenv("MINIMAX_REQUIRE_MOTION_COACH_CHAT"), True)
            minimax_motion_coach_keywords = os.getenv(
                "MINIMAX_MOTION_COACH_KEYWORDS",
                "ai motion coach|motion coach|video motion analysis",
            )
            minimax_fallback_to_local = _as_bool(os.getenv("MINIMAX_FALLBACK_TO_LOCAL"), False)
            minimax_use_cloudscraper = _as_bool(os.getenv("MINIMAX_USE_CLOUDSCRAPER"), True)
            minimax_request_max_attempts = int(os.getenv("MINIMAX_REQUEST_MAX_ATTEMPTS", "3"))
            minimax_retry_backoff_s = float(os.getenv("MINIMAX_RETRY_BACKOFF_S", "1.0"))
            minimax_browser_refresh_enabled = _as_bool(os.getenv("MINIMAX_BROWSER_REFRESH_ENABLED"), False)
            minimax_browser_only = _as_bool(os.getenv("MINIMAX_BROWSER_ONLY"), True)
            minimax_browser_email = os.getenv("MINIMAX_BROWSER_EMAIL", "")
            minimax_browser_password = os.getenv("MINIMAX_BROWSER_PASSWORD", "")
            minimax_browser_headless = _as_bool(os.getenv("MINIMAX_BROWSER_HEADLESS"), True)
            minimax_browser_timeout_s = int(os.getenv("MINIMAX_BROWSER_TIMEOUT_S", "120"))
            minimax_browser_profile_dir = os.getenv("MINIMAX_BROWSER_PROFILE_DIR", "media/minimax_browser_profile")
            minimax_browser_local_storage_json = os.getenv("MINIMAX_BROWSER_LOCAL_STORAGE_JSON", "")
            minimax_browser_session_storage_json = os.getenv("MINIMAX_BROWSER_SESSION_STORAGE_JSON", "")
            minimax_browser_locale = os.getenv("MINIMAX_BROWSER_LOCALE", _DEFAULT_BROWSER_LOCALE)
            minimax_browser_timezone_id = os.getenv("MINIMAX_BROWSER_TIMEZONE_ID", _DEFAULT_BROWSER_TIMEZONE_ID)
            minimax_motion_coach_expert_url = os.getenv(
                "MINIMAX_MOTION_COACH_EXPERT_URL",
                "https://agent.minimax.io/expert/chat/362683345551702",
            )
            minimax_enable_cache = _as_bool(os.getenv("MINIMAX_ENABLE_CACHE"), True)
            minimax_cache_ttl_hours = int(os.getenv("MINIMAX_CACHE_TTL_HOURS", "168"))
            minimax_cache_path = os.getenv("MINIMAX_CACHE_PATH", "media/minimax_cache.sqlite")
            minimax_optimize_video = _as_bool(os.getenv("MINIMAX_OPTIMIZE_VIDEO"), True)
            minimax_max_clip_s = int(os.getenv("MINIMAX_MAX_CLIP_S", "240"))
            minimax_preserve_full_video_up_to_s = int(os.getenv("MINIMAX_PRESERVE_FULL_VIDEO_UP_TO_S", "480"))
            minimax_target_height = int(os.getenv("MINIMAX_TARGET_HEIGHT", "720"))
            minimax_target_fps = int(os.getenv("MINIMAX_TARGET_FPS", "24"))
            minimax_target_video_bitrate_kbps = int(os.getenv("MINIMAX_TARGET_VIDEO_BITRATE_KBPS", "1400"))
            minimax_keep_audio = _as_bool(os.getenv("MINIMAX_KEEP_AUDIO"), False)
            minimax_user_agent = os.getenv("MINIMAX_USER_AGENT", _DEFAULT_USER_AGENT)
            minimax_cookie = os.getenv("MINIMAX_COOKIE", "")

        return _FallbackSettings()


settings = _load_settings()


@dataclass
class MiniMaxAnalysis:
    exercise_slug: str = "unknown"
    exercise_display: str = "Exercice non identifie"
    exercise_confidence: float = 0.0
    score: int = 0
    reps_total: int = 0
    reps_complete: int = 0
    reps_partial: int = 0
    intensity_score: int = 0
    intensity_label: str = "indeterminee"
    avg_inter_rep_rest_s: float = 0.0
    positives: list[str] = field(default_factory=list)
    corrections: list[dict[str, str]] = field(default_factory=list)
    corrective_exercises: list[dict[str, str]] = field(default_factory=list)
    score_breakdown: dict[str, int] = field(default_factory=dict)
    sections: dict[str, str] = field(default_factory=dict)
    plan_action: list[str] = field(default_factory=list)
    report_text: str = ""
    raw_response: str = ""
    model_used: str = "minimax_motion_coach"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class _UploadedAsset:
    file_id: str
    file_url: str
    object_key: str
    upload_uuid: str


@dataclass
class _PreparedVideo:
    path: str
    temporary: bool = False
    source_duration_s: float = 0.0
    prepared_duration_s: float = 0.0
    source_size_bytes: int = 0
    prepared_size_bytes: int = 0
    was_trimmed: bool = False
    was_transcoded: bool = False
    strategy: str = "original"


def _json_body(payload: Any) -> str:
    if payload is None:
        return "{}"
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _md5_text(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def _md5_file(path: Path) -> str:
    md5 = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            md5.update(chunk)
    return md5.hexdigest()


def _clamp_int(value: Any, minimum: int = 0, maximum: int = 100) -> int:
    try:
        ivalue = int(float(value))
    except Exception:
        return minimum
    return max(minimum, min(maximum, ivalue))


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _extract_http_status(exc: Exception) -> int | None:
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            return int(exc.response.status_code)
        except Exception:
            return None
    raw = str(exc or "")
    match = re.search(r"\bHTTP\s+(\d{3})\b", raw, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def _is_retryable_minimax_error(exc: Exception) -> bool:
    if isinstance(
        exc,
        (
            TimeoutError,
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.ReadError,
            httpx.RemoteProtocolError,
        ),
    ):
        return True

    status = _extract_http_status(exc)
    if status in _RETRYABLE_HTTP_STATUSES:
        return True

    raw = str(exc or "").strip().lower()
    if not raw:
        return False

    # Hard failures should not be retried.
    if "not enough credits" in raw or "1400010161" in raw:
        return False
    if "configuration incomplete" in raw:
        return False

    retryable_markers = (
        "timeout",
        "timed out",
        "temporarily unavailable",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "connection reset",
        "connection aborted",
        "network",
        "transport failed",
    )
    return any(marker in raw for marker in retryable_markers)


def _slugify(value: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "_", (value or "").strip().lower())
    base = re.sub(r"_+", "_", base).strip("_")
    return base or "unknown"


def _intensity_label_from_score(score: int) -> str:
    for label, threshold in _INTENSITY_LABELS:
        if score >= threshold:
            return label
    return "indeterminee"


def _extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None

    # Prefer explicit JSON code fences.
    fence = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    candidates = [part.strip() for part in fence if part.strip()]

    # Fallback: broad object extraction.
    first = text.find("{")
    last = text.rfind("}")
    if first >= 0 and last > first:
        candidates.append(text[first : last + 1].strip())

    for candidate in candidates:
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return None


def _extract_score_from_text(text: str) -> int:
    labeled_match = re.search(
        r"(?:score(?:\s+global)?|note(?:\s+globale)?)\s*[:\-]?\s*(\d{1,3})\s*/\s*(100|10)\b",
        text,
        flags=re.IGNORECASE,
    )
    if labeled_match:
        value = int(labeled_match.group(1))
        denominator = int(labeled_match.group(2))
        if denominator == 10:
            value *= 10
        return _clamp_int(value)

    generic_100 = re.search(r"\b(\d{1,3})\s*/\s*100\b", text)
    if generic_100:
        return _clamp_int(generic_100.group(1))

    generic_10 = re.search(r"\b(\d{1,2})\s*/\s*10\b", text)
    if generic_10:
        return _clamp_int(int(generic_10.group(1)) * 10)
    return 0


def _looks_like_report_template(text: str) -> bool:
    low = _compact_text(text).lower()
    if not low:
        return False
    template_markers = (
        "nom exact",
        "snake_case_exact",
        "0/100",
        "0.00",
        "3 a 5 phrases",
        "commentaire bref",
        "point 1",
        "action 1",
        "x/40",
        "x/30",
        "x/20",
        "x/10",
    )
    hits = sum(1 for marker in template_markers if marker in low)
    return hits >= 3


def _looks_like_unstructured_report_text(text: str) -> bool:
    normalized = _clean_markdown_report_text(text)
    low = _compact_text(normalized).lower()
    if len(low) < 180:
        return False
    if _looks_like_process_text(low):
        return False
    if _looks_like_report_template(low):
        return False
    negative_markers = (
        "upload your workout video",
        "personal ai coach that never sleeps",
        "made by minimax",
        "new task",
        "explore experts",
        "task history",
        "you have control of the ai window",
        "end takeover",
        "format de sortie obligatoire",
        "l'utilisateur me demande",
        "regarder la video jointe",
        "analyser l'exercice en identifiant visuellement",
    )
    if any(marker in low for marker in negative_markers):
        return False
    keyword_hits = sum(
        1
        for token in (
            "amplitude",
            "tempo",
            "compensation",
            "biomecan",
            "alignement",
            "stabil",
            "posture",
            "fatigue",
            "repetition",
            "rep ",
            "intensit",
            "serie",
        )
        if token in low
    )
    sentence_hits = len(re.findall(r"[.!?]\s+", normalized))
    bullet_hits = normalized.count("\n- ") + normalized.count("\n* ")
    return keyword_hits >= 3 or sentence_hits >= 3 or bullet_hits >= 2


def _extract_reps_from_text(text: str) -> int:
    raw = str(text or "")
    patterns = (
        r"\b(?:reps?_total|r[eé]p[eé]titions?\s+d[eé]tect[eé]e?s?|repetitions?\s+detecte(?:e|es)?|nombre\s+de\s+reps?)\s*[:=\-]?\s*(\d{1,3})\b",
        r"\b(\d{1,3})\s*(?:reps?|r[eé]p[eé]titions?|repetitions?)\b",
        r"\b(?:reps?|r[eé]p[eé]titions?|repetitions?)\s*[:=\-]?\s*(\d{1,3})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            return max(0, int(match.group(1)))
    return 0


def _count_rep_entries(text: str) -> int:
    raw = str(text or "").replace("\r", "\n")
    if not raw.strip():
        return 0

    # Accept common separators seen in Motion Coach outputs:
    # - 00:09 - 00:13
    # - 9s -> 13s
    # - de 9s a 13s
    time_range_pattern = (
        r"(?:\b\d{1,2}:\d{2}(?::\d{2})?\b|\b\d{1,3}(?:[.,]\d+)?\s*s\b)\s*"
        r"(?:[-–—]|a|à|to|->|→)\s*"
        r"(?:\b\d{1,2}:\d{2}(?::\d{2})?\b|\b\d{1,3}(?:[.,]\d+)?\s*s\b)"
    )

    explicit_rep_ids: set[int] = set()
    timed_rep_lines = 0
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        core = re.sub(r"^(?:[-*•]|\d+[.)])\s*", "", line, flags=re.IGNORECASE).strip()
        if not core:
            continue
        normalized = _normalize_label_text(core)

        has_time_range = bool(re.search(time_range_pattern, normalized, flags=re.IGNORECASE))
        has_pause_marker = any(
            marker in normalized
            for marker in ("pause", "repos", "recuperation", "transition")
        )
        has_rep_range = bool(
            re.search(r"\brep(?:etition)?\s*\d{1,3}\s*[-–—]\s*\d{1,3}\b", normalized, flags=re.IGNORECASE)
        )

        rep_match = re.search(r"\brep(?:etition)?\s*(\d{1,3})\b", normalized, flags=re.IGNORECASE)
        numbered_line_match = re.match(r"^\s*(\d{1,3})[.)]\s+", line)
        if rep_match and not has_rep_range and not (has_pause_marker and not has_time_range):
            explicit_rep_ids.add(int(rep_match.group(1)))
        elif (
            numbered_line_match
            and (has_time_range or any(token in normalized for token in ("execution", "technique", "fatigue", "contraction")))
            and not has_pause_marker
        ):
            explicit_rep_ids.add(int(numbered_line_match.group(1)))

        # Primary counting rule: one timed movement line = one measured rep line.
        # Ignore pause/transition commentary lines without explicit timing windows.
        if has_time_range and (rep_match or "|" in normalized or ":" in normalized):
            timed_rep_lines += 1

    return max(len(explicit_rep_ids), timed_rep_lines)


def _harmonize_rep_counts(analysis: MiniMaxAnalysis, raw_text: str = "") -> None:
    """Reconcile parsed rep fields with rep-by-rep evidence when available."""
    parsed_total = max(0, int(getattr(analysis, "reps_total", 0) or 0))
    parsed_complete = max(0, int(getattr(analysis, "reps_complete", 0) or 0))
    parsed_partial = max(0, int(getattr(analysis, "reps_partial", 0) or 0))

    inferred_candidates = [
        _count_rep_entries(str((analysis.sections or {}).get("rep_par_rep", "") or "")),
        _count_rep_entries(str(getattr(analysis, "report_text", "") or "")),
        _extract_reps_from_text(raw_text),
    ]
    inferred = max(inferred_candidates) if inferred_candidates else 0

    canonical_total = max(parsed_total, parsed_complete + parsed_partial)
    inferred_upgraded_total = False
    if inferred > canonical_total:
        canonical_total = inferred
        inferred_upgraded_total = True
        analysis.metadata["rep_count_source"] = "rep_par_rep_inference"
        analysis.metadata["rep_count_inferred"] = inferred

    if canonical_total <= 0:
        analysis.reps_total = 0
        analysis.reps_complete = 0
        analysis.reps_partial = 0
        return

    if parsed_complete <= 0 and parsed_partial <= 0:
        parsed_complete = canonical_total
    elif (
        inferred_upgraded_total
        and parsed_partial <= 0
        and parsed_total > 0
        and parsed_complete == parsed_total
    ):
        # Common MiniMax inconsistency: header count under-reported while rep-by-rep
        # section clearly lists more complete reps.
        parsed_complete = canonical_total
    elif parsed_complete <= 0 and parsed_partial > 0:
        parsed_complete = max(0, canonical_total - parsed_partial)
    elif parsed_partial <= 0:
        parsed_partial = max(0, canonical_total - parsed_complete)

    if parsed_complete + parsed_partial > canonical_total:
        canonical_total = parsed_complete + parsed_partial
    if parsed_complete > canonical_total:
        parsed_complete = canonical_total
    parsed_partial = max(0, canonical_total - parsed_complete)

    analysis.reps_total = canonical_total
    analysis.reps_complete = parsed_complete
    analysis.reps_partial = parsed_partial


def _extract_intensity_from_text(text: str) -> tuple[int, float]:
    score = 0
    rest = 0.0

    score_match = re.search(
        r"intensit[eé]\s*[:\-]?\s*(\d{1,3})\s*/\s*(100|10)",
        text,
        flags=re.IGNORECASE,
    )
    if score_match:
        value = int(score_match.group(1))
        denominator = int(score_match.group(2))
        if denominator == 10:
            value *= 10
        score = _clamp_int(value)

    rest_match = re.search(
        r"repos?\s+(?:moyen|avg|average)?\s*([0-9]+(?:[.,][0-9]+)?)\s*s",
        text,
        flags=re.IGNORECASE,
    )
    if rest_match:
        rest = _coerce_float(rest_match.group(1).replace(",", "."), default=0.0)

    return score, max(0.0, rest)


def _extract_exercise_from_text(text: str) -> str:
    raw = _clean_markdown_report_text(str(text or ""))
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        return "Exercice non identifie"

    def _strip_metric_suffix(candidate: str) -> str:
        out = str(candidate or "").strip()
        if not out:
            return out
        if "—" in out and re.search(r"(?:\d+\s*/\s*\d+|\breps?\b|intensit[eé])", out, flags=re.IGNORECASE):
            out = out.split("—", 1)[0].strip()
        out = re.sub(r"\s*[-–—]\s*\d{1,3}\s*/\s*\d{1,3}.*$", "", out, flags=re.IGNORECASE).strip()
        out = re.sub(r"\s*[-–—]\s*\d{1,3}\s*reps?.*$", "", out, flags=re.IGNORECASE).strip()
        return out or str(candidate or "").strip()

    # 1) Strongest source: explicit metric line.
    for line in lines:
        candidate_line = re.sub(r"^[-*•#\s]+", "", line).strip()
        match = re.match(
            r"^(?:exercice|exercise|display_name_fr|display_name)\s*:\s*(.+)$",
            candidate_line,
            flags=re.IGNORECASE,
        )
        if match:
            candidate = _strip_metric_suffix(str(match.group(1) or "").strip())
            candidate = re.sub(r"</?FORMCHECK_REPORT_MD>", "", candidate, flags=re.IGNORECASE).strip()
            if candidate and _normalize_label_text(candidate) not in {"formcheck", "formcheck report md"}:
                return candidate

    # 2) Common heading pattern: "ANALYSE BIOMECANIQUE — <exercise>".
    for line in lines:
        match = re.match(
            r"^analyse\s+biomecanique\s*[—:-]\s*(.+)$",
            line,
            flags=re.IGNORECASE,
        )
        if match:
            candidate = _strip_metric_suffix(str(match.group(1) or "").strip())
            candidate = re.sub(r"</?FORMCHECK_REPORT_MD>", "", candidate, flags=re.IGNORECASE).strip()
            if candidate and _normalize_label_text(candidate) not in {"formcheck", "formcheck report md"}:
                return candidate

    # 3) Fallback: first meaningful line after removing wrappers/headings.
    skip_norm = {
        "formcheck",
        "formcheck report md",
        "analyse biomecanique",
        "resume",
        "score global",
        "score",
        "confiance exercice",
        "exercice slug",
        "repetitions detectees",
        "repetitions completes",
        "repetitions partielles",
        "intensite",
        "repos inter reps moyen",
        "points positifs",
        "corrections prioritaires",
        "analyse rep par rep",
        "plan action",
    }
    for line in lines:
        candidate = re.sub(r"</?FORMCHECK_REPORT_MD>", "", line, flags=re.IGNORECASE)
        candidate = re.sub(r"^[-*•#\s]+", "", candidate).strip()
        candidate_norm = _normalize_label_text(candidate)
        if not candidate:
            continue
        if candidate_norm in skip_norm:
            continue
        if candidate.endswith((".", "!", "?")) and len(candidate.split()) >= 3:
            # Narrative sentence, not an exercise name.
            continue
        if candidate.startswith("<") and candidate.endswith(">"):
            continue
        return _strip_metric_suffix(candidate)
    return "Exercice non identifie"


def _is_unknown_exercise_label(value: Any) -> bool:
    norm = _normalize_label_text(value)
    return norm in {
        "",
        "unknown",
        "none",
        "n a",
        "na",
        "exercice non identifie",
        "formcheck",
        "formcheck report md",
        "report md",
    }


def _reconcile_exercise_from_report_text(analysis: MiniMaxAnalysis, report_text: str) -> None:
    cleaned = _clean_markdown_report_text(str(report_text or ""))
    if not cleaned:
        return

    low_cleaned = _compact_text(cleaned).lower()
    has_structured_markers = any(
        marker in low_cleaned
        for marker in (
            "exercice:",
            "exercise:",
            "exercice slug:",
            "score global:",
            "repetitions detectees:",
            "analyse biomecanique",
            "resume",
        )
    )

    candidate_display = _extract_metric_line(
        cleaned,
        ("Exercice", "Exercise", "Display name", "Display_name_fr", "Nom exercice"),
    ).strip()
    if not candidate_display and has_structured_markers:
        candidate_display = _extract_exercise_from_text(cleaned).strip()
    candidate_display = re.sub(r"</?FORMCHECK_REPORT_MD>", "", candidate_display, flags=re.IGNORECASE).strip()

    candidate_slug = _extract_metric_line(
        cleaned,
        ("Exercice slug", "Exercise slug"),
    ).strip()

    if candidate_display and not _is_unknown_exercise_label(candidate_display):
        analysis.exercise_display = candidate_display
        if candidate_slug and not _is_unknown_exercise_label(candidate_slug):
            analysis.exercise_slug = _slugify(candidate_slug)
        elif _is_unknown_exercise_label(analysis.exercise_slug):
            analysis.exercise_slug = _slugify(candidate_display)
        return

    if candidate_slug and not _is_unknown_exercise_label(candidate_slug):
        analysis.exercise_slug = _slugify(candidate_slug)


def _clean_markdown_report_text(text: str) -> str:
    normalized = str(text or "").replace("\r", "\n")
    lines: list[str] = []
    noise_prefixes = (
        "New Task",
        "Search",
        "Assets",
        "Gallery",
        "MiniMax Lab",
        "MaxClaw",
        "Experts",
        "Explore Experts",
        "Task History",
        "You have control of the AI window",
        "End Takeover",
        "Files",
        "Current Process",
        "Thinking Process",
        "Ongoing Video Understanding",
        "Completed Skill",
        "Ongoing Command Line Execution",
        "Completed Command Line Execution",
        "Upload your workout video",
        "Made by MiniMax",
    )
    for raw_line in normalized.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        if _contains_cjk_characters(line):
            continue
        if re.match(r"^\s*</?\s*formcheck_report_md\s*>\s*$", line, flags=re.IGNORECASE):
            continue
        if re.match(r"^\s*```(?:markdown|md|json)?\s*$", line, flags=re.IGNORECASE):
            continue
        if any(line.startswith(prefix) for prefix in noise_prefixes):
            continue
        if line == "MAX":
            continue
        cleaned_line = re.sub(r"^\s*(?:[-–—]{2,}|[-*•])\s*", "", raw_line.rstrip())
        if re.fullmatch(r"[\s\-–—_=:|.]+", cleaned_line or ""):
            continue
        lines.append(cleaned_line.rstrip())
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _normalize_report_heading(line: str) -> str:
    heading = re.sub(r"^#+\s*", "", str(line or "").strip())
    heading = re.sub(r"^[*-]\s*", "", heading)
    heading = heading.strip(" :.-")
    return _normalize_label_text(heading)


def _looks_like_markdown_report(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False

    metric_hits = 0
    heading_hits = 0
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        norm = _normalize_report_heading(line)
        if norm in {
            "resume",
            "points positifs",
            "amplitude de mouvement",
            "corrections prioritaires",
            "analyse du tempo et des phases",
            "analyse rep par rep",
            "intensite de serie",
            "compensations et biomecanique avancee",
            "decomposition du score",
            "point biomecanique",
            "recommandation pour la prochaine video",
            "plan action",
        }:
            heading_hits += 1
        metric_line = re.sub(r"^[-*]\s*", "", line)
        metric_norm = _normalize_label_text(metric_line.split(":", 1)[0]) if ":" in metric_line else ""
        if metric_norm in {
            "exercice",
            "exercice slug",
            "confiance exercice",
            "score global",
            "repetitions detectees",
            "repetitions completes",
            "repetitions partielles",
            "intensite",
            "repos inter reps moyen",
        }:
            metric_hits += 1
    return metric_hits >= 3 or (metric_hits >= 2 and heading_hits >= 2)


def _extract_tagged_report_block(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    pattern = re.compile(
        re.escape(_REPORT_START_TAG) + r"([\s\S]*?)" + re.escape(_REPORT_END_TAG),
        flags=re.IGNORECASE,
    )
    matches = pattern.findall(raw)
    for candidate in reversed(matches):
        cleaned = _clean_markdown_report_text(candidate)
        if cleaned and not _looks_like_report_template(cleaned) and _looks_like_markdown_report(cleaned):
            return cleaned
    return ""


def _extract_markdown_report_block(text: str) -> str:
    tagged = _extract_tagged_report_block(text)
    if tagged:
        return tagged

    raw = _clean_markdown_report_text(text)
    if not raw:
        return ""
    if _looks_like_process_text(raw):
        return ""
    if _looks_like_report_template(raw):
        return ""
    if _looks_like_markdown_report(raw):
        return raw
    return ""


def _extract_metric_line(text: str, aliases: tuple[str, ...]) -> str:
    normalized_aliases = {_normalize_label_text(alias) for alias in aliases}
    for raw_line in str(text or "").splitlines():
        line = re.sub(r"^[-*]\s*", "", raw_line.strip())
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if _normalize_label_text(key) in normalized_aliases:
            return value.strip()
    return ""


def _canonical_markdown_section_key(heading: str) -> str:
    norm = _normalize_report_heading(heading)
    aliases: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("resume", ("resume",)),
        ("rom", ("amplitude de mouvement", "amplitude", "range of motion")),
        ("tempo", ("analyse du tempo et des phases", "tempo et phases", "tempo")),
        ("rep_par_rep", ("analyse rep par rep", "analyse repetition par repetition", "rep par rep")),
        ("intensite", ("intensite de serie", "intensite", "densite")),
        ("compensations", ("compensations et biomecanique avancee", "compensations", "biomecanique avancee")),
        ("breakdown", ("decomposition du score",)),
        ("biomecanique", ("point biomecanique",)),
        ("next_video", ("recommandation pour la prochaine video", "recommandation")),
        ("plan_action", ("plan action", "plan d action")),
        ("positives", ("points positifs",)),
        ("corrections", ("corrections prioritaires",)),
    )
    for canonical, keys in aliases:
        if norm in keys:
            return canonical
    return ""


def _split_markdown_sections(text: str) -> tuple[str, dict[str, str]]:
    intro_lines: list[str] = []
    sections: dict[str, list[str]] = {}
    current_key = ""

    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            if current_key:
                sections.setdefault(current_key, []).append("")
            else:
                intro_lines.append("")
            continue
        if line in {_REPORT_START_TAG, _REPORT_END_TAG}:
            continue
        if _normalize_report_heading(line) == "formcheck":
            continue
        heading_key = _canonical_markdown_section_key(line)
        if heading_key:
            current_key = heading_key
            sections.setdefault(current_key, [])
            continue
        if current_key:
            sections.setdefault(current_key, []).append(raw_line.rstrip())
        else:
            intro_lines.append(raw_line.rstrip())

    out = {
        key: "\n".join(value).strip()
        for key, value in sections.items()
        if "\n".join(value).strip()
    }
    return "\n".join(intro_lines).strip(), out


def _looks_like_process_text(text: str) -> bool:
    low = _compact_text(text).lower()
    if not low:
        return False
    return any(marker in low for marker in _PROCESS_MARKERS)


def _has_final_output_markers(text: str) -> bool:
    low = _compact_text(_normalize_labeled_minimax_text(text)).lower()
    if not low:
        return False
    marker_hits = sum(1 for marker in _FINAL_OUTPUT_MARKERS if marker in low)
    if marker_hits >= 2:
        return True
    if re.search(r"\bscore\s*:\s*\d{1,3}\s*/\s*100\b", low) and re.search(r"\breps?_total\s*:\s*\d+\b", low):
        return True
    if re.search(r"\bexercise\s*:\s*[a-z0-9_ -]{3,}\b", low) and re.search(r"\bplan_action\s*:\b", low):
        return True
    return False


def _normalize_labeled_minimax_text(text: str) -> str:
    normalized = str(text or "").replace("\r", "\n")
    normalized = re.sub(r":\s*_+\s*", ":\n", normalized)
    normalized = re.sub(r"(?<=\s)_+\s*(?=[A-Z][A-Z_ ]+\s*:)", "\n", normalized)
    normalized = re.sub(r"(?<=[0-9A-Za-z])_+\s+(?=[A-Z][A-Z_ ]+\s*:)", "\n", normalized)
    for heading in sorted(_LABELED_HEADINGS, key=len, reverse=True):
        normalized = re.sub(
            r"(?i)(?<![\w])\s*{}\s*:".format(re.escape(heading)),
            "\n{}:".format(heading),
            normalized,
        )
    normalized = re.sub(r"\n{2,}", "\n", normalized)
    return normalized.strip()


def _extract_labeled_scalar(text: str, labels: tuple[str, ...]) -> str:
    pattern = r"(?:^|\n)\s*(?:{})\s*:\s*(.+)".format("|".join(re.escape(label) for label in labels))
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return ""
    return str(match.group(1) or "").strip()


def _extract_labeled_section(text: str, heading: str, next_headings: tuple[str, ...]) -> str:
    if not text:
        return ""
    if next_headings:
        end_pattern = r"(?:\n\s*(?:{})\s*:)|\Z".format("|".join(re.escape(item) for item in next_headings))
    else:
        end_pattern = r"\Z"
    pattern = r"(?:^|\n)\s*{}\s*:\s*(.*?)\s*(?={})".format(
        re.escape(heading),
        end_pattern,
    )
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return str(match.group(1) or "").strip()


def _extract_bullets(text: str) -> list[str]:
    if not text:
        return []
    items: list[str] = []
    normalized = str(text or "").replace("\r", "\n")
    normalized = re.sub(r"\s+-\s+", "\n- ", normalized)
    normalized = re.sub(r"\s+•\s+", "\n- ", normalized)
    for raw_line in normalized.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^(?:[-•*]|\d+[.)])\s*", "", line).strip()
        if line:
            if len(line) > 220 and ". " in line:
                sentence_parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", line) if part.strip()]
                if len(sentence_parts) > 1:
                    items.extend(sentence_parts)
                    continue
            items.append(line)
    return items


def _parse_corrections_block(text: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    normalized = re.sub(r"\s+(?=\d+[.)]\s+)", "\n", str(text or "").strip())
    for item in _extract_bullets(normalized):
        parts = [part.strip() for part in item.split("|")]
        if not parts:
            continue
        title = parts[0] if len(parts) >= 1 else "Correction"
        why = parts[1] if len(parts) >= 2 else ""
        impact = parts[2] if len(parts) >= 3 else ""
        cue = parts[3] if len(parts) >= 4 else ""
        if title or why or impact or cue:
            out.append(
                {
                    "title": title or "Correction",
                    "issue": why,
                    "impact": impact,
                    "fix": cue,
                }
            )
    return out


def _parse_score_breakdown_block(text: str, total_score: int) -> dict[str, int]:
    if not text:
        return {}
    raw: dict[str, int] = {}
    normalized_text = _normalize_label_text(text)
    for key in ("Securite", "Efficacite technique", "Controle et tempo", "Symetrie"):
        norm_key = _normalize_label_text(key)
        match = re.search(
            r"{}\s*:\s*(\d{{1,3}})\s*/\s*(\d{{1,3}})".format(re.escape(norm_key)),
            normalized_text,
            flags=re.IGNORECASE,
        )
        if match:
            raw[key] = max(0, int(match.group(1)))
    return _normalize_score_breakdown(raw or None, total_score=total_score)


def _score_breakdown_total(breakdown: dict[str, int]) -> int:
    return max(0, min(100, sum(max(0, int(value or 0)) for value in breakdown.values())))


def _normalize_label_text(text: Any) -> str:
    normalized = str(text or "").strip().lower().translate(_LABEL_NORMALIZATION_TABLE)
    return re.sub(r"[\s_-]+", " ", normalized)


def _parse_labeled_analysis_payload(text: str) -> MiniMaxAnalysis | None:
    normalized_text = _normalize_labeled_minimax_text(text)
    if not _has_final_output_markers(normalized_text):
        return None

    analysis = MiniMaxAnalysis(raw_response=(text or "").strip())
    section_order = (
        "POINTS_POSITIFS",
        "CORRECTIONS_PRIORITAIRES",
        "RESUME",
        "AMPLITUDE_DE_MOUVEMENT",
        "ANALYSE_DU_TEMPO_ET_DES_PHASES",
        "ANALYSE_REP_PAR_REP",
        "INTENSITE_DE_SERIE",
        "COMPENSATIONS_ET_BIOMECANIQUE_AVANCEE",
        "DECOMPOSITION_DU_SCORE",
        "POINT_BIOMECANIQUE",
        "RECOMMANDATION_POUR_LA_PROCHAINE_VIDEO",
        "PLAN_ACTION",
    )

    exercise_name = _extract_labeled_scalar(normalized_text, ("EXERCISE", "EXERCICE"))
    display_name = _extract_labeled_scalar(normalized_text, ("DISPLAY_NAME_FR", "DISPLAY NAME", "DISPLAY_NAME"))
    confidence_text = _extract_labeled_scalar(normalized_text, ("CONFIDENCE", "CONFIANCE"))
    score_text = _extract_labeled_scalar(normalized_text, ("SCORE", "TOTAL"))
    reps_total_text = _extract_labeled_scalar(normalized_text, ("REPS_TOTAL", "TOTAL_REPS"))
    reps_complete_text = _extract_labeled_scalar(normalized_text, ("REPS_COMPLETE", "COMPLETE_REPS"))
    reps_partial_text = _extract_labeled_scalar(normalized_text, ("REPS_PARTIAL", "PARTIAL_REPS"))
    intensity_score_text = _extract_labeled_scalar(normalized_text, ("INTENSITY_SCORE", "INTENSITE_SCORE"))
    intensity_label_text = _extract_labeled_scalar(normalized_text, ("INTENSITY_LABEL", "INTENSITE_LABEL", "LABEL"))
    avg_rest_text = _extract_labeled_scalar(normalized_text, ("AVG_INTER_REP_REST_S", "REPOS_MOYEN_S", "AVG_REST_S"))

    analysis.exercise_slug = _slugify(exercise_name or display_name)
    if display_name and not _is_unknown_exercise_label(display_name):
        analysis.exercise_display = display_name
    elif _is_unknown_exercise_label(analysis.exercise_display):
        analysis.exercise_display = "Exercice non identifie"
    analysis.exercise_confidence = max(0.0, min(1.0, _coerce_float(confidence_text.replace(",", "."), 0.0)))
    analysis.score = _extract_score_from_text(score_text) or _extract_score_from_text(text)
    analysis.reps_total = max(0, int(_coerce_float(reps_total_text, 0.0)))
    analysis.reps_complete = max(0, int(_coerce_float(reps_complete_text, 0.0)))
    analysis.reps_partial = max(0, int(_coerce_float(reps_partial_text, 0.0)))
    analysis.intensity_score = _extract_score_from_text(intensity_score_text) or _clamp_int(_coerce_float(intensity_score_text, 0.0))
    analysis.intensity_label = (
        str(intensity_label_text or "").strip().lower() or _intensity_label_from_score(analysis.intensity_score)
    )
    analysis.avg_inter_rep_rest_s = max(0.0, _coerce_float(avg_rest_text.replace(",", "."), 0.0))

    if analysis.reps_complete <= 0 and analysis.reps_total > 0:
        analysis.reps_complete = analysis.reps_total
    if analysis.reps_total <= 0 and analysis.reps_complete > 0:
        analysis.reps_total = analysis.reps_complete

    positives_block = _extract_labeled_section(normalized_text, "POINTS_POSITIFS", section_order[1:])
    corrections_block = _extract_labeled_section(normalized_text, "CORRECTIONS_PRIORITAIRES", section_order[2:])
    resume_block = _extract_labeled_section(normalized_text, "RESUME", section_order[3:])
    rom_block = _extract_labeled_section(normalized_text, "AMPLITUDE_DE_MOUVEMENT", section_order[4:])
    tempo_block = _extract_labeled_section(normalized_text, "ANALYSE_DU_TEMPO_ET_DES_PHASES", section_order[5:])
    rep_by_rep_block = _extract_labeled_section(normalized_text, "ANALYSE_REP_PAR_REP", section_order[6:])
    intensite_block = _extract_labeled_section(normalized_text, "INTENSITE_DE_SERIE", section_order[7:])
    compensations_block = _extract_labeled_section(normalized_text, "COMPENSATIONS_ET_BIOMECANIQUE_AVANCEE", section_order[8:])
    breakdown_block = _extract_labeled_section(normalized_text, "DECOMPOSITION_DU_SCORE", section_order[9:])
    biomecanique_block = _extract_labeled_section(normalized_text, "POINT_BIOMECANIQUE", section_order[10:])
    next_video_block = _extract_labeled_section(normalized_text, "RECOMMANDATION_POUR_LA_PROCHAINE_VIDEO", section_order[11:])
    plan_block = _extract_labeled_section(normalized_text, "PLAN_ACTION", ())

    analysis.positives = _extract_bullets(positives_block)[:6]
    analysis.corrections = _parse_corrections_block(corrections_block)[:6]
    analysis.sections = {
        key: value
        for key, value in {
            "resume": resume_block,
            "rom": rom_block,
            "tempo": tempo_block,
            "rep_par_rep": rep_by_rep_block,
            "intensite": intensite_block,
            "compensations": compensations_block,
            "biomecanique": biomecanique_block,
            "next_video": next_video_block,
        }.items()
        if value
    }
    analysis.score_breakdown = _parse_score_breakdown_block(breakdown_block, analysis.score)
    normalized_breakdown = _normalize_label_text(breakdown_block)
    if breakdown_block and all(label in normalized_breakdown for label in ("securite", "efficacite", "controle", "symetrie")):
        derived_total = _score_breakdown_total(analysis.score_breakdown)
        if derived_total > 0:
            analysis.score = derived_total
    analysis.plan_action = _extract_bullets(plan_block)[:6]
    analysis.report_text = _build_structured_report_text(analysis)
    _harmonize_rep_counts(analysis, raw_text=(text or ""))
    return analysis


def _parse_markdown_analysis_payload(text: str) -> MiniMaxAnalysis | None:
    report_text = _extract_markdown_report_block(text)
    if not report_text:
        return None

    intro_text, markdown_sections = _split_markdown_sections(report_text)
    analysis = MiniMaxAnalysis(raw_response=(text or "").strip())

    exercise_display = (
        _extract_metric_line(report_text, ("Exercice", "Display name", "Nom exercice"))
        or _extract_exercise_from_text(report_text)
    )
    exercise_slug = _extract_metric_line(report_text, ("Exercice slug", "Exercise slug", "Exercise"))
    confidence_text = _extract_metric_line(report_text, ("Confiance exercice", "Confidence", "Confiance"))
    score_text = _extract_metric_line(report_text, ("Score global", "Score", "Note globale"))
    reps_total_text = _extract_metric_line(report_text, ("Repetitions detectees", "Reps total", "Nombre de reps"))
    reps_complete_text = _extract_metric_line(report_text, ("Repetitions completes", "Reps completes"))
    reps_partial_text = _extract_metric_line(report_text, ("Repetitions partielles", "Reps partielles"))
    intensity_text = _extract_metric_line(report_text, ("Intensite",))
    rest_text = _extract_metric_line(report_text, ("Repos inter-reps moyen", "Repos inter reps moyen", "Repos moyen"))

    analysis.exercise_display = exercise_display or analysis.exercise_display
    analysis.exercise_slug = _slugify(exercise_slug or exercise_display)
    analysis.exercise_confidence = max(0.0, min(1.0, _coerce_float(confidence_text.replace(",", "."), 0.0)))
    analysis.score = _extract_score_from_text(score_text or report_text)
    analysis.reps_total = max(0, int(_coerce_float(reps_total_text, 0.0)))
    analysis.reps_complete = max(0, int(_coerce_float(reps_complete_text, 0.0)))
    analysis.reps_partial = max(0, int(_coerce_float(reps_partial_text, 0.0)))
    analysis.intensity_score, extracted_rest = _extract_intensity_from_text(
        ("Intensite: " + intensity_text) if intensity_text else report_text
    )
    if analysis.intensity_score <= 0 and intensity_text:
        analysis.intensity_score = _extract_score_from_text(intensity_text)
    rest_value = 0.0
    if rest_text:
        rest_match = re.search(r"([0-9]+(?:[.,][0-9]+)?)", rest_text)
        if rest_match:
            rest_value = _coerce_float(rest_match.group(1).replace(",", "."), 0.0)
    analysis.avg_inter_rep_rest_s = max(extracted_rest, rest_value)

    intensity_label_match = re.search(
        r"\((tres elevee|elevee|moderee|faible|tres faible)\)",
        intensity_text,
        flags=re.IGNORECASE,
    )
    analysis.intensity_label = (
        str(intensity_label_match.group(1) or "").strip().lower()
        if intensity_label_match
        else _intensity_label_from_score(analysis.intensity_score)
    )

    if analysis.reps_total <= 0:
        analysis.reps_total = _extract_reps_from_text(report_text)
    if analysis.reps_complete <= 0 and analysis.reps_total > 0:
        analysis.reps_complete = analysis.reps_total

    analysis.sections = {
        key: markdown_sections[key]
        for key in ("resume", "rom", "tempo", "rep_par_rep", "intensite", "compensations", "biomecanique", "next_video")
        if key in markdown_sections
    }
    analysis.positives = _extract_bullets(markdown_sections.get("positives", ""))[:6]
    analysis.corrections = _parse_corrections_block(markdown_sections.get("corrections", ""))[:6]
    analysis.plan_action = _extract_bullets(markdown_sections.get("plan_action", ""))[:6]
    analysis.score_breakdown = _parse_score_breakdown_block(markdown_sections.get("breakdown", ""), analysis.score)

    if analysis.score_breakdown:
        derived_total = _score_breakdown_total(analysis.score_breakdown)
        if derived_total > 0:
            analysis.score = derived_total

    if intro_text and "resume" not in analysis.sections:
        analysis.sections["resume"] = intro_text
    analysis.report_text = report_text
    _reconcile_exercise_from_report_text(analysis, report_text)

    invalid_display_norm = _normalize_label_text(analysis.exercise_display)
    if invalid_display_norm in {"formcheck", "formcheck report md", "report md"}:
        analysis.exercise_display = "Exercice non identifie"
    if not analysis.exercise_slug:
        analysis.exercise_slug = _slugify(analysis.exercise_display)
    if not analysis.exercise_display:
        analysis.exercise_display = "Exercice non identifie"
    _harmonize_rep_counts(analysis, raw_text=(text or ""))
    return analysis


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value).strip()
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return " ".join(parts).strip()
    if isinstance(value, dict):
        for key in ("text", "content", "summary", "analysis", "value"):
            val = value.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        parts = [str(v).strip() for v in value.values() if isinstance(v, (str, int, float)) and str(v).strip()]
        return " ".join(parts).strip()
    return ""


def _coerce_list_of_strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        # Split multi-line or semi-colon list gracefully.
        raw_parts = re.split(r"[\n;]+", value)
        return [part.strip("-• ").strip() for part in raw_parts if part.strip("-• ").strip()]
    return []


def _extract_sections(payload: dict[str, Any]) -> dict[str, str]:
    section_sources: list[dict[str, Any]] = []
    sections = payload.get("sections")
    if isinstance(sections, dict):
        section_sources.append(sections)
    section_sources.append(payload)

    aliases: dict[str, tuple[str, ...]] = {
        "resume": ("resume", "summary", "diagnostic"),
        "rom": ("rom", "amplitude", "amplitude_rom", "range_of_motion"),
        "tempo": ("tempo", "phases", "tempo_phases", "motor_control"),
        "rep_par_rep": ("rep_par_rep", "analyse_rep_par_rep", "rep_by_rep", "repetition_analysis"),
        "intensite": ("intensite", "intensity", "densite", "intensity_analysis"),
        "compensations": ("compensations", "compensation", "risks", "risk_analysis"),
        "biomecanique": ("biomecanique", "biomechanics", "biomechanical_point"),
        "next_video": ("next_video", "next_video_recommendation", "camera_recommendation"),
    }

    out: dict[str, str] = {}
    for canonical, keys in aliases.items():
        value = ""
        for source in section_sources:
            for key in keys:
                if key not in source:
                    continue
                value = _coerce_text(source.get(key))
                if value:
                    break
            if value:
                break
        if value:
            out[canonical] = value
    return out


def _estimate_score_breakdown(score: int) -> dict[str, int]:
    total = max(0, min(100, int(score or 0)))
    sec = min(40, int(round(total * 0.40)))
    eff = min(30, int(round(total * 0.30)))
    ctrl = min(20, int(round(total * 0.20)))
    # Keep symetrie aligned with remaining points, bounded to /10.
    sym = max(0, min(10, total - sec - eff - ctrl))
    return {
        "Securite": sec,
        "Efficacite technique": eff,
        "Controle et tempo": ctrl,
        "Symetrie": sym,
    }


def _normalize_score_breakdown(
    raw_breakdown: dict[str, Any] | None,
    *,
    total_score: int,
) -> dict[str, int]:
    if not isinstance(raw_breakdown, dict) or not raw_breakdown:
        return {}

    aliases: tuple[tuple[str, tuple[tuple[str, ...], ...], int], ...] = (
        ("Securite", (("securite",),), 40),
        ("Efficacite technique", (("efficacite", "technique"), ("efficacite",), ("technique",)), 30),
        ("Controle et tempo", (("controle", "tempo"), ("controle",), ("tempo",)), 20),
        ("Symetrie", (("symetrie",), ("symmetry",)), 10),
    )

    out: dict[str, int] = {}
    matched = 0
    for canonical, token_groups, max_value in aliases:
        value: int | None = None
        for key, raw_val in raw_breakdown.items():
            norm_key = (
                _normalize_label_text(key)
                .replace("&", "et")
            )
            if any(all(token in norm_key for token in group) for group in token_groups):
                try:
                    parsed = int(float(raw_val))
                except Exception:
                    parsed = 0
                value = max(0, min(max_value, parsed))
                matched += 1
                break
        if value is None:
            value = 0
        out[canonical] = value

    if matched == 0:
        return {}
    return out


def _build_structured_report_text(analysis: MiniMaxAnalysis) -> str:
    exercise_display = analysis.exercise_display or "Exercice non identifie"
    reps_total = max(0, int(analysis.reps_total or 0))
    reps_complete = max(0, int(analysis.reps_complete or 0))
    reps_partial = max(0, int(analysis.reps_partial or 0))
    rest_s = max(0.0, float(analysis.avg_inter_rep_rest_s or 0.0))
    intensity_score = max(0, min(100, int(analysis.intensity_score or 0)))
    intensity_label = (analysis.intensity_label or "indeterminee").strip().lower()
    breakdown = dict(analysis.score_breakdown or {})

    def _section_or_missing(key: str) -> str:
        text = str(analysis.sections.get(key, "") or "").strip()
        return text or "Information non fournie par MiniMax."

    positives = [item.strip() for item in analysis.positives if item and item.strip()]
    corrections = analysis.corrections[:4]
    plan_actions = [item.strip() for item in analysis.plan_action if item and item.strip()]
    next_video = str(analysis.sections.get("next_video", "") or "").strip()

    lines: list[str] = []
    lines.append("ANALYSE BIOMECANIQUE — {}".format(exercise_display))
    if analysis.score > 0:
        lines.append("Score : {}/100".format(analysis.score))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("RESUME")
    lines.append(_section_or_missing("resume"))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("POINTS POSITIFS")
    if positives:
        for idx, item in enumerate(positives[:4], start=1):
            lines.append("{}. {}".format(idx, item))
    else:
        lines.append("MiniMax n'a pas fourni de points positifs explicites.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("AMPLITUDE DE MOUVEMENT")
    lines.append(_section_or_missing("rom"))

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("CORRECTIONS PRIORITAIRES")
    if corrections:
        for idx, corr in enumerate(corrections, start=1):
            title = str(corr.get("title", "") or "Correction {}".format(idx)).strip()
            issue = str(corr.get("issue", "") or corr.get("why", "") or "").strip()
            impact = str(corr.get("impact", "") or "").strip()
            fix = str(corr.get("fix", "") or corr.get("cue", "") or "").strip()
            lines.append("{}. {}".format(idx, title))
            if issue:
                lines.append("Donnee mesuree: {}".format(issue))
            if impact:
                lines.append("Impact biomecanique: {}".format(impact))
            if fix:
                lines.append("Correction: {}".format(fix))
    else:
        lines.append("MiniMax n'a pas fourni de corrections detaillees.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("ANALYSE DU TEMPO ET DES PHASES")
    lines.append(_section_or_missing("tempo"))

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("ANALYSE REP PAR REP")
    lines.append(_section_or_missing("rep_par_rep"))

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("INTENSITE DE SERIE (DENSITE)")
    intensite_text = str(analysis.sections.get("intensite", "") or "").strip()
    if intensite_text:
        lines.append(intensite_text)
    elif intensity_score > 0:
        lines.append(
            "MiniMax: intensite {}/100 ({})".format(intensity_score, intensity_label)
        )
    else:
        lines.append("Information d'intensite non fournie par MiniMax.")
    if reps_total > 0 or reps_complete > 0 or reps_partial > 0:
        lines.append(
            "Repetitions detectees: {} ({} completes, {} partielles)."
            .format(reps_total, reps_complete, reps_partial)
        )
    if rest_s > 0:
        lines.append("Repos inter-reps moyen: {:.2f}s.".format(rest_s))

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("COMPENSATIONS ET BIOMECANIQUE AVANCEE")
    lines.append(_section_or_missing("compensations"))

    if analysis.corrective_exercises:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("EXERCICES CORRECTIFS")
        for idx, item in enumerate(analysis.corrective_exercises[:4], start=1):
            name = str(item.get("name", "") or "Exercice {}".format(idx)).strip()
            dosage = str(item.get("dosage", "") or "").strip()
            target = str(item.get("target", "") or "").strip()
            execution = str(item.get("execution", "") or "").strip()
            timing = str(item.get("timing", "") or "").strip()
            suffix = " — {}".format(dosage) if dosage else ""
            lines.append("{}. {}{}".format(idx, name, suffix))
            if target:
                lines.append("Cible: {}".format(target))
            if execution:
                lines.append("Execution detaillee: {}".format(execution))
            if timing:
                lines.append("Quand le faire: {}".format(timing))

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("DECOMPOSITION DU SCORE")
    if breakdown:
        ordered = (
            ("Securite", 40),
            ("Efficacite technique", 30),
            ("Controle et tempo", 20),
            ("Symetrie", 10),
        )
        for key, max_value in ordered:
            val = int(breakdown.get(key, 0) or 0)
            val = max(0, min(max_value, val))
            lines.append("{}: {}/{}".format(key, val, max_value))
    else:
        lines.append("MiniMax n'a pas fourni de decomposition detaillee du score.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("POINT BIOMECANIQUE")
    lines.append(_section_or_missing("biomecanique"))

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("RECOMMANDATION POUR LA PROCHAINE VIDEO")
    lines.append(next_video or "Information non fournie par MiniMax.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("PLAN ACTION")
    if plan_actions:
        for idx, action in enumerate(plan_actions[:4], start=1):
            lines.append("{}. {}".format(idx, action))
    else:
        lines.append("MiniMax n'a pas fourni de plan d'action explicite.")

    return "\n".join(lines).strip()


_CACHE_SCHEMA = """
CREATE TABLE IF NOT EXISTS minimax_cache (
    video_hash TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    model_option INTEGER NOT NULL,
    created_at REAL NOT NULL,
    last_used_at REAL NOT NULL,
    hit_count INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (video_hash, prompt_hash, model_option)
)
"""


def _cache_db_path() -> Path:
    raw = str(getattr(settings, "minimax_cache_path", "") or "media/minimax_cache.sqlite")
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _open_cache_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_cache_db_path()))
    conn.execute(_CACHE_SCHEMA)
    return conn


def _analysis_to_payload(analysis: MiniMaxAnalysis) -> str:
    return json.dumps(asdict(analysis), ensure_ascii=False)


def _analysis_from_payload(payload_json: str) -> MiniMaxAnalysis | None:
    try:
        data = json.loads(payload_json)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    try:
        return MiniMaxAnalysis(**data)
    except Exception:
        return None


def _cache_get(video_hash: str, prompt_hash: str) -> MiniMaxAnalysis | None:
    if not _as_bool(getattr(settings, "minimax_enable_cache", True), True):
        return None

    ttl_h = max(1, int(getattr(settings, "minimax_cache_ttl_hours", 168) or 168))
    now = time.time()
    min_created_ts = now - (ttl_h * 3600)
    model_option = int(getattr(settings, "minimax_model_option", 0) or 0)

    conn: sqlite3.Connection | None = None
    try:
        conn = _open_cache_db()
        row = conn.execute(
            """
            SELECT payload_json
            FROM minimax_cache
            WHERE video_hash = ? AND prompt_hash = ? AND model_option = ? AND created_at >= ?
            """,
            (video_hash, prompt_hash, model_option, min_created_ts),
        ).fetchone()
        if not row:
            return None
        analysis = _analysis_from_payload(str(row[0]))
        if analysis is None:
            return None
        # Keep cache-compatible with parser fixes: recompute rep coherence on read.
        _harmonize_rep_counts(
            analysis,
            raw_text=str(getattr(analysis, "raw_response", "") or getattr(analysis, "report_text", "") or ""),
        )
        if not _analysis_is_valid_final_output(analysis):
            logger.warning(
                "MiniMax cache entry ignored: invalid final output (video_hash=%s prompt_hash=%s)",
                video_hash[:12],
                prompt_hash[:12],
            )
            conn.execute(
                "DELETE FROM minimax_cache WHERE video_hash = ? AND prompt_hash = ? AND model_option = ?",
                (video_hash, prompt_hash, model_option),
            )
            conn.commit()
            return None
        conn.execute(
            """
            UPDATE minimax_cache
            SET last_used_at = ?, hit_count = hit_count + 1
            WHERE video_hash = ? AND prompt_hash = ? AND model_option = ?
            """,
            (now, video_hash, prompt_hash, model_option),
        )
        conn.commit()
        analysis.metadata.update({"cache_hit": True})
        return analysis
    except Exception as exc:
        logger.debug("MiniMax cache read failed: %s", exc)
        return None
    finally:
        if conn is not None:
            conn.close()


def _cache_put(video_hash: str, prompt_hash: str, analysis: MiniMaxAnalysis) -> None:
    if not _as_bool(getattr(settings, "minimax_enable_cache", True), True):
        return
    if not _analysis_is_valid_final_output(analysis):
        logger.warning(
            "MiniMax cache write skipped: invalid final output (video_hash=%s prompt_hash=%s)",
            video_hash[:12],
            prompt_hash[:12],
        )
        return
    model_option = int(getattr(settings, "minimax_model_option", 0) or 0)
    now = time.time()

    conn: sqlite3.Connection | None = None
    try:
        conn = _open_cache_db()
        conn.execute(
            """
            INSERT INTO minimax_cache (
                video_hash, prompt_hash, model_option, created_at, last_used_at, hit_count, payload_json
            ) VALUES (?, ?, ?, ?, ?, 0, ?)
            ON CONFLICT(video_hash, prompt_hash, model_option)
            DO UPDATE SET
                created_at = excluded.created_at,
                last_used_at = excluded.last_used_at,
                payload_json = excluded.payload_json
            """,
            (video_hash, prompt_hash, model_option, now, now, _analysis_to_payload(analysis)),
        )
        # Prune old entries for bounded cache growth.
        ttl_h = max(1, int(getattr(settings, "minimax_cache_ttl_hours", 168) or 168))
        min_created_ts = now - (ttl_h * 3600)
        conn.execute("DELETE FROM minimax_cache WHERE created_at < ?", (min_created_ts,))
        conn.commit()
    except Exception as exc:
        logger.debug("MiniMax cache write failed: %s", exc)
    finally:
        if conn is not None:
            conn.close()


def _video_stats(video_path: str) -> dict[str, float]:
    stats = {
        "duration_s": 0.0,
        "fps": 0.0,
        "total_frames": 0.0,
        "width": 0.0,
        "height": 0.0,
    }
    try:
        import cv2  # type: ignore

        cap = cv2.VideoCapture(video_path)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        total_frames = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
        width = float(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0.0)
        height = float(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0.0)
        cap.release()
        duration = (total_frames / fps) if fps > 0 and total_frames > 0 else 0.0
        stats.update(
            {
                "duration_s": duration,
                "fps": fps,
                "total_frames": total_frames,
                "width": width,
                "height": height,
            }
        )
    except Exception as exc:
        logger.debug("Video stats probe failed: %s", exc)

    if stats["duration_s"] > 0 and stats["width"] > 0 and stats["height"] > 0:
        return stats

    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            payload = json.loads(proc.stdout)
            streams = payload.get("streams", []) if isinstance(payload, dict) else []
            fmt = payload.get("format", {}) if isinstance(payload, dict) else {}
            video_stream = None
            for stream in streams:
                if isinstance(stream, dict) and stream.get("codec_type") == "video":
                    video_stream = stream
                    break
            if isinstance(video_stream, dict):
                width = _coerce_float(video_stream.get("width"), 0.0)
                height = _coerce_float(video_stream.get("height"), 0.0)
                fps_raw = str(
                    video_stream.get("avg_frame_rate")
                    or video_stream.get("r_frame_rate")
                    or ""
                ).strip()
                fps = 0.0
                if "/" in fps_raw:
                    num_text, den_text = fps_raw.split("/", 1)
                    den = _coerce_float(den_text, 0.0)
                    if den > 0:
                        fps = _coerce_float(num_text, 0.0) / den
                else:
                    fps = _coerce_float(fps_raw, 0.0)
                duration = _coerce_float(
                    video_stream.get("duration"),
                    _coerce_float(fmt.get("duration"), 0.0),
                )
                total_frames = _coerce_float(video_stream.get("nb_frames"), 0.0)
                if total_frames <= 0 and duration > 0 and fps > 0:
                    total_frames = duration * fps
                stats.update(
                    {
                        "duration_s": max(stats["duration_s"], duration),
                        "fps": max(stats["fps"], fps),
                        "total_frames": max(stats["total_frames"], total_frames),
                        "width": max(stats["width"], width),
                        "height": max(stats["height"], height),
                    }
                )
    except Exception as exc:
        logger.debug("ffprobe stats fallback failed: %s", exc)
    return stats


def _detect_active_window(video_path: str) -> tuple[float, float] | None:
    """Return (start_s, end_s) of likely active movement window."""
    try:
        import cv2  # type: ignore
        import numpy as np

        cap = cv2.VideoCapture(video_path)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if fps <= 0 or total_frames < 30:
            cap.release()
            return None

        # Sample up to ~280 frames to keep this pass cheap.
        step = max(1, total_frames // 280)
        motion_scores: list[float] = []
        frame_ids: list[int] = []
        prev: Any = None
        for idx in range(0, total_frames, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (160, 96))
            if prev is not None:
                diff = cv2.absdiff(gray, prev)
                motion_scores.append(float(np.mean(diff)))
                frame_ids.append(idx)
            prev = gray
        cap.release()

        if len(motion_scores) < 12:
            return None

        arr = np.array(motion_scores, dtype=float)
        baseline = float(np.percentile(arr, 60))
        peak = float(np.percentile(arr, 95))
        threshold = baseline + (peak - baseline) * 0.25
        active_idx = np.where(arr >= threshold)[0]

        if active_idx.size == 0:
            peak_i = int(np.argmax(arr))
            center = frame_ids[peak_i]
            start_f = max(0, center - int(fps * 7))
            end_f = min(total_frames - 1, center + int(fps * 10))
        else:
            start_f = frame_ids[int(active_idx[0])]
            end_f = frame_ids[int(active_idx[-1])]
            margin = int(fps * 1.5)
            start_f = max(0, start_f - margin)
            end_f = min(total_frames - 1, end_f + margin)

        if end_f <= start_f:
            return None
        return float(start_f) / fps, float(end_f) / fps
    except Exception as exc:
        logger.debug("Active window detection failed: %s", exc)
        return None


def _prepare_video_for_minimax(video_path: str) -> _PreparedVideo:
    src = Path(video_path)
    src_size = src.stat().st_size if src.exists() else 0
    stats = _video_stats(video_path)
    src_duration = float(stats.get("duration_s", 0.0) or 0.0)
    src_height = float(stats.get("height", 0.0) or 0.0)
    src_fps = float(stats.get("fps", 0.0) or 0.0)

    prepared = _PreparedVideo(
        path=str(src),
        temporary=False,
        source_duration_s=src_duration,
        prepared_duration_s=src_duration,
        source_size_bytes=int(src_size),
        prepared_size_bytes=int(src_size),
        strategy="original",
    )

    if not _as_bool(getattr(settings, "minimax_optimize_video", True), True):
        return prepared

    max_clip_s = max(8, int(getattr(settings, "minimax_max_clip_s", 240) or 240))
    preserve_full_up_to_s = max(
        max_clip_s,
        int(getattr(settings, "minimax_preserve_full_video_up_to_s", 480) or 480),
    )
    target_height = max(360, int(getattr(settings, "minimax_target_height", 720) or 720))
    target_fps = max(12, int(getattr(settings, "minimax_target_fps", 24) or 24))
    target_bitrate = max(700, int(getattr(settings, "minimax_target_video_bitrate_kbps", 1400) or 1400))
    keep_audio = _as_bool(getattr(settings, "minimax_keep_audio", False), False)

    need_duration_trim = src_duration > (preserve_full_up_to_s + 2)
    need_duration_opt = need_duration_trim
    # Keep source quality for common smartphone videos to reduce exercise misclassification.
    # We only force full transcode on genuinely heavy/high-spec media.
    need_resolution_opt = src_height > max(float(target_height + 2), 1920.0)
    need_fps_opt = src_fps > max(float(target_fps + 1), 60.0)
    need_size_opt = src_size > (32 * 1024 * 1024)
    if not any((need_duration_opt, need_resolution_opt, need_fps_opt, need_size_opt)):
        return prepared

    start_s = 0.0
    end_s = src_duration if src_duration > 0 else 0.0
    window_duration = max(0.0, end_s - start_s)

    if need_duration_trim:
        active_window = _detect_active_window(video_path)
        if active_window:
            start_s, end_s = active_window
        window_duration = max(0.0, end_s - start_s)

        if window_duration <= 0 and src_duration > 0:
            start_s = 0.0
            end_s = min(float(max_clip_s), src_duration)
            window_duration = max(0.0, end_s - start_s)

        if window_duration > max_clip_s and src_duration > 0:
            center_s = (start_s + end_s) / 2.0
            half = max_clip_s / 2.0
            start_s = max(0.0, center_s - half)
            end_s = min(src_duration, start_s + max_clip_s)
            if (end_s - start_s) < max_clip_s:
                start_s = max(0.0, end_s - max_clip_s)
            window_duration = max(0.0, end_s - start_s)
    elif src_duration <= 0:
        # If duration is unknown, keep the original file to avoid accidental truncation.
        return prepared

    if window_duration <= 0.1:
        return prepared

    out_dir = src.parent / "minimax_prepared"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "{}_minimax_{}.mp4".format(src.stem, uuid.uuid4().hex[:8])

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-vf",
        "scale=-2:{}:force_original_aspect_ratio=decrease,fps={}".format(target_height, target_fps),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "24",
        "-b:v",
        "{}k".format(target_bitrate),
        "-maxrate",
        "{}k".format(int(target_bitrate * 1.2)),
        "-bufsize",
        "{}k".format(int(target_bitrate * 2.0)),
        "-movflags",
        "+faststart",
    ]
    if start_s > 0.01:
        cmd[5:5] = ["-ss", "{:.3f}".format(start_s)]
    if window_duration > 0.1:
        cmd.extend(["-t", "{:.3f}".format(window_duration)])
    if keep_audio:
        cmd.extend(["-c:a", "aac", "-b:a", "96k"])
    else:
        cmd.append("-an")
    cmd.append(str(out_path))

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if proc.returncode != 0 or not out_path.exists():
            logger.warning(
                "MiniMax preprocess failed (%s). Falling back to original.",
                (proc.stderr or proc.stdout or "").strip()[:240],
            )
            return prepared
        out_size = out_path.stat().st_size
        prepared.path = str(out_path)
        prepared.temporary = True
        prepared.prepared_size_bytes = int(out_size)
        prepared.prepared_duration_s = window_duration
        prepared.was_trimmed = (start_s > 0.01) or ((src_duration - end_s) > 0.01)
        prepared.was_transcoded = True
        prepared.strategy = "trim_transcode" if prepared.was_trimmed else "full_transcode"
        return prepared
    except Exception as exc:
        logger.warning("MiniMax preprocess exception, using original: %s", exc)
        return prepared


def _parse_analysis_payload(text: str) -> MiniMaxAnalysis:
    markdown = _parse_markdown_analysis_payload(text)
    if markdown is not None:
        return markdown

    payload = _extract_json_object(text)
    raw_text = (text or "").strip()
    analysis = MiniMaxAnalysis(raw_response=raw_text)

    if payload:
        exercise = payload.get("exercise", {})
        if isinstance(exercise, dict):
            exercise_name = str(exercise.get("name", "") or "")
            exercise_display = str(exercise.get("display_name_fr", "") or "")
            analysis.exercise_slug = _slugify(exercise_name or exercise_display)
            if exercise_display and not _is_unknown_exercise_label(exercise_display):
                analysis.exercise_display = exercise_display
            elif _is_unknown_exercise_label(analysis.exercise_display):
                analysis.exercise_display = "Exercice non identifie"
            analysis.exercise_confidence = max(0.0, min(1.0, _coerce_float(exercise.get("confidence", 0.0))))
        else:
            exercise_text = str(exercise or "")
            analysis.exercise_slug = _slugify(exercise_text)
            if exercise_text and not _is_unknown_exercise_label(exercise_text):
                analysis.exercise_display = exercise_text

        analysis.score = _clamp_int(payload.get("score", 0))

        reps = payload.get("reps", {})
        if isinstance(reps, dict):
            analysis.reps_total = max(0, int(reps.get("total", 0) or 0))
            analysis.reps_complete = max(0, int(reps.get("complete", 0) or 0))
            analysis.reps_partial = max(0, int(reps.get("partial", 0) or 0))

        intensity = payload.get("intensity", {})
        if isinstance(intensity, dict):
            analysis.intensity_score = _clamp_int(intensity.get("score", 0))
            analysis.avg_inter_rep_rest_s = max(0.0, _coerce_float(intensity.get("avg_inter_rep_rest_s", 0.0)))
            raw_label = str(intensity.get("label", "") or "").strip().lower()
            analysis.intensity_label = raw_label or _intensity_label_from_score(analysis.intensity_score)

        score_breakdown = payload.get("score_breakdown", {})
        analysis.score_breakdown = _normalize_score_breakdown(
            score_breakdown if isinstance(score_breakdown, dict) else None,
            total_score=analysis.score,
        )
        if isinstance(score_breakdown, dict) and len(score_breakdown) >= 4:
            derived_total = _score_breakdown_total(analysis.score_breakdown)
            if derived_total > 0:
                analysis.score = derived_total

        positives = payload.get("positives", [])
        if isinstance(positives, list):
            analysis.positives = [str(item).strip() for item in positives if str(item).strip()]

        corrections = payload.get("corrections", [])
        if isinstance(corrections, list):
            parsed: list[dict[str, str]] = []
            for item in corrections:
                if isinstance(item, dict):
                    title = str(item.get("title", "") or "").strip()
                    why = str(item.get("why", "") or "").strip()
                    cue = str(item.get("cue", "") or "").strip()
                    text_item = " | ".join(part for part in (title, why, cue) if part)
                    if text_item:
                        parsed.append(
                            {
                                "title": title or "Correction",
                                "issue": why or text_item,
                                "fix": cue or "",
                            }
                        )
                else:
                    raw = str(item).strip()
                    if raw:
                        parsed.append({"title": "Correction", "issue": raw, "fix": ""})
            analysis.corrections = parsed

        corrective_exercises = payload.get("corrective_exercises", []) or payload.get("exercices_correctifs", [])
        if isinstance(corrective_exercises, list):
            parsed_correctives: list[dict[str, str]] = []
            for item in corrective_exercises:
                if isinstance(item, dict):
                    parsed_correctives.append(
                        {
                            "name": str(item.get("name", "") or "").strip(),
                            "dosage": str(item.get("dosage", "") or item.get("sets_reps", "") or "").strip(),
                            "target": str(item.get("target", "") or item.get("cible", "") or "").strip(),
                            "execution": str(item.get("execution", "") or item.get("execution_detaillee", "") or "").strip(),
                            "timing": str(item.get("timing", "") or item.get("quand", "") or "").strip(),
                        }
                    )
                else:
                    text_item = str(item).strip()
                    if text_item:
                        parsed_correctives.append(
                            {
                                "name": text_item,
                                "dosage": "",
                                "target": "",
                                "execution": "",
                                "timing": "",
                            }
                        )
            analysis.corrective_exercises = [
                item
                for item in parsed_correctives
                if any(value for value in item.values())
            ]

        analysis.sections = _extract_sections(payload)

        section_positives = _coerce_list_of_strings(
            payload.get("points_positifs")
            or payload.get("strengths")
            or (payload.get("sections", {}) if isinstance(payload.get("sections"), dict) else {}).get("points_positifs")
        )
        if section_positives and not analysis.positives:
            analysis.positives = section_positives[:6]

        plan_action = payload.get("plan_action")
        if plan_action is None and isinstance(payload.get("sections"), dict):
            plan_action = payload["sections"].get("plan_action")
        analysis.plan_action = _coerce_list_of_strings(plan_action)[:6]

        report_text = str(
            payload.get("report_markdown")
            or payload.get("report_text")
            or payload.get("summary")
            or ""
        ).strip()
        if report_text:
            analysis.report_text = report_text
            _reconcile_exercise_from_report_text(analysis, report_text)
        else:
            analysis.report_text = _build_structured_report_text(analysis)

        if analysis.intensity_label == "indeterminee" and analysis.intensity_score > 0:
            analysis.intensity_label = _intensity_label_from_score(analysis.intensity_score)

        invalid_display_norm = _normalize_label_text(analysis.exercise_display)
        if invalid_display_norm in {"formcheck", "formcheck report md", "report md"}:
            analysis.exercise_display = "Exercice non identifie"

        if analysis.reps_total <= 0:
            analysis.reps_total = _extract_reps_from_text(raw_text)
        if analysis.score <= 0:
            analysis.score = _extract_score_from_text(raw_text)
        if not analysis.report_text:
            analysis.report_text = _build_structured_report_text(analysis)
        _harmonize_rep_counts(analysis, raw_text=raw_text)
        return analysis

    labeled = _parse_labeled_analysis_payload(raw_text)
    if labeled is not None:
        return labeled

    # Regex fallback for non-JSON answers.
    analysis.exercise_display = _extract_exercise_from_text(raw_text)
    analysis.exercise_slug = _slugify(analysis.exercise_display)
    invalid_display_norm = _normalize_label_text(analysis.exercise_display)
    if invalid_display_norm in {"formcheck", "formcheck report md", "report md"}:
        analysis.exercise_display = "Exercice non identifie"
        analysis.exercise_slug = "unknown"
    analysis.score = _extract_score_from_text(raw_text)
    analysis.reps_total = _extract_reps_from_text(raw_text)
    intensity_score, avg_rest = _extract_intensity_from_text(raw_text)
    analysis.intensity_score = intensity_score
    analysis.intensity_label = _intensity_label_from_score(intensity_score)
    analysis.avg_inter_rep_rest_s = avg_rest
    analysis.sections = {}
    analysis.plan_action = []
    if _looks_like_unstructured_report_text(raw_text):
        analysis.report_text = _clean_markdown_report_text(raw_text)
    else:
        analysis.report_text = _build_structured_report_text(analysis)
    if raw_text:
        analysis.raw_response = raw_text
    _harmonize_rep_counts(analysis, raw_text=raw_text)
    return analysis


def _analysis_is_valid_final_output(analysis: MiniMaxAnalysis) -> bool:
    raw = str(getattr(analysis, "raw_response", "") or "").strip()
    display = str(getattr(analysis, "exercise_display", "") or "").strip()
    report = str(getattr(analysis, "report_text", "") or "").strip()
    low_blob = _compact_text("\n".join(part for part in (raw, display, report) if part)).lower()
    invalid_markers = (
        "l'utilisateur me demande",
        "the user is asking me to",
        "the user wants me to",
        "they want me to",
        "regarder la video jointe",
        "analyser l'exercice en identifiant visuellement",
        "rapport markdown attendu",
        "format de sortie obligatoire",
    )
    if any(marker in low_blob for marker in invalid_markers):
        return False

    if _extract_tagged_report_block(raw) or _extract_markdown_report_block(raw):
        return True

    has_metrics = bool(
        int(getattr(analysis, "score", 0) or 0) > 0
        or int(getattr(analysis, "reps_total", 0) or 0) > 0
        or int(getattr(analysis, "intensity_score", 0) or 0) > 0
    )
    has_content = any(
        bool(item)
        for item in (
            getattr(analysis, "sections", {}),
            getattr(analysis, "positives", []),
            getattr(analysis, "corrections", []),
            getattr(analysis, "plan_action", []),
        )
    )
    return has_metrics or has_content


def _should_retry_browser_analysis(exc: Exception) -> bool:
    raw = _compact_text(str(exc or "")).lower()
    if not raw:
        return False
    retry_markers = (
        "process text instead of final analysis",
        "returned non-analysis reply",
        "response timeout (no assistant message)",
    )
    return any(marker in raw for marker in retry_markers)


def _iter_dicts(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for val in obj.values():
            yield from _iter_dicts(val)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_dicts(item)


_CHAT_NAME_KEYS = (
    "chat_name",
    "chat_title",
    "title",
    "name",
    "display_name",
    "bot_name",
    "expert_name",
    "workspace_name",
    "session_name",
)


def _motion_coach_keywords() -> list[str]:
    raw = str(getattr(settings, "minimax_motion_coach_keywords", "") or "").strip().lower()
    if not raw:
        raw = "ai motion coach|motion coach|video motion analysis"
    items = [item.strip() for item in raw.split("|") if item.strip()]
    return items or ["motion coach"]


def _is_motion_coach_label(text: str) -> bool:
    norm = (text or "").strip().lower()
    if not norm:
        return False
    return any(keyword in norm for keyword in _motion_coach_keywords())


def _extract_chat_name(payload: Any) -> str:
    best = ""
    for node in _iter_dicts(payload):
        if not isinstance(node, dict):
            continue
        for key in _CHAT_NAME_KEYS:
            value = node.get(key)
            if not isinstance(value, str):
                continue
            txt = value.strip()
            if not txt:
                continue
            if "\n" in txt or len(txt) > 160:
                continue
            low = txt.lower()
            if any(
                marker in low for marker in (
                    "analyse cette video",
                    "rapport markdown attendu",
                    "format de sortie",
                    "thinking process",
                    _REPORT_START_TAG.lower(),
                )
            ):
                continue
            if _is_motion_coach_label(txt):
                return txt
            if len(txt) > len(best):
                best = txt
    return best


def _extract_chat_candidates(payload: Any) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for node in _iter_dicts(payload):
        if not isinstance(node, dict):
            continue
        raw_chat_id = node.get("chat_id")
        if raw_chat_id in (None, ""):
            continue
        chat_id = str(raw_chat_id).strip()
        if not chat_id:
            continue
        name = ""
        for key in _CHAT_NAME_KEYS:
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                name = value.strip()
                break
        item = (chat_id, name)
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _resolve_target_chat_id(
    client: "_MiniMaxClient",
    configured_chat_id: str,
) -> tuple[str, str, str]:
    """Return (chat_id, chat_name, source)."""
    prefer_motion = _as_bool(getattr(settings, "minimax_prefer_motion_coach_chat", True), True)
    if prefer_motion:
        try:
            resp = client.request("POST", "/matrix/api/v1/chat/list_chat", payload={})
            candidates = _extract_chat_candidates(resp)
            for cand_chat_id, cand_name in candidates:
                if _is_motion_coach_label(cand_name):
                    return cand_chat_id, cand_name, "list_chat_motion_match"
            # Keep first candidate only as a weak fallback if no configured chat id is set.
            if (not configured_chat_id) and candidates:
                first_id, first_name = candidates[0]
                return first_id, first_name, "list_chat_first"
        except Exception as exc:
            logger.warning("MiniMax list_chat lookup failed: %s", exc)

    if configured_chat_id:
        return configured_chat_id, "", "configured_chat_id"
    raise RuntimeError("MiniMax chat target unresolved: set MINIMAX_CHAT_ID or enable list_chat discovery")


def _extract_message_text(msg: dict[str, Any]) -> str:
    def _candidate_score(text: str) -> int:
        normalized = str(text or "").strip()
        if not normalized:
            return -10_000
        low = normalized.lower()
        score = len(normalized)
        if _extract_tagged_report_block(normalized):
            score += 3_000
        if _extract_markdown_report_block(normalized):
            score += 2_500
        if _has_final_output_markers(normalized):
            score += 2_000
        if _looks_like_unstructured_report_text(normalized):
            score += 1_500
        prompt_markers = (
            "analyse cette video de musculation comme un coach expert",
            "le message final doit etre uniquement un rapport markdown",
            "rapport markdown attendu",
            "fais exactement une ligne numerotee par rep detectee",
            "type to chat with ai motion coach",
            "start chat",
            "l'utilisateur me demande",
            "regarder la video jointe",
            "analyser l'exercice en identifiant visuellement",
        )
        if any(marker in low for marker in prompt_markers):
            score -= 8_000
        if _looks_like_process_text(normalized):
            score -= 5_000
        return score

    def _iter_text_candidates(value: Any):
        if isinstance(value, str):
            text = value.strip()
            if text:
                yield text
            return
        if isinstance(value, dict):
            for nested in value.values():
                yield from _iter_text_candidates(nested)
            return
        if isinstance(value, list):
            for item in value:
                yield from _iter_text_candidates(item)

    for key in ("msg_content", "content", "text", "answer"):
        value = msg.get(key)
        if isinstance(value, str) and value.strip():
            direct = value.strip()
            if _candidate_score(direct) >= 0:
                return direct
        if isinstance(value, dict):
            nested = value.get("text") or value.get("content") or value.get("answer")
            if isinstance(nested, str) and nested.strip():
                direct = nested.strip()
                if _candidate_score(direct) >= 0:
                    return direct
    # Fallback: recursively scan the message payload for the most meaningful text.
    best = ""
    best_score = -10_000
    for candidate in _iter_text_candidates(msg):
        normalized = candidate.strip()
        if len(normalized) <= 12:
            continue
        if normalized.startswith("http://") or normalized.startswith("https://"):
            continue
        score = _candidate_score(normalized)
        if score > best_score:
            best_score = score
            best = normalized
    return best


def _extract_agent_message(
    payload: Any,
    known_message_ids: set[str],
) -> tuple[str, set[str], int]:
    messages: list[dict[str, Any]] = []
    chat_status = 0

    for node in _iter_dicts(payload):
        if "chat_status" in node:
            try:
                chat_status = int(node.get("chat_status") or chat_status)
            except Exception:
                pass
        if "msg_type" in node and ("msg_id" in node or "msg_content" in node):
            messages.append(node)

    if not messages:
        return "", known_message_ids, chat_status

    # Keep deterministic ordering.
    def _msg_order(item: dict[str, Any]) -> tuple[float, str]:
        ts = _coerce_float(item.get("timestamp", 0.0), 0.0)
        msg_id = str(item.get("msg_id", ""))
        return ts, msg_id

    messages.sort(key=_msg_order)
    current_ids = {
        str(item.get("msg_id"))
        for item in messages
        if item.get("msg_id") is not None
    }

    best_text = ""
    for msg in messages:
        try:
            msg_type = int(msg.get("msg_type", 0) or 0)
        except Exception:
            msg_type = 0
        # 1 = user prompt. All other message types may carry assistant output
        # depending on MiniMax backend revisions.
        if msg_type == 1:
            continue

        msg_id = str(msg.get("msg_id", ""))
        if msg_id and msg_id in known_message_ids:
            continue

        text = _extract_message_text(msg)
        if text:
            best_text = text

    return best_text, current_ids, chat_status


class _MiniMaxClient:
    def __init__(self, timeout_s: float = 120.0):
        self.base_url = settings.minimax_base_url.rstrip("/")
        self.timeout_s = timeout_s
        self._request_max_attempts = max(
            1,
            int(getattr(settings, "minimax_request_max_attempts", 3) or 3),
        )
        self._retry_backoff_s = max(
            0.2,
            float(getattr(settings, "minimax_retry_backoff_s", 1.0) or 1.0),
        )
        user_agent = str(getattr(settings, "minimax_user_agent", "") or _DEFAULT_USER_AGENT)
        self.client = httpx.Client(
            timeout=timeout_s,
            headers={
                "User-Agent": user_agent,
                "Accept": "application/json, text/plain, */*",
            },
        )
        self._runtime_uuid: str | None = None
        self._scraper: Any | None = None
        self._use_cloudscraper = _as_bool(
            getattr(settings, "minimax_use_cloudscraper", True),
            True,
        )
        self._user_agent = user_agent

    def close(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass
        scraper = self._scraper
        if scraper is not None:
            try:
                scraper.close()
            except Exception:
                pass

    def _cookie_header(self) -> str:
        raw = str(getattr(settings, "minimax_cookie", "") or "").strip()
        if raw:
            return raw
        return ""

    def _ensure_scraper(self) -> Any | None:
        if not self._use_cloudscraper:
            return None
        if self._scraper is not None:
            return self._scraper
        try:
            import cloudscraper  # type: ignore
        except Exception:
            return None

        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "darwin", "mobile": False}
        )
        scraper.headers.update(
            {
                "User-Agent": self._user_agent,
                "Accept": "application/json, text/plain, */*",
            }
        )
        cookie_header = self._cookie_header()
        if cookie_header:
            scraper.headers["Cookie"] = cookie_header
        self._scraper = scraper
        return self._scraper

    def _timezone_offset_s(self) -> int:
        configured = int(settings.minimax_timezone_offset or 0)
        if configured:
            return configured
        local = time.localtime()
        gmtoff = getattr(local, "tm_gmtoff", None)
        if isinstance(gmtoff, int):
            return gmtoff
        return 0

    def _query_params(self, unix_ms: int) -> list[tuple[str, str]]:
        if not self._runtime_uuid:
            configured_uuid = str(settings.minimax_uuid or "").strip()
            if configured_uuid:
                self._runtime_uuid = configured_uuid
            else:
                seed = "{}:{}".format(settings.minimax_user_id, settings.minimax_device_id)
                self._runtime_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))

        return [
            ("device_platform", "web"),
            ("biz_id", str(settings.minimax_biz_id)),
            ("app_id", str(settings.minimax_app_id)),
            ("version_code", str(settings.minimax_version_code)),
            ("unix", str(unix_ms)),
            ("timezone_offset", str(self._timezone_offset_s())),
            ("lang", settings.minimax_lang),
            ("uuid", self._runtime_uuid),
            ("device_id", str(settings.minimax_device_id)),
            ("os_name", settings.minimax_os_name),
            ("browser_name", settings.minimax_browser_name),
            ("device_memory", str(settings.minimax_device_memory)),
            ("cpu_core_num", str(settings.minimax_cpu_core_num)),
            ("browser_language", settings.minimax_browser_language),
            ("browser_platform", settings.minimax_browser_platform),
            ("user_id", str(settings.minimax_user_id)),
            ("screen_width", str(settings.minimax_screen_width)),
            ("screen_height", str(settings.minimax_screen_height)),
            ("token", settings.minimax_token),
            ("client", settings.minimax_client),
        ]

    def _signed_headers(
        self,
        path: str,
        params: list[tuple[str, str]],
        body_json: str,
        unix_ms: int,
    ) -> dict[str, str]:
        path_with_query = "{}?{}".format(path, urlencode(params, doseq=True))
        x_timestamp = str(unix_ms // 1000)
        x_signature = _md5_text("{}{}{}".format(x_timestamp, _SIGNING_SECRET, body_json))

        encoded_path = quote(path_with_query, safe="")
        yy_seed = "{}_{}{}{}".format(encoded_path, body_json, _md5_text(str(unix_ms)), _YY_SUFFIX)
        yy = _md5_text(yy_seed)

        return {
            "Content-type": "application/json",
            "token": settings.minimax_token,
            "x-timestamp": x_timestamp,
            "x-signature": x_signature,
            "yy": yy,
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Any | None = None,
    ) -> dict[str, Any]:
        last_exc: Exception | None = None

        for attempt in range(1, self._request_max_attempts + 1):
            try:
                unix_ms = int(time.time()) * 1000
                params = self._query_params(unix_ms)
                body_json = _json_body(payload)
                headers = self._signed_headers(path, params, body_json, unix_ms)
                url = "{}{}".format(self.base_url, path)
                cookie_header = self._cookie_header()
                if cookie_header:
                    headers["Cookie"] = cookie_header

                kwargs: dict[str, Any] = {
                    "method": method.upper(),
                    "url": url,
                    "params": params,
                    "headers": headers,
                }
                if method.upper() != "GET":
                    kwargs["content"] = body_json

                httpx_response: Any | None = None
                try:
                    httpx_response = self.client.request(**kwargs)
                except Exception as exc:
                    logger.warning("MiniMax httpx request failed, trying cloudscraper: %s", exc)

                needs_scraper = (
                    httpx_response is None
                    or int(getattr(httpx_response, "status_code", 0) or 0) == HTTPStatus.FORBIDDEN
                )

                response_obj: Any
                if needs_scraper:
                    scraper = self._ensure_scraper()
                    if scraper is None:
                        if httpx_response is None:
                            raise RuntimeError("MiniMax transport failed and cloudscraper unavailable")
                        try:
                            httpx_response.raise_for_status()
                        except httpx.HTTPStatusError as http_exc:
                            snippet = (httpx_response.text or "").strip().replace("\n", " ")
                            if len(snippet) > 240:
                                snippet = snippet[:240]
                            raise RuntimeError(
                                "MiniMax HTTP {}: {}".format(
                                    int(httpx_response.status_code),
                                    snippet or str(http_exc),
                                )
                            ) from http_exc
                        response_obj = httpx_response
                    else:
                        request_kwargs: dict[str, Any] = {
                            "method": method.upper(),
                            "url": url,
                            "params": params,
                            "headers": headers,
                            "timeout": self.timeout_s,
                        }
                        if method.upper() != "GET":
                            request_kwargs["data"] = body_json
                        response_obj = scraper.request(**request_kwargs)
                        status_code = int(getattr(response_obj, "status_code", 0) or 0)
                        if status_code >= HTTPStatus.BAD_REQUEST:
                            snippet = str(getattr(response_obj, "text", "") or "").strip().replace("\n", " ")
                            if len(snippet) > 240:
                                snippet = snippet[:240]
                            raise RuntimeError("MiniMax HTTP {}: {}".format(status_code, snippet))
                else:
                    try:
                        httpx_response.raise_for_status()
                    except httpx.HTTPStatusError as http_exc:
                        snippet = (httpx_response.text or "").strip().replace("\n", " ")
                        if len(snippet) > 240:
                            snippet = snippet[:240]
                        raise RuntimeError(
                            "MiniMax HTTP {}: {}".format(
                                int(httpx_response.status_code),
                                snippet or str(http_exc),
                            )
                        ) from http_exc
                    response_obj = httpx_response

                try:
                    data = response_obj.json()
                except Exception as json_exc:
                    snippet = str(getattr(response_obj, "text", "") or "").strip().replace("\n", " ")
                    if len(snippet) > 240:
                        snippet = snippet[:240]
                    raise RuntimeError(
                        "MiniMax invalid JSON response: {}".format(snippet or str(json_exc))
                    ) from json_exc
                base_resp = data.get("base_resp", {})
                if isinstance(base_resp, dict):
                    status_code = int(base_resp.get("status_code", 0) or 0)
                    if status_code != 0:
                        status_msg = str(base_resp.get("status_msg", "minimax error"))
                        raise RuntimeError("MiniMax API error {}: {}".format(status_code, status_msg))

                status_info = data.get("statusInfo", {})
                if isinstance(status_info, dict):
                    code = int(status_info.get("code", 0) or 0)
                    if code != 0:
                        msg = str(status_info.get("msg", "minimax error"))
                        raise RuntimeError("MiniMax API error {}: {}".format(code, msg))

                return data
            except Exception as exc:
                last_exc = exc
                retryable = _is_retryable_minimax_error(exc)
                if (not retryable) or attempt >= self._request_max_attempts:
                    raise
                delay_s = self._retry_backoff_s * (2 ** (attempt - 1))
                logger.warning(
                    "MiniMax request retry %d/%d after error: %s (sleep %.1fs)",
                    attempt,
                    self._request_max_attempts,
                    exc,
                    delay_s,
                )
                time.sleep(delay_s)

        if last_exc:
            raise last_exc
        raise RuntimeError("MiniMax request failed unexpectedly")

    @staticmethod
    def unwrap_data(response: dict[str, Any]) -> dict[str, Any]:
        maybe = response.get("data")
        return maybe if isinstance(maybe, dict) else response

    def upload_video(self, video_path: str) -> _UploadedAsset:
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError("Video introuvable: {}".format(video_path))

        policy_resp = self.request("GET", "/v1/api/files/request_policy")
        policy = self.unwrap_data(policy_resp)

        required = ("endpoint", "accessKeyId", "accessKeySecret", "securityToken", "bucketName", "dir")
        missing = [key for key in required if not policy.get(key)]
        if missing:
            raise RuntimeError("MiniMax upload policy incomplete: missing {}".format(",".join(missing)))

        try:
            import oss2  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "Le package 'oss2' est requis pour l'upload MiniMax (pip install oss2)."
            ) from exc

        upload_uuid = uuid.uuid4().hex
        ext = path.suffix.lstrip(".").lower() or "mp4"
        object_key = "{}/{}.{}".format(str(policy["dir"]).rstrip("/"), upload_uuid, ext)

        endpoint = str(policy["endpoint"])
        if not endpoint.startswith("http://") and not endpoint.startswith("https://"):
            endpoint = "https://{}".format(endpoint)

        auth = oss2.StsAuth(
            str(policy["accessKeyId"]),
            str(policy["accessKeySecret"]),
            str(policy["securityToken"]),
        )
        bucket = oss2.Bucket(auth, endpoint, str(policy["bucketName"]))

        headers = {
            "Content-Disposition": "attachment;filename={};".format(quote(path.name)),
        }
        file_size = path.stat().st_size
        if file_size >= 5 * 1024 * 1024:
            oss2.resumable_upload(
                bucket,
                object_key,
                str(path),
                multipart_threshold=5 * 1024 * 1024,
                part_size=2 * 1024 * 1024,
                num_threads=4,
                headers=headers,
            )
        else:
            bucket.put_object_from_file(object_key, str(path), headers=headers)

        file_md5 = _md5_file(path)
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        callback_payload = {
            "fileName": "{}.{}".format(upload_uuid, ext),
            "originFileName": path.name,
            "dir": policy["dir"],
            "endpoint": policy["endpoint"],
            "bucketName": policy["bucketName"],
            "size": str(file_size),
            "mimeType": mime_type,
            "fileMd5": file_md5,
        }
        callback_resp = self.request("POST", "/v1/api/files/policy_callback", payload=callback_payload)
        callback_data = self.unwrap_data(callback_resp)

        file_id = str(callback_data.get("fileID") or callback_data.get("file_id") or "")
        file_url = str(callback_data.get("ossPath") or callback_data.get("oss_path") or "").strip()
        if not file_url:
            file_url = "{}/{}".format(endpoint.rstrip("/"), object_key.lstrip("/"))
        if not file_id:
            file_id = "unknown"

        return _UploadedAsset(
            file_id=file_id,
            file_url=file_url,
            object_key=object_key,
            upload_uuid=upload_uuid,
        )

    def get_chat_detail(self, chat_id: str) -> dict[str, Any]:
        payload = {"chat_id": int(chat_id) if str(chat_id).isdigit() else chat_id}
        return self.request("POST", "/matrix/api/v1/chat/get_chat_detail", payload=payload)

    def send_video_message(self, chat_id: str, prompt: str, asset: _UploadedAsset, origin_file_name: str) -> dict[str, Any]:
        attachment = {
            "file": {
                "file_name": origin_file_name,
                "file_url": asset.file_url,
            },
            "attachment_type": 1,
        }
        payload: dict[str, Any] = {
            "msg_type": 1,
            "text": prompt,
            "chat_type": settings.minimax_chat_type,
            "chat_id": int(chat_id) if str(chat_id).isdigit() else chat_id,
            "attachments": [attachment],
        }
        model_option = int(settings.minimax_model_option or 0)
        if model_option > 0:
            payload["model_option"] = model_option
        return self.request("POST", "/matrix/api/v1/chat/send_msg", payload=payload)


def _browser_profile_seed_available() -> bool:
    raw = str(getattr(settings, "minimax_browser_profile_dir", "") or "").strip()
    if not raw:
        return False
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists() or not path.is_dir():
        return False
    try:
        return any(path.iterdir())
    except Exception:
        return False


def _browser_auth_seed_available() -> bool:
    if str(getattr(settings, "minimax_cookie", "") or "").strip():
        return True
    if _normalized_storage_dump(getattr(settings, "minimax_browser_local_storage_json", ""), label="localStorage"):
        return True
    if _normalized_storage_dump(getattr(settings, "minimax_browser_session_storage_json", ""), label="sessionStorage"):
        return True
    return _browser_profile_seed_available()


def _validate_settings() -> list[str]:
    missing: list[str] = []
    email = str(getattr(settings, "minimax_browser_email", "") or "").strip()
    password = str(getattr(settings, "minimax_browser_password", "") or "").strip()
    if not email:
        missing.append("minimax_browser_email")
    if not password and not _browser_auth_seed_available():
        missing.append("minimax_browser_password_or_browser_auth_seed")
    return missing


def _browser_refresh_enabled() -> bool:
    return _as_bool(getattr(settings, "minimax_browser_refresh_enabled", False), False)


def _browser_only_enabled() -> bool:
    return _as_bool(getattr(settings, "minimax_browser_only", True), True)


def _browser_profile_dir() -> Path:
    raw = str(getattr(settings, "minimax_browser_profile_dir", "") or "media/minimax_browser_profile")
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _motion_coach_expert_url() -> str:
    raw = str(getattr(settings, "minimax_motion_coach_expert_url", "") or "").strip()
    return raw or "https://agent.minimax.io/expert/chat/362683345551702"


def _chat_page_url(chat_id: str) -> str:
    return "https://agent.minimax.io/chat?id={}".format(str(chat_id).strip())


def _browser_launch_options(headless: bool) -> dict[str, Any]:
    options: dict[str, Any] = {
        "headless": headless,
        "user_agent": str(getattr(settings, "minimax_user_agent", "") or _DEFAULT_USER_AGENT),
        "locale": str(getattr(settings, "minimax_browser_locale", "") or _DEFAULT_BROWSER_LOCALE),
        "timezone_id": str(getattr(settings, "minimax_browser_timezone_id", "") or _DEFAULT_BROWSER_TIMEZONE_ID),
        "viewport": dict(_DEFAULT_BROWSER_VIEWPORT),
        "screen": dict(_DEFAULT_BROWSER_VIEWPORT),
        "java_script_enabled": True,
        "ignore_https_errors": False,
        "accept_downloads": False,
        "bypass_csp": False,
        "is_mobile": False,
        "has_touch": False,
        "color_scheme": "light",
        "ignore_default_args": ["--enable-automation"],
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-gpu",
        ],
    }
    if not headless:
        options["args"].extend(
            [
                "--start-minimized",
                "--window-position=-2400,0",
                "--window-size=1440,1100",
            ]
        )
    channel = str(getattr(settings, "minimax_browser_channel", "") or "").strip()
    if channel:
        options["channel"] = channel
    return options


def _install_browser_stealth(context: Any) -> None:
    try:
        context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'platform', {get: () => 'MacIntel'});
            window.chrome = window.chrome || { runtime: {} };
            const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
            if (originalQuery) {
              window.navigator.permissions.query = (parameters) => (
                parameters && parameters.name === 'notifications'
                  ? Promise.resolve({ state: Notification.permission })
                  : originalQuery(parameters)
              );
            }
            """
        )
    except Exception:
        pass


def _inject_browser_cookies(context: Any) -> None:
    raw = str(getattr(settings, "minimax_cookie", "") or "").strip()
    if not raw:
        return
    cookies: list[dict[str, Any]] = []
    for chunk in raw.split(";"):
        part = chunk.strip()
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        cookies.append(
            {
                "name": name,
                "value": value,
                "domain": "agent.minimax.io",
                "path": "/",
                "secure": True,
                "httpOnly": False,
                "sameSite": "Lax",
            }
        )
    if not cookies:
        return
    try:
        context.add_cookies(cookies)
    except Exception as exc:
        logger.warning("MiniMax browser cookie injection failed: %s", exc)


def _normalized_storage_dump(raw: Any, *, label: str) -> dict[str, str]:
    if isinstance(raw, dict):
        payload = raw
    else:
        text = str(raw or "").strip()
        if not text:
            return {}
        try:
            payload = json.loads(text)
        except Exception as exc:
            logger.warning("MiniMax browser %s injection ignored: invalid JSON (%s)", label, exc)
            return {}
    if not isinstance(payload, dict):
        logger.warning("MiniMax browser %s injection ignored: expected JSON object", label)
        return {}
    normalized: dict[str, str] = {}
    for key, value in payload.items():
        if key is None or value is None:
            continue
        normalized[str(key)] = str(value)
    return normalized


def _inject_browser_storage(context: Any) -> None:
    local_storage = _normalized_storage_dump(
        getattr(settings, "minimax_browser_local_storage_json", ""),
        label="localStorage",
    )
    session_storage = _normalized_storage_dump(
        getattr(settings, "minimax_browser_session_storage_json", ""),
        label="sessionStorage",
    )
    if not local_storage and not session_storage:
        return

    storage_script = """
        (() => {
          const localEntries = __LOCAL_ENTRIES__;
          const sessionEntries = __SESSION_ENTRIES__;
          if (window.location.hostname !== 'agent.minimax.io') {
            return;
          }
          try {
            for (const [key, value] of Object.entries(localEntries)) {
              window.localStorage.setItem(String(key), String(value));
            }
          } catch (_) {}
          try {
            for (const [key, value] of Object.entries(sessionEntries)) {
              window.sessionStorage.setItem(String(key), String(value));
            }
          } catch (_) {}
        })();
    """.replace("__LOCAL_ENTRIES__", json.dumps(local_storage)).replace(
        "__SESSION_ENTRIES__", json.dumps(session_storage)
    )

    try:
        context.add_init_script(storage_script)
    except Exception as exc:
        logger.warning("MiniMax browser storage injection failed: %s", exc)


def _extract_query_identity_from_url(url: str, out: dict[str, str]) -> None:
    try:
        parsed = urlparse(url)
    except Exception:
        return
    if "agent.minimax.io" not in (parsed.netloc or ""):
        return
    if "/matrix/api/v1/chat/" not in (parsed.path or ""):
        return
    query = parse_qs(parsed.query or "")
    for key in ("token", "user_id", "device_id", "uuid"):
        val = (query.get(key) or [None])[0]
        if val and not out.get(key):
            out[key] = str(val)


def _extract_jwt_from_text(raw: str) -> str:
    if not raw:
        return ""
    match = re.search(r"([A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)", raw)
    return str(match.group(1) if match else "")


def _decode_user_id_from_token(token: str) -> str:
    token = (token or "").strip()
    if token.count(".") != 2:
        return ""
    try:
        payload = token.split(".")[1]
        padding = "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload + padding).decode("utf-8", errors="ignore")
        obj = json.loads(decoded)
    except Exception:
        return ""

    if isinstance(obj, dict):
        user = obj.get("user")
        if isinstance(user, dict):
            user_id = str(user.get("id") or "").strip()
            if user_id:
                return user_id
        uid = str(obj.get("user_id") or "").strip()
        if uid:
            return uid
    return ""


def _minimax_login_if_needed(page: Any, email: str, password: str, timeout_ms: int) -> None:
    email_selectors = (
        "input[type='email']",
        "input[name='email']",
        "input[placeholder*='mail' i]",
    )
    password_selectors = (
        "input[type='password']",
        "input[name='password']",
        "input[placeholder*='password' i]",
        "input[placeholder*='mot de passe' i]",
    )
    submit_selectors = (
        "button[type='submit']",
        "button:has-text('Log in')",
        "button:has-text('Sign in')",
        "button:has-text('Continue')",
        "button:has-text('Connexion')",
        "button:has-text('Se connecter')",
    )

    email_locator = None
    for selector in email_selectors:
        try:
            locator = page.locator(selector).first
            if locator and locator.count() > 0 and locator.is_visible(timeout=1500):
                email_locator = locator
                break
        except Exception:
            continue
    if email_locator is None:
        return
    if not str(password or "").strip():
        logger.warning("MiniMax direct login form visible but no password configured; relying on persisted browser auth.")
        return

    password_locator = None
    for selector in password_selectors:
        try:
            locator = page.locator(selector).first
            if locator and locator.count() > 0:
                password_locator = locator
                break
        except Exception:
            continue
    if password_locator is None:
        raise RuntimeError("MiniMax browser login failed: password field not found")

    email_locator.fill(email, timeout=timeout_ms)
    password_locator.fill(password, timeout=timeout_ms)

    submitted = False
    for selector in submit_selectors:
        try:
            locator = page.locator(selector).first
            if locator and locator.count() > 0 and locator.is_enabled():
                locator.click(timeout=4000)
                submitted = True
                break
        except Exception:
            continue
    if not submitted:
        try:
            password_locator.press("Enter", timeout=2000)
            submitted = True
        except Exception:
            pass
    if not submitted:
        raise RuntimeError("MiniMax browser login failed: submit action not found")

    try:
        page.wait_for_timeout(2200)
    except Exception:
        pass


def _refresh_minimax_session_via_browser() -> dict[str, Any]:
    email = str(getattr(settings, "minimax_browser_email", "") or "").strip()
    password = str(getattr(settings, "minimax_browser_password", "") or "").strip()
    if not email or not password:
        raise RuntimeError("MiniMax browser refresh disabled: missing MINIMAX_BROWSER_EMAIL/PASSWORD")

    timeout_s = max(45, int(getattr(settings, "minimax_browser_timeout_s", 120) or 120))
    timeout_ms = timeout_s * 1000
    headless = _as_bool(getattr(settings, "minimax_browser_headless", True), True)

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Playwright unavailable for MiniMax browser refresh. Install dependency and Chromium."
        ) from exc

    captured: dict[str, str] = {}
    storage_dump: dict[str, str] = {}
    cookies: list[dict[str, Any]] = []

    with sync_playwright() as p:
        try:
            launch_options = _browser_launch_options(headless=headless)
            browser = p.chromium.launch(
                headless=headless,
                args=list(launch_options.get("args", []) or []),
                ignore_default_args=list(launch_options.get("ignore_default_args", []) or []),
            )
        except Exception as launch_exc:
            # Render/runtime safety net: install Chromium once if missing.
            logger.warning("Playwright Chromium launch failed, trying install: %s", launch_exc)
            try:
                subprocess.run(
                    ["python3", "-m", "playwright", "install", "chromium"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except Exception as install_exc:
                raise RuntimeError(
                    "MiniMax browser refresh failed: Chromium not available and auto-install failed ({})"
                    .format(install_exc)
                ) from launch_exc
            browser = p.chromium.launch(
                headless=headless,
                args=list(launch_options.get("args", []) or []),
                ignore_default_args=list(launch_options.get("ignore_default_args", []) or []),
            )
        try:
            context = browser.new_context(
                user_agent=launch_options["user_agent"],
                locale=launch_options["locale"],
                timezone_id=launch_options["timezone_id"],
                viewport=launch_options["viewport"],
                screen=launch_options["screen"],
                java_script_enabled=launch_options["java_script_enabled"],
                ignore_https_errors=launch_options["ignore_https_errors"],
                is_mobile=launch_options["is_mobile"],
                has_touch=launch_options["has_touch"],
                color_scheme=launch_options["color_scheme"],
            )
            _install_browser_stealth(context)
            _inject_browser_cookies(context)
            _inject_browser_storage(context)
            try:
                context.set_extra_http_headers(
                    {
                        "Accept-Language": "en-US,en;q=0.9",
                        "Upgrade-Insecure-Requests": "1",
                    }
                )
            except Exception:
                pass
            page = context.new_page()
            page.on("request", lambda req: _extract_query_identity_from_url(req.url, captured))

            page.goto("https://agent.minimax.io/experts", wait_until="domcontentloaded", timeout=timeout_ms)
            if not _wait_for_bot_challenge_to_clear(page, timeout_ms=min(timeout_ms, 25000)):
                raise RuntimeError("MiniMax browser refresh blocked by anti-bot challenge")
            _minimax_login_if_needed(page, email, password, timeout_ms)
            page.goto("https://agent.minimax.io/experts", wait_until="domcontentloaded", timeout=timeout_ms)
            if not _wait_for_bot_challenge_to_clear(page, timeout_ms=min(timeout_ms, 25000)):
                raise RuntimeError("MiniMax browser refresh blocked by anti-bot challenge")

            # Force one authenticated chat API call from browser context to surface query identity.
            try:
                page.evaluate(
                    """async () => {
                        try {
                            await fetch('/matrix/api/v1/chat/list_chat', {
                                method: 'POST',
                                credentials: 'include',
                                headers: {'content-type': 'application/json'},
                                body: '{}'
                            });
                        } catch (_) {}
                    }"""
                )
            except Exception:
                pass

            # Give time for request listeners and app boot API calls.
            deadline = time.time() + max(12, timeout_s // 3)
            while time.time() < deadline:
                if captured.get("token"):
                    break
                page.wait_for_timeout(350)

            try:
                storage_raw = page.evaluate(
                    """() => {
                        const out = {};
                        try {
                            for (let i = 0; i < localStorage.length; i++) {
                                const k = localStorage.key(i);
                                if (!k) continue;
                                out[k] = localStorage.getItem(k) || '';
                            }
                        } catch (_) {}
                        return out;
                    }"""
                )
                if isinstance(storage_raw, dict):
                    storage_dump = {str(k): str(v) for k, v in storage_raw.items()}
            except Exception:
                storage_dump = {}

            cookies = context.cookies("https://agent.minimax.io")
        finally:
            try:
                browser.close()
            except Exception:
                pass

    if not captured.get("token"):
        for value in storage_dump.values():
            jwt = _extract_jwt_from_text(str(value))
            if jwt:
                captured["token"] = jwt
                break

    if not captured.get("user_id"):
        token_user_id = _decode_user_id_from_token(captured.get("token", ""))
        if token_user_id:
            captured["user_id"] = token_user_id

    cookie_header = "; ".join(
        "{}={}".format(str(c.get("name", "")), str(c.get("value", "")))
        for c in cookies
        if c.get("name") and c.get("value")
    )
    if cookie_header:
        captured["cookie"] = cookie_header

    # Keep previous values if browser refresh returned only partial identity.
    if captured.get("token"):
        settings.minimax_token = captured["token"]
    if captured.get("user_id"):
        settings.minimax_user_id = captured["user_id"]
    if captured.get("device_id"):
        settings.minimax_device_id = captured["device_id"]
    if captured.get("uuid"):
        settings.minimax_uuid = captured["uuid"]
    if captured.get("cookie"):
        settings.minimax_cookie = captured["cookie"]

    missing = []
    if not str(getattr(settings, "minimax_token", "") or "").strip():
        missing.append("token")
    if not str(getattr(settings, "minimax_user_id", "") or "").strip():
        missing.append("user_id")
    if missing:
        raise RuntimeError(
            "MiniMax browser refresh incomplete: missing {}".format(",".join(missing))
        )

    return {
        "token_refreshed": bool(captured.get("token")),
        "user_id_refreshed": bool(captured.get("user_id")),
        "device_id_refreshed": bool(captured.get("device_id")),
        "uuid_refreshed": bool(captured.get("uuid")),
        "cookie_refreshed": bool(captured.get("cookie")),
    }


def _locator_is_visible(page: Any, selector: str, timeout_ms: int = 1200) -> bool:
    try:
        locator = page.locator(selector).first
        return locator.count() > 0 and locator.is_visible(timeout=timeout_ms)
    except Exception:
        return False


def _click_first_visible(page: Any, selectors: tuple[str, ...], timeout_ms: int = 2500) -> bool:
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() > 0 and locator.is_visible(timeout=timeout_ms):
                if _click_locator_robust(locator, timeout_ms=timeout_ms, description=selector):
                    return True
        except Exception:
            continue
    return False


def _click_locator_robust(locator: Any, *, timeout_ms: int, description: str) -> bool:
    try:
        locator.click(timeout=timeout_ms)
        return True
    except Exception as click_exc:
        logger.warning("MiniMax locator click blocked for %s, retrying with force click: %s", description, click_exc)
        try:
            locator.click(timeout=min(timeout_ms, 2500), force=True)
            return True
        except Exception:
            try:
                locator.evaluate("(el) => el && el.click && el.click()")
                return True
            except Exception:
                return False


def _locator_exists(page: Any, selector: str) -> bool:
    try:
        return page.locator(selector).count() > 0
    except Exception:
        return False


def _safe_page_wait(page: Any, delay_ms: int) -> None:
    try:
        page.wait_for_timeout(delay_ms)
    except Exception:
        time.sleep(max(delay_ms, 0) / 1000.0)


def _role_locator_exists(page: Any, role: str, name: Any = None) -> bool:
    try:
        return page.get_by_role(role, name=name).count() > 0
    except Exception:
        return False


def _text_locator_exists(page: Any, text: str, exact: bool = False) -> bool:
    try:
        return page.get_by_text(text, exact=exact).count() > 0
    except Exception:
        return False


def _blanket_overlay_visible(page: Any) -> bool:
    selectors = (
        "[class*='bg-utility_blanket']",
        "div.fixed.inset-0",
        "[role='dialog']",
    )
    return any(_locator_is_visible(page, selector, timeout_ms=500) for selector in selectors)


def _dismiss_browser_blanket_overlay(page: Any, timeout_ms: int) -> bool:
    try:
        logger.warning("MiniMax blanket overlay detected: %s", _overlay_debug_summary(page))
    except Exception:
        pass
    if _remove_maxclaw_promo_overlay(page):
        _safe_page_wait(page, 200)
    close_selectors = (
        "button[aria-label='Close']",
        "button:has-text('Close')",
        "button:has-text('Not now')",
        "button:has-text('Maybe later')",
        "button:has-text('Skip')",
        "button:has-text('Got it')",
        "button:has-text('Cancel')",
        "img[alt='close']",
        "img[alt='Close']",
    )
    if _click_first_visible(page, close_selectors, timeout_ms=min(timeout_ms, 1800)):
        _wait_for_page_condition(page, lambda: not _blanket_overlay_visible(page), timeout_ms=min(timeout_ms, 2500))
    else:
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        _safe_page_wait(page, 250)
    return not _blanket_overlay_visible(page)


def _remove_maxclaw_promo_overlay(page: Any) -> bool:
    try:
        return bool(
            page.evaluate(
                """() => {
                    let removed = false;
                    const nodes = Array.from(document.querySelectorAll('[class*="bg-utility_blanket"], div.fixed.inset-0, [role="dialog"]'));
                    for (const node of nodes) {
                        const text = String(node.textContent || '');
                        if (!text.includes('MaxClaw is here') && !text.includes('Get MaxClaw')) continue;
                        node.remove();
                        removed = true;
                    }
                    return removed;
                }"""
            )
        )
    except Exception:
        return False


def _overlay_debug_summary(page: Any) -> str:
    try:
        payload = page.evaluate(
            """() => {
                const overlays = Array.from(document.querySelectorAll('[class*="bg-utility_blanket"], [role="dialog"], div.fixed.inset-0'))
                    .slice(0, 4)
                    .map((el) => ({
                        cls: typeof el.className === 'string' ? el.className : '',
                        text: (el.textContent || '').trim().slice(0, 600),
                        buttons: Array.from(el.querySelectorAll('button')).slice(0, 12).map((b) => ({
                            text: (b.textContent || '').trim().slice(0, 120),
                            aria: b.getAttribute('aria-label') || '',
                            title: b.getAttribute('title') || '',
                        })),
                    }));
                return JSON.stringify(overlays);
            }"""
        )
        return str(payload or "")[:2000]
    except Exception as exc:
        return "overlay-summary-unavailable: {}".format(exc)


def _motion_coach_composer_ready(page: Any) -> bool:
    return (
        _locator_is_visible(page, ".tiptap-editor", timeout_ms=800)
        or _locator_exists(page, ".tiptap-editor")
        or _locator_exists(page, "input[type='file']")
        or _locator_exists(page, "#input-send-icon")
    )


def _motion_coach_cta_present(page: Any) -> bool:
    selectors = (
        "button:has-text('Type to chat with AI Motion Coach')",
        "button:has-text('Start Chat')",
        "button:has-text('Chat with AI Motion Coach')",
    )
    if any(_locator_is_visible(page, selector, timeout_ms=800) or _locator_exists(page, selector) for selector in selectors):
        return True
    return any(
        (
            _role_locator_exists(page, "button", name=pattern)
            or _text_locator_exists(page, text, exact=False)
        )
        for pattern, text in (
            (re.compile(r"type to chat with ai motion coach", re.I), "Type to chat with AI Motion Coach"),
            (re.compile(r"start chat", re.I), "Start Chat"),
            (re.compile(r"chat with ai motion coach", re.I), "Chat with AI Motion Coach"),
        )
    )


def _motion_coach_card_present(page: Any) -> bool:
    return _locator_exists(page, "img[alt='AI Motion Coach']") or _text_locator_exists(
        page, "AI Motion Coach", exact=False
    )


def _experts_search_box_present(page: Any) -> bool:
    return (
        _locator_exists(page, "input[placeholder='Search experts']")
        or _locator_exists(page, "[aria-label='Search experts']")
        or _role_locator_exists(page, "textbox", name=re.compile(r"search experts", re.I))
    )


def _wait_for_page_condition(page: Any, predicate: Any, timeout_ms: int, step_ms: int = 350) -> bool:
    deadline = time.monotonic() + max(timeout_ms, 0) / 1000.0
    while time.monotonic() < deadline:
        try:
            if predicate():
                return True
        except Exception:
            pass
        _safe_page_wait(page, step_ms)
    try:
        return bool(predicate())
    except Exception:
        return False


def _page_is_motion_coach_chat(page: Any) -> bool:
    current = str(getattr(page, "url", "") or "").strip()
    if not current:
        return False
    current_base = current.split("#", 1)[0].split("?", 1)[0].rstrip("/")
    target_base = _motion_coach_expert_url().split("#", 1)[0].split("?", 1)[0].rstrip("/")
    return bool(current_base) and current_base == target_base


def _goto_minimax_page(page: Any, url: str, timeout_ms: int, *, label: str, raise_on_error: bool = True) -> bool:
    try:
        page.goto(url, wait_until="commit", timeout=timeout_ms)
    except Exception as exc:
        state: dict[str, Any] = {"url": str(getattr(page, "url", "") or "")}
        if "agent.minimax.io" in url:
            try:
                state = _motion_coach_page_state(page)
            except Exception:
                pass
        logger.warning(
            "MiniMax browser navigation failed (%s): %s | state=%s",
            label,
            exc,
            json.dumps(state, ensure_ascii=True),
        )
        if raise_on_error:
            raise
        return False
    try:
        page.wait_for_load_state("domcontentloaded", timeout=min(timeout_ms, 4000))
    except Exception:
        pass
    try:
        page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 6000))
    except Exception:
        pass
    return True


def _motion_coach_page_state(page: Any) -> dict[str, Any]:
    state: dict[str, Any] = {
        "url": str(getattr(page, "url", "") or ""),
        "composer_ready": _motion_coach_composer_ready(page),
        "cta_present": _motion_coach_cta_present(page),
        "card_present": _motion_coach_card_present(page),
        "search_present": _experts_search_box_present(page),
        "login_modal": _login_modal_visible(page),
    }
    try:
        state["title"] = str(page.title() or "")
    except Exception:
        state["title"] = ""
    state["bot_challenge"] = _bot_challenge_active(page)
    return state


def _bot_challenge_active(page: Any) -> bool:
    try:
        title = str(page.title() or "").strip().lower()
    except Exception:
        title = ""
    if "just a moment" in title or "attention required" in title:
        return True
    try:
        body = str(page.locator("body").inner_text(timeout=1200) or "").lower()
    except Exception:
        body = ""
    markers = (
        "just a moment",
        "checking your browser",
        "verify you are human",
        "enable javascript and cookies to continue",
        "cloudflare",
    )
    return any(marker in body for marker in markers)


def _wait_for_bot_challenge_to_clear(page: Any, timeout_ms: int) -> bool:
    if not _bot_challenge_active(page):
        return True
    deadline = time.monotonic() + max(timeout_ms, 0) / 1000.0
    reloaded = False
    while time.monotonic() < deadline:
        if not _bot_challenge_active(page):
            return True
        _safe_page_wait(page, 1800)
        remaining = deadline - time.monotonic()
        if not reloaded and remaining > 1.5:
            try:
                page.reload(wait_until="domcontentloaded", timeout=min(int(remaining * 1000), 12000))
                reloaded = True
            except Exception:
                reloaded = True
                continue
    return not _bot_challenge_active(page)


def _click_motion_coach_cta(page: Any, timeout_ms: int) -> bool:
    if _click_first_visible(
        page,
        (
            "button:has-text('Type to chat with AI Motion Coach')",
            "button:has-text('Start Chat')",
            "button:has-text('Chat with AI Motion Coach')",
        ),
        timeout_ms=timeout_ms,
    ):
        return True

    role_patterns = (
        re.compile(r"type to chat with ai motion coach", re.I),
        re.compile(r"start chat", re.I),
        re.compile(r"chat with ai motion coach", re.I),
    )
    for pattern in role_patterns:
        try:
            locator = page.get_by_role("button", name=pattern).first
            if locator.count() > 0:
                locator.click(timeout=timeout_ms)
                return True
        except Exception:
            continue

    text_patterns = (
        "Type to chat with AI Motion Coach",
        "Start Chat",
        "Chat with AI Motion Coach",
    )
    for pattern in text_patterns:
        try:
            locator = page.get_by_text(pattern, exact=False).first
            if locator.count() > 0:
                locator.click(timeout=timeout_ms)
                return True
        except Exception:
            continue
    return False


def _click_motion_coach_card(page: Any, timeout_ms: int) -> bool:
    try:
        card = page.locator("img[alt='AI Motion Coach']").first
        if card.count() > 0:
            card.click(timeout=timeout_ms)
            return True
    except Exception:
        pass
    try:
        page.get_by_text("AI Motion Coach", exact=False).first.click(timeout=timeout_ms)
        return True
    except Exception:
        return False


def _resolve_experts_search_box(page: Any) -> Any | None:
    selectors = (
        "input[placeholder='Search experts']:not([readonly])",
        "input[placeholder='Search experts']",
        "[aria-label='Search experts']",
    )
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() > 0:
                return locator
        except Exception:
            continue
    try:
        locator = page.get_by_role("textbox", name=re.compile(r"search experts", re.I)).first
        if locator.count() > 0:
            return locator
    except Exception:
        pass
    return None


def _login_modal_visible(page: Any) -> bool:
    return (
        _locator_is_visible(page, "button:has-text('Continue with Google')", timeout_ms=600)
        or _locator_is_visible(page, "text=Welcome to MiniMax", timeout_ms=600)
    )


def _login_with_google_if_needed(page: Any, email: str, password: str, timeout_ms: int) -> None:
    if not _locator_is_visible(page, "button:has-text('Continue with Google')", timeout_ms=900):
        return

    origin_page = page
    google_btn = page.locator("button:has-text('Continue with Google')").first
    if not _click_locator_robust(
        google_btn,
        timeout_ms=timeout_ms,
        description="button:has-text('Continue with Google')",
    ):
        raise RuntimeError("MiniMax browser login failed: cannot start Google auth flow")

    # Google auth can open in current tab or in a popup page.
    google_page = page
    start_wait = time.monotonic()
    while (time.monotonic() - start_wait) < 12:
        if "accounts.google.com" in (google_page.url or ""):
            break
        candidate = None
        for p in page.context.pages:
            if "accounts.google.com" in (p.url or ""):
                candidate = p
                break
        if candidate is not None:
            google_page = candidate
            break
        page.wait_for_timeout(250)

    if "accounts.google.com" not in (google_page.url or ""):
        candidate_pages: list[Any] = []
        try:
            candidate_pages = list(origin_page.context.pages)
        except Exception:
            candidate_pages = [origin_page]
        if origin_page not in candidate_pages:
            candidate_pages.append(origin_page)
        for candidate in candidate_pages:
            try:
                url = str(getattr(candidate, "url", "") or "")
            except Exception:
                url = ""
            if "agent.minimax.io" not in url:
                continue
            if _locator_is_visible(candidate, ".tiptap-editor", timeout_ms=800) and not _login_modal_visible(candidate):
                try:
                    candidate.bring_to_front()
                except Exception:
                    pass
                return
        if _login_modal_visible(origin_page):
            raise RuntimeError("MiniMax browser login failed: Google auth flow did not open")
        return

    try:
        google_page.bring_to_front()
    except Exception:
        pass

    # Account chooser fast-path.
    account_selectors = (
        '[data-email="{}"]'.format(email),
        'div[aria-label="{}"]'.format(email),
        'div:has-text("{}")'.format(email),
    )
    if _click_first_visible(google_page, account_selectors, timeout_ms=2000):
        try:
            google_page.wait_for_timeout(900)
        except Exception:
            pass

    # Email step.
    email_selectors = (
        "input[type='email']",
        "input#identifierId",
        "input[name='identifier']",
    )
    for selector in email_selectors:
        try:
            locator = google_page.locator(selector).first
            if locator.count() > 0 and locator.is_visible(timeout=1200):
                locator.fill(email, timeout=timeout_ms)
                if not _click_first_visible(
                    google_page,
                    ("#identifierNext button", "button:has-text('Next')", "button:has-text('Suivant')"),
                    timeout_ms=3000,
                ):
                    locator.press("Enter")
                break
        except Exception:
            continue

    # Password step.
    pass_selectors = (
        "input[type='password']",
        "input[name='Passwd']",
    )
    pass_filled = False
    pass_deadline = time.monotonic() + 18
    while time.monotonic() < pass_deadline and not pass_filled:
        for selector in pass_selectors:
            try:
                locator = google_page.locator(selector).first
                if locator.count() > 0 and locator.is_visible(timeout=1200):
                    if not str(password or "").strip():
                        raise RuntimeError(
                            "MiniMax browser login failed: Google password step required but MINIMAX_BROWSER_PASSWORD is empty"
                        )
                    locator.fill(password, timeout=timeout_ms)
                    if not _click_first_visible(
                        google_page,
                        ("#passwordNext button", "button:has-text('Next')", "button:has-text('Suivant')"),
                        timeout_ms=3000,
                    ):
                        locator.press("Enter")
                    pass_filled = True
                    break
            except Exception:
                continue
        if not pass_filled:
            google_page.wait_for_timeout(250)

    # Consent screen can appear after account selection even when password was not required.
    consent_deadline = time.monotonic() + 12
    while time.monotonic() < consent_deadline:
        clicked = _click_first_visible(
            google_page,
            (
                "button:has-text('Continue')",
                "button:has-text('Allow')",
                "button:has-text('Autoriser')",
                "button:has-text('Accepter')",
            ),
            timeout_ms=1200,
        )
        if clicked:
            try:
                google_page.wait_for_timeout(900)
            except Exception:
                pass
            break
        if "accounts.google.com" not in (google_page.url or ""):
            break
        google_page.wait_for_timeout(250)

    # Wait until the original MiniMax page is actually authenticated.
    redirect_deadline = time.monotonic() + 45
    while time.monotonic() < redirect_deadline:
        candidate_pages: list[Any] = []
        try:
            candidate_pages = list(origin_page.context.pages)
        except Exception:
            candidate_pages = [origin_page]
        if origin_page not in candidate_pages:
            candidate_pages.append(origin_page)
        for candidate in candidate_pages:
            try:
                url = str(getattr(candidate, "url", "") or "")
            except Exception:
                url = ""
            if "agent.minimax.io" not in url:
                continue
            if _locator_is_visible(candidate, ".tiptap-editor", timeout_ms=800) and not _login_modal_visible(candidate):
                try:
                    candidate.bring_to_front()
                except Exception:
                    pass
                return
        origin_page.wait_for_timeout(300)

    raise RuntimeError(
        "MiniMax browser login failed: Google auth did not return to agent.minimax.io (2FA or verification required)."
    )


def _ensure_browser_authenticated(page: Any, email: str, password: str, timeout_ms: int) -> None:
    # Direct login form (if available in some MiniMax variants).
    _minimax_login_if_needed(page, email, password, timeout_ms)
    # Google OAuth modal fallback.
    _login_with_google_if_needed(page, email, password, timeout_ms)
    # Best-effort close of any remaining login modal.
    _click_first_visible(page, ("button[aria-label='Close']", "img[alt='close']", "img[alt='Close']"), timeout_ms=1200)


def _open_motion_coach_chat(page: Any, timeout_ms: int, *, email: str = "", password: str = "") -> None:
    direct_wait_ms = min(timeout_ms, 15000)
    composer_wait_ms = min(timeout_ms, 12000)
    can_reauth = bool(str(email or "").strip() and str(password or "").strip())

    for auth_cycle in range(2 if can_reauth else 1):
        restart_after_auth = False
        for attempt in range(2):
            current_page_ready = False
            if _page_is_motion_coach_chat(page):
                current_page_ready = _wait_for_page_condition(
                    page,
                    lambda: _motion_coach_composer_ready(page) or _motion_coach_cta_present(page) or _login_modal_visible(page),
                    timeout_ms=min(timeout_ms, 5000),
                )
            if not current_page_ready and not _goto_minimax_page(
                page,
                _motion_coach_expert_url(),
                timeout_ms,
                label="motion_coach_direct",
                raise_on_error=False,
            ):
                if attempt == 0:
                    continue
                break
            if not _wait_for_bot_challenge_to_clear(page, timeout_ms=min(timeout_ms, 25000)):
                state = json.dumps(_motion_coach_page_state(page), ensure_ascii=True)
                logger.warning("MiniMax Motion Coach direct page blocked by anti-bot challenge: %s", state)
                if auth_cycle == 0 and attempt == 0:
                    continue
                raise RuntimeError("MiniMax browser flow blocked by anti-bot challenge")

            _wait_for_page_condition(
                page,
                lambda: _motion_coach_composer_ready(page) or _motion_coach_cta_present(page) or _login_modal_visible(page),
                timeout_ms=direct_wait_ms,
            )
            if _login_modal_visible(page):
                logger.warning(
                    "MiniMax Motion Coach direct page requires authentication: %s",
                    json.dumps(_motion_coach_page_state(page), ensure_ascii=True),
                )
                if can_reauth:
                    _ensure_browser_authenticated(page, email=email, password=password, timeout_ms=timeout_ms)
                    restart_after_auth = True
                    break
            if _motion_coach_composer_ready(page):
                return
            if _click_motion_coach_cta(page, timeout_ms=min(timeout_ms, 5000)):
                if _wait_for_page_condition(page, lambda: _motion_coach_composer_ready(page), timeout_ms=composer_wait_ms):
                    return
                try:
                    page.wait_for_selector(".tiptap-editor", timeout=composer_wait_ms)
                    return
                except Exception:
                    if _motion_coach_composer_ready(page):
                        return
            if attempt == 0:
                logger.warning(
                    "MiniMax Motion Coach direct expert page not ready, retrying once: %s",
                    json.dumps(_motion_coach_page_state(page), ensure_ascii=True),
                )

        if restart_after_auth:
            continue

        logger.warning(
            "MiniMax Motion Coach direct expert page unavailable, falling back to experts index: %s",
            json.dumps(_motion_coach_page_state(page), ensure_ascii=True),
        )
        if not _goto_minimax_page(
            page,
            "https://agent.minimax.io/experts",
            timeout_ms,
            label="motion_coach_experts_index",
            raise_on_error=False,
        ):
            if auth_cycle == 0:
                continue
            raise RuntimeError("MiniMax browser flow failed: experts index navigation unavailable")
        if not _wait_for_bot_challenge_to_clear(page, timeout_ms=min(timeout_ms, 25000)):
            state = json.dumps(_motion_coach_page_state(page), ensure_ascii=True)
            logger.warning("MiniMax Motion Coach experts page blocked by anti-bot challenge: %s", state)
            if auth_cycle == 0:
                continue
            raise RuntimeError("MiniMax browser flow blocked by anti-bot challenge")

        _wait_for_page_condition(
            page,
            lambda: _motion_coach_card_present(page) or _experts_search_box_present(page) or _login_modal_visible(page),
            timeout_ms=min(timeout_ms, 15000),
        )

        if _login_modal_visible(page):
            logger.warning(
                "MiniMax Motion Coach experts index requires authentication: %s",
                json.dumps(_motion_coach_page_state(page), ensure_ascii=True),
            )
            if can_reauth and auth_cycle == 0:
                _ensure_browser_authenticated(page, email=email, password=password, timeout_ms=timeout_ms)
                continue

        clicked = _click_motion_coach_card(page, timeout_ms=min(timeout_ms, 5000))
        if not clicked and _experts_search_box_present(page):
            _click_first_visible(
                page,
                (
                    "input[placeholder='Search experts'][readonly]",
                    "div:has(input[placeholder='Search experts'])",
                    "input[placeholder='Search experts']",
                    "[aria-label='Search experts']",
                ),
                timeout_ms=3500,
            )
            search_box = _resolve_experts_search_box(page)
            if search_box is not None:
                search_box.fill("AI Motion Coach", timeout=timeout_ms)
                try:
                    search_box.press("Enter")
                except Exception:
                    pass
                _wait_for_page_condition(page, lambda: _motion_coach_card_present(page), timeout_ms=min(timeout_ms, 8000))
                clicked = _click_motion_coach_card(page, timeout_ms=min(timeout_ms, 5000))

        if not clicked:
            state = json.dumps(_motion_coach_page_state(page), ensure_ascii=True)
            logger.warning("MiniMax Motion Coach entry unavailable after fallback: %s", state)
            if can_reauth and auth_cycle == 0:
                _ensure_browser_authenticated(page, email=email, password=password, timeout_ms=timeout_ms)
                continue
            raise RuntimeError("MiniMax browser flow failed: AI Motion Coach entry unavailable")

        _wait_for_page_condition(
            page,
            lambda: _motion_coach_composer_ready(page) or _motion_coach_cta_present(page) or _login_modal_visible(page),
            timeout_ms=min(timeout_ms, 12000),
        )
        if _login_modal_visible(page):
            logger.warning(
                "MiniMax Motion Coach chat CTA blocked by authentication: %s",
                json.dumps(_motion_coach_page_state(page), ensure_ascii=True),
            )
            if can_reauth and auth_cycle == 0:
                _ensure_browser_authenticated(page, email=email, password=password, timeout_ms=timeout_ms)
                continue
        if not _motion_coach_composer_ready(page) and not _click_motion_coach_cta(page, timeout_ms=min(timeout_ms, 5000)):
            state = json.dumps(_motion_coach_page_state(page), ensure_ascii=True)
            logger.warning("MiniMax Motion Coach chat CTA unavailable: %s", state)
            if can_reauth and auth_cycle == 0:
                _ensure_browser_authenticated(page, email=email, password=password, timeout_ms=timeout_ms)
                continue
            raise RuntimeError("MiniMax browser flow failed: AI Motion Coach chat CTA unavailable")

        try:
            page.wait_for_url(re.compile(r"https://agent\.minimax\.io/(expert/chat|chat)"), timeout=timeout_ms)
        except Exception:
            pass
        if _wait_for_page_condition(page, lambda: _motion_coach_composer_ready(page), timeout_ms=composer_wait_ms):
            return
        try:
            page.wait_for_selector(".tiptap-editor", timeout=composer_wait_ms)
            return
        except Exception:
            if _motion_coach_composer_ready(page):
                return
            state = json.dumps(_motion_coach_page_state(page), ensure_ascii=True)
            logger.warning("MiniMax Motion Coach composer unavailable after CTA: %s", state)
            if can_reauth and auth_cycle == 0:
                _ensure_browser_authenticated(page, email=email, password=password, timeout_ms=timeout_ms)
                continue
            raise RuntimeError("MiniMax browser flow failed: AI Motion Coach composer unavailable")

    raise RuntimeError("MiniMax browser flow failed: AI Motion Coach entry unavailable")


def _populate_browser_message(
    page: Any,
    video_path: str,
    prompt: str,
    timeout_ms: int,
    *,
    email: str = "",
    password: str = "",
) -> None:
    page.wait_for_selector(".tiptap-editor", timeout=timeout_ms)
    if _blanket_overlay_visible(page):
        _dismiss_browser_blanket_overlay(page, timeout_ms=min(timeout_ms, 2500))

    editor = page.locator(".tiptap-editor").first
    _focus_browser_editor(editor, timeout_ms=timeout_ms)
    for hotkey in ("Meta+A", "Control+A"):
        try:
            page.keyboard.press(hotkey)
        except Exception:
            continue
    try:
        page.keyboard.press("Backspace")
    except Exception:
        pass
    if prompt:
        try:
            _set_browser_editor_text(editor, prompt)
        except Exception:
            page.keyboard.type(prompt)

    # Upload video file via hidden input.
    upload_input = page.locator("input[type='file']").last
    if upload_input.count() <= 0:
        raise RuntimeError("MiniMax browser flow failed: upload input not found")
    upload_input.set_input_files(video_path, timeout=timeout_ms)

    # Wait briefly for upload attachment binding.
    file_name = Path(video_path).name
    try:
        page.locator("text={}".format(file_name)).first.wait_for(timeout=8000)
    except Exception:
        page.wait_for_timeout(1300)

    if _login_modal_visible(page):
        dismissed = _dismiss_browser_blanket_overlay(page, timeout_ms=min(timeout_ms, 2500))
        if _login_modal_visible(page) and not dismissed:
            if str(email or "").strip() and str(password or "").strip():
                _ensure_browser_authenticated(page, email=email, password=password, timeout_ms=timeout_ms)
                if not _locator_is_visible(page, ".tiptap-editor", timeout_ms=3000):
                    _open_motion_coach_chat(page, timeout_ms=timeout_ms, email=email, password=password)
                if not _login_modal_visible(page):
                    return _populate_browser_message(
                        page,
                        video_path,
                        prompt,
                        timeout_ms,
                        email=email,
                        password=password,
                    )
            raise RuntimeError("MiniMax browser flow blocked by login modal before send")


def _focus_browser_editor(editor: Any, *, timeout_ms: int) -> None:
    click_timeout = min(timeout_ms, 2500)
    try:
        editor.click(timeout=click_timeout)
        return
    except Exception as click_exc:
        logger.warning("MiniMax browser editor click blocked, using DOM focus fallback: %s", click_exc)
        try:
            editor.evaluate(
                """(el) => {
                    if (!el) return;
                    el.focus();
                    const selection = window.getSelection ? window.getSelection() : null;
                    if (!selection || !document.createRange) return;
                    selection.removeAllRanges();
                    const range = document.createRange();
                    range.selectNodeContents(el);
                    range.collapse(false);
                    selection.addRange(range);
                }"""
            )
            return
        except Exception:
            try:
                editor.click(timeout=click_timeout, force=True)
                return
            except Exception:
                raise click_exc


def _set_browser_editor_text(editor: Any, prompt: str) -> None:
    editor.evaluate(
        """(el, text) => {
            if (!el) return;
            const value = String(text || "");
            el.focus();
            el.textContent = value;
            const selection = window.getSelection ? window.getSelection() : null;
            if (selection && document.createRange) {
                selection.removeAllRanges();
                const range = document.createRange();
                range.selectNodeContents(el);
                range.collapse(false);
                selection.addRange(range);
            }
            const inputEvent = typeof InputEvent === "function"
                ? new InputEvent("input", { bubbles: true, data: value, inputType: "insertText" })
                : new Event("input", { bubbles: true });
            el.dispatchEvent(inputEvent);
        }""",
        prompt,
    )


def _send_button_enabled(page: Any) -> bool:
    try:
        return bool(
            page.evaluate(
                """() => {
                    const root = document.querySelector('#input-send-icon');
                    if (!root) return false;
                    const target = root.firstElementChild || root;
                    const className = String(target.className || '');
                    const ariaDisabled = String(target.getAttribute('aria-disabled') || '').toLowerCase();
                    const disabled = className.includes('cursor-not-allowed')
                        || className.includes('bg-bg_interaction_primary_inactive')
                        || ariaDisabled === 'true';
                    return !disabled;
                }"""
            )
        )
    except Exception:
        return False


def _send_browser_message(page: Any, timeout_ms: int) -> None:
    if _blanket_overlay_visible(page):
        _dismiss_browser_blanket_overlay(page, timeout_ms=min(timeout_ms, 2500))
    send_ready = _wait_for_page_condition(page, lambda: _send_button_enabled(page), timeout_ms=min(timeout_ms, 8000), step_ms=200)
    if not send_ready:
        try:
            editor = page.locator(".tiptap-editor").first
            prompt_text = str(editor.inner_text(timeout=1200) or "").strip()
            if prompt_text:
                _set_browser_editor_text(editor, prompt_text)
                send_ready = _wait_for_page_condition(
                    page,
                    lambda: _send_button_enabled(page),
                    timeout_ms=min(timeout_ms, 8000),
                    step_ms=200,
                )
        except Exception:
            send_ready = False
    if not send_ready:
        try:
            send_html = str(page.locator("#input-send-icon").first.evaluate("(el) => el.outerHTML"))
        except Exception:
            send_html = ""
        raise RuntimeError("MiniMax browser flow failed: send button stayed disabled {}".format(send_html[:400]))
    if not _click_first_visible(page, ("#input-send-icon", "div#input-send-icon"), timeout_ms=2200):
        try:
            send_icon = page.locator("#input-send-icon").first
            if send_icon.count() > 0 and send_icon.is_visible(timeout=1200):
                send_icon.click(timeout=timeout_ms, force=True)
                return
            page.keyboard.press("Enter")
        except Exception as exc:
            raise RuntimeError("MiniMax browser flow failed: send action not available") from exc


def _upload_and_send_via_browser(
    page: Any,
    video_path: str,
    prompt: str,
    timeout_ms: int,
    *,
    email: str,
    password: str,
) -> None:
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            if _blanket_overlay_visible(page):
                _dismiss_browser_blanket_overlay(page, timeout_ms=min(timeout_ms, 2500))
            if _login_modal_visible(page):
                _ensure_browser_authenticated(page, email=email, password=password, timeout_ms=timeout_ms)
                if not _locator_is_visible(page, ".tiptap-editor", timeout_ms=3000):
                    _open_motion_coach_chat(page, timeout_ms=timeout_ms, email=email, password=password)
            _populate_browser_message(
                page,
                video_path,
                prompt,
                timeout_ms,
                email=email,
                password=password,
            )
            _send_browser_message(page, timeout_ms)
            if _login_modal_visible(page):
                dismissed = _dismiss_browser_blanket_overlay(page, timeout_ms=min(timeout_ms, 2500))
                if _login_modal_visible(page) and not dismissed:
                    raise RuntimeError("MiniMax browser flow blocked by login modal after send")
            return
        except Exception as exc:
            last_exc = exc
            low_exc = str(exc).lower()
            retryable_send_issue = "send button stayed disabled" in low_exc or "send action not available" in low_exc
            if attempt > 0:
                break
            if not _login_modal_visible(page) and "login modal" not in low_exc and not retryable_send_issue:
                break
            if retryable_send_issue:
                _safe_page_wait(page, 1200)
            _ensure_browser_authenticated(page, email=email, password=password, timeout_ms=timeout_ms)
            if not _locator_is_visible(page, ".tiptap-editor", timeout_ms=3000):
                _open_motion_coach_chat(page, timeout_ms=timeout_ms, email=email, password=password)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("MiniMax browser flow failed before send")


def _compact_text(raw: str) -> str:
    return re.sub(r"\s+", " ", str(raw or "")).strip()


def _is_analysis_candidate_text(text: str) -> bool:
    normalized = _compact_text(text)
    if len(normalized) < 80:
        return False

    low = normalized.lower()
    if _extract_tagged_report_block(text):
        return True

    if _looks_like_process_text(normalized):
        process_only_markers = (
            "format de sortie obligatoire",
            "the user is asking me to",
            "the user wants me to",
            "they want me to",
            "let me",
            "je dois",
            "i must",
            "you have control of the ai window",
        )
        if any(marker in low for marker in process_only_markers):
            return False
        if not _has_final_output_markers(normalized):
            return False

    if _extract_markdown_report_block(text):
        return True

    if _looks_like_process_text(normalized) and not _has_final_output_markers(normalized):
        return False

    negative_markers = (
        "bonjour ! je suis ravi de vous accompagner",
        "je suis ravi de vous accompagner en tant que coach",
        "upload your workout video",
        "send me your video",
        "i'd be happy to analyze",
        "could you please provide",
        "once you share the video",
        "personal ai coach that never sleeps",
    )
    if any(marker in low for marker in negative_markers):
        return False

    if _has_final_output_markers(normalized):
        return True

    positive_markers = (
        '"exercise"',
        '"score"',
        '"reps"',
        '"intensity"',
        '"report_markdown"',
        '"sections"',
        "analyse biomecanique",
        "resume",
        "corrections prioritaires",
        "intensite de serie",
        "decomposition du score",
        "plan action",
        "point biomecanique",
        "score global:",
        "repetitions detectees:",
        "repetitions completes:",
        "repetitions partielles:",
        "repos inter-reps moyen:",
        "## resume",
        "## amplitude de mouvement",
        "## analyse rep par rep",
        "## plan action",
    )
    if any(marker in low for marker in positive_markers):
        return True

    if re.search(r"\b\d{1,3}/100\b", low) and re.search(r"\b\d+\s*reps?\b", low):
        return True
    if re.search(r"\bexercise\b", low) and re.search(r"\bconfidence\b", low):
        return True
    return False


def _score_dom_candidate(text: str) -> int:
    low = text.lower()
    if _looks_like_process_text(text) and not _has_final_output_markers(text):
        return -1000
    score = len(text)
    if "{" in text and "}" in text:
        score += 220
    if _has_final_output_markers(text):
        score += 420
    for token in ('"exercise"', '"reps"', '"score"', '"intensity"', '"report_markdown"', '"sections"'):
        if token in low:
            score += 120
    for token in (
        "analyse biomecanique",
        "corrections prioritaires",
        "intensite de serie",
        "decomposition du score",
        "plan action",
    ):
        if token in low:
            score += 80
    return score


def _collect_dom_analysis_candidates(page: Any, max_items: int = 120) -> list[str]:
    script = """
() => {
  const selectors = [
    "[data-message-author-role='assistant']",
    "[data-message-role='assistant']",
    "[data-testid*='assistant']",
    ".markdown-body",
    "[class*='markdown']",
    "[class*='assistant'] [class*='content']"
  ];
  const out = [];
  for (const sel of selectors) {
    for (const node of Array.from(document.querySelectorAll(sel))) {
      const txt = (node && (node.innerText || node.textContent || "") || "").trim();
      if (txt) out.push(txt);
    }
  }
  return out.slice(-400);
}
"""
    try:
        raw_values = page.evaluate(script)
    except Exception:
        return []

    if not isinstance(raw_values, list):
        return []

    filtered: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        text = _compact_text(str(raw or ""))
        if len(text) < 60:
            continue
        low = text.lower()
        if low.startswith("tu es un coach biomecanique expert"):
            continue
        if "analyse la video envoyee et reponds uniquement en json" in low:
            continue
        if "start chat" in low:
            continue
        if not _is_analysis_candidate_text(text):
            continue
        if text not in seen:
            seen.add(text)
            filtered.append(text)

    if len(filtered) > max_items:
        return filtered[-max_items:]
    return filtered


def _collect_dom_text_candidates(page: Any, max_items: int = 160) -> list[str]:
    script = """
() => {
  const selectors = [
    "[data-message-author-role='assistant']",
    "[data-message-role='assistant']",
    "[data-testid*='assistant']",
    ".markdown-body",
    "[class*='markdown']",
    "[class*='assistant'] [class*='content']"
  ];
  const out = [];
  for (const sel of selectors) {
    for (const node of Array.from(document.querySelectorAll(sel))) {
      const txt = (node && (node.innerText || node.textContent || "") || "").trim();
      if (txt) out.push(txt);
    }
  }
  return out.slice(-400);
}
"""
    try:
        raw_values = page.evaluate(script)
    except Exception:
        return []
    if not isinstance(raw_values, list):
        return []

    filtered: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        text = _clean_markdown_report_text(str(raw or ""))
        if len(text) < 80:
            continue
        low = text.lower()
        if _looks_like_process_text(text):
            continue
        if low.startswith("tu es un coach biomecanique expert"):
            continue
        if "analyse cette video de musculation comme un coach expert" in low:
            continue
        if "format de sortie obligatoire" in low:
            continue
        if "start chat" in low:
            continue
        if text not in seen:
            seen.add(text)
            filtered.append(text)
    if len(filtered) > max_items:
        return filtered[-max_items:]
    return filtered


def _collect_page_report_candidate(page: Any) -> str:
    dom_candidates = _collect_dom_analysis_candidates(page)
    if dom_candidates:
        return _select_new_dom_candidate(dom_candidates, set())

    broad_dom_candidates = _collect_dom_text_candidates(page)
    unstructured = [candidate for candidate in broad_dom_candidates if _looks_like_unstructured_report_text(candidate)]
    if unstructured:
        unstructured.sort(key=lambda item: (len(item), item.count("\n")), reverse=True)
        return unstructured[0]

    try:
        body_text = str(page.locator("body").inner_text(timeout=1800) or "")
    except Exception:
        return ""
    report_block = _extract_markdown_report_block(body_text)
    if report_block:
        return report_block
    if _looks_like_unstructured_report_text(body_text):
        return _clean_markdown_report_text(body_text)
    if _is_analysis_candidate_text(body_text):
        return _compact_text(body_text)
    return ""


def _browser_task_failed_visible(page: Any) -> bool:
    try:
        body_text = str(page.locator("body").inner_text(timeout=1500) or "")
    except Exception:
        return False
    return "task failed" in body_text.lower()


def _retry_browser_task(page: Any, timeout_ms: int) -> bool:
    return _click_first_visible(
        page,
        (
            "button:has-text('Retry')",
            "button:has-text('Try again')",
            "button:has-text('Réessayer')",
        ),
        timeout_ms=min(timeout_ms, 3500),
    )


def _select_new_dom_candidate(candidates: list[str], baseline: set[str]) -> str:
    fresh = [candidate for candidate in candidates if candidate not in baseline]
    if not fresh:
        return ""
    fresh.sort(key=_score_dom_candidate, reverse=True)
    return fresh[0]


def _run_minimax_browser_only_once(
    *,
    prepared: _PreparedVideo,
    prompt: str,
    poll_interval: float,
    timeout_s_effective: int,
    video_hash: str,
    prompt_hash: str,
) -> MiniMaxAnalysis:
    email = str(getattr(settings, "minimax_browser_email", "") or "").strip()
    password = str(getattr(settings, "minimax_browser_password", "") or "").strip()
    has_auth_seed = _browser_auth_seed_available()
    if not email or (not password and not has_auth_seed):
        raise RuntimeError(
            "MiniMax browser-only mode requires MINIMAX_BROWSER_EMAIL and either MINIMAX_BROWSER_PASSWORD "
            "or persisted browser auth (profile/storage/cookie)"
        )

    timeout_s = max(45, int(getattr(settings, "minimax_browser_timeout_s", 120) or 120))
    timeout_ms = timeout_s * 1000
    headless = _as_bool(getattr(settings, "minimax_browser_headless", True), True)
    profile_dir = _browser_profile_dir()

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Playwright unavailable for MiniMax browser-only mode. Install dependency and Chromium."
        ) from exc

    start = time.monotonic()
    state: dict[str, Any] = {
        "sent": False,
        "done": False,
        "best_text": "",
        "latest_text": "",
        "stable_rounds": 0,
        "chat_status": 0,
        "chat_status_known": False,
        "baseline_ids": set(),
        "known_ids": set(),
        "dom_baseline": set(),
        "dom_candidates_seen": 0,
        "dom_fallback_used": False,
        "chat_name": "",
        "sent_chat_id": "",
        "responses_seen": 0,
        "motion_coach_opened": False,
        "task_failed_retries": 0,
        "page_report": "",
        "timeout_debug": {},
    }

    def _on_response(response: Any) -> None:
        url = str(getattr(response, "url", "") or "")
        if "/matrix/api/v1/chat/send_msg" in url:
            try:
                payload = response.json()
            except Exception:
                payload = {}
            if isinstance(payload, dict):
                sent_chat_id = str(payload.get("chat_id") or "").strip()
                if sent_chat_id:
                    state["sent_chat_id"] = sent_chat_id
        if "/matrix/api/v1/chat/get_chat_detail" not in url:
            return
        try:
            payload = response.json()
        except Exception:
            return
        state["responses_seen"] = int(state.get("responses_seen", 0) or 0) + 1
        state["chat_status_known"] = True
        chat_name = _extract_chat_name(payload)
        if chat_name and not state.get("chat_name"):
            state["chat_name"] = chat_name

        if not state.get("sent"):
            _, all_ids, chat_status = _extract_agent_message(payload, known_message_ids=set())
            state["baseline_ids"] = set(all_ids)
            state["known_ids"] = set(all_ids)
            state["chat_status"] = chat_status
            return

        known_ids = set(state.get("known_ids", set()))
        candidate, all_ids, chat_status = _extract_agent_message(payload, known_message_ids=known_ids)
        state["known_ids"] = set(all_ids)
        state["chat_status"] = chat_status
        if candidate:
            state["latest_text"] = candidate
        if candidate and _is_analysis_candidate_text(candidate):
            if candidate == state.get("best_text", ""):
                state["stable_rounds"] = int(state.get("stable_rounds", 0) or 0) + 1
            else:
                state["best_text"] = candidate
                state["stable_rounds"] = 0
            if chat_status != 1 or int(state.get("stable_rounds", 0) or 0) >= 2:
                state["done"] = True

    with sync_playwright() as p:
        context = None
        page = None
        try:
            launch_options = _browser_launch_options(headless=headless)
            try:
                context = p.chromium.launch_persistent_context(
                    str(profile_dir),
                    **launch_options,
                )
            except Exception as launch_exc:
                logger.warning("Playwright Chromium launch failed, trying install: %s", launch_exc)
                try:
                    subprocess.run(
                        ["python3", "-m", "playwright", "install", "chromium"],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                except Exception as install_exc:
                    raise RuntimeError(
                        "MiniMax browser-only failed: Chromium not available and auto-install failed ({})"
                        .format(install_exc)
                    ) from launch_exc
                context = p.chromium.launch_persistent_context(
                    str(profile_dir),
                    **launch_options,
                )

            _install_browser_stealth(context)
            _inject_browser_cookies(context)
            _inject_browser_storage(context)
            try:
                context.set_extra_http_headers(
                    {
                        "Accept-Language": "en-US,en;q=0.9",
                        "Upgrade-Insecure-Requests": "1",
                    }
                )
            except Exception:
                pass
            page = context.new_page() if hasattr(context, "new_page") else (context.pages[0] if context.pages else context.new_page())
            page.on("response", _on_response)

            _goto_minimax_page(page, _motion_coach_expert_url(), timeout_ms, label="motion_coach_bootstrap")
            _ensure_browser_authenticated(page, email=email, password=password, timeout_ms=timeout_ms)
            _open_motion_coach_chat(page, timeout_ms=timeout_ms, email=email, password=password)
            state["motion_coach_opened"] = True

            # Baseline collection window.
            page.wait_for_timeout(1400)
            state["known_ids"] = set(state.get("baseline_ids", set()))
            state["dom_baseline"] = set(_collect_dom_analysis_candidates(page))

            _upload_and_send_via_browser(
                page,
                prepared.path,
                prompt,
                timeout_ms=timeout_ms,
                email=email,
                password=password,
            )
            state["sent"] = True
            state["known_ids"] = set(state.get("baseline_ids", set()))
            if _wait_for_page_condition(page, lambda: bool(str(state.get("sent_chat_id", "")).strip()), timeout_ms=8000, step_ms=250):
                sent_chat_id = str(state.get("sent_chat_id", "") or "").strip()
                if sent_chat_id:
                    _goto_minimax_page(page, _chat_page_url(sent_chat_id), timeout_ms, label="motion_coach_sent_chat")
                    state["dom_baseline"] = set(_collect_dom_analysis_candidates(page))

            deadline = time.monotonic() + timeout_s_effective
            sleep_ms = max(300, int(max(0.8, poll_interval) * 1000))
            while time.monotonic() < deadline:
                if state.get("best_text") and (
                    state.get("done")
                    or (
                        bool(state.get("chat_status_known"))
                        and int(state.get("chat_status", 0) or 0) != 1
                    )
                ):
                    break

                if _browser_task_failed_visible(page):
                    page_report = _collect_page_report_candidate(page)
                    if page_report:
                        state["latest_text"] = page_report
                        state["best_text"] = page_report
                        state["done"] = True
                        break
                    if int(state.get("task_failed_retries", 0) or 0) < 2 and _retry_browser_task(page, timeout_ms=timeout_ms):
                        state["task_failed_retries"] = int(state.get("task_failed_retries", 0) or 0) + 1
                        page.wait_for_timeout(2500)
                        continue
                    raise RuntimeError("MiniMax browser task failed in UI")

                page.wait_for_timeout(sleep_ms)
                dom_candidates = _collect_dom_analysis_candidates(page)
                state["dom_candidates_seen"] = max(
                    int(state.get("dom_candidates_seen", 0) or 0),
                    len(dom_candidates),
                )
                dom_baseline = set(state.get("dom_baseline", set()))
                dom_candidate = _select_new_dom_candidate(dom_candidates, dom_baseline)
                if dom_candidate:
                    state["dom_fallback_used"] = True
                    state["latest_text"] = dom_candidate
                    if dom_candidate == state.get("best_text", ""):
                        state["stable_rounds"] = int(state.get("stable_rounds", 0) or 0) + 1
                    else:
                        state["best_text"] = dom_candidate
                        state["stable_rounds"] = 0
                    if int(state.get("stable_rounds", 0) or 0) >= 2:
                        state["done"] = True
                elif not state.get("best_text"):
                    page_report = _collect_page_report_candidate(page)
                    if page_report:
                        state["dom_fallback_used"] = True
                        state["latest_text"] = page_report
                        state["best_text"] = page_report
                        state["done"] = True
                page_report_snapshot = _collect_page_report_candidate(page)
                if page_report_snapshot:
                    state["page_report"] = page_report_snapshot

        finally:
            if page is not None and not str(state.get("best_text", "") or "").strip():
                debug: dict[str, Any] = {}
                try:
                    debug["page_state"] = _motion_coach_page_state(page)
                except Exception:
                    pass
                try:
                    body_text = str(page.locator("body").inner_text(timeout=1800) or "")
                    debug["body_tail"] = body_text[-1800:]
                except Exception:
                    pass
                try:
                    shot_path = Path.cwd() / "tmp" / "minimax-timeout-{}.png".format(uuid.uuid4().hex[:8])
                    shot_path.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(shot_path), full_page=True)
                    debug["screenshot"] = str(shot_path)
                except Exception:
                    pass
                state["timeout_debug"] = debug
            if page is not None:
                try:
                    page.off("response", _on_response)
                except Exception:
                    pass
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass

    best_text = str(state.get("best_text", "") or "").strip()
    if not best_text:
        page_report = _clean_markdown_report_text(str(state.get("page_report", "") or ""))
        if page_report:
            best_text = page_report
            analysis = _parse_analysis_payload(best_text)
            if not _analysis_is_valid_final_output(analysis):
                raise RuntimeError(
                    "MiniMax returned process text instead of final analysis: {}".format(best_text[:400])
                )
            elapsed = time.monotonic() - start
            analysis.metadata.update(
                {
                    "transport": "browser_ui_only",
                    "chat_name": str(state.get("chat_name", "") or "").strip(),
                    "motion_coach_validated": bool(state.get("motion_coach_opened")),
                    "motion_coach_validation_source": "expert_browser_flow",
                    "elapsed_s": round(elapsed, 2),
                    "timeout_s_effective": int(timeout_s_effective),
                    "chat_status": int(state.get("chat_status", 0) or 0),
                    "responses_seen": int(state.get("responses_seen", 0) or 0),
                    "dom_fallback_used": True,
                    "dom_candidates_seen": int(state.get("dom_candidates_seen", 0) or 0),
                    "task_failed_retries": int(state.get("task_failed_retries", 0) or 0),
                }
            )
            return analysis
        latest_text = _compact_text(str(state.get("latest_text", "") or ""))
        if latest_text and not _looks_like_process_text(latest_text):
            raise RuntimeError("MiniMax returned non-analysis reply: {}".format(latest_text[:400]))
        timeout_debug = state.get("timeout_debug") or {}
        debug_suffix = ""
        if isinstance(timeout_debug, dict) and timeout_debug:
            debug_suffix = " debug={}".format(json.dumps(timeout_debug, ensure_ascii=False)[:1600])
        raise TimeoutError("MiniMax browser-only response timeout (no assistant message){}".format(debug_suffix))

    analysis = _parse_analysis_payload(best_text)
    if not _analysis_is_valid_final_output(analysis):
        raise RuntimeError(
            "MiniMax returned process text instead of final analysis: {}".format(best_text[:400])
        )
    elapsed = time.monotonic() - start
    chat_name = str(state.get("chat_name", "") or "").strip()
    analysis.metadata.update(
        {
            "transport": "browser_ui_only",
            "chat_name": chat_name,
            "motion_coach_validated": bool(state.get("motion_coach_opened")) or bool(chat_name and _is_motion_coach_label(chat_name)),
            "motion_coach_validation_source": (
                "expert_browser_flow" if bool(state.get("motion_coach_opened")) else "chat_label"
            ),
            "elapsed_s": round(elapsed, 2),
            "timeout_s_effective": int(timeout_s_effective),
            "chat_status": int(state.get("chat_status", 0) or 0),
            "responses_seen": int(state.get("responses_seen", 0) or 0),
            "dom_fallback_used": bool(state.get("dom_fallback_used")),
            "dom_candidates_seen": int(state.get("dom_candidates_seen", 0) or 0),
            "cache_hit": False,
            "video_hash": video_hash,
            "prompt_hash": prompt_hash,
            "source_duration_s": round(float(prepared.source_duration_s), 2),
            "prepared_duration_s": round(float(prepared.prepared_duration_s), 2),
            "source_size_bytes": int(prepared.source_size_bytes),
            "prepared_size_bytes": int(prepared.prepared_size_bytes),
            "prepared_strategy": prepared.strategy,
            "prepared_trimmed": bool(prepared.was_trimmed),
            "prepared_transcoded": bool(prepared.was_transcoded),
            "browser_profile_dir": str(profile_dir),
        }
    )
    if not analysis.report_text:
        analysis.report_text = best_text
    return analysis


def _run_minimax_direct_once(
    *,
    prepared: _PreparedVideo,
    prompt: str,
    timeout_s: int,
    poll_interval: float,
    timeout_s_effective: int,
    video_hash: str,
    prompt_hash: str,
) -> MiniMaxAnalysis:
    client = _MiniMaxClient(timeout_s=timeout_s)
    start = time.monotonic()
    try:
        configured_chat_id = str(getattr(settings, "minimax_chat_id", "") or "").strip()
        chat_id, chat_name_hint, chat_source = _resolve_target_chat_id(
            client,
            configured_chat_id=configured_chat_id,
        )
        baseline_ids: set[str] = set()
        baseline_name = chat_name_hint
        motion_chat_validated = False
        try:
            baseline = client.get_chat_detail(chat_id)
            _, baseline_ids, _ = _extract_agent_message(baseline, known_message_ids=set())
            if not baseline_name:
                baseline_name = _extract_chat_name(baseline)
        except Exception as exc:
            logger.warning("MiniMax baseline get_chat_detail failed (continuing): %s", exc)

        require_motion = _as_bool(getattr(settings, "minimax_require_motion_coach_chat", True), True)
        if require_motion:
            if baseline_name:
                motion_chat_validated = _is_motion_coach_label(baseline_name)
                if not motion_chat_validated:
                    raise RuntimeError(
                        "MiniMax chat mismatch: '{}' is not AI Motion Coach."
                        .format(baseline_name)
                    )
            elif chat_source == "list_chat_motion_match":
                motion_chat_validated = True
            else:
                raise RuntimeError(
                    "MiniMax chat mismatch: unable to validate AI Motion Coach target chat."
                )

        asset = client.upload_video(prepared.path)
        send_resp = client.send_video_message(
            chat_id=chat_id,
            prompt=prompt,
            asset=asset,
            origin_file_name=Path(prepared.path).name,
        )
        send_data = client.unwrap_data(send_resp)
        sent_chat_id = str(send_data.get("chat_id") or chat_id)

        best_text = ""
        stable_rounds = 0
        current_ids = set(baseline_ids)
        last_chat_status = 0
        deadline = time.monotonic() + timeout_s_effective

        while time.monotonic() < deadline:
            detail = client.get_chat_detail(sent_chat_id)
            candidate, all_ids, chat_status = _extract_agent_message(detail, known_message_ids=current_ids)
            last_chat_status = chat_status
            current_ids = all_ids
            if candidate:
                if candidate == best_text:
                    stable_rounds += 1
                else:
                    best_text = candidate
                    stable_rounds = 0

                if chat_status != 1 or stable_rounds >= 2:
                    break
            time.sleep(poll_interval)

        if not best_text:
            raise TimeoutError("MiniMax response timeout (no assistant message)")

        analysis = _parse_analysis_payload(best_text)
        if not _analysis_is_valid_final_output(analysis):
            raise RuntimeError(
                "MiniMax returned process text instead of final analysis: {}".format(best_text[:400])
            )
        elapsed = time.monotonic() - start
        analysis.metadata.update(
            {
                "chat_id": sent_chat_id,
                "chat_name": baseline_name,
                "chat_source": chat_source,
                "motion_coach_validated": bool(motion_chat_validated),
                "file_id": asset.file_id,
                "file_url": asset.file_url,
                "object_key": asset.object_key,
                "elapsed_s": round(elapsed, 2),
                "timeout_s_effective": int(timeout_s_effective),
                "chat_status": last_chat_status,
                "cache_hit": False,
                "video_hash": video_hash,
                "prompt_hash": prompt_hash,
                "source_duration_s": round(float(prepared.source_duration_s), 2),
                "prepared_duration_s": round(float(prepared.prepared_duration_s), 2),
                "source_size_bytes": int(prepared.source_size_bytes),
                "prepared_size_bytes": int(prepared.prepared_size_bytes),
                "prepared_strategy": prepared.strategy,
                "prepared_trimmed": bool(prepared.was_trimmed),
                "prepared_transcoded": bool(prepared.was_transcoded),
            }
        )
        if not analysis.report_text:
            analysis.report_text = best_text
        return analysis
    finally:
        client.close()


def run_minimax_motion_coach(video_path: str) -> MiniMaxAnalysis:
    """Analyze a video using MiniMax Motion Coach chat backend."""
    missing = _validate_settings()
    if missing:
        raise RuntimeError("MiniMax configuration incomplete: {}".format(", ".join(missing)))

    timeout_s = max(30, int(settings.minimax_timeout_s or 180))
    max_effective_timeout_s = max(
        timeout_s,
        int(getattr(settings, "minimax_max_effective_timeout_s", 300) or 300),
    )
    poll_interval = max(0.8, float(settings.minimax_poll_interval_s or 2.0))

    video_hash = _md5_file(Path(video_path))
    prepared = _prepare_video_for_minimax(video_path)
    # Long/heavy videos can require significantly longer async processing on MiniMax.
    base_duration_s = max(
        float(prepared.prepared_duration_s or 0.0),
        float(prepared.source_duration_s or 0.0),
    )
    adaptive_timeout_s = int(180 + (base_duration_s * 5.0))
    timeout_s_effective = max(timeout_s, min(max_effective_timeout_s, adaptive_timeout_s))
    analysis: MiniMaxAnalysis | None = None
    prompt_variants = [
        ("primary", _compose_analysis_prompt(settings.minimax_prompt_template, fallback=False)),
        ("fallback", _compose_analysis_prompt(fallback=True)),
    ]
    prompt_retry_enabled = _as_bool(getattr(settings, "minimax_prompt_retry_enabled", False), False)
    if not prompt_retry_enabled:
        prompt_variants = prompt_variants[:1]

    global_deadline = time.monotonic() + float(timeout_s_effective) + 20.0
    last_exc: Exception | None = None

    try:
        policy_browser_only = _browser_only_enabled()
        if not policy_browser_only:
            logger.warning("MINIMAX_BROWSER_ONLY=false ignored by policy: forcing browser UI transport.")
        for attempt_index, (variant_name, prompt) in enumerate(prompt_variants, start=1):
            prompt_hash = _md5_text(
                "{}|{}|{}|clip:{}|preserve_full:{}|optimize:{}".format(
                    prompt,
                    int(getattr(settings, "minimax_model_option", 0) or 0),
                    "v11_minimax_preserve_source_quality",
                    int(getattr(settings, "minimax_max_clip_s", 240) or 240),
                    int(getattr(settings, "minimax_preserve_full_video_up_to_s", 480) or 480),
                    1 if _as_bool(getattr(settings, "minimax_optimize_video", True), True) else 0,
                )
            )
            cached = _cache_get(video_hash, prompt_hash)
            if cached is not None:
                cached.metadata.update(
                    {
                        "video_hash": video_hash,
                        "prompt_hash": prompt_hash,
                        "cache_hit": True,
                        "prompt_variant": variant_name,
                        "attempt_index": attempt_index,
                    }
                )
                return cached

            try:
                remaining_s = int(max(45, global_deadline - time.monotonic()))
                if remaining_s <= 45:
                    raise TimeoutError("MiniMax global analysis timeout reached")

                analysis = _run_minimax_browser_only_once(
                    prepared=prepared,
                    prompt=prompt,
                    poll_interval=poll_interval,
                    timeout_s_effective=remaining_s,
                    video_hash=video_hash,
                    prompt_hash=prompt_hash,
                )
            except Exception as exc:
                last_exc = exc
                retryable = _should_retry_browser_analysis(exc)
                can_try_fallback_once = (not prompt_retry_enabled) and attempt_index == 1 and retryable
                if can_try_fallback_once and len(prompt_variants) < 2:
                    prompt_variants.append(("fallback", _compose_analysis_prompt(fallback=True)))
                if attempt_index < len(prompt_variants) and retryable:
                    logger.warning(
                        "MiniMax browser analysis retrying with %s prompt after semantic failure: %s",
                        prompt_variants[attempt_index][0],
                        exc,
                    )
                    continue
                raise

            analysis.metadata.update(
                {
                    "policy_forced_browser_only": bool(not policy_browser_only),
                    "prompt_variant": variant_name,
                    "attempt_index": attempt_index,
                }
            )

            if analysis is None:
                raise RuntimeError("MiniMax analysis unavailable (unknown error)")

            _cache_put(video_hash, prompt_hash, analysis)
            return analysis

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("MiniMax analysis unavailable (all attempts failed)")
    finally:
        if prepared.temporary:
            try:
                Path(prepared.path).unlink(missing_ok=True)
            except Exception:
                pass
