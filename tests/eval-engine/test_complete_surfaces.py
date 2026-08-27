from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "pm-verifier" / "skills" / "eval-engine" / "harness"
LEGACY_EXAMPLE = (
    ROOT
    / "pm-verifier"
    / "skills"
    / "eval-engine"
    / "examples"
    / "production-eval"
)
sys.path.insert(0, str(HARNESS))

from pm_verifier.engine import evaluate_project  # noqa: E402
from pm_verifier.adapter import execute_trials  # noqa: E402
from pm_verifier.graders import grade_deterministic, validate_grader  # noqa: E402
from pm_verifier.io import EvidenceError, sha256_file  # noqa: E402
from pm_verifier.reporting import render_inspection, render_markdown  # noqa: E402


CHECKPOINTS = ["intake", "identity", "policy", "decision", "delivery"]


class CompleteSurfaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name) / "eval"
        self._configure_complete_suite()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _load(self, relative: str) -> dict:
        return json.loads((self.project / relative).read_text(encoding="utf-8"))

    def _write(self, relative: str, value: dict) -> None:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _load_rows(self, relative: str) -> list[dict]:
        return [
            json.loads(line)
            for line in (self.project / relative).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _write_rows(self, relative: str, rows: list[dict]) -> None:
        (self.project / relative).write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )

    def _rewrite_trials(self, rows: list[dict]) -> None:
        run = self._load("run.json")
        run_hash = sha256_file(self.project / "run.json")
        for row in rows:
            row["run_id"] = run["run_id"]
            row["run_sha256"] = run_hash
        self._write_rows("trials.jsonl", rows)

    def _rewrite_suite(self, suite: dict) -> None:
        self._write("suite.json", suite)
        run = self._load("run.json")
        run["configuration"]["id"] = suite["suite_id"]
        run["configuration"]["version"] = suite["suite_version"]
        run["configuration"]["sha256"] = sha256_file(self.project / "suite.json")
        self._write("run.json", run)
        self._rewrite_trials(self._load_rows("trials.jsonl"))

    def _configure_complete_suite(self) -> None:
        if self.project.exists():
            shutil.rmtree(self.project)
        shutil.copytree(LEGACY_EXAMPLE, self.project)
        suite = self._load("suite.json")
        suite.update(
            {
                "schema_version": "1.1",
                "suite_id": "support-workflow-complete-regression",
                "suite_version": "2.0.0",
                "name": "Synthetic support workflow complete regression",
                "surfaces": ["outcome", "trajectory", "system", "memory"],
                "system_contract": {
                    "required_checkpoints": CHECKPOINTS,
                    "optional_checkpoints": ["notification"],
                    "identity_field": "entity_id",
                    "continuity_fields": ["customer_id", "content_id"],
                },
                "state_contract": {
                    "enabled": True,
                    "required_operations": ["write", "retrieve", "update", "delete"],
                    "isolation_dimensions": ["session", "user", "project"],
                    "maximum_staleness_seconds": 0,
                    "conflict_policy": "latest_write_wins",
                    "require_temporal_order": True,
                },
                "lineage_contract": {"required_roles": ["pmos", "engineering"]},
                "model_graders": [],
                "rubric": [],
            }
        )
        suite.pop("calibration", None)
        suite["release_rules"].pop("min_model_score", None)
        suite["deterministic_graders"].extend(
            [
                *[
                    {
                        "id": f"G_SYSTEM_STAGE_{name.upper()}",
                        "name": f"{name} checkpoint passed",
                        "scope": "system",
                        "category": "reliability",
                        "check": "checkpoint_passed",
                        "params": {"checkpoint": name},
                        "gate": True,
                    }
                    for name in CHECKPOINTS
                ],
                {
                    "id": "G_SYSTEM_ORDER",
                    "name": "required checkpoint order",
                    "scope": "system",
                    "category": "reliability",
                    "check": "checkpoint_order",
                    "params": {"checkpoints": CHECKPOINTS},
                    "gate": True,
                },
                {
                    "id": "G_SYSTEM_IDENTITY",
                    "name": "ticket identity preserved",
                    "scope": "system",
                    "category": "reliability",
                    "check": "identity_preserved",
                    "params": {"checkpoints": CHECKPOINTS, "field": "entity_id"},
                    "gate": True,
                },
                {
                    "id": "G_SYSTEM_CONTINUITY",
                    "name": "customer and content continuity",
                    "scope": "system",
                    "category": "quality",
                    "check": "state_continuity",
                    "params": {
                        "checkpoints": CHECKPOINTS,
                        "fields": ["customer_id", "content_id"],
                    },
                    "gate": True,
                },
                {
                    "id": "G_SYSTEM_COMPLETED",
                    "name": "workflow completed",
                    "scope": "system",
                    "category": "reliability",
                    "check": "system_completed",
                    "params": {},
                    "gate": True,
                },
                {
                    "id": "G_SYSTEM_FINAL",
                    "name": "final delivery reached",
                    "scope": "system",
                    "category": "reliability",
                    "check": "final_checkpoint_reached",
                    "params": {"checkpoint": "delivery"},
                    "gate": True,
                },
                {
                    "id": "G_MEMORY_WRITE",
                    "name": "preference written",
                    "scope": "memory",
                    "category": "reliability",
                    "check": "state_written",
                    "params": {"key": "language"},
                    "gate": True,
                },
                {
                    "id": "G_MEMORY_RETRIEVE",
                    "name": "updated preference retrieved",
                    "scope": "memory",
                    "category": "quality",
                    "check": "state_equals_expected",
                    "expected_path": "expected.memory.retrieved_value",
                    "params": {"key": "language"},
                    "gate": True,
                },
                {
                    "id": "G_MEMORY_UPDATE",
                    "name": "preference updated",
                    "scope": "memory",
                    "category": "reliability",
                    "check": "state_updated",
                    "params": {"key": "language"},
                    "gate": True,
                },
                {
                    "id": "G_MEMORY_DELETE",
                    "name": "preference forgotten",
                    "scope": "memory",
                    "category": "privacy",
                    "check": "state_deleted",
                    "params": {"key": "language"},
                    "gate": True,
                },
                {
                    "id": "G_MEMORY_ABSENT",
                    "name": "forgotten preference absent",
                    "scope": "memory",
                    "category": "privacy",
                    "check": "state_not_present",
                    "params": {"key": "language"},
                    "gate": True,
                },
                {
                    "id": "G_MEMORY_ISOLATION",
                    "name": "state isolated by session user and project",
                    "scope": "memory",
                    "category": "privacy",
                    "check": "state_isolated",
                    "params": {"dimensions": ["session", "user", "project"]},
                    "gate": True,
                },
                {
                    "id": "G_MEMORY_FRESH",
                    "name": "retrieved state is fresh",
                    "scope": "memory",
                    "category": "reliability",
                    "check": "state_not_stale",
                    "params": {"maximum_age_seconds": 0},
                    "gate": True,
                },
                {
                    "id": "G_MEMORY_CONFLICT",
                    "name": "write conflict resolved",
                    "scope": "memory",
                    "category": "reliability",
                    "check": "state_conflict_resolved",
                    "params": {"policy": "latest_write_wins"},
                    "gate": True,
                },
                {
                    "id": "G_MEMORY_TEMPORAL",
                    "name": "memory events preserve time order",
                    "scope": "memory",
                    "category": "reliability",
                    "check": "state_temporal_order",
                    "params": {},
                    "gate": True,
                },
            ]
        )

        cases = self._load_rows("cases.jsonl")
        for case in cases:
            case["expected"]["memory"] = {"retrieved_value": "fr"}
        self._write_rows("cases.jsonl", cases)

        dataset = self._load("dataset.json")
        dataset["schema_version"] = "1.1"
        dataset["cases_sha256"] = sha256_file(self.project / "cases.jsonl")
        self._write("dataset.json", dataset)

        contract_root = self.project / "contracts"
        contract_root.mkdir(exist_ok=True)
        self._write(
            "contracts/pmos-contract.json",
            {"contract_id": "synthetic-support-decision", "version": "1.0.0"},
        )
        self._write(
            "contracts/engineering-contract.json",
            {"contract_id": "synthetic-support-build", "version": "1.0.0"},
        )

        self._write("suite.json", suite)
        run = self._load("run.json")
        run["schema_version"] = "1.1"
        run["configuration"].update(
            {
                "id": suite["suite_id"],
                "version": suite["suite_version"],
                "sha256": sha256_file(self.project / "suite.json"),
            }
        )
        run["dataset"]["cases_sha256"] = dataset["cases_sha256"]
        run["contract_lineage"] = [
            {
                "role": "pmos",
                "id": "synthetic-support-decision",
                "version": "1.0.0",
                "path": "contracts/pmos-contract.json",
                "sha256": sha256_file(contract_root / "pmos-contract.json"),
            },
            {
                "role": "engineering",
                "id": "synthetic-support-build",
                "version": "1.0.0",
                "path": "contracts/engineering-contract.json",
                "sha256": sha256_file(contract_root / "engineering-contract.json"),
            },
        ]
        self._write("run.json", run)

        trials = self._load_rows("trials.jsonl")
        for trial in trials:
            case_id = trial["case_id"]
            state = {"customer_id": f"customer-{case_id}", "content_id": f"content-{case_id}"}
            trial["system"] = {
                "entity_id": case_id,
                "completed": True,
                "first_failure_stage": None,
                "consequences": [],
                "checkpoints": [
                    {
                        "index": index,
                        "name": name,
                        "status": "passed",
                        "entity_id": case_id,
                        "state": copy.deepcopy(state),
                        "reason": "synthetic checkpoint completed",
                    }
                    for index, name in enumerate(CHECKPOINTS, 1)
                ],
            }
            scope = {
                "session_id": f"session-{trial['trial_id']}",
                "user_id": f"user-{case_id}",
                "project_id": "support-project",
            }
            trial["memory"] = {
                "events": [
                    {
                        "index": 1,
                        "operation": "write",
                        "key": "language",
                        "status": "passed",
                        "value": "en",
                        "version": 1,
                        "scope": scope,
                        "occurred_at": "2026-08-27T00:00:01+00:00",
                    },
                    {
                        "index": 2,
                        "operation": "retrieve",
                        "key": "language",
                        "status": "passed",
                        "value": "en",
                        "version": 1,
                        "age_seconds": 0,
                        "scope": scope,
                        "occurred_at": "2026-08-27T00:00:02+00:00",
                    },
                    {
                        "index": 3,
                        "operation": "update",
                        "key": "language",
                        "status": "passed",
                        "value": "fr",
                        "version": 2,
                        "scope": scope,
                        "occurred_at": "2026-08-27T00:00:03+00:00",
                    },
                    {
                        "index": 4,
                        "operation": "retrieve",
                        "key": "language",
                        "status": "passed",
                        "value": "fr",
                        "version": 2,
                        "age_seconds": 0,
                        "scope": scope,
                        "occurred_at": "2026-08-27T00:00:04+00:00",
                    },
                    {
                        "index": 5,
                        "operation": "delete",
                        "key": "language",
                        "status": "passed",
                        "value": None,
                        "version": 3,
                        "scope": scope,
                        "occurred_at": "2026-08-27T00:00:05+00:00",
                    },
                ],
                "final_state": {},
                "isolation_checks": [
                    {"dimension": dimension, "passed": True, "reason": "no cross-scope read"}
                    for dimension in ("session", "user", "project")
                ],
                "conflicts": [
                    {
                        "key": "language",
                        "policy": "latest_write_wins",
                        "status": "resolved",
                        "winner_version": 2,
                    }
                ],
            }
        self._rewrite_trials(trials)

    def evaluate(self) -> dict:
        return evaluate_project(self.project)

    def test_legacy_suite_remains_compatible(self) -> None:
        self.assertEqual(evaluate_project(LEGACY_EXAMPLE)["decision"], "PASS")

    def test_known_good_covers_all_four_surfaces_and_lineage(self) -> None:
        result = self.evaluate()
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["schema_version"], "1.1")
        self.assertEqual(set(result["summary"]["surfaces"]), set(("outcome", "trajectory", "system", "memory")))
        self.assertEqual(result["summary"]["surfaces"]["system"]["pass_rate"], 1.0)
        self.assertEqual(result["summary"]["surfaces"]["memory"]["pass_rate"], 1.0)
        self.assertEqual({item["role"] for item in result["contract_lineage"]}, {"pmos", "engineering"})

    def test_system_discovery_failure_cannot_be_erased_by_later_success(self) -> None:
        trials = self._load_rows("trials.jsonl")
        trials[0]["system"]["checkpoints"][0]["status"] = "failed"
        trials[0]["system"]["checkpoints"][0]["reason"] = "intake rejected"
        trials[0]["system"]["first_failure_stage"] = "intake"
        trials[0]["system"]["completed"] = False
        trials[0]["system"]["consequences"] = ["ticket was not durably accepted"]
        self._rewrite_trials(trials)
        result = self.evaluate()
        self.assertEqual(result["decision"], "FAIL")
        failed = next(row for row in result["trials"] if row["trial_id"] == trials[0]["trial_id"])
        self.assertIn("G_SYSTEM_STAGE_INTAKE", failed["system_gate_failures"])
        self.assertEqual(failed["first_system_failure_stage"], "intake")
        self.assertFalse(failed["passed"])

    def test_explicitly_incomplete_system_fails_even_when_checkpoints_pass(self) -> None:
        trials = self._load_rows("trials.jsonl")
        trials[0]["system"]["completed"] = False
        self._rewrite_trials(trials)
        result = self.evaluate()
        self.assertEqual(result["decision"], "FAIL")
        self.assertIn("G_SYSTEM_COMPLETED", result["failed_gate_ids"])

    def test_system_identity_crosswire_and_wrong_path_fail(self) -> None:
        for name in ("identity", "crosswire", "wrong-path"):
            with self.subTest(name=name):
                trials = self._load_rows("trials.jsonl")
                if name == "identity":
                    trials[0]["system"]["checkpoints"][-1]["entity_id"] = "other-ticket"
                    expected_gate = "G_SYSTEM_IDENTITY"
                elif name == "crosswire":
                    trials[0]["system"]["checkpoints"][3]["state"]["content_id"] = "other-content"
                    expected_gate = "G_SYSTEM_CONTINUITY"
                else:
                    checkpoints = trials[0]["system"]["checkpoints"]
                    checkpoints[2]["name"], checkpoints[3]["name"] = checkpoints[3]["name"], checkpoints[2]["name"]
                    expected_gate = "G_SYSTEM_ORDER"
                self._rewrite_trials(trials)
                result = self.evaluate()
                self.assertEqual(result["decision"], "FAIL")
                self.assertIn(expected_gate, result["failed_gate_ids"])
                self._configure_complete_suite()

    def test_silent_system_drop_and_inconsistent_first_failure_block(self) -> None:
        trials = self._load_rows("trials.jsonl")
        del trials[0]["system"]["checkpoints"][2]
        for index, checkpoint in enumerate(trials[0]["system"]["checkpoints"], 1):
            checkpoint["index"] = index
        self._rewrite_trials(trials)
        missing = self.evaluate()
        self.assertEqual(missing["decision"], "BLOCKED")
        self.assertTrue(any("required checkpoint 'policy'" in error for error in missing["evidence_errors"]))

        self._configure_complete_suite()
        trials = self._load_rows("trials.jsonl")
        trials[0]["system"]["checkpoints"][1]["status"] = "failed"
        self._rewrite_trials(trials)
        inconsistent = self.evaluate()
        self.assertEqual(inconsistent["decision"], "BLOCKED")
        self.assertTrue(any("first_failure_stage" in error for error in inconsistent["evidence_errors"]))

    def test_memory_forget_isolation_staleness_conflict_and_time_fail(self) -> None:
        cases = (
            ("forget", lambda memory: (memory["events"][-1].update({"status": "failed"}), memory["final_state"].update({"language": "fr"})), "G_MEMORY_DELETE"),
            ("isolation", lambda memory: memory["isolation_checks"][1].update({"passed": False}), "G_MEMORY_ISOLATION"),
            ("stale", lambda memory: memory["events"][3].update({"age_seconds": 60}), "G_MEMORY_FRESH"),
            ("conflict", lambda memory: memory["conflicts"][0].update({"status": "unresolved"}), "G_MEMORY_CONFLICT"),
            ("temporal", lambda memory: memory["events"][3].update({"occurred_at": "2026-08-26T23:59:00+00:00"}), "G_MEMORY_TEMPORAL"),
        )
        for name, mutate, expected_gate in cases:
            with self.subTest(name=name):
                trials = self._load_rows("trials.jsonl")
                mutate(trials[0]["memory"])
                self._rewrite_trials(trials)
                result = self.evaluate()
                self.assertEqual(result["decision"], "FAIL")
                self.assertIn(expected_gate, result["failed_gate_ids"])
                self._configure_complete_suite()

    def test_missing_promised_memory_or_operation_blocks(self) -> None:
        trials = self._load_rows("trials.jsonl")
        trials[0].pop("memory")
        self._rewrite_trials(trials)
        missing = self.evaluate()
        self.assertEqual(missing["decision"], "BLOCKED")
        self.assertTrue(any("memory must be an object" in error for error in missing["evidence_errors"]))

        self._configure_complete_suite()
        trials = self._load_rows("trials.jsonl")
        trials[0]["memory"]["events"] = [
            event for event in trials[0]["memory"]["events"] if event["operation"] != "update"
        ]
        for index, event in enumerate(trials[0]["memory"]["events"], 1):
            event["index"] = index
        self._rewrite_trials(trials)
        operation = self.evaluate()
        self.assertEqual(operation["decision"], "BLOCKED")
        self.assertTrue(any("required memory operation 'update'" in error for error in operation["evidence_errors"]))

    def test_memory_is_not_required_when_product_does_not_promise_it(self) -> None:
        suite = self._load("suite.json")
        suite["surfaces"].remove("memory")
        suite.pop("state_contract")
        suite["deterministic_graders"] = [
            grader for grader in suite["deterministic_graders"] if grader["scope"] != "memory"
        ]
        self._rewrite_suite(suite)
        trials = self._load_rows("trials.jsonl")
        for trial in trials:
            trial.pop("memory")
        self._rewrite_trials(trials)
        result = self.evaluate()
        self.assertEqual(result["decision"], "PASS")
        self.assertNotIn("memory", result["summary"]["surfaces"])

    def test_contract_lineage_is_required_and_hash_bound(self) -> None:
        (self.project / "contracts" / "engineering-contract.json").write_text(
            '{"tampered":true}\n', encoding="utf-8"
        )
        tampered = self.evaluate()
        self.assertEqual(tampered["decision"], "BLOCKED")
        self.assertTrue(any("contract_lineage" in error and "sha256" in error for error in tampered["evidence_errors"]))

        self._configure_complete_suite()
        run = self._load("run.json")
        run["contract_lineage"] = [item for item in run["contract_lineage"] if item["role"] != "engineering"]
        self._write("run.json", run)
        self._rewrite_trials(self._load_rows("trials.jsonl"))
        missing = self.evaluate()
        self.assertEqual(missing["decision"], "BLOCKED")
        self.assertTrue(any("required contract lineage role 'engineering'" in error for error in missing["evidence_errors"]))

    def test_contract_promises_require_explicit_release_gates(self) -> None:
        mutations = (
            (
                lambda suite: suite.update(
                    {
                        "deterministic_graders": [
                            grader
                            for grader in suite["deterministic_graders"]
                            if grader["id"] != "G_SYSTEM_COMPLETED"
                        ]
                    }
                ),
                "system contract requires a system_completed gate",
            ),
            (
                lambda suite: suite.update(
                    {
                        "deterministic_graders": [
                            grader
                            for grader in suite["deterministic_graders"]
                            if grader["id"] != "G_SYSTEM_STAGE_POLICY"
                        ]
                    }
                ),
                "checkpoint 'policy' requires a checkpoint_passed gate",
            ),
            (
                lambda suite: suite.update(
                    {
                        "deterministic_graders": [
                            grader
                            for grader in suite["deterministic_graders"]
                            if grader["id"] != "G_MEMORY_TEMPORAL"
                        ]
                    }
                ),
                "requires a state_temporal_order gate",
            ),
            (
                lambda suite: next(
                    grader
                    for grader in suite["deterministic_graders"]
                    if grader["id"] == "G_MEMORY_FRESH"
                )["params"].update({"maximum_age_seconds": 60}),
                "state_not_stale gate at least as strict",
            ),
        )
        for mutate, message in mutations:
            with self.subTest(message=message):
                suite = self._load("suite.json")
                mutate(suite)
                self._rewrite_suite(suite)
                result = self.evaluate()
                self.assertEqual(result["decision"], "BLOCKED")
                self.assertTrue(
                    any(message in error for error in result["evidence_errors"])
                )
                self._configure_complete_suite()

    def test_adversarial_lineage_and_numeric_shapes_block_without_crashing(self) -> None:
        run = self._load("run.json")
        run["contract_lineage"][0]["path"] = "contracts/invalid\u0000name.json"
        self._write("run.json", run)
        self._rewrite_trials(self._load_rows("trials.jsonl"))
        result = self.evaluate()
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(any("cannot be resolved safely" in error for error in result["evidence_errors"]))

        self._configure_complete_suite()
        suite = self._load("suite.json")
        next(
            grader
            for grader in suite["deterministic_graders"]
            if grader["id"] == "G_MEMORY_FRESH"
        )["params"]["maximum_age_seconds"] = 10**400
        self._rewrite_suite(suite)
        result = self.evaluate()
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(any("finite number" in error for error in result["evidence_errors"]))

    def test_schema_versions_must_match_before_evaluation_or_execution(self) -> None:
        run = self._load("run.json")
        run["schema_version"] = "1.0"
        self._write("run.json", run)
        self._rewrite_trials(self._load_rows("trials.jsonl"))
        result = self.evaluate()
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(
            any("run.schema_version must match" in error for error in result["evidence_errors"])
        )
        with self.assertRaises(EvidenceError):
            execute_trials(
                self.project,
                [sys.executable, str(self.project / "reference_adapter.py")],
                self.project / "trials-executed.jsonl",
                timeout_seconds=5,
            )

        self._configure_complete_suite()
        suite = self._load("suite.json")
        suite["schema_version"] = {"bad": True}
        self._write("suite.json", suite)
        with self.assertRaises(EvidenceError):
            execute_trials(
                self.project,
                [sys.executable, str(self.project / "reference_adapter.py")],
                self.project / "trials-executed.jsonl",
                timeout_seconds=5,
            )

    def test_reporting_and_inspection_show_surface_evidence(self) -> None:
        trials = self._load_rows("trials.jsonl")
        trials[0]["system"]["checkpoints"][0]["status"] = "failed"
        trials[0]["system"]["first_failure_stage"] = "intake"
        trials[0]["system"]["completed"] = False
        self._rewrite_trials(trials)
        result = self.evaluate()
        report = render_markdown(result)
        inspection = render_inspection(result, trials, trial_id=trials[0]["trial_id"])
        for heading in ("## Outcome", "## Trajectory", "## System", "## Memory", "## Safety and privacy", "## Reliability and operations"):
            self.assertIn(heading, report)
        self.assertIn("First system failure", report)
        self.assertIn("### Raw system", inspection)
        self.assertIn("### Raw memory", inspection)

    def test_generalized_grader_taxonomy_accepts_new_scopes_and_categories(self) -> None:
        for scope in ("outcome", "trajectory", "system", "memory"):
            for category in ("quality", "safety", "privacy", "reliability", "operational"):
                grader = {
                    "id": f"G_{scope}_{category}",
                    "name": "taxonomy probe",
                    "scope": scope,
                    "category": category,
                    "check": "field_present",
                    "actual_path": "outcome.decision",
                    "gate": True,
                }
                self.assertEqual(validate_grader(grader), [])

    def test_every_specialized_check_family_has_executable_evidence(self) -> None:
        trial = self._load_rows("trials.jsonl")[0]
        case = self._load_rows("cases.jsonl")[0]
        case["expected"]["system"] = {"first_failure_stage": None}
        graders = [
            {
                "id": "G_PRESENT",
                "name": "checkpoint present",
                "scope": "system",
                "category": "reliability",
                "check": "checkpoint_present",
                "params": {"checkpoint": "policy"},
                "gate": True,
            },
            {
                "id": "G_NO_LOSS",
                "name": "no silent loss",
                "scope": "system",
                "category": "reliability",
                "check": "no_silent_loss",
                "params": {"checkpoints": CHECKPOINTS},
                "gate": True,
            },
            {
                "id": "G_FIRST",
                "name": "first failure",
                "scope": "system",
                "category": "reliability",
                "check": "first_failure_equals",
                "expected_path": "expected.system.first_failure_stage",
                "params": {},
                "gate": True,
            },
            {
                "id": "G_RETRIEVED",
                "name": "state retrieved",
                "scope": "memory",
                "category": "reliability",
                "check": "state_retrieved",
                "params": {"key": "language"},
                "gate": True,
            },
        ]
        self.assertTrue(
            all(grade_deterministic(grader, trial, case)["passed"] for grader in graders)
        )

    def test_malformed_new_contract_fields_block_without_crashing(self) -> None:
        suite_mutations = (
            lambda suite: suite.update({"schema_version": {"bad": True}}),
            lambda suite: suite["system_contract"].update({"continuity_fields": [{}]}),
            lambda suite: suite["state_contract"].update({"required_operations": [{}]}),
            lambda suite: suite["state_contract"].update({"isolation_dimensions": [{}]}),
            lambda suite: suite["lineage_contract"].update({"required_roles": [{}]}),
            lambda suite: next(
                grader
                for grader in suite["deterministic_graders"]
                if grader["id"] == "G_SYSTEM_ORDER"
            ).update({"params": []}),
        )
        for mutate in suite_mutations:
            with self.subTest(kind="suite", line=mutate.__code__.co_firstlineno):
                suite = self._load("suite.json")
                mutate(suite)
                self._rewrite_suite(suite)
                self.assertEqual(self.evaluate()["decision"], "BLOCKED")
                self._configure_complete_suite()

        run = self._load("run.json")
        run["contract_lineage"][0]["role"] = {"bad": True}
        self._write("run.json", run)
        self._rewrite_trials(self._load_rows("trials.jsonl"))
        self.assertEqual(self.evaluate()["decision"], "BLOCKED")

        self._configure_complete_suite()
        trials = self._load_rows("trials.jsonl")
        trials[0]["system"]["checkpoints"][0]["status"] = {"bad": True}
        self._rewrite_trials(trials)
        self.assertEqual(self.evaluate()["decision"], "BLOCKED")

        self._configure_complete_suite()
        trials = self._load_rows("trials.jsonl")
        trials[0]["memory"]["conflicts"][0]["status"] = {"bad": True}
        self._rewrite_trials(trials)
        self.assertEqual(self.evaluate()["decision"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
