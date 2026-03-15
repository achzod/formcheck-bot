from __future__ import annotations

import asyncio
import logging
import os
import shutil
import socket
import sys
import tempfile
from pathlib import Path
from typing import Any

import httpx

import analysis.minimax_motion_coach as minimax_motion_coach
from analysis.minimax_motion_coach import _analysis_to_payload, run_minimax_motion_coach

logger = logging.getLogger("formcheck.minimax_remote_worker")

_JOB_BROWSER_SETTING_TYPES: dict[str, type] = {
    "minimax_browser_email": str,
    "minimax_browser_password": str,
    "minimax_cookie": str,
    "minimax_browser_local_storage_json": str,
    "minimax_browser_session_storage_json": str,
    "minimax_motion_coach_expert_url": str,
    "minimax_prompt_template": str,
    "minimax_browser_timeout_s": int,
    "minimax_timeout_s": int,
    "minimax_poll_interval_s": float,
    "minimax_browser_only": bool,
    "minimax_browser_headless": bool,
}
_SETTING_TO_ENV: dict[str, str] = {
    "minimax_browser_email": "MINIMAX_BROWSER_EMAIL",
    "minimax_browser_password": "MINIMAX_BROWSER_PASSWORD",
    "minimax_cookie": "MINIMAX_COOKIE",
    "minimax_browser_local_storage_json": "MINIMAX_BROWSER_LOCAL_STORAGE_JSON",
    "minimax_browser_session_storage_json": "MINIMAX_BROWSER_SESSION_STORAGE_JSON",
    "minimax_motion_coach_expert_url": "MINIMAX_MOTION_COACH_EXPERT_URL",
    "minimax_prompt_template": "MINIMAX_PROMPT_TEMPLATE",
    "minimax_browser_timeout_s": "MINIMAX_BROWSER_TIMEOUT_S",
    "minimax_timeout_s": "MINIMAX_TIMEOUT_S",
    "minimax_poll_interval_s": "MINIMAX_POLL_INTERVAL_S",
    "minimax_browser_only": "MINIMAX_BROWSER_ONLY",
    "minimax_browser_headless": "MINIMAX_BROWSER_HEADLESS",
}
_RUNTIME_SETTING_KEYS: tuple[str, ...] = tuple(
    dict.fromkeys(
        tuple(_SETTING_TO_ENV.keys())
        + (
            "minimax_browser_channel",
        )
    ).keys()
)
_RUNTIME_ENV_KEYS: tuple[str, ...] = tuple(
    dict.fromkeys(
        tuple(_SETTING_TO_ENV.values())
        + (
            "MINIMAX_BROWSER_CHANNEL",
        )
    ).keys()
)


def _base_url() -> str:
    return str(
        os.getenv("FORMCHECK_BASE_URL")
        or os.getenv("BASE_URL")
        or "https://formcheck-bot.onrender.com"
    ).rstrip("/")


def _token() -> str:
    return str(
        os.getenv("MINIMAX_REMOTE_WORKER_TOKEN")
        or os.getenv("FORMCHECK_INTERNAL_TOKEN")
        or os.getenv("RENDER_API_KEY")
        or ""
    ).strip()


def _poll_interval_s() -> float:
    try:
        return max(2.0, float(os.getenv("MINIMAX_REMOTE_WORKER_POLL_INTERVAL_S", "5")))
    except Exception:
        return 5.0


def _worker_id() -> str:
    raw = str(os.getenv("MINIMAX_REMOTE_WORKER_ID", "") or "").strip()
    if raw:
        return raw[:120]
    return "{}-{}".format(socket.gethostname(), os.getpid())[:120]


def _headers() -> dict[str, str]:
    token = _token()
    if not token:
        raise RuntimeError(
            "Missing MINIMAX_REMOTE_WORKER_TOKEN or FORMCHECK_INTERNAL_TOKEN or RENDER_API_KEY"
        )
    return {"X-Formcheck-Internal-Token": token}


