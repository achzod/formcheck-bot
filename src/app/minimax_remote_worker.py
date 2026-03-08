from __future__ import annotations

import asyncio
import logging
import os
import socket
import tempfile
from pathlib import Path

import httpx

from analysis.minimax_motion_coach import _analysis_to_payload, run_minimax_motion_coach

logger = logging.getLogger("formcheck.minimax_remote_worker")


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
        raise RuntimeError("Missing MINIMAX_REMOTE_WORKER_TOKEN or FORMCHECK_INTERNAL_TOKEN")
    return {"X-Formcheck-Internal-Token": token}


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
    # MiniMax/Cloudflare blocks AI Motion Coach reliably in headless mode on this setup.
    # Force a headed Chrome session for the production browser worker.
    os.environ["MINIMAX_BROWSER_HEADLESS"] = "false"
    os.environ.setdefault("MINIMAX_BROWSER_CHANNEL", "chrome")

    worker_id = _worker_id()
    poll_s = _poll_interval_s()
    timeout = httpx.Timeout(120.0, connect=20.0)

    logger.info(
        "MiniMax remote worker bootstrap (worker_id=%s headless=%s channel=%s base_url=%s)",
        worker_id,
        os.getenv("MINIMAX_BROWSER_HEADLESS", ""),
        os.getenv("MINIMAX_BROWSER_CHANNEL", ""),
        _base_url(),
    )

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        while True:
            try:
                job = await _claim_job(client, worker_id)
                if not job:
                    await asyncio.sleep(poll_s)
                    continue
                await _process_job(client, job)
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
