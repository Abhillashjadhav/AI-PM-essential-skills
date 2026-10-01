"""Regression tests for defects found in the independent code review."""

import stat
import sys

from helpers import FAKE_CODEX, RouterTestCase
from model_router.adapters.codex_stdio import CodexConfig, CodexStdioAdapter, PinManifest
from model_router.contracts import Binding, JobState, Role, SpendStatus
from model_router.coordinator import Coordinator
from model_router.doctor import pin_installation
from model_router.evals.metrics import iso_week, weekly_report
from model_router.evals.runner import build_live_plan, run_live
from model_router.contracts import utc_now


class LeaseAndRecovery(RouterTestCase):
    def test_recover_does_not_touch_a_live_dispatch(self):
        result = self.coordinator.submit("Portfolio", "Format my notes")
        other = Coordinator(self.store, self.adapter, live=False, ui=self.ui)
        other.start()
        started = {}
        original_create = self.adapter.create_thread

        def create_while_other_recovers(*args, **kwargs):
            started["report"] = other.recover()  # terminal B starts while A is mid-dispatch
            return original_create(*args, **kwargs)

        self.adapter.create_thread = create_while_other_recovers
        self.assertEqual(self.coordinator.run(result.job_id), JobState.SUCCEEDED)
        self.assertEqual(started["report"], [], "recovery skipped because a live process holds the lease")
        self.assertEqual(self.adapter.model_sends, 1)
        other.close()

    def test_settled_dispatch_is_never_sent(self):
        result = self.coordinator.submit("Portfolio", "Format my notes")
        original_create = self.adapter.create_thread

        def settle_then_create(*args, **kwargs):
            self.store.execute("UPDATE dispatches SET phase='NOT_EXECUTED' WHERE job_id=?", (result.job_id,))
            return original_create(*args, **kwargs)

        self.adapter.create_thread = settle_then_create
        self.coordinator.run(result.job_id)
        self.assertEqual(self.adapter.model_sends, 0)
        self.assertTrue(self.events("dispatch.abandoned"))

    def test_resume_error_holds_without_sticking(self):
        first, _ = self.submit_and_run("Format my notes")
        self.scenario.resume_error = "thread not found"
        fresh = self.make_coordinator()
        fresh.start()
        follow = fresh.submit("Portfolio", "more", thread_id=first.thread_id)
        self.assertEqual(fresh.run(follow.job_id), JobState.BLOCKED_CAPABILITY)
        self.assertEqual(self.store.one("SELECT phase FROM dispatches WHERE job_id=?", (follow.job_id,))["phase"], "NOT_EXECUTED")
        self.scenario.resume_error = None
        self.assertEqual(fresh.wake(), [(follow.job_id, JobState.SUCCEEDED)])
        fresh.close()

    def test_resend_when_gate_blocks_does_not_crash_and_resumes_later(self):
        from model_router.adapters.fake import SimulatedCrash

        result = self.coordinator.submit("Portfolio", "Format my notes")
        self.scenario.crash_at = "after_send_before_ack"
        self.scenario.echo_client_id = False
        try:
            self.coordinator.run(result.job_id)
        except SimulatedCrash:
            pass
        fresh = self.make_coordinator()
        fresh.start()
        fresh.recover()
        self.assertEqual(self.job_state(result.job_id), "RECOVERY_REQUIRED")
        self.scenario.spend_status = SpendStatus.UNKNOWN
        self.assertEqual(fresh.resolve_recovery(result.job_id, "resend"), JobState.BLOCKED_SPEND)
        self.scenario.spend_status = SpendStatus.ALLOWED_INCLUDED_ONLY
        self.assertEqual(fresh.wake(), [(result.job_id, JobState.SUCCEEDED)])
        fresh.close()

    def test_new_connection_forces_resume_check(self):
        first, _ = self.submit_and_run("Format my notes")
        self.adapter.connection_generation += 1  # the provider process was restarted
        self.scenario.resume_model = "sim-astra-1"
        _, state = self.submit_and_run("more", thread_id=first.thread_id)
        self.assertEqual(state, JobState.BLOCKED_CAPABILITY)
        self.assertTrue(self.events("model.resume_mismatch"))


