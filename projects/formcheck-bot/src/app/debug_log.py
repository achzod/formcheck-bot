"""Ring buffer for recent errors — accessible via /debug/errors endpoint."""

from __future__ import annotations

import datetime

MAX_ERRORS = 20
_last_errors: list[dict] = []


def log_error(context: str, error: str, extra: dict | None = None) -> None:
    """Store an error in the ring buffer for debug endpoint."""
    entry: dict = {
        "ts": datetime.datetime.utcnow().isoformat(),
        "context": context,
        "error": error[:500],
    }
    if extra:
        entry["extra"] = {k: str(v)[:200] for k, v in extra.items()}
    _last_errors.append(entry)
    if len(_last_errors) > MAX_ERRORS:
        _last_errors.pop(0)


def get_errors() -> list[dict]:
    """Return the last N errors."""
    return _last_errors[-MAX_ERRORS:]
