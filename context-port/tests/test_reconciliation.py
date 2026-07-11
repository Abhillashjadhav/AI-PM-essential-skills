import copy
import importlib.util
import json
import sys
import subprocess
import tempfile
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
reconciliation = load("reconciliation")


class ReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads((ROOT / "fixtures" / "segregation-contextpack.json").read_text())
        mappings = json.loads((ROOT / "fixtures" / "project-mappings-valid.json").read_text())
        segregation_plan = segregation.segregate(cls.document, mappings, validator=contextport.validate)
        package = review.build_review_package(cls.document, segregation_plan)
        decision = {"decision_version": "0.1", "review_package_sha256": package["review_package_sha256"], "decision": "approve", "confirmations": {name: True for name in review.REQUIRED_CONFIRMATIONS}}
        cls.plan = reconstruction.build_reconstruction_plan(cls.document, segregation_plan, package, decision)

    def report(self, plan=None):
        return reconciliation.reconcile(self.document, plan or self.plan)

    def resign(self, plan):
        unsigned = {key: value for key, value in plan.items() if key != "reconstruction_plan_sha256"}
        plan["reconstruction_plan_sha256"] = review.canonical_digest(unsigned)
        return plan

    def test_clean_plan_has_zero_differences(self):
        report = self.report()
        self.assertEqual(report["status"], "clean")
        self.assertEqual(report["differences"], [])
        self.assertFalse(report["writer_status_flags_used"])

    def test_omission_is_reported(self):
        plan = copy.deepcopy(self.plan)
        plan["operations"] = [item for item in plan["operations"] if item["operation_id"] != "message:message-a"]
        report = self.report(self.resign(plan))
        self.assertTrue(any(item["category"] == "omission" for item in report["differences"]))

    def test_content_and_order_differences_are_reported(self):
        plan = copy.deepcopy(self.plan)
        operation = next(item for item in plan["operations"] if item["operation_id"] == "message:message-a")
        operation["payload"]["content"] = []
        operation["payload"]["ordinal"] = 9
        categories = {item["category"] for item in self.report(self.resign(plan))["differences"]}
        self.assertIn("content_difference", categories)
        self.assertIn("ordering_difference", categories)

    def test_extra_and_duplicate_operations_are_reported(self):
        plan = copy.deepcopy(self.plan)
        plan["operations"].append(copy.deepcopy(plan["operations"][0]))
        extra = copy.deepcopy(plan["operations"][0])
        extra["operation_id"] = "message:extra"
        plan["operations"].append(extra)
        categories = {item["category"] for item in self.report(self.resign(plan))["differences"]}
        self.assertIn("duplicate", categories)
        self.assertIn("extra", categories)

    def test_tampered_plan_digest_is_reported_not_trusted(self):
        plan = copy.deepcopy(self.plan)
        plan["writes_performed"] = True
        report = self.report(plan)
        self.assertTrue(any(item["category"] == "integrity_failure" for item in report["differences"]))

    def test_report_is_deterministic(self):
        self.assertEqual(self.report(), self.report())

    def test_public_schema_matches_reviewer_version(self):
        schema = json.loads((ROOT / "schemas" / "reconciliation-report-0.1.schema.json").read_text())
        self.assertEqual(schema["properties"]["reconciliation_version"]["const"], reconciliation.RECONCILIATION_VERSION)
        self.assertFalse(schema["properties"]["writer_status_flags_used"]["const"])

    def test_cli_clean_and_failed_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            clean_path = Path(directory) / "clean.json"
            failed_path = Path(directory) / "failed.json"
            clean_path.write_text(json.dumps(self.plan))
            failed = copy.deepcopy(self.plan)
            failed["operations"].pop()
            failed_path.write_text(json.dumps(self.resign(failed)))
            base = [sys.executable, str(ROOT / "contextport.py"), "reconcile-plan", str(ROOT / "fixtures" / "segregation-contextpack.json")]
            clean = subprocess.run([*base, str(clean_path)], check=False, capture_output=True, text=True)
            failed_result = subprocess.run([*base, str(failed_path)], check=False, capture_output=True, text=True)
            self.assertEqual(clean.returncode, 0)
            self.assertEqual(failed_result.returncode, 5)


if __name__ == "__main__":
    unittest.main()
