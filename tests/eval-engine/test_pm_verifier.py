from __future__ import annotations

import hashlib
import json
import lzma
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
from pm_verifier.io import sha256_file  # noqa: E402
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

    def test_migrated_source_data_hashes_are_preserved(self) -> None:
        migrated = EXAMPLE.parent / "migrated"
        expected = {
            "pm-evals/examples/coding-assistant/traces.jsonl.xz": "4d410728942947e1d75bec11e69b419b31f01903e6d6283450ef5a8f6ef92182",
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
