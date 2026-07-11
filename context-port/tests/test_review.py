import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


contextport = load("contextport")
segregation = load("segregation")
review = load("review")


class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads((ROOT / "fixtures" / "segregation-contextpack.json").read_text())
        cls.mappings = json.loads((ROOT / "fixtures" / "project-mappings-valid.json").read_text())
        cls.plan = segregation.segregate(cls.document, cls.mappings, validator=contextport.validate)

    def package(self, document=None):
        return review.build_review_package(document or self.document, self.plan)

    def approved_decision(self, package):
        return {
            "decision_version": "0.1",
            "review_package_sha256": package["review_package_sha256"],
            "decision": "approve",
            "confirmations": {name: True for name in review.REQUIRED_CONFIRMATIONS},
            "note": "Synthetic approval.",
        }

    def test_every_group_is_represented(self):
        package = self.package()
        self.assertEqual(len(package["groups"]), 3)
        self.assertTrue(package["selection"]["all_groups_represented"])

    def test_sample_is_first_and_last_without_duplicates(self):
        document = copy.deepcopy(self.document)
        plan = copy.deepcopy(self.plan)
        group = plan["groups"][0]
        template = copy.deepcopy(document["conversations"][0])
        for ordinal in (1, 2):
            conversation = copy.deepcopy(template)
            conversation["id"] = f"conversation-extra-{ordinal}"
            conversation["source_ref"] = f"source-conversation-extra-{ordinal}"
            conversation["ordinal"] = ordinal
            document["conversations"].append(conversation)
            group["conversations"].append(
                {"conversation_id": conversation["id"], "source_ref": conversation["source_ref"], "title": conversation["title"], "ordinal": ordinal, "message_ids": [], "message_count": 0}
            )
            plan["membership"].append(
                {"conversation_id": conversation["id"], "group_project_id": "project-a"}
            )
        unsigned = {key: value for key, value in plan.items() if key != "plan_sha256"}
        plan["plan_sha256"] = review.canonical_digest(unsigned)
        package = review.build_review_package(document, plan)
        ids = [item["conversation_id"] for item in package["groups"][0]["samples"]]
        self.assertEqual(ids, ["conversation-a", "conversation-extra-2"])

    def test_package_omits_message_text_and_unknown_raw(self):
        package = self.package()
        encoded = json.dumps(package)
        self.assertFalse(package["message_text_emitted"])
        self.assertFalse(package["unknown_raw_payload_emitted"])
        self.assertNotIn("Synthetic inert content", encoded)

    def test_package_is_deterministic(self):
        self.assertEqual(self.package(), self.package())

    def test_approval_requires_all_confirmations(self):
        package = self.package()
        decision = self.approved_decision(package)
        decision["confirmations"][review.REQUIRED_CONFIRMATIONS[0]] = False
        with self.assertRaisesRegex(review.ReviewError, "every confirmation"):
            review.validate_decision(package, decision)

    def test_decision_must_match_package_digest(self):
        package = self.package()
        decision = self.approved_decision(package)
        decision["review_package_sha256"] = "0" * 64
        with self.assertRaisesRegex(review.ReviewError, "does not match"):
            review.validate_decision(package, decision)

    def test_tampered_plan_is_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan["groups"][0]["title"] = "Tampered"
        with self.assertRaisesRegex(review.ReviewError, "plan digest"):
            review.build_review_package(self.document, plan)

    def test_incomplete_plan_membership_is_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan["membership"].pop()
        unsigned = {key: value for key, value in plan.items() if key != "plan_sha256"}
        plan["plan_sha256"] = review.canonical_digest(unsigned)
        with self.assertRaisesRegex(review.ReviewError, "exactly cover"):
            review.build_review_package(self.document, plan)

    def test_rejection_never_authorizes_automatic_repair(self):
        package = self.package()
        decision = self.approved_decision(package)
        decision["decision"] = "reject"
        decision["confirmations"] = {name: False for name in review.REQUIRED_CONFIRMATIONS}
        result = review.validate_decision(package, decision)
        self.assertFalse(result["automatic_repair_authorized"])

    def test_html_escapes_imported_titles(self):
        package = self.package()
        package["groups"][0]["title"] = "<script>alert('x')</script>"
        rendered = review.render_review_html(package)
        self.assertNotIn("<script>alert('x')</script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("Required confirmations", rendered)

    def test_golden_review_package_digest(self):
        package = self.package()
        golden = json.loads((ROOT / "fixtures" / "review-package-synthetic.json").read_text())
        self.assertEqual(package, golden)

    def test_public_schema_versions_match(self):
        package_schema = json.loads((ROOT / "schemas" / "review-package-0.1.schema.json").read_text())
        decision_schema = json.loads((ROOT / "schemas" / "review-decision-0.1.schema.json").read_text())
        self.assertEqual(package_schema["properties"]["review_version"]["const"], review.REVIEW_VERSION)
        self.assertEqual(decision_schema["properties"]["decision_version"]["const"], review.DECISION_VERSION)

    def test_cli_renders_html_and_validates_decisions(self):
        package = ROOT / "fixtures" / "review-package-synthetic.json"
        html_result = subprocess.run(
            [sys.executable, str(ROOT / "contextport.py"), "review-html", str(package)],
            check=False,
            capture_output=True,
            text=True,
        )
        approved = subprocess.run(
            [sys.executable, str(ROOT / "contextport.py"), "review-decision", str(package), str(ROOT / "fixtures" / "review-decision-approved.json")],
            check=False,
            capture_output=True,
            text=True,
        )
        rejected = subprocess.run(
            [sys.executable, str(ROOT / "contextport.py"), "review-decision", str(package), str(ROOT / "fixtures" / "review-decision-rejected.json")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(html_result.returncode, 0)
        self.assertIn("<!doctype html>", html_result.stdout)
        self.assertEqual(approved.returncode, 0)
        self.assertEqual(rejected.returncode, 4)
        self.assertFalse(json.loads(rejected.stdout)["automatic_repair_authorized"])


if __name__ == "__main__":
    unittest.main()
