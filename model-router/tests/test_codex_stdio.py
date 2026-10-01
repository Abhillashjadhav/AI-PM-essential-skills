"""Codex App Server adapter against a fake App Server *subprocess*: real
JSONL framing, interleaved notifications, server-initiated approvals, malformed
lines, crashes, pin drift and the spend decision."""

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import FAKE_CODEX, ROOT, RecordingUI
from model_router.adapters.base import AdapterError, DispatchUncertain
from model_router.adapters.codex_stdio import (
    CodexConfig,
    CodexStdioAdapter,
    check_schema_compat,
    inspect_installation,
    pin_status,
    translate_notification,
)
from model_router.contracts import Binding, JobState, Role, SpendStatus, utc_now
from model_router.coordinator import Coordinator
from model_router.doctor import pin_installation, run_doctor
from model_router.registry import mapping_hash_for
from model_router.store import Store

SCHEMA_FIXTURE = ROOT / "fixtures" / "codex-schema-min"


class FakeServerCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="codex-test-")
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "codex-home"
        self.home.mkdir()
        self.wrapper = self.tmp / "codex"
        self.wrapper.write_text(f"#!/bin/sh\nexec {sys.executable} {FAKE_CODEX} \"$@\"\n")
        self.wrapper.chmod(self.wrapper.stat().st_mode | stat.S_IEXEC)

    def tearDown(self):
        self._tmp.cleanup()

    def scenario(self, **values):
        (self.home / "fake-scenario.json").write_text(json.dumps(values))

    def log(self):
        path = self.home / "fake-log.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def adapter(self, *, enforce_pin=False, **kwargs):
        config = CodexConfig(
            data_dir=self.tmp / "data", executable=str(self.wrapper), codex_home=self.home, enforce_pin=enforce_pin,
            request_timeout=5, turn_idle_timeout=5, **kwargs,
        )
        (self.tmp / "data").mkdir(exist_ok=True)
        adapter = CodexStdioAdapter(config)
        self.addCleanup(adapter.close)
        return adapter


