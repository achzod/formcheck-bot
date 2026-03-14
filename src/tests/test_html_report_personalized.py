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
        self.assertIn("Synthese de serie", html)
        self.assertNotIn("Salut Achzod", html)
        self.assertNotIn("Achzod Client", html)
        self.assertIn("Score global", html)
        self.assertIn("8 detectees", html)
        self.assertIn("Intensite et Densite", html)
        self.assertIn("Plan d&#x27;Action", html)

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
        self.assertIn("Analyse Rep par Rep", html)
        self.assertIn("Rep 1 | 00:09 - 00:13 | Execution fluide.", html)
        self.assertNotIn("Plan d&#x27;Action", html)

    def test_minimax_short_report_stays_source_first_without_local_analysis(self) -> None:
        report = Report(
            exercise="machine_chest_press",
            exercise_display="Presse Pectorale Machine",
            score=79,
            report_text="Analyse breve mais valide.",
            model_used="minimax_motion_coach",
        )
        html, _, _ = generate_html_report(
            report=report,
            annotated_frames={},
            analysis_id="minimaxshort",
            pipeline_result=None,
            client_name="Client",
        )
        self.assertIn("Analyse breve mais valide.", html)
        self.assertNotIn("Plan d&#x27;Action", html)
        self.assertNotIn("Intensite et Densite", html)

    def test_minimax_wrapper_and_frontmatter_are_not_rendered(self) -> None:
        report = Report(
            exercise="machine_chest_press",
            exercise_display="Presse Pectorale Machine",
            score=86,
            model_used="minimax_motion_coach",
            report_text=(
                "<FORMCHECK_REPORT_MD>\n"
                "FORMCHECK\n"
                "Exercice: Presse Pectorale Machine\n"
                "Exercice slug: machine_chest_press\n"
                "Confiance exercice: 0.95\n"
                "Score global: 86/100\n"
                "Repetitions detectees: 11\n"
                "Intensite: 85/100 (elevee)\n"
                "Repos inter-reps moyen: 0.00 s\n"
                "RESUME\n"
                "Execution propre et stable.\n"
                "ANALYSE REP PAR REP\n"
                "1. Rep 1 | 00:09 - 00:13 | Fluide.\n"
                "</FORMCHECK_REPORT_MD>\n"
            ),
        )
        html, _, _ = generate_html_report(
            report=report,
            annotated_frames={},
            analysis_id="minimaxclean",
            pipeline_result=None,
            client_name="Client",
        )
        self.assertNotIn("&lt;FORMCHECK_REPORT_MD&gt;", html)
        self.assertNotIn("Exercice slug: machine_chest_press", html)
        self.assertNotIn("Confiance exercice: 0.95", html)
        self.assertIn("Execution propre et stable.", html)
        self.assertIn("Analyse Rep par Rep", html)
        self.assertIn("11 detectees", html)
        self.assertIn("85 /100 (elevee)", html)
        self.assertIn("0.00s", html)
        self.assertIn("95%", html)

    def test_render_strips_cjk_noise_and_visible_dash_artifacts(self) -> None:
        report = Report(
            exercise="machine_chest_press",
            exercise_display="Presse Pectorale Machine",
            score=81,
            model_used="minimax_motion_coach",
            report_text=(
                "RESUME\n"
                "收到您的请求，我正在处理。\n"
                "--\n"
                "- Execution stable et propre.\n"
                "ANALYSE REP PAR REP\n"
                "1. Rep 1 | 00:09 - 00:13 | Fluide.\n"
                "PLAN ACTION\n"
                "-- Filme plus large\n"
                "- Ralentis la descente\n"
            ),
        )
        html, _, _ = generate_html_report(
            report=report,
            annotated_frames={},
            analysis_id="minimaxnoise",
            pipeline_result=None,
            client_name="Client",
        )
        self.assertNotIn("收到您的请求", html)
        self.assertIn("Execution stable et propre.", html)
        self.assertIn("Filme plus large", html)
        self.assertNotIn("-- Filme plus large", html)
        self.assertNotIn("Presse Pectorale Machine — score global", html)
        self.assertIn("Score global", html)
        self.assertIn("Presse Pectorale Machine", html)

    def test_correction_lines_are_rendered_as_structured_blocks(self) -> None:
        report = Report(
            exercise="lat_pulldown",
            exercise_display="Lat Pulldown (Tirage Vertical)",
            score=76,
            model_used="minimax_motion_coach",
            report_text=(
                "CORRECTIONS PRIORITAIRES\n"
                "1. Tempo excentrique | Descente trop rapide | Tu perds de la tension sur le grand dorsal | Garde 2 secondes de freinage\n"
            ),
        )
        html, _, _ = generate_html_report(
            report=report,
            annotated_frames={},
            analysis_id="corrblocks",
            pipeline_result=None,
            client_name="Client",
        )
        self.assertIn("Tempo excentrique", html)
        self.assertIn("Observation", html)
        self.assertIn("Impact", html)
        self.assertIn("Cue", html)
        self.assertIn("Garde 2 secondes de freinage", html)

    def test_malformed_minimax_frontmatter_does_not_break_report_delivery(self) -> None:
        report = Report(
            exercise="row",
            exercise_display="Row",
            score=73,
            model_used="minimax_motion_coach",
            report_text=(
                "<FORMCHECK_REPORT_MD>\n"
                "- Exercice: Row assis\n"
                "- Score global: NON MESURABLE\n"
                "- Confiance exercice: forte\n"
                "- Intensite: elevee\n"
                "RESUME\n"
                "Lecture exploitable avec un besoin de mieux freiner le retour.\n"
                "</FORMCHECK_REPORT_MD>\n"
            ),
        )
        html, _, _ = generate_html_report(
            report=report,
            annotated_frames={},
            analysis_id="minimaxmalformed",
            pipeline_result=None,
            client_name="Client",
        )
        self.assertIn("Row", html)
        self.assertIn("73/100", html)
        self.assertIn("Lecture exploitable", html)

    def test_intro_prefers_reconciled_report_exercise_over_raw_frontmatter_exercise(self) -> None:
        report = Report(
            exercise="machine_chest_press",
            exercise_display="Presse Pectorale Machine",
            score=78,
            model_used="minimax_motion_coach",
            report_text=(
                "<FORMCHECK_REPORT_MD>\n"
                "- Exercice: Leg Press\n"
                "- Score global: 55/100\n"
                "RESUME\n"
                "Execution stable.\n"
                "</FORMCHECK_REPORT_MD>\n"
            ),
        )
        html, _, _ = generate_html_report(
            report=report,
            annotated_frames={},
            analysis_id="introreconciled",
            pipeline_result=None,
            client_name="Client",
        )
        self.assertIn("Presse Pectorale Machine", html)
        self.assertNotIn("<strong>Leg Press</strong>", html)
        self.assertIn("78/100", html)


if __name__ == "__main__":
    unittest.main()
