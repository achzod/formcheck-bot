import asyncio
import os
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from fastapi.testclient import TestClient
from analysis.minimax_motion_coach import MiniMaxAnalysis, _analysis_to_payload

try:
    from app import database as db
    from app import handlers
    from app import main
    from app import minimax_remote_worker
    from sqlalchemy.dialects import sqlite
    _HANDLERS_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - local env may miss app deps
    db = None
    handlers = None
    main = None
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
            status="processing",
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
            data = dict(job.__dict__)
            data["status"] = "completed"
            return SimpleNamespace(**data)

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
            status="processing",
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
            data = dict(job.__dict__)
            data["status"] = "completed"
            return SimpleNamespace(**data)

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

    def test_complete_remote_minimax_job_ignores_non_processing_callback(self) -> None:
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
            id=27,
            analysis_id=62,
            user_id=9,
            phone="+33655555555",
            video_path="/tmp/stale-complete.mp4",
            status="failed",
        )

        original_get = handlers.db.get_minimax_remote_job
        original_complete = handlers.db.complete_minimax_remote_job
        original_deliver = handlers._deliver_pipeline_success
        original_active = dict(handlers._active_analyses)
        handlers._active_analyses[job.phone] = time.time()

        async def fake_get(job_id: int):
            self.assertEqual(job_id, 27)
            return job

        async def fake_complete(_job_id: int, _result_payload: str):
            raise AssertionError("complete_minimax_remote_job must not be called for non-processing jobs")

        async def fake_deliver(**_kwargs):
            raise AssertionError("_deliver_pipeline_success must not run for stale completion callbacks")

        try:
            handlers.db.get_minimax_remote_job = fake_get
            handlers.db.complete_minimax_remote_job = fake_complete
            handlers._deliver_pipeline_success = fake_deliver
            ok = asyncio.run(handlers.complete_remote_minimax_job(27, payload))
        finally:
            handlers.db.get_minimax_remote_job = original_get
            handlers.db.complete_minimax_remote_job = original_complete
            handlers._deliver_pipeline_success = original_deliver
            handlers._active_analyses.clear()
            handlers._active_analyses.update(original_active)

        self.assertTrue(ok)

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
        original_get = handlers.db.get_minimax_remote_job
        original_send = handlers.wa.send_text
        original_cleanup = handlers.cleanup_video
        original_active = dict(handlers._active_analyses)
        handlers._active_analyses[job.phone] = time.time()

        async def fake_get(job_id: int):
            self.assertEqual(job_id, 8)
            return SimpleNamespace(**job.__dict__, status="processing")

        async def fake_fail(job_id: int, error: str):
            self.assertEqual(job_id, 8)
            self.assertIn("blocked", error)
            return SimpleNamespace(**job.__dict__, status="failed")

        async def fake_send_text(phone: str, text: str):
            sent.append((phone, text))

        def fake_cleanup(path: str):
            cleaned.append(path)

        try:
            handlers.db.get_minimax_remote_job = fake_get
            handlers.db.fail_minimax_remote_job = fake_fail
            handlers.wa.send_text = fake_send_text
            handlers.cleanup_video = fake_cleanup
            ok = asyncio.run(handlers.fail_remote_minimax_job(8, "blocked by anti-bot"))
        finally:
            handlers.db.get_minimax_remote_job = original_get
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
        original_get = handlers.db.get_minimax_remote_job
        original_send = handlers.wa.send_text
        original_cleanup = handlers.cleanup_video
        original_active = dict(handlers._active_analyses)
        handlers._active_analyses[job.phone] = time.time()

        async def fake_get(job_id: int):
            self.assertEqual(job_id, 18)
            return job

        async def fake_fail(job_id: int, error: str):
            self.assertEqual(job_id, 18)
            self.assertIn("already completed", error)
            return job

        async def fake_send_text(phone: str, text: str):
            sent.append((phone, text))

        def fake_cleanup(path: str):
            cleaned.append(path)

        try:
            handlers.db.get_minimax_remote_job = fake_get
            handlers.db.fail_minimax_remote_job = fake_fail
            handlers.wa.send_text = fake_send_text
            handlers.cleanup_video = fake_cleanup
            ok = asyncio.run(handlers.fail_remote_minimax_job(18, "already completed upstream"))
        finally:
            handlers.db.get_minimax_remote_job = original_get
            handlers.db.fail_minimax_remote_job = original_fail
            handlers.wa.send_text = original_send
            handlers.cleanup_video = original_cleanup
            handlers._active_analyses.clear()
            handlers._active_analyses.update(original_active)

        self.assertTrue(ok)
        self.assertEqual(sent, [])
        self.assertEqual(cleaned, [])
        self.assertNotIn(job.phone, handlers._active_analyses)

    def test_fail_remote_minimax_job_ignores_duplicate_failed_callback(self) -> None:
        job = SimpleNamespace(
            id=28,
            analysis_id=101,
            user_id=6,
            phone="+33666666666",
            video_path="/tmp/already-failed-video.mp4",
            status="failed",
        )
        sent: list[tuple[str, str]] = []

        original_get = handlers.db.get_minimax_remote_job
        original_fail = handlers.db.fail_minimax_remote_job
        original_send = handlers.wa.send_text
        original_active = dict(handlers._active_analyses)
        handlers._active_analyses[job.phone] = time.time()

        async def fake_get(job_id: int):
            self.assertEqual(job_id, 28)
            return job

        async def fake_fail(_job_id: int, _error: str):
            raise AssertionError("fail_minimax_remote_job must not run on duplicate failed callbacks")

        async def fake_send_text(phone: str, text: str):
            sent.append((phone, text))

        try:
            handlers.db.get_minimax_remote_job = fake_get
            handlers.db.fail_minimax_remote_job = fake_fail
            handlers.wa.send_text = fake_send_text
            ok = asyncio.run(handlers.fail_remote_minimax_job(28, "duplicate fail callback"))
        finally:
            handlers.db.get_minimax_remote_job = original_get
            handlers.db.fail_minimax_remote_job = original_fail
            handlers.wa.send_text = original_send
            handlers._active_analyses.clear()
            handlers._active_analyses.update(original_active)

        self.assertTrue(ok)
        self.assertEqual(sent, [])

    def test_get_blocking_remote_job_for_phone_auto_expires_old_job(self) -> None:
        phone = "+33677777777"
        stale_job = SimpleNamespace(
            id=31,
            phone=phone,
            status="processing",
            video_path="/tmp/stale-remote-job.mp4",
            created_at=db.dt.datetime.utcnow() - db.dt.timedelta(seconds=3600),
        )
        events: list[tuple[str, object]] = []

        original_timeout = handlers.app_settings.minimax_remote_phone_job_block_timeout_s
        original_get_open = handlers.db.get_open_minimax_remote_job_for_phone
        original_fail = handlers.db.fail_minimax_remote_job
        original_cleanup = handlers.cleanup_video
        original_active = dict(handlers._active_analyses)
        handlers._active_analyses[phone] = time.time()

        async def fake_get_open(_phone: str):
            self.assertEqual(_phone, phone)
            return stale_job

        async def fake_fail(job_id: int, error: str):
            events.append(("fail", job_id, error))
            return stale_job

        def fake_cleanup(path: str):
            events.append(("cleanup", path))

        try:
            handlers.app_settings.minimax_remote_phone_job_block_timeout_s = 120
            handlers.db.get_open_minimax_remote_job_for_phone = fake_get_open
            handlers.db.fail_minimax_remote_job = fake_fail
            handlers.cleanup_video = fake_cleanup
            result = asyncio.run(handlers._get_blocking_remote_job_for_phone(phone))
        finally:
            handlers.app_settings.minimax_remote_phone_job_block_timeout_s = original_timeout
            handlers.db.get_open_minimax_remote_job_for_phone = original_get_open
            handlers.db.fail_minimax_remote_job = original_fail
            handlers.cleanup_video = original_cleanup
            handlers._active_analyses.clear()
            handlers._active_analyses.update(original_active)

        self.assertIsNone(result)
        self.assertTrue(any(evt[0] == "fail" and evt[1] == 31 for evt in events))
        self.assertTrue(any(evt[0] == "cleanup" and evt[1] == "/tmp/stale-remote-job.mp4" for evt in events))
        self.assertNotIn(phone, handlers._active_analyses)

    def test_get_blocking_remote_job_for_phone_keeps_fresh_job(self) -> None:
        phone = "+33688888888"
        fresh_job = SimpleNamespace(
            id=32,
            phone=phone,
            status="processing",
            video_path="/tmp/fresh-remote-job.mp4",
            created_at=db.dt.datetime.utcnow() - db.dt.timedelta(seconds=30),
        )

        original_timeout = handlers.app_settings.minimax_remote_phone_job_block_timeout_s
        original_get_open = handlers.db.get_open_minimax_remote_job_for_phone
        original_fail = handlers.db.fail_minimax_remote_job
        original_cleanup = handlers.cleanup_video

        async def fake_get_open(_phone: str):
            self.assertEqual(_phone, phone)
            return fresh_job

        async def fake_fail(_job_id: int, _error: str):
            raise AssertionError("fresh job must not be auto-expired")

        def fake_cleanup(_path: str):
            raise AssertionError("fresh job video must not be cleaned")

        try:
            handlers.app_settings.minimax_remote_phone_job_block_timeout_s = 600
            handlers.db.get_open_minimax_remote_job_for_phone = fake_get_open
            handlers.db.fail_minimax_remote_job = fake_fail
            handlers.cleanup_video = fake_cleanup
            result = asyncio.run(handlers._get_blocking_remote_job_for_phone(phone))
        finally:
            handlers.app_settings.minimax_remote_phone_job_block_timeout_s = original_timeout
            handlers.db.get_open_minimax_remote_job_for_phone = original_get_open
            handlers.db.fail_minimax_remote_job = original_fail
            handlers.cleanup_video = original_cleanup

        self.assertIs(result, fresh_job)

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

    def test_heartbeat_job_touches_processing_job(self) -> None:
        now = db.dt.datetime.utcnow()
        job = SimpleNamespace(
            id=12,
            status="processing",
            worker_id="worker-a",
            updated_at=now - db.dt.timedelta(seconds=600),
        )
        captured = {}

        class _FakeSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, _model, job_id: int):
                captured["job_id"] = job_id
                return job

            async def commit(self):
                captured["committed"] = True

        original_async_session = db.async_session
        try:
            db.async_session = lambda: _FakeSession()
            ok = asyncio.run(db.heartbeat_minimax_remote_job(12, "worker-a"))
        finally:
            db.async_session = original_async_session

        self.assertTrue(ok)
        self.assertEqual(captured.get("job_id"), 12)
        self.assertTrue(captured.get("committed"))
        self.assertGreater(job.updated_at, now)


