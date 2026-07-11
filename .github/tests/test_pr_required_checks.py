import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "pr_required_checks.py"
SPEC = importlib.util.spec_from_file_location("pr_required_checks", SCRIPT)
checks = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(checks)


class RequiredCheckTests(unittest.TestCase):
    def test_privacy_check_detects_high_signal_secrets_and_private_files(self):
        findings = checks.privacy_findings(
            ["context-port/session.json"],
            ["token = 'ghp_abcdefghijklmnopqrstuvwxyz123456'"],
        )
        self.assertTrue(any("private filename" in finding for finding in findings))
        self.assertTrue(any("GitHub token" in finding for finding in findings))

    def test_privacy_check_allows_placeholders(self):
        findings = checks.privacy_findings(
            ["context-port/fixtures/synthetic-export.json"],
            ["TOKEN=placeholder", "CLAUDESECRET is optional"],
        )
        self.assertEqual(findings, [])

    def test_existing_skill_impact_uses_base_roots(self):
        roots = {"context-auditor", "plugins/example/skills/demo"}
        paths = ["context-auditor/SKILL.md", "context-port/README.md"]
        self.assertEqual(checks.impacted_skills(paths, roots), ["context-auditor"])

    def test_syntax_check_does_not_write_bytecode(self):
        before = set(SCRIPT.parent.glob("__pycache__/*"))
        self.assertEqual(checks.syntax_errors([str(SCRIPT)]), [])
        after = set(SCRIPT.parent.glob("__pycache__/*"))
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
