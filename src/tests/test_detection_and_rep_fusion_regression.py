from __future__ import annotations

import sys
import types
import unittest

import numpy as np

# Keep pipeline utility imports testable without OpenCV runtime dependency.
if "cv2" not in sys.modules:
    sys.modules["cv2"] = types.ModuleType("cv2")

from analysis.exercise_detector import DetectionResult, Exercise
from analysis.fusion_utils import (
    apply_gemini_vision_consensus_override,
    disambiguate_upper_pull_exercise,
    estimate_intensity_from_fused_count,
    select_reference_rep_count,
)
from analysis.pipeline import _derive_key_frames_from_reps, _map_model_exercise_name
from analysis.rep_segmenter import (
    Rep,
    RepSegmentation,
    _active_region_bounds,
    _compute_intensity_metrics,
    _estimate_transition_rests,
    _should_apply_robust_down_override,
)


class DetectionFusionRegressionTests(unittest.TestCase):
    def test_consensus_overrides_pattern_for_shoulder_confusion(self) -> None:
        gemini = DetectionResult(
            exercise=Exercise.LATERAL_RAISE,
            confidence=0.92,
            reasoning="gemini",
        )
        vision = DetectionResult(
            exercise=Exercise.LATERAL_RAISE,
            confidence=0.88,
            reasoning="vision",
        )
        pattern = DetectionResult(
            exercise=Exercise.OHP,
            confidence=0.80,
            reasoning="pattern",
        )
        scored = [
            ("gemini", gemini, 1.11),
            ("vision", vision, 1.08),
            ("pattern", pattern, 1.22),
        ]
        source, detection, score = apply_gemini_vision_consensus_override(
            source="pattern",
            detection=pattern,
            winning_score=1.22,
            scored_candidates=scored,
            press_profile={"overhead_ratio": 0.16},
        )
        self.assertEqual(source, "gemini_vision_consensus_override")
        self.assertEqual(detection.exercise, Exercise.LATERAL_RAISE)
        self.assertAlmostEqual(score, 1.11, places=6)

    def test_no_override_without_gemini_vision_agreement(self) -> None:
        gemini = DetectionResult(exercise=Exercise.LATERAL_RAISE, confidence=0.92, reasoning="gemini")
        vision = DetectionResult(exercise=Exercise.FRONT_RAISE, confidence=0.88, reasoning="vision")
        pattern = DetectionResult(exercise=Exercise.OHP, confidence=0.80, reasoning="pattern")
        scored = [
            ("gemini", gemini, 1.11),
            ("vision", vision, 1.09),
            ("pattern", pattern, 1.22),
        ]
        source, detection, score = apply_gemini_vision_consensus_override(
            source="pattern",
            detection=pattern,
            winning_score=1.22,
            scored_candidates=scored,
            press_profile={"overhead_ratio": 0.16},
        )
        self.assertEqual(source, "pattern")
        self.assertEqual(detection.exercise, Exercise.OHP)
        self.assertAlmostEqual(score, 1.22, places=6)

    def test_upper_lower_conflict_overrides_pattern(self) -> None:
        gemini = DetectionResult(exercise=Exercise.LAT_PULLDOWN, confidence=1.0, reasoning="gemini")
        vision = DetectionResult(exercise=Exercise.LAT_PULLDOWN, confidence=0.95, reasoning="vision")
        pattern = DetectionResult(exercise=Exercise.LUNGE, confidence=0.80, reasoning="pattern")
        scored = [
            ("gemini", gemini, 0.98),
            ("vision", vision, 0.93),
            ("pattern", pattern, 1.43),
        ]
        source, detection, _ = apply_gemini_vision_consensus_override(
            source="pattern",
            detection=pattern,
            winning_score=1.43,
            scored_candidates=scored,
            press_profile={"overhead_ratio": 0.79},
        )
        self.assertEqual(source, "gemini_vision_consensus_override")
        self.assertEqual(detection.exercise, Exercise.LAT_PULLDOWN)


class RepFusionRegressionTests(unittest.TestCase):
    def test_robust_down_override_threshold(self) -> None:
        self.assertTrue(_should_apply_robust_down_override(peak_count=26, robust_count=19, robust_reliable=True))
        self.assertFalse(_should_apply_robust_down_override(peak_count=24, robust_count=19, robust_reliable=True))
        self.assertFalse(_should_apply_robust_down_override(peak_count=26, robust_count=19, robust_reliable=False))

    def test_fused_intensity_estimate_has_non_zero_rest(self) -> None:
        metrics = estimate_intensity_from_fused_count(rep_count=19, set_duration_s=54.5)
        self.assertGreater(float(metrics["avg_inter_rep_rest_s"]), 0.0)
        self.assertGreater(float(metrics["reps_per_min"]), 0.0)
        self.assertIn(str(metrics["intensity_label"]), {"tres elevee", "elevee", "moderee", "faible", "tres faible"})

    def test_reference_count_ignores_unreliable_robust(self) -> None:
        self.assertEqual(
            select_reference_rep_count(signal_rep_count=19, robust_rep_count=1, robust_reliable=False),
            19,
        )
        self.assertEqual(
            select_reference_rep_count(signal_rep_count=19, robust_rep_count=6, robust_reliable=True),
            6,
        )