@unittest.skipIf(main is None, "app deps unavailable: {}".format(_HANDLERS_IMPORT_ERROR))
class RemoteMiniMaxHeartbeatEndpointTests(unittest.TestCase):
    def test_heartbeat_endpoint_accepts_allowed_worker(self) -> None:
        client = TestClient(main.app)
        token_snapshot = main.settings.minimax_remote_worker_token
        render_snapshot = main.settings.render_api_key
        enabled_snapshot = main.settings.minimax_remote_worker_enabled
        base_url_snapshot = main.settings.base_url
        test_mode_snapshot = main.settings.test_mode
        allowed_ids_snapshot = main.settings.minimax_remote_worker_allowed_ids
        allowed_prefixes_snapshot = main.settings.minimax_remote_worker_allowed_prefixes
        original_heartbeat = main.db.heartbeat_minimax_remote_job
        try:
            main.settings.minimax_remote_worker_token = "worker-token"
            main.settings.render_api_key = ""
            main.settings.minimax_remote_worker_enabled = True
            main.settings.base_url = "https://formcheck-bot.onrender.com"
            main.settings.test_mode = False
            main.settings.minimax_remote_worker_allowed_ids = ""
            main.settings.minimax_remote_worker_allowed_prefixes = ""

            async def fake_heartbeat(job_id: int, worker_id: str | None = None):
                self.assertEqual(job_id, 21)
                self.assertEqual(worker_id, "srv-d6o382rh46gs73a59h8g-jgc2l-29")
                return True

            main.db.heartbeat_minimax_remote_job = fake_heartbeat
            response = client.post(
                "/internal/minimax/jobs/21/heartbeat",
                headers={"X-Formcheck-Internal-Token": "worker-token"},
                json={"worker_id": "srv-d6o382rh46gs73a59h8g-jgc2l-29"},
            )
        finally:
            main.db.heartbeat_minimax_remote_job = original_heartbeat
            main.settings.minimax_remote_worker_token = token_snapshot
            main.settings.render_api_key = render_snapshot
            main.settings.minimax_remote_worker_enabled = enabled_snapshot
            main.settings.base_url = base_url_snapshot
            main.settings.test_mode = test_mode_snapshot
            main.settings.minimax_remote_worker_allowed_ids = allowed_ids_snapshot
            main.settings.minimax_remote_worker_allowed_prefixes = allowed_prefixes_snapshot

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


