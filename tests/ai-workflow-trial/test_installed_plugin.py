"""Offline copied-plugin checks, not native Claude Code installation or invocation."""
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
END = "2026-09-08T00:00:00Z"
LABOR = ("draft_minutes", "review_minutes", "rework_minutes", "followup_minutes")
COLUMNS = ("unit_id", "actual_arm", "status", "success", "observed_through", *LABOR)


def fingerprint(folder):
    return {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in folder.rglob("*") if path.is_file()}


class CopiedPluginTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="comparison copied plugin ")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        self.entry = next(p for p in marketplace["plugins"] if p["name"] == "pm-tactical")
        self.plugin = self.folder / "installed cache" / "pm-tactical"
        shutil.copytree(ROOT / self.entry["source"], self.plugin)
        self.skill = self.plugin / "skills/ai-workflow-trial"
        self.workspace = self.folder / "unrelated customer project" / "comparison outputs"
        self.workspace.mkdir(parents=True)
        self.before = fingerprint(self.plugin)
        # The subprocess has no inherited credentials, Python path or account state.
        self.environment = {"PATH": os.defpath, "LANG": "C.UTF-8",
                            "PYTHONDONTWRITEBYTECODE": "1"}

    def run_python(self, arguments, expected=0):
        result = subprocess.run([sys.executable, "-I", *arguments],
                                cwd=self.workspace, env=self.environment,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        return result.stdout

    def cli(self, *arguments, expected=0):
        return json.loads(self.run_python([str(self.skill / "trial_kit.py"),
                                          *map(str, arguments), "--format", "json"], expected))

    def make_plan(self):
        path = self.workspace / "plan.json"
        value = self.cli("plan", "--design", self.skill / "examples/design.json",
                         "--units", self.skill / "examples/units.csv", "--out", path)
        return path, value

    def assert_bundle_unchanged(self):
        self.assertEqual(fingerprint(self.plugin), self.before)

    def test_catalog_discovery_and_bundled_links(self):
        manifest = json.loads((self.plugin / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(manifest["name"], self.entry["name"])
        metadata = (self.skill / "SKILL.md").read_text().split("---", 2)[1]
        name = re.search(r"^name:\s*(\S+)$", metadata, re.M).group(1)
        self.assertEqual(f"/{manifest['name']}:{name}", "/pm-tactical:ai-workflow-comparison")
        self.assertNotEqual(name, self.skill.name)  # documented host name override
        self.assertNotRegex(metadata, r"(?m)^allowed-tools:")
        markdown = [self.plugin / "README.md", *self.skill.rglob("*.md")]
        for source in markdown:
            for raw in re.findall(r"(?<!!)\[[^]]*\]\(([^)]+)\)", source.read_text()):
                target = urlsplit(raw.strip().strip("<>"))
                if target.scheme or target.netloc:
                    continue
                destination = (source.parent / unquote(target.path)).resolve()
                with self.subTest(source=source.relative_to(self.plugin), link=raw):
                    self.assertTrue(destination.is_relative_to(self.plugin))
                    self.assertTrue(destination.exists())
        for relative in ("trial_kit.py", "templates/design.json", "templates/units.csv",
                         "templates/effort-log.csv", "examples/collection-plan-completed.md",
                         "references/source-notes.md", "tools/run_uat.py"):
            self.assertTrue((self.skill / relative).is_file(), relative)
        self.assert_bundle_unchanged()

    def test_installed_markdown_recipes_from_unrelated_cwd_with_spaces(self):
        text = (self.skill / "SKILL.md").read_text()
        recipes = [line for line in text.splitlines()
                   if line.startswith('python3 "${CLAUDE_SKILL_DIR}/trial_kit.py"')]
        self.assertEqual(len(recipes), 3)
        shutil.copy(self.skill / "examples/design.json", self.workspace / "design.json")
        shutil.copy(self.skill / "examples/units.csv", self.workspace / "units.csv")
        def run_recipe(index):
            substituted = recipes[index].replace("${CLAUDE_SKILL_DIR}", str(self.skill))
            substituted = substituted.replace("/absolute/path/to/comparison", str(self.workspace))
            substituted = substituted.replace("YYYY-MM-DDTHH:MM:SSZ", END)
            return self.run_python(shlex.split(substituted)[1:])
        self.assertIn("AI WORKFLOW COMPARISON PLAN", run_recipe(0))
        plan = json.loads((self.workspace / "plan.json").read_text())
        self.assertIn("trial_id", plan["design"])  # compatible JSON key
        self.assertIn("BLANK measurement template", run_recipe(1))
        with (self.workspace / "results.csv").open(newline="") as source:
            rows = list(csv.DictReader(source))
        self.assertEqual({row["unit_id"] for row in rows},
                         {a["unit_id"] for a in plan["assignments"]})
        self.assertTrue(all(row[field] == "" for row in rows
                            for field in ("actual_arm", "status", "success", *LABOR)))
        blocked = self.cli("audit", "--plan", self.workspace / "plan.json",
                           "--results", self.workspace / "results.csv", "--as-of", END,
                           expected=2)
        self.assertEqual(blocked["status"], "BLOCKED")
        shutil.copy(self.skill / "examples/results_fast_draft.csv", self.workspace / "results.csv")
        self.assertIn("Accounted: 32/32", run_recipe(2))
        version = self.run_python([str(self.skill / "trial_kit.py"), "--version"])
        self.assertTrue(version.startswith("ai-workflow-comparison "))
        self.assert_bundle_unchanged()

    def test_copied_synthetic_scenarios_and_collection_blocks(self):
        path, _ = self.make_plan()
        for name, successes, minutes, ratio in (("fast_draft", 10, 400, 1.5),
                                               ("favorable", 15, 160, 5.625),
                                               ("ratio_tradeoff", 10, 80, 7.5)):
            with self.subTest(scenario=name):
                report = self.cli("audit", "--plan", path, "--results",
                                  self.skill / f"examples/results_{name}.csv", "--as-of", END)
                standard, ai = (report["by_assignment"][arm]
                                for arm in ("standard_workflow", "ai_workflow"))
                self.assertEqual((report["accounted_units"], report["assigned_units"]), (32, 32))
                self.assertEqual((standard["successes"], standard["total_measured_human_minutes"]),
                                 (14, 320))
                self.assertEqual((ai["successes"], ai["total_measured_human_minutes"],
                                  ai["successful_outcomes_per_measured_human_hour"]),
                                 (successes, minutes, ratio))
                self.assertEqual((ai["assigned_units"], ai["unfinished"], ai["assignment_deviations"]),
                                 (16, 1, 1))
        gap = self.cli("audit", "--plan", path, "--results",
                       self.skill / "examples/results_gap.csv", "--as-of", END, expected=2)
        self.assertEqual(gap["reason"], "missing_assigned_units")
        immature = self.cli("audit", "--plan", path, "--results",
                            self.skill / "examples/results_fast_draft.csv", "--as-of",
                            "2026-09-07T00:00:00Z", expected=2)
        self.assertEqual(immature["reason"], "immature_window")
        frozen = path.read_bytes()
        duplicate = self.cli("plan", "--design", self.skill / "examples/design.json",
                             "--units", self.skill / "examples/units.csv", "--out", path, expected=2)
        self.assertEqual(duplicate["reason"], "output_exists")
        self.assertEqual(path.read_bytes(), frozen)
        placeholder = self.cli("plan", "--design", self.skill / "templates/design.json",
                               "--units", self.skill / "examples/units.csv", "--out",
                               self.workspace / "unresolved.json", expected=2)
        self.assertEqual(placeholder["status"], "BLOCKED")
        self.assertFalse((self.workspace / "unresolved.json").exists())
        self.assert_bundle_unchanged()

    def test_copied_runtime_supports_custom_units_and_retains_unfinished_deviations(self):
        design = json.loads((self.skill / "examples/design.json").read_text())
        design.update(trial_id="synthetic-handoff-comparison", outcome="Handoff accepted by cutoff")
        design_path, units_path = self.workspace / "design.json", self.workspace / "units.csv"
        design_path.write_text(json.dumps(design))
        units_path.write_text("unit_id,stratum\nA,small\nB,small\nC,large\nD,large\n")
        plan_path = self.workspace / "plan.json"
        plan = self.cli("plan", "--design", design_path, "--units", units_path, "--out", plan_path)
        results = self.workspace / "observations.csv"
        with results.open("w", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=COLUMNS)
            writer.writeheader()
            for assignment in plan["assignments"]:
                writer.writerow({"unit_id": assignment["unit_id"], "actual_arm": "mixed",
                                 "status": "unfinished", "success": "no", "observed_through": END,
                                 **dict(zip(LABOR, (1, 2, 3, 4)))})
        report = self.cli("audit", "--plan", plan_path, "--results", results, "--as-of", END)
        self.assertEqual((report["assigned_units"], report["accounted_units"]), (4, 4))
        for group in report["by_assignment"].values():
            self.assertEqual((group["assigned_units"], group["unfinished"], group["successes"],
                              group["assignment_deviations"], group["total_measured_human_minutes"]),
                             (2, 2, 0, 2, 20))
        self.assert_bundle_unchanged()

    def test_copied_uat_and_walkthrough_have_no_repository_dependency(self):
        uat = self.run_python([str(self.skill / "tools/run_uat.py")])
        self.assertIn("UAT PASS | 9 checks", uat)
        self.assertEqual(sum(line.startswith("PASS | ") for line in uat.splitlines()), 9)
        demo = self.run_python([str(self.skill / "demo/walkthrough.py"), "--pause-seconds", "0"])
        self.assertIn("SYNTHETIC teaching data", demo)
        self.assertIn("BLOCKED [missing_assigned_units]", demo)
        self.assertIn("Standard 14; AI 10", demo)
        self.assert_bundle_unchanged()


if __name__ == "__main__":
    unittest.main()
