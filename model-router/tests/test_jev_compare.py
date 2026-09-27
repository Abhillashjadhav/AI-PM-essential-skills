"""Comparison isolation and failure handling. All provider responses are synthetic."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from helpers import ROOT
from model_router.cli import parser
from model_router.jev import (EVALUATION_CANDIDATE, EVALUATION_CLARIFICATION, PROMPT_VERSION,
                              JevClient, JevUnavailable, parse_response, request_for)
from model_router.jev_cli import CASES, report_saved_pilot
from model_router.jev_compare import (CHECKS, COMPARISON_CASES, VARIANTS, request_digest,
                                      run_comparison, score_result, summarize)
from test_jev import KEY, response


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.data = Path(self.tmp.name)
        self.send = Mock(side_effect=self.synthetic_reply)
        self.client = JevClient(self.data, transport=self.send)
        self.client.configure(key=KEY, free_only=True, auto_recharge_off=True, no_payment_method=True)

    @staticmethod
    def synthetic_reply(request, key):
        # Scripted fixture, not an LLM evaluation or assertion of live quality.
        kinds = ("architecture", "implementation", "routine_text", "high_credibility_writing",
                 "high_risk_coding", "resource_extraction", "implementation", "high_risk_coding",
                 "high_risk_coding", "high_risk_coding", "architecture", "product_decision")
        index = [prompt for _, prompt, _ in COMPARISON_CASES].index(request["state"]["task_text"])
        candidate = request["questions"]["consequences"]["instructions"].endswith(EVALUATION_CLARIFICATION)
        consequences = 0.9 if COMPARISON_CASES[index][2] == "highest" else 0.01
        if index == 1 and not candidate:
            consequences = 0.33
        return response(kinds[index], consequences=consequences)

    def run_comparison(self):
        with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
            result = run_comparison(self.client)
        report = json.loads(output.getvalue())
        evidence = json.loads(Path(report["evidence_file"]).read_text()) if "evidence_file" in report else None
        return result, report, evidence

    def test_single_mutation_leaves_default_and_baseline_requests_identical(self):
        for _, prompt, _ in COMPARISON_CASES:
            default = request_for(prompt)
            baseline = request_for(prompt, evaluation_variant="baseline")
            candidate = request_for(prompt, evaluation_variant=EVALUATION_CANDIDATE)
            self.assertEqual(default, baseline)
            changed = copy.deepcopy(candidate)
            changed["questions"]["consequences"]["instructions"] = changed["questions"]["consequences"]["instructions"].removesuffix(EVALUATION_CLARIFICATION)
            self.assertEqual(changed, default)
        self.assertEqual(COMPARISON_CASES[:6], CASES)

    def test_observed_scores_still_escalate_without_lowering_the_threshold(self):
        raw = response("implementation", confidence=0.95, consequences=0.33)
        raw["answers"]["task"]["confidence"] = 0.94
        answer, _ = parse_response(raw)
        scored = score_result(CASES[1][1], "middle", answer, 0.55)
        self.assertEqual(scored["role"], "highest")
        self.assertEqual(answer["task_kind"], "unknown")
        self.assertTrue(scored["checks"]["confidence_sufficient"])
        self.assertFalse(scored["checks"]["expected_role"])
        self.assertEqual(answer["diagnostics"]["thresholds"]["maximum_ordinary_consequences"], 0.2)

    def test_comparison_is_bounded_and_saves_exact_public_requests_without_promotion(self):
        before = request_for(CASES[1][1])
        with patch("model_router.cli.build", side_effect=AssertionError("Codex/queue must not start")):
            code, report, evidence = self.run_comparison()
        self.assertEqual(code, 0, report)
        self.assertEqual(self.send.call_count, 24)
        self.assertEqual(report["completed_calls"], 24)
        self.assertEqual(report["gpt_calls"], 0)
        self.assertEqual(report["verdict"], "ready_for_owner_review_not_promoted")
        self.assertFalse(report["promoted"])
        self.assertEqual(report["scores"]["baseline"], 59)
        self.assertEqual(report["scores"][EVALUATION_CANDIDATE], 60)
        self.assertEqual(before, request_for(CASES[1][1]))
        self.assertEqual(self.client.status()["prompt_version"], PROMPT_VERSION)
        self.assertTrue(self.client.status()["enabled"])
        self.assertEqual(evidence["locked_checks"], list(CHECKS))
        for index, row in enumerate(evidence["cases"]):
            self.assertEqual(row["order"], list(VARIANTS if index % 2 == 0 else reversed(VARIANTS)))
            for variant, request in row["requests"].items():
                self.assertEqual(row["request_digests"][variant], request_digest(request))
                self.assertIn(variant, row["request_ids"])
        self.assertEqual(Path(report["evidence_file"]).stat().st_mode & 0o777, 0o600)
        self.assertNotIn(KEY, json.dumps(report))
        self.assertNotIn(KEY, json.dumps(evidence))
        self.assertEqual(len(list((self.client.path / "requests").glob("*.json"))), 24)

    def test_flat_score_cannot_promote_or_be_called_an_improvement(self):
        def same_for_both(request, key):
            request = copy.deepcopy(request)
            request["questions"]["consequences"]["instructions"] += EVALUATION_CLARIFICATION
            return self.synthetic_reply(request, key)
        self.send.side_effect = same_for_both
        _, report, _ = self.run_comparison()
        self.assertEqual(report["verdict"], "no_improvement_keep_active_prompt")
        self.assertFalse(report["promoted"])

    def test_provider_risk_regression_cannot_hide_behind_local_risk_floor(self):
        def bad_candidate(request, key):
            if request["state"]["task_text"] == COMPARISON_CASES[9][1] and request["questions"]["consequences"]["instructions"].endswith(EVALUATION_CLARIFICATION):
                return response("implementation", consequences=0.01)
            return self.synthetic_reply(request, key)
        self.send.side_effect = bad_candidate
        code, report, evidence = self.run_comparison()
        self.assertEqual(code, 1)
        self.assertEqual(report["verdict"], "regression_keep_active_prompt")
        self.assertIn({"case": "approved security design", "check": "provider_role_matches"}, report["regressions"])
        self.assertEqual(evidence["cases"][9]["results"][EVALUATION_CANDIDATE]["role"], "highest")

    def test_late_and_unknown_answers_are_not_scored_as_success(self):
        answer, _ = parse_response(response("architecture"))
        self.assertFalse(score_result(CASES[0][1], "highest", answer, 2.0001)["checks"]["within_two_seconds"])
        answer, _ = parse_response(response("unknown"))
        self.assertFalse(score_result(CASES[0][1], "highest", answer, 0.5)["checks"]["provider_role_matches"])

    def test_first_provider_error_stops_run_and_disables_client_without_retry(self):
        self.send.side_effect = [response("architecture"), JevUnavailable("http_402")]
        code, report, evidence = self.run_comparison()
        self.assertEqual(code, 1)
        self.assertEqual(self.send.call_count, 2)
        self.assertEqual(report["completed_calls"], 1)
        self.assertEqual(report["verdict"], "incomplete_no_promotion")
        self.assertEqual(evidence["status"], "stopped")
        self.assertEqual(evidence["stop_reason"], "http_402")
        self.assertFalse(self.client.status()["enabled"])
        self.run_comparison()
        self.assertEqual(self.send.call_count, 2)

    def test_interruption_preserves_pending_request_and_never_resumes_it(self):
        self.send.side_effect = KeyboardInterrupt
        _, report, evidence = self.run_comparison()
        self.assertEqual(report["stop_reason"], "interrupted")
        self.assertEqual(evidence["status"], "stopped")
        self.assertEqual(self.client.status()["reason"], "unreconciled_attempt")
        self.run_comparison()
        self.assertEqual(self.send.call_count, 1)

    def test_failed_evidence_write_prevents_all_sends(self):
        with patch.object(self.client, "_write_json", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.run_comparison()
        self.send.assert_not_called()

    def test_variant_and_request_identity_are_bound_in_durable_journal(self):
        text = CASES[1][1]
        first = self.client(text, request_id="fixed-eval", evaluation_variant=EVALUATION_CANDIDATE)
        cached = self.client(text, request_id="fixed-eval", evaluation_variant=EVALUATION_CANDIDATE, cache_only=True)
        self.assertEqual(first["diagnostics"], cached["diagnostics"])
        self.assertIn(EVALUATION_CANDIDATE, first["reason"])
        self.assertEqual(self.send.call_count, 1)
        for variant in (None, "baseline"):
            with self.subTest(variant=variant), self.assertRaisesRegex(JevUnavailable, "request_changed"):
                self.client(text, request_id="fixed-eval", evaluation_variant=variant)
        record_path = next((self.client.path / "requests").glob("*.json"))
        record = json.loads(record_path.read_text())
        self.assertEqual(record["prompt_version"], PROMPT_VERSION + "/" + EVALUATION_CANDIDATE)
        record["request_digest"] = "different"
        record_path.write_text(json.dumps(record))
        with self.assertRaisesRegex(JevUnavailable, "request_changed"):
            self.client(text, request_id="fixed-eval", evaluation_variant=EVALUATION_CANDIDATE)
        self.assertEqual(self.send.call_count, 1)

    def test_invalid_or_anonymous_evaluation_never_sends(self):
        with self.assertRaisesRegex(JevUnavailable, "evaluation_request_id_required"):
            self.client(CASES[1][1], evaluation_variant=EVALUATION_CANDIDATE)
        with self.assertRaisesRegex(JevUnavailable, "invalid_evaluation_variant"):
            self.client(CASES[1][1], request_id="id", evaluation_variant="anything")
        self.send.assert_not_called()

    def test_old_normal_cache_still_works_but_not_as_an_evaluation(self):
        self.client(CASES[1][1], request_id="normal")
        path = next((self.client.path / "requests").glob("*.json"))
        record = json.loads(path.read_text())
        record.pop("request_digest")
        path.write_text(json.dumps(record))
        self.assertEqual(self.client(CASES[1][1], request_id="normal", cache_only=True)["task_kind"], "unknown")
        with self.assertRaisesRegex(JevUnavailable, "request_changed"):
            self.client(CASES[1][1], request_id="normal", evaluation_variant="baseline")
        self.assertEqual(self.send.call_count, 1)

    def test_comparison_does_not_overwrite_active_pilot_report(self):
        self.client(CASES[1][1])
        with contextlib.redirect_stdout(io.StringIO()) as before:
            report_saved_pilot(self.client)
        self.run_comparison()
        with contextlib.redirect_stdout(io.StringIO()) as after:
            report_saved_pilot(self.client)
        self.assertEqual(json.loads(before.getvalue()), json.loads(after.getvalue()))

    def test_every_explicit_rerun_preserves_old_evidence_as_separate_run(self):
        _, first, _ = self.run_comparison()
        old = Path(first["evidence_file"]).read_bytes()
        _, second, _ = self.run_comparison()
        self.assertNotEqual(first["evidence_file"], second["evidence_file"])
        self.assertEqual(Path(first["evidence_file"]).read_bytes(), old)
        self.assertEqual(self.send.call_count, 48)

    def test_compare_is_available_in_cli_and_unconfigured_client_sends_nothing(self):
        args = parser().parse_args(["jev", "compare", "--data-dir", str(self.data / "unused")])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(args.func(args), 1)
        self.assertEqual(json.loads(output.getvalue())["jev_calls"], 0)
        self.send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
