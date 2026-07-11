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


adapter = load("chatgpt_adapter")


class ChatGPTAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads((ROOT / "fixtures" / "reconstruction-plan-synthetic.json").read_text())

    def test_report_is_deterministic_and_offline(self):
        first = adapter.build_chatgpt_adapter_report(self.plan)
        self.assertEqual(first, adapter.build_chatgpt_adapter_report(self.plan))
        self.assertEqual(first["status"], "blocked_unsupported")
        self.assertFalse(first["writes_performed"])
        self.assertFalse(first["network_calls_performed"])
        self.assertFalse(first["browser_automation_performed"])

    def test_every_operation_is_preserved_and_explicitly_unsupported(self):
        report = adapter.build_chatgpt_adapter_report(self.plan)
        self.assertEqual(len(report["operation_assessments"]), len(self.plan["operations"]))
        for source, assessment in zip(self.plan["operations"], report["operation_assessments"]):
            self.assertEqual(assessment["source_operation"], source)
            self.assertEqual(assessment["capability_status"], "UNSUPPORTED")
            self.assertFalse(assessment["write_attempted"])

    def test_api_platform_projects_are_not_treated_as_chatgpt_projects(self):
        evidence = adapter.build_chatgpt_adapter_report(self.plan)["capability_evidence"]
        self.assertFalse(evidence["api_platform_projects_are_destination_equivalent"])

    def test_tampered_plan_is_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan["operations"][0]["payload"]["title"] = "tampered"
        with self.assertRaisesRegex(adapter.ChatGPTAdapterError, "digest"):
            adapter.build_chatgpt_adapter_report(plan)

    def test_unapproved_or_unknown_operations_are_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan["review_decision"] = "reject"
        with self.assertRaisesRegex(adapter.ChatGPTAdapterError, "approved"):
            adapter.build_chatgpt_adapter_report(plan)

    def test_public_schema_matches_adapter_version(self):
        schema = json.loads((ROOT / "schemas" / "chatgpt-adapter-report-0.1.schema.json").read_text())
        self.assertEqual(schema["properties"]["adapter_version"]["const"], adapter.ADAPTER_VERSION)
        self.assertFalse(schema["properties"]["writes_performed"]["const"])

    def test_cli_emits_blocked_report_without_writes(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "contextport.py"), "chatgpt-adapt", str(ROOT / "fixtures" / "reconstruction-plan-synthetic.json")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 7)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "blocked_unsupported")
        self.assertFalse(report["writes_performed"])


if __name__ == "__main__":
    unittest.main()
