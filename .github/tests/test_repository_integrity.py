import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / ".." / "scripts" / "check_repository_integrity.py"
SPEC = importlib.util.spec_from_file_location("check_repository_integrity", SCRIPT)
integrity = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(integrity)


class RepositoryIntegrityTests(unittest.TestCase):
    def test_declared_plugin_directories_are_valid(self):
        failures, count = integrity.validate_plugin_directories()
        self.assertEqual(failures, [])
        self.assertEqual(count, 4)

    def test_portfolio_documents_are_in_link_check_scope(self):
        documents = integrity.markdown_paths()
        self.assertIn(integrity.ROOT / "docs" / "PORTFOLIO_MAP.md", documents)
        self.assertFalse(any(".agents" in path.parts for path in documents))


if __name__ == "__main__":
    unittest.main()
