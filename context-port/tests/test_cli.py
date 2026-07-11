import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*arguments):
    return subprocess.run(
        [sys.executable, str(ROOT / "contextport.py"), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


class PublicCLITests(unittest.TestCase):
    def test_version_is_stable_and_printed_to_stdout(self):
        result = run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "ContextPort 0.1.0\n")
        self.assertEqual(result.stderr, "")

    def test_capabilities_are_deterministic_machine_readable_and_offline(self):
        first = run_cli("capabilities")
        second = run_cli("capabilities")
        self.assertEqual(first.returncode, 0)
        self.assertEqual(first.stdout, second.stdout)
        report = json.loads(first.stdout)
        self.assertFalse(report["network_required"])
        self.assertFalse(report["destination_writes_supported"])
        self.assertEqual(report["runtime_dependencies"], [])
        self.assertEqual(sorted(report["commands"]), report["commands"])
        self.assertEqual(sorted(report["exit_codes"].values()), list(range(8)))

    def test_help_lists_every_declared_command(self):
        help_result = run_cli("--help")
        capabilities = json.loads(run_cli("capabilities").stdout)
        self.assertEqual(help_result.returncode, 0)
        for command in capabilities["commands"]:
            self.assertIn(command, help_result.stdout)

    def test_invalid_command_uses_documented_error_channel_and_code(self):
        result = run_cli("does-not-exist")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("invalid choice", result.stderr)


if __name__ == "__main__":
    unittest.main()
