"""Evaluation foundation and weekly metrics (E01-E06), plus the capacity
estimator branches."""

import json
import unittest
from datetime import timedelta

from helpers import RouterTestCase
from model_router.capacity import CalibrationArtifact, CapacityEstimator, UsageObservation, build_calibration
from model_router.contracts import CreditsState, GradeStatus, UsageBucket, UsageSnapshot, parse_utc, utc_now
from model_router.evals.graders import SEEDED_CASES, check_judge, grade_assertions, promotion_evidence
from model_router.evals.metrics import iso_week, render_markdown, weekly_report
from model_router.evals.runner import build_live_plan, run_live, run_offline
from model_router.importer import import_file
from model_router.reporting import diagnostic_export, thread_drilldown

WEEK = iso_week(utc_now())


class Metrics(RouterTestCase):
    def answered_thread(self, text="Format my private notes"):
        result, _ = self.submit_and_run(text)
        return result.thread_id

    def report(self):
        return weekly_report(self.store, WEEK, include_synthetic=True)

    def test_E01_multiple_overrides_count_once(self):
        thread = self.answered_thread()
        for model in ("sim-sol-1", "sim-astra-1", "sim-sol-1"):
            self.coordinator.override_model(thread, model, reason="quality")
        self.answered_thread("Summarize this memo")
        report = self.report()
        self.assertEqual(report["guardrail"]["eligible_threads"], 2)
        self.assertEqual(report["guardrail"]["threads_with_override"], 1)
        self.assertEqual(report["diagnostic"]["override_events_in_cohort"], 3)
        self.assertEqual(len(report["this_week_override_events"]), 3)

    def test_E02_different_task_and_unknown_reasons_kept_separate(self):
        a = self.answered_thread()
        b = self.answered_thread("Summarize this memo")
        self.coordinator.override_model(a, "sim-astra-1", reason="new task")
        self.coordinator.override_model(b, "sim-astra-1", reason="")
        report = self.report()
        self.assertEqual(report["guardrail"]["threads_with_override"], 2, "guardrail definition unchanged")
        self.assertEqual(report["diagnostic"]["override_reasons"], {"different_task": 1, "unknown": 1})
        self.assertEqual(report["proposed_adjusted_view"]["threads_with_override"], 1)
        self.assertIn("awaiting owner acceptance", report["proposed_adjusted_view"]["status"])

    def test_E03_no_override_wrong_answer_is_not_success(self):
        thread = self.answered_thread()
        self.coordinator.record_outcome(thread, "failed", note="wrong dates")
        other = self.answered_thread("Summarize this memo")
        report = self.report()
        self.assertEqual(report["diagnostic"]["explicit_failures_without_switch"], [thread])
        self.assertEqual(report["diagnostic"]["confirmed_resolutions"], 0)
        self.assertEqual(report["diagnostic"]["unknown_outcomes"], 1)
        self.assertNotIn(other, report["diagnostic"]["explicit_failures_without_switch"])

    def test_E05_tiny_sample_reports_raw_counts_only(self):
        self.answered_thread()
        report = self.report()
        self.assertIn("sample too small", report["guardrail"]["verdict"])
        self.assertNotIn("95%", report["guardrail"]["verdict"])
        markdown = render_markdown(report)
        self.assertIn("SYNTHETIC", markdown)
        self.assertIn("Eligible threads: **1**", markdown)

    def test_synthetic_and_blocked_threads_excluded_from_guardrail(self):
        self.answered_thread()
        self.assertEqual(weekly_report(self.store, WEEK)["guardrail"]["eligible_threads"], 0, "synthetic excluded by default")
        from model_router.contracts import SpendStatus

        self.scenario.spend_status = SpendStatus.UNKNOWN
        self.submit_and_run("Format more notes")
        report = self.report()
        self.assertEqual(report["system"]["blocked_or_no_answer_threads"], 1)
        self.assertEqual(report["guardrail"]["eligible_threads"], 1)

    def test_latency_percentiles_and_cohort(self):
        for text in ("Format notes", "Summarize memo", "Review this product architecture"):
            self.coordinator.submit("Portfolio", text)
        latency = self.report()["latency_ms"]
        self.assertEqual(latency["count"], 3)
        self.assertIsNotNone(latency["warm"]["p50"])
        self.assertFalse(self.report()["cohort_complete"])

    def test_E06_diagnostic_export_redacted_by_default(self):
        secret_note = self.tmp / "resume.md"
        secret_note.write_text("Jane Example, jane@example.com, ghp_" + "a" * 30, encoding="utf-8")
        result = self.coordinator.submit("Portfolio", "Extract the dates from my resume jane@example.com", attachments=[str(secret_note)])
        self.coordinator.run(result.job_id)
        export = json.dumps(diagnostic_export(self.store))
        self.assertNotIn("jane@example.com", export)
        self.assertNotIn("ghp_" + "a" * 30, export)
        self.assertNotIn("Extract the dates", export)
        private = json.dumps(diagnostic_export(self.store, private=True))
        self.assertIn("Extract the dates", private)
        drill = thread_drilldown(self.store, result.thread_id)
        self.assertTrue(all("withheld" in m["content"] for m in drill["messages"]))


