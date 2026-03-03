"""Dataset IO utilities for offline evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _ensure_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        if isinstance(payload.get("samples"), list):
            return [item for item in payload["samples"] if isinstance(item, dict)]
        return [payload]
    return []


def load_samples(path: str) -> list[dict[str, Any]]:
    """Load samples from JSON or JSONL."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    raw = p.read_text(encoding="utf-8").strip()
    if not raw:
        return []

    if p.suffix.lower() == ".jsonl":
        rows: list[dict[str, Any]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
        return rows

    return _ensure_list(json.loads(raw))


def sample_id(sample: dict[str, Any], default: str = "") -> str:
    for key in ("sample_id", "id", "analysis_id", "video_id"):
        if key in sample and sample[key] not in (None, ""):
            return str(sample[key])
    return default


def pair_by_id(
    reference_samples: list[dict[str, Any]],
    predicted_samples: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Pair predicted and reference rows by sample id, preserving reference order."""
    pred_index: dict[str, dict[str, Any]] = {}
    for pred in predicted_samples:
        sid = sample_id(pred)
        if sid:
            pred_index[sid] = pred

    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for idx, ref in enumerate(reference_samples):
        sid = sample_id(ref, default=str(idx))
        pred = pred_index.get(sid)
        if pred is None:
            continue
        pairs.append((ref, pred))
    return pairs

