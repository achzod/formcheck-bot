from __future__ import annotations

from types import SimpleNamespace
import unittest

from analysis.html_report import generate_html_report
from analysis.report_generator import Report


class HtmlReportPersonalizedTests(unittest.TestCase):
    def test_report_includes_client_intro_and_sectioned_fallback(self) -> None:
        report = Report(
            exercise="lat_pulldown",
            exercise_display="Lat Pulldown (Tirage Vertical)",
            score=78,
            report_text="Rapport tres court.",
        )
        reps = SimpleNamespace(
            total_reps=8,
            complete_reps=8,
            partial_reps=0,
            reps=[],
            intensity_score=72,
            intensity_label="elevee",
            avg_inter_rep_rest_s=0.95,
            intensity_confidence="moderee",
        )
        confidence = SimpleNamespace(overall_score=84)
        detection = SimpleNamespace(confidence=0.91)
        pipeline_result = SimpleNamespace(
            reps=reps,
            confidence=confidence,
            detection=detection,
            angles=None,
            morpho_profile=None,
        )

        html, analysis_id, token = generate_html_report(
            report=report,
            annotated_frames={},
            analysis_id="abc123",
            pipeline_result=pipeline_result,
            client_name="Achzod Client",
        )

        self.assertEqual(analysis_id, "abc123")
        self.assertTrue(token)
        self.assertIn("Synthese Client", html)
        self.assertIn("Salut Achzod", html)
        self.assertIn("INTENSITE DE SERIE (DENSITE)", html)
        self.assertIn("PLAN D&#x27;ACTION", html)


if __name__ == "__main__":
    unittest.main()