class Protocol(FakeServerCase):
    def test_account_models_usage_and_spend(self):
        adapter = self.adapter()
        adapter.initialise()
        account = adapter.read_account()
        self.assertEqual((account.auth_mode, account.plan_type, account.config_ok), ("chatgpt", "plus", True))
        self.assertTrue(account.account_scope.startswith("acct_"))
        self.assertNotIn("owner@example.invalid", json.dumps(account.raw_redacted))
        models = adapter.list_models().models
        self.assertEqual([m.model_id for m in models], ["fake-astra", "fake-sol"])
        self.assertEqual(models[0].reasoning_efforts, ["high", "medium"])
        usage = adapter.read_usage()
        self.assertEqual(usage.buckets[0].limit_id, "codex:primary")
        self.assertEqual(usage.buckets[0].used_percent, 12.0)
        self.assertTrue(usage.buckets[0].resets_at.endswith("Z"))
        self.assertEqual(usage.credits.has_credits, False)
        spend = adapter.check_spend_boundary(account, usage)
        self.assertEqual(spend.status, SpendStatus.UNKNOWN, "no verified enforcement -> never ALLOWED")
        self.assertTrue(spend.missing)
        first = self.log()[0]
        self.assertEqual(first, {"startup_env_names": first["startup_env_names"]})
        init = self.log()[1]
        self.assertEqual(init["method"], "initialize")
        self.assertNotIn("jsonrpc", init)
        self.assertEqual(self.log()[2], {"method": "initialized"})

    def test_api_key_variables_not_passed(self):
        os.environ["OPENAI_API_KEY"] = "sk-test-not-real"
        self.addCleanup(os.environ.pop, "OPENAI_API_KEY", None)
        adapter = self.adapter()
        adapter.initialise()
        adapter.read_account()
        self.assertIn("OPENAI_API_KEY", adapter.dropped_env)
        env_names = self.log()[0]["startup_env_names"]
        self.assertNotIn("OPENAI_API_KEY", env_names)
        self.assertIn("CODEX_HOME", env_names)
        self.assertIn('forced_login_method = "chatgpt"', (self.home / "config.toml").read_text())

    def test_B01_api_key_account_and_bad_config(self):
        self.scenario(account={"type": "apiKey"}, config={"forced_login_method": "api", "model_provider": "azure"})
        adapter = self.adapter()
        account = adapter.read_account()
        self.assertEqual(account.auth_mode, "apiKey")
        self.assertFalse(account.config_ok)
        self.assertEqual(len(account.config_problems), 2)

    def test_B04_missing_optional_fields_stay_unknown(self):
        self.scenario(rate_limits={"rateLimits": {"limitId": "codex"}})
        usage = self.adapter().read_usage()
        self.assertEqual(usage.buckets, [])
        self.assertFalse(usage.credits.reported)
        self.assertIsNone(usage.ordinary_usage_allowed)
        self.assertIsNone(usage.included_usage_available())

    def test_multi_bucket_form(self):
        self.scenario(rate_limits={"rateLimitsByLimitId": {
            "codex": {"primary": {"usedPercent": 40}, "secondary": {"usedPercent": 70, "resetsAt": 1790000000}},
            "codex_other": {"primary": {"usedPercent": 5}, "rateLimitReachedType": "rate_limit_reached"}},
            "rateLimits": {"primary": {"usedPercent": 1}}, "ordinaryUsageAllowed": True})
        usage = self.adapter().read_usage()
        self.assertEqual(sorted(b.limit_id for b in usage.buckets), ["codex:primary", "codex:secondary", "codex_other:primary"])
        self.assertFalse(usage.included_usage_available(), "a reached bucket means not available")

    def test_turn_stream_with_noise_approval_and_malformed_line(self):
        self.scenario(turn=[
            {"kind": "delta", "text": "Hel"},
            {"kind": "malformed"},
            {"kind": "other_thread_delta"},
            {"kind": "approval", "command": "rm -rf build"},
            {"kind": "warning", "text": "slow"},
            {"kind": "delta", "text": "lo"},
            {"kind": "completed", "status": "completed"},
        ])
        adapter = self.adapter()
        adapter.initialise()
        binding = Binding(role=Role.MIDDLE, model_id="fake-sol", reasoning_effort="medium", registry_revision=1)
        thread = adapter.create_thread(binding, developer_instructions="x", workspace=str(self.tmp), sandbox="read-only")
        seen = []
        events = list(adapter.start_turn(thread.provider_thread_id, "hi", "dsp_abc", binding=binding,
                                         approval_handler=lambda r: seen.append(r) or "decline"))
        kinds = [e.kind for e in events]
        self.assertEqual(kinds[0], "acknowledged")
        self.assertEqual("".join(e.text for e in events if e.kind == "delta"), "Hello")
        self.assertIn("approval", kinds)
        self.assertEqual(seen[0].command, "rm -rf build")
        self.assertEqual(events[-1].kind, "completed")
        self.assertTrue(adapter.rpc.malformed)
        turn_start = next(m for m in self.log() if m.get("method") == "turn/start")
        self.assertEqual(turn_start["params"]["clientUserMessageId"], "dsp_abc")
        self.assertEqual(turn_start["params"]["model"], "fake-sol")
        self.assertEqual(turn_start["params"]["effort"], "medium")
        reply = next(m for m in self.log() if m.get("id") == "srv-1")
        self.assertEqual(reply["result"], {"decision": "decline"})
        state = adapter.read_thread(thread.provider_thread_id)
        self.assertEqual(state.turns[0].client_message_id, "dsp_abc")

    def test_refuses_full_access_and_forbidden_methods(self):
        adapter = self.adapter()
        binding = Binding(role=Role.MIDDLE, model_id="fake-sol", reasoning_effort=None, registry_revision=1)
        with self.assertRaises(AdapterError):
            adapter.create_thread(binding, developer_instructions=None, workspace=None, sandbox="danger-full-access")
        adapter.read_account()
        with self.assertRaises(AdapterError):
            adapter.rpc.request("account/rateLimitResetCredit/consume", {}, 1)
        self.assertFalse(any(m.get("method") == "account/rateLimitResetCredit/consume" for m in self.log()))

    def test_turn_start_error_is_not_executed(self):
        self.scenario(turn_start_error="usage limit", turn_start_error_info="usageLimitExceeded")
        adapter = self.adapter()
        adapter.initialise()
        binding = Binding(role=Role.MIDDLE, model_id="fake-sol", reasoning_effort=None, registry_revision=1)
        thread = adapter.create_thread(binding, developer_instructions=None, workspace=None, sandbox="read-only")
        with self.assertRaises(AdapterError) as ctx:
            adapter.start_turn(thread.provider_thread_id, "hi", "dsp_1", binding=binding, approval_handler=lambda r: "decline")
        self.assertEqual((ctx.exception.executed, ctx.exception.code), ("no", "usageLimitExceeded"))

    def test_process_exit_mid_turn_is_uncertain(self):
        self.scenario(turn=[{"kind": "delta", "text": "x"}, {"kind": "exit"}])
        adapter = self.adapter()
        adapter.initialise()
        binding = Binding(role=Role.MIDDLE, model_id="fake-sol", reasoning_effort=None, registry_revision=1)
        thread = adapter.create_thread(binding, developer_instructions=None, workspace=None, sandbox="read-only")
        with self.assertRaises(DispatchUncertain):
            list(adapter.start_turn(thread.provider_thread_id, "hi", "dsp_2", binding=binding, approval_handler=lambda r: "decline"))

    def test_translation_rules(self):
        fatal = translate_notification("error", {"error": {"message": "x", "codexErrorInfo": "usageLimitExceeded"}, "willRetry": False}, "t")
        self.assertEqual((fatal.fatal, fatal.error_code), (True, "usageLimitExceeded"))
        retry = translate_notification("error", {"error": {"message": "x"}, "willRetry": True}, "t")
        self.assertFalse(retry.fatal)
        other = translate_notification("turn/completed", {"turn": {"id": "different", "status": "completed"}}, "t")
        self.assertIsNone(other)
        reroute = translate_notification("model/rerouted", {"fromModel": "a", "toModel": "b"}, "t")
        self.assertEqual((reroute.from_model, reroute.to_model), ("a", "b"))


