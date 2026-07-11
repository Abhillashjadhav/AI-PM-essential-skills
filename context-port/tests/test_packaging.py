import hashlib
import importlib.util
import tarfile
import tempfile
import tomllib
import unittest
import zipfile
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_backend():
    spec = importlib.util.spec_from_file_location("contextport_build", ROOT / "contextport_build.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


backend = load_backend()


class PackagingTests(unittest.TestCase):
    def test_metadata_has_no_dependencies_and_matches_cli_version(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
        self.assertEqual(project["version"], "0.1.0")
        self.assertEqual(project["dependencies"], [])
        self.assertEqual(project["scripts"]["contextport"], "contextport:main")
        self.assertEqual(tomllib.loads((ROOT / "pyproject.toml").read_text())["build-system"]["requires"], [])

    def test_wheel_is_reproducible_and_contains_runtime_contracts(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = Path(first_dir) / backend.build_wheel(first_dir)
            second = Path(second_dir) / backend.build_wheel(second_dir)
            self.assertEqual(hashlib.sha256(first.read_bytes()).digest(), hashlib.sha256(second.read_bytes()).digest())
            with zipfile.ZipFile(first) as archive:
                names = set(archive.namelist())
                self.assertIn("contextport.py", names)
                self.assertIn("contextport_data/schemas/contextpack-0.1.schema.json", names)
                self.assertIn(f"{backend.DIST_INFO}/entry_points.txt", names)
                self.assertIn(f"{backend.DIST_INFO}/RECORD", names)
                metadata = archive.read(f"{backend.DIST_INFO}/METADATA").decode()
                self.assertIn(f"Summary: {backend.SUMMARY}\n", metadata)
                self.assertIn(f"Author-email: {backend.AUTHOR_NAME} <{backend.AUTHOR_EMAIL}>\n", metadata)
                self.assertIn(f"Project-URL: Repository, {backend.PROJECT_URL}\n", metadata)
                self.assertIn("Description-Content-Type: text/markdown\n", metadata)
                self.assertIn("# ContextPort", metadata)

    def test_sdist_contains_build_runtime_tests_and_docs(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            archive_path = Path(first_dir) / backend.build_sdist(first_dir)
            second = Path(second_dir) / backend.build_sdist(second_dir)
            self.assertEqual(hashlib.sha256(archive_path.read_bytes()).digest(), hashlib.sha256(second.read_bytes()).digest())
            with tarfile.open(archive_path) as archive:
                names = set(archive.getnames())
            prefix = f"contextport-{backend.VERSION}/"
            for required in ("PKG-INFO", "pyproject.toml", "contextport_build.py", "contextport.py", "tests/test_cli.py", "docs/CLI.md"):
                self.assertIn(prefix + required, names)

    def test_wheel_installs_offline_and_console_entry_point_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel_dir = root / "wheel"
            environment = root / "venv"
            wheel_dir.mkdir()
            wheel = wheel_dir / backend.build_wheel(wheel_dir)
            subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(environment)], check=True)
            subprocess.run(
                [sys.executable, "-m", "pip", "--python", str(environment), "install", "--no-deps", "--no-index", str(wheel)],
                check=True,
                capture_output=True,
                text=True,
            )
            executable = environment / "bin" / "contextport"
            result = subprocess.run([str(executable), "--version"], check=False, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "ContextPort 0.1.0\n")


if __name__ == "__main__":
    unittest.main()
