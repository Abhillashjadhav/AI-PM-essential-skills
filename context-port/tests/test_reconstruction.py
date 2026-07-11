import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


contextport = load("contextport")
segregation = load("segregation")
review = load("review")
reconstruction = load("reconstruction")


class ReconstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads((ROOT / "fixtures" / "segregation-contextpack.json").read_text())
        cls.mappings = json.loads((ROOT / "fixtures" / "project-mappings-valid.json").read_text())
        cls.plan = segregation.segregate(cls.document, cls.mappings, validator=contextport.validate)
        cls.package = review.build_review_package(cls.document, cls.plan)
        cls.decision = {
            "decision_version": "0.1",
            "review_package_sha256": cls.package["review_package_sha256"],
            "decision": "approve",
            "confirmations": {name: True for name in review.REQUIRED_CONFIRMATIONS},
            "note": "Synthetic approval.",
        }

    def build(self, document=None, plan=None, package=None, decision=None):
        return reconstruction.build_reconstruction_plan(
            document or self.document,
            plan or self.plan,
            package or self.package,
            decision or self.decision,
        )

    def test_plan_is_deterministic_and_performs_no_writes(self):
        self.assertEqual(self.build(), self.build())
        self.assertFalse(self.build()["writes_performed"])
        self.assertEqual(
            self.build()["reconstruction_plan_sha256"],
            "2557e140733b15f94a987aba56b261d19b35ebadcb4f1bd2ab70a1f55371912c",
        )

    def test_exact_titles_roles_and_blocks_are_preserved(self):
        plan = self.build()
        conversation = next(item for item in plan["operations"] if item["operation_id"] == "conversation:conversation-a")
        message = next(item for item in plan["operations"] if item["operation_id"] == "message:message-a")
        self.assertEqual(conversation["payload"]["title"], "Same Conversation Title")
        self.assertEqual(message["payload"]["role"], "user")
        self.assertEqual(message["payload"]["content"], self.document["messages"][0]["content"])

    def test_dependencies_follow_container_conversation_message_order(self):
        plan = self.build()
        by_id = {item["operation_id"]: item for item in plan["operations"]}
        self.assertEqual(by_id["conversation:conversation-a"]["depends_on"], ["container:project-a"])
        self.assertEqual(by_id["message:message-a"]["depends_on"], ["conversation:conversation-a"])
        self.assertEqual(by_id["conversation:conversation-u"]["depends_on"], [])

    def test_idempotency_keys_are_unique_and_stable(self):
        first = self.build()
        second = self.build()
        first_keys = [item["idempotency_key"] for item in first["operations"]]
        second_keys = [item["idempotency_key"] for item in second["operations"]]
        self.assertEqual(first_keys, second_keys)
        self.assertEqual(len(first_keys), len(set(first_keys)))

    def test_rejected_or_incomplete_review_blocks_planning(self):
        decision = copy.deepcopy(self.decision)
        decision["decision"] = "reject"
        decision["confirmations"] = {name: False for name in review.REQUIRED_CONFIRMATIONS}
        with self.assertRaisesRegex(reconstruction.ReconstructionError, "approved"):
            self.build(decision=decision)

    def test_mismatched_review_package_blocks_planning(self):
        package = copy.deepcopy(self.package)
        package["segregation_plan_sha256"] = "0" * 64
        package_without_digest = {key: value for key, value in package.items() if key != "review_package_sha256"}
        package["review_package_sha256"] = review.canonical_digest(package_without_digest)
        decision = copy.deepcopy(self.decision)
        decision["review_package_sha256"] = package["review_package_sha256"]
        with self.assertRaisesRegex(reconstruction.ReconstructionError, "does not match segregation"):
            self.build(package=package, decision=decision)

    def test_unmapped_project_blocks_planning(self):
        plan = segregation.segregate(self.document, validator=contextport.validate)
        package = review.build_review_package(self.document, plan)
        decision = copy.deepcopy(self.decision)
        decision["review_package_sha256"] = package["review_package_sha256"]
        with self.assertRaisesRegex(reconstruction.ReconstructionError, "no approved destination"):
            self.build(plan=plan, package=package, decision=decision)

    def test_public_schema_matches_engine_version(self):
        schema = json.loads((ROOT / "schemas" / "reconstruction-plan-0.1.schema.json").read_text())
        self.assertEqual(schema["properties"]["reconstruction_version"]["const"], reconstruction.RECONSTRUCTION_VERSION)
        self.assertFalse(schema["properties"]["writes_performed"]["const"])

    def test_cli_builds_dry_run_only(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "contextport.py"),
                "reconstruct-plan",
                str(ROOT / "fixtures" / "segregation-contextpack.json"),
                "--mappings",
                str(ROOT / "fixtures" / "project-mappings-valid.json"),
                "--review-package",
                str(ROOT / "fixtures" / "review-package-synthetic.json"),
                "--decision",
                str(ROOT / "fixtures" / "review-decision-approved.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)["writes_performed"])


if __name__ == "__main__":
    unittest.main()
