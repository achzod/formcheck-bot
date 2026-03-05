"""MiniMax Motion Coach integration (video upload + chat analysis).

This module calls MiniMax web APIs directly:
- uploads a local video file to OSS using temporary STS credentials
- sends a chat message with the uploaded video attachment
- polls chat detail until an agent response is available
- parses structured JSON (preferred) or falls back to regex extraction
"""

from __future__ import annotations

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
from urllib.parse import quote, urlencode

import httpx

logger = logging.getLogger("formcheck.minimax")

_SIGNING_SECRET = "I*7Cf%WZ#S&%1RlZJ&C2"
_YY_SUFFIX = "ooui"
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)
_DEFAULT_ANALYSIS_PROMPT = (
    "Tu es un coach biomecanique expert.\n"
    "Analyse la video envoyee et reponds UNIQUEMENT en JSON valide (sans markdown).\n"
    "Tu t'adresses DIRECTEMENT au client, en francais, ton coach pro, concret et actionnable.\n"
    "Schema JSON strict:\n"
    "{\n"
    '  "exercise": {"name": "snake_case", "display_name_fr": "string", "confidence": 0.0},\n'
    '  "score": 0,\n'
    '  "reps": {"total": 0, "complete": 0, "partial": 0},\n'
    '  "intensity": {"score": 0, "label": "tres elevee|elevee|moderee|faible|tres faible", "avg_inter_rep_rest_s": 0.0},\n'
    '  "score_breakdown": {"Securite": 0, "Efficacite technique": 0, "Controle et tempo": 0, "Symetrie": 0},\n'
    '  "positives": ["string"],\n'
    '  "corrections": [{"title": "string", "why": "string", "impact": "string", "cue": "string"}],\n'
    '  "corrective_exercises": [{"name": "string", "dosage": "sets x reps", "target": "string", "execution": "string", "timing": "string"}],\n'
    '  "sections": {\n'
    '    "resume": "3-5 phrases directes au client",\n'
    '    "rom": "analyse amplitude / articulation",\n'
    '    "tempo": "analyse controle moteur + phases",\n'
    '    "intensite": "analyse densite serie + repos inter-reps",\n'
    '    "compensations": "compensations detectees + risque",\n'
    '    "biomecanique": "insight biomecanique avance et utile",\n'
    '    "plan_action": ["action 1", "action 2", "action 3"],\n'
    '    "next_video": "recommandation angle camera pour la prochaine video"\n'
    "  },\n"
    '  "report_markdown": "optionnel: rapport long deja sectionne"\n'
    "}\n"
    "Contraintes: score sur 100, reps strictement comptees, intensite inclut le repos moyen inter-reps.\n"
    "Optimisation tokens: sois precis mais concis. Chaque section textuelle: 2 a 4 phrases maximum.\n"
    "Ne renvoie aucune phrase hors JSON."
)

_INTENSITY_LABELS = (
    ("tres elevee", 85),
    ("elevee", 70),
    ("moderee", 55),
    ("faible", 40),
    ("tres faible", 0),
)
_RETRYABLE_HTTP_STATUSES = {403, 408, 409, 425, 429, 500, 502, 503, 504}


def _as_bool(raw: Any, default: bool = False) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


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
            minimax_fallback_to_local = _as_bool(os.getenv("MINIMAX_FALLBACK_TO_LOCAL"), True)
            minimax_use_cloudscraper = _as_bool(os.getenv("MINIMAX_USE_CLOUDSCRAPER"), True)
            minimax_request_max_attempts = int(os.getenv("MINIMAX_REQUEST_MAX_ATTEMPTS", "3"))
            minimax_retry_backoff_s = float(os.getenv("MINIMAX_RETRY_BACKOFF_S", "1.0"))
            minimax_enable_cache = _as_bool(os.getenv("MINIMAX_ENABLE_CACHE"), True)
            minimax_cache_ttl_hours = int(os.getenv("MINIMAX_CACHE_TTL_HOURS", "168"))
            minimax_cache_path = os.getenv("MINIMAX_CACHE_PATH", "media/minimax_cache.sqlite")
            minimax_optimize_video = _as_bool(os.getenv("MINIMAX_OPTIMIZE_VIDEO"), True)
            minimax_max_clip_s = int(os.getenv("MINIMAX_MAX_CLIP_S", "45"))
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
    match = re.search(r"\b(\d{1,3})\s*/\s*100\b", text)
    if not match:
        return 0
    return _clamp_int(match.group(1))


def _extract_reps_from_text(text: str) -> int:
    match = re.search(r"\b(\d{1,3})\s*reps?\b", text, flags=re.IGNORECASE)
    if not match:
        return 0
    return max(0, int(match.group(1)))


