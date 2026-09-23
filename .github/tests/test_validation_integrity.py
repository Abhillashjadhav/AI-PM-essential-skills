"""Offline regressions for validator false acceptance; no third-party imports."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


def load_script(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys, "path", [str(path.parent), *sys.path]):
        spec.loader.exec_module(module)
    return module


integrity = load_script("integrity_regression", ROOT / "scripts/check_repository_integrity.py")
checks = load_script("checks_regression", ROOT / ".github/scripts/pr_required_checks.py")


class MarketplaceValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aipm-marketplace-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / ".claude-plugin/marketplace.json"
        self.manifest.parent.mkdir()
        self.entries = []
        for name in integrity.EXPECTED_PLUGINS:
            directory = self.root / name
            (directory / ".claude-plugin").mkdir(parents=True)
            (directory / ".claude-plugin/plugin.json").write_text(
                json.dumps({"name": name}), encoding="utf-8"
            )
            (directory / "skills").mkdir()
            self.entries.append({"name": name, "source": f"./{name}"})

    def validate(self, entries):
        self.manifest.write_text(json.dumps({"plugins": entries}), encoding="utf-8")
        with patch.object(integrity, "ROOT", self.root), patch.object(
            integrity, "MARKETPLACE_PATH", self.manifest
        ):
            return integrity.validate_marketplace()

    def install(self, entries):
        # Same copy operation and destination key as public-smoke.yml.
        with tempfile.TemporaryDirectory(prefix="aipm-install-test-") as destination:
            for entry in entries:
                source = (self.root / entry["source"]).resolve()
                target = Path(destination) / entry["name"]
                shutil.copytree(source, target)
                self.assertTrue((target / ".claude-plugin/plugin.json").is_file())
                self.assertTrue((target / "skills").is_dir())

    def test_unique_marketplace_passes_and_installs(self):
        self.assertEqual(self.validate(self.entries), [])
        self.install(self.entries)

    def test_duplicate_install_collision_is_rejected(self):
        entries = [self.entries[0].copy(), *self.entries]
        with self.assertRaises(FileExistsError):
            self.install(entries)
        self.assertTrue(any("duplicate" in error for error in self.validate(entries)))

    def test_later_valid_entry_cannot_hide_bad_duplicate(self):
        entries = [{**self.entries[0], "source": "./missing-source"}, *self.entries]
        self.assertTrue(any("duplicate" in error for error in self.validate(entries)))


class SkillLintValidationTests(unittest.TestCase):
    VALID_METADATA = {
        "name": "synthetic-skill",
        "description": "Use when testing. Do NOT use for production.",
    }

    def lint(self, metadata=None, parse_error=None):
        # Exercise the complete lint script independently of PyYAML availability.
        # Real PyYAML CLI compatibility is checked separately in evaluation evidence.
        def safe_load(_text):
            if parse_error is not None:
                raise parse_error
            return metadata

        yaml = types.ModuleType("yaml")
        yaml.safe_load = safe_load
        with tempfile.TemporaryDirectory(prefix="aipm-lint-test-") as directory:
            path = Path(directory) / "SKILL.md"
            path.write_text("---\nsynthetic: fixture\n---\n## Limitations\nSynthetic only.\n")
            output = io.StringIO()
            with patch.dict(sys.modules, {"yaml": yaml}), patch.object(
                sys, "argv", [str(ROOT / "tests/lint_skill.py"), str(path)]
            ), contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as result:
                runpy.run_path(str(ROOT / "tests/lint_skill.py"), run_name="__main__")
        return result.exception.code, output.getvalue()

    def test_valid_metadata_passes_every_check(self):
        code, output = self.lint(self.VALID_METADATA)
        self.assertEqual(code, 0, output)
        self.assertNotIn("FAIL", output)

    def test_non_mapping_metadata_fails(self):
        for metadata in ([], ["synthetic"], None, True, 7, "synthetic"):
            with self.subTest(metadata=metadata):
                code, output = self.lint(metadata)
                self.assertNotEqual(code, 0, output)

    def test_non_string_name_or_description_fails(self):
        for field, value in (("name", True), ("name", 7), ("description", True),
                             ("description", 7), ("description", ["Use when", "Do NOT"])):
            with self.subTest(field=field, value=value):
                code, output = self.lint({**self.VALID_METADATA, field: value})
                self.assertNotEqual(code, 0, output)

    def test_parser_failure_and_missing_trigger_still_fail(self):
        code, output = self.lint(parse_error=ValueError("synthetic parse failure"))
        self.assertNotEqual(code, 0, output)
        code, output = self.lint({**self.VALID_METADATA, "description": "Use when testing."})
        self.assertNotEqual(code, 0, output)


class GitPathValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aipm-git-path-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic Review")
        self.git("config", "user.email", "synthetic@example.invalid")
        self.git("config", "core.quotePath", "true")
        self.base = self.commit({"seed.txt": "synthetic\n"})

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.root, check=True, capture_output=True, text=True
        ).stdout.strip()

    def commit(self, files):
        for name, content in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "synthetic fixture")
        return self.git("rev-parse", "HEAD")

    def run_gate(self, head):
        return subprocess.run(
            [sys.executable, str(ROOT / ".github/scripts/pr_required_checks.py"),
             "--base", self.base, "--head", head, "--head-ref", "synthetic-review"],
            cwd=self.root, text=True, capture_output=True,
        )

    def test_valid_quoted_python_paths_pass(self):
        head = self.commit({"café.py": "value = 1\n", "line\nbreak.py": "value = 2\n",
                            "carriage\rreturn.py": "value = 3\n"})
        result = self.run_gate(head)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("3 changed Python path(s)", result.stdout)

    def test_invalid_quoted_python_paths_fail_complete_gate(self):
        for name in ("café.py", "line\nbreak.py", "carriage\rreturn.py"):
            with self.subTest(name=name):
                self.git("reset", "--hard", self.base)
                head = self.commit({name: "def broken(\n"})
                result = self.run_gate(head)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("compilation failed:", result.stderr)

    def test_quoted_private_filename_is_detected(self):
        head = self.commit({"café/session.json": "{}\n"})
        result = self.run_gate(head)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("private filename: café/session.json", result.stderr)

    def test_quoted_base_skill_roots_preserve_impact(self):
        base = self.commit({"café/SKILL.md": "synthetic\n", "line\nbreak/SKILL.md": "synthetic\n",
                            "carriage\rreturn/SKILL.md": "synthetic\n"})
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            roots = checks.existing_skill_roots(base)
        finally:
            os.chdir(previous)
        self.assertEqual(roots, {"café", "line\nbreak", "carriage\rreturn"})
        self.assertEqual(checks.impacted_skills(["café/SKILL.md"], roots), ["café"])


if __name__ == "__main__":
    unittest.main()
