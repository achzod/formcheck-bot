import asyncio
import time
import unittest
from types import SimpleNamespace

from analysis.minimax_motion_coach import MiniMaxAnalysis, _analysis_to_payload

try:
    from app import handlers
    _HANDLERS_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - local env may miss app deps
    handlers = None
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


if __name__ == "__main__":
    unittest.main()