class RealisticPromptSets(unittest.TestCase):
    def test_no_under_routing_on_development_sets(self):
        from model_router.evals.runner import SUITABILITY_SETS, suitability

        self.assertGreaterEqual(len(SUITABILITY_SETS), 2)
        for path in SUITABILITY_SETS:
            if "dev" not in path.name:
                continue
            result = suitability(path)
            self.assertEqual(result["under_routed"], 0, (path.name, [m for m in result["misses"] if m["direction"] == "under"]))


class Graders(unittest.TestCase):
    def test_missing_evidence_is_never_pass(self):
        self.assertEqual(grade_assertions(None, {"required": ["x"]}).status, GradeStatus.BLOCKED)
        self.assertEqual(grade_assertions("text", {}).status, GradeStatus.INCONCLUSIVE)

    def test_E04_bad_judge_cannot_support_promotion(self):
        lenient = check_judge(lambda case: True, judge_id="lenient")
        self.assertFalse(lenient.usable)
        self.assertIn("seed-wrong-but-plausible", lenient.passed_critical)
        grades = [grade_assertions("ok", {"required": ["ok"]})]
        self.assertFalse(promotion_evidence(grades, lenient)["can_support_promotion"])
        self.assertFalse(check_judge(lambda c: c["should_pass"], judge_id="m", candidate_id="m").usable, "no self-judging")
        perfect = check_judge(lambda c: c["should_pass"], judge_id="oracle")
        self.assertTrue(perfect.usable)
        self.assertEqual(perfect.total, len(SEEDED_CASES))

    def test_critical_prohibited_action(self):
        grade = grade_assertions("I ran rm -rf docs", {"required": ["docs"], "prohibited_regex": [r"rm\s+-rf"]})
        self.assertEqual(grade.status, GradeStatus.FAIL)
        self.assertTrue(grade.critical_failures)


class Runner(RouterTestCase):
    def test_offline_run_records_evaluations_without_model_calls(self):
        result = run_offline(self.store)
        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["plan"]["model_calls"], 0)
        self.assertEqual(self.adapter.model_sends, 0)
        count = self.store.one("SELECT COUNT(*) AS n FROM evaluations WHERE run_id=?", (result["run_id"],))["n"]
        self.assertEqual(count, result["passed"])
        self.assertTrue(self.events("evaluation.started"))

    def test_live_plan_is_finite_and_authorised(self):
        cases = [{"id": "c1", "prompt": "Summarise: launch moved to 12 March", "spec": {"anchors": ["12 March"]}}]
        with self.assertRaises(ValueError):
            build_live_plan(cases * 60, ["a"])
        plan = build_live_plan(cases, ["sim-sol-1"])
        self.assertEqual(run_live(plan, self.coordinator, project="Portfolio", authorised_by=None)["status"], "BLOCKED")
        self.assertEqual(run_live(plan, self.coordinator, project="Portfolio", authorised_by="owner")["status"], "BLOCKED", "not live")
        self.scenario.turn_scripts.append([{"kind": "delta", "text": "Launch moved to 12 March."}, {"kind": "completed"}])
        simulated = run_live(plan, self.coordinator, project="Portfolio", authorised_by="owner", allow_simulated=True)
        self.assertEqual(simulated["status"], "COMPLETED")
        self.assertEqual(simulated["records"][0]["grade"]["status"], "PASS")
        self.assertTrue(simulated["records"][0]["synthetic"])

    def test_live_run_yields_to_foreground(self):
        self.scenario.ordinary_usage_allowed = False
        self.submit_and_run("Format my notes")
        self.scenario.ordinary_usage_allowed = True
        self.store.execute("UPDATE jobs SET state='SELECTED' WHERE kind='user_turn'")
        plan = build_live_plan([{"id": "c", "prompt": "x"}], ["sim-sol-1"])
        result = run_live(plan, self.coordinator, project="Portfolio", authorised_by="owner", allow_simulated=True)
        self.assertEqual(result["status"], "YIELDED")


