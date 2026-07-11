import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("claude_converter", ROOT / "claude_converter.py")
converter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(converter)
CONTEXT_SPEC = importlib.util.spec_from_file_location("contextport", ROOT / "contextport.py")
contextport = importlib.util.module_from_spec(CONTEXT_SPEC)
assert CONTEXT_SPEC.loader is not None
CONTEXT_SPEC.loader.exec_module(contextport)


class ClaudeConverterTests(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        export = root / "export"
        (export / "projects").mkdir(parents=True)
        (export / "design_chats").mkdir()
        project = {"uuid": "p1", "name": "Exact Project", "prompt_template": "Exact instructions", "docs": []}
        (export / "projects" / "p1.json").write_text(json.dumps(project), encoding="utf-8")
        conversations = [
            {
                "uuid": "c1", "name": "Exact title", "created_at": "t1", "updated_at": "t2",
                "chat_messages": [{
                    "uuid": "m1", "sender": "human", "created_at": "t1", "updated_at": "t2",
                    "parent_message_uuid": "parent", "text": "private synthetic text",
                    "content": [{"type": "text", "text": "private synthetic text"}],
                    "attachments": [{"file_name": "a.txt", "file_type": "text/plain", "extracted_content": "x"}],
                    "files": [],
                }],
            },
            {"uuid": "c2", "name": "Mapped", "project_uuid": "p1", "chat_messages": []},
        ]
        (export / "conversations.json").write_text(json.dumps(conversations), encoding="utf-8")
        (export / "users.json").write_text('[{"uuid":"u1"}]', encoding="utf-8")
        (export / "memories.json").write_text('[{"project_memories":{"p1":"memory"}}]', encoding="utf-8")
        (export / "design_chats" / "d1.json").write_text('{"uuid":"d1","messages":[]}', encoding="utf-8")
        return export

    def test_policy_preserves_explicit_mapping_and_uses_one_unmapped_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            contextpack, _, reconciliation, loss = converter.build_migration(self.fixture(Path(temporary)))
        self.assertEqual(len(contextpack["projects"]), 2)
        self.assertEqual(contextpack["conversations"][0]["project_id"], converter.UNMAPPED_ID)
        self.assertEqual(contextpack["conversations"][1]["project_id"], "p1")
        self.assertEqual(contextpack["conversations"][0]["title"], "Exact title")
        self.assertEqual(contextpack["messages"][0]["id"], "m1")
        self.assertEqual(contextport.validate(contextpack), [])
        self.assertEqual(reconciliation["status"], "clean")
        self.assertTrue(reconciliation["invariants"]["source_snapshot_exact"])
        self.assertEqual(loss["loss_count"], 0)

    def test_repeated_writes_are_byte_identical_and_preserve_extensions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            export = self.fixture(root)
            output = root / "migration"
            first = converter.write_migration(export, output)
            second = converter.write_migration(export, output)
            contextpack = json.loads((output / "contextpack.json").read_text(encoding="utf-8"))
        self.assertEqual(first, second)
        self.assertEqual(set(first), set(converter.OUTPUT_NAMES))
        self.assertEqual(contextpack["source_extensions"]["memories"][0]["project_memories"]["p1"], "memory")
        self.assertEqual(contextpack["source_extensions"]["design_chats"][0]["uuid"], "d1")

    def test_conflicting_explicit_mapping_fails_without_inference(self):
        with tempfile.TemporaryDirectory() as temporary:
            export = self.fixture(Path(temporary))
            conversations = json.loads((export / "conversations.json").read_text(encoding="utf-8"))
            conversations[1]["project"] = {"uuid": "different"}
            (export / "conversations.json").write_text(json.dumps(conversations), encoding="utf-8")
            with self.assertRaisesRegex(converter.ClaudeConversionError, "conflicting"):
                converter.build_migration(export)


if __name__ == "__main__":
    unittest.main()
