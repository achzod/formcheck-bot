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

    def test_clamps_invalid_symetrie_line_in_report_text_and_gauge(self) -> None:
        report = Report(
            exercise="row",
            exercise_display="Row",
            score=75,
            report_text=(
                "DECOMPOSITION DU SCORE\n"
                "Securite: 35/40\n"
                "Efficacite technique: 22/30\n"
                "Controle et tempo: 16/20\n"
                "Symetrie: 12/10\n"
            ),
            score_breakdown={
                "Securite": 35,
                "Efficacite technique": 22,
                "Controle et tempo": 16,
                "Symetrie": 12,
            },
        )

        html, _, _ = generate_html_report(
            report=report,
            annotated_frames={},
            analysis_id="symtest",
            pipeline_result=None,
            client_name="Client",
        )

        self.assertIn("Symetrie: 10/10", html)
        self.assertNotIn("Symetrie: 12/10", html)

    def test_minimax_report_uses_raw_text_without_local_fallback(self) -> None:
        report = Report(
            exercise="machine_chest_press",
            exercise_display="Presse Pectorale Machine",
            score=79,
            report_text="RESUME\nExecution correcte.\nANALYSE REP PAR REP\n1. Rep 1 | 00:09 - 00:13 | Execution fluide.\n",
            model_used="minimax_motion_coach",
        )
        html, _, _ = generate_html_report(
            report=report,
            annotated_frames={},
            analysis_id="minimaxraw",
            pipeline_result=None,
            client_name="Client",
        )
        self.assertIn("Execution correcte.", html)
        self.assertIn("ANALYSE REP PAR REP", html)
        self.assertIn("Rep 1 | 00:09 - 00:13 | Execution fluide.", html)
        self.assertNotIn("PLAN D&#x27;ACTION", html)


if __name__ == "__main__":
    unittest.main()
