"""Local persistence: migrations with backup, permissions, blob integrity,
leases and guarded job transitions."""

import os
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import ROOT  # noqa: F401
from model_router import store as store_module
from model_router.contracts import InvalidTransition, JobState
from model_router.store import StaleState, Store, StoreError, default_data_dir


class StoreBasics(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name) / "data"
        self.store = Store(self.dir)

    def tearDown(self):
        self.store.close()
        self._tmp.cleanup()

    def test_private_permissions(self):
        self.assertEqual(stat.S_IMODE(self.dir.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.store.db_path.stat().st_mode), 0o600)
        ref = self.store.write_blob("résumé text")
        blob = self.dir / "blobs" / ref[:2] / ref
        self.assertEqual(stat.S_IMODE(blob.stat().st_mode), 0o600)

    def test_blob_integrity_detected(self):
        ref = self.store.write_blob("original")
        path = self.dir / "blobs" / ref[:2] / ref
        path.chmod(0o600)
        path.write_text("tampered")
        with self.assertRaises(StoreError):
            self.store.read_blob(ref)

    def test_migration_backup_and_failure_keeps_data(self):
        self.store.execute("INSERT INTO meta(key, value) VALUES ('probe', 'kept')")
        self.store.close()
        extra = Path(self._tmp.name) / "migrations"
        extra.mkdir()
        (extra / "0001_initial.sql").write_text((store_module.MIGRATIONS_DIR / "0001_initial.sql").read_text())
        (extra / "0002_broken.sql").write_text("CREATE TABLE broken (;\n")
        with mock.patch.object(store_module, "MIGRATIONS_DIR", extra):
            with self.assertRaises(StoreError):
                Store(self.dir)
        backups = list((self.dir / "backups").glob("pre-migration-1-to-2-*.sqlite3"))
        self.assertEqual(len(backups), 1)
        with sqlite3.connect(backups[0]) as conn:
            self.assertEqual(conn.execute("SELECT value FROM meta WHERE key='probe'").fetchone()[0], "kept")
        self.store = Store(self.dir)
        self.assertEqual(self.store.schema_version(), 1)
        self.assertEqual(self.store.one("SELECT value FROM meta WHERE key='probe'")["value"], "kept")

    def test_integrity_check_clean(self):
        self.assertEqual(self.store.integrity_check(), [])

    def test_guarded_transitions_and_cas(self):
        now = "2026-09-25T00:00:00Z"
        self.store.execute("INSERT INTO projects(id, name, root, created_at) VALUES ('p','P','/tmp',?)", (now,))
        self.store.execute("INSERT INTO threads(id, project_id, kind, status, created_at, updated_at) VALUES ('t','p','ordinary','active',?,?)", (now, now))
        self.store.execute("INSERT INTO jobs(id, logical_key, thread_id, request_id, kind, state, route_attempt_id, created_at, updated_at) "
                           "VALUES ('j','k','t','r','user_turn','ROUTING','a1',?,?)", (now, now))
        with self.assertRaises(StaleState):
            self.store.transition_job("j", JobState.SELECTED, route_attempt_id="stale")
        with self.assertRaises(InvalidTransition):
            self.store.transition_job("j", JobState.DISPATCHING)
        self.store.transition_job("j", JobState.SELECTED, route_attempt_id="a1")
        with self.assertRaises(StaleState):
            self.store.transition_job("j", JobState.READY, expected=JobState.ROUTING, eligibility_passed=True)
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.execute("INSERT INTO jobs(id, logical_key, thread_id, request_id, kind, state, created_at, updated_at) "
                               "VALUES ('j2','k','t','r','user_turn','DRAFT',?,?)", (now, now))

    def test_leases(self):
        self.assertTrue(self.store.acquire_lease("dispatch", f"pid{os.getpid()}:a", 60))
        self.assertFalse(self.store.acquire_lease("dispatch", f"pid{os.getpid()}:b", 60))
        self.store.release_lease("dispatch", f"pid{os.getpid()}:a")
        self.assertTrue(self.store.acquire_lease("dispatch", f"pid{os.getpid()}:b", 60))

    def test_default_data_dir_override(self):
        with mock.patch.dict(os.environ, {"MODEL_ROUTER_DATA_DIR": "/tmp/x-router"}):
            self.assertEqual(default_data_dir(), Path("/tmp/x-router"))
        with mock.patch.dict(os.environ, {}, clear=False), mock.patch.object(store_module.sys, "platform", "darwin"):
            os.environ.pop("MODEL_ROUTER_DATA_DIR", None)
            self.assertTrue(str(default_data_dir()).endswith("Library/Application Support/AI-PM-Model-Router"))


if __name__ == "__main__":
    unittest.main()
