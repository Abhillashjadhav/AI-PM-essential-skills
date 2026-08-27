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
from pm_verifier.io import EvidenceError, sha256_file  # noqa: E402
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
            "system-incomplete-fail",
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
        output = self.project / "trials-fault-cli.jsonl"
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
        before = output.read_bytes()
        self.assertEqual(
            main(
                [
                    "fault",
                    "--project",
                    str(self.project),
                    "--name",
                    "system-identity-fail",
                    "--out",
                    output.name,
                ]
            ),
            0,
        )
        self.assertEqual(output.read_bytes(), before)

    def test_fault_command_refuses_to_overwrite_source_evidence(self) -> None:
        for relative in (
            "trials.jsonl",
            "suite.json",
            "run.json",
            "dataset.json",
            "cases.jsonl",
            "reference_adapter.py",
        ):
            with self.subTest(relative=relative):
                source = self.project / relative
                before = source.read_bytes()
                exit_code = main(
                    [
                        "fault",
                        "--project",
                        str(self.project),
                        "--name",
                        "system-identity-fail",
                        "--out",
                        relative,
                    ]
                )
                self.assertEqual(exit_code, 2)
                self.assertEqual(source.read_bytes(), before)

    def test_fault_command_refuses_to_overwrite_declared_lineage_artifact(self) -> None:
        artifact = self.project / "contracts" / "trials-engineering.jsonl"
        artifact.write_text('{"contract":"engineering"}\n', encoding="utf-8")

        run_path = self.project / "run.json"
        run = json.loads(run_path.read_text(encoding="utf-8"))
        engineering = next(
            item for item in run["contract_lineage"] if item["role"] == "engineering"
        )
        engineering["path"] = "contracts/trials-engineering.jsonl"
        engineering["sha256"] = sha256_file(artifact)
        run_path.write_text(
            json.dumps(run, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        trials = self._rows("trials.jsonl")
        run_hash = sha256_file(run_path)
        for trial in trials:
            trial["run_sha256"] = run_hash
        self._write_rows("trials.jsonl", trials)
        self.assertEqual(evaluate_project(self.project)["decision"], "PASS")

        before = artifact.read_bytes()
        exit_code = main(
            [
                "fault",
                "--project",
                str(self.project),
                "--name",
                "system-identity-fail",
                "--out",
                "contracts/trials-engineering.jsonl",
            ]
        )
        self.assertEqual(exit_code, 2)
        self.assertEqual(artifact.read_bytes(), before)

    def test_fault_command_rejects_redirected_destinations(self) -> None:
        adapter = self.project / "reference_adapter.py"
        before = adapter.read_bytes()
        symlink = self.project / "trials-fault-link.jsonl"
        symlink.symlink_to(adapter)
        exit_code = main(
            [
                "fault",
                "--project",
                str(self.project),
                "--name",
                "system-identity-fail",
                "--out",
                symlink.name,
            ]
        )
        self.assertEqual(exit_code, 2)
        self.assertEqual(adapter.read_bytes(), before)
        self.assertTrue(symlink.is_symlink())

        outside = Path(self.tempdir.name) / "trials-fault-outside.jsonl"
        exit_code = main(
            [
                "fault",
                "--project",
                str(self.project),
                "--name",
                "system-identity-fail",
                "--out",
                str(outside),
            ]
        )
        self.assertEqual(exit_code, 2)
        self.assertFalse(outside.exists())

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
