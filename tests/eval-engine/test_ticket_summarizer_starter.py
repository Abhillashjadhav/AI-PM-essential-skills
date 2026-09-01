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
    / "ticket-summarizer-starter"
)
sys.path.insert(0, str(HARNESS))

from pm_verifier.adapter import execute_trials  # noqa: E402
from pm_verifier.engine import evaluate_project  # noqa: E402
from pm_verifier.faults import apply_faults  # noqa: E402
from pm_verifier.io import sha256_file  # noqa: E402


class TicketSummarizerStarterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name) / "eval"
        shutil.copytree(EXAMPLE, self.project)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def rows(self, path: Path) -> list[dict]:
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_clean_execution_is_repeatable_and_passes(self) -> None:
        first_path = self.project / "trials.first.jsonl"
        second_path = self.project / "trials.second.jsonl"
        adapter = [sys.executable, str(self.project / "reference_adapter.py")]

        self.assertEqual(execute_trials(self.project, adapter, first_path, timeout_seconds=5), [])
        self.assertEqual(execute_trials(self.project, adapter, second_path, timeout_seconds=5), [])
        self.assertEqual(first_path.read_bytes(), second_path.read_bytes())

        result = evaluate_project(self.project, trials_path=first_path)
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["summary"]["case_count"], 3)
        self.assertEqual(result["summary"]["trial_count"], 6)
        self.assertEqual(set(result["surfaces"]), {"outcome", "trajectory"})
        self.assertNotIn("memory", result["surfaces"])
        self.assertEqual(result["summary"]["safety_failures"], 0)
        self.assertEqual(result["summary"]["privacy_failures"], 0)

    def test_every_named_fault_fails_the_expected_gate(self) -> None:
        trials_path = self.project / "trials.executed.jsonl"
        adapter = [sys.executable, str(self.project / "reference_adapter.py")]
        self.assertEqual(execute_trials(self.project, adapter, trials_path, timeout_seconds=5), [])
        source = self.rows(trials_path)
        specs = json.loads((self.project / "faults/specs.json").read_text(encoding="utf-8"))
        expected = {
            "fabricated-claim": "G_OUTCOME_CLAIMS",
            "missing-escalation": "G_OUTCOME_ESCALATION",
            "wrong-order": "G_TRAJECTORY_CHRONOLOGY",
        }

        for name, mutations in specs.items():
            with self.subTest(name=name):
                fault_path = self.project / f"trials.{name}.jsonl"
                fault_path.write_text(
                    "".join(
                        json.dumps(row, sort_keys=True) + "\n"
                        for row in apply_faults(source, mutations)
                    ),
                    encoding="utf-8",
                )
                result = evaluate_project(
                    self.project,
                    trials_path=fault_path,
                )
                self.assertEqual(result["decision"], "FAIL")
                self.assertIn(expected[name], result["failed_gate_ids"])

    def test_hash_bound_inputs_and_demo_are_present(self) -> None:
        dataset = json.loads((self.project / "dataset.json").read_text(encoding="utf-8"))
        run = json.loads((self.project / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(dataset["cases_sha256"], sha256_file(self.project / "cases.jsonl"))
        self.assertEqual(run["dataset"]["cases_sha256"], dataset["cases_sha256"])
        self.assertEqual(run["configuration"]["sha256"], sha256_file(self.project / "suite.json"))
        self.assertEqual(run["candidate"]["sha256"], sha256_file(self.project / "reference_adapter.py"))
        self.assertTrue((self.project / "EVAL_CONTRACT.md").is_file())
        self.assertTrue((self.project / "tools/demo.py").is_file())


if __name__ == "__main__":
    unittest.main()
