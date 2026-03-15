import asyncio
import os
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from analysis.minimax_motion_coach import MiniMaxAnalysis, _analysis_to_payload

try:
    from app import database as db
    from app import handlers
    from app import minimax_remote_worker
    from sqlalchemy.dialects import sqlite
    _HANDLERS_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - local env may miss app deps
    db = None
    handlers = None
    minimax_remote_worker = None
    sqlite = None
    _HANDLERS_IMPORT_ERROR = exc


@unittest.skipIf(handlers is None, "app deps unavailable: {}".format(_HANDLERS_IMPORT_ERROR))
class RemoteMiniMaxWorkerFlowTests(unittest.TestCase):
    def test_complete_remote_minimax_job_maps_payload_and_delivers(self) -> None:
        payload = _analysis_to_payload(
            MiniMaxAnalysis(
                exercise_slug="machine_chest_press",
                exercise_display="Machine Chest Press",
                exercise_confidence=0.93,
                score=82,
                reps_total=8,
                reps_complete=8,
                intensity_score=74,
                intensity_label="elevee",
                avg_inter_rep_rest_s=1.1,
                positives=["Trajectoire stable"],
                report_text="Rapport MiniMax",
            )
        )
        job = SimpleNamespace(
            id=7,
            analysis_id=42,
            user_id=3,
            phone="+33600000000",
            video_path="/tmp/test-video.mp4",
        )
        captured: dict[str, object] = {}

        original_get = handlers.db.get_minimax_remote_job
        original_complete = handlers.db.complete_minimax_remote_job
        original_deliver = handlers._deliver_pipeline_success
        original_active = dict(handlers._active_analyses)
        handlers._active_analyses[job.phone] = time.time()

        async def fake_get(job_id: int):
            self.assertEqual(job_id, 7)
            return job

        async def fake_complete(job_id: int, result_payload: str):
            self.assertEqual(job_id, 7)
            self.assertEqual(result_payload, payload)
            return job

        async def fake_deliver(**kwargs):
            captured.update(kwargs)

        try:
            handlers.db.get_minimax_remote_job = fake_get
            handlers.db.complete_minimax_remote_job = fake_complete
            handlers._deliver_pipeline_success = fake_deliver
            ok = asyncio.run(handlers.complete_remote_minimax_job(7, payload))
        finally:
            handlers.db.get_minimax_remote_job = original_get
            handlers.db.complete_minimax_remote_job = original_complete
            handlers._deliver_pipeline_success = original_deliver
            handlers._active_analyses.clear()
            handlers._active_analyses.update(original_active)

        self.assertTrue(ok)
        self.assertEqual(captured["phone"], job.phone)
        self.assertEqual(captured["analysis_id"], job.analysis_id)
        result = captured["result"]
        self.assertEqual(result.report.exercise_display, "Machine Chest Press")
        self.assertEqual(result.reps.total_reps, 8)
        self.assertNotIn(job.phone, handlers._active_analyses)

    def test_complete_remote_minimax_job_keeps_completed_state_when_delivery_fails(self) -> None:
        payload = _analysis_to_payload(
            MiniMaxAnalysis(
                exercise_slug="machine_chest_press",
                exercise_display="Machine Chest Press",
                exercise_confidence=0.93,
                score=82,
                reps_total=8,
                reps_complete=8,
                intensity_score=74,
                intensity_label="elevee",
                avg_inter_rep_rest_s=1.1,
                positives=["Trajectoire stable"],
                report_text="Rapport MiniMax",
            )
        )
        job = SimpleNamespace(
            id=17,
            analysis_id=52,
            user_id=5,
            phone="+33622222222",
            video_path="/tmp/test-video-fail-delivery.mp4",
        )
        events: list[str] = []
        cleaned: list[str] = []

        original_get = handlers.db.get_minimax_remote_job
        original_complete = handlers.db.complete_minimax_remote_job
        original_deliver = handlers._deliver_pipeline_success
        original_cleanup = handlers.cleanup_video
        original_active = dict(handlers._active_analyses)
        handlers._active_analyses[job.phone] = time.time()

        async def fake_get(job_id: int):
            self.assertEqual(job_id, 17)
            return job

        async def fake_complete(job_id: int, result_payload: str):
            self.assertEqual(job_id, 17)
            self.assertEqual(result_payload, payload)
            events.append("complete")
            return job

        async def fake_deliver(**kwargs):
            events.append("deliver")
            raise RuntimeError("twilio down")

        def fake_cleanup(path: str):
            cleaned.append(path)

        try:
            handlers.db.get_minimax_remote_job = fake_get
            handlers.db.complete_minimax_remote_job = fake_complete
            handlers._deliver_pipeline_success = fake_deliver
            handlers.cleanup_video = fake_cleanup
            ok = asyncio.run(handlers.complete_remote_minimax_job(17, payload))
        finally:
            handlers.db.get_minimax_remote_job = original_get
            handlers.db.complete_minimax_remote_job = original_complete
            handlers._deliver_pipeline_success = original_deliver
            handlers.cleanup_video = original_cleanup
            handlers._active_analyses.clear()
            handlers._active_analyses.update(original_active)

        self.assertTrue(ok)
        self.assertEqual(events, ["complete", "deliver"])
        self.assertEqual(cleaned, [job.video_path])
        self.assertNotIn(job.phone, handlers._active_analyses)

    def test_fail_remote_minimax_job_notifies_and_cleans_up(self) -> None:
        job = SimpleNamespace(
            id=8,
            analysis_id=99,
            user_id=4,
            phone="+33611111111",
            video_path="/tmp/failed-video.mp4",
        )
        sent: list[tuple[str, str]] = []
        cleaned: list[str] = []

        original_fail = handlers.db.fail_minimax_remote_job
        original_send = handlers.wa.send_text
        original_cleanup = handlers.cleanup_video
        original_active = dict(handlers._active_analyses)
        handlers._active_analyses[job.phone] = time.time()

        async def fake_fail(job_id: int, error: str):
            self.assertEqual(job_id, 8)
            self.assertIn("blocked", error)
            return job

        async def fake_send_text(phone: str, text: str):
            sent.append((phone, text))

        def fake_cleanup(path: str):
            cleaned.append(path)

        try:
            handlers.db.fail_minimax_remote_job = fake_fail
            handlers.wa.send_text = fake_send_text
            handlers.cleanup_video = fake_cleanup
            ok = asyncio.run(handlers.fail_remote_minimax_job(8, "blocked by anti-bot"))
        finally:
            handlers.db.fail_minimax_remote_job = original_fail
            handlers.wa.send_text = original_send
            handlers.cleanup_video = original_cleanup
            handlers._active_analyses.clear()
            handlers._active_analyses.update(original_active)

        self.assertTrue(ok)
        self.assertEqual(sent[0][0], job.phone)
        self.assertEqual(cleaned, [job.video_path])
        self.assertNotIn(job.phone, handlers._active_analyses)

    def test_fail_remote_minimax_job_skips_notification_when_job_already_completed(self) -> None:
        job = SimpleNamespace(
            id=18,
            analysis_id=100,
            user_id=6,
            phone="+33633333333",
            video_path="/tmp/completed-video.mp4",
            status="completed",
        )
        sent: list[tuple[str, str]] = []
        cleaned: list[str] = []

        original_fail = handlers.db.fail_minimax_remote_job
        original_send = handlers.wa.send_text
        original_cleanup = handlers.cleanup_video
        original_active = dict(handlers._active_analyses)
        handlers._active_analyses[job.phone] = time.time()

        async def fake_fail(job_id: int, error: str):
            self.assertEqual(job_id, 18)
            self.assertIn("already completed", error)
            return job

        async def fake_send_text(phone: str, text: str):
            sent.append((phone, text))

        def fake_cleanup(path: str):
            cleaned.append(path)

        try:
            handlers.db.fail_minimax_remote_job = fake_fail
            handlers.wa.send_text = fake_send_text
            handlers.cleanup_video = fake_cleanup
            ok = asyncio.run(handlers.fail_remote_minimax_job(18, "already completed upstream"))
        finally:
            handlers.db.fail_minimax_remote_job = original_fail
            handlers.wa.send_text = original_send
            handlers.cleanup_video = original_cleanup
            handlers._active_analyses.clear()
            handlers._active_analyses.update(original_active)

        self.assertTrue(ok)
        self.assertEqual(sent, [])
        self.assertEqual(cleaned, [])
        self.assertNotIn(job.phone, handlers._active_analyses)

    def test_deliver_pipeline_success_falls_back_to_text_when_html_generation_fails(self) -> None:
        result = SimpleNamespace(
            report=SimpleNamespace(
                exercise_display="Lat Pulldown (Tirage Vertical)",
                score=78,
                report_text=(
                    "<FORMCHECK_REPORT_MD>\n"
                    "- Exercice: Lat Pulldown (Tirage Vertical)\n"
                    "- Score global: 78/100\n"
                    "RESUME\n"
                    "Serie solide avec une fin de trajectoire un peu moins propre.\n"
                    "</FORMCHECK_REPORT_MD>"
                ),
                model_used="minimax_motion_coach",
            ),
            reps=SimpleNamespace(
                total_reps=8,
                intensity_score=76,
                intensity_label="elevee",
                avg_inter_rep_rest_s=0.92,
            ),
            annotated_frames={},
            detection=None,
        )
        sent: list[tuple[str, str]] = []
        cleaned: list[str] = []

        original_update = handlers.db.update_analysis
        original_get_user = handlers.db.get_user_by_phone
        original_decrement = handlers.db.decrement_credit
        original_generate = handlers.generate_html_report
        original_save = handlers.save_report
        original_get_report_url = handlers.get_report_url
        original_send = handlers.wa.send_text
        original_cleanup = handlers.cleanup_video
        original_test_mode = handlers.app_settings.test_mode
        original_test_mode_free = handlers.app_settings.test_mode_free

        async def fake_update(*args, **kwargs):
            return None

        async def fake_get_user(_phone: str):
            return SimpleNamespace(name="Client", is_unlimited=True, credits=3)

        async def fake_decrement(_user_id: int):
            raise AssertionError("decrement_credit should not be called in test mode")

        def fake_generate_html_report(**kwargs):
            raise RuntimeError("html crash")

        def fake_save_report(*args, **kwargs):
            raise AssertionError("save_report should not be called when html generation fails")

        def fake_get_report_url(*args, **kwargs):
            return "https://example.com/report"

        async def fake_send_text(phone: str, text: str):
            sent.append((phone, text))
            return {"sid": "SM123", "status": "queued"}

        def fake_cleanup(path: str):
            cleaned.append(path)

        try:
            handlers.db.update_analysis = fake_update
            handlers.db.get_user_by_phone = fake_get_user
            handlers.db.decrement_credit = fake_decrement
            handlers.generate_html_report = fake_generate_html_report
            handlers.save_report = fake_save_report
            handlers.get_report_url = fake_get_report_url
            handlers.wa.send_text = fake_send_text
            handlers.cleanup_video = fake_cleanup
            handlers.app_settings.test_mode = True
            handlers.app_settings.test_mode_free = True

            asyncio.run(
                handlers._deliver_pipeline_success(
                    phone="+33644444444",
                    user_id=7,
                    analysis_id=321,
                    video_path="/tmp/test-fallback.mp4",
                    result=result,
                    include_annotated_frames=False,
                    strict_minimax_source=True,
                    fallback_local_enabled=False,
                )
            )
        finally:
            handlers.db.update_analysis = original_update
            handlers.db.get_user_by_phone = original_get_user
            handlers.db.decrement_credit = original_decrement
            handlers.generate_html_report = original_generate
            handlers.save_report = original_save
            handlers.get_report_url = original_get_report_url
            handlers.wa.send_text = original_send
            handlers.cleanup_video = original_cleanup
            handlers.app_settings.test_mode = original_test_mode
            handlers.app_settings.test_mode_free = original_test_mode_free

        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0][0], "+33644444444")
        self.assertIn("Lat Pulldown (Tirage Vertical)", sent[0][1])
        self.assertIn("Synthese immediate", sent[0][1])
        self.assertIn("Serie solide avec une fin de trajectoire", sent[0][1])
        self.assertEqual(cleaned, ["/tmp/test-fallback.mp4"])


