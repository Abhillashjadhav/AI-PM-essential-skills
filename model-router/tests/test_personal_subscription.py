"""Offline production-path checks. All accounts, models and provider turns are fake."""
import dataclasses
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from helpers import RecordingUI, ROOT
from model_router.adapters.base import AccountState, AdapterError
from model_router.adapters.codex_stdio import parse_rate_limits
from model_router.billing import BillingPolicy, KEY, PERSONAL_POLICY, PersonalConfirmation
from model_router.contracts import JobState, SpendStatus, parse_utc, utc_now
from model_router.coordinator import Coordinator
from model_router.onboard import Setup
from model_router.routing_check import configured_execution_passed, run_routing_check
from model_router.spend import decide_spend
from model_router.store import Store
from test_codex_stdio import FakeServerCase


def payload():
    return {"rateLimitsByLimitId": {"codex": {"limitId": "codex", "planType": "pro",
            "primary": {"usedPercent": 20}, "credits": {"hasCredits": False, "unlimited": False, "balance": "0"}}},
            "ordinaryUsageAllowed": True}


def account():
    return AccountState(True, "chatgpt", "acct_fixture", "pro", True, [], False, utc_now())


def confirmation():
    return PersonalConfirmation("confirmation-fixture", "acct_fixture", "pro", "pin", "/fixture/profile", utc_now())


class PersonalPolicyGuards(unittest.TestCase):
    def decide(self, raw=None, acct=None, consent=None, **kwargs):
        return decide_spend(acct or account(), parse_rate_limits(raw or payload(), account_scope="acct_fixture"),
                            pin_state="valid", personal_confirmation=consent or confirmation(), adapter_pin="pin",
                            profile="/fixture/profile", **kwargs)

    def test_live_zero_credit_signals_plus_confirmation_allow_only_conditional_status(self):
        result = self.decide()
        result.validate()
        self.assertEqual(result.status, SpendStatus.ALLOWED_ACCOUNT_CONFIRMED)
        self.assertNotEqual(result.status, SpendStatus.ALLOWED_INCLUDED_ONLY)
        self.assertEqual(result.mechanism, PERSONAL_POLICY)
        self.assertIn("cannot read", result.reasons[0])

    def test_no_confirmation_and_no_strict_provider_mechanism_stays_blocked(self):
        result = decide_spend(account(), parse_rate_limits(payload(), account_scope="acct_fixture"), pin_state="valid")
        self.assertFalse(result.allows_send)

    def test_missing_conflicting_exhausted_or_malformed_fields_cannot_be_allowed(self):
        modifications = [
            lambda r: r.update(ordinaryUsageAllowed=None),
            lambda r: r.update(ordinaryUsageAllowed=1),
            lambda r: r.update(ordinaryUsageAllowed=False),
            lambda r: r["rateLimitsByLimitId"]["codex"].pop("credits"),
            lambda r: r["rateLimitsByLimitId"]["codex"]["credits"].update(balance="2", hasCredits=True),
            lambda r: r["rateLimitsByLimitId"]["codex"]["credits"].update(balance="-1"),
            lambda r: r["rateLimitsByLimitId"]["codex"]["credits"].update(balance="NaN"),
            lambda r: r["rateLimitsByLimitId"]["codex"]["credits"].update(unlimited=None),
            lambda r: r["rateLimitsByLimitId"]["codex"]["credits"].update(hasCredits=0),
            lambda r: r["rateLimitsByLimitId"]["codex"]["credits"].update(unlimited=True),
            lambda r: r["rateLimitsByLimitId"]["codex"].update(planType="business"),
            lambda r: r["rateLimitsByLimitId"].update(second={"planType": "pro"}),
            lambda r: r["rateLimitsByLimitId"].update(second=[]),
            lambda r: r.update(rateLimits={"planType": "pro", "credits": {"hasCredits": True, "unlimited": False, "balance": "3"}}),
            lambda r: r["rateLimitsByLimitId"]["codex"]["primary"].update(usedPercent=100),
            lambda r: r["rateLimitsByLimitId"]["codex"]["primary"].update(usedPercent=True),
            lambda r: r["rateLimitsByLimitId"]["codex"].update(rateLimitReachedType="limit"),
            lambda r: r["rateLimitsByLimitId"]["codex"].update(spendControlReached="false"),
            lambda r: r["rateLimitsByLimitId"]["codex"].pop("primary"),
        ]
        for index, change in enumerate(modifications):
            raw = payload()
            change(raw)
            with self.subTest(case=index):
                self.assertFalse(self.decide(raw=raw).allows_send)

    def test_auth_account_profile_pin_time_and_simulation_are_checked(self):
        for changes in ({"auth_mode": "apiKey"}, {"config_ok": False}, {"authenticated": False},
                        {"account_scope": "other"}, {"synthetic": True}, {"plan_type": "plus"},
                        {"observed_at": "2000-01-01T00:00:00Z"}):
            with self.subTest(changes=changes):
                self.assertFalse(self.decide(acct=dataclasses.replace(account(), **changes)).allows_send)
        for changes in ({"enabled": False}, {"adapter_pin": "other"}, {"profile": "/other"},
                        {"plan_type": "plus"}, {"account_scope": "other"}):
            with self.subTest(changes=changes):
                self.assertFalse(self.decide(consent=dataclasses.replace(confirmation(), **changes)).allows_send)
        for changes in ({"observed_at": "2000-01-01T00:00:00Z"}, {"synthetic": True}, {"account_scope": None},
                        {"observed_at": (parse_utc(utc_now()) + timedelta(minutes=1)).isoformat()}):
            usage = dataclasses.replace(parse_rate_limits(payload(), account_scope="acct_fixture"), **changes)
            result = decide_spend(account(), usage, pin_state="valid", personal_confirmation=confirmation(),
                                   adapter_pin="pin", profile="/fixture/profile")
            self.assertFalse(result.allows_send)


