from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from urllib.parse import quote

import httpx

# Keep pipeline imports testable without OpenCV runtime dependency.
if "cv2" not in sys.modules:
    sys.modules["cv2"] = types.ModuleType("cv2")

import analysis.minimax_motion_coach as mm
from analysis.minimax_motion_coach import (
    _MiniMaxClient,
    _SIGNING_SECRET,
    _UploadedAsset,
    _YY_SUFFIX,
    _cache_get,
    _cache_put,
    _extract_chat_candidates,
    _extract_agent_message,
    _extract_chat_name,
    _extract_message_text,
    _is_motion_coach_label,
    _resolve_target_chat_id,
    _is_retryable_minimax_error,
    _parse_analysis_payload,
    MiniMaxAnalysis,
    run_minimax_motion_coach,
    settings as minimax_settings,
)
from analysis.pipeline import PipelineResult, _apply_minimax_analysis_to_result


class MiniMaxSigningTests(unittest.TestCase):
    def test_signed_headers_match_js_formula(self) -> None:
        client = _MiniMaxClient(timeout_s=5)
        try:
            unix_ms = 1772618396000
            params = [("a", "1"), ("b", "2")]
            body = '{"x":1}'
            headers = client._signed_headers(
                "/matrix/api/v1/chat/send_msg",
                params,
                body,
                unix_ms,
            )
        finally:
            client.close()

        self.assertEqual(headers["x-timestamp"], "1772618396")

        expected_signature = hashlib.md5(
            "1772618396{}{}".format(_SIGNING_SECRET, body).encode("utf-8")
        ).hexdigest()
        self.assertEqual(headers["x-signature"], expected_signature)

        path_with_query = "/matrix/api/v1/chat/send_msg?a=1&b=2"
        encoded = quote(path_with_query, safe="")
        expected_yy = hashlib.md5(
            "{}_{}{}{}".format(
                encoded,
                body,
                hashlib.md5(str(unix_ms).encode("utf-8")).hexdigest(),
                _YY_SUFFIX,
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(headers["yy"], expected_yy)


class MiniMaxParsingTests(unittest.TestCase):
    def test_parse_tagged_markdown_report(self) -> None:
        text = """
<FORMCHECK_REPORT_MD>
# FORMCHECK
- Exercice: Presse pectorale machine
- Exercice slug: machine_chest_press
- Confiance exercice: 0.91
- Score global: 8/10
- Repetitions detectees: 7
- Repetitions completes: 7
- Repetitions partielles: 0
- Intensite: 74/100 (elevee)
- Repos inter-reps moyen: 1.25 s

## RESUME
Serie globalement propre mais avec une excentrique a mieux freiner.

## POINTS POSITIFS
- Bon ancrage scapulaire
- Trajectoire stable

## AMPLITUDE DE MOUVEMENT
Amplitude utile et complete sur la majorite de la serie.

## CORRECTIONS PRIORITAIRES
1. Tempo excentrique | Descente trop rapide | Perte de tension | Controle 2 secondes

## ANALYSE DU TEMPO ET DES PHASES
La phase excentrique manque un peu de maitrise en fin de serie.

## ANALYSE REP PAR REP
1. Rep 1 | 00:09 - 00:13 | Fluide et propre.
2. Rep 2 | 00:14 - 00:18 | Legere baisse de vitesse.

## INTENSITE DE SERIE
Serie dense avec peu de repos inter-reps.

## COMPENSATIONS ET BIOMECANIQUE AVANCEE
Legere perte de verrouillage scapulaire en fin de serie.

## DECOMPOSITION DU SCORE
- Securite: 31/40
- Efficacite technique: 24/30
- Controle et tempo: 17/20
- Symetrie: 8/10

## POINT BIOMECANIQUE
Pense a garder les omoplates fixes pendant toute la poussee.

## RECOMMANDATION POUR LA PROCHAINE VIDEO
Filme un peu plus large avec la machine complete visible.

## PLAN ACTION
- Ralentis la descente
- Garde la cage haute
- Filme plus large
</FORMCHECK_REPORT_MD>
        """.strip()
        out = _parse_analysis_payload(text)
        self.assertEqual(out.exercise_slug, "machine_chest_press")
        self.assertEqual(out.exercise_display, "Presse pectorale machine")
        self.assertEqual(out.score, 80)
        self.assertEqual(out.reps_total, 7)
        self.assertEqual(out.intensity_score, 74)
        self.assertEqual(out.intensity_label, "elevee")
        self.assertAlmostEqual(out.avg_inter_rep_rest_s, 1.25, places=2)
        self.assertEqual(out.score_breakdown.get("Symetrie"), 8)
        self.assertIn("## RESUME", out.report_text)
        self.assertIn("## PLAN ACTION", out.report_text)

    def test_extract_message_text_prefers_real_report_over_prompt_template(self) -> None:
        msg = {
            "msg_type": 2,
            "msg_content": {
                "text": "Analyse cette video de musculation comme un coach expert en biomecanique de la musculation.\nRapport Markdown attendu:\n# FORMCHECK\n- Exercice: nom exact en francais"
            },
            "answer": "<FORMCHECK_REPORT_MD>\n# FORMCHECK\n- Exercice: Presse pectorale machine\n- Exercice slug: machine_chest_press\n- Score global: 80/100\n</FORMCHECK_REPORT_MD>",
        }
        text = _extract_message_text(msg)
        self.assertIn("Presse pectorale machine", text)
        self.assertNotIn("Rapport Markdown attendu", text)

    def test_extract_chat_name_ignores_prompt_blob(self) -> None:
        payload = {
            "data": {
                "session_name": "Analyse cette video de musculation comme un coach expert en biomecanique de la musculation.\nRapport Markdown attendu:",
                "expert_name": "AI Motion Coach",
            }
        }
        self.assertEqual(_extract_chat_name(payload), "AI Motion Coach")

    def test_parse_structured_json_response(self) -> None:
        text = """
```json
{
  "exercise": {"name": "lat_pulldown", "display_name_fr": "Lat Pulldown (Tirage Vertical)", "confidence": 0.93},
  "score": 78,
  "reps": {"total": 8, "complete": 8, "partial": 0},
  "intensity": {"score": 76, "label": "elevee", "avg_inter_rep_rest_s": 0.92},
  "positives": ["Bon controle global"],
  "corrections": [{"title": "Tempo", "why": "Excentrique un peu rapide", "cue": "Controle la descente"}],
  "report_markdown": "Rapport complet."
}
```
        """.strip()
        out = _parse_analysis_payload(text)
        self.assertEqual(out.exercise_slug, "lat_pulldown")
        self.assertEqual(out.exercise_display, "Lat Pulldown (Tirage Vertical)")
        self.assertEqual(out.score, 78)
        self.assertEqual(out.reps_total, 8)
        self.assertEqual(out.intensity_score, 76)
        self.assertEqual(out.intensity_label, "elevee")
        self.assertAlmostEqual(out.avg_inter_rep_rest_s, 0.92, places=2)
        self.assertEqual(out.report_text, "Rapport complet.")

    def test_parse_structured_json_builds_sectioned_report_when_markdown_missing(self) -> None:
        text = """
{
  "exercise": {"name": "smith_military_press", "display_name_fr": "Developpe militaire Smith", "confidence": 0.88},
  "score": 81,
  "reps": {"total": 7, "complete": 7, "partial": 0},
  "intensity": {"score": 74, "label": "elevee", "avg_inter_rep_rest_s": 1.10},
  "positives": ["Bonne stabilite du tronc"],
  "corrections": [{"title": "Tempo excentrique", "why": "Descente trop rapide", "impact": "Perte de tension", "cue": "Controle 2 secondes"}],
  "sections": {
    "resume": "Execution globalement solide avec marge sur le controle de descente.",
    "rom": "Amplitude correcte sur la majorite des reps.",
    "tempo": "Concentrique puissante mais excentrique trop rapide.",
    "rep_par_rep": "1. Rep 1 | 00:09 - 00:13 | Execution fluide et controlee.\\n2. Rep 2 | 00:14 - 00:18 | Vitesse constante, bonne technique.",
    "intensite": "Serie dense avec repos courts.",
    "compensations": "Legere perte d'alignement en fin de serie.",
    "next_video": "Filme de profil, camera fixe a hauteur d'epaule."
  }
}
        """.strip()
        out = _parse_analysis_payload(text)
        self.assertEqual(out.exercise_slug, "smith_military_press")
        self.assertEqual(out.score, 81)
        self.assertEqual(out.reps_total, 7)
        self.assertIn("RESUME", out.report_text)
        self.assertIn("ANALYSE REP PAR REP", out.report_text)
        self.assertIn("DECOMPOSITION DU SCORE", out.report_text)
        self.assertIn("RECOMMANDATION POUR LA PROCHAINE VIDEO", out.report_text)

    def test_score_is_derived_from_complete_breakdown_when_total_conflicts(self) -> None:
        text = """
{
  "exercise": {"name": "machine_chest_press", "display_name_fr": "Presse pectorale machine", "confidence": 0.91},
  "score": 92,
  "reps": {"total": 7, "complete": 7, "partial": 0},
  "intensity": {"score": 79, "label": "elevee", "avg_inter_rep_rest_s": 1.25},
  "score_breakdown": {
    "Securite": 31,
    "Efficacite technique": 24,
    "Controle et tempo": 17,
    "Symetrie": 8
  }
}
        """.strip()
        out = _parse_analysis_payload(text)
        self.assertEqual(out.score_breakdown.get("Securite"), 31)
        self.assertEqual(out.score_breakdown.get("Efficacite technique"), 24)
        self.assertEqual(out.score_breakdown.get("Controle et tempo"), 17)
        self.assertEqual(out.score_breakdown.get("Symetrie"), 8)
        self.assertEqual(out.score, 80)

    def test_parse_labeled_breakdown_accepts_accented_french_labels(self) -> None:
        text = """
EXERCISE: machine_chest_press
DISPLAY_NAME_FR: Presse pectorale machine
CONFIDENCE: 0.91
SCORE: 99/100
REPS_TOTAL: 7
REPS_COMPLETE: 7
REPS_PARTIAL: 0
INTENSITY_SCORE: 79/100
INTENSITY_LABEL: elevee
AVG_INTER_REP_REST_S: 1.25
POINTS_POSITIFS:
- Bonne stabilite
CORRECTIONS_PRIORITAIRES:
1. Tempo | Descente un peu rapide | Perte de tension | Freine la descente
RESUME:
Serie propre.
AMPLITUDE_DE_MOUVEMENT:
Amplitude correcte.
ANALYSE_DU_TEMPO_ET_DES_PHASES:
Tempo un peu irregulier en fin de serie.
ANALYSE_REP_PAR_REP:
1. Rep 1 | 00:09 - 00:13 | Fluide.
INTENSITE_DE_SERIE:
Serie dense.
COMPENSATIONS_ET_BIOMECANIQUE_AVANCEE:
Legere asymetrie.
DECOMPOSITION_DU_SCORE:
- Sécurité: 31/40
- Efficacité technique: 24/30
- Contrôle et tempo: 17/20
- Symétrie: 8/10
POINT_BIOMECANIQUE:
Reste gainé.
RECOMMANDATION_POUR_LA_PROCHAINE_VIDEO:
Filme un peu plus large.
PLAN_ACTION:
- Controle mieux l'excentrique
        """.strip()
        out = _parse_analysis_payload(text)
        self.assertEqual(out.score_breakdown.get("Securite"), 31)
        self.assertEqual(out.score_breakdown.get("Efficacite technique"), 24)
        self.assertEqual(out.score_breakdown.get("Controle et tempo"), 17)
        self.assertEqual(out.score_breakdown.get("Symetrie"), 8)
        self.assertEqual(out.score, 80)

    def test_parse_regex_fallback_response(self) -> None:
        text = (
            "Lat Pulldown (Tirage Vertical) — 78/100 — 8 reps\n"
            "Intensite: 76/100 (elevee) — repos moyen 0.92s"
        )
        out = _parse_analysis_payload(text)
        self.assertEqual(out.exercise_display, "Lat Pulldown (Tirage Vertical)")
        self.assertEqual(out.score, 78)
        self.assertEqual(out.reps_total, 8)
        self.assertEqual(out.intensity_score, 76)
        self.assertEqual(out.intensity_label, "elevee")
        self.assertAlmostEqual(out.avg_inter_rep_rest_s, 0.92, places=2)

    def test_parse_unstructured_report_preserves_raw_report_text(self) -> None:
        text = """
Machine Chest Press
Tu as une bonne stabilite globale sur la machine et ton placement de dos est propre.
L'amplitude est correcte, mais tu acceleres trop la phase excentrique sur les deux dernieres repetitions.
On voit aussi une legere compensation de l'epaule droite quand la fatigue monte.
- Point fort: trajectoire globalement stable
- Correction: ralentis la descente et garde les coudes mieux alignes
        """.strip()
        out = _parse_analysis_payload(text)
        self.assertEqual(out.exercise_display, "Machine Chest Press")
        self.assertIn("bonne stabilite globale", out.report_text.lower())
        self.assertIn("correction: ralentis la descente", out.report_text.lower())

    def test_score_breakdown_is_clamped_per_category(self) -> None:
        text = """
{
  "exercise": {"name": "lat_pulldown", "display_name_fr": "Lat Pulldown", "confidence": 0.91},
  "score": 82,
  "reps": {"total": 8, "complete": 8, "partial": 0},
  "score_breakdown": {
    "Securite": 44,
    "Efficacite technique": 31,
    "Controle et tempo": 25,
    "Symetrie": 12
  }
}
        """.strip()
        out = _parse_analysis_payload(text)
        self.assertEqual(out.score_breakdown.get("Securite"), 40)
        self.assertEqual(out.score_breakdown.get("Efficacite technique"), 30)
        self.assertEqual(out.score_breakdown.get("Controle et tempo"), 20)
        self.assertEqual(out.score_breakdown.get("Symetrie"), 10)

    def test_score_breakdown_is_not_invented_when_absent(self) -> None:
        text = """
{
  "exercise": {"name": "machine_chest_press", "display_name_fr": "Presse Pectorale Machine", "confidence": 0.94},
  "score": 86,
  "reps": {"total": 10, "complete": 10, "partial": 0},
  "sections": {
    "resume": "Execution globalement solide.",
    "tempo": "Excentrique a ralentir sur les deux dernieres reps."
  }
}
        """.strip()
        out = _parse_analysis_payload(text)
        self.assertEqual(out.score_breakdown, {})
        self.assertIn("MiniMax n'a pas fourni de decomposition detaillee du score.", out.report_text)

    def test_parse_labeled_minimax_output(self) -> None:
        text = """
EXERCISE: incline_smith_machine_chest_press
DISPLAY_NAME_FR: Developpe incline a la Smith machine
CONFIDENCE: 0.94
SCORE: 94/100
REPS_TOTAL: 10
REPS_COMPLETE: 10
REPS_PARTIAL: 0
INTENSITY_SCORE: 78/100
INTENSITY_LABEL: elevee
AVG_INTER_REP_REST_S: 0.85
POINTS_POSITIFS:
- Trajectoire stable et reguliere
- Bonne symetrie sur toute la serie
CORRECTIONS_PRIORITAIRES:
1. Tempo excentrique | Descente un peu rapide sur les deux dernieres reps | Perte de tension pecs | Garde 2 secondes de descente
RESUME:
Serie globalement propre et bien controlee.
AMPLITUDE_DE_MOUVEMENT:
Amplitude complete sans verrouillage agressif.
ANALYSE_DU_TEMPO_ET_DES_PHASES:
Concentrique explosive mais excentrique a ralentir legerement.
ANALYSE_REP_PAR_REP:
1. Rep 1 | 00:09 - 00:13 | Execution fluide et controlee.
2. Rep 2 | 00:14 - 00:18 | Legere baisse de vitesse.
INTENSITE_DE_SERIE:
Intensite elevee avec peu de repos inter-reps.
COMPENSATIONS_ET_BIOMECANIQUE_AVANCEE:
Leger raccourcissement de l'amplitude en fin de serie.
DECOMPOSITION_DU_SCORE:
- Securite: 37/40
- Efficacite technique: 28/30
- Controle et tempo: 19/20
- Symetrie: 10/10
POINT_BIOMECANIQUE:
Le maintien scapulaire reste solide pendant la poussee.
RECOMMANDATION_POUR_LA_PROCHAINE_VIDEO:
Filme de trois quarts avant a hauteur de poitrine.
PLAN_ACTION:
- Ralentis l'excentrique a 2 secondes
- Garde la cage haute
- Filme avec la machine entiere visible
        """.strip()
        out = _parse_analysis_payload(text)
        self.assertEqual(out.exercise_slug, "incline_smith_machine_chest_press")
        self.assertEqual(out.exercise_display, "Developpe incline a la Smith machine")
        self.assertEqual(out.score, 94)
        self.assertEqual(out.reps_total, 10)
        self.assertEqual(out.intensity_score, 78)
        self.assertEqual(out.intensity_label, "elevee")
        self.assertAlmostEqual(out.avg_inter_rep_rest_s, 0.85, places=2)
        self.assertEqual(out.score_breakdown.get("Securite"), 37)
        self.assertIn("AMPLITUDE DE MOUVEMENT", out.report_text)
        self.assertIn("PLAN ACTION", out.report_text)


class MiniMaxBrowserLaunchOptionsTests(unittest.TestCase):
    def test_browser_launch_options_include_channel_when_configured(self) -> None:
        original = getattr(minimax_settings, "minimax_browser_channel", "")
        try:
            minimax_settings.minimax_browser_channel = "chrome"
            options = mm._browser_launch_options(headless=True)
        finally:
            minimax_settings.minimax_browser_channel = original

        self.assertEqual(options.get("channel"), "chrome")

    def test_browser_launch_options_omit_channel_when_empty(self) -> None:
        original = getattr(minimax_settings, "minimax_browser_channel", "")
        try:
            minimax_settings.minimax_browser_channel = ""
            options = mm._browser_launch_options(headless=True)
        finally:
            minimax_settings.minimax_browser_channel = original

        self.assertNotIn("channel", options)

    def test_browser_launch_options_minimize_headed_chrome(self) -> None:
        options = mm._browser_launch_options(headless=False)
        args = options.get("args", [])
        self.assertIn("--start-minimized", args)
        self.assertIn("--window-position=-2400,0", args)
        self.assertIn("--window-size=1440,1100", args)


class MiniMaxVideoStatsTests(unittest.TestCase):
    def test_video_stats_falls_back_to_ffprobe_when_cv2_returns_zeros(self) -> None:
        fake_cv2 = types.SimpleNamespace(
            CAP_PROP_FPS=5,
            CAP_PROP_FRAME_COUNT=7,
            CAP_PROP_FRAME_WIDTH=3,
            CAP_PROP_FRAME_HEIGHT=4,
        )

        class _FakeCapture:
            def __init__(self, _path):
                pass

            def get(self, _prop):
                return 0.0

            def release(self):
                return None

        fake_cv2.VideoCapture = _FakeCapture

        ffprobe_payload = json.dumps(
            {
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 848,
                        "height": 480,
                        "avg_frame_rate": "600/19",
                        "duration": "56.215510",
                    }
                ],
                "format": {"duration": "56.215510"},
            }
        )

        original_cv2 = sys.modules.get("cv2")
        original_run = mm.subprocess.run
        try:
            sys.modules["cv2"] = fake_cv2

            def _fake_run(cmd, capture_output=False, text=False, timeout=0):
                self.assertIn("ffprobe", cmd[0])
                return types.SimpleNamespace(returncode=0, stdout=ffprobe_payload)

            mm.subprocess.run = _fake_run  # type: ignore[assignment]
            stats = mm._video_stats("/tmp/video.mp4")
        finally:
            mm.subprocess.run = original_run  # type: ignore[assignment]
            if original_cv2 is not None:
                sys.modules["cv2"] = original_cv2
            else:
                sys.modules.pop("cv2", None)

        self.assertAlmostEqual(stats["duration_s"], 56.215510, places=3)
        self.assertAlmostEqual(stats["fps"], 600 / 19, places=4)
        self.assertEqual(stats["width"], 848)
        self.assertEqual(stats["height"], 480)


