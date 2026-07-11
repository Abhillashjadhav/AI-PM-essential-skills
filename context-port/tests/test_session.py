import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_session():
    spec = importlib.util.spec_from_file_location("contextport_session", ROOT / "session.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


session = load_session()


class SessionArtifactTests(unittest.TestCase):
    def make_repository(self, directory):
        repository = Path(directory)
        context_port = repository / "context-port"
        (context_port / "prompts").mkdir(parents=True)
        (context_port / "docs").mkdir()
        (context_port / "tests").mkdir()
        (context_port / "contextport.py").write_text('CLI_VERSION = "0.1.0"\n')
        (context_port / "worker.py").write_text("VALUE = 1\n")
        (context_port / "tests" / "test_synthetic.py").write_text("import unittest\nclass T(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n")
        (context_port / "docs" / "CAPABILITIES.md").write_text("| Capability | Status | Evidence |\n|---|---|---|\n| Writes | `UNSUPPORTED` | synthetic |\n")
        (context_port / "prompts" / "001-bootstrap.md").write_text("# Phase 1\n")
        subprocess.run(["git", "init", "-b", "main"], cwd=repository, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Synthetic"], cwd=repository, check=True)
        subprocess.run(["git", "config", "user.email", "synthetic@example.invalid"], cwd=repository, check=True)
        subprocess.run(["git", "add", "."], cwd=repository, check=True)
        subprocess.run(["git", "commit", "-m", "feat(context-port): bootstrap (#1)"], cwd=repository, check=True, capture_output=True)
        subprocess.run(["git", "switch", "-c", "context-port/002-contextpack-schema"], cwd=repository, check=True, capture_output=True)
        return repository

    def collect(self, repository):
        return session.collect_session(
            repository,
            open_prs=[],
            test_result={"status": "passed", "passed": 1, "command": "synthetic"},
        )

    def test_repeated_runs_are_identical_when_state_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = self.make_repository(directory)
            first = self.collect(repository)
            second = self.collect(repository)
            self.assertEqual(session.render_json(first), session.render_json(second))
            self.assertEqual(session.render_markdown(first), session.render_markdown(second))

    def test_generated_artifacts_are_fresh_on_repeated_run(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = self.make_repository(directory)
            observation = {"status": "passed", "passed": 1, "command": "synthetic"}
            session.generate_session(repository, open_prs=[], test_result=observation)
            first_json = (repository / "context-port" / "SESSION.json").read_text()
            first_markdown = (repository / "context-port" / "SESSION.md").read_text()
            reports = repository / "context-port" / "reports"
            reports.mkdir()
            (reports / "RELEASE_READINESS.json").write_text("{}\n")
            (reports / "RELEASE_READINESS.md").write_text("# Synthetic report\n")
            fresh, _ = session.generate_session(
                repository, check=True, open_prs=[], test_result=observation
            )
            self.assertTrue(fresh)
            self.assertEqual(first_json, (repository / "context-port" / "SESSION.json").read_text())
            self.assertEqual(first_markdown, (repository / "context-port" / "SESSION.md").read_text())

    def test_tracked_generated_artifact_as_first_porcelain_entry_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = self.make_repository(directory)
            observation = {"status": "passed", "passed": 1, "command": "synthetic"}
            session.generate_session(repository, open_prs=[], test_result=observation)
            subprocess.run(["git", "add", "context-port/SESSION.json", "context-port/SESSION.md"], cwd=repository, check=True)
            subprocess.run(["git", "commit", "-m", "docs: add session"], cwd=repository, check=True, capture_output=True)
            (repository / "context-port" / "SESSION.json").write_text("{}\n")
            self.assertTrue(session._worktree_clean(repository))

    def test_repository_branch_and_main_changes_update_session(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = self.make_repository(directory)
            first = self.collect(repository)
            subprocess.run(["git", "switch", "main"], cwd=repository, check=True, capture_output=True)
            (repository / "context-port" / "prompts" / "002-contextpack-schema.md").write_text("# Phase 2\n")
            subprocess.run(["git", "add", "."], cwd=repository, check=True)
            subprocess.run(["git", "commit", "-m", "feat(context-port): phase two (#2)"], cwd=repository, check=True, capture_output=True)
            subprocess.run(["git", "switch", "-c", "context-port/003-safe-export-inspection"], cwd=repository, check=True, capture_output=True)
            second = self.collect(repository)
            self.assertNotEqual(first["latest_merged_commit"], second["latest_merged_commit"])
            self.assertNotEqual(first["current_branch"], second["current_branch"])
            self.assertEqual([item["number"] for item in second["completed_phases"]], [1, 2])
            self.assertEqual(second["current_phase"]["number"], 3)

    def test_json_and_markdown_include_required_gates_and_unknown_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            state = self.collect(self.make_repository(directory))
            rendered = session.render_markdown(state)
            self.assertEqual(state["coverage"]["line_coverage"], "UNKNOWN")
            self.assertIn("Real Claude ZIP", rendered)
            self.assertIn("Browser/write", rendered)
            self.assertIn("Writes", state["known_unsupported_capabilities"])

    def test_public_schema_matches_session_version(self):
        schema = json.loads((ROOT / "schemas" / "session-0.1.schema.json").read_text())
        self.assertEqual(schema["properties"]["session_version"]["const"], session.SESSION_VERSION)


if __name__ == "__main__":
    unittest.main()
