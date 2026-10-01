"""Every PM Verifier writer must preserve selected evidence on output collision."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "pm-verifier" / "skills" / "eval-engine" / "harness"
EXAMPLE = ROOT / "pm-verifier" / "skills" / "eval-engine" / "examples" / "production-eval"
sys.path.insert(0, str(HARNESS))

from pm_verifier.cli import main as cli_main  # noqa: E402
from pm_verifier.engine import evaluate_project  # noqa: E402
from pm_verifier.faults import apply_faults  # noqa: E402


class OutputAliasTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        shutil.copytree(EXAMPLE, self.project)
        self.results = self.project / "fresh-results.json"
        self.results.write_text(json.dumps(evaluate_project(self.project)))

    def test_all_other_writers_reject_selected_input_aliases(self) -> None:
        cases = (
            (["prepare", "--project", str(self.project)], self.project / "suite.json"),
            (["validate", "--project", str(self.project)], self.project / "run.json"),
            (["run", "--project", str(self.project)], self.project / "calibration.json"),
            (["report", "--results", str(self.results)], self.results),
            (["inspect", "--results", str(self.results), "--trials", str(self.project / "trials.jsonl")], self.results),
            (["calibrate", "--suite", str(self.project / "suite.json"),
              "--goldens", str(self.project / "calibration" / "human-goldens.jsonl"),
              "--judgments", str(self.project / "calibration" / "judge-labels.jsonl")], self.project / "suite.json"),
            (["bias", "--pairs", str(self.project / "calibration" / "pairwise-stable.jsonl")],
             self.project / "calibration" / "pairwise-stable.jsonl"),
        )
        for args, target in cases:
            with self.subTest(command=args[0]):
                before = target.read_bytes()
                self.assertEqual(cli_main([*args, "--out", str(target)]), 2)
                self.assertEqual(target.read_bytes(), before)

    def test_project_writer_rejects_bound_lineage_input(self) -> None:
        run_path = self.project / "run.json"
        run = json.loads(run_path.read_text())
        run["contract_lineage"] = [{"path": "reference_adapter.py"}]
        run_path.write_text(json.dumps(run))
        adapter = self.project / "reference_adapter.py"
        before = adapter.read_bytes()
        self.assertEqual(cli_main(["run", "--project", str(self.project), "--out", str(adapter)]), 2)
        self.assertEqual(adapter.read_bytes(), before)

    def test_symlink_and_hardlink_to_input_are_rejected(self) -> None:
        for variant in ("symlink", "hardlink"):
            target = self.project / "suite.json"
            alias = self.root / f"{variant}.json"
            if variant == "symlink":
                alias.symlink_to(target)
            else:
                alias.hardlink_to(target)
            before = target.read_bytes()
            with self.subTest(variant=variant):
                self.assertEqual(cli_main(["prepare", "--project", str(self.project), "--out", str(alias)]), 2)
                self.assertEqual(target.read_bytes(), before)
            alias.unlink()

    def test_missing_or_malformed_run_still_writes_blocked_result(self) -> None:
        run_path = self.project / "run.json"
        for state in ("missing", "malformed"):
            if state == "missing":
                run_path.unlink()
            else:
                run_path.write_text("{")
            for command in ("prepare", "validate", "run"):
                output = self.root / f"{state}-{command}-result.json"
                with self.subTest(state=state, command=command):
                    self.assertEqual(cli_main([command, "--project", str(self.project), "--out", str(output)]), 2)
                    self.assertEqual(json.loads(output.read_text())["decision"], "BLOCKED")

    def test_distinct_output_preserves_product_fail_result(self) -> None:
        specs = json.loads((self.project / "faults" / "specs.json").read_text())
        trials = [json.loads(line) for line in (self.project / "trials.jsonl").read_text().splitlines()]
        faulted = apply_faults(trials, specs["outcome"])
        fault_path = self.root / "faulted-trials.jsonl"
        fault_path.write_text("".join(json.dumps(row) + "\n" for row in faulted))
        result_path = self.root / "product-fail.json"
        self.assertEqual(cli_main([
            "run", "--project", str(self.project), "--trials", str(fault_path),
            "--out", str(result_path),
        ]), 1)
        self.assertEqual(json.loads(result_path.read_text())["decision"], "FAIL")

    def test_all_other_writers_keep_safe_external_output_paths(self) -> None:
        cases = (
            (["prepare", "--project", str(self.project)], self.project / "suite.json"),
            (["validate", "--project", str(self.project)], self.project / "run.json"),
            (["run", "--project", str(self.project)], self.project / "calibration.json"),
            (["report", "--results", str(self.results)], self.results),
            (["inspect", "--results", str(self.results), "--trials", str(self.project / "trials.jsonl")], self.results),
            (["calibrate", "--suite", str(self.project / "suite.json"),
              "--goldens", str(self.project / "calibration" / "human-goldens.jsonl"),
              "--judgments", str(self.project / "calibration" / "judge-labels.jsonl")], self.project / "suite.json"),
            (["bias", "--pairs", str(self.project / "calibration" / "pairwise-stable.jsonl")],
             self.project / "calibration" / "pairwise-stable.jsonl"),
        )
        for args, source in cases:
            output = self.root / f"safe-{args[0]}.json"
            before = source.read_bytes()
            with self.subTest(command=args[0]):
                self.assertIn(cli_main([*args, "--out", str(output)]), (0, 1, 2))
                self.assertTrue(output.is_file())
                self.assertEqual(source.read_bytes(), before)
