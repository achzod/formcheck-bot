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
import time
import uuid
from dataclasses import dataclass, field
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
    "Schema JSON:\n"
    "{\n"
    '  "exercise": {"name": "snake_case", "display_name_fr": "string", "confidence": 0.0},\n'
    '  "score": 0,\n'
    '  "reps": {"total": 0, "complete": 0, "partial": 0},\n'
    '  "intensity": {"score": 0, "label": "tres elevee|elevee|moderee|faible|tres faible", "avg_inter_rep_rest_s": 0.0},\n'
    '  "score_breakdown": {"Securite": 0, "Efficacite technique": 0, "Controle et tempo": 0, "Symetrie": 0},\n'
    '  "positives": ["string"],\n'
    '  "corrections": [{"title": "string", "why": "string", "cue": "string"}],\n'
    '  "report_markdown": "rapport complet en francais, style coach, precis"\n'
    "}\n"
    "Contraintes: score sur 100, reps strictement comptees, intensite inclut le repos moyen inter-reps."
)

_INTENSITY_LABELS = (
    ("tres elevee", 85),
    ("elevee", 70),
    ("moderee", 55),
    ("faible", 40),
    ("tres faible", 0),
)


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
            minimax_use_cloudscraper = _as_bool(os.getenv("MINIMAX_USE_CLOUDSCRAPER"), True)
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
    score_breakdown: dict[str, int] = field(default_factory=dict)
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
        if isinstance(score_breakdown, dict):
            analysis.score_breakdown = {
                str(k): _clamp_int(v)
                for k, v in score_breakdown.items()
            }

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

        report_text = str(
            payload.get("report_markdown")
            or payload.get("report_text")
            or payload.get("summary")
            or raw_text
        ).strip()
        analysis.report_text = report_text or raw_text

        if analysis.intensity_label == "indeterminee" and analysis.intensity_score > 0:
            analysis.intensity_label = _intensity_label_from_score(analysis.intensity_score)

        if analysis.reps_total <= 0:
            analysis.reps_total = _extract_reps_from_text(raw_text)
        if analysis.score <= 0:
            analysis.score = _extract_score_from_text(raw_text)
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
    analysis.report_text = raw_text
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

        asset = client.upload_video(video_path)
        send_resp = client.send_video_message(
            chat_id=chat_id,
            prompt=prompt,
            asset=asset,
            origin_file_name=Path(video_path).name,
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
            }
        )
        if not analysis.report_text:
            analysis.report_text = best_text
        return analysis
    finally:
        client.close()