def _extract_intensity_from_text(text: str) -> tuple[int, float]:
    score = 0
    rest = 0.0

    score_match = re.search(
        r"intensit[eé]\s*[:\-]?\s*(\d{1,3})\s*/\s*100",
        text,
        flags=re.IGNORECASE,
    )
    if score_match:
        score = _clamp_int(score_match.group(1))

    rest_match = re.search(
        r"repos?\s+(?:moyen|avg|average)?\s*([0-9]+(?:[.,][0-9]+)?)\s*s",
        text,
        flags=re.IGNORECASE,
    )
    if rest_match:
        rest = _coerce_float(rest_match.group(1).replace(",", "."), default=0.0)

    return score, max(0.0, rest)


def _extract_exercise_from_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "Exercice non identifie"

    first = lines[0]
    # Remove leading label patterns.
    first = re.sub(r"^FORMCHECK\s*[-:]\s*", "", first, flags=re.IGNORECASE)
    if "—" in first:
        first = first.split("—", 1)[0].strip()
    return first or "Exercice non identifie"


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
        return _estimate_score_breakdown(total_score) if total_score > 0 else {}

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
                str(key)
                .strip()
                .lower()
                .replace("é", "e")
                .replace("è", "e")
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

    if matched == 0 and total_score > 0:
        return _estimate_score_breakdown(total_score)
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
    if not breakdown and analysis.score > 0:
        breakdown = _estimate_score_breakdown(analysis.score)

    resume_text = analysis.sections.get("resume", "").strip()
    if not resume_text:
        base = (
            "Tu as realise une serie de {} avec un score global de {}/100."
            .format(exercise_display, max(0, int(analysis.score or 0)))
        )
        if reps_total > 0:
            base += " {} repetitions detectees.".format(reps_total)
        if intensity_score > 0:
            base += " Intensite {} /100 ({})".format(intensity_score, intensity_label)
            if rest_s > 0:
                base += ", repos moyen {:.2f}s.".format(rest_s)
            else:
                base += "."
        resume_text = base

    positives = [item.strip() for item in analysis.positives if item and item.strip()]
    if not positives:
        positives = [
            "Ta base technique est exploitable pour progresser proprement.",
            "Le mouvement reste lisible sur l'ensemble de la serie, ce qui permet un travail corrigeable rapidement.",
        ]

    corrections = analysis.corrections[:4]
    if not corrections:
        corrections = [
            {
                "title": "Controle de trajectoire",
                "issue": "La trajectoire manque de regularite sur certaines repetitions.",
                "impact": (
                    "Une trajectoire variable decharge le muscle cible et augmente la compensation "
                    "sur les structures passives."
                ),
                "fix": "Cue: garde la meme ligne de mouvement sur chaque rep, sans acceleration parasite.",
            },
            {
                "title": "Gestion du tempo",
                "issue": "Le rythme n'est pas totalement constant entre les reps.",
                "impact": (
                    "Une execution trop acceleree reduit le temps sous tension utile "
                    "et degrade la qualite mecanique en fin de serie."
                ),
                "fix": "Cue: ralentis l'excentrique et marque un mini controle avant de repartir.",
            },
        ]

    rom_text = analysis.sections.get("rom", "").strip()
    if not rom_text:
        if reps_total > 0:
            rom_text = (
                "Amplitude exploitable sur la serie analysee. L'objectif est de garder cette amplitude "
                "constante sur toutes les repetitions, surtout sur les dernieres reps."
            )
        else:
            rom_text = "Donnees d'amplitude insuffisantes pour conclure proprement sur cette video."

    tempo_text = analysis.sections.get("tempo", "").strip()
    if not tempo_text:
        tempo_text = (
            "Le controle moteur est globalement present, mais il faut homogeniser le rythme "
            "entre le debut et la fin de serie pour maximiser le stimulus."
        )

    intensite_text = analysis.sections.get("intensite", "").strip()
    if not intensite_text:
        if intensity_score > 0:
            intensite_text = (
                "Intensite de serie estimee a {}/100 ({}) avec un repos moyen inter-reps de {:.2f}s."
                .format(intensity_score, intensity_label, rest_s)
            )
        else:
            intensite_text = "Intensite non estimable de facon robuste sur cette video."

    compensations_text = analysis.sections.get("compensations", "").strip()
    if not compensations_text:
        compensations_text = (
            "Compensations principales a surveiller: perte d'alignement en fin de rep "
            "et stabilisation moins propre quand la fatigue monte."
        )

    biomech_text = analysis.sections.get("biomecanique", "").strip()
    if not biomech_text:
        biomech_text = (
            "Le levier et la stabilisation articulaire doivent rester prioritaires: "
            "quand la vitesse augmente sans controle, le muscle cible travaille moins "
            "et la contrainte bascule vers les articulations."
        )

    plan_actions = [item.strip() for item in analysis.plan_action if item and item.strip()]
    if not plan_actions:
        plan_actions = [
            "Sur la prochaine serie, garde la meme amplitude sur toutes les reps.",
            "Controle la phase excentrique pour eviter le rebond ou le momentum.",
            "Filme une serie a charge identique avec un angle plus stable pour comparer.",
        ]

    next_video = analysis.sections.get("next_video", "").strip()
    if not next_video:
        next_video = (
            "Filme de profil a hauteur de hanche, camera fixe a 2-3 metres, "
            "avec tout le corps visible du debut a la fin."
        )

    lines: list[str] = []
    lines.append("ANALYSE BIOMECANIQUE — {}".format(exercise_display))
    if analysis.score > 0:
        lines.append("Score : {}/100".format(analysis.score))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("RESUME")
    lines.append(resume_text)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("POINTS POSITIFS")
    for idx, item in enumerate(positives[:4], start=1):
        lines.append("{}. {}".format(idx, item))

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("AMPLITUDE DE MOUVEMENT")
    lines.append(rom_text)

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("CORRECTIONS PRIORITAIRES")
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

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("ANALYSE DU TEMPO ET DES PHASES")
    lines.append(tempo_text)

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("INTENSITE DE SERIE (DENSITE)")
    lines.append(intensite_text)
    if reps_total > 0:
        lines.append(
            "Repetitions detectees: {} ({} completes, {} partielles)."
            .format(reps_total, reps_complete, reps_partial)
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("COMPENSATIONS ET BIOMECANIQUE AVANCEE")
    lines.append(compensations_text)

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
        lines.append("Justification: score etabli selon la qualite d'execution observee sur la video.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("POINT BIOMECANIQUE")
    lines.append(biomech_text)

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("RECOMMANDATION POUR LA PROCHAINE VIDEO")
    lines.append(next_video)

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("PLAN D'ACTION")
    for idx, action in enumerate(plan_actions[:4], start=1):
        lines.append("{}. {}".format(idx, action))

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

    max_clip_s = max(8, int(getattr(settings, "minimax_max_clip_s", 45) or 45))
    target_height = max(360, int(getattr(settings, "minimax_target_height", 720) or 720))
    target_fps = max(12, int(getattr(settings, "minimax_target_fps", 24) or 24))
    target_bitrate = max(700, int(getattr(settings, "minimax_target_video_bitrate_kbps", 1400) or 1400))
    keep_audio = _as_bool(getattr(settings, "minimax_keep_audio", False), False)

    need_duration_opt = src_duration > (max_clip_s + 2)
    need_resolution_opt = src_height > (target_height + 2)
    need_fps_opt = src_fps > (target_fps + 1)
    need_size_opt = src_size > (10 * 1024 * 1024)
    if not any((need_duration_opt, need_resolution_opt, need_fps_opt, need_size_opt)):
        return prepared

    start_s = 0.0
    end_s = src_duration if src_duration > 0 else 0.0
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
        "-ss",
        "{:.3f}".format(start_s),
        "-i",
        str(src),
        "-t",
        "{:.3f}".format(window_duration),
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
        prepared.strategy = "trim_transcode"
        return prepared
    except Exception as exc:
        logger.warning("MiniMax preprocess exception, using original: %s", exc)
        return prepared


def _parse_analysis_payload(text: str) -> MiniMaxAnalysis:
    payload = _extract_json_object(text)
    raw_text = (text or "").strip()
    analysis = MiniMaxAnalysis(raw_response=raw_text)

    if payload:
        exercise = payload.get("exercise", {})
        if isinstance(exercise, dict):
            exercise_name = str(exercise.get("name", "") or "")
            exercise_display = str(exercise.get("display_name_fr", "") or "")
            analysis.exercise_slug = _slugify(exercise_name or exercise_display)
            analysis.exercise_display = exercise_display or exercise_name.replace("_", " ").title() or analysis.exercise_display
            analysis.exercise_confidence = max(0.0, min(1.0, _coerce_float(exercise.get("confidence", 0.0))))
        else:
            exercise_text = str(exercise or "")
            analysis.exercise_slug = _slugify(exercise_text)
            analysis.exercise_display = exercise_text or analysis.exercise_display

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
        else:
            analysis.report_text = _build_structured_report_text(analysis)

        if analysis.intensity_label == "indeterminee" and analysis.intensity_score > 0:
            analysis.intensity_label = _intensity_label_from_score(analysis.intensity_score)

        if analysis.reps_total <= 0:
            analysis.reps_total = _extract_reps_from_text(raw_text)
        if analysis.score <= 0:
            analysis.score = _extract_score_from_text(raw_text)
        if not analysis.report_text:
            analysis.report_text = _build_structured_report_text(analysis)
        return analysis

    # Regex fallback for non-JSON answers.
    analysis.exercise_display = _extract_exercise_from_text(raw_text)
    analysis.exercise_slug = _slugify(analysis.exercise_display)
    analysis.score = _extract_score_from_text(raw_text)
    analysis.reps_total = _extract_reps_from_text(raw_text)
    intensity_score, avg_rest = _extract_intensity_from_text(raw_text)
    analysis.intensity_score = intensity_score
    analysis.intensity_label = _intensity_label_from_score(intensity_score)
    analysis.avg_inter_rep_rest_s = avg_rest
    analysis.sections = {}
    analysis.plan_action = []
    analysis.report_text = _build_structured_report_text(analysis)
    if raw_text:
        analysis.raw_response = raw_text
    return analysis


def _iter_dicts(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for val in obj.values():
            yield from _iter_dicts(val)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_dicts(item)


def _extract_message_text(msg: dict[str, Any]) -> str:
    for key in ("msg_content", "content", "text", "answer"):
        value = msg.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            nested = value.get("text") or value.get("content") or value.get("answer")
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return ""


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
        if msg_type not in (2, 10):
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
                        httpx_response.raise_for_status()
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
                    httpx_response.raise_for_status()
                    response_obj = httpx_response

                data = response_obj.json()
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


def _validate_settings() -> list[str]:
    missing: list[str] = []
    required = {
        "minimax_token": settings.minimax_token,
        "minimax_user_id": settings.minimax_user_id,
        "minimax_device_id": settings.minimax_device_id,
        "minimax_chat_id": settings.minimax_chat_id,
    }
    for key, value in required.items():
        if not str(value or "").strip():
            missing.append(key)
    return missing


def run_minimax_motion_coach(video_path: str) -> MiniMaxAnalysis:
    """Analyze a video using MiniMax Motion Coach chat backend."""
    missing = _validate_settings()
    if missing:
        raise RuntimeError("MiniMax configuration incomplete: {}".format(", ".join(missing)))

    timeout_s = max(30, int(settings.minimax_timeout_s or 180))
    poll_interval = max(0.8, float(settings.minimax_poll_interval_s or 2.0))

    prompt = (settings.minimax_prompt_template or _DEFAULT_ANALYSIS_PROMPT).strip()
    video_hash = _md5_file(Path(video_path))
    prompt_hash = _md5_text(
        "{}|{}|{}".format(
            prompt,
            int(getattr(settings, "minimax_model_option", 0) or 0),
            "v2",
        )
    )
    cached = _cache_get(video_hash, prompt_hash)
    if cached is not None:
        cached.metadata.update(
            {
                "video_hash": video_hash,
                "prompt_hash": prompt_hash,
                "cache_hit": True,
            }
        )
        return cached

    prepared = _prepare_video_for_minimax(video_path)
    client = _MiniMaxClient(timeout_s=timeout_s)
    start = time.monotonic()

    try:
        chat_id = str(settings.minimax_chat_id)
        baseline_ids: set[str] = set()
        try:
            baseline = client.get_chat_detail(chat_id)
            _, baseline_ids, _ = _extract_agent_message(baseline, known_message_ids=set())
        except Exception as exc:
            logger.warning("MiniMax baseline get_chat_detail failed (continuing): %s", exc)

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
        deadline = time.monotonic() + timeout_s

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

                # chat_status 1 = generating; any other status generally means terminal.
                if chat_status != 1 or stable_rounds >= 2:
                    break
            time.sleep(poll_interval)

        if not best_text:
            raise TimeoutError("MiniMax response timeout (no assistant message)")

        analysis = _parse_analysis_payload(best_text)
        elapsed = time.monotonic() - start
        analysis.metadata.update(
            {
                "chat_id": sent_chat_id,
                "file_id": asset.file_id,
                "file_url": asset.file_url,
                "object_key": asset.object_key,
                "elapsed_s": round(elapsed, 2),
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
        _cache_put(video_hash, prompt_hash, analysis)
        return analysis
    finally:
        if prepared.temporary:
            try:
                Path(prepared.path).unlink(missing_ok=True)
            except Exception:
                pass
        client.close()
