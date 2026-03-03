"""Offline evaluation runner for deterministic biomechanics outputs."""

from __future__ import annotations

from typing import Any

from evaluation.dataset import load_samples, pair_by_id, sample_id
from evaluation.metrics import (
    angle_mae_deg,
    compensation_f1,
    exercise_macro_f1,
    rep_count_mae,
    tempo_mae_s,
)


def _extract_exercise(sample: dict[str, Any]) -> str | None:
    value = sample.get("exercise")
    if value not in (None, ""):
        return str(value)
    det = sample.get("detection")
    if isinstance(det, dict):
        ex = det.get("exercise")
        if ex not in (None, ""):
            return str(ex)
    return None


def _extract_rep_count(sample: dict[str, Any]) -> float | None:
    for key in ("rep_count", "total_reps"):
        if key in sample:
            value = sample.get(key)
            if value not in (None, ""):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None
    reps = sample.get("reps")
    if isinstance(reps, list):
        return float(len(reps))
    return None


def _parse_tempo_string(value: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(value, str):
        return None
    if ":" not in value:
        return None
    parts = value.split(":")
    if len(parts) != 3:
        return None
    try:
        return float(parts[0]), 0.0, float(parts[2]), 0.0
    except (TypeError, ValueError):
        return None


def _extract_tempo(sample: dict[str, Any]) -> tuple[float, float, float, float] | None:
    tempo = sample.get("tempo")
    if isinstance(tempo, dict):
        keys = ("eccentric_s", "pause_bottom_s", "concentric_s", "pause_top_s")
        values: list[float] = []
        for key in keys:
            raw = tempo.get(key)
            if raw in (None, ""):
                return None
            try:
                values.append(float(raw))
            except (TypeError, ValueError):
                return None
        return values[0], values[1], values[2], values[3]

    return _parse_tempo_string(sample.get("avg_tempo"))


def _extract_angles(sample: dict[str, Any]) -> dict[str, float] | None:
    for key in ("angles", "joint_angles_deg", "angle_metrics"):
        payload = sample.get(key)
        if not isinstance(payload, dict):
            continue
        out: dict[str, float] = {}
        for k, v in payload.items():
            try:
                out[str(k)] = float(v)
            except (TypeError, ValueError):
                continue
        if out:
            return out
    return None


def _extract_compensations(sample: dict[str, Any]) -> set[str] | None:
    for key in ("compensations", "compensation_flags"):
        payload = sample.get(key)
        if isinstance(payload, list):
            return {str(v) for v in payload if v not in (None, "")}
    return None


def evaluate_paired_samples(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    """Evaluate a list of `(reference, prediction)` sample pairs."""
    exercise_true: list[str] = []
    exercise_pred: list[str] = []
    rep_true: list[float] = []
    rep_pred: list[float] = []
    tempo_true: list[tuple[float, float, float, float]] = []
    tempo_pred: list[tuple[float, float, float, float]] = []
    angle_true: list[dict[str, float]] = []
    angle_pred: list[dict[str, float]] = []
    comp_true: list[set[str]] = []
    comp_pred: list[set[str]] = []
    ids: list[str] = []

    for ref, pred in pairs:
        ids.append(sample_id(ref))

        ex_ref = _extract_exercise(ref)
        ex_pred = _extract_exercise(pred)
        if ex_ref is not None and ex_pred is not None:
            exercise_true.append(ex_ref)
            exercise_pred.append(ex_pred)

        rep_ref = _extract_rep_count(ref)
        rep_p = _extract_rep_count(pred)
        if rep_ref is not None and rep_p is not None:
            rep_true.append(rep_ref)
            rep_pred.append(rep_p)

        tempo_ref = _extract_tempo(ref)
        tempo_p = _extract_tempo(pred)
        if tempo_ref is not None and tempo_p is not None:
            tempo_true.append(tempo_ref)
            tempo_pred.append(tempo_p)

        ang_ref = _extract_angles(ref)
        ang_p = _extract_angles(pred)
        if ang_ref is not None and ang_p is not None:
            angle_true.append(ang_ref)
            angle_pred.append(ang_p)

        comp_ref = _extract_compensations(ref)
        comp_p = _extract_compensations(pred)
        if comp_ref is not None and comp_p is not None:
            comp_true.append(comp_ref)
            comp_pred.append(comp_p)

    metrics = {
        "exercise_macro_f1": exercise_macro_f1(exercise_true, exercise_pred),
        "rep_count_mae": rep_count_mae(rep_true, rep_pred),
        "tempo_mae_s": tempo_mae_s(tempo_true, tempo_pred),
        "angle_mae_deg": angle_mae_deg(angle_true, angle_pred),
        "compensation_f1": compensation_f1(comp_true, comp_pred),
    }

    coverage = {
        "exercise_pairs": len(exercise_true),
        "rep_pairs": len(rep_true),
        "tempo_pairs": len(tempo_true),
        "angle_pairs": len(angle_true),
        "compensation_pairs": len(comp_true),
    }

    return {
        "paired_samples": len(pairs),
        "sample_ids": ids,
        "coverage": coverage,
        "metrics": metrics,
    }


def evaluate_prediction_files(
    reference_path: str,
    prediction_path: str,
) -> dict[str, Any]:
    """Load two datasets and evaluate prediction quality."""
    reference_samples = load_samples(reference_path)
    predicted_samples = load_samples(prediction_path)
    pairs = pair_by_id(reference_samples, predicted_samples)
    result = evaluate_paired_samples(pairs)
    result["reference_count"] = len(reference_samples)
    result["prediction_count"] = len(predicted_samples)
    result["paired_ratio"] = (
        float(len(pairs)) / float(len(reference_samples))
        if reference_samples
        else 0.0
    )
    return result