class MiniMaxBrowserConfigValidationTests(unittest.TestCase):
    def test_validate_settings_allows_seeded_browser_profile_without_password(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir) / "profile"
            default_dir = profile_dir / "Default"
            default_dir.mkdir(parents=True)
            (default_dir / "Preferences").write_text("{}", encoding="utf-8")
            original = {
                "email": minimax_settings.minimax_browser_email,
                "password": minimax_settings.minimax_browser_password,
                "profile_dir": minimax_settings.minimax_browser_profile_dir,
                "local": minimax_settings.minimax_browser_local_storage_json,
                "session": minimax_settings.minimax_browser_session_storage_json,
                "cookie": minimax_settings.minimax_cookie,
            }
            try:
                minimax_settings.minimax_browser_email = "achzodyt@gmail.com"
                minimax_settings.minimax_browser_password = ""
                minimax_settings.minimax_browser_profile_dir = str(profile_dir)
                minimax_settings.minimax_browser_local_storage_json = ""
                minimax_settings.minimax_browser_session_storage_json = ""
                minimax_settings.minimax_cookie = ""
                self.assertEqual(mm._validate_settings(), [])
            finally:
                minimax_settings.minimax_browser_email = original["email"]
                minimax_settings.minimax_browser_password = original["password"]
                minimax_settings.minimax_browser_profile_dir = original["profile_dir"]
                minimax_settings.minimax_browser_local_storage_json = original["local"]
                minimax_settings.minimax_browser_session_storage_json = original["session"]
                minimax_settings.minimax_cookie = original["cookie"]

    def test_validate_settings_requires_password_or_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir) / "empty-profile"
            profile_dir.mkdir(parents=True)
            original = {
                "email": minimax_settings.minimax_browser_email,
                "password": minimax_settings.minimax_browser_password,
                "profile_dir": minimax_settings.minimax_browser_profile_dir,
                "local": minimax_settings.minimax_browser_local_storage_json,
                "session": minimax_settings.minimax_browser_session_storage_json,
                "cookie": minimax_settings.minimax_cookie,
            }
            try:
                minimax_settings.minimax_browser_email = "achzodyt@gmail.com"
                minimax_settings.minimax_browser_password = ""
                minimax_settings.minimax_browser_profile_dir = str(profile_dir)
                minimax_settings.minimax_browser_local_storage_json = ""
                minimax_settings.minimax_browser_session_storage_json = ""
                minimax_settings.minimax_cookie = ""
                self.assertEqual(mm._validate_settings(), ["minimax_browser_password_or_browser_auth_seed"])
            finally:
                minimax_settings.minimax_browser_email = original["email"]
                minimax_settings.minimax_browser_password = original["password"]
                minimax_settings.minimax_browser_profile_dir = original["profile_dir"]
                minimax_settings.minimax_browser_local_storage_json = original["local"]
                minimax_settings.minimax_browser_session_storage_json = original["session"]
                minimax_settings.minimax_cookie = original["cookie"]

    def test_parse_labeled_output_embedded_in_thinking_process(self) -> None:
        text = (
            "Thinking Process The user wants me to analyze a workout video. "
            "Let me compile the analysis report in the exact format requested: "
            "_ EXERCISE: smith_machine_incline_bench_press "
            "DISPLAY_NAME_FR: Developpe couche incline a la machine Smith "
            "CONFIDENCE: 0.85 SCORE: 78/100 REPS_TOTAL: 10 REPS_COMPLETE: 10 REPS_PARTIAL: 0 "
            "INTENSITY_SCORE: 75/100 INTENSITY_LABEL: elevee AVG_INTER_REP_REST_S: 0.97_ "
            "POINTS_POSITIFS:_ Positionnement excellent des epaules "
            "CORRECTIONS_PRIORITAIRES:_ 1. Tempo excentrique | Descente un peu rapide | Perte de tension | Controle 2 secondes "
            "RESUME:_ Serie propre et reguliere "
            "AMPLITUDE_DE_MOUVEMENT:_ Amplitude complete "
            "ANALYSE_DU_TEMPO_ET_DES_PHASES:_ Tempo globalement controle "
            "INTENSITE_DE_SERIE:_ Intensite elevee avec peu de repos "
            "COMPENSATIONS_ET_BIOMECANIQUE_AVANCEE:_ Legere baisse de vitesse en fin de serie "
            "DECOMPOSITION_DU_SCORE:_ - Securite: 32/40 - Efficacite technique: 24/30 - Controle et tempo: 15/20 - Symetrie: 7/10 "
            "POINT_BIOMECANIQUE:_ Bon ancrage scapulaire "
            "RECOMMANDATION_POUR_LA_PROCHAINE_VIDEO:_ Filme de trois quarts avant "
            "PLAN_ACTION:_ - Ralentis la descente - Garde la cage haute - Filme plus large"
        )
        out = _parse_analysis_payload(text)
        self.assertEqual(out.exercise_slug, "smith_machine_incline_bench_press")
        self.assertEqual(out.score, 78)
        self.assertEqual(out.reps_total, 10)
        self.assertEqual(out.intensity_score, 75)
        self.assertEqual(out.intensity_label, "elevee")
        self.assertAlmostEqual(out.avg_inter_rep_rest_s, 0.97, places=2)
        self.assertIn("resume", out.sections)
        self.assertEqual(out.score_breakdown.get("Symetrie"), 7)


