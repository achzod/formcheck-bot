from __future__ import annotations

import atexit
import asyncio
import logging
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

import analysis.minimax_motion_coach as minimax_motion_coach

logger = logging.getLogger("formcheck.minimax_remote_worker")
_XVFB_PROCESS: subprocess.Popen[str] | None = None

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
    "minimax_max_effective_timeout_s": int,
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
    "minimax_max_effective_timeout_s": "MINIMAX_MAX_EFFECTIVE_TIMEOUT_S",
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


def _download_chunk_size_bytes() -> int:
    try:
        raw_mb = float(os.getenv("MINIMAX_REMOTE_VIDEO_DOWNLOAD_CHUNK_MB", "2") or 2.0)
    except Exception:
        raw_mb = 2.0
    return max(256 * 1024, int(raw_mb * 1024 * 1024))


def _download_max_bytes() -> int:
    try:
        raw_mb = float(os.getenv("MINIMAX_REMOTE_VIDEO_MAX_MB", "512") or 512.0)
    except Exception:
        raw_mb = 512.0
    # Keep a safe lower bound while allowing long/heavy clips when configured.
    return max(32 * 1024 * 1024, int(raw_mb * 1024 * 1024))


def _download_timeout_s() -> float:
    try:
        return max(120.0, float(os.getenv("MINIMAX_REMOTE_VIDEO_DOWNLOAD_TIMEOUT_S", "900") or 900.0))
    except Exception:
        return 900.0


def _orphan_cleanup_interval_s() -> float:
    try:
        return max(10.0, float(os.getenv("MINIMAX_REMOTE_ORPHAN_CLEANUP_INTERVAL_S", "90") or 90.0))
    except Exception:
        return 90.0


def _is_browser_cmdline(cmdline: str) -> bool:
    low = str(cmdline or "").strip().lower()
    if not low:
        return False
    markers = (
        "ms-playwright/chromium",
        "chrome-linux64/chrome",
        "playwright/driver/node",
        "chrome_crashpad_handler",
        "/chromium ",
        "/chromium --",
        "/chrome ",
        "/chrome --",
    )
    return any(marker in low for marker in markers)


def _kill_orphan_browser_processes() -> int:
    """Best-effort cleanup of stale browser processes left by crashed runs."""
    current_pid = os.getpid()
    killed = 0
    try:
        proc_entries = [entry for entry in os.listdir("/proc") if entry.isdigit()]
    except Exception:
        return 0

    for entry in proc_entries:
        pid = int(entry)
        if pid == current_pid:
            continue
        cmdline = ""
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as handle:
                cmdline = handle.read().replace(b"\x00", b" ").decode("utf-8", "ignore").strip()
        except Exception:
            continue
        if not _is_browser_cmdline(cmdline):
            continue
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
        except PermissionError:
            continue
        except Exception:
            continue
        time.sleep(0.05)
        still_alive = True
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            still_alive = False
        except Exception:
            still_alive = True
        if still_alive:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except Exception:
                continue
        killed += 1
    return killed


def _worker_id() -> str:
    raw = str(os.getenv("MINIMAX_REMOTE_WORKER_ID", "") or "").strip()
    if raw and raw.lower() not in {"auto", "render-auto"}:
        return raw[:120]
    return "{}-{}".format(socket.gethostname(), os.getpid())[:120]


def _analysis_subprocess_timeout_s() -> int:
    max_effective = max(
        60,
        int(getattr(minimax_motion_coach.settings, "minimax_max_effective_timeout_s", 900) or 900),
    )
    grace_s = max(30, int(os.getenv("MINIMAX_REMOTE_JOB_TIMEOUT_GRACE_S", "120") or 120))
    hard_cap_s = max(120, int(os.getenv("MINIMAX_REMOTE_JOB_MAX_TIMEOUT_S", "1200") or 1200))
    return min(max_effective + grace_s, hard_cap_s)


def _analysis_browser_stall_after_s() -> int:
    return max(30, int(os.getenv("MINIMAX_REMOTE_BROWSER_STALL_AFTER_S", "45") or 45))


def _job_heartbeat_interval_s() -> float:
    try:
        return max(10.0, float(os.getenv("MINIMAX_REMOTE_JOB_HEARTBEAT_INTERVAL_S", "30") or 30))
    except Exception:
        return 30.0


def _analysis_subprocess_should_abort_early(
    *,
    elapsed_s: float,
    result_size_bytes: int,
    browser_alive: bool,
    browser_seen: bool,
    idle_without_browser_s: float,
    stall_after_s: float,
) -> bool:
    if result_size_bytes > 0:
        return False
    if browser_alive:
        return False
    if elapsed_s < stall_after_s:
        return False
    if not browser_seen:
        return True
    return idle_without_browser_s >= stall_after_s


