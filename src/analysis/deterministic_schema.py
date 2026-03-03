"""Deterministic biomechanical output schema (v2).

This module defines a strict, model-agnostic output contract used by:
- offline benchmarking (evaluation harness)
- long-term report consistency checks
- future integration with 3D + inverse dynamics modules

The schema intentionally avoids free-form text and stores only deterministic
metrics produced by the analytical pipeline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Any


def _round(value: float, ndigits: int = 3) -> float:
    return round(float(value), ndigits)


@dataclass
class TempoSummary:
    eccentric_s: float = 0.0
    pause_bottom_s: float = 0.0
    concentric_s: float = 0.0
    pause_top_s: float = 0.0
    consistency: float = 0.0
    source_confidence: str = "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "eccentric_s": _round(self.eccentric_s, 3),
            "pause_bottom_s": _round(self.pause_bottom_s, 3),
            "concentric_s": _round(self.concentric_s, 3),
            "pause_top_s": _round(self.pause_top_s, 3),
            "consistency": _round(self.consistency, 3),
            "source_confidence": self.source_confidence,
        }


@dataclass
class IntensitySummary:
    score_0_100: int = 0
    label: str = "indeterminee"
    confidence: str = "faible"
    avg_inter_rep_rest_s: float = 0.0
    median_inter_rep_rest_s: float = 0.0
    max_inter_rep_rest_s: float = 0.0
    reps_per_min: float = 0.0
    rest_measure_method: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "score_0_100": int(self.score_0_100),
            "label": self.label,
            "confidence": self.confidence,
            "avg_inter_rep_rest_s": _round(self.avg_inter_rep_rest_s, 3),
            "median_inter_rep_rest_s": _round(self.median_inter_rep_rest_s, 3),
            "max_inter_rep_rest_s": _round(self.max_inter_rep_rest_s, 3),
            "reps_per_min": _round(self.reps_per_min, 3),
            "rest_measure_method": self.rest_measure_method,
        }


@dataclass
class MovementWindow:
    start_frame: int = 0
    end_frame: int = 0
    duration_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_frame": int(self.start_frame),
            "end_frame": int(self.end_frame),
            "duration_s": _round(self.duration_s, 3),
        }


@dataclass
class RepMetric:
    rep_number: int
    start_frame: int
    end_frame: int
    bottom_frame: int
    eccentric_s: float
    concentric_s: float
    tempo_ratio: float
    rom_deg: float
    cheat_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rep_number": int(self.rep_number),
            "start_frame": int(self.start_frame),
            "end_frame": int(self.end_frame),
            "bottom_frame": int(self.bottom_frame),
            "eccentric_s": _round(self.eccentric_s, 3),
            "concentric_s": _round(self.concentric_s, 3),
            "tempo_ratio": _round(self.tempo_ratio, 3),
            "rom_deg": _round(self.rom_deg, 3),
            "cheat_score": _round(self.cheat_score, 3),
        }


@dataclass
class SymmetrySummary:
    knee_flexion_symmetry: float | None = None
    asymmetry_alert: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "knee_flexion_symmetry": (
                None if self.knee_flexion_symmetry is None else _round(self.knee_flexion_symmetry, 3)
            ),
            "asymmetry_alert": bool(self.asymmetry_alert),
        }


@dataclass
class DeterministicBiomechanicsV2:
    schema_version: str = "deterministic-v2"
    sample_id: str = ""
    exercise: str = "unknown"
    exercise_confidence: float = 0.0
    rep_count: int = 0
    complete_reps: int = 0
    partial_reps: int = 0
    tempo: TempoSummary = field(default_factory=TempoSummary)
    intensity: IntensitySummary = field(default_factory=IntensitySummary)
    movement: MovementWindow = field(default_factory=MovementWindow)
    symmetry: SymmetrySummary = field(default_factory=SymmetrySummary)
    rep_metrics: list[RepMetric] = field(default_factory=list)
    deterministic_flags: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sample_id": self.sample_id,
            "exercise": self.exercise,
            "exercise_confidence": _round(self.exercise_confidence, 4),
            "rep_count": int(self.rep_count),
            "complete_reps": int(self.complete_reps),
            "partial_reps": int(self.partial_reps),
            "tempo": self.tempo.to_dict(),
            "intensity": self.intensity.to_dict(),
            "movement": self.movement.to_dict(),
            "symmetry": self.symmetry.to_dict(),
            "rep_metrics": [rep.to_dict() for rep in self.rep_metrics],
            "deterministic_flags": dict(self.deterministic_flags),
        }


def _parse_avg_tempo(avg_tempo: str) -> tuple[float, float]:
    """Parse legacy avg tempo string format 'X:0:Y' -> (ecc, conc)."""
    if not avg_tempo or ":" not in avg_tempo:
        return 0.0, 0.0
    parts = avg_tempo.split(":")
    if len(parts) != 3:
        return 0.0, 0.0
    try:
        return float(parts[0]), float(parts[2])
    except (TypeError, ValueError):
        return 0.0, 0.0


def _estimate_pause_breakdown(rep_metrics: list[RepMetric], movement_duration_s: float) -> tuple[float, float]:
    """Estimate bottom/top pause split from deterministic rep timings.

    We treat total inter-rep rest as observed pauses and distribute it according
    to turnaround tendencies:
    - bottom pause proxy from mean transition around bottom_frame
    - top pause proxy from post-concentric stabilization
    """
    if movement_duration_s <= 0 or not rep_metrics:
        return 0.0, 0.0

    total_active = sum((rep.eccentric_s + rep.concentric_s) for rep in rep_metrics)
    total_pause = max(0.0, movement_duration_s - total_active)
    if total_pause <= 1e-6:
        return 0.0, 0.0

    # Conservative split (top pauses are usually larger on press/curl sets).
    pause_bottom = total_pause * 0.35
    pause_top = total_pause * 0.65
    return pause_bottom / max(1, len(rep_metrics)), pause_top / max(1, len(rep_metrics))


def build_deterministic_output_v2(
    pipeline_result: Any,
    *,
    sample_id: str = "",
) -> dict[str, Any]:
    """Build deterministic v2 output from pipeline result object."""
    detection = getattr(pipeline_result, "detection", None)
    reps = getattr(pipeline_result, "reps", None)

    exercise = "unknown"
    exercise_conf = 0.0
    if detection is not None:
        exercise_obj = getattr(detection, "exercise", None)
        exercise = getattr(exercise_obj, "value", str(exercise_obj or "unknown"))
        exercise_conf = float(getattr(detection, "confidence", 0.0) or 0.0)

    rep_list = []
    if reps is not None:
        for rep in getattr(reps, "reps", []) or []:
            rep_list.append(
                RepMetric(
                    rep_number=int(getattr(rep, "rep_number", 0) or 0),
                    start_frame=int(getattr(rep, "start_frame", 0) or 0),
                    end_frame=int(getattr(rep, "end_frame", 0) or 0),
                    bottom_frame=int(getattr(rep, "bottom_frame", 0) or 0),
                    eccentric_s=float(getattr(rep, "eccentric_duration_ms", 0.0) or 0.0) / 1000.0,
                    concentric_s=float(getattr(rep, "concentric_duration_ms", 0.0) or 0.0) / 1000.0,
                    tempo_ratio=float(getattr(rep, "tempo_ratio", 0.0) or 0.0),
                    rom_deg=float(getattr(rep, "rom", 0.0) or 0.0),
                    cheat_score=float(getattr(rep, "cheat_score", 0.0) or 0.0),
                )
            )

    movement_duration = float(getattr(reps, "movement_duration_s", 0.0) or 0.0) if reps else 0.0
    avg_ecc, avg_conc = _parse_avg_tempo(str(getattr(reps, "avg_tempo", "")) if reps else "")
    if rep_list and (avg_ecc <= 0 or avg_conc <= 0):
        avg_ecc = mean(rep.eccentric_s for rep in rep_list)
        avg_conc = mean(rep.concentric_s for rep in rep_list)
    pause_bottom, pause_top = _estimate_pause_breakdown(rep_list, movement_duration)

    out = DeterministicBiomechanicsV2(
        sample_id=sample_id,
        exercise=exercise,
        exercise_confidence=exercise_conf,
        rep_count=int(getattr(reps, "total_reps", 0) or 0) if reps else 0,
        complete_reps=int(getattr(reps, "complete_reps", 0) or 0) if reps else 0,
        partial_reps=int(getattr(reps, "partial_reps", 0) or 0) if reps else 0,
        tempo=TempoSummary(
            eccentric_s=avg_ecc,
            pause_bottom_s=pause_bottom,
            concentric_s=avg_conc,
            pause_top_s=pause_top,
            consistency=float(getattr(reps, "tempo_consistency", 0.0) or 0.0) if reps else 0.0,
            source_confidence="high" if rep_list else "limited",
        ),
        intensity=IntensitySummary(
            score_0_100=int(getattr(reps, "intensity_score", 0) or 0) if reps else 0,
            label=str(getattr(reps, "intensity_label", "indeterminee")) if reps else "indeterminee",
            confidence=str(getattr(reps, "intensity_confidence", "faible")) if reps else "faible",
            avg_inter_rep_rest_s=float(getattr(reps, "avg_inter_rep_rest_s", 0.0) or 0.0) if reps else 0.0,
            median_inter_rep_rest_s=float(getattr(reps, "median_inter_rep_rest_s", 0.0) or 0.0) if reps else 0.0,
            max_inter_rep_rest_s=float(getattr(reps, "max_inter_rep_rest_s", 0.0) or 0.0) if reps else 0.0,
            reps_per_min=float(getattr(reps, "reps_per_min", 0.0) or 0.0) if reps else 0.0,
            rest_measure_method=str(getattr(reps, "rest_measure_method", "unknown")) if reps else "unknown",
        ),
        movement=MovementWindow(
            start_frame=int(getattr(reps, "movement_start_frame", 0) or 0) if reps else 0,
            end_frame=int(getattr(reps, "movement_end_frame", 0) or 0) if reps else 0,
            duration_s=movement_duration,
        ),
        symmetry=SymmetrySummary(
            knee_flexion_symmetry=None,
            asymmetry_alert=bool(
                float(getattr(reps, "cheat_percentage", 0.0) or 0.0) > 35.0 if reps else False
            ),
        ),
        rep_metrics=rep_list,
        deterministic_flags={
            "has_rep_metrics": bool(rep_list),
            "count_method": str(getattr(reps, "count_method", "")) if reps else "",
            "segmentation_signal": str(getattr(reps, "segmentation_signal", "")) if reps else "",
            "robust_reliable": bool(getattr(reps, "robust_reliable", False)) if reps else False,
        },
    )
    return out.to_dict()