class MiniMaxMessageExtractionTests(unittest.TestCase):
    def test_analysis_candidate_filter_rejects_generic_welcome(self) -> None:
        self.assertFalse(
            mm._is_analysis_candidate_text(
                "Bonjour ! Je suis ravi de vous accompagner en tant que coach biomecanique expert."
            )
        )
        self.assertTrue(
            mm._is_analysis_candidate_text(
                '{"exercise":{"name":"lat_pulldown"},"score":78,"reps":{"total":8},"intensity":{"score":76}}'
            )
        )

    def test_analysis_candidate_filter_rejects_thinking_process(self) -> None:
        self.assertFalse(
            mm._is_analysis_candidate_text(
                "Thinking Process 3.47s Je vais analyser cette vidéo pour un rapport biomécanique complet. "
                "Je commence par extraire les images clés de la vidéo."
            )
        )
        self.assertFalse(
            mm._is_analysis_candidate_text(
                "Completed Skill expert-skills:frame-extraction Thinking Process The user wants me to extract "
                "frames from a video file and then run motion analysis."
            )
        )

    def test_analysis_candidate_filter_accepts_labeled_final_output(self) -> None:
        self.assertTrue(
            mm._is_analysis_candidate_text(
                "EXERCISE: machine_chest_press\nDISPLAY_NAME_FR: Presse pectorale machine\n"
                "SCORE: 88/100\nREPS_TOTAL: 9\nPLAN_ACTION:\n- Controle la descente"
            )
        )

    def test_analysis_candidate_filter_accepts_tagged_markdown_report(self) -> None:
        self.assertTrue(
            mm._is_analysis_candidate_text(
                "<FORMCHECK_REPORT_MD>\n# FORMCHECK\n- Exercice: Presse pectorale machine\n"
                "- Score global: 82/100\n- Repetitions detectees: 9\n## RESUME\nSerie propre.\n"
                "## PLAN ACTION\n- Controle la descente\n</FORMCHECK_REPORT_MD>"
            )
        )

    def test_unstructured_report_text_detector_accepts_real_analysis(self) -> None:
        self.assertTrue(
            mm._looks_like_unstructured_report_text(
                "Tu as une bonne posture de depart et une amplitude cohérente. "
                "La phase excentrique est trop rapide sur les dernières répétitions. "
                "On voit une compensation d'épaule quand la fatigue monte, ce qui dégrade l'alignement. "
                "- Point fort: stabilité du tronc\n- Correction: ralentis la descente"
            )
        )

    def test_unstructured_report_text_detector_rejects_english_process_output(self) -> None:
        self.assertFalse(
            mm._looks_like_unstructured_report_text(
                "The extract_frames.py script doesn't exist. Let me check what's in the skills directory "
                "and find an alternative way to extract frames. I can use ffmpeg directly to extract frames "
                "from the video."
            )
        )

    def test_analysis_candidate_filter_rejects_thinking_process_with_markdown_instructions(self) -> None:
        self.assertFalse(
            mm._is_analysis_candidate_text(
                "Thinking Process Je dois respecter le format final entre <FORMCHECK_REPORT_MD> et "
                "</FORMCHECK_REPORT_MD>. # FORMCHECK - Exercice: nom exact - Score global: 0/100 "
                "## RESUME 3 a 5 phrases ## PLAN ACTION - action 1"
            )
        )

    def test_extract_agent_message_ignores_known_ids(self) -> None:
        payload = {
            "data": {
                "chat_status": 2,
                "messages": [
                    {"msg_id": "1", "msg_type": 1, "msg_content": "user prompt", "timestamp": 1},
                    {"msg_id": "2", "msg_type": 2, "msg_content": "old agent", "timestamp": 2},
                    {"msg_id": "3", "msg_type": 2, "msg_content": "new agent", "timestamp": 3},
                ],
            }
        }
        text, ids, chat_status = _extract_agent_message(payload, known_message_ids={"1", "2"})
        self.assertEqual(text, "new agent")
        self.assertEqual(chat_status, 2)
        self.assertIn("3", ids)

    def test_extract_agent_message_accepts_non_user_types_and_nested_content(self) -> None:
        payload = {
            "data": {
                "chat_status": 1,
                "messages": [
                    {
                        "msg_id": "10",
                        "msg_type": 1,
                        "msg_content": "user prompt",
                        "timestamp": 10,
                    },
                    {
                        "msg_id": "11",
                        "msg_type": 12,
                        "msg_content": {
                            "payload": {
                                "segments": [
                                    {"text": "Rapport MiniMax complet: 8 reps detectees."}
                                ]
                            }
                        },
                        "timestamp": 11,
                    },
                ],
            }
        }
        text, ids, chat_status = _extract_agent_message(payload, known_message_ids={"10"})
        self.assertEqual(chat_status, 1)
        self.assertIn("11", ids)
        self.assertIn("Rapport MiniMax complet", text)