class Capacity(unittest.TestCase):
    def usage(self, used, *, age=0, plan="plus", synthetic=True):
        observed = (parse_utc(utc_now()) - timedelta(seconds=age)).isoformat().replace("+00:00", "Z")
        return UsageSnapshot("u", "a", plan, "s", [UsageBucket("codex", None, used, 300, None)] if used is not None else [],
                             CreditsState(None, None, None, False), True, None, None, observed, "t", synthetic)

    def calibration(self, **kw):
        base = dict(model_id="m", reasoning_effort="e", plan_type="plus", bucket_ids=["codex"], forecast_low=30.0,
                    forecast_high=45.0, observation_ids=["o"], validated=True, approval_id="a", synthetic=True)
        return CalibrationArtifact(**(base | kw))

    def estimate(self, calibration, usage):
        return CapacityEstimator([calibration] if calibration else []).estimate(model_id="m", reasoning_effort="e", usage=usage)

    def test_branches(self):
        self.assertEqual(self.estimate(self.calibration(), self.usage(10)).state.value, "SUFFICIENT")
        self.assertEqual(self.estimate(self.calibration(), self.usage(90)).state.value, "TIGHT")
        self.assertEqual(self.estimate(self.calibration(), self.usage(60)).state.value, "UNKNOWN", "overlap")
        self.assertEqual(self.estimate(None, self.usage(10)).state.value, "UNKNOWN", "shipped default")
        self.assertEqual(self.estimate(self.calibration(validated=False, approval_id=None), self.usage(90)).state.value, "UNKNOWN")
        self.assertEqual(self.estimate(self.calibration(), self.usage(90, age=3600)).state.value, "UNKNOWN", "stale")
        self.assertEqual(self.estimate(self.calibration(), self.usage(None)).state.value, "UNKNOWN", "absent bucket")
        self.assertEqual(self.estimate(self.calibration(), self.usage(90, plan="pro")).state.value, "UNKNOWN", "plan regime")
        self.assertEqual(self.estimate(self.calibration(), self.usage(90, synthetic=False)).state.value, "UNKNOWN", "no mixing")
        tight = self.estimate(self.calibration(), self.usage(90))
        self.assertEqual(tight.label, "estimated")
        self.assertIn("estimated, not guaranteed", tight.uncertainty)

    def test_calibration_excludes_contaminated_and_needs_evidence(self):
        obs = [UsageObservation(f"o{i}", "m", "e", "plus", "codex", 10, 10 + i, "s", 100, 1, 1) for i in range(5)]
        obs.append(UsageObservation("bad", "m", "e", "plus", "codex", 10, 90, "s", 100, 1, 1, concurrent_sessions=True))
        artifact, notes = build_calibration(obs, model_id="m", reasoning_effort="e", plan_type="plus")
        self.assertFalse(artifact.validated)
        self.assertNotIn("bad", artifact.observation_ids)
        self.assertTrue(any("contaminated" in n for n in notes))
        none, notes = build_calibration(obs[:2], model_id="m", reasoning_effort="e", plan_type="plus")
        self.assertIsNone(none)


class Importer(RouterTestCase):
    def test_import_dedupes_marks_summaries_and_reports_coverage(self):
        from helpers import ROOT

        path = ROOT / "fixtures" / "import-example.json"
        first = import_file(self.store, path, project_root=str(self.tmp), since_days=30, now="2026-09-25T00:00:00Z")
        second = import_file(self.store, path, project_root=str(self.tmp), since_days=30, now="2026-09-25T00:00:00Z")
        coverage = first["coverage"]["Portfolio"]
        self.assertEqual((coverage["threads"], coverage["messages"], coverage["summaries"], coverage["skipped_old"]), (2, 3, 1, 1))
        self.assertEqual(second["coverage"]["Portfolio"]["duplicates"], 3)
        kinds = {r["kind"] for r in self.store.all("SELECT kind FROM messages WHERE provenance LIKE 'import:%'")}
        self.assertEqual(kinds, {"imported", "memory_summary"})
        self.assertEqual(weekly_report(self.store, "2026-W38")["guardrail"]["eligible_threads"], 0, "imports are not routed threads")


if __name__ == "__main__":
    unittest.main()