class ConfirmationStorage(unittest.TestCase):
    def test_private_persistent_confirmation_atomic_disable_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data"
            policy = BillingPolicy(path)
            self.assertFalse(policy.status()["enabled"])
            first = policy.confirm(account_scope="a", plan_type="pro", adapter_pin="pin", profile="profile")
            self.assertTrue(BillingPolicy(path).load()[0].enabled)
            second = policy.confirm(account_scope="a", plan_type="pro", adapter_pin="pin", profile="profile")
            self.assertFalse(policy.disable(expected_id=first.id))
            self.assertTrue(policy.disable(expected_id=second.id))
            self.assertFalse(BillingPolicy(path).load()[0].enabled)
            store = Store(path)
            try:
                self.assertEqual(len(store.events(event_type="billing.confirmed")), 2)
                self.assertEqual(len(store.events(event_type="billing.disabled")), 1)
                self.assertEqual(store.db_path.stat().st_mode & 0o777, 0o600)
                store.execute("UPDATE meta SET value=? WHERE key=?", ('{"enabled":true,"verified":true}', KEY))
                self.assertIsNone(policy.load()[0])
            finally:
                store.close()


class PersonalSetupAndDispatch(FakeServerCase):
    def prepare(self, *, approve=True):
        self.scenario(account={"type": "chatgpt", "email": "fixture@example.invalid", "planType": "pro"}, rate_limits=payload())
        answers = iter(["y", "1", "", "1", "", "2", "", "y" if approve else "n"])
        self.said = []
        self.data = self.tmp / "data"
        report = Setup(self.data, codex_path=str(self.wrapper), codex_home=self.home,
                       ask=lambda _: next(answers), say=self.said.append).run()
        return report

    def coordinator(self):
        adapter = self.adapter(enforce_pin=True)
        store = Store(self.data)
        coordinator = Coordinator(store, adapter, live=True, ui=RecordingUI())
        self.addCleanup(store.close)
        self.addCleanup(coordinator.close)
        return coordinator

    def test_setup_reuses_roles_and_confirmation_without_repeated_prompts(self):
        report = self.prepare()
        self.assertTrue(report["ready"], report)
        self.assertEqual(report["spend"]["status"], "ALLOWED_ACCOUNT_CONFIRMED")
        again = Setup(self.data, codex_path=str(self.wrapper), codex_home=self.home,
                      ask=lambda _: self.fail("already confirmed"), say=lambda _: None).run()
        self.assertTrue(again["ready"])
        methods = [m.get("method") for m in self.log()]
        self.assertGreater(max(i for i, method in enumerate(methods) if method == "account/read"),
                           max(i for i, method in enumerate(methods) if method == "model/list"))
        self.assertFalse(any(m.get("method") == "turn/start" for m in self.log()))

    def test_declining_confirmation_blocks_and_no_model_turn_occurs(self):
        self.assertFalse(self.prepare(approve=False)["ready"])
        self.assertFalse(BillingPolicy(self.data).status()["enabled"])
        self.assertFalse(any(m.get("method") == "turn/start" for m in self.log()))

    def test_two_tasks_execute_through_real_adapter_protocol_without_other_queued_work(self):
        self.prepare()
        coordinator = self.coordinator()
        coordinator.start()
        coordinator.add_project("old", str(self.tmp))
        queued = coordinator.submit("old", "Format my notes as bullets")
        report = run_routing_check(coordinator)
        self.assertEqual(report["dispatch_attempts"], 2, report)
        self.assertTrue(report["configured_execution_passed"], report)
        self.assertEqual(report["status"], "MODEL_USE_UNVERIFIED")
        self.assertFalse(report["passed"], "fake server provides config, not per-turn attestation")
        self.assertEqual(coordinator.store.job(queued.job_id)["state"], queued.state.value)
        requests = [m for m in self.log() if m.get("method") == "turn/start"]
        self.assertEqual([m["params"]["model"] for m in requests], ["fake-sol", "fake-astra"])
        self.assertTrue(all(c["response"] == "Hello from fake codex." for c in report["cases"]))

    def test_ordinary_chat_uses_same_policy_then_disable_blocks_without_losing_pin(self):
        self.prepare()
        coordinator = self.coordinator()
        coordinator.start()
        coordinator.add_project("normal", str(self.tmp))
        first = coordinator.submit("normal", "Format my notes as bullets")
        self.assertEqual(coordinator.run(first.job_id), JobState.SUCCEEDED)
        proc = subprocess.run([sys.executable, str(ROOT / "router.py"), "billing", "disable", "--data-dir", str(self.data)],
                              capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        followup = coordinator.submit("normal", "Make it shorter", thread_id=first.thread_id)
        self.assertEqual(coordinator.run(followup.job_id), JobState.BLOCKED_SPEND)
        self.assertEqual(coordinator.store.thread(first.thread_id)["pinned_model"], "fake-sol")
        self.assertEqual(len([m for m in self.log() if m.get("method") == "turn/start"]), 1)

    def test_disable_during_thread_creation_is_checked_before_the_turn(self):
        self.prepare()
        coordinator = self.coordinator()
        coordinator.start()
        coordinator.add_project("normal", str(self.tmp))
        original = coordinator.adapter.create_thread

        def changed(*args, **kwargs):
            result = original(*args, **kwargs)
            BillingPolicy(self.data).disable()
            return result

        task = coordinator.submit("normal", "Format my notes")
        with patch.object(coordinator.adapter, "create_thread", side_effect=changed):
            self.assertEqual(coordinator.run(task.job_id), JobState.BLOCKED_SPEND)
        self.assertFalse(any(m.get("method") == "turn/start" for m in self.log()))

    def test_observed_credits_or_account_drift_revokes_confirmation(self):
        for change in ("credits", "account", "pin", "profile"):
            with self.subTest(change=change):
                self.prepare()
                adapter = self.adapter(enforce_pin=True)
                adapter.initialise()
                acct, usage = adapter.read_account(), adapter.read_usage()
                if change == "credits":
                    usage.billing_limits[0].credits.balance = "1"
                elif change == "account":
                    acct = dataclasses.replace(acct, account_scope="other")
                elif change == "pin":
                    adapter.validated_pin_digest = "different"
                else:
                    adapter.config.codex_home = self.tmp / "different-profile"
                self.assertFalse(adapter.check_spend_boundary(acct, usage).allows_send)
                self.assertFalse(BillingPolicy(self.data).status()["enabled"])
                adapter.close()

    def test_included_usage_pause_and_reset_reuse_same_pin_and_confirmation(self):
        self.prepare()
        coordinator = self.coordinator()
        coordinator.start()
        coordinator.add_project("normal", str(self.tmp))
        task = coordinator.submit("normal", "Format my notes")
        raw = payload()
        raw["ordinaryUsageAllowed"] = False
        exhausted = parse_rate_limits(raw, account_scope=coordinator.account_scope)
        with patch.object(coordinator.adapter, "read_usage", return_value=exhausted):
            self.assertEqual(coordinator.run(task.job_id), JobState.WAITING_USAGE)
        self.assertTrue(BillingPolicy(self.data).status()["enabled"])
        self.assertEqual(coordinator.run(task.job_id), JobState.SUCCEEDED)
        self.assertEqual(coordinator.store.thread(task.thread_id)["pinned_model"], "fake-sol")
        self.assertEqual(len([m for m in self.log() if m.get("method") == "turn/start"]), 1)

    def test_credits_seen_while_usage_exhausted_revoke_before_reset(self):
        self.prepare()
        coordinator = self.coordinator()
        coordinator.start()
        coordinator.add_project("normal", str(self.tmp))
        task = coordinator.submit("normal", "Format my notes")
        raw = payload()
        raw["ordinaryUsageAllowed"] = False
        raw["rateLimitsByLimitId"]["codex"]["credits"].update(hasCredits=True, balance="1")
        usage = parse_rate_limits(raw, account_scope=coordinator.account_scope)
        with patch.object(coordinator.adapter, "read_usage", return_value=usage):
            self.assertEqual(coordinator.run(task.job_id), JobState.WAITING_USAGE)
        self.assertFalse(BillingPolicy(self.data).status()["enabled"])
        self.assertEqual(coordinator.run(task.job_id), JobState.BLOCKED_SPEND)
        self.assertFalse(any(m.get("method") == "turn/start" for m in self.log()))

    def test_mid_turn_recheck_accepts_unchanged_policy_and_stops_on_credit_change(self):
        self.prepare()
        coordinator = self.coordinator()
        coordinator.start()
        self.assertIsNone(coordinator._spend_recheck_mid_turn())
        raw = payload()
        raw["rateLimitsByLimitId"]["codex"]["credits"].update(hasCredits=True, balance="1")
        usage = parse_rate_limits(raw, account_scope=coordinator.account_scope)
        with patch.object(coordinator.adapter, "read_usage", return_value=usage):
            self.assertIn("BLOCKED", coordinator._spend_recheck_mid_turn())
        self.assertFalse(BillingPolicy(self.data).status()["enabled"])

    def test_missing_per_turn_identity_does_not_hide_functional_success_or_fabricate_proof(self):
        row = {"routing_correct": True, "job_state": "SUCCEEDED", "response": "ok", "response_complete": True,
               "expected_model": "fixture", "thread_configured_model": "fixture",
               "dispatch": {"requested_model": "fixture", "provider_turn_id": "t", "turn_status": "completed"}}
        self.assertTrue(configured_execution_passed(row))
        self.assertFalse(configured_execution_passed(row | {"thread_configured_model": "other"}))
