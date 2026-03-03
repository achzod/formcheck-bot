from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from analysis.deterministic_schema import build_deterministic_output_v2
from evaluation.cli import main as evaluation_cli_main
from evaluation.gates import GateThresholds, evaluate_gates
from evaluation.runner import evaluate_prediction_files, evaluate_paired_samples


class DeterministicSchemaTests(unittest.TestCase):
    def test_build_deterministic_output_v2_maps_pipeline_fields(self) -> None:
        reps = [
            SimpleNamespace(
                rep_number=1,
                start_frame=10,
                end_frame=40,
                bottom_frame=24,
                eccentric_duration_ms=1200.0,
                concentric_duration_ms=800.0,
                tempo_ratio=1.5,
                rom=52.0,
                cheat_score=0.05,
            ),
            SimpleNamespace(
                rep_number=2,
                start_frame=40,
                end_frame=70,
                bottom_frame=55,
                eccentric_duration_ms=1100.0,
                concentric_duration_ms=900.0,
                tempo_ratio=1.22,
                rom=49.5,
                cheat_score=0.10,
            ),
        ]
        rep_seg = SimpleNamespace(
            reps=reps,
            total_reps=2,
            complete_reps=2,
            partial_reps=0,
            avg_tempo="1:0:1",
            tempo_consistency=0.88,
            movement_duration_s=6.0,
            intensity_score=79,
            intensity_label="elevee",
            intensity_confidence="elevee",
            avg_inter_rep_rest_s=0.9,
            median_inter_rep_rest_s=0.8,
            max_inter_rep_rest_s=1.1,
            reps_per_min=20.0,
            rest_measure_method="transition_velocity",
            movement_start_frame=10,
            movement_end_frame=70,
            count_method="peak_aligned_with_robust",
            segmentation_signal="left_elbow_flexion",
            robust_reliable=True,
            cheat_percentage=10.0,
        )
        detection = SimpleNamespace(exercise=SimpleNamespace(value="ohp"), confidence=0.9132)
        pipeline_result = SimpleNamespace(detection=detection, reps=rep_seg)

        out = build_deterministic_output_v2(pipeline_result, sample_id="sample-ohp-1")

        self.assertEqual(out["schema_version"], "deterministic-v2")
        self.assertEqual(out["sample_id"], "sample-ohp-1")
        self.assertEqual(out["exercise"], "ohp")
        self.assertAlmostEqual(out["exercise_confidence"], 0.9132, places=4)
        self.assertEqual(out["rep_count"], 2)
        self.assertEqual(out["complete_reps"], 2)
        self.assertEqual(out["partial_reps"], 0)
        self.assertAlmostEqual(out["tempo"]["eccentric_s"], 1.0, places=3)
        self.assertAlmostEqual(out["tempo"]["concentric_s"], 1.0, places=3)
        self.assertAlmostEqual(out["tempo"]["pause_bottom_s"], 0.35, places=3)
        self.assertAlmostEqual(out["tempo"]["pause_top_s"], 0.65, places=3)
        self.assertEqual(out["intensity"]["score_0_100"], 79)
        self.assertEqual(out["movement"]["start_frame"], 10)
        self.assertEqual(out["movement"]["end_frame"], 70)
        self.assertEqual(len(out["rep_metrics"]), 2)
        self.assertTrue(out["deterministic_flags"]["has_rep_metrics"])


