"""Automatic resume: bounded backoff, fresh gates, same pin, cancellation,
foreground precedence, sleep detection and duplicate-send protection."""

import threading
import time

from helpers import RouterTestCase
from model_router.adapters.fake import SimulatedCrash
from model_router.contracts import JobState
from model_router.coordinator import Coordinator
from model_router.scheduler import AutoResumer


class FakeClock:
    def __init__(self):
        self.mono = 1000.0
        self.wall = 1_790_000_000.0

    def advance(self, seconds, *, slept=0.0):
        self.mono += seconds
        self.wall += seconds + slept


class AutoResume(RouterTestCase):
    def resumer(self, coordinator=None, clock=None, **kw):
        clock = clock or FakeClock()
        return AutoResumer(coordinator or self.coordinator, min_interval=30, max_interval=900,
                           monotonic=lambda: clock.mono, wall=lambda: clock.wall, jitter=0.0, **kw), clock

    def queued_job(self, text="Implement the CSV import per the agreed architecture"):
        self.scenario.ordinary_usage_allowed = False
        result, state = self.submit_and_run(text)
        self.assertEqual(state, JobState.WAITING_USAGE)
        return result

    def test_resumes_automatically_on_the_same_model_once_usage_returns(self):
        job = self.queued_job()
        resumer, _ = self.resumer()
        first = resumer.tick()
        self.assertEqual(first.resumed, [(job.job_id, "WAITING_USAGE")])
        self.assertEqual(self.adapter.model_sends, 0)
        self.scenario.ordinary_usage_allowed = True
        second = resumer.tick()
        self.assertEqual(second.resumed, [(job.job_id, "SUCCEEDED")])
        self.assertEqual([t["model"] for t in self.adapter.sent_turns], ["sim-sol-1"])
        self.assertEqual(resumer.tick().resumed, [], "nothing left; no resend")
        self.assertEqual(self.adapter.model_sends, 1)

    def test_backoff_doubles_is_bounded_and_resets_on_progress(self):
        self.queued_job()
        resumer, _ = self.resumer()
        delays = [resumer.tick().next_delay for _ in range(7)]
        self.assertEqual(delays, [60, 120, 240, 480, 900, 900, 900])
        self.scenario.ordinary_usage_allowed = True
        resumer.tick()
        self.queued_job("Implement the TSV import per the agreed architecture")
        self.assertEqual(resumer.tick().next_delay, 60)

    def test_reported_reset_schedules_an_earlier_check_but_proves_nothing(self):
        from datetime import datetime, timedelta, timezone

        soon = (datetime.now(timezone.utc) + timedelta(seconds=100)).isoformat().replace("+00:00", "Z")
        self.scenario.buckets[0]["resets_at"] = soon
        job = self.queued_job()
        resumer, _ = self.resumer()
        for _ in range(4):
            result = resumer.tick()
        self.assertLessEqual(result.next_delay, 106)
        self.assertEqual(self.job_state(job.job_id), "WAITING_USAGE", "the due time alone did not dispatch")
        self.assertEqual(self.adapter.model_sends, 0)

    def test_cancelled_work_is_never_resumed(self):
        job = self.queued_job()
        self.coordinator.cancel(job.job_id)
        self.scenario.ordinary_usage_allowed = True
        resumer, _ = self.resumer()
        self.assertEqual(resumer.tick().waiting, 0)
        self.assertEqual(self.adapter.model_sends, 0)

    def test_foreground_turn_takes_precedence(self):
        self.queued_job()
        self.scenario.ordinary_usage_allowed = True
        resumer, _ = self.resumer()
        self.coordinator._turn_lock.acquire()
        try:
            holder = threading.Thread(target=lambda: setattr(self, "tick_result", resumer.tick()))
            holder.start()
            holder.join(5)
        finally:
            self.coordinator._turn_lock.release()
        self.assertEqual(self.tick_result.resumed, [], "deferred while a foreground turn runs")
        self.assertEqual(self.adapter.model_sends, 0)

    def test_sleep_is_detected_and_reconciled_before_continuing(self):
        result = self.coordinator.submit("Portfolio", "Format my notes")
        self.scenario.crash_at = "after_send_before_ack"
        try:
            self.coordinator.run(result.job_id)
        except SimulatedCrash:
            pass
        resumer, clock = self.resumer()
        clock.advance(5, slept=3600)  # the Mac slept for an hour
        tick = resumer.tick()
        self.assertTrue(tick.reconciled_after_sleep)
        self.assertEqual(self.job_state(result.job_id), "SUCCEEDED")
        self.assertEqual(self.adapter.model_sends, 1)
        self.assertTrue(self.events("scheduler.woke_from_sleep"))

    def test_two_running_routers_never_double_send(self):
        job = self.queued_job()
        self.scenario.ordinary_usage_allowed = True
        other = Coordinator(self.store, self.adapter, live=False, ui=self.ui)
        other.start()
        r1, _ = self.resumer()
        r2, _ = self.resumer(coordinator=other)
        barrier = threading.Barrier(2)

        def go(r):
            barrier.wait()
            r.tick()

        threads = [threading.Thread(target=go, args=(r,)) for r in (r1, r2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(10)
        self.assertEqual(self.adapter.model_sends, 1)
        self.assertEqual(self.job_state(job.job_id), "SUCCEEDED")
        other.close()

    def test_background_thread_runs_and_stops(self):
        job = self.queued_job()
        resumer = AutoResumer(self.coordinator, min_interval=0.05, max_interval=0.2, jitter=0.0)
        resumer.start()
        try:
            self.scenario.ordinary_usage_allowed = True
            resumer.nudge()
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and self.job_state(job.job_id) != "SUCCEEDED":
                time.sleep(0.05)
        finally:
            resumer.stop()
        self.assertFalse(resumer.running)
        self.assertEqual(self.job_state(job.job_id), "SUCCEEDED")
        self.assertEqual(self.adapter.model_sends, 1)
        status = self.store.one("SELECT value FROM meta WHERE key='auto_resume'")
        self.assertIn("runs only while a router process is open", status["value"])