class Pinning(FakeServerCase):
    def test_compat_check_on_fixture_and_missing_method(self):
        problems, _ = check_schema_compat(SCHEMA_FIXTURE)
        self.assertEqual(problems, [])
        self.scenario(schema_drop_method="turn/start")
        manifest, _ = inspect_installation(self.wrapper, self.home)
        self.assertIn("required client method missing: turn/start", manifest.compat_problems)

    def test_pin_review_approve_and_drift_blocks_sends(self):
        data = self.tmp / "data"
        review = pin_installation(data, codex_path=str(self.wrapper), codex_home=self.home, approve_digest=None, actor="owner")
        self.assertEqual(review["status"], "REVIEW")
        self.assertEqual(pin_installation(data, codex_path=str(self.wrapper), codex_home=self.home, approve_digest="0" * 64, actor="owner")["status"], "FAILED")
        pinned = pin_installation(data, codex_path=str(self.wrapper), codex_home=self.home, approve_digest=review["digest"], actor="owner")
        self.assertEqual(pinned["status"], "PINNED")
        adapter = self.adapter(enforce_pin=True)
        self.assertEqual(adapter.initialise().pin["state"], "valid")
        self.scenario(version="codex-cli 9.9.9-new")
        drifted = self.adapter(enforce_pin=True)
        caps = drifted.initialise()
        self.assertEqual(caps.pin["state"], "drift")
        self.assertTrue(caps.operations["start_turn"].startswith("blocked"))
        binding = Binding(role=Role.MIDDLE, model_id="fake-sol", reasoning_effort=None, registry_revision=1)
        with self.assertRaises(AdapterError):
            drifted.create_thread(binding, developer_instructions=None, workspace=None, sandbox="read-only")

    def test_unpinned_state(self):
        state, reasons = pin_status(None, None)
        self.assertEqual(state, "unpinned")
        self.assertTrue(reasons)


class CoordinatorOverStdio(FakeServerCase):
    """Full coordinator over the stdio adapter: live mode stays blocked on spend."""

    def test_live_mode_blocks_without_enforcement_and_sends_nothing(self):
        store = Store(self.tmp / "data")
        adapter = self.adapter()
        coordinator = Coordinator(store, adapter, live=True, ui=RecordingUI())
        coordinator.start()
        account = coordinator.account_scope
        coordinator.registry.approve_mapping(account, Role.LOWEST, "fake-sol", "medium", actor="owner",
                                             confirm_hash=mapping_hash_for(account, Role.LOWEST, "fake-sol", "medium"))
        project = self.tmp / "p"
        project.mkdir()
        coordinator.add_project("P", str(project))
        result = coordinator.submit("P", "Format my notes")
        self.assertEqual(result.model_id, "fake-sol")
        self.assertEqual(coordinator.run(result.job_id), JobState.BLOCKED_SPEND)
        methods = [m.get("method") for m in self.log()]
        self.assertNotIn("thread/start", methods)
        self.assertNotIn("turn/start", methods)
        coordinator.close()
        store.close()