class EvaluationHarnessTests(unittest.TestCase):
    def test_evaluate_paired_samples_computes_core_metrics(self) -> None:
        pairs = [
            (
                {
                    "sample_id": "s1",
                    "exercise": "squat",
                    "rep_count": 5,
                    "tempo": {
                        "eccentric_s": 3.0,
                        "pause_bottom_s": 1.0,
                        "concentric_s": 2.0,
                        "pause_top_s": 1.0,
                    },
                    "angles": {"knee": 100.0, "hip": 80.0},
                    "compensations": ["knee_valgus"],
                },
                {
                    "sample_id": "s1",
                    "exercise": "squat",
                    "rep_count": 6,
                    "tempo": {
                        "eccentric_s": 2.8,
                        "pause_bottom_s": 0.9,
                        "concentric_s": 2.1,
                        "pause_top_s": 1.2,
                    },
                    "angles": {"knee": 98.0, "hip": 84.0},
                    "compensations": ["knee_valgus"],
                },
            ),
            (
                {
                    "sample_id": "s2",
                    "exercise": "ohp",
                    "rep_count": 8,
                    "tempo": {
                        "eccentric_s": 2.0,
                        "pause_bottom_s": 0.5,
                        "concentric_s": 1.5,
                        "pause_top_s": 0.6,
                    },
                    "angles": {"shoulder": 110.0},
                    "compensations": [],
                },
                {
                    "sample_id": "s2",
                    "exercise": "upright_row",
                    "rep_count": 8,
                    "tempo": {
                        "eccentric_s": 2.2,
                        "pause_bottom_s": 0.4,
                        "concentric_s": 1.4,
                        "pause_top_s": 0.4,
                    },
                    "angles": {"shoulder": 112.0},
                    "compensations": ["upper_trap_compensation"],
                },
            ),
        ]

        out = evaluate_paired_samples(pairs)
        metrics = out["metrics"]

        self.assertEqual(out["paired_samples"], 2)
        self.assertEqual(out["coverage"]["exercise_pairs"], 2)
        self.assertEqual(out["coverage"]["rep_pairs"], 2)
        self.assertAlmostEqual(metrics["rep_count_mae"], 0.5, places=6)
        self.assertGreaterEqual(metrics["exercise_macro_f1"], 0.0)
        self.assertLess(metrics["exercise_macro_f1"], 1.0)
        self.assertGreater(metrics["tempo_mae_s"], 0.0)
        self.assertGreater(metrics["angle_mae_deg"], 0.0)
        self.assertGreaterEqual(metrics["compensation_f1"], 0.0)
        self.assertLess(metrics["compensation_f1"], 1.0)

    def test_evaluate_prediction_files_pairs_by_sample_id(self) -> None:
        reference = [
            {"sample_id": "vid-a", "exercise": "squat", "rep_count": 6, "avg_tempo": "3:0:2"},
            {"sample_id": "vid-b", "exercise": "ohp", "rep_count": 8, "avg_tempo": "2:0:2"},
        ]
        predictions = [
            {"sample_id": "vid-b", "exercise": "ohp", "rep_count": 8, "avg_tempo": "2:0:2"},
            {"sample_id": "vid-a", "exercise": "squat", "rep_count": 5, "avg_tempo": "3:0:2"},
            {"sample_id": "vid-c", "exercise": "deadlift", "rep_count": 4, "avg_tempo": "2:0:2"},
        ]

        with tempfile.TemporaryDirectory() as td:
            ref_path = Path(td) / "ref.json"
            pred_path = Path(td) / "pred.json"
            ref_path.write_text(json.dumps(reference), encoding="utf-8")
            pred_path.write_text(json.dumps(predictions), encoding="utf-8")

            out = evaluate_prediction_files(str(ref_path), str(pred_path))

        self.assertEqual(out["reference_count"], 2)
        self.assertEqual(out["prediction_count"], 3)
        self.assertEqual(out["paired_samples"], 2)
        self.assertEqual(out["sample_ids"], ["vid-a", "vid-b"])
        self.assertAlmostEqual(out["paired_ratio"], 1.0, places=6)
        self.assertAlmostEqual(out["metrics"]["rep_count_mae"], 0.5, places=6)


class EvaluationGateTests(unittest.TestCase):
    def test_gate_pass_and_fail_paths(self) -> None:
        metrics = {
            "exercise_macro_f1": 0.95,
            "rep_count_mae": 0.35,
            "tempo_mae_s": 0.22,
            "angle_mae_deg": 3.5,
            "compensation_f1": 0.90,
        }
        passing = evaluate_gates(
            metrics,
            thresholds=GateThresholds(min_paired_samples=2),
            paired_samples=2,
        )
        self.assertTrue(passing["passed"])

        failing = evaluate_gates(
            metrics,
            thresholds=GateThresholds(
                exercise_macro_f1_min=0.98,
                rep_count_mae_max=0.20,
                tempo_mae_s_max=0.10,
                angle_mae_deg_max=2.0,
                compensation_f1_min=0.95,
                min_paired_samples=3,
            ),
            paired_samples=2,
        )
        self.assertFalse(failing["passed"])
        self.assertFalse(failing["checks"]["paired_samples"]["passed"])

    def test_cli_returns_non_zero_when_fail_on_gates(self) -> None:
        reference = [{"sample_id": "x", "exercise": "squat", "rep_count": 8, "avg_tempo": "3:0:2"}]
        predictions = [{"sample_id": "x", "exercise": "lunge", "rep_count": 3, "avg_tempo": "1:0:1"}]

        with tempfile.TemporaryDirectory() as td:
            ref_path = Path(td) / "ref.json"
            pred_path = Path(td) / "pred.json"
            out_path = Path(td) / "result.json"
            ref_path.write_text(json.dumps(reference), encoding="utf-8")
            pred_path.write_text(json.dumps(predictions), encoding="utf-8")

            with redirect_stdout(StringIO()):
                code = evaluation_cli_main(
                    [
                        "--reference",
                        str(ref_path),
                        "--predictions",
                        str(pred_path),
                        "--output",
                        str(out_path),
                        "--fail-on-gates",
                        "--exercise-f1-min",
                        "0.95",
                        "--rep-mae-max",
                        "0.10",
                        "--tempo-mae-max",
                        "0.10",
                        "--angle-mae-max",
                        "1.0",
                        "--comp-f1-min",
                        "0.95",
                        "--min-samples",
                        "1",
                    ]
                )

            self.assertEqual(code, 1)
            self.assertTrue(out_path.exists())


if __name__ == "__main__":
    unittest.main()
