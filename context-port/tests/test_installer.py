import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_installer():
    spec = importlib.util.spec_from_file_location("contextport_installer", ROOT / "install.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


installer = load_installer()


class InstallerTests(unittest.TestCase):
    def test_dry_run_is_default_and_performs_no_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "contextport"
            result = subprocess.run(
                [sys.executable, str(ROOT / "install.py"), str(target)],
                check=False,
                capture_output=True,
                text=True,
            )
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(report["status"], "ready")
            self.assertFalse(report["writes_performed"])
            self.assertFalse(target.exists())

    def test_existing_target_is_blocked_without_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing"
            target.mkdir()
            marker = target / "keep.txt"
            marker.write_text("keep")
            dry_run = subprocess.run(
                [sys.executable, str(ROOT / "install.py"), str(target)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(dry_run.returncode, 3)
            self.assertEqual(json.loads(dry_run.stdout)["status"], "blocked_existing_target")
            install = subprocess.run(
                [sys.executable, str(ROOT / "install.py"), str(target), "--install"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(install.returncode, 2)
            self.assertEqual(json.loads(install.stdout)["status"], "install_failed")
            self.assertEqual(marker.read_text(), "keep")

    def test_explicit_install_is_offline_and_observably_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "contextport"
            report = installer.install(target)
            self.assertEqual(report["status"], "installed_verified")
            self.assertTrue(report["writes_performed"])
            self.assertFalse(report["network_allowed"])
            self.assertEqual(report["verification"]["version"], "ContextPort 0.1.0")
            self.assertFalse(report["verification"]["network_required"])
            self.assertFalse(report["verification"]["destination_writes_supported"])
            self.assertTrue(Path(report["command"]).is_file())

    def test_target_appearance_race_is_blocked_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "raced"
            original_plan = installer.plan_install

            def raced_plan(path):
                plan = original_plan(path)
                target.mkdir()
                (target / "other-process.txt").write_text("untouched")
                return plan

            with mock.patch.object(installer, "plan_install", side_effect=raced_plan):
                with self.assertRaisesRegex(installer.InstallError, "appeared"):
                    installer.install(target)
            self.assertEqual((target / "other-process.txt").read_text(), "untouched")

    def test_partial_failure_is_retained_and_structurally_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "partial"

            class FailingBuilder:
                def __init__(self, **kwargs):
                    pass

                def create(self, path):
                    (Path(path) / "partial-marker.txt").write_text("retained")
                    raise OSError("synthetic venv failure")

            output = StringIO()
            with mock.patch.object(installer.venv, "EnvBuilder", FailingBuilder), redirect_stdout(output):
                code = installer.main([str(target), "--install"])
            report = json.loads(output.getvalue())
            self.assertEqual(code, 2)
            self.assertEqual(report["status"], "install_failed")
            self.assertTrue(report["writes_performed"])
            self.assertTrue(report["partial_target_retained"])
            self.assertEqual((target / "partial-marker.txt").read_text(), "retained")

    def test_executable_paths_cover_posix_and_windows_layouts(self):
        target = Path("install-root")
        self.assertEqual(installer._executable(target, "contextport", "posix"), target / "bin" / "contextport")
        self.assertEqual(installer._executable(target, "contextport", "nt"), target / "Scripts" / "contextport.exe")


if __name__ == "__main__":
    unittest.main()