class MiniMaxTargetChatResolutionTests(unittest.TestCase):
    def test_motion_coach_keyword_match(self) -> None:
        self.assertTrue(_is_motion_coach_label("AI Motion Coach"))
        self.assertTrue(_is_motion_coach_label("Video Motion Analysis Assistant"))
        self.assertFalse(_is_motion_coach_label("Marketing Copilot"))

    def test_extract_chat_candidates(self) -> None:
        payload = {
            "data": {
                "sessions": [
                    {"chat_id": 1, "chat_name": "General Chat"},
                    {"chat_id": 2, "title": "AI Motion Coach"},
                ]
            }
        }
        out = _extract_chat_candidates(payload)
        self.assertIn(("1", "General Chat"), out)
        self.assertIn(("2", "AI Motion Coach"), out)

    def test_resolve_target_chat_prefers_motion_coach_from_list_chat(self) -> None:
        class _DummyClient:
            @staticmethod
            def request(method: str, path: str, *, payload=None):
                assert method == "POST"
                assert path == "/matrix/api/v1/chat/list_chat"
                return {
                    "data": {
                        "sessions": [
                            {"chat_id": 77, "chat_name": "General"},
                            {"chat_id": 88, "chat_name": "AI Motion Coach"},
                        ]
                    }
                }

        old_prefer = minimax_settings.minimax_prefer_motion_coach_chat
        minimax_settings.minimax_prefer_motion_coach_chat = True
        try:
            chat_id, name, source = _resolve_target_chat_id(_DummyClient(), configured_chat_id="42")
        finally:
            minimax_settings.minimax_prefer_motion_coach_chat = old_prefer
        self.assertEqual(chat_id, "88")
        self.assertEqual(name, "AI Motion Coach")
        self.assertEqual(source, "list_chat_motion_match")


class MiniMaxPipelineMappingTests(unittest.TestCase):
    def test_pipeline_mapping_from_minimax_analysis(self) -> None:
        base = PipelineResult(video_path="video.mp4", output_dir="out")
        analysis = MiniMaxAnalysis(
            exercise_slug="lat_pulldown",
            exercise_display="Lat Pulldown (Tirage Vertical)",
            exercise_confidence=0.91,
            score=82,
            reps_total=9,
            reps_complete=9,
            reps_partial=0,
            intensity_score=74,
            intensity_label="elevee",
            avg_inter_rep_rest_s=1.02,
            report_text="Rapport MiniMax",
        )
        out = _apply_minimax_analysis_to_result(base, analysis)
        self.assertIsNotNone(out.report)
        self.assertIsNotNone(out.reps)
        self.assertIsNotNone(out.detection)
        assert out.report is not None
        assert out.reps is not None
        assert out.detection is not None
        self.assertEqual(out.report.score, 82)
        self.assertEqual(out.report.exercise_display, "Lat Pulldown (Tirage Vertical)")
        self.assertEqual(out.reps.total_reps, 9)
        self.assertEqual(out.reps.intensity_score, 74)
        self.assertEqual(out.detection.exercise.value, "lat_pulldown")

    def test_pipeline_mapping_prefers_display_when_slug_conflicts(self) -> None:
        base = PipelineResult(video_path="video.mp4", output_dir="out")
        analysis = MiniMaxAnalysis(
            exercise_slug="leg_press",
            exercise_display="Presse Pectorale Machine",
            exercise_confidence=0.90,
            score=80,
            reps_total=10,
            reps_complete=10,
            reps_partial=0,
            intensity_score=71,
            intensity_label="elevee",
            avg_inter_rep_rest_s=0.9,
            report_text="Rapport MiniMax",
        )
        out = _apply_minimax_analysis_to_result(base, analysis)
        assert out.detection is not None
        self.assertEqual(out.detection.exercise.value, "machine_chest_press")

    def test_pipeline_mapping_handles_freeform_minimax_machine_shoulder_slug(self) -> None:
        base = PipelineResult(video_path="video.mp4", output_dir="out")
        analysis = MiniMaxAnalysis(
            exercise_slug="developpe_epaules_machine_convergente",
            exercise_display="Développé épaules à la machine convergente",
            exercise_confidence=0.90,
            score=91,
            reps_total=8,
            reps_complete=8,
            reps_partial=0,
            intensity_score=90,
            intensity_label="tres elevee",
            avg_inter_rep_rest_s=0.2,
            report_text="Rapport MiniMax",
        )
        out = _apply_minimax_analysis_to_result(base, analysis)
        assert out.detection is not None
        self.assertEqual(out.detection.exercise.value, "ohp")

    def test_pipeline_mapping_handles_freeform_minimax_machine_chest_slug(self) -> None:
        base = PipelineResult(video_path="video.mp4", output_dir="out")
        analysis = MiniMaxAnalysis(
            exercise_slug="chest_press_machine",
            exercise_display="Développé Couché à la Machine (Hammer Strength)",
            exercise_confidence=0.95,
            score=90,
            reps_total=10,
            reps_complete=10,
            reps_partial=0,
            intensity_score=75,
            intensity_label="moderee",
            avg_inter_rep_rest_s=4.0,
            report_text="Rapport MiniMax",
        )
        out = _apply_minimax_analysis_to_result(base, analysis)
        assert out.detection is not None
        self.assertEqual(out.detection.exercise.value, "machine_chest_press")


class MiniMaxCacheTests(unittest.TestCase):
    def test_cache_roundtrip_returns_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            old_path = minimax_settings.minimax_cache_path
            old_enabled = minimax_settings.minimax_enable_cache
            old_ttl = minimax_settings.minimax_cache_ttl_hours
            minimax_settings.minimax_cache_path = "{}/cache.sqlite".format(tmpdir)
            minimax_settings.minimax_enable_cache = True
            minimax_settings.minimax_cache_ttl_hours = 24
            try:
                analysis = MiniMaxAnalysis(
                    exercise_slug="squat",
                    exercise_display="Back Squat",
                    score=82,
                    reps_total=9,
                    intensity_score=70,
                    report_text="Test report",
                )
                _cache_put("video_hash_1", "prompt_hash_1", analysis)
                loaded = _cache_get("video_hash_1", "prompt_hash_1")
                self.assertIsNotNone(loaded)
                assert loaded is not None
                self.assertEqual(loaded.exercise_slug, "squat")
                self.assertEqual(loaded.reps_total, 9)
                self.assertTrue(bool(loaded.metadata.get("cache_hit")))
            finally:
                minimax_settings.minimax_cache_path = old_path
                minimax_settings.minimax_enable_cache = old_enabled
                minimax_settings.minimax_cache_ttl_hours = old_ttl


class MiniMaxPayloadContractTests(unittest.TestCase):
    def test_send_video_message_uses_minimal_payload_contract(self) -> None:
        client = _MiniMaxClient(timeout_s=5)
        captured: dict[str, object] = {}

        def _fake_request(method: str, path: str, *, payload=None):
            captured["method"] = method
            captured["path"] = path
            captured["payload"] = payload
            return {"data": {}}

        client.request = _fake_request  # type: ignore[assignment]
        try:
            asset = _UploadedAsset(
                file_id="123",
                file_url="https://cdn.example.com/video.mp4",
                object_key="dir/video.mp4",
                upload_uuid="uuid",
            )
            client.send_video_message(
                chat_id="42",
                prompt="Analyse cette video",
                asset=asset,
                origin_file_name="video.mp4",
            )
        finally:
            client.close()

        self.assertEqual(captured.get("method"), "POST")
        self.assertEqual(captured.get("path"), "/matrix/api/v1/chat/send_msg")
        payload = captured.get("payload")
        self.assertIsInstance(payload, dict)
        assert isinstance(payload, dict)
        self.assertIn("attachments", payload)
        self.assertIn("chat_id", payload)
        self.assertIn("chat_type", payload)
        self.assertIn("msg_type", payload)
        self.assertIn("text", payload)
        self.assertNotIn("website_selection", payload)
        self.assertNotIn("backend_config", payload)
        self.assertNotIn("selected_mcp_tools", payload)


