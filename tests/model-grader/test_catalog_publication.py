"""Publication regressions for the owner-approved D4/D2 rules. No model calls."""

import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "model-grader/reference/catalog"
SPEC = importlib.util.spec_from_file_location("catalog_publication", CATALOG / "grader.py")
GRADER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GRADER)


def record(obj, sku="P1"):
    return next(row for row in obj["records"] if row["sku"] == sku)


def fixture():
    data = json.loads((CATALOG / "gold/S1.json").read_text())
    return data["input"], data["candidate"]


def conflict(case, field="description", sku="P1", first="Slim fit", second="Relaxed fit"):
    record(case, sku)["fields"][field] = first
    refs = [f"{sku}.{field}", f"{sku}.{field}.alternative"]
    for ref, value in zip(refs, (first, second)):
        case["evidence"][ref] = {"sku": sku, "field": field, "value": value}
    record(case, sku).setdefault("conflicts", []).append({"field": field, "evidence": refs})
    return refs


def published(result):
    return {row["sku"]: row for row in result["publication_payload"]["records"]}


class CatalogPublicationTests(unittest.TestCase):
    def test_optional_conflict_can_be_silent_or_reported_without_an_action(self):
        for reported in (False, True):
            with self.subTest(reported=reported):
                case, candidate = fixture()
                refs = conflict(case)
                if reported:
                    record(candidate)["issues"].append({"code": "SOURCE_CONFLICT", "field": "description", "evidence": refs})
                result = GRADER.grade(case, candidate)
                self.assertEqual(result["verdict"], "PASS", result["errors"])
                self.assertIn("P1", published(result))
                self.assertNotIn("description", published(result)["P1"]["fields"])
                self.assertEqual(result["withheld"]["P1"], ["description"])

    def test_conditionally_required_subbrand_cannot_be_withheld(self):
        case, candidate = fixture()
        case["profile"]["subbrand_applicable"] = True
        conflict(case, "subbrand", first="Core", second="Premium")
        record(candidate)["fields"].pop("subbrand")
        record(candidate)["evidence"].pop("subbrand")
        result = GRADER.grade(case, candidate)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(published(result), {})
        self.assertFalse(result["withheld"])

    def test_withheld_child_field_is_not_also_a_family_mismatch(self):
        # PR #54 finding 1: an optional, disputed child value has no settled
        # value to compare with the parent. Other family fields remain checked.
        case, candidate = fixture()
        case["profile"]["subbrand_applicable"] = False
        conflict(case, "subbrand", "C1", "Core", "Premium")
        record(case)["fields"]["subbrand"] = "Heritage"
        case["evidence"]["P1.subbrand"]["value"] = "Heritage"
        record(candidate)["fields"]["subbrand"] = "Heritage"
        record(candidate, "C1")["fields"].pop("subbrand")
        record(candidate, "C1")["evidence"].pop("subbrand")
        result = GRADER.grade(case, candidate)
        self.assertEqual(result["verdict"], "PASS", result["errors"])
        self.assertEqual(set(published(result)), {"P1", "C1"})
        self.assertNotIn("subbrand", published(result)["C1"]["fields"])

    def test_warning_branches_follow_publication_and_authority(self):
        for mode in ("eligible_for_publication", "awaiting_approval", "blocked"):
            with self.subTest(mode=mode):
                case, candidate = fixture()
                refs = conflict(case)
                if mode == "awaiting_approval":
                    case["authority_registry"] = {"P1.description": {
                        "evidence_id": refs[1], "source_location": "supplier/spec",
                        "supplier_approved": False}}
                if mode == "blocked":
                    record(case)["fields"].pop("price")
                    case["evidence"].pop("P1.price")
                    row = record(candidate)
                    row["fields"].pop("price")
                    row["evidence"].pop("price")
                    row["status"] = "BLOCKED"
                    row["issues"] = [{"code": "MISSING_REQUIRED", "field": "price", "evidence": [], "action": "Supply price."}]
                result = GRADER.grade(case, candidate)
                self.assertEqual(result["verdict"], "PASS", result["errors"])
                warning = result["seller_warnings"][0]
                self.assertEqual(warning["branch"], mode)
                self.assertEqual("P1" in published(result), mode != "blocked")
                self.assertEqual({entry["evidence_id"] for entry in warning["conflicting_values"]}, set(refs))

    def test_rejected_candidate_never_gets_a_publication_claim(self):
        # A source may be READY while the candidate fails: warnings must use
        # the actual payload eligibility, including batch-level rejection.
        for defect in ("wrong-price", "wrong-case", "disputed-field", "omitted-sku"):
            with self.subTest(defect=defect):
                case, candidate = fixture()
                conflict(case)
                if defect == "wrong-price":
                    record(candidate)["fields"]["price"] = "0"
                elif defect == "wrong-case":
                    candidate["case_id"] = "wrong-case"
                elif defect == "disputed-field":
                    record(candidate)["fields"]["description"] = "Slim fit"
                else:
                    candidate["records"] = [record(candidate, "C1")]
                result = GRADER.grade(case, candidate)
                self.assertEqual(result["verdict"], "FAIL")
                self.assertNotIn("P1", published(result))
                self.assertEqual(result["seller_warnings"][0]["branch"], "blocked")

    def test_parent_projection_preserves_inputs_and_only_links_published_records(self):
        for parent_ready in (True, False):
            with self.subTest(parent_ready=parent_ready):
                case, candidate = fixture()
                if not parent_ready:
                    record(case)["fields"].pop("price")
                    case["evidence"].pop("P1.price")
                    row = record(candidate)
                    row["fields"].pop("price")
                    row["evidence"].pop("price")
                    row["status"] = "BLOCKED"
                    row["issues"] = [{"code": "MISSING_REQUIRED", "field": "price", "evidence": [], "action": "Supply price."}]
                before = copy.deepcopy((case, candidate))
                result = GRADER.grade(case, candidate)
                self.assertEqual(result["verdict"], "PASS", result["errors"])
                self.assertEqual(published(result)["C1"]["parent_sku"], "P1" if parent_ready else None)
                self.assertEqual(published(result)["C1"]["role"], "child")
                self.assertEqual((case, candidate), before)


if __name__ == "__main__":
    unittest.main()
