import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "pm-tactical/skills/ai-workflow-trial"
SPEC = importlib.util.spec_from_file_location("trial_kit", SKILL / "trial_kit.py")
kit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kit)
EXAMPLES = SKILL / "examples"
AS_OF = "2026-09-08T00:00:00Z"


def results_bytes(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=kit.RESULT_COLUMNS, lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    return output.getvalue().encode()


class TrialKitTests(unittest.TestCase):
    def setUp(self):
        self.design_raw = (EXAMPLES / "design.json").read_bytes()
        self.units_raw = (EXAMPLES / "units.csv").read_bytes()
        self.plan = kit.build_plan(self.design_raw, self.units_raw)
        self.rows = kit.csv_rows((EXAMPLES / "results_fast_draft.csv").read_bytes(), kit.RESULT_COLUMNS)

    def assert_block(self, code, call):
        with self.assertRaises(kit.TrialBlocked) as raised:
            call()
        self.assertEqual(raised.exception.code, code)

    def changed_design(self, **changes):
        return json.dumps({**json.loads(self.design_raw), **changes}).encode()

    def report(self, rows=None):
        return kit.audit(self.plan, results_bytes(self.rows if rows is None else rows), AS_OF)

    def test_reproducible_balanced_assignments_and_raw_hashes(self):
        self.assertEqual(self.plan, kit.build_plan(self.design_raw, self.units_raw))
        self.assertEqual(self.plan["manifest"]["units_file_sha256"], kit.hashlib.sha256(self.units_raw).hexdigest())
        for stratum in ("account", "billing", "complex", "simple"):
            group = [a for a in self.plan["assignments"] if a["stratum"] == stratum]
            self.assertEqual(sum(a["assigned_arm"] == kit.ARMS[0] for a in group), 4)
            self.assertEqual(sum(a["assigned_arm"] == kit.ARMS[1] for a in group), 4)

    def test_csv_order_does_not_change_assignments(self):
        lines = self.units_raw.decode().splitlines()
        reordered = ("\n".join([lines[0], *reversed(lines[1:])]) + "\n").encode()
        self.assertEqual(self.plan["assignments"], kit.build_plan(self.design_raw, reordered)["assignments"])
        self.assertNotEqual(self.plan["manifest"]["units_file_sha256"], kit.build_plan(self.design_raw, reordered)["manifest"]["units_file_sha256"])

    def test_seed_changes_assignment(self):
        changed = kit.build_plan(self.changed_design(seed=7), self.units_raw)
        self.assertNotEqual(changed["assignments"], self.plan["assignments"])

    def test_unsupported_designs_and_spillover_stop(self):
        for value in ("cluster", "adaptive", "crossover"):
            self.assert_block("unsupported_design", lambda: kit.build_plan(self.changed_design(design=value), self.units_raw))
        for value in ("yes", "unknown", False):
            self.assert_block("spillover_not_resolved", lambda: kit.build_plan(self.changed_design(spillover=value), self.units_raw))

    def test_unfrozen_eligibility_stops(self):
        for value in (False, "true", None):
            self.assert_block("eligibility_not_frozen", lambda: kit.build_plan(self.changed_design(eligibility_frozen=value), self.units_raw))

    def test_scope_and_omissions_must_be_declared(self):
        self.assert_block("labor_scope", lambda: kit.build_plan(self.changed_design(labor_scope={}), self.units_raw))
        self.assert_block("unmeasured_work", lambda: kit.build_plan(self.changed_design(unmeasured_work="none"), self.units_raw))
        self.assert_block("missing_declaration", lambda: kit.build_plan(self.changed_design(outcome=" "), self.units_raw))

    def test_invalid_seed_and_window(self):
        self.assert_block("invalid_seed", lambda: kit.build_plan(self.changed_design(seed=True), self.units_raw))
        self.assert_block("invalid_window", lambda: kit.build_plan(self.changed_design(window_end="2026-08-01T00:00:00Z"), self.units_raw))

    def test_duplicate_units_and_odd_strata_stop(self):
        self.assert_block("duplicate_unit", lambda: kit.build_plan(self.design_raw, self.units_raw + b"TASK-001,account\n"))
        self.assert_block("unbalanced_stratum", lambda: kit.build_plan(self.design_raw, b"unit_id,stratum\nONE,simple\n"))

    def test_manifest_and_assignment_changes_stop(self):
        changed = copy.deepcopy(self.plan); changed["manifest"]["design_sha256"] = "0" * 64
        self.assert_block("manifest_mismatch", lambda: kit.validate_plan(changed))
        changed = copy.deepcopy(self.plan); changed["assignments"][0]["assigned_arm"] = "altered"
        self.assert_block("assignment_mismatch", lambda: kit.validate_plan(changed))

    def test_missing_duplicate_and_extra_results_stop(self):
        self.assert_block("missing_assigned_units", lambda: self.report(self.rows[:-1]))
        self.assert_block("duplicate_result", lambda: self.report(self.rows + [self.rows[0]]))
        extra = {**self.rows[0], "unit_id": "OUTSIDE"}
        self.assert_block("extra_unit", lambda: self.report(self.rows + [extra]))

    def test_missing_invalid_negative_nonfinite_labor_never_becomes_zero(self):
        for value in ("", "no data", "-1", "NaN", "Infinity", "-inf", "1e309"):
            with self.subTest(value=value):
                rows = copy.deepcopy(self.rows); rows[0]["review_minutes"] = value
                self.assert_block("invalid_labor", lambda: self.report(rows))

    def test_unrepresentable_aggregate_stops(self):
        rows = copy.deepcopy(self.rows)
        for row in rows:
            for key in kit.LABOR:
                row[key] = "1e308"
        self.assert_block("unrepresentable_aggregate", lambda: self.report(rows))

    def test_failed_unfinished_and_crossovers_keep_original_denominators(self):
        report = self.report()
        control, ai = (report["by_assignment"][arm] for arm in kit.ARMS)
        self.assertEqual((control["assigned_units"], ai["assigned_units"]), (16, 16))
        self.assertEqual((control["successes"], ai["successes"]), (14, 10))
        self.assertEqual((control["failed"], control["unfinished"]), (1, 1))
        self.assertEqual((ai["failed"], ai["unfinished"]), (5, 1))
        self.assertEqual((control["assignment_deviations"], ai["assignment_deviations"]), (1, 1))
        self.assertEqual((control["total_measured_human_minutes"], ai["total_measured_human_minutes"]), (320, 400))
        self.assertEqual(ai["successful_outcomes_per_measured_human_hour"], 1.5)
        self.assertEqual(control["successful_outcomes_per_measured_human_hour"], 2.625)

    def test_all_unfinished_have_observed_effort_and_unsuccessful_at_horizon(self):
        rows = [{**r, "status": "unfinished", "success": "no"} for r in self.rows]
        report = self.report(rows)
        self.assertEqual(report["assigned_units"], 32)
        for arm in kit.ARMS:
            group = report["by_assignment"][arm]
            self.assertEqual(group["unfinished"], 16)
            self.assertEqual(group["success_rate"], 0)
            self.assertGreater(group["total_measured_human_minutes"], 0)
        self.assertIn("unsuccessful there", kit.report_text(report))

    def test_immature_global_and_unit_horizons_stop(self):
        self.assert_block("immature_window", lambda: kit.audit(self.plan, results_bytes(self.rows), "2026-09-07T23:59:59Z"))
        rows = copy.deepcopy(self.rows); rows[0]["observed_through"] = "2026-09-07T00:00:00Z"
        self.assert_block("immature_unit_window", lambda: self.report(rows))
        rows[0]["observed_through"] = "2026-09-09T00:00:00Z"
        self.assert_block("unequal_unit_horizon", lambda: self.report(rows))

    def test_failed_or_unfinished_cannot_be_successful(self):
        for status in ("failed", "unfinished"):
            rows = copy.deepcopy(self.rows); rows[0].update(status=status, success="yes")
            self.assert_block("inconsistent_success", lambda: self.report(rows))

    def test_zero_effort_efficiency_stays_undefined_with_success_counts(self):
        rows = [{**r, **{k: "0" for k in kit.LABOR}} for r in self.rows]
        report = self.report(rows)
        for arm in kit.ARMS:
            self.assertIsNone(report["by_assignment"][arm]["successful_outcomes_per_measured_human_hour"])
        self.assertIn("undefined", kit.report_text(report))
        self.assertIn("null", json.dumps(report, allow_nan=False))
        self.assertEqual(report["by_assignment"][kit.ARMS[1]]["successes"], 10)

    def test_higher_ratio_and_worse_outcomes_never_name_a_winner(self):
        report = kit.audit(self.plan, (EXAMPLES / "results_ratio_tradeoff.csv").read_bytes(), AS_OF)
        control, ai = (report["by_assignment"][arm] for arm in kit.ARMS)
        self.assertGreater(ai["successful_outcomes_per_measured_human_hour"], control["successful_outcomes_per_measured_human_hour"])
        self.assertLess(ai["successes"], control["successes"])
        text = kit.report_text(report)
        self.assertIn("Success", text); self.assertIn("Measured min", text)
        self.assertIn("Ratio alone names no winner", text)
        self.assertNotIn("winner", report)
        self.assertNotIn("p_value", report)

    def test_omitted_work_stays_visible_and_scope_is_measured_not_all(self):
        plan = kit.build_plan(self.changed_design(unmeasured_work=["onboarding outside the four fields"]), self.units_raw)
        report = kit.audit(plan, results_bytes(self.rows), AS_OF)
        self.assertIn("onboarding outside the four fields", kit.report_text(report))
        self.assertEqual(report["labor_scope"], plan["design"]["labor_scope"])
        self.assertNotIn("total_human_minutes", report["by_assignment"][kit.ARMS[0]])

    def test_favorable_fixture_reuses_same_assignments(self):
        report = kit.audit(self.plan, (EXAMPLES / "results_favorable.csv").read_bytes(), AS_OF)
        control, ai = (report["by_assignment"][arm] for arm in kit.ARMS)
        self.assertEqual(report["plan_sha256"], self.report()["plan_sha256"])
        self.assertEqual((control["successes"], ai["successes"]), (14, 15))
        self.assertEqual((control["total_measured_human_minutes"], ai["total_measured_human_minutes"]), (320, 160))
        self.assertEqual(ai["successful_outcomes_per_measured_human_hour"], 5.625)

    def test_bad_csv_shapes_and_duplicate_json_keys_stop(self):
        self.assert_block("csv_columns", lambda: kit.csv_rows(b"unit_id,unit_id\nA,A\n", ("unit_id", "stratum")))
        self.assert_block("csv_row_shape", lambda: kit.csv_rows(b"unit_id,stratum\nA,simple,extra\n", ("unit_id", "stratum")))
        self.assert_block("duplicate_json_key", lambda: kit.read_json(b'{"a":1,"a":2}'))
        self.assert_block("invalid_json", lambda: kit.read_json(b'{"a":NaN}'))

    def test_cli_plan_audit_refusal_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan_path = Path(tmp) / "plan.json"
            command = [sys.executable, str(SKILL / "trial_kit.py")]
            def run(*args):
                return subprocess.run([*command, *args], capture_output=True, text=True, timeout=15)
            planned = run("plan", "--design", str(EXAMPLES / "design.json"), "--units", str(EXAMPLES / "units.csv"), "--out", str(plan_path))
            self.assertEqual(planned.returncode, 0, planned.stdout)
            before = plan_path.read_bytes()
            duplicate = run("plan", "--design", str(EXAMPLES / "design.json"), "--units", str(EXAMPLES / "units.csv"), "--out", str(plan_path), "--format", "json")
            self.assertEqual(json.loads(duplicate.stdout)["reason"], "output_exists")
            self.assertEqual(plan_path.read_bytes(), before)
            good = run("audit", "--plan", str(plan_path), "--results", str(EXAMPLES / "results_fast_draft.csv"), "--as-of", AS_OF, "--format", "json")
            self.assertEqual(good.returncode, 0, good.stdout)
            self.assertEqual(json.loads(good.stdout)["accounted_units"], 32)
            gap = run("audit", "--plan", str(plan_path), "--results", str(EXAMPLES / "results_gap.csv"), "--as-of", AS_OF, "--format", "json")
            self.assertEqual(gap.returncode, 2)
            self.assertEqual(json.loads(gap.stdout)["reason"], "missing_assigned_units")

    def test_blank_results_template_retains_units_without_inventing_effort(self):
        rows = kit.csv_rows(kit.results_template(self.plan).encode(), kit.RESULT_COLUMNS)
        self.assertEqual([r["unit_id"] for r in rows], [a["unit_id"] for a in self.plan["assignments"]])
        self.assertTrue(all(r["observed_through"] == AS_OF for r in rows))
        self.assertTrue(all(r[key] == "" for r in rows for key in ("actual_arm", "status", "success", *kit.LABOR)))
        self.assert_block("invalid_actual_arm", lambda: kit.audit(self.plan, results_bytes(rows), AS_OF))

    def test_results_template_cli_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan_path, output = Path(tmp) / "plan.json", Path(tmp) / "blank.csv"
            kit.write_json(plan_path, self.plan)
            args = [sys.executable, str(SKILL / "trial_kit.py"), "results-template", "--plan", str(plan_path), "--out", str(output), "--format", "json"]
            result = subprocess.run(args, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(json.loads(result.stdout)["status"], "BLANK_TEMPLATE")
            before = output.read_bytes()
            result = subprocess.run(args, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["reason"], "output_exists")
            self.assertEqual(output.read_bytes(), before)

    def test_unfilled_design_template_cannot_be_used_as_a_frozen_plan(self):
        template = (SKILL / "templates/design.json").read_bytes()
        self.assert_block("eligibility_not_frozen", lambda: kit.build_plan(template, self.units_raw))

    def test_custom_workflow_not_tied_to_synthetic_support_ids_or_32_tasks(self):
        units = b"unit_id,stratum\nRESEARCH-A,small\nRESEARCH-B,small\nRESEARCH-C,large\nRESEARCH-D,large\n"
        plan = kit.build_plan(self.changed_design(trial_id="custom-research", outcome="Handoff accepted by cutoff"), units)
        rows = [{"unit_id": a["unit_id"], "actual_arm": a["assigned_arm"], "status": "unfinished", "success": "no", "observed_through": AS_OF,
                 **{key: "2.5" for key in kit.LABOR}} for a in plan["assignments"]]
        report = kit.audit(plan, results_bytes(rows), AS_OF)
        self.assertEqual((report["trial_id"], report["assigned_units"], report["outcome"]), ("custom-research", 4, "Handoff accepted by cutoff"))
        self.assertEqual(report["human_effort_method"], plan["design"]["human_effort_method"])
        for group in report["by_assignment"].values():
            self.assertEqual((group["assigned_units"], group["unfinished"], group["total_measured_human_minutes"]), (2, 2, 20))

    def test_demo_narration_tracks_changed_fixture_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "skill"
            (skill / "demo").mkdir(parents=True)
            shutil.copy(SKILL / "trial_kit.py", skill / "trial_kit.py")
            shutil.copy(SKILL / "demo/walkthrough.py", skill / "demo/walkthrough.py")
            shutil.copytree(EXAMPLES, skill / "examples")
            assignments = {a["unit_id"]: a["assigned_arm"] for a in self.plan["assignments"]}
            fast = copy.deepcopy(self.rows)
            for row in fast:
                if assignments[row["unit_id"]] == kit.ARMS[1]:
                    row["draft_minutes"] = "5"
            (skill / "examples/results_fast_draft.csv").write_bytes(results_bytes(fast))
            tradeoff = kit.csv_rows((EXAMPLES / "results_ratio_tradeoff.csv").read_bytes(), kit.RESULT_COLUMNS)
            removed = 0
            for row in tradeoff:
                if assignments[row["unit_id"]] == kit.ARMS[1] and row["success"] == "yes" and removed < 2:
                    row.update(status="failed", success="no"); removed += 1
            (skill / "examples/results_ratio_tradeoff.csv").write_bytes(results_bytes(tradeoff))
            result = subprocess.run([sys.executable, str(skill / "demo/walkthrough.py"), "--pause-seconds", "0"], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Fictional mean AI-assigned effort: 5 draft + 7 review + 10 rework + 4 follow-up min", result.stdout)
            self.assertIn("58.3% less drafting time", result.stdout)
            self.assertIn("AI ratio = 6.000; customer successes: Standard 14, AI 8", result.stdout)
            self.assertNotIn("ratio = 7.500", result.stdout)


if __name__ == "__main__":
    unittest.main()