class MiniMaxRetryTests(unittest.TestCase):
    def test_retryable_error_classifier(self) -> None:
        self.assertTrue(_is_retryable_minimax_error(TimeoutError("timeout")))
        self.assertTrue(_is_retryable_minimax_error(RuntimeError("MiniMax HTTP 503: upstream")))
        self.assertTrue(_is_retryable_minimax_error(RuntimeError("MiniMax HTTP 429: rate limited")))
        self.assertFalse(
            _is_retryable_minimax_error(
                RuntimeError("MiniMax API error 1400010161: not enough credits")
            )
        )
        self.assertFalse(
            _is_retryable_minimax_error(
                RuntimeError("MiniMax configuration incomplete: minimax_token")
            )
        )

    def test_request_retries_on_transient_timeout(self) -> None:
        client = _MiniMaxClient(timeout_s=5)
        client._request_max_attempts = 2  # type: ignore[attr-defined]
        client._retry_backoff_s = 0.01  # type: ignore[attr-defined]
        calls = {"count": 0}

        class _FakeResponse:
            status_code = 200

            @staticmethod
            def raise_for_status() -> None:
                return None

            @staticmethod
            def json() -> dict:
                return {"data": {"ok": True}}

        def _fake_request(**kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                raise httpx.ReadTimeout("boom")
            return _FakeResponse()

        client.client.request = _fake_request  # type: ignore[assignment]
        client._ensure_scraper = lambda: None  # type: ignore[assignment]
        try:
            out = client.request("GET", "/matrix/api/v1/chat/get_chat_detail")
        finally:
            client.close()

        self.assertEqual(calls["count"], 2)
        self.assertEqual(out.get("data", {}).get("ok"), True)


class MiniMaxBrowserAuthFlowTests(unittest.TestCase):
    def test_upload_and_send_retries_after_login_modal_blocks_send(self) -> None:
        calls = {"populate": 0, "send": 0, "auth": 0, "reopen": 0}
        login_modal_states = iter([False, True, False, False])

        original_populate = mm._populate_browser_message
        original_send = mm._send_browser_message
        original_login_modal_visible = mm._login_modal_visible
        original_ensure_auth = mm._ensure_browser_authenticated
        original_locator_visible = mm._locator_is_visible
        original_open_motion_coach_chat = mm._open_motion_coach_chat
        try:
            mm._populate_browser_message = lambda *_args, **_kwargs: calls.__setitem__(  # type: ignore[assignment]
                "populate", calls["populate"] + 1
            )

            def _fake_send(*_args, **_kwargs):
                calls["send"] += 1
                if calls["send"] == 1:
                    raise RuntimeError("MiniMax browser flow blocked by login modal after send")
                return None

            mm._send_browser_message = _fake_send  # type: ignore[assignment]
            mm._login_modal_visible = lambda *_args, **_kwargs: next(login_modal_states)  # type: ignore[assignment]
            mm._ensure_browser_authenticated = lambda *_args, **_kwargs: calls.__setitem__(  # type: ignore[assignment]
                "auth", calls["auth"] + 1
            )
            mm._locator_is_visible = lambda *_args, **_kwargs: True  # type: ignore[assignment]
            mm._open_motion_coach_chat = lambda *_args, **_kwargs: calls.__setitem__(  # type: ignore[assignment]
                "reopen", calls["reopen"] + 1
            )

            mm._upload_and_send_via_browser(
                object(),
                "video.mp4",
                "Analyse cette video",
                3000,
                email="coaching@achzodcoaching.com",
                password="secret",
            )
        finally:
            mm._populate_browser_message = original_populate  # type: ignore[assignment]
            mm._send_browser_message = original_send  # type: ignore[assignment]
            mm._login_modal_visible = original_login_modal_visible  # type: ignore[assignment]
            mm._ensure_browser_authenticated = original_ensure_auth  # type: ignore[assignment]
            mm._locator_is_visible = original_locator_visible  # type: ignore[assignment]
            mm._open_motion_coach_chat = original_open_motion_coach_chat  # type: ignore[assignment]

        self.assertEqual(calls["populate"], 2)
        self.assertEqual(calls["send"], 2)
        self.assertEqual(calls["auth"], 1)
        self.assertEqual(calls["reopen"], 0)

    def test_upload_and_send_retries_after_send_button_stays_disabled(self) -> None:
        calls = {"populate": 0, "send": 0, "auth": 0}

        original_populate = mm._populate_browser_message
        original_send = mm._send_browser_message
        original_login_modal_visible = mm._login_modal_visible
        original_ensure_auth = mm._ensure_browser_authenticated
        original_locator_visible = mm._locator_is_visible
        try:
            mm._populate_browser_message = lambda *_args, **_kwargs: calls.__setitem__(  # type: ignore[assignment]
                "populate", calls["populate"] + 1
            )

            def _fake_send(*_args, **_kwargs):
                calls["send"] += 1
                if calls["send"] == 1:
                    raise RuntimeError("MiniMax browser flow failed: send button stayed disabled")
                return None

            mm._send_browser_message = _fake_send  # type: ignore[assignment]
            mm._login_modal_visible = lambda *_args, **_kwargs: False  # type: ignore[assignment]
            mm._ensure_browser_authenticated = lambda *_args, **_kwargs: calls.__setitem__(  # type: ignore[assignment]
                "auth", calls["auth"] + 1
            )
            mm._locator_is_visible = lambda *_args, **_kwargs: True  # type: ignore[assignment]

            mm._upload_and_send_via_browser(
                object(),
                "video.mp4",
                "Analyse cette video",
                3000,
                email="coaching@achzodcoaching.com",
                password="secret",
            )
        finally:
            mm._populate_browser_message = original_populate  # type: ignore[assignment]
            mm._send_browser_message = original_send  # type: ignore[assignment]
            mm._login_modal_visible = original_login_modal_visible  # type: ignore[assignment]
            mm._ensure_browser_authenticated = original_ensure_auth  # type: ignore[assignment]
            mm._locator_is_visible = original_locator_visible  # type: ignore[assignment]

        self.assertEqual(calls["populate"], 2)
        self.assertEqual(calls["send"], 2)
        self.assertEqual(calls["auth"], 1)

    def test_google_login_waits_for_authenticated_minimax_page(self) -> None:
        class _FakeLocator:
            def __init__(self, page, selector: str):
                self._page = page
                self._selector = selector

            @property
            def first(self):
                return self

            def count(self) -> int:
                if self._page.kind == "origin" and self._selector == "button:has-text('Continue with Google')":
                    return 1
                if self._page.kind == "google" and self._selector == "input[type='password']":
                    return 1
                return 0

            def is_visible(self, timeout=None) -> bool:
                return self.count() > 0

            def click(self, timeout=None) -> None:
                return None

            def fill(self, value: str, timeout=None) -> None:
                return None

            def press(self, key: str) -> None:
                return None

        class _FakeContext:
            def __init__(self, pages):
                self.pages = pages

        class _FakePage:
            def __init__(self, kind: str, url: str):
                self.kind = kind
                self.url = url
                self.context = None
                self.brought_to_front = False

            def locator(self, selector: str):
                return _FakeLocator(self, selector)

            def wait_for_timeout(self, _ms: int) -> None:
                return None

            def bring_to_front(self) -> None:
                self.brought_to_front = True

        origin = _FakePage("origin", "https://agent.minimax.io/expert/chat/362683345551702")
        google = _FakePage("google", "https://accounts.google.com/signin/v2/challenge")
        authed = _FakePage("authed", "https://agent.minimax.io/chat?id=123")
        ctx = _FakeContext([origin, google, authed])
        origin.context = ctx
        google.context = ctx
        authed.context = ctx

        original_locator_visible = mm._locator_is_visible
        original_click_first = mm._click_first_visible
        try:
            def _fake_locator_visible(page, selector: str, timeout_ms: int = 1200) -> bool:
                if page is origin and selector == "button:has-text('Continue with Google')":
                    return True
                if page is origin and selector == ".tiptap-editor":
                    return True
                if page is origin and selector in (
                    "button:has-text('Continue with Google')",
                    "text=Welcome to MiniMax",
                ):
                    return True
                if page is authed and selector == ".tiptap-editor":
                    return True
                return False

            def _fake_click_first(page, selectors: tuple[str, ...], timeout_ms: int = 2500) -> bool:
                if page is google and "button:has-text('Continue')" in selectors:
                    google.url = "https://agent.minimax.io/oauth-complete"
                    return True
                return False

            mm._locator_is_visible = _fake_locator_visible  # type: ignore[assignment]
            mm._click_first_visible = _fake_click_first  # type: ignore[assignment]

            mm._login_with_google_if_needed(
                origin,
                email="coaching@achzodcoaching.com",
                password="secret",
                timeout_ms=3000,
            )
        finally:
            mm._locator_is_visible = original_locator_visible  # type: ignore[assignment]
            mm._click_first_visible = original_click_first  # type: ignore[assignment]

        self.assertFalse(origin.brought_to_front)
        self.assertTrue(authed.brought_to_front)

    def test_open_motion_coach_chat_uses_direct_expert_cta_before_experts_search(self) -> None:
        class _FakePage:
            def __init__(self):
                self.goto_calls: list[str] = []
                self.waited_for_selector = False

            def goto(self, url: str, **_kwargs) -> None:
                self.goto_calls.append(url)

            def wait_for_selector(self, selector: str, timeout=None) -> None:
                if selector == ".tiptap-editor":
                    self.waited_for_selector = True
                    return None
                raise AssertionError("unexpected selector")

        page = _FakePage()
        original_composer_ready = mm._motion_coach_composer_ready
        original_cta_present = mm._motion_coach_cta_present
        original_click_cta = mm._click_motion_coach_cta
        original_wait_for_page_condition = mm._wait_for_page_condition
        try:
            mm._motion_coach_composer_ready = lambda *_args, **_kwargs: False  # type: ignore[assignment]
            mm._motion_coach_cta_present = lambda *_args, **_kwargs: True  # type: ignore[assignment]
            mm._click_motion_coach_cta = lambda *_args, **_kwargs: True  # type: ignore[assignment]
            mm._wait_for_page_condition = lambda _page, predicate, timeout_ms, step_ms=350: bool(predicate())  # type: ignore[assignment]

            mm._open_motion_coach_chat(page, timeout_ms=3000)
        finally:
            mm._motion_coach_composer_ready = original_composer_ready  # type: ignore[assignment]
            mm._motion_coach_cta_present = original_cta_present  # type: ignore[assignment]
            mm._click_motion_coach_cta = original_click_cta  # type: ignore[assignment]
            mm._wait_for_page_condition = original_wait_for_page_condition  # type: ignore[assignment]

        self.assertEqual(page.goto_calls, [mm._motion_coach_expert_url()])
        self.assertTrue(page.waited_for_selector)

    def test_click_motion_coach_cta_uses_accessible_button_role_fallback(self) -> None:
        class _FakeLocator:
            def __init__(self):
                self.clicked = False

            @property
            def first(self):
                return self

            def count(self) -> int:
                return 1

            def click(self, timeout=None) -> None:
                self.clicked = True

        class _FakeMissingText:
            @property
            def first(self):
                return self

            def count(self) -> int:
                return 0

            def click(self, timeout=None) -> None:
                raise AssertionError("should not click missing text locator")

        class _FakePage:
            def __init__(self):
                self.role_locator = _FakeLocator()

            def get_by_role(self, role: str, name=None):
                if role == "button":
                    return self.role_locator
                raise AssertionError("unexpected role")

            def get_by_text(self, text: str, exact=False):
                return _FakeMissingText()

        page = _FakePage()
        original_click_first = mm._click_first_visible
        try:
            mm._click_first_visible = lambda *_args, **_kwargs: False  # type: ignore[assignment]
            out = mm._click_motion_coach_cta(page, timeout_ms=3000)
        finally:
            mm._click_first_visible = original_click_first  # type: ignore[assignment]

        self.assertTrue(out)
        self.assertTrue(page.role_locator.clicked)

    def test_focus_browser_editor_uses_dom_fallback_when_click_is_blocked(self) -> None:
        class _FakeEditor:
            def __init__(self):
                self.evaluate_called = False
                self.force_click_attempted = False

            def click(self, timeout=None, force=False) -> None:
                if force:
                    self.force_click_attempted = True
                    return None
                raise RuntimeError("pointer events intercepted by overlay")

            def evaluate(self, script: str, arg=None) -> None:
                self.evaluate_called = True
                return None

        editor = _FakeEditor()
        mm._focus_browser_editor(editor, timeout_ms=4000)
        self.assertTrue(editor.evaluate_called)
        self.assertFalse(editor.force_click_attempted)

    def test_click_first_visible_uses_force_click_fallback_when_overlay_blocks_normal_click(self) -> None:
        class _FakeLocator:
            def __init__(self):
                self.force_clicked = False

            @property
            def first(self):
                return self

            def count(self) -> int:
                return 1

            def is_visible(self, timeout=None) -> bool:
                return True

            def click(self, timeout=None, force=False) -> None:
                if force:
                    self.force_clicked = True
                    return None
                raise RuntimeError("pointer events intercepted by overlay")

            def evaluate(self, script: str, arg=None) -> None:
                raise AssertionError("force click should have succeeded before DOM click")

        class _FakePage:
            def __init__(self):
                self.loc = _FakeLocator()

            def locator(self, selector: str):
                if selector == "button.test":
                    return self.loc
                raise AssertionError("unexpected selector")

        page = _FakePage()
        self.assertTrue(mm._click_first_visible(page, ("button.test",), timeout_ms=3000))
        self.assertTrue(page.loc.force_clicked)

    def test_remove_maxclaw_promo_overlay_returns_true_when_dom_cleanup_succeeds(self) -> None:
        class _FakePage:
            def evaluate(self, script: str):
                self.script = script
                return True

        page = _FakePage()
        self.assertTrue(mm._remove_maxclaw_promo_overlay(page))
        self.assertIn("MaxClaw is here", page.script)

    def test_inject_browser_storage_adds_init_script_for_agent_minimax_origin(self) -> None:
        class _FakeContext:
            def __init__(self):
                self.script = ""

            def add_init_script(self, script: str) -> None:
                self.script = script

        context = _FakeContext()
        old_local = minimax_settings.minimax_browser_local_storage_json
        old_session = minimax_settings.minimax_browser_session_storage_json
        try:
            minimax_settings.minimax_browser_local_storage_json = '{"_token":"abc","USER_HARD_WARE_INFO":"42"}'
            minimax_settings.minimax_browser_session_storage_json = '{"tab_device_id":"77"}'
            mm._inject_browser_storage(context)
        finally:
            minimax_settings.minimax_browser_local_storage_json = old_local
            minimax_settings.minimax_browser_session_storage_json = old_session

        self.assertIn("agent.minimax.io", context.script)
        self.assertIn('"_token": "abc"', context.script)
        self.assertIn('"tab_device_id": "77"', context.script)

    def test_inject_browser_storage_ignores_invalid_json(self) -> None:
        class _FakeContext:
            def __init__(self):
                self.calls = 0

            def add_init_script(self, script: str) -> None:
                self.calls += 1

        context = _FakeContext()
        old_local = minimax_settings.minimax_browser_local_storage_json
        old_session = minimax_settings.minimax_browser_session_storage_json
        try:
            minimax_settings.minimax_browser_local_storage_json = "{invalid"
            minimax_settings.minimax_browser_session_storage_json = ""
            mm._inject_browser_storage(context)
        finally:
            minimax_settings.minimax_browser_local_storage_json = old_local
            minimax_settings.minimax_browser_session_storage_json = old_session

        self.assertEqual(context.calls, 0)

    def test_populate_browser_message_uses_dom_text_fallback_when_keyboard_type_fails(self) -> None:
        class _FakeEditor:
            def __init__(self):
                self.prompt_set_via_dom = None

            @property
            def first(self):
                return self

            def click(self, timeout=None, force=False) -> None:
                return None

            def evaluate(self, script: str, arg=None) -> None:
                if arg is not None:
                    self.prompt_set_via_dom = arg
                return None

        class _FakeUploadInput:
            def __init__(self):
                self.uploaded_path = None

            @property
            def last(self):
                return self

            def count(self) -> int:
                return 1

            def set_input_files(self, path: str, timeout=None) -> None:
                self.uploaded_path = path

        class _FakeTextLocator:
            @property
            def first(self):
                return self

            def wait_for(self, timeout=None) -> None:
                return None

        class _FakeKeyboard:
            def __init__(self):
                self.presses: list[str] = []

            def press(self, key: str) -> None:
                self.presses.append(key)

            def type(self, value: str) -> None:
                raise RuntimeError("keyboard typing unavailable")

        class _FakePage:
            def __init__(self):
                self.editor = _FakeEditor()
                self.upload_input = _FakeUploadInput()
                self.keyboard = _FakeKeyboard()

            def wait_for_selector(self, selector: str, timeout=None) -> None:
                if selector != ".tiptap-editor":
                    raise AssertionError("unexpected selector")

            def locator(self, selector: str):
                if selector == ".tiptap-editor":
                    return self.editor
                if selector == "input[type='file']":
                    return self.upload_input
                if selector.startswith("text="):
                    return _FakeTextLocator()
                raise AssertionError("unexpected selector {}".format(selector))

            def wait_for_timeout(self, _ms: int) -> None:
                return None

        page = _FakePage()
        original_login_modal = mm._login_modal_visible
        try:
            mm._login_modal_visible = lambda *_args, **_kwargs: False  # type: ignore[assignment]
            mm._populate_browser_message(
                page,
                "/tmp/example.mp4",
                "Analyse ce mouvement",
                timeout_ms=4000,
            )
        finally:
            mm._login_modal_visible = original_login_modal  # type: ignore[assignment]

        self.assertEqual(page.editor.prompt_set_via_dom, "Analyse ce mouvement")
        self.assertEqual(page.upload_input.uploaded_path, "/tmp/example.mp4")

    def test_send_button_enabled_detects_inactive_and_active_states(self) -> None:
        class _FakePage:
            def __init__(self, active: bool):
                self.active = active

            def evaluate(self, script: str):
                return self.active

        self.assertFalse(mm._send_button_enabled(_FakePage(False)))
        self.assertTrue(mm._send_button_enabled(_FakePage(True)))

    def test_wait_for_bot_challenge_to_clear_reloads_and_succeeds(self) -> None:
        class _FakeBodyLocator:
            def __init__(self, page):
                self.page = page

            def inner_text(self, timeout=None):
                return "Just a moment..." if self.page.challenge_active else "AI Motion Coach"

        class _FakePage:
            def __init__(self):
                self.challenge_active = True
                self.reloads = 0

            def title(self):
                return "Just a moment..." if self.challenge_active else "MiniMax Agent"

            def locator(self, selector: str):
                if selector == "body":
                    return _FakeBodyLocator(self)
                raise AssertionError("unexpected selector")

            def reload(self, **_kwargs):
                self.reloads += 1
                self.challenge_active = False

            def wait_for_timeout(self, _delay_ms):
                return None

        page = _FakePage()
        self.assertTrue(mm._wait_for_bot_challenge_to_clear(page, timeout_ms=5000))
        self.assertEqual(page.reloads, 1)

    def test_wait_for_bot_challenge_to_clear_returns_false_when_challenge_persists(self) -> None:
        class _FakeBodyLocator:
            def inner_text(self, timeout=None):
                return "Just a moment..."

        class _FakePage:
            def title(self):
                return "Just a moment..."

            def locator(self, selector: str):
                if selector == "body":
                    return _FakeBodyLocator()
                raise AssertionError("unexpected selector")

            def reload(self, **_kwargs):
                return None

            def wait_for_timeout(self, _delay_ms):
                return None

        page = _FakePage()
        original_monotonic = mm.time.monotonic
        ticks = iter([0.0, 0.5, 1.2, 2.1, 3.2, 4.3, 5.4])
        try:
            mm.time.monotonic = lambda: next(ticks)  # type: ignore[assignment]
            self.assertFalse(mm._wait_for_bot_challenge_to_clear(page, timeout_ms=4000))
        finally:
            mm.time.monotonic = original_monotonic  # type: ignore[assignment]

    def test_open_motion_coach_chat_retries_direct_expert_page_before_experts_fallback(self) -> None:
        class _FakePage:
            def __init__(self):
                self.goto_calls: list[str] = []
                self.url = ""
                self.waited_for_selector = False

            def goto(self, url: str, **_kwargs) -> None:
                self.goto_calls.append(url)
                self.url = url

            def wait_for_load_state(self, *_args, **_kwargs) -> None:
                return None

            def wait_for_selector(self, selector: str, timeout=None) -> None:
                if selector == ".tiptap-editor":
                    self.waited_for_selector = True
                    return None
                raise AssertionError("unexpected selector")

        page = _FakePage()
        original_composer_ready = mm._motion_coach_composer_ready
        original_cta_present = mm._motion_coach_cta_present
        original_click_cta = mm._click_motion_coach_cta
        original_wait_for_page_condition = mm._wait_for_page_condition
        try:
            mm._motion_coach_composer_ready = lambda *_args, **_kwargs: False  # type: ignore[assignment]
            mm._motion_coach_cta_present = lambda current_page, **_kwargs: len(current_page.goto_calls) >= 2  # type: ignore[assignment]
            mm._click_motion_coach_cta = lambda current_page, timeout_ms=0: len(current_page.goto_calls) >= 2  # type: ignore[assignment]
            mm._wait_for_page_condition = lambda _page, predicate, timeout_ms, step_ms=350: bool(predicate())  # type: ignore[assignment]

            mm._open_motion_coach_chat(page, timeout_ms=3000)
        finally:
            mm._motion_coach_composer_ready = original_composer_ready  # type: ignore[assignment]
            mm._motion_coach_cta_present = original_cta_present  # type: ignore[assignment]
            mm._click_motion_coach_cta = original_click_cta  # type: ignore[assignment]
            mm._wait_for_page_condition = original_wait_for_page_condition  # type: ignore[assignment]

        self.assertEqual(page.goto_calls, [mm._motion_coach_expert_url(), mm._motion_coach_expert_url()])
        self.assertTrue(page.waited_for_selector)

    def test_open_motion_coach_chat_uses_experts_card_when_search_box_missing(self) -> None:
        class _FakePage:
            def __init__(self):
                self.goto_calls: list[str] = []
                self.url = ""
                self.stage = "init"

            def goto(self, url: str, **_kwargs) -> None:
                self.goto_calls.append(url)
                self.url = url
                if url.endswith("/experts"):
                    self.stage = "experts"
                else:
                    self.stage = "direct"

            def wait_for_load_state(self, *_args, **_kwargs) -> None:
                return None

            def wait_for_url(self, *_args, **_kwargs) -> None:
                return None

            def wait_for_selector(self, selector: str, timeout=None) -> None:
                if selector == ".tiptap-editor" and self.stage == "composer":
                    return None
                raise RuntimeError("composer missing")

        page = _FakePage()
        original_composer_ready = mm._motion_coach_composer_ready
        original_cta_present = mm._motion_coach_cta_present
        original_click_cta = mm._click_motion_coach_cta
        original_wait_for_page_condition = mm._wait_for_page_condition
        original_card_present = mm._motion_coach_card_present
        original_search_present = mm._experts_search_box_present
        original_click_card = mm._click_motion_coach_card
        try:
            mm._motion_coach_composer_ready = lambda current_page, **_kwargs: current_page.stage == "composer"  # type: ignore[assignment]
            mm._motion_coach_cta_present = lambda current_page, **_kwargs: current_page.stage == "card_opened"  # type: ignore[assignment]

            def _fake_click_cta(current_page, timeout_ms=0):
                if current_page.stage == "card_opened":
                    current_page.stage = "composer"
                    return True
                return False

            def _fake_click_card(current_page, timeout_ms=0):
                if current_page.stage == "experts":
                    current_page.stage = "card_opened"
                    return True
                return False

            mm._click_motion_coach_cta = _fake_click_cta  # type: ignore[assignment]
            mm._wait_for_page_condition = lambda _page, predicate, timeout_ms, step_ms=350: bool(predicate())  # type: ignore[assignment]
            mm._motion_coach_card_present = lambda current_page, **_kwargs: current_page.stage == "experts"  # type: ignore[assignment]
            mm._experts_search_box_present = lambda *_args, **_kwargs: False  # type: ignore[assignment]
            mm._click_motion_coach_card = _fake_click_card  # type: ignore[assignment]

            mm._open_motion_coach_chat(page, timeout_ms=3000)
        finally:
            mm._motion_coach_composer_ready = original_composer_ready  # type: ignore[assignment]
            mm._motion_coach_cta_present = original_cta_present  # type: ignore[assignment]
            mm._click_motion_coach_cta = original_click_cta  # type: ignore[assignment]
            mm._wait_for_page_condition = original_wait_for_page_condition  # type: ignore[assignment]
            mm._motion_coach_card_present = original_card_present  # type: ignore[assignment]
            mm._experts_search_box_present = original_search_present  # type: ignore[assignment]
            mm._click_motion_coach_card = original_click_card  # type: ignore[assignment]

        self.assertEqual(
            page.goto_calls,
            [mm._motion_coach_expert_url(), mm._motion_coach_expert_url(), "https://agent.minimax.io/experts"],
        )
        self.assertEqual(page.stage, "composer")

    def test_open_motion_coach_chat_reauthenticates_when_direct_page_shows_login_modal(self) -> None:
        class _FakePage:
            def __init__(self):
                self.goto_calls: list[str] = []
                self.url = ""
                self.auth_stage = 0

            def goto(self, url: str, **_kwargs) -> None:
                self.goto_calls.append(url)
                self.url = url

            def wait_for_load_state(self, *_args, **_kwargs) -> None:
                return None

        page = _FakePage()
        original_composer_ready = mm._motion_coach_composer_ready
        original_cta_present = mm._motion_coach_cta_present
        original_login_modal_visible = mm._login_modal_visible
        original_wait_for_page_condition = mm._wait_for_page_condition
        original_ensure_auth = mm._ensure_browser_authenticated
        auth_calls: list[str] = []
        try:
            mm._motion_coach_composer_ready = lambda current_page, **_kwargs: current_page.auth_stage == 1 and len(current_page.goto_calls) >= 2  # type: ignore[assignment]
            mm._motion_coach_cta_present = lambda *_args, **_kwargs: False  # type: ignore[assignment]
            mm._login_modal_visible = lambda current_page, **_kwargs: current_page.auth_stage == 0  # type: ignore[assignment]
            mm._wait_for_page_condition = lambda _page, predicate, timeout_ms, step_ms=350: bool(predicate())  # type: ignore[assignment]

            def _fake_ensure_auth(current_page, email="", password="", timeout_ms=0):
                auth_calls.append(email)
                current_page.auth_stage = 1

            mm._ensure_browser_authenticated = _fake_ensure_auth  # type: ignore[assignment]

            mm._open_motion_coach_chat(
                page,
                timeout_ms=3000,
                email="coaching@achzodcoaching.com",
                password="secret",
            )
        finally:
            mm._motion_coach_composer_ready = original_composer_ready  # type: ignore[assignment]
            mm._motion_coach_cta_present = original_cta_present  # type: ignore[assignment]
            mm._login_modal_visible = original_login_modal_visible  # type: ignore[assignment]
            mm._wait_for_page_condition = original_wait_for_page_condition  # type: ignore[assignment]
            mm._ensure_browser_authenticated = original_ensure_auth  # type: ignore[assignment]

        self.assertEqual(auth_calls, ["coaching@achzodcoaching.com"])
        self.assertEqual(page.goto_calls, [mm._motion_coach_expert_url(), mm._motion_coach_expert_url()])

    def test_run_browser_only_authenticates_before_opening_motion_coach_chat(self) -> None:
        class _FakePage:
            def __init__(self):
                self.handlers = {}
                self.goto_calls: list[str] = []

            def on(self, event: str, handler) -> None:
                self.handlers[event] = handler

            def off(self, event: str, handler) -> None:
                if self.handlers.get(event) is handler:
                    self.handlers.pop(event, None)

            def goto(self, url: str, **_kwargs) -> None:
                self.goto_calls.append(url)

        class _FakeContext:
            def __init__(self, page):
                self.pages = [page]

            def close(self) -> None:
                return None

        class _FakeChromium:
            def __init__(self, context):
                self._context = context

            def launch_persistent_context(self, *_args, **_kwargs):
                return self._context

        class _FakePlaywright:
            def __init__(self, context):
                self.chromium = _FakeChromium(context)

        class _FakeManager:
            def __init__(self, context):
                self._playwright = _FakePlaywright(context)

            def __enter__(self):
                return self._playwright

            def __exit__(self, exc_type, exc, tb):
                return False

        fake_page = _FakePage()
        fake_context = _FakeContext(fake_page)
        fake_module = types.ModuleType("playwright.sync_api")
        fake_module.sync_playwright = lambda: _FakeManager(fake_context)  # type: ignore[attr-defined]

        old_module = sys.modules.get("playwright.sync_api")
        old_email = minimax_settings.minimax_browser_email
        old_password = minimax_settings.minimax_browser_password
        order: list[str] = []
        original_ensure_auth = mm._ensure_browser_authenticated
        original_open_motion = mm._open_motion_coach_chat
        try:
            sys.modules["playwright.sync_api"] = fake_module
            minimax_settings.minimax_browser_email = "coaching@achzodcoaching.com"
            minimax_settings.minimax_browser_password = "secret"

            mm._ensure_browser_authenticated = lambda *_args, **_kwargs: order.append("auth")  # type: ignore[assignment]

            def _fake_open(*_args, **_kwargs):
                order.append("open")
                raise RuntimeError("stop after order check")

            mm._open_motion_coach_chat = _fake_open  # type: ignore[assignment]

            with self.assertRaisesRegex(RuntimeError, "stop after order check"):
                mm._run_minimax_browser_only_once(
                    prepared=mm._PreparedVideo(path="video.mp4"),
                    prompt="Analyse cette video",
                    poll_interval=2.0,
                    timeout_s_effective=10,
                    video_hash="vh",
                    prompt_hash="ph",
                )
        finally:
            if old_module is not None:
                sys.modules["playwright.sync_api"] = old_module
            else:
                sys.modules.pop("playwright.sync_api", None)
            minimax_settings.minimax_browser_email = old_email
            minimax_settings.minimax_browser_password = old_password
            mm._ensure_browser_authenticated = original_ensure_auth  # type: ignore[assignment]
            mm._open_motion_coach_chat = original_open_motion  # type: ignore[assignment]

        self.assertEqual(order, ["auth", "open"])
        self.assertEqual(fake_page.goto_calls, [mm._motion_coach_expert_url()])


class MiniMaxBrowserFallbackStrategyTests(unittest.TestCase):
    def test_run_forces_browser_transport_even_if_flag_disabled(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            tmp.write(b"test-video")
            tmp.flush()

            old_enabled = minimax_settings.minimax_enable_cache
            old_browser_only = minimax_settings.minimax_browser_only
            old_email = minimax_settings.minimax_browser_email
            old_password = minimax_settings.minimax_browser_password
            minimax_settings.minimax_enable_cache = False
            minimax_settings.minimax_browser_only = False
            minimax_settings.minimax_browser_email = "user@example.com"
            minimax_settings.minimax_browser_password = "secret"

            calls = {"browser": 0, "direct": 0, "cache_put": 0}
            original_prepare = mm._prepare_video_for_minimax
            original_direct = mm._run_minimax_direct_once
            original_browser_only = mm._run_minimax_browser_only_once
            original_cache_put = mm._cache_put
            try:
                mm._prepare_video_for_minimax = lambda path: mm._PreparedVideo(path=path)  # type: ignore[assignment]
                mm._run_minimax_direct_once = lambda **kwargs: (  # type: ignore[assignment]
                    calls.__setitem__("direct", calls["direct"] + 1)
                    or (_ for _ in ()).throw(RuntimeError("direct transport should not be used"))
                )

                def _fake_browser_only(**kwargs):
                    calls["browser"] += 1
                    return MiniMaxAnalysis(
                        exercise_slug="machine_chest_press",
                        exercise_display="Presse Pectorale Machine",
                        score=80,
                        reps_total=10,
                        report_text="ok",
                        metadata={"transport": "browser_ui_only"},
                    )

                mm._run_minimax_browser_only_once = _fake_browser_only  # type: ignore[assignment]
                mm._cache_put = lambda *_args, **_kwargs: calls.__setitem__("cache_put", calls["cache_put"] + 1)  # type: ignore[assignment]

                out = run_minimax_motion_coach(tmp.name)
            finally:
                mm._prepare_video_for_minimax = original_prepare  # type: ignore[assignment]
                mm._run_minimax_direct_once = original_direct  # type: ignore[assignment]
                mm._run_minimax_browser_only_once = original_browser_only  # type: ignore[assignment]
                mm._cache_put = original_cache_put  # type: ignore[assignment]
                minimax_settings.minimax_enable_cache = old_enabled
                minimax_settings.minimax_browser_only = old_browser_only
                minimax_settings.minimax_browser_email = old_email
                minimax_settings.minimax_browser_password = old_password

            self.assertEqual(calls["browser"], 1)
            self.assertEqual(calls["direct"], 0)
            self.assertEqual(calls["cache_put"], 1)
            self.assertEqual(out.metadata.get("transport"), "browser_ui_only")
            self.assertEqual(out.metadata.get("policy_forced_browser_only"), True)

    def test_run_browser_only_mode_skips_direct_api_transport(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            tmp.write(b"test-video")
            tmp.flush()

            old_enabled = minimax_settings.minimax_enable_cache
            old_browser_only = minimax_settings.minimax_browser_only
            old_email = minimax_settings.minimax_browser_email
            old_password = minimax_settings.minimax_browser_password
            old_token = minimax_settings.minimax_token
            old_user = minimax_settings.minimax_user_id
            old_device = minimax_settings.minimax_device_id
            minimax_settings.minimax_enable_cache = False
            minimax_settings.minimax_browser_only = True
            minimax_settings.minimax_browser_email = "user@example.com"
            minimax_settings.minimax_browser_password = "secret"
            minimax_settings.minimax_token = ""
            minimax_settings.minimax_user_id = ""
            minimax_settings.minimax_device_id = ""

            calls = {"browser": 0, "direct": 0, "cache_put": 0}
            original_prepare = mm._prepare_video_for_minimax
            original_direct = mm._run_minimax_direct_once
            original_browser_only = mm._run_minimax_browser_only_once
            original_cache_put = mm._cache_put
            try:
                mm._prepare_video_for_minimax = lambda path: mm._PreparedVideo(path=path)  # type: ignore[assignment]
                mm._run_minimax_direct_once = lambda **kwargs: (  # type: ignore[assignment]
                    calls.__setitem__("direct", calls["direct"] + 1)
                    or (_ for _ in ()).throw(RuntimeError("direct transport should not be used"))
                )

                def _fake_browser_only(**kwargs):
                    calls["browser"] += 1
                    return MiniMaxAnalysis(
                        exercise_slug="machine_chest_press",
                        exercise_display="Presse Pectorale Machine",
                        score=84,
                        reps_total=9,
                        report_text="ok",
                        metadata={"transport": "browser_ui_only"},
                    )

                mm._run_minimax_browser_only_once = _fake_browser_only  # type: ignore[assignment]
                mm._cache_put = lambda *_args, **_kwargs: calls.__setitem__("cache_put", calls["cache_put"] + 1)  # type: ignore[assignment]

                out = run_minimax_motion_coach(tmp.name)
            finally:
                mm._prepare_video_for_minimax = original_prepare  # type: ignore[assignment]
                mm._run_minimax_direct_once = original_direct  # type: ignore[assignment]
                mm._run_minimax_browser_only_once = original_browser_only  # type: ignore[assignment]
                mm._cache_put = original_cache_put  # type: ignore[assignment]
                minimax_settings.minimax_enable_cache = old_enabled
                minimax_settings.minimax_browser_only = old_browser_only
                minimax_settings.minimax_browser_email = old_email
                minimax_settings.minimax_browser_password = old_password
                minimax_settings.minimax_token = old_token
                minimax_settings.minimax_user_id = old_user
                minimax_settings.minimax_device_id = old_device

            self.assertEqual(calls["browser"], 1)
            self.assertEqual(calls["direct"], 0)
            self.assertEqual(calls["cache_put"], 1)
            self.assertEqual(out.metadata.get("transport"), "browser_ui_only")

    def test_run_browser_only_mode_requires_browser_credentials(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            tmp.write(b"test-video")
            tmp.flush()

            old_enabled = minimax_settings.minimax_enable_cache
            old_browser_only = minimax_settings.minimax_browser_only
            old_email = minimax_settings.minimax_browser_email
            old_password = minimax_settings.minimax_browser_password
            old_token = minimax_settings.minimax_token
            old_user = minimax_settings.minimax_user_id
            old_device = minimax_settings.minimax_device_id
            minimax_settings.minimax_enable_cache = False
            minimax_settings.minimax_browser_only = True
            minimax_settings.minimax_browser_email = ""
            minimax_settings.minimax_browser_password = ""
            minimax_settings.minimax_token = ""
            minimax_settings.minimax_user_id = ""
            minimax_settings.minimax_device_id = ""

            try:
                with self.assertRaises(RuntimeError):
                    run_minimax_motion_coach(tmp.name)
            finally:
                minimax_settings.minimax_enable_cache = old_enabled
                minimax_settings.minimax_browser_only = old_browser_only
                minimax_settings.minimax_browser_email = old_email
                minimax_settings.minimax_browser_password = old_password
                minimax_settings.minimax_token = old_token
                minimax_settings.minimax_user_id = old_user
                minimax_settings.minimax_device_id = old_device


if __name__ == "__main__":
    unittest.main()
