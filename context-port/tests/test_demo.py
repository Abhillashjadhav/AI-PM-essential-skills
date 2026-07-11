import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_demo():
    spec = importlib.util.spec_from_file_location("contextport_demo", ROOT / "demo.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


demo = load_demo()
REVISION = "0" * 40


class SyntheticDemoTests(unittest.TestCase):
    def run_demo(self):
        with mock.patch.object(demo, "_revision", return_value=REVISION):
            return demo.run_demo(ROOT)

    def test_demo_is_deterministic_and_proves_zero_writes(self):
        first = self.run_demo()
        second = self.run_demo()
        self.assertEqual(first, second)
        self.assertFalse(first["writes_performed"])
        self.assertFalse(first["network_calls_performed"])
        self.assertFalse(first["browser_automation_performed"])

    def test_every_pipeline_stage_has_truthful_evidence(self):
        report = self.run_demo()
        stages = {item["stage"]: item for item in report["stages"]}
        self.assertEqual(stages["contextpack_validation"]["errors"], 0)
        self.assertEqual(stages["independent_reconciliation"]["differences"], 0)
        self.assertEqual(stages["chatgpt_capability_assessment"]["status"], "UNSUPPORTED")
        self.assertFalse(stages["chatgpt_capability_assessment"]["writes_performed"])
        self.assertGreater(stages["chatgpt_capability_assessment"]["operations_not_written"], 0)

    def test_real_compatibility_is_not_claimed(self):
        claims = self.run_demo()["claims"]
        self.assertEqual(claims["synthetic_pipeline"], "VERIFIED")
        self.assertEqual(claims["real_claude_export_compatibility"], "UNKNOWN")
        self.assertEqual(claims["chatgpt_reconstruction_writes"], "UNSUPPORTED")

    def test_cli_binds_report_to_exact_checkout_head(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "demo.py")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True)
        self.assertEqual(report["revision"], head.stdout.strip())
        self.assertRegex(report["demo_report_sha256"], r"^[0-9a-f]{64}$")

    def test_evidence_contract_has_digests_inventories_and_dispositions(self):
        report = self.run_demo()
        self.assertRegex(report["source"]["artifact_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(report["source"]["inventory"]["inventory_sha256"], r"^[0-9a-f]{64}$")
        self.assertFalse(report["destination_inventory"]["observed"])
        self.assertEqual(report["destination_inventory"]["status"], "UNSUPPORTED")
        self.assertEqual(len(report["everything_not_copied"]), 8)
        self.assertEqual(report["everything_not_copied"], report["dispositions"]["unsupported"])
        self.assertTrue(all(stage["exit_state"] == "completed" for stage in report["stages"]))
        self.assertTrue(all(stage["exit_code"] == 0 for stage in report["stages"]))


if __name__ == "__main__":
    unittest.main()
