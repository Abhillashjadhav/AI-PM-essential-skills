from __future__ import annotations

import hashlib
import json
import lzma
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "pm-verifier" / "skills" / "eval-engine" / "harness"
EXAMPLE = (
    ROOT
    / "pm-verifier"
    / "skills"
    / "eval-engine"
    / "examples"
    / "production-eval"
)
sys.path.insert(0, str(HARNESS))

from pm_verifier.bias import analyze_pairwise_bias  # noqa: E402
from pm_verifier.calibration import calibrate  # noqa: E402
from pm_verifier.engine import evaluate_project  # noqa: E402
from pm_verifier.faults import apply_faults  # noqa: E402
from pm_verifier.io import EvidenceError, sha256_file  # noqa: E402
from pm_verifier.adapter import (  # noqa: E402
    MAX_ADAPTER_ERROR_BYTES,
    MAX_ADAPTER_INPUT_BYTES,
    MAX_ADAPTER_OUTPUT_BYTES,
    execute_trials,
)
from pm_verifier.reporting import render_inspection, render_markdown  # noqa: E402


class PMVerifierTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name) / "eval"
        shutil.copytree(EXAMPLE, self.project)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def evaluate(self, **kwargs):
        return evaluate_project(self.project, **kwargs)

    def load_jsonl(self, relative: str) -> list[dict]:
        return [
            json.loads(line)
            for line in (self.project / relative).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def write_jsonl(self, relative: str, rows: list[dict]) -> Path:
        path = self.project / relative
        path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
        return path

    def fault(self, name: str) -> Path:
        specs = json.loads(
            (self.project / "faults" / "specs.json").read_text(encoding="utf-8")
        )
        rows = apply_faults(self.load_jsonl("trials.jsonl"), specs[name])
        return self.write_jsonl(f"fault-{name}.jsonl", rows)

    def rewrite_suite(self, suite: dict) -> None:
        suite_path = self.project / "suite.json"
        suite_path.write_text(json.dumps(suite, indent=2), encoding="utf-8")
        run_path = self.project / "run.json"
        run = json.loads(run_path.read_text(encoding="utf-8"))
        run["configuration"]["sha256"] = sha256_file(suite_path)
        run_path.write_text(json.dumps(run, indent=2), encoding="utf-8")

    def test_known_good_repeated_trials_pass(self) -> None:
        result = self.evaluate()
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["summary"]["case_count"], 2)
        self.assertEqual(result["summary"]["trial_count"], 4)
        self.assertEqual(result["summary"]["trial_pass_rate"], 1.0)
        self.assertEqual(result["summary"]["pass_at_k"], 1.0)
        self.assertEqual(result["summary"]["pass_power_k"], 1.0)
        self.assertIn("metrics", result)
        self.assertIn("slices", result)

    def test_known_bad_outcome_gate_fires(self) -> None:
        result = self.evaluate(trials_path=self.fault("outcome"))
        self.assertEqual(result["decision"], "FAIL")
        self.assertIn("G_OUTCOME_DECISION", result["failed_gate_ids"])

    def test_known_bad_trajectory_gate_fires_on_silent_failure(self) -> None:
        result = self.evaluate(trials_path=self.fault("trajectory"))
        self.assertEqual(result["decision"], "FAIL")
        self.assertIn("G_TRAJECTORY_POLICY", result["failed_gate_ids"])
        silent = [trial for trial in result["trials"] if trial["silent_trajectory_failure"]]
        self.assertEqual(len(silent), 1)
        self.assertEqual(silent[0]["outcome_gate_failures"], [])

    def test_known_bad_safety_and_privacy_gates_fire(self) -> None:
        safety = self.evaluate(trials_path=self.fault("safety"))
        privacy = self.evaluate(trials_path=self.fault("privacy"))
        self.assertIn("G_SAFETY_COMMITMENT", safety["failed_gate_ids"])
        self.assertIn("G_PRIVACY_EMAIL", privacy["failed_gate_ids"])
        self.assertGreater(safety["summary"]["safety_failures"], 0)
        self.assertGreater(privacy["summary"]["privacy_failures"], 0)

    def test_model_gate_is_release_critical(self) -> None:
        rows = self.load_jsonl("judgments.jsonl")
        rows[0]["gate_answers"]["G_MODEL_GROUNDED"] = "FAIL"
        path = self.write_jsonl("judgments-fail.jsonl", rows)
        result = self.evaluate(judgments_path=path)
        self.assertEqual(result["decision"], "FAIL")
        self.assertIn("G_MODEL_GROUNDED", result["failed_gate_ids"])

    def test_missing_or_invalid_evidence_blocks_instead_of_passing(self) -> None:
        missing_path = self.write_jsonl("empty-judgments.jsonl", [])
        missing = self.evaluate(judgments_path=missing_path)
        invalid_metrics = self.evaluate(trials_path=self.fault("missing-metrics"))
        self.assertEqual(missing["decision"], "BLOCKED")
        self.assertEqual(invalid_metrics["decision"], "BLOCKED")
        self.assertTrue(missing["evidence_errors"])
        self.assertTrue(invalid_metrics["evidence_errors"])

    def test_invalid_utf8_json_and_jsonl_block_instead_of_crashing(self) -> None:
        suite_path = self.project / "suite.json"
        original_suite = suite_path.read_bytes()
        suite_path.write_bytes(b"\xff")
        invalid_json = self.evaluate()
        self.assertEqual(invalid_json["decision"], "BLOCKED")
        self.assertTrue(
            any("UTF-8" in error for error in invalid_json["evidence_errors"])
        )

        suite_path.write_bytes(original_suite)
        cases_path = self.project / "cases.jsonl"
        cases_path.write_bytes(b"\xff")
        invalid_jsonl = self.evaluate()
        self.assertEqual(invalid_jsonl["decision"], "BLOCKED")
        self.assertTrue(
            any("UTF-8" in error for error in invalid_jsonl["evidence_errors"])
        )

    def test_fractional_token_counts_and_limits_are_rejected(self) -> None:
        rows = self.load_jsonl("trials.jsonl")
        rows[0]["metrics"]["input_tokens"] = 0.9
        fractional_evidence = self.evaluate(
            trials_path=self.write_jsonl("fractional-tokens.jsonl", rows)
        )
        self.assertEqual(fractional_evidence["decision"], "BLOCKED")
        self.assertTrue(
            any(
                "metrics.input_tokens must be an integer" in error
                for error in fractional_evidence["evidence_errors"]
            )
        )

        suite = json.loads((self.project / "suite.json").read_text(encoding="utf-8"))
        suite["release_rules"]["max_total_tokens_per_trial"] = 0.9
        self.rewrite_suite(suite)
        fractional_limit = self.evaluate()
        self.assertEqual(fractional_limit["decision"], "BLOCKED")
        self.assertTrue(
            any(
                "max_total_tokens_per_trial must be an integer" in error
                for error in fractional_limit["evidence_errors"]
            )
        )

    def test_non_finite_operational_metrics_block(self) -> None:
        for index, value in enumerate((float("nan"), float("inf"))):
            with self.subTest(value=value):
                rows = self.load_jsonl("trials.jsonl")
                rows[0]["metrics"]["latency_ms"] = value
                path = self.write_jsonl(f"non-finite-{index}.jsonl", rows)
                result = self.evaluate(trials_path=path)
                self.assertEqual(result["decision"], "BLOCKED")
                self.assertTrue(
                    any("latency_ms" in error for error in result["evidence_errors"])
                )

    def test_malformed_identifiers_block_without_crashing(self) -> None:
        cases = self.load_jsonl("cases.jsonl")
        cases[0]["case_id"] = {"not": "hashable"}
        self.write_jsonl("cases.jsonl", cases)
        malformed_case = self.evaluate()
        self.assertEqual(malformed_case["decision"], "BLOCKED")
        self.assertTrue(
            any("case_id" in error for error in malformed_case["evidence_errors"])
        )

        shutil.copyfile(EXAMPLE / "cases.jsonl", self.project / "cases.jsonl")
        rows = self.load_jsonl("trials.jsonl")
        rows[0]["trial_id"] = ["not", "hashable"]
        rows[0]["isolation_id"] = {"not": "hashable"}
        malformed_trial_path = self.write_jsonl("malformed-identifiers.jsonl", rows)
        malformed_trial = self.evaluate(trials_path=malformed_trial_path)
        self.assertEqual(malformed_trial["decision"], "BLOCKED")
        self.assertTrue(
            any("trial_id" in error for error in malformed_trial["evidence_errors"])
        )

    def test_provenance_mismatch_blocks(self) -> None:
        run_path = self.project / "run.json"
        run = json.loads(run_path.read_text(encoding="utf-8"))
        run["dataset"]["cases_sha256"] = "0" * 64
        run_path.write_text(json.dumps(run, indent=2), encoding="utf-8")
        result = self.evaluate()
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(any("cases_sha256" in error for error in result["evidence_errors"]))

    def test_malformed_nested_provenance_blocks_without_crashing(self) -> None:
        run_path = self.project / "run.json"
        run = json.loads(run_path.read_text(encoding="utf-8"))
        run["dataset"] = []
        run_path.write_text(json.dumps(run, indent=2), encoding="utf-8")
        result = self.evaluate()
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(any("run.dataset" in error for error in result["evidence_errors"]))

    def test_minimum_trials_and_operational_guardrails(self) -> None:
        one_each = [
            row for row in self.load_jsonl("trials.jsonl") if row["trial_index"] == 1
        ]
        too_few_path = self.write_jsonl("too-few.jsonl", one_each)
        too_few = self.evaluate(trials_path=too_few_path)
        retries = self.evaluate(trials_path=self.fault("retries"))
        self.assertEqual(too_few["decision"], "BLOCKED")
        self.assertEqual(retries["decision"], "FAIL")
        self.assertIn("max_retries_per_trial", retries["failed_release_rules"])

    def test_capability_and_regression_suites_apply_different_reliability_rules(self) -> None:
        fault_path = self.fault("outcome")
        regression = self.evaluate(trials_path=fault_path)
        suite = json.loads((self.project / "suite.json").read_text(encoding="utf-8"))
        suite["suite_type"] = "capability"
        suite["release_rules"]["min_trial_pass_rate"] = 0.5
        suite["release_rules"]["require_all_regression_trials"] = False
        self.rewrite_suite(suite)
        capability = self.evaluate(trials_path=fault_path)
        self.assertEqual(regression["decision"], "FAIL")
        self.assertEqual(capability["decision"], "PASS")
        self.assertIn("G_OUTCOME_DECISION", capability["failed_gate_ids"])

    def test_deterministic_only_suite_does_not_require_model_evidence(self) -> None:
        suite = json.loads((self.project / "suite.json").read_text(encoding="utf-8"))
        suite["model_graders"] = []
        suite["rubric"] = []
        suite.pop("calibration")
        self.rewrite_suite(suite)
        (self.project / "judgments.jsonl").unlink()
        (self.project / "calibration.json").unlink()
        result = self.evaluate()
        self.assertEqual(result["decision"], "PASS")

    def test_deterministic_failures_skip_unneeded_model_evidence(self) -> None:
        rows = self.load_jsonl("trials.jsonl")
        for row in rows:
            row["outcome"]["decision"] = "known-bad"
        path = self.write_jsonl("all-deterministic-fail.jsonl", rows)
        (self.project / "judgments.jsonl").unlink()
        (self.project / "calibration.json").unlink()
        result = self.evaluate(trials_path=path)
        self.assertEqual(result["decision"], "FAIL")
        self.assertEqual(result["summary"]["passed_trials"], 0)
        self.assertTrue(all(trial["model_grading_skipped"] for trial in result["trials"]))

    def test_invalid_release_and_calibration_contracts_block(self) -> None:
        suite = json.loads((self.project / "suite.json").read_text(encoding="utf-8"))
        del suite["release_rules"]["min_case_pass_rate"]
        self.rewrite_suite(suite)
        invalid_rules = self.evaluate()
        self.assertEqual(invalid_rules["decision"], "BLOCKED")
        self.assertTrue(
            any("min_case_pass_rate" in error for error in invalid_rules["evidence_errors"])
        )

        suite["release_rules"]["min_case_pass_rate"] = 1.0
        self.rewrite_suite(suite)
        calibration_path = self.project / "calibration.json"
        calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
        calibration["metrics"] = []
        calibration_path.write_text(json.dumps(calibration, indent=2), encoding="utf-8")
        invalid_calibration = self.evaluate()
        self.assertEqual(invalid_calibration["decision"], "BLOCKED")
        self.assertTrue(
            any("calibration.metrics" in error for error in invalid_calibration["evidence_errors"])
        )

    def test_malformed_deterministic_grader_blocks_without_crashing(self) -> None:
        suite = json.loads((self.project / "suite.json").read_text(encoding="utf-8"))
        suite["deterministic_graders"][3]["params"] = []
        self.rewrite_suite(suite)
        result = self.evaluate()
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(any("params" in error for error in result["evidence_errors"]))

        suite = json.loads((self.project / "suite.json").read_text(encoding="utf-8"))
        suite["deterministic_graders"][0]["id"] = []
        self.rewrite_suite(suite)
        result = self.evaluate()
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(any("string id" in error for error in result["evidence_errors"]))

    def test_failure_slices_and_clusters_are_explainable(self) -> None:
        result = self.evaluate(trials_path=self.fault("mixed"))
        self.assertEqual(result["decision"], "FAIL")
        self.assertIn("category=electronics", result["slices"])
        self.assertTrue(result["failure_clusters"])
        self.assertEqual(result["failure_clusters"][0]["method"], "lexical-v1")

    def test_calibration_uses_human_goldens_and_fails_bias(self) -> None:
        suite = json.loads((self.project / "suite.json").read_text(encoding="utf-8"))
        good = calibrate(
            suite,
            self.project / "calibration" / "human-goldens.jsonl",
            self.project / "calibration" / "judge-labels.jsonl",
        )
        bad = calibrate(
            suite,
            self.project / "calibration" / "human-goldens.jsonl",
            self.project / "calibration" / "judge-labels-biased.jsonl",
        )
        self.assertEqual(good["status"], "PASS")
        self.assertEqual(good["golden_set"]["source"], "human")
        self.assertTrue(good["golden_set"]["held_out"])
        self.assertEqual(bad["status"], "FAIL")
        self.assertGreater(bad["metrics"]["false_positive_rate"], 0)

    def test_calibration_blocks_small_sets_and_rejects_degenerate_judge(self) -> None:
        suite = json.loads((self.project / "suite.json").read_text(encoding="utf-8"))
        goldens = self.load_jsonl("calibration/human-goldens.jsonl")
        judgments = self.load_jsonl("calibration/judge-labels.jsonl")

        small_goldens = self.write_jsonl("small-goldens.jsonl", goldens[:5])
        small_judgments = self.write_jsonl("small-judgments.jsonl", judgments[:5])
        too_small = calibrate(suite, small_goldens, small_judgments)
        self.assertEqual(too_small["status"], "BLOCKED")
        self.assertTrue(any("minimum" in error for error in too_small["evidence_errors"]))

        degenerate = []
        for human in goldens:
            degenerate.append(
                {
                    "item_id": human["item_id"],
                    "judge_id": suite["calibration"]["judge_id"],
                    "labels": {
                        grader_id: "PASS" for grader_id in human["labels"]
                    },
                    "scores": human["scores"],
                }
            )
        degenerate_path = self.write_jsonl("degenerate-judge.jsonl", degenerate)
        result = calibrate(
            suite,
            self.project / "calibration" / "human-goldens.jsonl",
            degenerate_path,
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertLess(result["metrics"]["cohens_kappa"], suite["calibration"]["minimum_kappa"])

    def test_calibration_rejects_non_string_judge_id_without_crashing(self) -> None:
        suite = json.loads((self.project / "suite.json").read_text(encoding="utf-8"))
        judgments = self.load_jsonl("calibration/judge-labels.jsonl")
        judgments[0]["judge_id"] = []
        judgment_path = self.write_jsonl("invalid-judge-id.jsonl", judgments)

        result = calibrate(
            suite,
            self.project / "calibration" / "human-goldens.jsonl",
            judgment_path,
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("judge_id" in error for error in result["evidence_errors"]))

        suite["calibration"]["judge_id"] = []
        result = calibrate(
            suite,
            self.project / "calibration" / "human-goldens.jsonl",
            self.project / "calibration" / "judge-labels.jsonl",
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("judge_id" in error for error in result["evidence_errors"]))

    def test_calibration_cannot_hide_a_bad_dimension_in_pooled_metrics(self) -> None:
        suite = json.loads((self.project / "suite.json").read_text(encoding="utf-8"))
        second = dict(suite["model_graders"][0])
        second["id"] = "G_MODEL_SECOND"
        second["name"] = "second independently calibrated dimension"
        suite["model_graders"].append(second)
        goldens = self.load_jsonl("calibration/human-goldens.jsonl")
        judgments = self.load_jsonl("calibration/judge-labels.jsonl")
        for human, judge in zip(goldens, judgments):
            human["labels"][second["id"]] = human["labels"]["G_MODEL_GROUNDED"]
            judge["labels"][second["id"]] = judge["labels"]["G_MODEL_GROUNDED"]
        mismatched = next(
            row
            for row in judgments
            if row["labels"][second["id"]] == "PASS"
        )
        mismatched["labels"][second["id"]] = "FAIL"
        golden_path = self.write_jsonl("two-dimension-goldens.jsonl", goldens)
        judgment_path = self.write_jsonl("two-dimension-judgments.jsonl", judgments)

        result = calibrate(suite, golden_path, judgment_path)

        self.assertEqual(result["status"], "FAIL")
        self.assertGreaterEqual(
            result["metrics"]["label_agreement_interval_95"]["lower"],
            suite["calibration"]["minimum_agreement"],
        )
        self.assertLess(
            result["metrics"]["label_dimensions"][second["id"]][
                "agreement_interval_95"
            ]["lower"],
            suite["calibration"]["minimum_agreement"],
        )

    def test_imported_calibration_requires_complete_dimension_counts(self) -> None:
        calibration_path = self.project / "calibration.json"
        original = json.loads(calibration_path.read_text(encoding="utf-8"))
        mutations = (
            ("label_dimensions", "G_MODEL_GROUNDED"),
            ("score_dimensions", "C_CLARITY"),
        )
        for group, dimension in mutations:
            with self.subTest(group=group, dimension=dimension):
                calibration = json.loads(json.dumps(original))
                calibration["metrics"][group][dimension]["n"] = 1
                calibration_path.write_text(
                    json.dumps(calibration, indent=2), encoding="utf-8"
                )
                result = self.evaluate()
                self.assertEqual(result["decision"], "BLOCKED")
                self.assertTrue(
                    any("sample count" in error for error in result["evidence_errors"])
                )
        calibration_path.write_text(json.dumps(original, indent=2), encoding="utf-8")

    def test_non_gating_trajectory_check_is_diagnostic(self) -> None:
        suite = json.loads((self.project / "suite.json").read_text(encoding="utf-8"))
        trajectory = next(
            grader
            for grader in suite["deterministic_graders"]
            if grader["id"] == "G_TRAJECTORY_POLICY"
        )
        trajectory["gate"] = False
        self.rewrite_suite(suite)
        result = self.evaluate(trials_path=self.fault("trajectory"))
        self.assertEqual(result["decision"], "PASS")
        self.assertNotIn("G_TRAJECTORY_POLICY", result["failed_gate_ids"])
        diagnostic = [
            trial
            for trial in result["trials"]
            if "G_TRAJECTORY_POLICY" in trial["diagnostic_failure_ids"]
        ]
        self.assertEqual(len(diagnostic), 1)
        self.assertLess(diagnostic[0]["partial_quality_score"], 1.0)

    def test_duplicate_trial_isolation_blocks(self) -> None:
        rows = self.load_jsonl("trials.jsonl")
        rows[1]["isolation_id"] = rows[0]["isolation_id"]
        path = self.write_jsonl("shared-isolation.jsonl", rows)
        result = self.evaluate(trials_path=path)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(any("isolation_id" in error for error in result["evidence_errors"]))

    def test_stdio_adapter_runs_fresh_trials_without_expected_answers(self) -> None:
        adapter = Path(self.tempdir.name) / "adapter.py"
        adapter.write_text(
            "import hashlib, json, sys\n"
            "request = json.load(sys.stdin)\n"
            "assert 'expected' not in request\n"
            "case_id = request['case_id']\n"
            "category = 'electronics' if case_id == 'A400' else 'bedding'\n"
            "method = 'in-store' if case_id == 'A400' else 'mail-back'\n"
            "print(json.dumps({\n"
            "  'status': 'completed',\n"
            "  'outcome': {'decision': 'ALLOW', 'method': method, 'message': 'Eligible.'},\n"
            "  'trajectory': [{'index': 1, 'type': 'tool', 'name': 'get_policy_doc', 'attributes': {'category': category}}],\n"
            "  'metrics': {'latency_ms': 1, 'input_tokens': 1, 'output_tokens': 1, 'cost_usd': 0, 'retries': 0},\n"
            "  'missing_evidence': [],\n"
            "  'environment_fingerprint': hashlib.sha256(b'reference-clean-state').hexdigest(),\n"
            "  'isolation_id': request['trial_id']\n"
            "}))\n",
            encoding="utf-8",
        )
        out = self.project / "adapter-trials.jsonl"
        errors = execute_trials(
            self.project,
            [sys.executable, str(adapter)],
            out,
            timeout_seconds=5,
        )
        self.assertEqual(errors, [])
        rows = self.load_jsonl("adapter-trials.jsonl")
        self.assertEqual(len(rows), 4)
        self.assertEqual(len({row["isolation_id"] for row in rows}), 4)
        result = self.evaluate(trials_path=out)
        self.assertEqual(result["decision"], "PASS")

    def test_stdio_adapter_failure_becomes_blocked_evidence(self) -> None:
        adapter = Path(self.tempdir.name) / "broken-adapter.py"
        adapter.write_text("print('not-json')\n", encoding="utf-8")
        out = self.project / "broken-trials.jsonl"
        errors = execute_trials(
            self.project,
            [sys.executable, str(adapter)],
            out,
            timeout_seconds=5,
        )
        self.assertTrue(errors)
        result = self.evaluate(trials_path=out)
        self.assertEqual(result["decision"], "BLOCKED")

    def test_stdio_adapter_output_is_bounded_while_the_process_runs(self) -> None:
        adapter = Path(self.tempdir.name) / "oversized-adapter.py"
        adapter.write_text(
            "import sys\n"
            f"sys.stdout.write('x' * {MAX_ADAPTER_OUTPUT_BYTES + 1})\n",
            encoding="utf-8",
        )
        out = self.project / "oversized-trials.jsonl"
        errors = execute_trials(
            self.project,
            [sys.executable, str(adapter)],
            out,
            timeout_seconds=5,
        )
        self.assertEqual(len(errors), 4)
        self.assertTrue(all("stdout exceeds" in error for error in errors))
        self.assertEqual(self.evaluate(trials_path=out)["decision"], "BLOCKED")

    def test_stdio_adapter_input_and_stderr_are_bounded(self) -> None:
        cases = self.load_jsonl("cases.jsonl")
        cases[0]["input"] = "x" * (MAX_ADAPTER_INPUT_BYTES + 1)
        self.write_jsonl("cases.jsonl", cases)
        unused_adapter = Path(self.tempdir.name) / "unused-adapter.py"
        unused_adapter.write_text("raise SystemExit(99)\n", encoding="utf-8")
        input_errors = execute_trials(
            self.project,
            [sys.executable, str(unused_adapter)],
            self.project / "oversized-input-trials.jsonl",
            timeout_seconds=5,
        )
        input_limit_errors = [
            error for error in input_errors if "input exceeds" in error
        ]
        self.assertEqual(len(input_limit_errors), 2)

        shutil.copyfile(EXAMPLE / "cases.jsonl", self.project / "cases.jsonl")
        stderr_adapter = Path(self.tempdir.name) / "oversized-stderr-adapter.py"
        stderr_adapter.write_text(
            "import sys\n"
            f"sys.stderr.write('x' * {MAX_ADAPTER_ERROR_BYTES + 1})\n",
            encoding="utf-8",
        )
        stderr_errors = execute_trials(
            self.project,
            [sys.executable, str(stderr_adapter)],
            self.project / "oversized-stderr-trials.jsonl",
            timeout_seconds=5,
        )
        self.assertEqual(len(stderr_errors), 4)
        self.assertTrue(all("stderr exceeds" in error for error in stderr_errors))

    def test_stdio_adapter_timeout_becomes_blocked_evidence(self) -> None:
        adapter = Path(self.tempdir.name) / "slow-adapter.py"
        adapter.write_text("import time\ntime.sleep(1)\n", encoding="utf-8")
        out = self.project / "timed-out-trials.jsonl"
        errors = execute_trials(
            self.project,
            [sys.executable, str(adapter)],
            out,
            timeout_seconds=0.05,
        )
        self.assertEqual(len(errors), 4)
        self.assertTrue(all("timed out" in error for error in errors))
        self.assertEqual(self.evaluate(trials_path=out)["decision"], "BLOCKED")

    @unittest.skipUnless(os.name == "posix", "process-group isolation is POSIX-only")
    def test_inherited_adapter_streams_cannot_defeat_timeout(self) -> None:
        adapter = Path(self.tempdir.name) / "inherited-streams-adapter.py"
        adapter.write_text(
            "import subprocess, sys\n"
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])\n",
            encoding="utf-8",
        )
        out = self.project / "inherited-streams-trials.jsonl"
        started = time.monotonic()
        errors = execute_trials(
            self.project,
            [sys.executable, str(adapter)],
            out,
            timeout_seconds=0.1,
        )
        elapsed = time.monotonic() - started
        self.assertEqual(len(errors), 4)
        self.assertTrue(all("timed out" in error for error in errors))
        self.assertLess(elapsed, 3)
        self.assertEqual(self.evaluate(trials_path=out)["decision"], "BLOCKED")

    def test_non_finite_adapter_timeout_is_rejected(self) -> None:
        for timeout in (float("nan"), float("inf")):
            with self.subTest(timeout=timeout):
                with self.assertRaises(EvidenceError):
                    execute_trials(
                        self.project,
                        [sys.executable, "-c", "pass"],
                        self.project / "invalid-timeout.jsonl",
                        timeout_seconds=timeout,
                    )

    def test_trajectory_indexes_must_be_ordered_and_contiguous(self) -> None:
        rows = self.load_jsonl("trials.jsonl")
        rows[0]["trajectory"][0]["index"], rows[0]["trajectory"][1]["index"] = (
            rows[0]["trajectory"][1]["index"],
            rows[0]["trajectory"][0]["index"],
        )
        path = self.write_jsonl("unordered-trajectory.jsonl", rows)
        result = self.evaluate(trials_path=path)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(
            any("contiguous and ordered" in error for error in result["evidence_errors"])
        )

    def test_inspection_exposes_failure_trace(self) -> None:
        result = self.evaluate(trials_path=self.fault("trajectory"))
        raw_trials = self.load_jsonl("fault-trajectory.jsonl")
        inspection = render_inspection(result, raw_trials, case_id="A400")
        self.assertIn("G_TRAJECTORY_POLICY", inspection)
        self.assertIn("get_policy_doc", inspection)
        self.assertIn("Raw outcome", inspection)

    def test_results_are_reproducible_and_reports_redact_secrets(self) -> None:
        first = self.evaluate()
        time.sleep(1.1)
        second = self.evaluate()
        self.assertEqual(first, second)

        secret = "api_key=" + "synthetic-secret-value-1234567890"
        first["failure_clusters"] = [
            {
                "label": "Synthetic",
                "size": 1,
                "method": "test",
                "representative": secret,
            }
        ]
        report = render_markdown(first)
        self.assertNotIn(secret, report)
        self.assertIn("[REDACTED]", report)

    def test_future_schema_versions_block_explicitly(self) -> None:
        suite = json.loads((self.project / "suite.json").read_text(encoding="utf-8"))
        suite["schema_version"] = "2.0"
        self.rewrite_suite(suite)
        result = self.evaluate()
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(any("schema_version" in error for error in result["evidence_errors"]))

    def test_swapped_order_bias_analysis(self) -> None:
        stable = analyze_pairwise_bias(
            self.project / "calibration" / "pairwise-stable.jsonl"
        )
        biased = analyze_pairwise_bias(
            self.project / "calibration" / "pairwise-biased.jsonl"
        )
        self.assertEqual(stable["status"], "PASS")
        self.assertEqual(stable["position_consistency"], 1.0)
        self.assertEqual(biased["status"], "FAIL")
        self.assertLess(biased["position_consistency"], 1.0)

    def test_pairwise_bias_rejects_duplicate_pair_ids(self) -> None:
        rows = self.load_jsonl("calibration/pairwise-stable.jsonl")
        rows.append(dict(rows[0]))
        result = analyze_pairwise_bias(self.write_jsonl("duplicate-pairs.jsonl", rows))

        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("unique" in error for error in result["evidence_errors"]))

    def test_machine_and_human_reports_state_limitations(self) -> None:
        result = self.evaluate()
        report = render_markdown(result)
        self.assertIn("Release decision: PASS", report)
        self.assertIn("Outcome vs trajectory", report)
        self.assertIn("calibrated judgments, not objective measurements", report)
        self.assertIn("production monitoring", report.lower())
        json.dumps(result)

    def test_migrated_source_data_hashes_are_preserved(self) -> None:
        migrated = EXAMPLE.parent / "migrated"
        expected = {
            "pm-evals/examples/coding-assistant/traces.jsonl.xz": "765d9d93190e5118e9938562910f934f7dffc5e08e47b81ad19d2a4973a2a4b4",
            "pm-evals/examples/customer-support/traces.jsonl.xz": "852faec7628b5866000515515ed990dd669c8bc2f02d4dfe9553db8259386784",
            "pm-evals/examples/summarization/traces.jsonl.xz": "b6dc285179f89266b0ad94c0eb96f838ddc681971d45b95eeb83030de3ba53d5",
            "pm-evals/examples/summarization/sources.jsonl.xz": "1c69abd25163de3d87f2b948be4681f8c0ef48db7bd26fa51a0ce500b2e0ae90",
            "pm-evals/golden/golden_scores.json": "fe1c6576e8f379797d56bf85f99cdf79795375e1caeb53ca8ef7776839739ab6",
            "Evals-pass-1/eval_set.json": "ca5ff2f491cb8959d6ef1478dc9bef2c12c47330ea5d66ed5a49bb17f6ee9476",
            "Evals-pass-1/part2/verdicts.json": "6f79b427af22c4dfd709e5fa83d2a7bf381b399a90f68590ce572a513b27a519",
            "Evals-pass-1/part2/verdicts_swapped.json": "250b37150f117eb4bce657e0033dc6af391c179f731fbaca353efe929c14b355",
        }
        for relative, digest in expected.items():
            with self.subTest(relative=relative):
                path = migrated / relative
                if path.suffix == ".xz":
                    actual = hashlib.sha256()
                    with lzma.open(path, "rb") as handle:
                        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                            actual.update(chunk)
                    self.assertEqual(actual.hexdigest(), digest)
                else:
                    self.assertEqual(sha256_file(path), digest)


if __name__ == "__main__":
    unittest.main()
