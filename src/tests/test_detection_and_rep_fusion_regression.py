from __future__ import annotations

import unittest

from analysis.exercise_detector import DetectionResult, Exercise
from analysis.fusion_utils import (
    apply_gemini_vision_consensus_override,
    estimate_intensity_from_fused_count,
    select_reference_rep_count,
)
from analysis.rep_segmenter import _should_apply_robust_down_override


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


if __name__ == "__main__":
    unittest.main()
