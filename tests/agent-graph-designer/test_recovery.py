"""Behavior checks with actual child processes and synthetic task evidence."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "agent-graph-designer/skills/agent-graph-designer/examples/sample-orchestrator.py"
SPEC = importlib.util.spec_from_file_location("sample_orchestrator", RUNNER)
assert SPEC and SPEC.loader
graph = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(graph)
PRODUCT, QUALITY, SAFETY = graph.REVIEW_NODES


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def read_state(self):
        return json.loads((self.directory / "checkpoint.json").read_text())

    def save_state(self, state):
        (self.directory / "checkpoint.json").write_text(json.dumps(state))

    def test_three_different_tasks_verified_before_join(self):
        result = graph.run(self.directory)
        self.assertEqual(result["status"], "AWAITING_HUMAN_APPROVAL")
        self.assertEqual(result["attempts"], {PRODUCT: 1, QUALITY: 1, SAFETY: 1})
        state = self.read_state()
        self.assertEqual(state["results"][PRODUCT]["observed"], {"minutes": 6})
        self.assertEqual(state["results"][QUALITY]["observed"], {"passed": 18, "total": 20})
        self.assertEqual(state["results"][SAFETY]["observed"], {"exposures": 0, "unsafe": 0})
        self.assertEqual(state["events"][-1]["event"], "join_ready")
        self.assertEqual(result["external_actions_taken"], [])

    def test_manifest_and_attempt_are_saved_before_every_dispatch(self):
        original = graph.subprocess.Popen
        registered = []

        def inspect_then_start(command, **kwargs):
            task = json.loads(command[command.index("--worker") + 1])
            state = self.read_state()
            self.assertEqual(set(state["task_manifest"]), set(graph.REVIEW_NODES))
            self.assertEqual(state["task_manifest"][task["node_id"]], task)
            self.assertGreater(state["attempts"][task["node_id"]], 0)
            registered.append(task["node_id"])
            return original(command, **kwargs)

        with patch.object(graph.subprocess, "Popen", side_effect=inspect_then_start):
            result = graph.run(self.directory, failure="crash-once")
        self.assertEqual(result["status"], "AWAITING_HUMAN_APPROVAL")
        self.assertEqual(registered.count(QUALITY), 2)
        self.assertEqual(registered.count(PRODUCT), 1)
        self.assertEqual(registered.count(SAFETY), 1)

    def test_crashed_worker_is_replaced_for_only_its_own_task(self):
        result = graph.run(self.directory, failure="crash-once")
        self.assertEqual(result["status"], "AWAITING_HUMAN_APPROVAL")
        self.assertEqual(result["attempts"], {PRODUCT: 1, QUALITY: 2, SAFETY: 1})
        dispatches = [e for e in self.read_state()["events"]
                      if e["event"] == "worker_dispatched" and e["node"] == QUALITY]
        self.assertEqual(len({e["pid"] for e in dispatches}), 2)

    def test_actual_timeout_terminates_child_then_recovers(self):
        contract = graph.load_contract()
        for node in contract["nodes"]:
            if node["id"] == QUALITY:
                node["timeout_seconds"] = 0.3
        result = graph.run(self.directory, contract=contract, failure="timeout-once")
        self.assertEqual(result["status"], "AWAITING_HUMAN_APPROVAL")
        self.assertEqual(result["attempts"], {PRODUCT: 1, QUALITY: 2, SAFETY: 1})
        failures = [e for e in self.read_state()["events"] if e["event"] == "attempt_failed"]
        self.assertEqual(failures[0]["reason"], "Worker timeout")

    def test_permanent_required_failure_blocks_and_retains_siblings(self):
        result = graph.run(self.directory, failure="crash-always")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIsNone(result["recommendation"])
        self.assertEqual(result["missing_branches"], [QUALITY])
        self.assertEqual(set(result["completed_branches"]), {PRODUCT, SAFETY})
        self.assertEqual(result["attempts"][QUALITY], 2)
        self.assertNotIn("join_ready", [e["event"] for e in self.read_state()["events"]])

    def test_resume_cannot_reset_exhausted_attempt_budget(self):
        first = graph.run(self.directory, failure="crash-always")
        before = self.read_state()["results"]
        with patch.object(graph.subprocess, "Popen", side_effect=AssertionError("unexpected dispatch")):
            second = graph.run(self.directory)
        self.assertEqual(second["status"], "BLOCKED")
        self.assertEqual(second["attempts"], first["attempts"])
        self.assertEqual(self.read_state()["results"], before)

    def test_resume_reuses_verified_work_without_dispatch(self):
        graph.run(self.directory)
        before = self.read_state()["results"]
        with patch.object(graph.subprocess, "Popen", side_effect=AssertionError("unexpected dispatch")):
            result = graph.run(self.directory)
        self.assertEqual(result["status"], "AWAITING_HUMAN_APPROVAL")
        self.assertEqual(set(result["reused_branches"]), set(graph.REVIEW_NODES))
        self.assertEqual(self.read_state()["results"], before)

    def test_new_coordinator_recovers_unique_task_after_interruption(self):
        # Separate process group contains only this test's coordinator and children.
        coordinator = subprocess.Popen(
            [sys.executable, str(RUNNER), "--state-dir", str(self.directory),
             "--failure", "timeout-once"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, start_new_session=True)
        snapshot = None
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if (self.directory / "checkpoint.json").exists():
                    candidate = self.read_state()
                    if set(candidate["results"]) == {PRODUCT, SAFETY}:
                        snapshot = candidate
                        break
                if coordinator.poll() is not None:
                    self.fail("Coordinator exited before interruption checkpoint")
                time.sleep(0.01)
            self.assertIsNotNone(snapshot, "Did not observe partial checkpoint")
        finally:
            try:
                os.killpg(coordinator.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            coordinator.communicate(timeout=5)
        result = graph.run(self.directory)
        self.assertEqual(result["status"], "AWAITING_HUMAN_APPROVAL")
        self.assertEqual(result["attempts"], {PRODUCT: 1, QUALITY: 2, SAFETY: 1})
        self.assertEqual(set(result["reused_branches"]), {PRODUCT, SAFETY})
        resumed = self.read_state()
        self.assertEqual(resumed["task_manifest"], snapshot["task_manifest"])
        for node in (PRODUCT, SAFETY):
            self.assertEqual(resumed["results"][node], snapshot["results"][node])

    def test_single_coordinator_lock_prevents_duplicate_dispatch(self):
        with (self.directory / "coordinator.lock").open("a") as lock:
            graph.fcntl.flock(lock, graph.fcntl.LOCK_EX | graph.fcntl.LOCK_NB)
            with patch.object(graph.subprocess, "Popen", side_effect=AssertionError("unexpected dispatch")):
                result = graph.run(self.directory)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("Another coordinator", result["blocking_reason"])

    def test_mismatched_output_is_rejected_despite_claiming_pass(self):
        result = graph.run(self.directory, failure="wrong-always")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["missing_branches"], [QUALITY])
        self.assertTrue(any("verification" in s for s in result["blocking_reasons"]))

    def test_each_distinct_acceptance_rule_can_block_the_join(self):
        cases = [(PRODUCT, "resolution_minutes", 20), (QUALITY, "passed_cases", 10),
                 (SAFETY, "restricted_data_exposures", 1)]
        for node, field, value in cases:
            with self.subTest(node=node):
                evidence = copy.deepcopy(graph.EVIDENCE)
                evidence[node][field] = value
                result = graph.run(self.directory / node, evidence=evidence)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(result["missing_branches"], [node])
                self.assertIsNone(result["recommendation"])

    def test_counterfeit_pass_cannot_waive_negative_safety_evidence(self):
        graph.run(self.directory)
        task = self.read_state()["task_manifest"][SAFETY]
        task["inputs"]["unsafe_outputs"] = 1
        forged = graph.review(task)
        self.assertEqual(forged["status"], "FAIL")
        forged["status"] = "PASS"
        self.assertFalse(graph.verify(task, forged))

    def test_lost_task_registration_blocks_without_reconstructing_it(self):
        graph.run(self.directory)
        state = self.read_state()
        del state["task_manifest"][QUALITY]
        self.save_state(state)
        with patch.object(graph.subprocess, "Popen", side_effect=AssertionError("unexpected dispatch")):
            result = graph.run(self.directory)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("registration", result["blocking_reason"])
        self.assertEqual(json.loads((self.directory / "result.json").read_text())["status"], "BLOCKED")

    def test_corrupted_saved_result_cannot_reach_join(self):
        graph.run(self.directory)
        state = self.read_state()
        state["results"][PRODUCT]["observed"]["minutes"] = 999
        self.save_state(state)
        result = graph.run(self.directory)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("verification", result["blocking_reason"])

    def test_changed_inputs_require_new_run(self):
        graph.run(self.directory)
        evidence = copy.deepcopy(graph.EVIDENCE)
        evidence[QUALITY]["passed_cases"] = 19
        result = graph.run(self.directory, evidence=evidence)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("Inputs changed", result["blocking_reason"])

    def test_missing_checkpoint_does_not_start_fresh_over_old_result(self):
        graph.run(self.directory)
        (self.directory / "checkpoint.json").unlink()
        result = graph.run(self.directory)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("Missing checkpoint", result["blocking_reason"])

    def test_expired_graph_budget_does_not_reset_on_resume(self):
        graph.run(self.directory)
        state = self.read_state()
        state["started_at"] = time.time() - 1000
        self.save_state(state)
        result = graph.run(self.directory)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("Graph time budget exhausted", result["blocking_reasons"])

    def test_stop_prevents_all_dispatch(self):
        (self.directory / "STOP").touch()
        with patch.object(graph.subprocess, "Popen", side_effect=AssertionError("unexpected dispatch")):
            result = graph.run(self.directory)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(sum(result["attempts"].values()), 0)

    def test_cli_returns_nonzero_for_required_failure(self):
        completed = subprocess.run([sys.executable, str(RUNNER), "--failure", "crash-always"],
                                   capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(json.loads(completed.stdout)["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