def _headers() -> dict[str, str]:
    token = _token()
    if not token:
        raise RuntimeError(
            "Missing MINIMAX_REMOTE_WORKER_TOKEN or FORMCHECK_INTERNAL_TOKEN or RENDER_API_KEY"
        )
    return {"X-Formcheck-Internal-Token": token}


def _stop_xvfb() -> None:
    global _XVFB_PROCESS
    proc = _XVFB_PROCESS
    _XVFB_PROCESS = None
    if proc is None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _ensure_display_for_headed_browser() -> None:
    """Start Xvfb in-process when headed Playwright has no DISPLAY.

    Render currently runs the worker with a plain docker command, so relying on
    an outer `xvfb-run` wrapper is brittle: the wrapper can stay alive while the
    actual Python worker dies, leaving the service marked live but no queue
    consumer running. Starting Xvfb from the worker process keeps the lifetime
    coupled to the real Python loop.
    """

    headless = _as_bool(os.getenv("MINIMAX_BROWSER_HEADLESS", "true"))
    if headless:
        return

    display = str(os.getenv("DISPLAY", "") or "").strip()
    if display:
        return

    global _XVFB_PROCESS
    if _XVFB_PROCESS is not None and _XVFB_PROCESS.poll() is None:
        os.environ["DISPLAY"] = str(os.getenv("DISPLAY") or ":99")
        return

    xvfb_bin = shutil.which("Xvfb")
    if not xvfb_bin:
        raise RuntimeError(
            "Xvfb is not installed while headed MiniMax worker requires a virtual display"
        )

    last_error = ""
    for display_num in range(99, 111):
        candidate = f":{display_num}"
        proc = subprocess.Popen(
            [
                xvfb_bin,
                candidate,
                "-screen",
                "0",
                "1920x1080x24",
                "-nolisten",
                "tcp",
                "-ac",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.3)
        if proc.poll() is None:
            _XVFB_PROCESS = proc
            os.environ["DISPLAY"] = candidate
            atexit.register(_stop_xvfb)
            logger.warning(
                "DISPLAY missing for headed MiniMax worker; started Xvfb on %s (pid=%s)",
                candidate,
                proc.pid,
            )
            return
        try:
            last_error = (proc.stderr.read() or "").strip()
        except Exception:
            last_error = ""

    raise RuntimeError(
        "Failed to start Xvfb for headed MiniMax worker{}".format(
            f": {last_error}" if last_error else ""
        )
    )


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
    suffix = Path(video_url).suffix or ".mp4"
    max_bytes = _download_max_bytes()
    chunk_size = _download_chunk_size_bytes()
    timeout_s = _download_timeout_s()
    tmp_path: Path | None = None

    try:
        async with client.stream(
            "GET",
            video_url,
            headers=_headers(),
            timeout=timeout_s,
        ) as response:
            response.raise_for_status()
            content_length_raw = str(response.headers.get("content-length", "") or "").strip()
            if content_length_raw.isdigit() and int(content_length_raw) > max_bytes:
                raise RuntimeError(
                    "MiniMax remote video too large ({} bytes > {} bytes cap)".format(
                        int(content_length_raw),
                        max_bytes,
                    )
                )
            with tempfile.NamedTemporaryFile(
                prefix="formcheck-minimax-",
                suffix=suffix,
                delete=False,
            ) as handle:
                tmp_path = Path(handle.name)
                downloaded = 0
                async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        raise RuntimeError(
                            "MiniMax remote video exceeded size cap during download ({} bytes > {} bytes cap)"
                            .format(downloaded, max_bytes)
                        )
                    handle.write(chunk)
        if tmp_path is None:
            raise RuntimeError("MiniMax remote video download failed: no temp file created")
        return tmp_path
    except Exception:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
        raise


def _descendant_cmdlines(root_pid: int) -> list[str]:
    try:
        proc_entries = [entry for entry in os.listdir("/proc") if entry.isdigit()]
    except Exception:
        return []

    parent_by_pid: dict[int, int] = {}
    cmd_by_pid: dict[int, str] = {}
    for entry in proc_entries:
        pid = int(entry)
        try:
            with open(f"/proc/{pid}/stat", encoding="utf-8") as handle:
                parent_by_pid[pid] = int(handle.read().split()[3])
            with open(f"/proc/{pid}/cmdline", "rb") as handle:
                cmd_by_pid[pid] = handle.read().replace(b"\x00", b" ").decode("utf-8", "ignore").strip()
        except Exception:
            continue

    descendants: list[str] = []
    stack = [root_pid]
    seen: set[int] = set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        for pid, parent_pid in parent_by_pid.items():
            if parent_pid != current or pid in seen:
                continue
            stack.append(pid)
            cmd = str(cmd_by_pid.get(pid, "") or "").strip()
            if cmd:
                descendants.append(cmd)
    return descendants


def _subprocess_has_live_browser_descendants(root_pid: int) -> bool:
    for cmd in _descendant_cmdlines(root_pid):
        low = cmd.lower()
        if "chrome_crashpad_handler" in low:
            continue
        if "playwright/driver/node" in low:
            continue
        if (
            "chrome-linux64/chrome" in low
            or "/chrome --" in low
            or "/chrome " in low
            or "ms-playwright/chromium" in low
            or "/chromium --" in low
            or "/chromium " in low
        ):
            return True
    return False


async def _run_analysis_subprocess(video_path: Path) -> str:
    timeout_s = _analysis_subprocess_timeout_s()
    browser_stall_after_s = _analysis_browser_stall_after_s()
    with tempfile.NamedTemporaryFile(
        prefix="formcheck-minimax-result-",
        suffix=".json",
        delete=False,
    ) as handle:
        result_path = Path(handle.name)

    runner = (
        "from pathlib import Path\n"
        "import sys\n"
        "from analysis.minimax_motion_coach import _analysis_to_payload, run_minimax_motion_coach\n"
        "video_path = Path(sys.argv[1])\n"
        "result_path = Path(sys.argv[2])\n"
        "analysis = run_minimax_motion_coach(str(video_path))\n"
        "result_path.write_text(_analysis_to_payload(analysis), encoding='utf-8')\n"
    )
    env = os.environ.copy()
    cwd = str(Path(__file__).resolve().parents[1])
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        runner,
        str(video_path),
        str(result_path),
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )

    def _cleanup_result_file() -> None:
        try:
            result_path.unlink(missing_ok=True)
        except Exception:
            pass

    start = time.monotonic()
    browser_seen = False
    last_browser_alive_at = start
    communicate_task = asyncio.create_task(proc.communicate())
    try:
        while True:
            now = time.monotonic()
            remaining_s = float(timeout_s) - (now - start)
            if remaining_s <= 0:
                raise asyncio.TimeoutError()
            try:
                stdout, stderr = await asyncio.wait_for(
                    asyncio.shield(communicate_task),
                    timeout=min(2.0, remaining_s),
                )
                break
            except asyncio.TimeoutError:
                browser_alive = _subprocess_has_live_browser_descendants(proc.pid)
                if browser_alive:
                    browser_seen = True
                    last_browser_alive_at = now
                result_size_bytes = 0
                try:
                    if result_path.exists():
                        result_size_bytes = int(result_path.stat().st_size or 0)
                except Exception:
                    result_size_bytes = 0
                if _analysis_subprocess_should_abort_early(
                    elapsed_s=(now - start),
                    result_size_bytes=result_size_bytes,
                    browser_alive=browser_alive,
                    browser_seen=browser_seen,
                    idle_without_browser_s=max(0.0, now - last_browser_alive_at),
                    stall_after_s=float(browser_stall_after_s),
                ):
                    raise RuntimeError(
                        "MiniMax worker subprocess stalled without active browser after {}s".format(
                            int(now - start)
                        )
                    )
    except (asyncio.TimeoutError, RuntimeError) as exc:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            proc.kill()
        try:
            await asyncio.wait_for(asyncio.shield(communicate_task), timeout=10.0)
        except Exception:
            pass
        _cleanup_result_file()
        if isinstance(exc, asyncio.TimeoutError):
            raise TimeoutError(
                "MiniMax worker hard timeout reached after {}s".format(int(timeout_s))
            ) from exc
        raise
    finally:
        if not communicate_task.done():
            communicate_task.cancel()

    if proc.returncode != 0:
        stderr_text = (stderr or b"").decode("utf-8", "ignore").strip()
        stdout_text = (stdout or b"").decode("utf-8", "ignore").strip()
        detail = stderr_text or stdout_text or "unknown subprocess failure"
        _cleanup_result_file()
        raise RuntimeError("MiniMax worker subprocess failed: {}".format(detail[-1600:]))
    if not result_path.exists():
        raise RuntimeError("MiniMax worker subprocess exited without result payload")

    try:
        payload = result_path.read_text(encoding="utf-8").strip()
    finally:
        _cleanup_result_file()

    if not payload:
        raise RuntimeError("MiniMax worker subprocess returned empty payload")
    return payload