@unittest.skipIf(db is None, "app deps unavailable: {}".format(_HANDLERS_IMPORT_ERROR))
class RemoteMiniMaxJobClaimTests(unittest.TestCase):
    def test_claim_query_reclaims_stale_processing_jobs(self) -> None:
        job = SimpleNamespace(
            id=11,
            analysis_id=11,
            status="processing",
            worker_id="old-worker",
            error="old crash",
        )
        captured = {}

        class _FakeResult:
            def scalar_one_or_none(self):
                return job

        class _FakeSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def execute(self, stmt):
                captured["sql"] = str(
                    stmt.compile(
                        dialect=sqlite.dialect(),
                        compile_kwargs={"literal_binds": True},
                    )
                )
                return _FakeResult()

            async def commit(self):
                captured["committed"] = True

            async def refresh(self, current_job):
                captured["refreshed"] = current_job.id

        original_async_session = db.async_session
        original_stale_after = db.settings.minimax_remote_job_stale_after_s
        try:
            db.async_session = lambda: _FakeSession()
            db.settings.minimax_remote_job_stale_after_s = 600
            claimed = asyncio.run(db.claim_next_minimax_remote_job("worker-new"))
        finally:
            db.async_session = original_async_session
            db.settings.minimax_remote_job_stale_after_s = original_stale_after

        self.assertIs(claimed, job)
        self.assertEqual(job.status, "processing")
        self.assertEqual(job.worker_id, "worker-new")
        self.assertIsNone(job.error)
        self.assertTrue(captured.get("committed"))
        self.assertEqual(captured.get("refreshed"), 11)
        sql = captured.get("sql", "")
        self.assertIn("minimax_remote_jobs.status = 'queued'", sql)
        self.assertIn("minimax_remote_jobs.status = 'processing'", sql)
        self.assertIn("minimax_remote_jobs.updated_at <", sql)


