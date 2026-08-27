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
from pm_verifier.reporting import render_inspection, render_markdown  # noqa: E402


PUBLIC_BRAND = "AI Evals for PMs"


class PackagingContractTest(unittest.TestCase):
    def test_package_and_console_versions_match(self) -> None:
        metadata = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(metadata["project"]["version"], __version__)
        self.assertEqual(
            metadata["project"]["scripts"]["pm-verifier"],
            "pm_verifier.cli:main",
        )

    def test_public_brand_and_plugin_versions_match(self) -> None:
        metadata = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        plugin = json.loads(
            (PACKAGE_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        marketplace_entry = next(
            entry for entry in marketplace["plugins"] if entry["name"] == "pm-verifier"
        )

        self.assertEqual(plugin["version"], metadata["project"]["version"])
        self.assertIn(PUBLIC_BRAND, metadata["project"]["description"])
        self.assertIn(PUBLIC_BRAND, plugin["description"])
        self.assertIn(PUBLIC_BRAND, marketplace_entry["description"])
        self.assertIn(PUBLIC_BRAND, build_parser().description)
        self.assertIn(
            PUBLIC_BRAND,
            (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8").splitlines()[0],
        )
        self.assertIn(
            PUBLIC_BRAND,
            (ROOT / "README.md").read_text(encoding="utf-8"),
        )
        self.assertIn(PUBLIC_BRAND, render_markdown({"decision": "BLOCKED"}))
        self.assertIn(
            PUBLIC_BRAND,
            render_inspection({"decision": "BLOCKED", "trials": []}, []),
        )

    def test_public_cli_contains_the_complete_pm_loop(self) -> None:
        parser = build_parser()
        subparser_action = next(
            action for action in parser._actions if action.dest == "command"
        )
        commands = set(subparser_action.choices)
        self.assertTrue(
            {"validate", "execute", "run", "inspect", "report", "calibrate", "fault"}
            <= commands
        )

    def test_versioned_schemas_are_valid_json(self) -> None:
        schema_root = HARNESS / "pm_verifier" / "schemas"
        suite = json.loads((schema_root / "suite.schema.json").read_text(encoding="utf-8"))
        result = json.loads((schema_root / "result.schema.json").read_text(encoding="utf-8"))
        legacy_suite = json.loads(
            (schema_root / "suite-1.0.schema.json").read_text(encoding="utf-8")
        )
        legacy_result = json.loads(
            (schema_root / "result-1.0.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            suite["properties"]["schema_version"]["enum"], ["1.0", "1.1"]
        )
        self.assertEqual(result["properties"]["schema_version"]["const"], "1.1")
        self.assertEqual(legacy_suite["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(legacy_result["properties"]["schema_version"]["const"], "1.0")


if __name__ == "__main__":
    unittest.main()