async def _complete_job(client: httpx.AsyncClient, job_id: int, analysis_payload: str) -> None:
    response = await client.post(
        _base_url() + "/internal/minimax/jobs/{}/complete".format(job_id),
        headers=_headers(),
        json={"analysis_payload": analysis_payload},
    )
    response.raise_for_status()


async def _heartbeat_job(client: httpx.AsyncClient, job_id: int, worker_id: str) -> None:
    response = await client.post(
        _base_url() + "/internal/minimax/jobs/{}/heartbeat".format(job_id),
        headers=_headers(),
        json={"worker_id": worker_id},
    )
    response.raise_for_status()


async def _fail_job(client: httpx.AsyncClient, job_id: int, error: str) -> None:
    response = await client.post(
        _base_url() + "/internal/minimax/jobs/{}/fail".format(job_id),
        headers=_headers(),
        json={"error": error[:2000]},
    )
    response.raise_for_status()


async def _job_heartbeat_loop(
    client: httpx.AsyncClient,
    *,
    job_id: int,
    worker_id: str,
    stop_event: asyncio.Event,
) -> None:
    interval_s = _job_heartbeat_interval_s()
    while True:
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_s)
            return
        except asyncio.TimeoutError:
            pass
        if stop_event.is_set():
            return
        try:
            await _heartbeat_job(client, job_id, worker_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning(
                "MiniMax remote worker heartbeat failed (job_id=%s worker_id=%s)",
                job_id,
                worker_id,
                exc_info=True,
            )


async def _process_job(client: httpx.AsyncClient, job: dict, worker_id: str) -> None:
    job_id = int(job["id"])
    video_url = str(job["video_url"])
    video_path: Path | None = None
    heartbeat_stop = asyncio.Event()
    heartbeat_task = asyncio.create_task(
        _job_heartbeat_loop(
            client,
            job_id=job_id,
            worker_id=worker_id,
            stop_event=heartbeat_stop,
        )
    )
    try:
        applied_context = _apply_job_browser_context(job)
        if applied_context:
            logger.info(
                "MiniMax remote job runtime context applied (job_id=%s keys=%s)",
                job_id,
                ",".join(sorted(applied_context.keys())),
            )
        video_path = await _download_video(client, job_id, video_url)
        analysis_payload = await _run_analysis_subprocess(video_path)
        analysis = minimax_motion_coach._parse_analysis_payload(analysis_payload)
        logger.info(
            "MiniMax remote job analysis summary (job_id=%s exercise_slug=%s exercise_display=%s score=%s reps_total=%s intensity_score=%s)",
            job_id,
            getattr(analysis, "exercise_slug", ""),
            getattr(analysis, "exercise_display", ""),
            getattr(analysis, "score", 0),
            getattr(analysis, "reps_total", 0),
            getattr(analysis, "intensity_score", 0),
        )
        await _complete_job(client, job_id, analysis_payload)
        logger.info("MiniMax remote job completed (job_id=%s)", job_id)
    except Exception as exc:
        logger.exception("MiniMax remote job failed (job_id=%s)", job_id)
        try:
            await _fail_job(client, job_id, str(exc))
        except Exception:
            logger.exception("Failed to report remote worker error (job_id=%s)", job_id)
    finally:
        heartbeat_stop.set()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("MiniMax remote job heartbeat loop crashed (job_id=%s)", job_id, exc_info=True)
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
    _ensure_display_for_headed_browser()

    worker_id = _worker_id()
    poll_s = _poll_interval_s()
    orphan_cleanup_interval_s = _orphan_cleanup_interval_s()
    last_orphan_cleanup_at = 0.0
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
                now = time.monotonic()
                if (now - last_orphan_cleanup_at) >= orphan_cleanup_interval_s:
                    killed = _kill_orphan_browser_processes()
                    if killed:
                        logger.warning(
                            "Killed %s orphan MiniMax browser process(es) before claim loop",
                            killed,
                        )
                    last_orphan_cleanup_at = now
                job = await _claim_job(client, worker_id)
                if not job:
                    await asyncio.sleep(poll_s)
                    continue
                try:
                    await _process_job(client, job, worker_id)
                finally:
                    _restore_runtime_browser_context(base_runtime_context)
                    killed = _kill_orphan_browser_processes()
                    if killed:
                        logger.warning(
                            "Killed %s orphan MiniMax browser process(es) after job cleanup",
                            killed,
                        )
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
