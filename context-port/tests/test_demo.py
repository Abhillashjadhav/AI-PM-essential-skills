import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


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
    def test_demo_is_deterministic_and_proves_zero_writes(self):
        first = demo.run_demo(ROOT, REVISION)
        second = demo.run_demo(ROOT, REVISION)
        self.assertEqual(first, second)
        self.assertFalse(first["writes_performed"])
        self.assertFalse(first["network_calls_performed"])
        self.assertFalse(first["browser_automation_performed"])

    def test_every_pipeline_stage_has_truthful_evidence(self):
        report = demo.run_demo(ROOT, REVISION)
        stages = {item["stage"]: item for item in report["stages"]}
        self.assertEqual(stages["contextpack_validation"]["errors"], 0)
        self.assertEqual(stages["independent_reconciliation"]["differences"], 0)
        self.assertEqual(stages["chatgpt_capability_assessment"]["status"], "UNSUPPORTED")
        self.assertFalse(stages["chatgpt_capability_assessment"]["writes_performed"])
        self.assertGreater(stages["chatgpt_capability_assessment"]["operations_not_written"], 0)

    def test_real_compatibility_is_not_claimed(self):
        claims = demo.run_demo(ROOT, REVISION)["claims"]
        self.assertEqual(claims["synthetic_pipeline"], "VERIFIED")
        self.assertEqual(claims["real_claude_export_compatibility"], "UNKNOWN")
        self.assertEqual(claims["chatgpt_reconstruction_writes"], "UNSUPPORTED")

    def test_cli_accepts_an_explicit_revision_and_emits_json(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "demo.py"), "--revision", REVISION],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertEqual(report["revision"], REVISION)
        self.assertRegex(report["demo_report_sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