def _maybe_reexec_under_xvfb() -> None:
    """Ensure headed Playwright runs with an X server even if Render bypasses CMD.

    Render workers should normally start through `xvfb-run` via the Docker
    entrypoint. In practice, some worker runtimes end up invoking
    `python -m app.minimax_remote_worker` directly, leaving `DISPLAY` unset.
    When that happens, Playwright headed Chromium crashes before MiniMax sees
    the video. Re-exec the current process under `xvfb-run` so the worker can
    self-heal from runtime command drift.
    """

    headless = _as_bool(os.getenv("MINIMAX_BROWSER_HEADLESS", "true"))
    if headless:
        return

    display = str(os.getenv("DISPLAY", "") or "").strip()
    if display:
        return

    if _as_bool(os.getenv("FORMCHECK_XVFB_REEXEC", "false")):
        raise RuntimeError(
            "DISPLAY is still missing after xvfb re-exec; headed MiniMax worker cannot start"
        )

    xvfb_run = shutil.which("xvfb-run")
    if not xvfb_run:
        raise RuntimeError(
            "xvfb-run is not installed while headed MiniMax worker requires a virtual display"
        )

    cmd = [
        xvfb_run,
        "-a",
        "-s",
        "-screen 0 1920x1080x24",
        sys.executable,
        "-m",
        "app.minimax_remote_worker",
    ]
    env = os.environ.copy()
    env["FORMCHECK_XVFB_REEXEC"] = "true"
    logger.warning(
        "DISPLAY missing for headed MiniMax worker; re-executing under xvfb-run"
    )
    os.execvpe(xvfb_run, cmd, env)


def _as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _cast_setting_value(value: Any, expected_type: type) -> Any:
    if expected_type is bool:
        return _as_bool(value)
    if expected_type is int:
        try:
            return int(float(value))
        except Exception:
            return 0
    if expected_type is float:
        try:
            return float(value)
        except Exception:
            return 0.0
    return str(value or "")


def _to_env_value(value: Any, expected_type: type) -> str:
    if expected_type is bool:
        return "true" if bool(value) else "false"
    if expected_type is int:
        return str(int(value))
    if expected_type is float:
        return str(float(value))
    return str(value or "")


def _apply_job_browser_context(job: dict) -> dict[str, Any]:
    context = job.get("browser_context")
    if not isinstance(context, dict):
        return {}

    applied: dict[str, Any] = {}
    for key, expected_type in _JOB_BROWSER_SETTING_TYPES.items():
        if key not in context:
            continue
        raw_value = context.get(key)
        if raw_value is None:
            continue
        casted = _cast_setting_value(raw_value, expected_type)
        applied[key] = casted
        env_name = _SETTING_TO_ENV.get(key)
        if env_name:
            os.environ[env_name] = _to_env_value(casted, expected_type)
        try:
            setattr(minimax_motion_coach.settings, key, casted)
        except Exception:
            logger.warning("Failed to override runtime setting %s", key, exc_info=True)
    return applied


def _capture_runtime_browser_context() -> dict[str, dict[str, Any]]:
    runtime_settings = minimax_motion_coach.settings
    return {
        "env": {name: os.environ.get(name) for name in _RUNTIME_ENV_KEYS},
        "settings": {
            key: getattr(runtime_settings, key, None)
            for key in _RUNTIME_SETTING_KEYS
        },
    }


def _restore_runtime_browser_context(snapshot: dict[str, dict[str, Any]]) -> None:
    env_snapshot = snapshot.get("env", {}) if isinstance(snapshot, dict) else {}
    settings_snapshot = snapshot.get("settings", {}) if isinstance(snapshot, dict) else {}

    for name in _RUNTIME_ENV_KEYS:
        value = env_snapshot.get(name)
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = str(value)

    runtime_settings = minimax_motion_coach.settings
    for key in _RUNTIME_SETTING_KEYS:
        if key in settings_snapshot:
            setattr(runtime_settings, key, settings_snapshot.get(key))


async def _claim_job(client: httpx.AsyncClient, worker_id: str) -> dict | None:
    response = await client.post(
        _base_url() + "/internal/minimax/jobs/claim",
        headers=_headers(),
        json={"worker_id": worker_id},
    )
    response.raise_for_status()
    payload = response.json()
    job = payload.get("job")
    return job if isinstance(job, dict) else None


