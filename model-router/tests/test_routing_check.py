"""Two public task probes: verify execution evidence, bounds and evaluation isolation."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from helpers import RouterTestCase
from model_router.classifier import ClassifierInput, classify
from model_router.cli import parser
from model_router.contracts import Role, SpendStatus, utc_now
from model_router.evals.metrics import iso_week, weekly_report
from model_router.registry import mapping_hash_for
from model_router.routing_check import run_routing_check, verdict
from model_router.spend import decide_spend
import test_cli as cli_tests


class EvidenceVerdict(unittest.TestCase):
    def row(self):
        return {
            "routing_correct": True, "job_state": "SUCCEEDED", "response": "apples\npears\nfigs",
            "response_complete": True, "expected_model": "fixture-low",
            "dispatch": {"requested_model": "fixture-low", "observed_model": "fixture-low",
                         "provider_turn_id": "turn-fixture", "turn_status": "completed"},
        }

    def test_matching_turn_evidence_and_answer_are_required(self):
        self.assertEqual(verdict(self.row()), "PASS")
        row = self.row()
        row["dispatch"]["observed_model"] = None
        row["thread_configured_model"] = "fixture-low"
        row["response"] = "I am fixture-low.\napples\npears\nfigs"
        self.assertEqual(verdict(row), "MODEL_USE_UNVERIFIED")

    def test_mismatch_missing_turn_and_failed_response_cannot_pass(self):
        for change, expected in (
            ({"observed_model": "another-model"}, "FAIL_OBSERVED_MODEL"),
            ({"requested_model": "another-model"}, "FAIL_REQUESTED_MODEL"),
            ({"provider_turn_id": None}, "INCOMPLETE_TURN_EVIDENCE"),
        ):
            row = self.row()
            row["dispatch"].update(change)
            self.assertEqual(verdict(row), expected)
        for change in ({"response": ""}, {"response": None}, {"response_complete": False}, {"job_state": "FAILED"}):
            row = self.row() | change
            self.assertEqual(verdict(row), "FAIL_EXECUTION")


class TwoCaseCheck(RouterTestCase):
    def check(self):
        return run_routing_check(self.coordinator, allow_simulated=True)

    def test_two_new_chats_route_to_distinct_models_but_simulation_is_not_live_pass(self):
        report = self.check()
        self.assertEqual(report["status"], "SIMULATED")
        self.assertFalse(report["passed"])
        self.assertEqual(report["dispatch_attempts"], 2)
        self.assertEqual(self.adapter.model_sends, 2)
        cases = report["cases"]
        self.assertEqual([c["selected_model"] for c in cases], ["sim-luna-1", "sim-astra-1"])
        self.assertEqual(len({c["thread_id"] for c in cases}), 2)
        for case in cases:
            self.assertEqual(case["status"], "MODEL_USE_UNVERIFIED")
            self.assertTrue(case["response"])
            self.assertEqual(case["thread_configured_model"], case["selected_model"])
            self.assertIsNone(case["dispatch"]["observed_model"])
            self.assertEqual(self.store.thread(case["thread_id"])["kind"], "evaluation")
            self.assertEqual(self.store.job(case["job_id"])["user_requested"], 0)
        self.assertEqual(json.loads(Path(report["saved_to"]).read_text())["cases"], cases)

    def test_existing_queued_work_is_not_run_and_probes_do_not_count_as_adoption(self):
        other = self.coordinator.submit("Portfolio", "Format my notes as bullets")
        before = self.store.job(other.job_id)["state"]
        self.check()
        self.assertEqual(self.store.job(other.job_id)["state"], before)
        self.assertEqual(self.adapter.model_sends, 2)
        report = weekly_report(self.store, iso_week(utc_now()), include_synthetic=True)
        # Inspect the population, not a guessed accuracy from the two canned probes.
        self.assertEqual(self.store.one("SELECT count(*) n FROM threads WHERE kind='ordinary'")["n"], 1)
        self.assertEqual(report["system"]["threads_started"], 1)
        self.assertEqual(report["guardrail"]["eligible_threads"], 0)

    def test_blocked_spending_precedes_classification_and_all_sends(self):
        self.scenario.spend_status = SpendStatus.UNKNOWN
        with patch.object(self.coordinator, "submit", side_effect=AssertionError("no task before spend approval")):
            report = self.check()
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(self.adapter.model_sends, 0)
        self.assertEqual(report["dispatch_attempts"], 0)
        self.assertTrue(all(c["status"] == "NOT_RUN" for c in report["cases"]))

    def test_real_personal_plan_rule_is_preserved(self):
        self.scenario.plan_type = "pro"
        with patch.object(self.adapter, "check_spend_boundary",
                          side_effect=lambda account, usage: decide_spend(account, usage, pin_state="valid")):
            report = self.check()
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["spend"]["status"], "UNKNOWN")
        self.assertEqual(self.adapter.model_sends, 0)

    def test_identical_role_models_are_rejected_before_calls(self):
        model, effort = "sim-astra-1", "high"
        self.coordinator.registry.approve_mapping(
            self.account, Role.LOWEST, model, effort, actor="test-owner",
            confirm_hash=mapping_hash_for(self.account, Role.LOWEST, model, effort))
        report = self.check()
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("different approved models", report["blocked"])
        self.assertEqual(self.adapter.model_sends, 0)

    def test_known_wrong_routing_does_not_send_that_case(self):
        self.coordinator.classifier = lambda _: classify(ClassifierInput(text="Review this architecture"))
        report = self.check()
        self.assertEqual(report["cases"][0]["status"], "FAIL_ROUTING")
        self.assertEqual(self.adapter.model_sends, 1)
        self.assertEqual(report["cases"][1]["selected_model"], "sim-astra-1")

    def test_error_stops_after_one_turn_and_job_cannot_auto_resume(self):
        self.scenario.turn_scripts = [[{"kind": "error", "text": "No included usage", "code": "usage_limit_reached"},
                                       {"kind": "completed"}]]
        report = self.check()
        self.assertEqual(self.adapter.model_sends, 1)
        self.assertEqual(report["cases"][1]["status"], "NOT_RUN")
        self.assertEqual(self.coordinator.waiting_jobs(), [])
        self.assertFalse(report["passed"])

    def test_rerunning_creates_new_probe_threads_without_replaying_old_jobs(self):
        first, second = self.check(), self.check()
        self.assertNotEqual(first["saved_to"], second["saved_to"])
        self.assertEqual(self.adapter.model_sends, 4)
        self.assertEqual(len({c["thread_id"] for r in (first, second) for c in r["cases"]}), 4)

    def test_interruption_keeps_durable_attempt_count_without_a_false_pass(self):
        original_run = self.coordinator.run

        def interrupted(job):
            original_run(job)
            raise KeyboardInterrupt

        with patch.object(self.coordinator, "run", side_effect=interrupted):
            report = self.check()
        self.assertEqual(report["status"], "INTERRUPTED")
        self.assertEqual(report["dispatch_attempts"], 1)
        self.assertEqual(self.adapter.model_sends, 1)
        self.assertFalse(report["passed"])
        self.assertEqual(report["cases"][1]["status"], "NOT_RUN")

    def test_evaluation_is_non_resumable_even_during_initial_classification(self):
        def classifier(value):
            jobs = self.store.all("SELECT user_requested FROM jobs WHERE kind='evaluation'")
            self.assertTrue(jobs)
            self.assertTrue(all(j["user_requested"] == 0 for j in jobs))
            return classify(value)
        self.coordinator.classifier = classifier
        self.check()


class RoutingCheckCli(unittest.TestCase):
    setUp = cli_tests.Cli.setUp
    tearDown = cli_tests.Cli.tearDown

    def test_command_accepts_two_case_option_and_never_claims_simulated_pass(self):
        self.assertTrue(parser().parse_args(["pilot", "--routing-check"]).routing_check)
        ready = cli_tests.run("start", "--simulate", "--data-dir", str(self.data), "--path", str(self.project), stdin="/quit\n")
        self.assertEqual(ready.returncode, 0, ready.stderr)
        result = cli_tests.run("pilot", "--routing-check", "--simulate", "--data-dir", str(self.data))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('"status": "SIMULATED"', result.stdout)
        self.assertIn('"passed": false', result.stdout)
        self.assertIn('"dispatch_attempts": 2', result.stdout)


if __name__ == "__main__":
    unittest.main()
