"""Utility functions for detection/rep fusion that are easy to unit-test."""

from __future__ import annotations

from analysis.exercise_detector import DetectionResult, Exercise


def apply_gemini_vision_consensus_override(
    source: str,
    detection: DetectionResult,
    winning_score: float,
    scored_candidates: list[tuple[str, DetectionResult, float]],
    press_profile: dict[str, float | bool] | None = None,
) -> tuple[str, DetectionResult, float]:
    """Priorise a strong Gemini+Vision consensus over isolated pattern votes."""
    gemini_tuple = next((it for it in scored_candidates if it[0] == "gemini"), None)
    vision_tuple = next((it for it in scored_candidates if it[0] == "vision"), None)
    if gemini_tuple is None or vision_tuple is None:
        return source, detection, winning_score

    gemini_det = gemini_tuple[1]
    vision_det = vision_tuple[1]
    if (
        gemini_det.exercise == Exercise.UNKNOWN
        or vision_det.exercise == Exercise.UNKNOWN
        or gemini_det.exercise != vision_det.exercise
    ):
        return source, detection, winning_score

    consensus_conf = (float(gemini_det.confidence) + float(vision_det.confidence)) / 2.0
    if consensus_conf < 0.72:
        return source, detection, winning_score

    consensus_ex = gemini_det.exercise
    consensus_tuple = gemini_tuple if gemini_det.confidence >= vision_det.confidence else vision_tuple
    consensus_score = max(float(gemini_tuple[2]), float(vision_tuple[2]))
    margin = winning_score - consensus_score

    overhead_ratio = 0.0
    if press_profile:
        overhead_ratio = float(press_profile.get("overhead_ratio", 0.0) or 0.0)
    shoulder_ambiguity = (
        detection.exercise in {Exercise.OHP, Exercise.DUMBBELL_OHP, Exercise.UPRIGHT_ROW}
        and consensus_ex in {Exercise.LATERAL_RAISE, Exercise.FRONT_RAISE}
    )

    should_override = False
    if source == "pattern" and margin <= 0.24:
        should_override = True
    if source == "pattern" and shoulder_ambiguity and overhead_ratio < 0.24:
        should_override = True

    if should_override:
        return "gemini_vision_consensus_override", consensus_tuple[1], consensus_score

    return source, detection, winning_score


def estimate_intensity_from_fused_count(
    rep_count: int,
    set_duration_s: float,
) -> dict[str, float | int | str]:
    """Conservative fallback used when rep count is overridden after segmentation."""
    base = {
        "avg_inter_rep_rest_s": 0.0,
        "median_inter_rep_rest_s": 0.0,
        "max_inter_rep_rest_s": 0.0,
        "rest_consistency": 0.0,
        "set_duration_s": max(0.0, set_duration_s),
        "reps_per_min": 0.0,
        "intensity_score": 0,
        "intensity_label": "indeterminee",
    }
    if rep_count < 2 or set_duration_s <= 0:
        return base

    reps_per_min = (rep_count * 60.0 / set_duration_s) if set_duration_s > 0 else 0.0
    avg_cycle_s = set_duration_s / max(1, rep_count)
    avg_rest = max(0.0, avg_cycle_s * 0.20)

    if avg_rest <= 0.6:
        score = 84
    elif avg_rest <= 1.0:
        score = 76
    elif avg_rest <= 1.5:
        score = 66
    elif avg_rest <= 2.5:
        score = 54
    else:
        score = 42

    if reps_per_min >= 20:
        score += 4
    elif reps_per_min >= 14:
        score += 2
    elif reps_per_min < 8:
        score -= 6

    score = int(max(0, min(100, score)))
    if score >= 85:
        label = "tres elevee"
    elif score >= 70:
        label = "elevee"
    elif score >= 55:
        label = "moderee"
    elif score >= 40:
        label = "faible"
    else:
        label = "tres faible"

    return {
        "avg_inter_rep_rest_s": avg_rest,
        "median_inter_rep_rest_s": avg_rest,
        "max_inter_rep_rest_s": avg_rest * 1.4,
        "rest_consistency": 0.45,
        "set_duration_s": set_duration_s,
        "reps_per_min": reps_per_min,
        "intensity_score": score,
        "intensity_label": label,
    }