class EvaluationLeftovers(RouterTestCase):
    def test_stopped_plan_leaves_no_dispatchable_jobs(self):
        self.scenario.spend_status = SpendStatus.UNKNOWN
        plan = build_live_plan([{"id": "c", "prompt": "x"}], ["sim-sol-1"])
        result = run_live(plan, self.coordinator, project="Portfolio", authorised_by="owner", allow_simulated=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.scenario.spend_status = SpendStatus.ALLOWED_INCLUDED_ONLY
        self.coordinator.wake()
        self.assertEqual(self.adapter.model_sends, 0)
        states = {r["state"] for r in self.store.all("SELECT state FROM jobs WHERE kind='evaluation'")}
        self.assertEqual(states, {"CANCELLED"})


class GuardrailEligibility(RouterTestCase):
    def test_answer_from_override_model_is_not_eligible(self):
        self.scenario.models = [m for m in self.scenario.models if m.model_id != "sim-luna-1"]
        result, state = self.submit_and_run("Format my notes")  # auto route: sim-luna-1, now unavailable
        self.assertEqual(state, JobState.BLOCKED_CAPABILITY)
        self.coordinator.override_model(result.thread_id, "sim-astra-1", reason="quality")
        self.coordinator.wake()
        report = weekly_report(self.store, iso_week(utc_now()), include_synthetic=True)
        self.assertEqual(report["guardrail"]["eligible_threads"], 0)
        self.assertEqual(report["system"]["blocked_or_no_answer_threads"], 1)


class AdapterRegressions(RouterTestCase):
    def wrapper(self):
        path = self.tmp / "codex"
        path.write_text(f"#!/bin/sh\nexec {sys.executable} {FAKE_CODEX} \"$@\"\n")
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
        return path

    def test_binary_replaced_after_pin_blocks_on_respawn(self):
        wrapper, home, data = self.wrapper(), self.tmp / "home", self.tmp / "pin-data"
        home.mkdir()
        review = pin_installation(data, codex_path=str(wrapper), codex_home=home, approve_digest=None, actor="owner")
        pin_installation(data, codex_path=str(wrapper), codex_home=home, approve_digest=review["digest"], actor="owner")
        adapter = CodexStdioAdapter(CodexConfig(data_dir=data, executable=str(wrapper), codex_home=home, request_timeout=5))
        self.addCleanup(adapter.close)
        self.assertEqual(adapter.initialise().pin["state"], "valid")
        adapter.read_account()
        wrapper.write_text(wrapper.read_text() + "# replaced\n")
        adapter._reset()
        adapter.read_account()  # respawn
        self.assertEqual(adapter.pin_state, "drift")
        with self.assertRaises(Exception):
            adapter.create_thread(Binding(role=Role.MIDDLE, model_id="fake-sol", reasoning_effort=None, registry_revision=1),
                                  developer_instructions=None, workspace=None, sandbox="read-only")

    def test_client_message_id_omitted_when_pinned_schema_lacks_it(self):
        wrapper, home, data = self.wrapper(), self.tmp / "home2", self.tmp / "pin2"
        home.mkdir()
        data.mkdir()
        PinManifest(str(wrapper), "v", "0" * 64, "0" * 64, {}, [],
                    ["TurnStartParams.clientUserMessageId absent: crash reconciliation limited to turn ids"], None, None).save(data / "adapter-pin.json")
        adapter = CodexStdioAdapter(CodexConfig(data_dir=data, executable=str(wrapper), codex_home=home, enforce_pin=False, request_timeout=5))
        self.addCleanup(adapter.close)
        adapter.initialise()
        self.assertFalse(adapter.send_client_message_id)