@unittest.skipIf(minimax_remote_worker is None, "app deps unavailable: {}".format(_HANDLERS_IMPORT_ERROR))
class RemoteMiniMaxWorkerBootstrapTests(unittest.TestCase):
    def test_token_falls_back_to_render_api_key(self) -> None:
        original_remote = os.environ.get("MINIMAX_REMOTE_WORKER_TOKEN")
        original_internal = os.environ.get("FORMCHECK_INTERNAL_TOKEN")
        original_render = os.environ.get("RENDER_API_KEY")
        try:
            os.environ.pop("MINIMAX_REMOTE_WORKER_TOKEN", None)
            os.environ.pop("FORMCHECK_INTERNAL_TOKEN", None)
            os.environ["RENDER_API_KEY"] = "render-fallback-token"
            self.assertEqual(minimax_remote_worker._token(), "render-fallback-token")
            headers = minimax_remote_worker._headers()
            self.assertEqual(headers.get("X-Formcheck-Internal-Token"), "render-fallback-token")
        finally:
            if original_remote is None:
                os.environ.pop("MINIMAX_REMOTE_WORKER_TOKEN", None)
            else:
                os.environ["MINIMAX_REMOTE_WORKER_TOKEN"] = original_remote
            if original_internal is None:
                os.environ.pop("FORMCHECK_INTERNAL_TOKEN", None)
            else:
                os.environ["FORMCHECK_INTERNAL_TOKEN"] = original_internal
            if original_render is None:
                os.environ.pop("RENDER_API_KEY", None)
            else:
                os.environ["RENDER_API_KEY"] = original_render

    def test_apply_job_browser_context_updates_runtime_settings(self) -> None:
        job = {
            "id": 12,
            "browser_context": {
                "minimax_browser_email": "coach@example.com",
                "minimax_browser_password": "secret-pw",
                "minimax_motion_coach_expert_url": "https://agent.minimax.io/expert/chat/123456",
                "minimax_browser_timeout_s": "240",
                "minimax_poll_interval_s": "1.5",
                "minimax_browser_headless": "false",
            },
        }
        keys = tuple(job["browser_context"].keys())
        env_map = minimax_remote_worker._SETTING_TO_ENV
        original_env = {name: os.environ.get(name) for name in env_map.values()}
        runtime_settings = minimax_remote_worker.minimax_motion_coach.settings
        original_settings = {key: getattr(runtime_settings, key) for key in keys}

        try:
            applied = minimax_remote_worker._apply_job_browser_context(job)
            self.assertEqual(applied.get("minimax_browser_email"), "coach@example.com")
            self.assertEqual(applied.get("minimax_browser_timeout_s"), 240)
            self.assertEqual(applied.get("minimax_poll_interval_s"), 1.5)
            self.assertIs(applied.get("minimax_browser_headless"), False)
            self.assertEqual(
                getattr(runtime_settings, "minimax_motion_coach_expert_url"),
                "https://agent.minimax.io/expert/chat/123456",
            )
            self.assertEqual(os.environ.get("MINIMAX_BROWSER_EMAIL"), "coach@example.com")
            self.assertEqual(os.environ.get("MINIMAX_BROWSER_TIMEOUT_S"), "240")
            self.assertEqual(os.environ.get("MINIMAX_BROWSER_HEADLESS"), "false")
        finally:
            for key, value in original_settings.items():
                setattr(runtime_settings, key, value)
            for name, value in original_env.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def test_restore_runtime_browser_context_resets_job_overrides(self) -> None:
        runtime_settings = minimax_remote_worker.minimax_motion_coach.settings
        snapshot = minimax_remote_worker._capture_runtime_browser_context()
        original_email = getattr(runtime_settings, "minimax_browser_email", None)
        original_timeout = getattr(runtime_settings, "minimax_browser_timeout_s", None)
        try:
            os.environ["MINIMAX_BROWSER_EMAIL"] = "job@example.com"
            os.environ["MINIMAX_BROWSER_TIMEOUT_S"] = "240"
            runtime_settings.minimax_browser_email = "job@example.com"
            runtime_settings.minimax_browser_timeout_s = 240

            minimax_remote_worker._restore_runtime_browser_context(snapshot)

            self.assertEqual(os.environ.get("MINIMAX_BROWSER_EMAIL"), snapshot["env"].get("MINIMAX_BROWSER_EMAIL"))
            self.assertEqual(os.environ.get("MINIMAX_BROWSER_TIMEOUT_S"), snapshot["env"].get("MINIMAX_BROWSER_TIMEOUT_S"))
            self.assertEqual(getattr(runtime_settings, "minimax_browser_email"), snapshot["settings"].get("minimax_browser_email"))
            self.assertEqual(getattr(runtime_settings, "minimax_browser_timeout_s"), snapshot["settings"].get("minimax_browser_timeout_s"))
        finally:
            runtime_settings.minimax_browser_email = original_email
            runtime_settings.minimax_browser_timeout_s = original_timeout

    def test_run_worker_forces_headed_browser_without_forcing_channel(self) -> None:
        original_headless = os.environ.get("MINIMAX_BROWSER_HEADLESS")
        original_channel = os.environ.get("MINIMAX_BROWSER_CHANNEL")
        original_claim = minimax_remote_worker._claim_job
        original_reexec = minimax_remote_worker._maybe_reexec_under_xvfb
        observed: dict[str, str | None] = {"headless": None, "channel": None}

        async def fake_claim(_client, _worker_id):
            observed["headless"] = os.environ.get("MINIMAX_BROWSER_HEADLESS")
            observed["channel"] = os.environ.get("MINIMAX_BROWSER_CHANNEL")
            raise asyncio.CancelledError()

        def fake_reexec():
            return None

        try:
            os.environ["MINIMAX_BROWSER_HEADLESS"] = "true"
            os.environ.pop("MINIMAX_BROWSER_CHANNEL", None)
            minimax_remote_worker._claim_job = fake_claim
            minimax_remote_worker._maybe_reexec_under_xvfb = fake_reexec
            with self.assertRaises(asyncio.CancelledError):
                asyncio.run(minimax_remote_worker.run_worker())
        finally:
            minimax_remote_worker._claim_job = original_claim
            minimax_remote_worker._maybe_reexec_under_xvfb = original_reexec
            if original_headless is None:
                os.environ.pop("MINIMAX_BROWSER_HEADLESS", None)
            else:
                os.environ["MINIMAX_BROWSER_HEADLESS"] = original_headless
            if original_channel is None:
                os.environ.pop("MINIMAX_BROWSER_CHANNEL", None)
            else:
                os.environ["MINIMAX_BROWSER_CHANNEL"] = original_channel

        self.assertEqual(observed["headless"], "false")
        self.assertEqual(observed["channel"], "")

    def test_reexec_under_xvfb_when_display_missing(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "MINIMAX_BROWSER_HEADLESS": "false",
                "DISPLAY": "",
            },
            clear=False,
        ):
            with mock.patch.object(minimax_remote_worker.shutil, "which", return_value="/usr/bin/xvfb-run"):
                with mock.patch.object(minimax_remote_worker.os, "execvpe") as execvpe:
                    minimax_remote_worker._maybe_reexec_under_xvfb()

        execvpe.assert_called_once()
        path, cmd, env = execvpe.call_args.args
        self.assertEqual(path, "/usr/bin/xvfb-run")
        self.assertEqual(
            cmd,
            [
                "/usr/bin/xvfb-run",
                "-a",
                "-s",
                "-screen 0 1920x1080x24",
                minimax_remote_worker.sys.executable,
                "-m",
                "app.minimax_remote_worker",
            ],
        )
        self.assertEqual(env.get("FORMCHECK_XVFB_REEXEC"), "true")

    def test_reexec_is_skipped_when_display_present(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "MINIMAX_BROWSER_HEADLESS": "false",
                "DISPLAY": ":99",
            },
            clear=False,
        ):
            with mock.patch.object(minimax_remote_worker.os, "execvpe") as execvpe:
                minimax_remote_worker._maybe_reexec_under_xvfb()
        execvpe.assert_not_called()

    def test_reexec_raises_if_display_still_missing_after_retry(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "MINIMAX_BROWSER_HEADLESS": "false",
                "DISPLAY": "",
                "FORMCHECK_XVFB_REEXEC": "true",
            },
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                minimax_remote_worker._maybe_reexec_under_xvfb()


if __name__ == "__main__":
    unittest.main()
