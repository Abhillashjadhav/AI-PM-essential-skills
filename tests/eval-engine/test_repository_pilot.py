from __future__ import annotations

import importlib.util
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
PILOT_TOOL = EXAMPLE / "tools" / "repository_pilot.py"
sys.path.insert(0, str(HARNESS))

from pm_verifier.adapter import execute_trials  # noqa: E402
from pm_verifier.engine import evaluate_project  # noqa: E402


def _load_pilot_tool():
    spec = importlib.util.spec_from_file_location("repository_pilot", PILOT_TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load repository pilot tool: {PILOT_TOOL}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pilot = _load_pilot_tool()


class RepositoryPilotTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.project = self.root / "customer-support-pilot"
        shutil.copytree(EXAMPLE, self.project)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _load(self, relative: str) -> dict:
        return json.loads((self.project / relative).read_text(encoding="utf-8"))

    def _write(self, relative: str, payload: dict) -> None:
        (self.project / relative).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_create_copies_only_the_customer_support_pilot_and_never_overwrites(self) -> None:
        destination = self.root / "created-pilot"
        summary = pilot.create_pilot(destination)
        self.assertEqual(summary["template_id"], "customer-support-agent")
        self.assertEqual(summary["decision"], "GO")
        self.assertEqual(pilot.verify_pilot(destination)["status"], "VERIFIED")

        before = {
            path.relative_to(destination): path.read_bytes()
            for path in destination.rglob("*")
            if path.is_file()
        }
        with self.assertRaises(pilot.PilotError):
            pilot.create_pilot(destination)
        after = {
            path.relative_to(destination): path.read_bytes()
            for path in destination.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, before)

    def test_bind_is_idempotent_and_produces_a_valid_runtime_project(self) -> None:
        first = pilot.bind_pilot(self.project)
        snapshot = {
            path.relative_to(self.project): path.read_bytes()
            for path in self.project.rglob("*")
            if path.is_file()
        }
        second = pilot.bind_pilot(self.project)
        rerun = {
            path.relative_to(self.project): path.read_bytes()
            for path in self.project.rglob("*")
            if path.is_file()
        }

        self.assertEqual(first, second)
        self.assertEqual(snapshot, rerun)
        self.assertEqual(first["status"], "VERIFIED")
        self.assertEqual(first["requirement_count"], 3)
        self.assertEqual(first["acceptance_criteria_count"], 3)
        self.assertEqual(first["case_count"], 2)
        self.assertGreater(first["grader_count"], 10)
        self.assertEqual(evaluate_project(self.project)["decision"], "PASS")

    def test_verify_rejects_tampering_at_every_bound_boundary(self) -> None:
        pilot.bind_pilot(self.project)
        bound_files = (
            "pilot.json",
            "ci/github-actions.yml",
            "contracts/pmos-contract.json",
            "suite.json",
            "cases.jsonl",
            "dataset.json",
            "contracts/eval-contract.json",
            "contracts/engineering-contract.json",
            "reference_adapter.py",
            "product-package.json",
            "tools/repository_pilot.py",
            "run.json",
            "trials.jsonl",
        )
        for relative in bound_files:
            with self.subTest(relative=relative):
                mutated = self.root / f"mutated-{relative.replace('/', '-') }"
                shutil.copytree(self.project, mutated)
                target = mutated / relative
                target.write_bytes(target.read_bytes() + b"\n")
                with self.assertRaises(pilot.PilotError):
                    pilot.verify_pilot(mutated)

    def test_candidate_and_adapter_can_live_in_different_repository_paths(self) -> None:
        repository = self.root / "real-repository"
        project = repository / "eval" / "customer-support"
        source = repository / "src" / "candidate.py"
        source.parent.mkdir(parents=True)
        source.write_text("def candidate():\n    return 'ready'\n", encoding="utf-8")
        shutil.copytree(EXAMPLE, project)
        config = json.loads((project / "pilot.json").read_text(encoding="utf-8"))
        config["candidate_files"] = ["src/candidate.py"]
        config["paths"]["trials"] = "trials.candidate.jsonl"
        config["synthetic_fixture"] = False
        (project / "pilot.json").write_text(
            json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        summary = pilot.bind_pilot(project, repository)

        self.assertEqual(summary["status"], "BOUND")
        evidence = project / config["paths"]["trials"]
        adapter = [sys.executable, str(project / "reference_adapter.py")]
        self.assertEqual(
            execute_trials(project, adapter, evidence, timeout_seconds=5), []
        )
        verified = pilot.verify_pilot(project, repository)
        self.assertEqual(verified["status"], "VERIFIED")
        self.assertEqual(verified["candidate_sha256"], summary["candidate_sha256"])

    def test_bind_rejects_unapproved_or_ambiguous_product_intent(self) -> None:
        pmos = self._load("contracts/pmos-contract.json")
        invalid_mutations = (
            lambda value: value.update({"decision": "HOLD"}),
            lambda value: value.update({"unresolved_questions": ["Which refund policy?"]}),
            lambda value: value["requirements"].append(value["requirements"][0]),
            lambda value: value["acceptance_criteria"][0].update(
                {"requirement_ids": ["FR-999"]}
            ),
        )
        for mutate in invalid_mutations:
            with self.subTest(line=mutate.__code__.co_firstlineno):
                candidate = json.loads(json.dumps(pmos))
                mutate(candidate)
                self._write("contracts/pmos-contract.json", candidate)
                with self.assertRaises(pilot.PilotError):
                    pilot.bind_pilot(self.project)
                self._write("contracts/pmos-contract.json", pmos)

    def test_verify_requires_complete_case_and_grader_traceability(self) -> None:
        pilot.bind_pilot(self.project)
        contract = self._load("contracts/eval-contract.json")
        contract["traceability"][0]["grader_ids"] = []
        self._write("contracts/eval-contract.json", contract)
        with self.assertRaises(pilot.PilotError):
            pilot.bind_pilot(self.project)

        shutil.rmtree(self.project)
        shutil.copytree(EXAMPLE, self.project)
        cases = [
            json.loads(line)
            for line in (self.project / "cases.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        cases[0]["traceability"]["acceptance_criteria_ids"] = []
        (self.project / "cases.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in cases),
            encoding="utf-8",
        )
        with self.assertRaises(pilot.PilotError):
            pilot.bind_pilot(self.project)

    def test_candidate_paths_must_stay_inside_the_selected_repository(self) -> None:
        config = self._load("pilot.json")
        config["candidate_files"] = ["../outside.py"]
        self._write("pilot.json", config)
        with self.assertRaises(pilot.PilotError):
            pilot.bind_pilot(self.project)

    def test_ci_example_runs_chain_verification_before_execution(self) -> None:
        workflow = (self.project / "ci" / "github-actions.yml").read_text(
            encoding="utf-8"
        )
        verify = workflow.index("repository_pilot.py verify")
        execute = workflow.index("pm-verifier execute")
        self.assertLess(verify, execute)
        self.assertIn("1511156a38d14c162ee7c0e92b14d16e43144f47", workflow)
        self.assertIn("actions/upload-artifact@", workflow)


if __name__ == "__main__":
    unittest.main()