async def _download_video(client: httpx.AsyncClient, job_id: int, video_url: str) -> Path:
    response = await client.get(video_url, headers=_headers())
    response.raise_for_status()
    suffix = Path(video_url).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(prefix="formcheck-minimax-", suffix=suffix, delete=False) as handle:
        handle.write(response.content)
        return Path(handle.name)


async def _complete_job(client: httpx.AsyncClient, job_id: int, analysis_payload: str) -> None:
    response = await client.post(
        _base_url() + "/internal/minimax/jobs/{}/complete".format(job_id),
        headers=_headers(),
        json={"analysis_payload": analysis_payload},
    )
    response.raise_for_status()


async def _fail_job(client: httpx.AsyncClient, job_id: int, error: str) -> None:
    response = await client.post(
        _base_url() + "/internal/minimax/jobs/{}/fail".format(job_id),
        headers=_headers(),
        json={"error": error[:2000]},
    )
    response.raise_for_status()


async def _process_job(client: httpx.AsyncClient, job: dict) -> None:
    job_id = int(job["id"])
    video_url = str(job["video_url"])
    video_path: Path | None = None
    try:
        applied_context = _apply_job_browser_context(job)
        if applied_context:
            logger.info(
                "MiniMax remote job runtime context applied (job_id=%s keys=%s)",
                job_id,
                ",".join(sorted(applied_context.keys())),
            )
        video_path = await _download_video(client, job_id, video_url)
        analysis = await asyncio.to_thread(run_minimax_motion_coach, str(video_path))
        logger.info(
            "MiniMax remote job analysis summary (job_id=%s exercise_slug=%s exercise_display=%s score=%s reps_total=%s intensity_score=%s)",
            job_id,
            getattr(analysis, "exercise_slug", ""),
            getattr(analysis, "exercise_display", ""),
            getattr(analysis, "score", 0),
            getattr(analysis, "reps_total", 0),
            getattr(analysis, "intensity_score", 0),
        )
        await _complete_job(client, job_id, _analysis_to_payload(analysis))
        logger.info("MiniMax remote job completed (job_id=%s)", job_id)
    except Exception as exc:
        logger.exception("MiniMax remote job failed (job_id=%s)", job_id)
        try:
            await _fail_job(client, job_id, str(exc))
        except Exception:
            logger.exception("Failed to report remote worker error (job_id=%s)", job_id)
    finally:
        if video_path is not None:
            try:
                video_path.unlink(missing_ok=True)
            except Exception:
                pass


async def run_worker() -> None:
    os.environ["MINIMAX_BROWSER_ONLY"] = "true"
    # MiniMax/Cloudflare blocks AI Motion Coach reliably in headless mode.
    # Keep browser headed; Render worker should run through xvfb-run.
    os.environ["MINIMAX_BROWSER_HEADLESS"] = "false"
    # Do not force a specific browser channel here:
    # - local machines can set MINIMAX_BROWSER_CHANNEL=chrome
    # - Render workers can rely on bundled Chromium (empty channel)
    channel = str(os.getenv("MINIMAX_BROWSER_CHANNEL", "") or "").strip()
    os.environ["MINIMAX_BROWSER_CHANNEL"] = channel
    minimax_motion_coach.settings.minimax_browser_only = True
    minimax_motion_coach.settings.minimax_browser_headless = False
    minimax_motion_coach.settings.minimax_browser_channel = channel
    _maybe_reexec_under_xvfb()

    worker_id = _worker_id()
    poll_s = _poll_interval_s()
    timeout = httpx.Timeout(120.0, connect=20.0)
    base_runtime_context = _capture_runtime_browser_context()

    logger.info(
        "MiniMax remote worker bootstrap (worker_id=%s headless=%s channel=%s base_url=%s)",
        worker_id,
        os.getenv("MINIMAX_BROWSER_HEADLESS", ""),
        channel,
        _base_url(),
    )

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        while True:
            try:
                job = await _claim_job(client, worker_id)
                if not job:
                    await asyncio.sleep(poll_s)
                    continue
                try:
                    await _process_job(client, job)
                finally:
                    _restore_runtime_browser_context(base_runtime_context)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("MiniMax remote worker loop failed")
                await asyncio.sleep(poll_s)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
