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


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


contextport = load("contextport")
sync = load("sync")


class SyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous = json.loads((ROOT / "fixtures" / "segregation-contextpack.json").read_text())

    def current(self):
        document = copy.deepcopy(self.previous)
        document["manifest"]["source"]["artifact_sha256"] = "d" * 64
        return document

    def plan(self, current=None, peer=None):
        return sync.plan_sync(self.previous, current or self.current(), peer, validator=contextport.validate)

    def test_unchanged_inventory_has_no_changes(self):
        plan = sync.plan_sync(self.previous, self.previous, validator=contextport.validate)
        self.assertEqual(plan["changes"], [])

    def test_detects_rename_move_reorder_edit_append_and_delete(self):
        current = self.current()
        current["projects"][0]["title"] = "Renamed Synthetic Project"
        current["conversations"][0]["project_id"] = "project-b"
        current["conversations"][1]["ordinal"] = 1
        current["messages"][0]["role"] = "assistant"
        current["messages"].pop(1)
        added = copy.deepcopy(current["messages"][0])
        added.update({"id": "message-new", "source_ref": "source-message-new", "conversation_id": "conversation-b", "ordinal": 2})
        current["messages"].append(added)
        current["dispositions"].append(
            {"source_ref": "source-message-new", "item_type": "message", "status": "copied"}
        )
        kinds = {item["kind"] for item in self.plan(current)["changes"]}
        self.assertTrue({"rename", "move", "reorder", "edit", "append", "delete"}.issubset(kinds))

    def test_deletion_creates_tombstone_and_never_applies(self):
        current = self.current()
        current["messages"].pop()
        plan = self.plan(current)
        self.assertEqual(plan["tombstones"][0]["item_id"], "message-u")
        self.assertFalse(plan["automatic_apply_performed"])

    def test_peer_divergence_creates_human_conflict(self):
        old = sync._inventory(self.previous)[("project", "project-a")]["sha256"]
        current = self.current()
        current["projects"][0]["title"] = "Source Rename"
        peer = {"items": [{"item_type": "project", "item_id": "project-a", "base_sha256": old, "current_sha256": "e" * 64}]}
        plan = self.plan(current, peer)
        self.assertEqual(plan["status"], "conflict")
        self.assertEqual(plan["conflicts"][0]["resolution"], "human_required")
        self.assertFalse(plan["automatic_conflict_resolution"])

    def test_plan_is_deterministic_and_replayable(self):
        self.assertEqual(self.plan(), self.plan())

    def test_invalid_contextpack_fails_closed(self):
        current = self.current()
        current["conversations"][0]["project_id"] = "missing"
        with self.assertRaisesRegex(sync.SyncError, "validation failed"):
            self.plan(current)

    def test_public_schema_matches_engine_version(self):
        schema = json.loads((ROOT / "schemas" / "sync-plan-0.1.schema.json").read_text())
        self.assertEqual(schema["properties"]["sync_version"]["const"], sync.SYNC_VERSION)
        self.assertFalse(schema["properties"]["automatic_apply_performed"]["const"])

    def test_cli_ready_exit_code(self):
        current = self.current()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "current.json"
            path.write_text(json.dumps(current))
            result = subprocess.run(
                [sys.executable, str(ROOT / "contextport.py"), "sync-plan", str(ROOT / "fixtures" / "segregation-contextpack.json"), str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertFalse(json.loads(result.stdout)["automatic_apply_performed"])


if __name__ == "__main__":
    unittest.main()
