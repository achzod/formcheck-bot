from __future__ import annotations

import hashlib
import sys
import tempfile
import types
import unittest
from urllib.parse import quote

import httpx

# Keep pipeline imports testable without OpenCV runtime dependency.
if "cv2" not in sys.modules:
    sys.modules["cv2"] = types.ModuleType("cv2")

from analysis.minimax_motion_coach import (
    _MiniMaxClient,
    _SIGNING_SECRET,
    _UploadedAsset,
    _YY_SUFFIX,
    _cache_get,
    _cache_put,
    _extract_agent_message,
    _is_retryable_minimax_error,
    _parse_analysis_payload,
    MiniMaxAnalysis,
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
        self.assertIn("DECOMPOSITION DU SCORE", out.report_text)
        self.assertIn("RECOMMANDATION POUR LA PROCHAINE VIDEO", out.report_text)

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


class MiniMaxMessageExtractionTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
