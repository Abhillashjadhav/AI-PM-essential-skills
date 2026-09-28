"""Regressions for stale public counts and missing installation entry points."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


def load_script(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys, "path", [str(path.parent), *sys.path]):
        spec.loader.exec_module(module)
    return module


integrity = load_script("public_inventory", ROOT / "scripts/check_repository_integrity.py")
all_skills = load_script("all_skills", ROOT / "scripts/lint_all_skills.py")


class PublicInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / ".claude-plugin/marketplace.json"
        self.manifest.parent.mkdir()
        self.entries = [{"name": "alpha", "source": "./alpha"},
                        {"name": "beta", "source": "./nested/beta"}]
        self.manifest.write_text(json.dumps({"plugins": self.entries}))
        for entry in self.entries:
            directory = self.root / entry["source"]
            directory.mkdir(parents=True)
            (directory / "README.md").write_text("# Plugin\n")
        self.table = ("## Choose the job you need done\n\n"
                      "| **[Alpha](alpha/)** | first |\n"
                      "| **[Beta](nested/beta/)** | second |\n\n## Next\n")
        for name in ("README.md", "CLAUDE.md", "docs/VALIDATION.md"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Catalogue: **2 installable plugins**.\n\n" +
                            (self.table if name == "README.md" else ""))

    def validate(self):
        with patch.object(integrity, "ROOT", self.root), patch.object(
                integrity, "MARKETPLACE_PATH", self.manifest):
            return integrity.validate_public_inventory()

    def test_current_inventory_with_nested_source_passes(self):
        self.assertEqual(self.validate(), [])

    def test_each_stale_count_fails(self):
        for name in ("README.md", "CLAUDE.md", "docs/VALIDATION.md"):
            with self.subTest(name=name):
                path = self.root / name
                original = path.read_text()
                path.write_text(original.replace("2 installable", "1 installable"))
                self.assertTrue(any(name in error for error in self.validate()))
                path.write_text(original)

    def test_missing_count_is_not_silently_skipped(self):
        (self.root / "CLAUDE.md").write_text("# Outdated overview\n")
        self.assertTrue(any("CLAUDE.md" in error for error in self.validate()))

    def test_missing_or_duplicate_table_entry_fails(self):
        path = self.root / "README.md"
        original = path.read_text()
        row = "| **[Beta](nested/beta/)** | second |\n"
        for replacement in ("", row + row):
            with self.subTest(replacement=replacement):
                path.write_text(original.replace(row, replacement))
                self.assertTrue(any("job table" in error for error in self.validate()))

    def test_missing_plugin_readme_fails(self):
        (self.root / "nested/beta/README.md").unlink()
        self.assertTrue(any("beta: missing README" in error for error in self.validate()))

    def test_manifest_count_change_requires_public_update(self):
        self.manifest.write_text(json.dumps({"plugins": self.entries[:1]}))
        self.assertTrue(any("1 installable plugins" in error for error in self.validate()))

    def test_scalar_marketplace_fails_without_crashing(self):
        for value in (True, [], None, 8):
            with self.subTest(value=value):
                self.manifest.write_text(json.dumps(value))
                with patch.object(integrity, "ROOT", self.root), patch.object(
                        integrity, "MARKETPLACE_PATH", self.manifest):
                    self.assertEqual(integrity.validate_marketplace(),
                                     ["marketplace manifest must be an object"])


class AllSkillDiscoveryTests(unittest.TestCase):
    def test_internal_and_quoted_paths_are_included(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", directory], check=True)
            names = (".claude/skills/internal/SKILL.md", "café/SKILL.md",
                     "line\nbreak/SKILL.md", "ordinary/SKILL.md")
            for name in names:
                path = root / name
                path.parent.mkdir(parents=True)
                path.write_text("synthetic\n")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            self.assertEqual(set(all_skills.tracked_skills(root)),
                             {root / name for name in names})


if __name__ == "__main__":
    unittest.main()
