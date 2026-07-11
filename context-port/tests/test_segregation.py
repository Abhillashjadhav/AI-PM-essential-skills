import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


contextport = load_module("contextport_for_segregation", ROOT / "contextport.py")
segregation = load_module("segregation", ROOT / "segregation.py")


class SegregationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads((ROOT / "fixtures" / "segregation-contextpack.json").read_text())
        cls.valid_mappings = json.loads((ROOT / "fixtures" / "project-mappings-valid.json").read_text())
        cls.ambiguous_mappings = json.loads(
            (ROOT / "fixtures" / "project-mappings-ambiguous.json").read_text()
        )

    def segregate(self, document=None, mappings=None):
        return segregation.segregate(
            document if document is not None else self.document,
            mappings,
            validator=contextport.validate,
        )

    def test_projects_duplicate_titles_and_ungrouped_stay_separate(self):
        plan = self.segregate(mappings=self.valid_mappings)
        self.assertEqual(plan["status"], "ready")
        self.assertEqual([group["group_kind"] for group in plan["groups"]], ["project", "project", "ungrouped"])
        self.assertEqual(plan["groups"][0]["title"], plan["groups"][1]["title"])
        self.assertNotEqual(plan["groups"][0]["project_id"], plan["groups"][1]["project_id"])
        self.assertEqual(plan["groups"][2]["conversations"][0]["conversation_id"], "conversation-u")

    def test_every_conversation_appears_exactly_once(self):
        plan = self.segregate()
        ids = [item["conversation_id"] for item in plan["membership"]]
        self.assertEqual(sorted(ids), ["conversation-a", "conversation-b", "conversation-u"])
        self.assertEqual(len(ids), len(set(ids)))

    def test_message_membership_never_crosses_conversations(self):
        plan = self.segregate()
        entries = {
            conversation["conversation_id"]: conversation["message_ids"]
            for group in plan["groups"]
            for conversation in group["conversations"]
        }
        self.assertEqual(entries["conversation-a"], ["message-a"])
        self.assertEqual(entries["conversation-b"], ["message-b"])
        self.assertEqual(entries["conversation-u"], ["message-u"])

    def test_plan_is_deterministic_and_emits_no_content(self):
        first = self.segregate(mappings=self.valid_mappings)
        second = self.segregate(mappings=self.valid_mappings)
        self.assertEqual(first, second)
        encoded = json.dumps(first, sort_keys=True)
        self.assertFalse(first["content_emitted"])
        self.assertNotIn("Synthetic inert content", encoded)

    def test_ambiguous_mapping_returns_decision_artifact_without_plan(self):
        result = self.segregate(mappings=self.ambiguous_mappings)
        self.assertEqual(result["status"], "decision_required")
        self.assertFalse(result["plan_emitted"])
        self.assertEqual(result["ambiguities"][0]["destination_container_ids"], ["destination-a", "destination-c"])
        self.assertNotIn("groups", result)

    def test_unknown_mapping_source_fails_closed(self):
        mappings = {
            "mapping_version": "0.1",
            "project_mappings": [
                {"source_project_id": "missing-project", "destination_container_id": "destination-a"}
            ],
        }
        with self.assertRaisesRegex(segregation.SegregationError, "unknown source project"):
            self.segregate(mappings=mappings)

    def test_invalid_contextpack_fails_before_segregation(self):
        document = copy.deepcopy(self.document)
        document["conversations"][0]["project_id"] = "missing-project"
        with self.assertRaisesRegex(segregation.SegregationError, "ContextPack validation failed"):
            self.segregate(document=document)

    def test_public_schema_matches_engine_version(self):
        schema = json.loads((ROOT / "schemas" / "segregation-plan-0.1.schema.json").read_text())
        self.assertEqual(schema["properties"]["segregation_version"]["const"], segregation.SEGREGATION_VERSION)
        self.assertEqual(schema["properties"]["status"]["enum"], ["ready", "decision_required"])

    def test_cli_ready_and_decision_exit_codes(self):
        base = [
            sys.executable,
            str(ROOT / "contextport.py"),
            "segregate",
            str(ROOT / "fixtures" / "segregation-contextpack.json"),
            "--mappings",
        ]
        ready = subprocess.run(
            [*base, str(ROOT / "fixtures" / "project-mappings-valid.json")],
            check=False,
            capture_output=True,
            text=True,
        )
        ambiguous = subprocess.run(
            [*base, str(ROOT / "fixtures" / "project-mappings-ambiguous.json")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(ready.returncode, 0)
        self.assertEqual(json.loads(ready.stdout)["status"], "ready")
        self.assertEqual(ambiguous.returncode, 3)
        self.assertEqual(json.loads(ambiguous.stdout)["status"], "decision_required")


if __name__ == "__main__":
    unittest.main()
