"""Quality gates for offline biomechanical evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class GateThresholds:
    """Production-readiness thresholds for deterministic metrics."""

    exercise_macro_f1_min: float = 0.90
    rep_count_mae_max: float = 0.75
    tempo_mae_s_max: float = 0.45
    angle_mae_deg_max: float = 8.0
    compensation_f1_min: float = 0.80
    min_paired_samples: int = 8


def _check_min(value: float | None, threshold: float) -> tuple[bool, str]:
    if value is None:
        return False, "missing"
    passed = bool(float(value) >= float(threshold))
    return passed, ("ok" if passed else "below_threshold")


def _check_max(value: float | None, threshold: float) -> tuple[bool, str]:
    if value is None:
        return False, "missing"
    passed = bool(float(value) <= float(threshold))
    return passed, ("ok" if passed else "above_threshold")


def evaluate_gates(
    metrics: dict[str, float],
    *,
    thresholds: GateThresholds | None = None,
    paired_samples: int = 0,
) -> dict[str, Any]:
    """Evaluate pass/fail gates against computed metric values."""
    th = thresholds or GateThresholds()

    ex_ok, ex_reason = _check_min(metrics.get("exercise_macro_f1"), th.exercise_macro_f1_min)
    rep_ok, rep_reason = _check_max(metrics.get("rep_count_mae"), th.rep_count_mae_max)
    tempo_ok, tempo_reason = _check_max(metrics.get("tempo_mae_s"), th.tempo_mae_s_max)
    angle_ok, angle_reason = _check_max(metrics.get("angle_mae_deg"), th.angle_mae_deg_max)
    comp_ok, comp_reason = _check_min(metrics.get("compensation_f1"), th.compensation_f1_min)
    sample_ok = int(paired_samples) >= int(th.min_paired_samples)

    checks = {
        "exercise_macro_f1": {
            "mode": "min",
            "value": metrics.get("exercise_macro_f1"),
            "threshold": th.exercise_macro_f1_min,
            "passed": ex_ok,
            "reason": ex_reason,
        },
        "rep_count_mae": {
            "mode": "max",
            "value": metrics.get("rep_count_mae"),
            "threshold": th.rep_count_mae_max,
            "passed": rep_ok,
            "reason": rep_reason,
        },
        "tempo_mae_s": {
            "mode": "max",
            "value": metrics.get("tempo_mae_s"),
            "threshold": th.tempo_mae_s_max,
            "passed": tempo_ok,
            "reason": tempo_reason,
        },
        "angle_mae_deg": {
            "mode": "max",
            "value": metrics.get("angle_mae_deg"),
            "threshold": th.angle_mae_deg_max,
            "passed": angle_ok,
            "reason": angle_reason,
        },
        "compensation_f1": {
            "mode": "min",
            "value": metrics.get("compensation_f1"),
            "threshold": th.compensation_f1_min,
            "passed": comp_ok,
            "reason": comp_reason,
        },
        "paired_samples": {
            "mode": "min",
            "value": int(paired_samples),
            "threshold": int(th.min_paired_samples),
            "passed": sample_ok,
            "reason": "ok",
        },
    }

    return {
        "passed": bool(ex_ok and rep_ok and tempo_ok and angle_ok and comp_ok and sample_ok),
        "paired_samples": int(paired_samples),
        "thresholds": asdict(th),
        "checks": checks,
    }
