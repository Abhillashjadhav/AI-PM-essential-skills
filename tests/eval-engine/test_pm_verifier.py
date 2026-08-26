from __future__ import annotations

import json
import shutil
import sys
import tempfile
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
from pm_verifier.reporting import render_markdown  # noqa: E402


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

    def test_provenance_mismatch_blocks(self) -> None:
        run_path = self.project / "run.json"
        run = json.loads(run_path.read_text(encoding="utf-8"))
        run["dataset"]["cases_sha256"] = "0" * 64
        run_path.write_text(json.dumps(run, indent=2), encoding="utf-8")
        result = self.evaluate()
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(any("cases_sha256" in error for error in result["evidence_errors"]))

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

    def test_machine_and_human_reports_state_limitations(self) -> None:
        result = self.evaluate()
        report = render_markdown(result)
        self.assertIn("Release decision: PASS", report)
        self.assertIn("Outcome vs trajectory", report)
        self.assertIn("calibrated judgments, not objective measurements", report)
        self.assertIn("production monitoring", report.lower())
        json.dumps(result)


if __name__ == "__main__":
    unittest.main()
