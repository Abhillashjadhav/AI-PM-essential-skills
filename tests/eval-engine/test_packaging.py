from __future__ import annotations

import json
import sys
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "pm-verifier"
HARNESS = PACKAGE_ROOT / "skills" / "eval-engine" / "harness"
sys.path.insert(0, str(HARNESS))

from pm_verifier import __version__  # noqa: E402
from pm_verifier.cli import build_parser  # noqa: E402


class PackagingContractTest(unittest.TestCase):
    def test_package_and_console_versions_match(self) -> None:
        metadata = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(metadata["project"]["version"], __version__)
        self.assertEqual(
            metadata["project"]["scripts"]["pm-verifier"],
            "pm_verifier.cli:main",
        )

    def test_public_cli_contains_the_complete_pm_loop(self) -> None:
        parser = build_parser()
        subparser_action = next(
            action for action in parser._actions if action.dest == "command"
        )
        commands = set(subparser_action.choices)
        self.assertTrue(
            {"validate", "execute", "run", "inspect", "report", "calibrate"}
            <= commands
        )

    def test_versioned_schemas_are_valid_json(self) -> None:
        schema_root = HARNESS / "pm_verifier" / "schemas"
        suite = json.loads((schema_root / "suite.schema.json").read_text(encoding="utf-8"))
        result = json.loads((schema_root / "result.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(suite["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(result["properties"]["schema_version"]["const"], "1.0")


if __name__ == "__main__":
    unittest.main()
