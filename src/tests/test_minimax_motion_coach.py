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

    def test_pipeline_mapping_keeps_minimax_slug_when_display_conflicts(self) -> None:
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
        self.assertEqual(out.detection.exercise.value, "leg_press")


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
        login_modal_states = iter([True, False])

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
        original_locator_visible = mm._locator_is_visible
        original_click_first = mm._click_first_visible
        try:
            mm._locator_is_visible = lambda *_args, **_kwargs: False  # type: ignore[assignment]

            def _fake_click_first(_page, selectors: tuple[str, ...], timeout_ms: int = 2500) -> bool:
                return "button:has-text('Type to chat with AI Motion Coach')" in selectors

            mm._click_first_visible = _fake_click_first  # type: ignore[assignment]

            mm._open_motion_coach_chat(page, timeout_ms=3000)
        finally:
            mm._locator_is_visible = original_locator_visible  # type: ignore[assignment]
            mm._click_first_visible = original_click_first  # type: ignore[assignment]

        self.assertEqual(page.goto_calls, [mm._motion_coach_expert_url()])
        self.assertTrue(page.waited_for_selector)

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
