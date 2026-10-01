"""Offline diagnostics for the public pilot; no account or private records."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from helpers import ROOT  # makes the repository's model_router package importable
from model_router.cli import parser
from model_router.jev import MODEL, PROMPT_VERSION, JevClient, parse_response
from model_router.jev_cli import CASES, command, run_pilot
from test_jev import KEY, response


class PilotDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name) / "data"

    def record(self, case=1, *, at=1.0, legacy=False, **changes):
        _, evidence = parse_response(response("implementation", confidence=0.7))
        if legacy:
            evidence.pop("provider_choice", None)
        record = {"at": at, "status": "completed", "model": MODEL,
                  "prompt_version": PROMPT_VERSION, "seconds": 0.5542,
                  "prompt_hash": hashlib.sha256(CASES[case][1].encode()).hexdigest(),
                  **evidence, **changes}
        directory = self.data / "jev" / "requests"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (hashlib.sha256(f"{case}-{at}".encode()).hexdigest() + ".json")
        path.write_text(json.dumps(record))
        return path

    def report(self):
        args = argparse.Namespace(data_dir=str(self.data), jev_action="report")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = command(args)
        self.assertTrue(output.getvalue(), "report must produce diagnostic output")
        return code, json.loads(output.getvalue())

    def test_provider_choice_survives_confidence_or_consequence_escalation(self):
        for raw in (response("implementation", confidence=0.7),
                    response("implementation", consequences=0.3)):
            with self.subTest(raw=raw):
                answer, evidence = parse_response(raw)
                self.assertEqual(answer["task_kind"], "unknown")
                self.assertEqual(evidence.get("provider_choice"), "implementation")
                self.assertEqual(answer["diagnostics"]["provider_choice"], "implementation")

    def test_live_pilot_shows_original_choice_and_checks_but_keeps_failure(self):
        send = Mock(side_effect=[response("architecture"),
            response("implementation", confidence=0.7), response("routine_text"),
            response("high_credibility_writing"), response("high_risk_coding"),
            response("resource_extraction")])
        client = JevClient(self.data, transport=send)
        with patch.dict("os.environ", {}, clear=True):
            client.configure(key=KEY, free_only=True, auto_recharge_off=True, no_payment_method=True)
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(run_pilot(client), 1)
        report = json.loads(output.getvalue())
        row = report["cases"][1]
        self.assertEqual(report["passed"], 5)
        self.assertEqual(send.call_count, 6)
        self.assertEqual((row["expected"], row["combined_role"]), ("middle", "highest"))
        self.assertEqual(row["jev_diagnostics"]["provider_choice"], "implementation")
        self.assertFalse(row["jev_diagnostics"]["checks"]["confidence_sufficient"])
        self.assertNotIn(KEY, output.getvalue())

    def test_legacy_report_reads_scores_without_guessing_original_choice(self):
        self.record(legacy=True)
        code, report = self.report()
        row = report["cases"][1]
        self.assertEqual(code, 0)
        self.assertEqual(row["record_status"], "completed")
        self.assertIsNone(row["jev_diagnostics"]["provider_choice"])
        self.assertEqual(row["jev_diagnostics"]["leading_choices"], ["implementation"])
        self.assertEqual(row["jev_diagnostics"]["confidence"], 0.7)
        self.assertEqual((report["jev_calls"], report["gpt_calls"]), (0, 0))
        self.assertEqual(report["source"], "latest_saved_attempt_per_public_case_not_one_run")

    def test_report_never_calls_network_reads_key_or_writes_even_when_unconfigured(self):
        self.record(legacy=True)
        before = {p.relative_to(self.data): p.read_bytes() for p in self.data.rglob("*") if p.is_file()}
        with patch.object(JevClient, "__call__", side_effect=AssertionError("network")), \
                patch.object(JevClient, "_key", side_effect=AssertionError("credential")), \
                patch.object(JevClient, "status", side_effect=AssertionError("status reads key")), \
                patch.object(JevClient, "_write_json", side_effect=AssertionError("write")):
            self.assertEqual(self.report()[0], 0)
        after = {p.relative_to(self.data): p.read_bytes() for p in self.data.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_report_does_not_create_data_directory_when_nothing_is_saved(self):
        code, report = self.report()
        self.assertEqual(code, 1)
        self.assertEqual(report["matched_cases"], 0)
        self.assertFalse(self.data.exists())

    def test_report_is_available_through_the_public_cli_parser(self):
        args = parser().parse_args(["jev", "report", "--data-dir", str(self.data)])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(args.func(args), 1)
        self.assertEqual(json.loads(output.getvalue())["jev_calls"], 0)

    def test_provider_unknown_is_distinct_from_a_threshold_rejection(self):
        answer, _ = parse_response(response("unknown", confidence=0.95))
        self.assertEqual(answer["diagnostics"]["provider_choice"], "unknown")
        self.assertTrue(answer["diagnostics"]["checks"]["confidence_sufficient"])
        self.assertEqual(answer["task_kind"], "unknown")

    def test_legacy_probability_ties_do_not_become_an_invented_choice(self):
        probs = {k: 0.0 for k in response()["answers"]["task"]["probabilities"]}
        probs.update(implementation=0.5, unknown=0.5)
        self.record(legacy=True, probabilities=probs)
        _, report = self.report()
        scores = report["cases"][1]["jev_diagnostics"]
        self.assertIsNone(scores["provider_choice"])
        self.assertEqual(scores["leading_choices"], ["implementation", "unknown"])

    def test_unreadable_records_are_counted_without_echoing_contents(self):
        self.record(at=10**400)
        directory = self.data / "jev" / "requests"
        (directory / "broken.json").write_text(KEY)
        code, report = self.report()
        self.assertEqual(code, 1)
        self.assertEqual(report["unreadable_records"], 2)
        self.assertNotIn(KEY, json.dumps(report))

    def test_latest_pending_attempt_is_not_hidden_by_an_earlier_success(self):
        self.record(at=1)
        self.record(at=2, status="pending")
        _, report = self.report()
        row = report["cases"][1]
        self.assertEqual(row["record_status"], "pending")
        self.assertNotIn("jev_diagnostics", row)

    def test_same_timestamp_is_reported_as_ambiguous_not_arbitrarily_selected(self):
        first = self.record(at=2)
        first.with_name("other.json").write_text(first.read_text())
        _, report = self.report()
        self.assertEqual(report["cases"][1]["record_status"], "ambiguous_latest_attempt")

    def test_unrelated_prompts_and_extra_fields_never_reach_output(self):
        self.record(extra_secret=KEY, prompt="private text must not appear", reason=KEY)
        unrelated = self.record(case=0, prompt_hash="unrelated", extra_secret=KEY)
        _, report = self.report()
        result = json.dumps(report)
        self.assertNotIn(KEY, result)
        self.assertNotIn("private text", result)
        self.assertNotIn(str(unrelated), result)
        self.assertEqual(report["matched_cases"], 1)

    def test_corrupt_or_incompatible_records_are_not_reported_as_valid(self):
        for changes in ({"confidence": float("nan")}, {"provider_choice": KEY},
                        {"model": "different-model"}, {"prompt_version": "future-version"}):
            with self.subTest(changes=changes):
                self.record(**changes)
                _, report = self.report()
                self.assertIn(report["cases"][1]["record_status"],
                              {"invalid_evidence", "different_version"})
                self.assertNotIn(KEY, json.dumps(report))


if __name__ == "__main__":
    unittest.main()
