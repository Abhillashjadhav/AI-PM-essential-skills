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

    def _snapshot(self) -> dict[Path, bytes]:
        return {
            path.relative_to(self.project): path.read_bytes()
            for path in self.project.rglob("*")
            if path.is_file()
        }

    def _jsonl(self, relative: str) -> list[dict]:
        return [
            json.loads(line)
            for line in (self.project / relative).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _write_jsonl(self, relative: str, rows: list[dict]) -> None:
        (self.project / relative).write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
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

    def test_bind_invalidates_stale_synthetic_evidence_without_relabeling(self) -> None:
        pilot.bind_pilot(self.project)
        trials_before = (self.project / "trials.jsonl").read_bytes()
        candidate = self.project / "synthetic_candidate.py"
        candidate.write_text(
            "raise RuntimeError('changed candidate must require fresh evidence')\n",
            encoding="utf-8",
        )

        summary = pilot.bind_pilot(self.project)

        self.assertEqual(summary["status"], "BOUND")
        self.assertEqual((self.project / "trials.jsonl").read_bytes(), trials_before)
        self.assertEqual(
            self._load("evidence-receipt.json")["evidence_status"], "PENDING"
        )
        with self.assertRaisesRegex(pilot.PilotError, "evidence is pending"):
            pilot.verify_pilot(self.project)

        errors = execute_trials(
            self.project,
            [sys.executable, str(self.project / "reference_adapter.py")],
            self.project / "trials.jsonl",
            timeout_seconds=5,
        )
        self.assertEqual(len(errors), 4)
        self.assertEqual(pilot.bind_pilot(self.project)["status"], "VERIFIED")
        self.assertEqual(pilot.verify_pilot(self.project)["status"], "VERIFIED")
        self.assertEqual(evaluate_project(self.project)["decision"], "BLOCKED")

    def test_verify_rejects_tampering_at_every_bound_boundary(self) -> None:
        pilot.bind_pilot(self.project)
        bound_files = (
            "pilot.json",
            "ci/github-actions.yml",
            "contracts/pmos-contract.json",
            "suite.json",
            "cases.jsonl",
            "dataset.json",
            "evidence-receipt.json",
            "contracts/eval-contract.json",
            "contracts/engineering-contract.json",
            "reference_adapter.py",
            "synthetic_candidate.py",
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
        with self.assertRaises(pilot.PilotError):
            pilot.verify_pilot(project, repository)
        sealed = pilot.bind_pilot(project, repository)
        self.assertEqual(sealed["status"], "VERIFIED")
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
        cases = self._jsonl("cases.jsonl")
        cases[0]["traceability"]["acceptance_criteria_ids"] = []
        self._write_jsonl("cases.jsonl", cases)
        with self.assertRaises(pilot.PilotError):
            pilot.bind_pilot(self.project)

    def test_bind_rejects_swapped_acceptance_relationships(self) -> None:
        contract = self._load("contracts/eval-contract.json")
        contract["traceability"][0]["acceptance_criteria_ids"] = ["AC-003"]
        contract["traceability"][2]["acceptance_criteria_ids"] = ["AC-001"]
        self._write("contracts/eval-contract.json", contract)

        with self.assertRaisesRegex(pilot.PilotError, "do not match PMOS links"):
            pilot.bind_pilot(self.project)

    def test_bind_rejects_a_referenced_case_without_its_fr_ac_relationship(self) -> None:
        cases = self._jsonl("cases.jsonl")
        cases[0]["traceability"]["requirement_ids"].remove("FR-001")
        cases[0]["traceability"]["acceptance_criteria_ids"].remove("AC-001")
        self._write_jsonl("cases.jsonl", cases)

        with self.assertRaisesRegex(pilot.PilotError, "does not carry its FR/AC"):
            pilot.bind_pilot(self.project)

    def test_bind_rejects_managed_path_aliases_before_writing(self) -> None:
        config = self._load("pilot.json")
        config["paths"]["eval_contract"] = config["paths"]["pmos_contract"]
        self._write("pilot.json", config)
        before = self._snapshot()

        with self.assertRaisesRegex(pilot.PilotError, "pilot paths alias"):
            pilot.bind_pilot(self.project)

        self.assertEqual(self._snapshot(), before)

    def test_bind_rejects_a_managed_path_that_aliases_pilot_config(self) -> None:
        config = self._load("pilot.json")
        config["paths"]["portable_package"] = "pilot.json"
        self._write("pilot.json", config)
        before = self._snapshot()

        with self.assertRaisesRegex(pilot.PilotError, "pilot paths alias"):
            pilot.bind_pilot(self.project)

        self.assertEqual(self._snapshot(), before)

    def test_bind_rejects_hardlinked_managed_paths_before_writing(self) -> None:
        alias = self.project / "eval-hardlink.json"
        alias.hardlink_to(self.project / "contracts" / "pmos-contract.json")
        config = self._load("pilot.json")
        config["paths"]["eval_contract"] = alias.name
        self._write("pilot.json", config)
        before = self._snapshot()

        with self.assertRaisesRegex(pilot.PilotError, "pilot paths alias"):
            pilot.bind_pilot(self.project)

        self.assertEqual(self._snapshot(), before)

    def test_bind_rejects_candidate_aliases_before_writing(self) -> None:
        config = self._load("pilot.json")
        config["candidate_files"] = [config["paths"]["pmos_contract"]]
        self._write("pilot.json", config)
        before = self._snapshot()

        with self.assertRaisesRegex(
            pilot.PilotError, "candidate and managed paths alias"
        ):
            pilot.bind_pilot(self.project)

        self.assertEqual(self._snapshot(), before)

    def test_verify_rejects_semantic_trial_tampering_with_preserved_run_ids(self) -> None:
        pilot.bind_pilot(self.project)
        trials = self._jsonl("trials.jsonl")
        trials[0]["outcome"]["decision"] = "REPLACE"
        self._write_jsonl("trials.jsonl", trials)

        with self.assertRaisesRegex(pilot.PilotError, "exact trial contents"):
            pilot.verify_pilot(self.project)

    def test_candidate_paths_must_stay_inside_the_selected_repository(self) -> None:
        config = self._load("pilot.json")
        config["candidate_files"] = ["../outside.py"]
        self._write("pilot.json", config)
        with self.assertRaises(pilot.PilotError):
            pilot.bind_pilot(self.project)

    def test_harness_owned_paths_cannot_be_reconfigured(self) -> None:
        harness_paths = ("suite", "dataset", "cases", "run")
        for key in harness_paths:
            with self.subTest(key=key):
                shutil.rmtree(self.project)
                shutil.copytree(EXAMPLE, self.project)
                config = self._load("pilot.json")
                source = self.project / config["paths"][key]
                alternate = self.project / f"alternate-{source.name}"
                shutil.copy2(source, alternate)
                config["paths"][key] = alternate.name
                self._write("pilot.json", config)
                before = self._snapshot()

                with self.assertRaisesRegex(
                    pilot.PilotError, "evaluation harness owns this filename"
                ):
                    pilot.bind_pilot(self.project)

                self.assertEqual(self._snapshot(), before)

    def test_ci_example_runs_chain_verification_before_execution(self) -> None:
        workflow = (self.project / "ci" / "github-actions.yml").read_text(
            encoding="utf-8"
        )
        verify = workflow.index("repository_pilot.py verify")
        execute = workflow.index("pm-verifier execute")
        self.assertLess(verify, execute)
        self.assertIn("1511156a38d14c162ee7c0e92b14d16e43144f47", workflow)
        self.assertIn("actions/upload-artifact@", workflow)

    def _real_pdc(self) -> dict:
        return json.loads(
            (ROOT / "tests/eval-engine/fixtures/pmos-pdc-v1.json").read_text(encoding="utf-8")
        )

    def _use_support_pdc(self) -> dict:
        # The unmodified cross-repo health fixture is tested separately. This
        # synthetic PDC maps the existing support intent without changing it.
        legacy = self._load("contracts/pmos-contract.json")
        pdc = self._real_pdc()
        pdc.update({
            "contract_id": "synthetic-support-pdc",
            "product_name": "Synthetic support agent",
            "problem": legacy["customer_problem"],
            "target_user": legacy["target_user"],
            "desired_outcome": legacy["expected_ai_outcome"],
            "scope": legacy["scope"]["v1"],
            "out_of_scope": legacy["scope"]["out_of_scope"],
            "functional_requirements": [
                {"id": row["id"], "title": row["intent"]}
                for row in legacy["requirements"]
            ],
            "acceptance_criteria": [
                {"id": row["id"], "criterion": row["intent"], "requirement": row["requirement_ids"][0]}
                for row in legacy["acceptance_criteria"]
            ],
        })
        self._write("contracts/pmos-contract.json", pdc)
        return pdc

    def test_real_pmos_pdc_v1_maps_exact_source_ids(self) -> None:
        fixture = ROOT / "tests/eval-engine/fixtures/pmos-pdc-v1.json"
        import hashlib
        self.assertEqual(
            hashlib.sha256(fixture.read_bytes()).hexdigest(),
            "0339adbc2c54acf58646ecbdd2e76d53e659e4c0999a19706ed81506ca4797d7",
        )
        contract = self._real_pdc()
        before = json.dumps(contract, sort_keys=True)
        self.assertEqual(
            pilot._validate_pmos(contract, "a-separate-runtime-product-id"),
            (("FR-001",), ("AC-001",), {"AC-001": frozenset({"FR-001"})}),
        )
        self.assertEqual(json.dumps(contract, sort_keys=True), before)

    def test_pdc_bind_preserves_source_identity_and_standalone_evaluation(self) -> None:
        pdc = self._use_support_pdc()
        before = (self.project / "contracts/pmos-contract.json").read_bytes()
        summary = pilot.bind_pilot(self.project)
        self.assertEqual(summary["status"], "BOUND")
        self.assertEqual(summary["decision"], "APPROVED")
        identity = summary["source_contract"]
        self.assertEqual(identity["dialect"], "product-decision-contract-v1")
        self.assertEqual(identity["contract_id"], pdc["contract_id"])
        self.assertEqual(identity["contract_version"], 1)
        self.assertNotEqual(summary["product_id"], pdc["product_name"])
        self.assertEqual(self._load("product-package.json")["source_contract"], identity)
        self.assertEqual(self._load("run.json")["contract_lineage"][0]["version"], "1")
        self.assertEqual(
            (self.project / "contracts/pmos-contract.json").read_bytes(), before
        )
        self.assertEqual(execute_trials(
            self.project, [sys.executable, str(self.project / "reference_adapter.py")],
            self.project / "trials.jsonl", timeout_seconds=5,
        ), [])
        self.assertEqual(pilot.bind_pilot(self.project)["status"], "VERIFIED")
        self.assertEqual(pilot.verify_pilot(self.project)["status"], "VERIFIED")
        self.assertEqual(evaluate_project(self.project)["decision"], "PASS")

    def test_pdc_rejects_missing_required_fields_and_malformed_shapes(self) -> None:
        pdc = self._real_pdc()
        for field in pdc:
            with self.subTest(missing=field):
                value = json.loads(json.dumps(pdc))
                del value[field]
                with self.assertRaises(pilot.PilotError):
                    pilot._validate_pmos(value, "runtime-product")
        mutations = (
            lambda p: p.update(contract_version=True),
            lambda p: p.update(contract_version=1.0),
            lambda p: p.update(contract_version=2),
            lambda p: p.update(contract_status="DRAFT"),
            lambda p: p.update(approved_by=" "),
            lambda p: p.update(approved_at=""),
            lambda p: p.update(guardrails={}),
            lambda p: p.update(functional_requirements=[]),
            lambda p: p["functional_requirements"].append(p["functional_requirements"][0]),
            lambda p: p["acceptance_criteria"].append(p["acceptance_criteria"][0]),
            lambda p: p["acceptance_criteria"][0].update(requirement="FR-UNKNOWN"),
            lambda p: p["acceptance_criteria"][0].update(criterion=[]),
            lambda p: p["functional_requirements"][0].update(capability=1),
            lambda p: p["known_risks"][0].update(level="unknown"),
            lambda p: p.update(schema_version="1.0", decision="GO"),
            lambda p: p.update(unresolved_questions=[{
                "id": "Q-001", "question": "Which policy?", "product_critical": True,
            }]),
            lambda p: p.update(unresolved_questions=[{
                "id": "Q-001", "question": "Which policy?", "product_critical": 1,
            }]),
        )
        for mutate in mutations:
            with self.subTest(line=mutate.__code__.co_firstlineno):
                value = json.loads(json.dumps(pdc))
                mutate(value)
                with self.assertRaises(pilot.PilotError):
                    pilot._validate_pmos(value, "runtime-product")

    def test_pdc_gate_refs_are_optional_but_must_name_existing_criteria(self) -> None:
        pdc = self._real_pdc()
        pilot._validate_pmos(pdc, "runtime-product")
        pdc["binary_release_gates"][0]["acceptance_criterion_refs"] = ["AC-001"]
        pilot._validate_pmos(pdc, "runtime-product")
        for refs in ([], ["AC-UNKNOWN"], ["AC-001", "AC-001"], "AC-001", [True], [{}]):
            with self.subTest(refs=refs):
                pdc["binary_release_gates"][0]["acceptance_criterion_refs"] = refs
                with self.assertRaises(pilot.PilotError):
                    pilot._validate_pmos(pdc, "runtime-product")

    def test_pdc_bad_shape_fails_before_any_binding_write(self) -> None:
        self._use_support_pdc()
        pdc = self._load("contracts/pmos-contract.json")
        pdc["acceptance_criteria"][0]["requirement"] = "FR-UNKNOWN"
        self._write("contracts/pmos-contract.json", pdc)
        before = self._snapshot()
        with self.assertRaises(pilot.PilotError):
            pilot.bind_pilot(self.project)
        self.assertEqual(self._snapshot(), before)

    def test_pdc_approved_intent_tampering_invalidates_bound_evidence(self) -> None:
        original = self._use_support_pdc()
        pilot.bind_pilot(self.project)
        mutations = (
            lambda p: p["functional_requirements"][0].update(title="Unapproved replacement intent"),
            lambda p: p["acceptance_criteria"][0].update(criterion="Unapproved acceptance"),
            lambda p: p["binary_release_gates"][0].update(description="Unapproved release gate"),
            lambda p: p.update(approved_by="different-approver"),
            lambda p: p.update(source_digest="sha256:" + "0" * 64),
        )
        for mutate in mutations:
            with self.subTest(line=mutate.__code__.co_firstlineno):
                pdc = json.loads(json.dumps(original))
                mutate(pdc)
                self._write("contracts/pmos-contract.json", pdc)
                with self.assertRaisesRegex(pilot.PilotError, "binding does not match its artifact"):
                    pilot.verify_pilot(self.project)
        self._write("contracts/pmos-contract.json", original)
        self.assertEqual(pilot.bind_pilot(self.project)["status"], "BOUND")

    def test_pdc_loader_rejects_duplicate_approval_keys(self) -> None:
        path = self.project / "contracts/pmos-contract.json"
        path.write_text('{"contract_status":"APPROVED","contract_status":"DRAFT"}')
        with self.assertRaisesRegex(pilot.PilotError, "duplicate JSON object key"):
            pilot.bind_pilot(self.project)


if __name__ == "__main__":
    unittest.main()