class UpperPullDisambiguationTests(unittest.TestCase):
    def test_lat_pulldown_relabelled_to_cable_pullover_when_profile_says_so(self) -> None:
        det = DetectionResult(exercise=Exercise.LAT_PULLDOWN, confidence=0.95, reasoning="base")
        source, out = disambiguate_upper_pull_exercise(
            "gemini_vision_consensus_override",
            det,
            upper_pull_profile={"pullover_signal": 0.76, "lat_pulldown_signal": 0.52},
        )
        self.assertEqual(source, "upper_pull_disambiguation")
        self.assertEqual(out.exercise, Exercise.CABLE_PULLOVER)

    def test_no_relabel_when_profile_not_decisive(self) -> None:
        det = DetectionResult(exercise=Exercise.LAT_PULLDOWN, confidence=0.95, reasoning="base")
        source, out = disambiguate_upper_pull_exercise(
            "gemini_vision_consensus_override",
            det,
            upper_pull_profile={"pullover_signal": 0.56, "lat_pulldown_signal": 0.52},
        )
        self.assertEqual(source, "gemini_vision_consensus_override")
        self.assertEqual(out.exercise, Exercise.LAT_PULLDOWN)


class GenericHardeningTests(unittest.TestCase):
    def test_model_name_mapping_handles_common_variants(self) -> None:
        self.assertEqual(_map_model_exercise_name("smith_machine_shoulder_press"), "ohp")
        self.assertEqual(_map_model_exercise_name("straight-arm pulldown"), "cable_pullover")
        self.assertEqual(_map_model_exercise_name("Bulgarian Split Lunge"), "bulgarian_split_squat")

    def test_active_region_bounds_focus_on_movement_window(self) -> None:
        signal = np.concatenate(
            [
                np.zeros(45, dtype=float),
                np.sin(np.linspace(0, 6 * np.pi, 140, dtype=float)),
                np.zeros(45, dtype=float),
            ]
        )
        start, end = _active_region_bounds(signal, fps=30.0)
        self.assertGreater(start, 0)
        self.assertLess(end, len(signal))
        self.assertLess(start, 90)
        self.assertGreater(end, 140)

    def test_transition_rests_are_non_zero_with_plateaus(self) -> None:
        signal = np.concatenate(
            [
                np.linspace(0.0, 1.0, 20, dtype=float),
                np.full(8, 1.0, dtype=float),
                np.linspace(1.0, 0.0, 20, dtype=float),
                np.full(8, 0.0, dtype=float),
                np.linspace(0.0, 1.0, 20, dtype=float),
                np.full(8, 1.0, dtype=float),
                np.linspace(1.0, 0.0, 20, dtype=float),
            ]
        )
        frame_indices = np.arange(len(signal), dtype=int)
        reps = [
            Rep(rep_number=1, start_frame=0, end_frame=48, bottom_frame=24),
            Rep(rep_number=2, start_frame=48, end_frame=96, bottom_frame=72),
            Rep(rep_number=3, start_frame=96, end_frame=len(signal) - 1, bottom_frame=120),
        ]
        rests = _estimate_transition_rests(reps, signal, frame_indices, fps=30.0)
        self.assertEqual(len(rests), 2)
        self.assertGreater(min(rests), 0.0)

        intensity = _compute_intensity_metrics(reps, fps=30.0, transition_rests_s=rests)
        self.assertGreater(float(intensity["avg_inter_rep_rest_s"]), 0.0)
        self.assertGreaterEqual(int(intensity["intensity_score"]), 0)

    def test_rep_keyframe_derivation_uses_segmented_boundaries(self) -> None:
        reps = RepSegmentation(
            reps=[
                Rep(rep_number=1, start_frame=15, end_frame=45, bottom_frame=30, rom=32.0),
                Rep(rep_number=2, start_frame=45, end_frame=78, bottom_frame=60, rom=48.0),
                Rep(rep_number=3, start_frame=78, end_frame=112, bottom_frame=96, rom=41.0),
            ]
        )
        keyframes = _derive_key_frames_from_reps(reps, total_frames=180)
        self.assertIsNotNone(keyframes)
        assert keyframes is not None
        self.assertEqual(keyframes["start"], 15)
        self.assertEqual(keyframes["mid"], 60)
        self.assertEqual(keyframes["end"], 112)


if __name__ == "__main__":
    unittest.main()
