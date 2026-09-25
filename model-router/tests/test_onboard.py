"""One-command setup (against the fake Codex subprocess), the bounded pilot,
and the optional classifier plugin."""

import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ARCH_RECORD, FAKE_CODEX, RouterTestCase
from model_router.classifier import ClassifierInput
from model_router.contracts import Role, SpendStatus, TaskKind
from model_router.onboard import Setup, candidates_for, run_pilot
from model_router.plugin_classifier import combined_classifier, load_plugin

WORKSPACE_LIMITS = {
    "rateLimitsByLimitId": {"codex": {"limitId": "codex", "planType": "business", "primary": {"usedPercent": 10},
                                      "credits": {"hasCredits": True, "unlimited": False, "balance": "50"},
                                      "spendControlReached": False,
                                      "individualLimit": {"limit": "0", "used": "0", "remainingPercent": 0, "resetsAt": 1790000000}}},
    "ordinaryUsageAllowed": True,
}


class SetupFlow(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.wrapper = self.tmp / "codex"
        self.wrapper.write_text(f"#!/bin/sh\nexec {sys.executable} {FAKE_CODEX} \"$@\"\n")
        self.wrapper.chmod(self.wrapper.stat().st_mode | stat.S_IEXEC)
        self.said = []

    def tearDown(self):
        self._tmp.cleanup()

    def scenario(self, **values):
        (self.home / "fake-scenario.json").write_text(json.dumps(values))

    def setup(self, answers, run_login=None):
        answers = list(answers)
        return Setup(self.tmp / "data", codex_path=str(self.wrapper), codex_home=self.home,
                     ask=lambda q: answers.pop(0) if answers else "", say=self.said.append, run_login=run_login).run()

    def test_personal_plan_ends_blocked_with_the_exact_gap(self):
        self.scenario(account={"type": "chatgpt", "email": "o@example.invalid", "planType": "plus"})
        report = self.setup(["y", "1", "", "1", "", ""])
        self.assertFalse(report["ready"])
        self.assertEqual(report["spend"]["status"], "UNKNOWN")
        self.assertIn("openai/codex#28382", report["spend"]["missing"][0])
        self.assertEqual(report["mappings"], {"highest": "fake-astra", "middle": "fake-sol"})
        statuses = {s["step"]: s["status"] for s in report["steps"]}
        self.assertEqual(statuses["adapter pin"], "VERIFIED")
        self.assertEqual(statuses["lowest role"], "BLOCKED")
        self.assertFalse(any("o@example.invalid" in line for line in self.said), "email never printed")
        methods = [json.loads(l).get("method") for l in (self.home / "fake-log.jsonl").read_text().splitlines()]
        self.assertNotIn("turn/start", methods)
        self.assertNotIn("thread/start", methods)

    def test_workspace_zero_member_limit_is_ready(self):
        self.scenario(account={"type": "chatgpt", "email": "o@example.invalid", "planType": "business"}, rate_limits=WORKSPACE_LIMITS)
        report = self.setup(["y", "1", "", "1", "", ""])
        self.assertTrue(report["ready"])
        self.assertEqual(report["spend"]["mechanism"], "workspace_member_zero_credit_limit")

    def test_sign_in_is_codex_login_not_a_pasted_credential(self):
        self.scenario(account=None)
        calls = []

        def fake_login(argv, env):
            calls.append((argv, env))
            self.scenario(account={"type": "chatgpt", "email": "o@example.invalid", "planType": "plus"})
            return 0

        report = self.setup(["y", "y", "", "", ""], run_login=fake_login)
        self.assertEqual(calls[0][0][-1], "login")
        self.assertEqual(calls[0][1]["CODEX_HOME"], str(self.home))
        self.assertNotIn("OPENAI_API_KEY", calls[0][1])
        self.assertEqual({s["step"]: s["status"] for s in report["steps"]}["sign-in"], "VERIFIED")

    def test_declining_the_pin_stops_before_any_account_access(self):
        report = self.setup(["n"])
        self.assertFalse(report["ready"])
        self.assertFalse((self.home / "fake-log.jsonl").exists())


class Candidates(unittest.TestCase):
    def test_family_candidates_newest_first(self):
        models = [{"model_id": m, "available": True, "info": {}} for m in
                  ("gpt-5.6-sol", "gpt-6-sol", "gpt-6-astra", "gpt-6-luna", "gpt-5.6-terra", "gpt-5.5")]
        self.assertEqual([m["model_id"] for m in candidates_for(models, Role.MIDDLE)], ["gpt-6-sol", "gpt-5.6-sol"])
        self.assertEqual([m["model_id"] for m in candidates_for(models, Role.LOWEST)], ["gpt-6-luna", "gpt-5.6-terra"])


class Pilot(RouterTestCase):
    def test_simulated_pilot_runs_all_four_scenarios(self):
        block = "```architecture-record\n" + json.dumps(ARCH_RECORD | {"files": ["hello.py"]}) + "\n```"
        self.scenario.turn_scripts[:] = [
            [{"kind": "delta", "text": "- picks a model\n- keeps it"}, {"kind": "completed"}],
            [{"kind": "delta", "text": block}, {"kind": "completed"}],
            [{"kind": "delta", "text": "implemented"}, {"kind": "completed"}],
            [{"kind": "delta", "text": "- one bullet"}, {"kind": "completed"}],
        ]
        report = run_pilot(self.coordinator, project_dir=self.tmp / "pilot", allow_simulated=True)
        self.assertIsNone(report["blocked"])
        self.assertTrue(report["all_passed"], json.dumps(report["scenarios"], indent=1, default=str))
        self.assertLessEqual(report["turns_sent"], 8)
        self.assertEqual(report["scenarios"]["handoff"]["implementation_role"], "middle")
        self.assertTrue(Path(report["saved_to"]).exists())

    def test_pilot_refuses_without_verified_spend_boundary(self):
        report = run_pilot(self.coordinator, project_dir=self.tmp / "pilot")  # simulator evidence is synthetic
        self.assertIn("not ALLOWED_INCLUDED_ONLY from a verified mechanism", report["blocked"])
        self.assertEqual(self.adapter.model_sends, 0)
        self.scenario.spend_status = SpendStatus.UNKNOWN
        report = run_pilot(self.coordinator, project_dir=self.tmp / "pilot", allow_simulated=True)
        self.assertIsNotNone(report["blocked"])
        self.assertEqual(self.adapter.model_sends, 0)


class PluginClassifier(unittest.TestCase):
    def test_plugin_cannot_lower_hard_floors_but_can_raise_or_resolve_unknown(self):
        lower = combined_classifier(lambda text: {"task_kind": "routine_text", "reason": "looks simple"})
        self.assertEqual(lower(ClassifierInput(text="Implement the payment transfer endpoint")).task_kind, TaskKind.HIGH_RISK_CODING)
        self.assertEqual(lower(ClassifierInput(text="Rewrite my LinkedIn post")).task_kind, TaskKind.HIGH_CREDIBILITY_WRITING)
        resolved = lower(ClassifierInput(text="hmm what about the thing"))
        self.assertEqual(resolved.task_kind, TaskKind.ROUTINE_TEXT)
        self.assertIn("PLUGIN_CLASSIFICATION_USED", resolved.reason_codes)
        raise_ = combined_classifier(lambda text: {"task_kind": "architecture"})
        self.assertEqual(raise_(ClassifierInput(text="Format my notes")).task_kind, TaskKind.ARCHITECTURE)

    def test_plugin_failure_falls_back_visibly(self):
        def broken(text):
            raise RuntimeError("model not loaded")

        result = combined_classifier(broken)(ClassifierInput(text="Format my notes"))
        self.assertEqual(result.task_kind, TaskKind.ROUTINE_TEXT)
        self.assertIn("PLUGIN_FAILED:RuntimeError", result.reason_codes)

    def test_plugin_is_off_unless_configured(self):
        self.assertIsNone(load_plugin(""))
        with self.assertRaises(ValueError):
            load_plugin("no-colon")
