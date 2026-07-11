import copy
import importlib.util
import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_readiness():
    spec = importlib.util.spec_from_file_location("contextport_readiness", ROOT / "readiness.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


readiness = load_readiness()


def evidence():
    return {
        "readiness_version": "0.1",
        "audited_revision": "a" * 40,
        "latest_merged_commit": "b" * 40,
        "current_branch": "context-port/015-release-readiness",
        "versions": {"cli": "0.1.0", "package": "0.1.0", "build_backend": "0.1.0"},
        "versions_consistent": True,
        "session_fresh": True,
        "tests": {"status": "passed", "passed": 99},
        "coverage": {"line_coverage": "UNKNOWN", "reason": "No instrumentation."},
        "schemas": {"status": "passed", "schemas": 9},
        "package": {"wheel_reproducible": True, "sdist_reproducible": True},
        "demo": {"reconciliation_differences": 0, "writes_performed": False, "network_calls_performed": False, "browser_automation_performed": False},
        "branch_commits": [],
        "authorship_pass": True,
        "changed_paths": ["context-port/readiness.py"],
        "approved_public_scope": True,
        "approved_infrastructure_paths": [],
        "private_export_artifacts_tracked": False,
        "working_tree_clean_except_generated_reports": True,
        "production_dependencies": [],
        "private_runtime_dependency": False,
        "human_gates": {"public_license_selected": False, "release_publication_approved": False, "real_claude_zip_access_approved": False, "browser_or_assistant_write_approved": False},
        "known_unsupported_capabilities": ["Writes"],
    }


class ReleaseReadinessTests(unittest.TestCase):
    def test_passing_automation_stops_at_human_release_gates(self):
        report = readiness.evaluate_readiness(evidence())
        self.assertEqual(report["synthetic_mvp_status"], "ready")
        self.assertEqual(report["public_release_status"], "blocked_human_decisions")
        self.assertEqual([item["id"] for item in report["release_blockers"]], ["public_license", "release_publication"])
        self.assertFalse(report["publication_performed"])

    def test_failed_automated_evidence_prevents_readiness(self):
        value = evidence()
        value["package"]["wheel_reproducible"] = False
        report = readiness.evaluate_readiness(value)
        self.assertEqual(report["synthetic_mvp_status"], "not_ready")
        self.assertIn("wheel_reproducible", report["failed_automated_checks"])

    def test_evaluation_is_deterministic_and_digest_bound(self):
        first = readiness.evaluate_readiness(evidence())
        second = readiness.evaluate_readiness(evidence())
        self.assertEqual(first, second)
        changed = evidence()
        changed["tests"]["passed"] = 100
        self.assertNotEqual(first["readiness_report_sha256"], readiness.evaluate_readiness(changed)["readiness_report_sha256"])
        schema = json.loads((ROOT / "schemas" / "release-readiness-0.1.schema.json").read_text())
        self.assertEqual(schema["properties"]["readiness_version"]["const"], readiness.READINESS_VERSION)

    def test_markdown_preserves_truthful_boundaries(self):
        rendered = readiness.render_markdown(readiness.evaluate_readiness(evidence()))
        self.assertIn("Real Claude export compatibility remains `UNKNOWN`", rendered)
        self.assertIn("ChatGPT reconstruction writes remain `UNSUPPORTED`", rendered)
        self.assertIn("Release publication performed: `false`", rendered)

    def test_audited_revision_ignores_only_generated_artifact_commits(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "context-port" / "reports").mkdir(parents=True)
            subprocess.run(["git", "init", "-b", "main"], cwd=repository, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Synthetic"], cwd=repository, check=True)
            subprocess.run(["git", "config", "user.email", "synthetic@example.invalid"], cwd=repository, check=True)
            (repository / "context-port" / "readiness.py").write_text("VALUE = 1\n")
            subprocess.run(["git", "add", "."], cwd=repository, check=True)
            subprocess.run(["git", "commit", "-m", "implementation"], cwd=repository, check=True, capture_output=True)
            implementation = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repository, check=True, capture_output=True, text=True).stdout.strip()
            (repository / "context-port" / "SESSION.md").write_text("generated\n")
            (repository / "context-port" / "reports" / "RELEASE_READINESS.json").write_text("{}\n")
            subprocess.run(["git", "add", "."], cwd=repository, check=True)
            subprocess.run(["git", "commit", "-m", "generated artifacts"], cwd=repository, check=True, capture_output=True)
            self.assertEqual(readiness._audited_revision(repository), implementation)


if __name__ == "__main__":
    unittest.main()
