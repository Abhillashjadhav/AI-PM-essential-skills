import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "contextport.py"
VALID_FIXTURE = ROOT / "fixtures" / "contextpack-valid.json"
INVALID_FIXTURE = ROOT / "fixtures" / "contextpack-invalid.json"

SPEC = importlib.util.spec_from_file_location("contextport", MODULE_PATH)
contextport = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(contextport)


class ContextPackValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = json.loads(VALID_FIXTURE.read_text(encoding="utf-8"))

    def test_valid_synthetic_fixture_passes(self):
        self.assertEqual(contextport.validate(self.valid), [])

    def test_invalid_fixture_reports_all_planted_failures(self):
        errors = contextport.validate(json.loads(INVALID_FIXTURE.read_text(encoding="utf-8")))
        joined = "\n".join(errors)
        self.assertIn("artifact_sha256", joined)
        self.assertIn("unresolved reference 'missing-project'", joined)
        self.assertIn("digest does not match exact text", joined)
        self.assertIn("reason: expected non-empty string", joined)
        self.assertIn("missing disposition for 'content_block'", joined)
        self.assertGreaterEqual(len(errors), 6)

    def test_unknown_block_requires_reason(self):
        document = copy.deepcopy(self.valid)
        del document["messages"][1]["content"][0]["reason"]
        self.assertTrue(any("reason" in error for error in contextport.validate(document)))

    def test_every_represented_item_requires_a_disposition(self):
        document = copy.deepcopy(self.valid)
        document["dispositions"] = [
            disposition
            for disposition in document["dispositions"]
            if disposition["source_ref"] != "source-message-001-block-001"
        ]
        self.assertTrue(
            any("missing disposition for 'content_block'" in error for error in contextport.validate(document))
        )

    def test_empty_text_is_distinct_from_unknown_content(self):
        document = copy.deepcopy(self.valid)
        block = document["messages"][0]["content"][0]
        block["text"] = ""
        block["sha256"] = contextport.hashlib.sha256(b"").hexdigest()
        self.assertEqual(contextport.validate(document), [])

    def test_duplicate_titles_are_allowed_but_duplicate_ids_are_not(self):
        document = copy.deepcopy(self.valid)
        duplicate = copy.deepcopy(document["conversations"][0])
        duplicate["id"] = "conversation-002"
        duplicate["source_ref"] = "source-conversation-002"
        duplicate["ordinal"] = 1
        document["conversations"].append(duplicate)
        document["dispositions"].append(
            {
                "source_ref": "source-conversation-002",
                "item_type": "conversation",
                "status": "copied",
            }
        )
        self.assertEqual(contextport.validate(document), [])
        document["conversations"][1]["id"] = "conversation-001"
        self.assertTrue(any("duplicate id" in error for error in contextport.validate(document)))

    def test_cli_exit_codes_and_messages(self):
        valid = subprocess.run(
            [sys.executable, str(MODULE_PATH), "validate", str(VALID_FIXTURE)],
            check=False,
            capture_output=True,
            text=True,
        )
        invalid = subprocess.run(
            [sys.executable, str(MODULE_PATH), "validate", str(INVALID_FIXTURE)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(valid.returncode, 0)
        self.assertIn("PASS", valid.stdout)
        self.assertEqual(invalid.returncode, 1)
        self.assertIn("6 error(s)", invalid.stdout)


if __name__ == "__main__":
    unittest.main()
