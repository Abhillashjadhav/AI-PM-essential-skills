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
    / "complete-eval"
)
sys.path.insert(0, str(HARNESS))

from pm_verifier.adapter import execute_trials  # noqa: E402
from pm_verifier.cli import main  # noqa: E402
from pm_verifier.engine import evaluate_project  # noqa: E402
from pm_verifier.faults import apply_faults  # noqa: E402
from pm_verifier.io import EvidenceError  # noqa: E402
from pm_verifier.reporting import render_markdown  # noqa: E402


class CompleteExampleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name) / "complete-eval"
        shutil.copytree(EXAMPLE, self.project)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _rows(self, relative: str) -> list[dict]:
        return [
            json.loads(line)
            for line in (self.project / relative).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _write_rows(self, relative: str, rows: list[dict]) -> Path:
        target = self.project / relative
        target.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
        return target

    def test_checked_in_and_executed_evidence_are_complete_and_repeatable(self) -> None:
        checked_in = evaluate_project(self.project)
        self.assertEqual(checked_in["decision"], "PASS")
        self.assertEqual(set(checked_in["surfaces"]), {"outcome", "trajectory", "system", "memory"})
        self.assertEqual({item["role"] for item in checked_in["contract_lineage"]}, {"pmos", "engineering"})

        adapter = [sys.executable, str(self.project / "reference_adapter.py")]
        first_path = self.project / "trials-first.jsonl"
        second_path = self.project / "trials-second.jsonl"
        self.assertEqual(execute_trials(self.project, adapter, first_path, timeout_seconds=5), [])
        self.assertEqual(execute_trials(self.project, adapter, second_path, timeout_seconds=5), [])
        self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
        first = evaluate_project(self.project, trials_path=first_path)
        second = evaluate_project(self.project, trials_path=second_path)
        self.assertEqual(first, second)
        self.assertEqual(first["decision"], "PASS")

        report = render_markdown(first)
        for heading in ("## Outcome", "## Trajectory", "## System", "## Memory"):
            self.assertIn(heading, report)

    def test_every_named_fault_has_the_expected_fail_closed_state(self) -> None:
        specs = json.loads((self.project / "faults" / "specs.json").read_text(encoding="utf-8"))
        source = self._rows("trials.jsonl")
        expected_fail = {
            "system-discovery-fail",
            "system-identity-fail",
            "system-content-crosswire",
            "system-wrong-path",
            "memory-forget-fail",
            "memory-isolation-fail",
            "memory-stale-fail",
            "memory-conflict-fail",
            "memory-temporal-fail",
        }
        expected_blocked = {
            "system-missing-evidence",
            "system-silent-drop",
            "memory-missing-evidence",
        }
        self.assertEqual(set(specs), expected_fail | expected_blocked)
        for name, mutations in specs.items():
            with self.subTest(name=name):
                path = self._write_rows(f"fault-{name}.jsonl", apply_faults(source, mutations))
                result = evaluate_project(self.project, trials_path=path)
                expected = "FAIL" if name in expected_fail else "BLOCKED"
                self.assertEqual(result["decision"], expected)

    def test_fault_command_materializes_a_named_fixture(self) -> None:
        output = self.project / "fault-cli.jsonl"
        exit_code = main(
            [
                "fault",
                "--project",
                str(self.project),
                "--name",
                "system-identity-fail",
                "--out",
                output.name,
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            evaluate_project(self.project, trials_path=output)["decision"], "FAIL"
        )

    def test_fault_command_refuses_to_overwrite_source_evidence(self) -> None:
        source = self.project / "trials.jsonl"
        before = source.read_bytes()
        exit_code = main(
            [
                "fault",
                "--project",
                str(self.project),
                "--name",
                "system-identity-fail",
                "--out",
                source.name,
            ]
        )
        self.assertEqual(exit_code, 2)
        self.assertEqual(source.read_bytes(), before)

    def test_fault_mutations_reject_malformed_evidence_and_specs(self) -> None:
        source = self._rows("trials.jsonl")
        malformed = (
            ([[]], []),
            (source, [{"trial_id": {}, "path": "system.completed", "operation": "set"}]),
            (
                source,
                [
                    {
                        "trial_id": source[0]["trial_id"],
                        "path": "system.checkpoints.not-an-index",
                        "operation": "delete",
                    }
                ],
            ),
        )
        for trials, specs in malformed:
            with self.subTest(specs=specs):
                with self.assertRaises(EvidenceError):
                    apply_faults(trials, specs)


if __name__ == "__main__":
    unittest.main()