@unittest.skipIf(main is None, "app deps unavailable: {}".format(_HANDLERS_IMPORT_ERROR))
class RemoteMiniMaxClaimEndpointGuardTests(unittest.TestCase):
    def test_claim_endpoint_rejects_non_render_worker_id_in_prod(self) -> None:
        client = TestClient(main.app)
        token_snapshot = main.settings.minimax_remote_worker_token
        render_snapshot = main.settings.render_api_key
        enabled_snapshot = main.settings.minimax_remote_worker_enabled
        base_url_snapshot = main.settings.base_url
        test_mode_snapshot = main.settings.test_mode
        allowed_ids_snapshot = main.settings.minimax_remote_worker_allowed_ids
        allowed_prefixes_snapshot = main.settings.minimax_remote_worker_allowed_prefixes
        original_claim = main.db.claim_next_minimax_remote_job
        try:
            main.settings.minimax_remote_worker_token = "worker-token"
            main.settings.render_api_key = ""
            main.settings.minimax_remote_worker_enabled = True
            main.settings.base_url = "https://formcheck-bot.onrender.com"
            main.settings.test_mode = False
            main.settings.minimax_remote_worker_allowed_ids = ""
            main.settings.minimax_remote_worker_allowed_prefixes = ""

            async def fake_claim(_worker_id: str):
                raise AssertionError("claim_next_minimax_remote_job should not be called")

            main.db.claim_next_minimax_remote_job = fake_claim
            response = client.post(
                "/internal/minimax/jobs/claim",
                headers={"X-Formcheck-Internal-Token": "worker-token"},
                json={"worker_id": "MacBook-Pro-de-achkan.local-60518"},
            )
        finally:
            main.db.claim_next_minimax_remote_job = original_claim
            main.settings.minimax_remote_worker_token = token_snapshot
            main.settings.render_api_key = render_snapshot
            main.settings.minimax_remote_worker_enabled = enabled_snapshot
            main.settings.base_url = base_url_snapshot
            main.settings.test_mode = test_mode_snapshot
            main.settings.minimax_remote_worker_allowed_ids = allowed_ids_snapshot
            main.settings.minimax_remote_worker_allowed_prefixes = allowed_prefixes_snapshot

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json().get("detail"), "Worker not allowed")

    def test_claim_endpoint_accepts_render_api_key_when_worker_token_drifts(self) -> None:
        client = TestClient(main.app)
        token_snapshot = main.settings.minimax_remote_worker_token
        render_snapshot = main.settings.render_api_key
        enabled_snapshot = main.settings.minimax_remote_worker_enabled
        base_url_snapshot = main.settings.base_url
        test_mode_snapshot = main.settings.test_mode
        allowed_ids_snapshot = main.settings.minimax_remote_worker_allowed_ids
        allowed_prefixes_snapshot = main.settings.minimax_remote_worker_allowed_prefixes
        original_claim = main.db.claim_next_minimax_remote_job
        try:
            main.settings.minimax_remote_worker_token = "worker-token"
            main.settings.render_api_key = "render-token"
            main.settings.minimax_remote_worker_enabled = True
            main.settings.base_url = "https://formcheck-bot.onrender.com"
            main.settings.test_mode = False
            main.settings.minimax_remote_worker_allowed_ids = ""
            main.settings.minimax_remote_worker_allowed_prefixes = ""

            async def fake_claim(worker_id: str):
                return SimpleNamespace(
                    id=6,
                    analysis_id=15,
                    phone="+33600000000",
                    worker_id=worker_id,
                )

            main.db.claim_next_minimax_remote_job = fake_claim
            response = client.post(
                "/internal/minimax/jobs/claim",
                headers={"X-Formcheck-Internal-Token": "render-token"},
                json={"worker_id": "srv-d6o382rh46gs73a59h8g-jgc2l-29"},
            )
        finally:
            main.db.claim_next_minimax_remote_job = original_claim
            main.settings.minimax_remote_worker_token = token_snapshot
            main.settings.render_api_key = render_snapshot
            main.settings.minimax_remote_worker_enabled = enabled_snapshot
            main.settings.base_url = base_url_snapshot
            main.settings.test_mode = test_mode_snapshot
            main.settings.minimax_remote_worker_allowed_ids = allowed_ids_snapshot
            main.settings.minimax_remote_worker_allowed_prefixes = allowed_prefixes_snapshot

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job"]["id"], 6)


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
        original_ensure_display = minimax_remote_worker._ensure_display_for_headed_browser
        observed: dict[str, str | None] = {"headless": None, "channel": None}

        async def fake_claim(_client, _worker_id):
            observed["headless"] = os.environ.get("MINIMAX_BROWSER_HEADLESS")
            observed["channel"] = os.environ.get("MINIMAX_BROWSER_CHANNEL")
            raise asyncio.CancelledError()

        def fake_ensure_display():
            return None

        try:
            os.environ["MINIMAX_BROWSER_HEADLESS"] = "true"
            os.environ.pop("MINIMAX_BROWSER_CHANNEL", None)
            minimax_remote_worker._claim_job = fake_claim
            minimax_remote_worker._ensure_display_for_headed_browser = fake_ensure_display
            with self.assertRaises(asyncio.CancelledError):
                asyncio.run(minimax_remote_worker.run_worker())
        finally:
            minimax_remote_worker._claim_job = original_claim
            minimax_remote_worker._ensure_display_for_headed_browser = original_ensure_display
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

    def test_worker_id_treats_auto_env_as_hostname_fallback(self) -> None:
        with mock.patch.dict(os.environ, {"MINIMAX_REMOTE_WORKER_ID": "auto"}, clear=False):
            with mock.patch.object(minimax_remote_worker.socket, "gethostname", return_value="srv-test"):
                with mock.patch.object(minimax_remote_worker.os, "getpid", return_value=42):
                    self.assertEqual(minimax_remote_worker._worker_id(), "srv-test-42")

    def test_ensure_display_starts_xvfb_when_display_missing(self) -> None:
        fake_proc = mock.Mock()
        fake_proc.poll.return_value = None
        fake_proc.pid = 4321
        xvfb_snapshot = minimax_remote_worker._XVFB_PROCESS
        observed_display: str | None = None
        with mock.patch.dict(
            os.environ,
            {
                "MINIMAX_BROWSER_HEADLESS": "false",
                "DISPLAY": "",
            },
            clear=False,
        ):
            try:
                minimax_remote_worker._XVFB_PROCESS = None
                with mock.patch.object(minimax_remote_worker.shutil, "which", return_value="/usr/bin/Xvfb"):
                    with mock.patch.object(minimax_remote_worker.subprocess, "Popen", return_value=fake_proc) as popen:
                        with mock.patch.object(minimax_remote_worker.atexit, "register") as register:
                            with mock.patch.object(minimax_remote_worker.time, "sleep", return_value=None):
                                minimax_remote_worker._ensure_display_for_headed_browser()
                                observed_display = os.environ.get("DISPLAY")
            finally:
                minimax_remote_worker._XVFB_PROCESS = xvfb_snapshot

        popen.assert_called_once()
        args = popen.call_args.args[0]
        self.assertEqual(
            args,
            [
                "/usr/bin/Xvfb",
                ":99",
                "-screen",
                "0",
                "1920x1080x24",
                "-nolisten",
                "tcp",
                "-ac",
            ],
        )
        register.assert_called_once()
        self.assertEqual(observed_display, ":99")

    def test_ensure_display_is_skipped_when_display_present(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "MINIMAX_BROWSER_HEADLESS": "false",
                "DISPLAY": ":99",
            },
            clear=False,
        ):
            with mock.patch.object(minimax_remote_worker.subprocess, "Popen") as popen:
                minimax_remote_worker._ensure_display_for_headed_browser()
        popen.assert_not_called()

    def test_ensure_display_raises_if_xvfb_missing(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "MINIMAX_BROWSER_HEADLESS": "false",
                "DISPLAY": "",
            },
            clear=False,
        ):
            with mock.patch.object(minimax_remote_worker.shutil, "which", return_value=None):
                with self.assertRaises(RuntimeError):
                    minimax_remote_worker._ensure_display_for_headed_browser()

    def test_analysis_subprocess_timeout_respects_hard_cap(self) -> None:
        runtime_settings = minimax_remote_worker.minimax_motion_coach.settings
        original_max_effective = getattr(runtime_settings, "minimax_max_effective_timeout_s", None)
        original_grace = os.environ.get("MINIMAX_REMOTE_JOB_TIMEOUT_GRACE_S")
        original_cap = os.environ.get("MINIMAX_REMOTE_JOB_MAX_TIMEOUT_S")
        try:
            runtime_settings.minimax_max_effective_timeout_s = 900
            os.environ["MINIMAX_REMOTE_JOB_TIMEOUT_GRACE_S"] = "180"
            os.environ["MINIMAX_REMOTE_JOB_MAX_TIMEOUT_S"] = "540"
            self.assertEqual(minimax_remote_worker._analysis_subprocess_timeout_s(), 540)

            os.environ["MINIMAX_REMOTE_JOB_MAX_TIMEOUT_S"] = "2000"
            self.assertEqual(minimax_remote_worker._analysis_subprocess_timeout_s(), 1080)
        finally:
            runtime_settings.minimax_max_effective_timeout_s = original_max_effective
            if original_grace is None:
                os.environ.pop("MINIMAX_REMOTE_JOB_TIMEOUT_GRACE_S", None)
            else:
                os.environ["MINIMAX_REMOTE_JOB_TIMEOUT_GRACE_S"] = original_grace
            if original_cap is None:
                os.environ.pop("MINIMAX_REMOTE_JOB_MAX_TIMEOUT_S", None)
            else:
                os.environ["MINIMAX_REMOTE_JOB_MAX_TIMEOUT_S"] = original_cap

    def test_analysis_subprocess_abort_helper_detects_browserless_stall(self) -> None:
        should_abort = minimax_remote_worker._analysis_subprocess_should_abort_early(
            elapsed_s=52.0,
            result_size_bytes=0,
            browser_alive=False,
            browser_seen=False,
            idle_without_browser_s=52.0,
            stall_after_s=45.0,
        )
        self.assertTrue(should_abort)

        should_abort_after_exit = minimax_remote_worker._analysis_subprocess_should_abort_early(
            elapsed_s=90.0,
            result_size_bytes=0,
            browser_alive=False,
            browser_seen=True,
            idle_without_browser_s=50.0,
            stall_after_s=45.0,
        )
        self.assertTrue(should_abort_after_exit)

        should_continue = minimax_remote_worker._analysis_subprocess_should_abort_early(
            elapsed_s=30.0,
            result_size_bytes=0,
            browser_alive=False,
            browser_seen=False,
            idle_without_browser_s=30.0,
            stall_after_s=45.0,
        )
        self.assertFalse(should_continue)

    def test_subprocess_browser_detection_ignores_driver_only_and_crashpad(self) -> None:
        original_descendants = minimax_remote_worker._descendant_cmdlines
        try:
            minimax_remote_worker._descendant_cmdlines = lambda _pid: [
                "/ms-playwright/driver/node cli.js run-driver",
                "/chrome_crashpad_handler --monitor-self",
            ]
            self.assertFalse(minimax_remote_worker._subprocess_has_live_browser_descendants(123))
        finally:
            minimax_remote_worker._descendant_cmdlines = original_descendants

    def test_subprocess_browser_detection_accepts_real_chrome_process(self) -> None:
        original_descendants = minimax_remote_worker._descendant_cmdlines
        try:
            minimax_remote_worker._descendant_cmdlines = lambda _pid: [
                "/ms-playwright/chromium-1161/chrome-linux64/chrome --type=zygote --no-zygote-sandbox",
            ]
            self.assertTrue(minimax_remote_worker._subprocess_has_live_browser_descendants(123))
        finally:
            minimax_remote_worker._descendant_cmdlines = original_descendants

    def test_download_video_streams_to_disk_and_respects_chunking(self) -> None:
        class FakeStreamResponse:
            def __init__(self) -> None:
                self.headers = {"content-length": "12"}

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self) -> None:
                return None

            async def aiter_bytes(self, chunk_size: int = 0):
                self.chunk_size = chunk_size
                yield b"abc"
                yield b"defgh"
                yield b"ijkl"

        class FakeClient:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str, dict, float]] = []
                self.response = FakeStreamResponse()

            def stream(self, method: str, url: str, headers: dict, timeout: float):
                self.calls.append((method, url, headers, timeout))
                return self.response

        client = FakeClient()
        original_headers = minimax_remote_worker._headers
        original_chunk_env = os.environ.get("MINIMAX_REMOTE_VIDEO_DOWNLOAD_CHUNK_MB")
        original_max_env = os.environ.get("MINIMAX_REMOTE_VIDEO_MAX_MB")
        original_timeout_env = os.environ.get("MINIMAX_REMOTE_VIDEO_DOWNLOAD_TIMEOUT_S")
        downloaded_path = None

        try:
            minimax_remote_worker._headers = lambda: {"X-Test": "1"}
            os.environ["MINIMAX_REMOTE_VIDEO_DOWNLOAD_CHUNK_MB"] = "1"
            os.environ["MINIMAX_REMOTE_VIDEO_MAX_MB"] = "64"
            os.environ["MINIMAX_REMOTE_VIDEO_DOWNLOAD_TIMEOUT_S"] = "321"
            downloaded_path = asyncio.run(
                minimax_remote_worker._download_video(
                    client,
                    42,
                    "https://example.com/demo.mp4",
                )
            )
            self.assertTrue(downloaded_path.exists())
            self.assertEqual(downloaded_path.read_bytes(), b"abcdefghijkl")
            self.assertEqual(client.calls[0][0], "GET")
            self.assertEqual(client.calls[0][1], "https://example.com/demo.mp4")
            self.assertEqual(client.calls[0][2], {"X-Test": "1"})
            self.assertEqual(client.calls[0][3], 321.0)
            self.assertEqual(client.response.chunk_size, 1024 * 1024)
        finally:
            minimax_remote_worker._headers = original_headers
            if downloaded_path is not None:
                downloaded_path.unlink(missing_ok=True)
            if original_chunk_env is None:
                os.environ.pop("MINIMAX_REMOTE_VIDEO_DOWNLOAD_CHUNK_MB", None)
            else:
                os.environ["MINIMAX_REMOTE_VIDEO_DOWNLOAD_CHUNK_MB"] = original_chunk_env
            if original_max_env is None:
                os.environ.pop("MINIMAX_REMOTE_VIDEO_MAX_MB", None)
            else:
                os.environ["MINIMAX_REMOTE_VIDEO_MAX_MB"] = original_max_env
            if original_timeout_env is None:
                os.environ.pop("MINIMAX_REMOTE_VIDEO_DOWNLOAD_TIMEOUT_S", None)
            else:
                os.environ["MINIMAX_REMOTE_VIDEO_DOWNLOAD_TIMEOUT_S"] = original_timeout_env

    def test_download_video_rejects_oversized_content_length(self) -> None:
        class FakeStreamResponse:
            def __init__(self) -> None:
                self.headers = {"content-length": str(128 * 1024 * 1024)}

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self) -> None:
                return None

            async def aiter_bytes(self, chunk_size: int = 0):
                if False:
                    yield b""

        class FakeClient:
            def stream(self, method: str, url: str, headers: dict, timeout: float):
                return FakeStreamResponse()

        original_headers = minimax_remote_worker._headers
        original_max_env = os.environ.get("MINIMAX_REMOTE_VIDEO_MAX_MB")
        try:
            minimax_remote_worker._headers = lambda: {"X-Test": "1"}
            os.environ["MINIMAX_REMOTE_VIDEO_MAX_MB"] = "32"
            with self.assertRaises(RuntimeError):
                asyncio.run(
                    minimax_remote_worker._download_video(
                        FakeClient(),
                        77,
                        "https://example.com/heavy.mp4",
                    )
                )
        finally:
            minimax_remote_worker._headers = original_headers
            if original_max_env is None:
                os.environ.pop("MINIMAX_REMOTE_VIDEO_MAX_MB", None)
            else:
                os.environ["MINIMAX_REMOTE_VIDEO_MAX_MB"] = original_max_env

    def test_kill_orphan_browser_processes_targets_only_browser_like_cmdlines(self) -> None:
        open_original = open
        cmdlines = {
            "/proc/111/cmdline": b"/usr/bin/python worker.py",
            "/proc/222/cmdline": b"/ms-playwright/chromium-1161/chrome-linux64/chrome --type=renderer",
            "/proc/333/cmdline": b"/chrome_crashpad_handler --monitor-self",
        }
        killed: list[tuple[int, int]] = []

        def fake_open(path: str, mode: str = "r", *args, **kwargs):
            if path in cmdlines:
                return mock.mock_open(read_data=cmdlines[path]).return_value
            return open_original(path, mode, *args, **kwargs)

        with mock.patch.object(minimax_remote_worker.os, "listdir", return_value=["111", "222", "333"]):
            with mock.patch.object(minimax_remote_worker.os, "getpid", return_value=999):
                with mock.patch("builtins.open", side_effect=fake_open):
                    with mock.patch.object(minimax_remote_worker.os, "kill", side_effect=lambda pid, sig: killed.append((pid, sig))):
                        with mock.patch.object(minimax_remote_worker.time, "sleep", return_value=None):
                            cleaned = minimax_remote_worker._kill_orphan_browser_processes()

        self.assertEqual(cleaned, 2)
        self.assertEqual(
            killed,
            [
                (222, minimax_remote_worker.signal.SIGTERM),
                (222, 0),
                (222, minimax_remote_worker.signal.SIGKILL),
                (333, minimax_remote_worker.signal.SIGTERM),
                (333, 0),
                (333, minimax_remote_worker.signal.SIGKILL),
            ],
        )

    def test_process_job_uses_subprocess_payload_and_completes(self) -> None:
        payload = _analysis_to_payload(
            MiniMaxAnalysis(
                exercise_slug="lat_pulldown",
                exercise_display="Lat Pulldown",
                score=81,
                reps_total=9,
                intensity_score=77,
                report_text="Rapport MiniMax",
            )
        )
        events: list[tuple[str, object]] = []
        original_download = minimax_remote_worker._download_video
        original_run_subprocess = minimax_remote_worker._run_analysis_subprocess
        original_complete = minimax_remote_worker._complete_job
        original_fail = minimax_remote_worker._fail_job
        original_heartbeat_loop = minimax_remote_worker._job_heartbeat_loop
        original_unlink = minimax_remote_worker.Path.unlink

        async def fake_download(_client, job_id: int, video_url: str):
            self.assertEqual(job_id, 21)
            self.assertEqual(video_url, "https://example.com/video.mp4")
            return minimax_remote_worker.Path("/tmp/fake-video.mp4")

        async def fake_run_subprocess(video_path):
            self.assertEqual(str(video_path), "/tmp/fake-video.mp4")
            return payload

        async def fake_complete(_client, job_id: int, analysis_payload: str):
            events.append(("complete", job_id, analysis_payload))

        async def fake_fail(_client, job_id: int, error: str):
            events.append(("fail", job_id, error))

        async def fake_heartbeat_loop(_client, *, job_id: int, worker_id: str, stop_event: asyncio.Event):
            events.append(("heartbeat_loop", job_id, worker_id))
            await stop_event.wait()

        def fake_unlink(self, missing_ok: bool = False):
            events.append(("unlink", str(self), missing_ok))

        try:
            minimax_remote_worker._download_video = fake_download
            minimax_remote_worker._run_analysis_subprocess = fake_run_subprocess
            minimax_remote_worker._complete_job = fake_complete
            minimax_remote_worker._fail_job = fake_fail
            minimax_remote_worker._job_heartbeat_loop = fake_heartbeat_loop
            minimax_remote_worker.Path.unlink = fake_unlink
            asyncio.run(
                minimax_remote_worker._process_job(
                    object(),
                    {"id": 21, "video_url": "https://example.com/video.mp4"},
                    "worker-123",
                )
            )
        finally:
            minimax_remote_worker._download_video = original_download
            minimax_remote_worker._run_analysis_subprocess = original_run_subprocess
            minimax_remote_worker._complete_job = original_complete
            minimax_remote_worker._fail_job = original_fail
            minimax_remote_worker._job_heartbeat_loop = original_heartbeat_loop
            minimax_remote_worker.Path.unlink = original_unlink

        self.assertIn(("heartbeat_loop", 21, "worker-123"), events)
        self.assertIn(("complete", 21, payload), events)
        self.assertIn(("unlink", "/tmp/fake-video.mp4", True), events)
        self.assertEqual(len(events), 3)


if __name__ == "__main__":
    unittest.main()