class SimulatedSpendAdapter(CodexStdioAdapter):
    """Test-only: a *synthetic* spend approval so the real protocol path can be
    exercised in simulation mode. Live mode rejects synthetic decisions."""

    def check_spend_boundary(self, account, usage):
        from model_router.contracts import SpendDecision as Decision

        return Decision(SpendStatus.ALLOWED_INCLUDED_ONLY, [], [{"source": "synthetic"}], account.account_scope, utc_now(), True)


class DispatchOverStdio(FakeServerCase):
    def build(self):
        store = Store(self.tmp / "data")
        config = CodexConfig(data_dir=self.tmp / "data", executable=str(self.wrapper), codex_home=self.home,
                             enforce_pin=False, request_timeout=5, turn_idle_timeout=5)
        adapter = SimulatedSpendAdapter(config)
        ui = RecordingUI()
        coordinator = Coordinator(store, adapter, live=False, ui=ui)
        coordinator.start()
        account = coordinator.account_scope
        coordinator.registry.approve_mapping(account, Role.LOWEST, "fake-sol", "medium", actor="owner",
                                             confirm_hash=mapping_hash_for(account, Role.LOWEST, "fake-sol", "medium"))
        project = self.tmp / "p"
        project.mkdir(exist_ok=True)
        if store.project_by_name("P") is None:
            coordinator.add_project("P", str(project))
        self.addCleanup(store.close)
        self.addCleanup(coordinator.close)
        self.addCleanup(adapter.close)
        return coordinator, store, ui

    def test_stream_to_success_over_real_framing(self):
        coordinator, store, ui = self.build()
        result = coordinator.submit("P", "Format my notes")
        self.assertEqual(coordinator.run(result.job_id), JobState.SUCCEEDED)
        self.assertEqual("".join(ui.streamed), "Hello from fake codex.")
        answer = store.one("SELECT content, complete FROM messages WHERE thread_id=? AND role='assistant'", (result.thread_id,))
        self.assertEqual((answer["content"], answer["complete"]), ("Hello from fake codex.", 1))
        start = next(m for m in self.log() if m.get("method") == "thread/start")
        self.assertEqual((start["params"]["sandbox"], start["params"]["approvalPolicy"]), ("read-only", "on-request"))

    def test_server_crash_after_send_needs_owner_decision(self):
        self.scenario(exit_after_turn_start_request=True)
        coordinator, store, ui = self.build()
        result = coordinator.submit("P", "Format my notes")
        self.assertEqual(coordinator.run(result.job_id), JobState.RECOVERY_REQUIRED)
        self.assertEqual(sum(1 for m in self.log() if m.get("method") == "turn/start"), 1)
        self.assertEqual(coordinator.wake(), [])
        self.assertEqual(sum(1 for m in self.log() if m.get("method") == "turn/start"), 1, "no blind resend")
        self.assertTrue(any("will NOT be resent" in n for n in ui.notices))


class Doctor(FakeServerCase):
    def test_doctor_is_read_only_and_reports_spend_blocked(self):
        gates = {g.name: g for g in run_doctor(self.tmp / "data", codex_path=str(self.wrapper), codex_home=self.home)}
        self.assertEqual(gates["codex cli"].status.value, "VERIFIED")
        self.assertEqual(gates["protocol compatibility"].status.value, "VERIFIED")
        self.assertEqual(gates["adapter pin"].status.value, "BLOCKED")
        self.assertEqual(gates["chatgpt sign-in"].status.value, "VERIFIED")
        self.assertEqual(gates["spend boundary"].status.value, "BLOCKED")
        self.assertNotIn("owner@example.invalid", json.dumps([g.to_dict() for g in gates.values()]))
        methods = {m.get("method") for m in self.log()}
        self.assertFalse(methods & {"thread/start", "turn/start", "thread/resume"})


if __name__ == "__main__":
    unittest.main()
