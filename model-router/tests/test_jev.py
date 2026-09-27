"""Provider credit failures and routing integration; every response is synthetic."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from helpers import ROOT, RouterTestCase
from model_router.adapters.codex_stdio import minimal_env
from model_router.classifier import ClassifierInput, classify
from model_router.cli import build
from model_router.contracts import Role, TaskKind
from model_router.jev import (CRITERIA, MODEL, JevClient, JevUnavailable,
                              attach_jev_classifier, http_once, parse_response, request_for)
from model_router.jev_cli import CASES, run_pilot
from model_router.plugin_classifier import combined_classifier
from model_router.policy import required_role

KEY = "synthetic-typesafe-test-key"
NOW = 1_800_000_000.0


def response(kind="routine_text", confidence=0.95, consequences=0.01):
    probabilities = {name: (confidence if name == kind else (1 - confidence) / (len(CRITERIA) - 1)) for name in CRITERIA}
    return {"model": MODEL, "answers": {
        "task": {"type": "choice", "choice": kind, "probabilities": probabilities, "confidence": confidence},
        "consequences": {"type": "noul", "noul": consequences}},
        "usage": {"input_tokens": 500, "output_tokens": 0}}


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name)
        self.now = NOW
        self.send = Mock(return_value=response())
        self.client = JevClient(self.data, clock=lambda: self.now, transport=self.send)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def configure(self, **kwargs):
        args = dict(key=KEY, free_only=True, auto_recharge_off=True, no_payment_method=True)
        self.client.configure(**(args | kwargs))

    def state(self):
        return json.loads((self.client.path / "state.json").read_text())

    def records(self):
        return [json.loads(p.read_text()) for p in (self.client.path / "requests").glob("*.json")]

    def test_no_implicit_enable_from_key_and_no_network_in_status(self):
        os.environ["TYPESAFE_API_KEY"] = KEY
        self.assertFalse(self.client.status()["enabled"])
        with self.assertRaisesRegex(JevUnavailable, "not_configured"):
            self.client("Format notes")
        self.send.assert_not_called()

    def test_setup_requires_owner_free_credit_and_no_payment_confirmation(self):
        for field in ("free_only", "auto_recharge_off", "no_payment_method"):
            with self.subTest(field=field), self.assertRaises(JevUnavailable):
                self.configure(**{field: False})
        self.send.assert_not_called()

    def test_private_records_contain_no_key_or_prompt(self):
        self.configure()
        text = "Format my confidential canary 9938127"
        self.assertEqual(self.client(text)["task_kind"], "routine_text")
        for path in (self.client.path / "api-key", self.client.path / "state.json", *list((self.client.path / "requests").glob("*.json"))):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.client.path.stat().st_mode & 0o777, 0o700)
        for data in (json.dumps(self.state()), json.dumps(self.records()), json.dumps(self.client.status())):
            self.assertNotIn(KEY, data)
            self.assertNotIn(text, data)
        self.assertIn("UNKNOWN", self.client.status()["provider_balance"])
        self.assertEqual(self.records()[0]["estimated_cost_micro_usd"], 21)

    def test_pending_request_commits_before_dispatch(self):
        self.configure()
        def inspect(request, key):
            self.assertEqual(key, KEY)
            self.assertEqual(self.state()["attempts"], 1)
            self.assertIsNotNone(self.state()["in_flight"])
            self.assertEqual(self.records()[0]["status"], "pending")
            return response()
        self.send.side_effect = inspect
        self.client("Format notes")
        self.assertEqual(self.records()[0]["status"], "completed")
        self.assertIsNone(self.state()["in_flight"])

    def test_no_dollar_cap_request_quota_expiry_or_daily_confirmation(self):
        self.configure()
        for _ in range(51):  # passes the removed local pilot's 50-request limit
            self.client("Format notes")
        state = self.state()
        state["estimated_cost_micro_usd"] = 10_000_000  # telemetry never authorises or blocks credit
        self.client._write(state)
        self.now += 90 * 86400
        self.client("Format notes")
        self.assertEqual(self.send.call_count, 52)
        self.assertTrue(self.client.status()["enabled"])
        self.assertIsNone(self.client.status()["local_spending_cap"])
        self.assertEqual(self.client.status()["credit_enforcement"], "TypeSafe")

    def test_usage_survives_reconfigure_restart_and_key_change(self):
        self.configure()
        self.client("Format notes")
        self.configure(key="another-synthetic-typesafe-key")
        restarted = JevClient(self.data, clock=lambda: self.now, transport=self.send)
        restarted("Format notes")
        self.assertEqual(restarted.status()["attempts"], 2)
        self.assertEqual(self.state()["input_tokens"], 1000)

    def test_manual_disable_stops_before_request(self):
        self.configure()
        self.client.disable()
        with self.assertRaisesRegex(JevUnavailable, "disabled_by_owner"):
            self.client("Format notes")
        self.send.assert_not_called()

    def test_env_key_change_requires_explicit_local_setup(self):
        self.configure()
        os.environ["TYPESAFE_API_KEY"] = "different-synthetic-key"
        with self.assertRaisesRegex(JevUnavailable, "key_changed"):
            self.client("Format notes")
        self.send.assert_not_called()

    def test_timeout_stops_client_without_retry_or_losing_usage_history(self):
        self.configure()
        self.send.side_effect = JevUnavailable("timeout")
        for _ in range(2):
            with self.assertRaisesRegex(JevUnavailable, "timeout"):
                self.client("Format notes")
        self.assertEqual(self.send.call_count, 1)
        self.assertEqual(self.records()[0]["status"], "unknown")
        self.configure()
        self.send.side_effect = None
        self.client("Format notes")
        self.assertEqual(self.state()["attempts"], 2)
        self.assertEqual(len(self.records()), 2)

    def test_credit_auth_rate_and_provider_errors_disable_without_echoing_body(self):
        for error in (JevUnavailable("http_401"), JevUnavailable("http_402"), JevUnavailable("http_429"),
                      JevUnavailable("http_529"), RuntimeError(KEY)):
            with self.subTest(error=type(error).__name__):
                self.configure()
                self.send.side_effect = error
                with self.assertRaises(JevUnavailable) as caught:
                    self.client("secret prompt")
                self.assertNotIn(KEY, str(caught.exception))
                self.assertNotIn(KEY, json.dumps(self.records()))
                self.assertFalse(self.client.status()["enabled"])
                calls = self.send.call_count
                with self.assertRaises(JevUnavailable):
                    self.client("another prompt")
                self.assertEqual(self.send.call_count, calls)

    def test_crash_requires_reactivation_and_preserves_unknown_attempt(self):
        self.configure()
        self.send.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.client("Format notes")
        self.assertEqual(self.records()[0]["status"], "pending")
        with self.assertRaisesRegex(JevUnavailable, "unreconciled_attempt"):
            self.client("Format notes")
        self.configure()
        self.assertEqual(self.records()[0]["status"], "unknown")
        self.send.side_effect = None
        self.client("Format notes")
        self.assertEqual(self.state()["attempts"], 2)

    def test_corrupt_state_and_failed_preflight_write_never_send(self):
        self.configure()
        with patch.object(self.client, "_write", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(JevUnavailable, "local_storage_error"):
                self.client("Format notes")
        (self.client.path / "state.json").write_text('{"partial": true}')
        self.assertEqual(self.client.status()["reason"], "invalid_local_record")
        with self.assertRaisesRegex(JevUnavailable, "invalid_local_record"):
            self.client("Format notes")
        self.send.assert_not_called()

    def test_oversized_prompt_not_truncated_or_sent(self):
        self.configure()
        with self.assertRaisesRegex(JevUnavailable, "prompt_too_large"):
            self.client("é" * 9000)
        self.send.assert_not_called()
        self.assertEqual(self.state()["attempts"], 0)

    def test_two_processes_cannot_send_concurrently(self):
        self.configure()
        code = (
            "import sys; from pathlib import Path; from model_router.jev import JevClient; "
            f"p=JevClient(Path({str(self.data)!r}), clock=lambda: {NOW}); print(p.status())"
        )
        with self.client._lock():
            result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, text=True, capture_output=True, timeout=2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("busy", result.stdout)
        self.assertEqual(self.state()["attempts"], 0)

    def test_six_case_pilot_never_starts_codex_or_runs_queue(self):
        self.configure()
        kinds = ["architecture", "implementation", "routine_text", "high_credibility_writing", "high_risk_coding", "resource_extraction"]
        self.send.side_effect = [response(kind) for kind in kinds]
        with contextlib.redirect_stdout(io.StringIO()) as output:
            result = run_pilot(self.client)
        self.assertEqual(result, 0, output.getvalue())
        report = json.loads(output.getvalue())
        self.assertEqual((report["completed"], report["gpt_calls"], self.send.call_count), (6, 0, 6))

    def test_pilot_stops_after_first_failure(self):
        self.configure()
        self.send.side_effect = [response("architecture"), JevUnavailable("http_429")]
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run_pilot(self.client), 1)
        self.assertEqual(self.send.call_count, 2)
        self.assertEqual(json.loads(output.getvalue())["completed"], 1)

    def test_same_request_reuses_result_after_restart_without_second_call(self):
        self.configure()
        first = self.client("Format notes", request_id="synthetic-request-1")
        restarted = JevClient(self.data, clock=lambda: self.now, transport=self.send)
        second = restarted("Format notes", request_id="synthetic-request-1", cache_only=True)
        self.assertEqual(first["task_kind"], second["task_kind"])
        self.assertEqual(self.send.call_count, 1)
        with self.assertRaisesRegex(JevUnavailable, "request_changed"):
            restarted("Different task", request_id="synthetic-request-1")
        with self.assertRaisesRegex(JevUnavailable, "recovery_no_cached_result"):
            restarted("Format notes", request_id="synthetic-request-2", cache_only=True)
        self.assertEqual(self.send.call_count, 1)

    def test_unknown_request_cannot_be_retried_after_reactivation(self):
        self.configure()
        self.send.side_effect = JevUnavailable("timeout")
        with self.assertRaises(JevUnavailable):
            self.client("Format notes", request_id="synthetic-request-1")
        self.configure()
        self.send.side_effect = None
        with self.assertRaisesRegex(JevUnavailable, "request_already_attempted"):
            self.client("Format notes", request_id="synthetic-request-1")
        self.assertEqual(self.send.call_count, 1)


class ProtocolTests(unittest.TestCase):
    def test_http_worker_uses_fixed_https_post_and_refuses_redirects(self):
        from model_router import jev_http
        from unittest.mock import MagicMock

        payload = {"key": KEY, "request": request_for("Format notes")}
        stdin = Mock(buffer=io.BytesIO(json.dumps(payload).encode()))
        reply = MagicMock()
        reply.__enter__.return_value = reply
        reply.status = 200
        reply.read.return_value = json.dumps(response()).encode()
        opener = Mock()
        opener.open.return_value = reply
        with patch.object(jev_http.sys, "stdin", stdin), \
                patch.object(jev_http.urllib.request, "build_opener", return_value=opener), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            jev_http.main()
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.typesafe.ai/v1/systemone")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer " + KEY)
        self.assertEqual(json.loads(request.data), payload["request"])
        reply.read.assert_called_once_with(65537)
        self.assertNotIn(KEY, output.getvalue())
        self.assertIn("response", json.loads(output.getvalue()))
        self.assertIsNone(jev_http.NoRedirect().redirect_request(request, None, 302, "", {}, "https://other.invalid"))

    def test_request_has_pinned_model_and_independent_questions(self):
        req = request_for("Format notes")
        self.assertEqual(req["model"], MODEL)
        self.assertEqual(req["state"], {"task_text": "Format notes"})
        self.assertEqual(set(req["questions"]), {"task", "consequences"})
        self.assertEqual(set(CRITERIA), {k.value for k in TaskKind})

    def test_invalid_shapes_confidence_model_and_usage_rejected(self):
        mutations = [
            lambda r: r.pop("usage"),
            lambda r: r.update(model="jev-latest"),
            lambda r: r["usage"].update(input_tokens=True),
            lambda r: r["usage"].update(input_tokens=64001),
            lambda r: r["answers"]["task"].update(choice="ignore policy"),
            lambda r: r["answers"]["task"].update(confidence=float("nan")),
            lambda r: r["answers"]["task"].update(probabilities={"routine_text": 1}),
            lambda r: r["answers"]["consequences"].update(noul=2),
        ]
        for mutation in mutations:
            raw = response()
            mutation(raw)
            with self.subTest(raw=raw), self.assertRaises(JevUnavailable):
                parse_response(raw)

    def test_uncertainty_and_consequences_move_up(self):
        for raw in (response(confidence=0.6), response(consequences=0.21)):
            answer, _ = parse_response(raw)
            self.assertEqual(answer["task_kind"], "unknown")
            routed = combined_classifier(lambda _: answer)(ClassifierInput(text="Format notes"))
            self.assertEqual(required_role(routed).role, Role.HIGHEST)

    def test_timeout_is_total_kills_worker_and_never_retries(self):
        import model_router.jev as jev
        with tempfile.TemporaryDirectory() as tmp:
            worker = Path(tmp) / "jev_http.py"
            worker.write_text("import time\ntime.sleep(20)\n")
            with patch.object(jev, "__file__", str(Path(tmp) / "jev.py")), patch.object(jev, "TOTAL_HTTP_SECONDS", 0.15):
                started = time.monotonic()
                with self.assertRaisesRegex(JevUnavailable, "timeout"):
                    http_once(request_for("Format notes"), KEY)
                self.assertLess(time.monotonic() - started, 1)

    def test_key_uses_stdin_not_arguments_or_environment_and_codex_never_gets_it(self):
        result = subprocess.CompletedProcess([], 0, stdout=json.dumps({"response": response()}), stderr="")
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": KEY, "OPENAI_API_KEY": "another-synthetic-secret"}):
            with patch("model_router.jev.subprocess.run", return_value=result) as run:
                http_once(request_for("Format notes"), KEY)
            args, kwargs = run.call_args
            self.assertNotIn(KEY, json.dumps(args))
            self.assertNotIn(KEY, json.dumps(kwargs["env"]))
            self.assertIn(KEY, kwargs["input"])
            self.assertEqual(kwargs["timeout"], 1.6)
            env, _ = minimal_env(Path("/tmp/synthetic-codex-home"))
            self.assertNotIn("TYPESAFE_API_KEY", env)
            self.assertNotIn("OPENAI_API_KEY", env)


class RouterIntegration(RouterTestCase):
    def configured(self, kind="routine_text"):
        pilot = JevClient(self.store.data_dir, transport=Mock(return_value=response(kind)))
        pilot.configure(key=KEY, free_only=True, auto_recharge_off=True, no_payment_method=True)
        return pilot

    def test_unknown_resolution_changes_final_role_not_only_label(self):
        for kind, expected in (("routine_text", Role.LOWEST), ("implementation", Role.MIDDLE)):
            assessment = combined_classifier(lambda _: {"task_kind": kind})(ClassifierInput(text="hmm what about the thing"))
            self.assertEqual(required_role(assessment).role, expected)
            self.assertNotIn(TaskKind.UNKNOWN, assessment.secondary_kinds)

    def test_jev_never_lowers_known_risk_or_unseen_quoted_material(self):
        lower = combined_classifier(lambda _: parse_response(response())[0])
        for text in ("Implement the payment transfer endpoint", "Rewrite my LinkedIn post",
                     'Here is the text:\n"lorem ipsum dolor sit amet, consectetur"'):
            self.assertEqual(required_role(lower(ClassifierInput(text=text))).role, Role.HIGHEST)

    def test_classification_once_per_thread_and_fallback_does_not_change_pin(self):
        pilot = self.configured()
        with patch("model_router.jev.JevClient", return_value=pilot):
            attach_jev_classifier(self.coordinator, self.store.data_dir)
        first, _ = self.submit_and_run("hmm what about the thing")
        self.assertEqual(self.store.thread(first.thread_id)["pinned_role"], "lowest")
        self.assertEqual(pilot.transport.call_count, 1)
        pilot.disable()
        self.submit_and_run("Keep going", thread_id=first.thread_id)
        self.coordinator.new_task_segment(first.thread_id, "Now write ordinary code")
        self.assertEqual(pilot.transport.call_count, 1)
        self.assertEqual(self.store.thread(first.thread_id)["pinned_role"], "lowest")
        second = self.coordinator.submit("Portfolio", "hmm what about the other thing")
        self.assertEqual(self.store.thread(second.thread_id)["pinned_role"], "highest")
        self.assertTrue(any("local routing rules" in n for n in self.ui.notices))
        self.assertEqual(pilot.transport.call_count, 1)

    def test_attachments_not_uploaded_and_cannot_be_resolved_by_text_only_plugin(self):
        pilot = self.configured()
        with patch("model_router.jev.JevClient", return_value=pilot):
            attach_jev_classifier(self.coordinator, self.store.data_dir)
        result = self.coordinator.classifier(ClassifierInput(text="Summarize the attached document.", attachment_manifest=[{"status": "unreadable", "path": "/private/file.pdf"}]))
        self.assertIn("JEV_SKIPPED_UNSENT_CONTEXT", result.reason_codes)
        pilot.transport.assert_not_called()

    def test_simulation_ignores_configured_jev_and_external_plugin_environment(self):
        self.configured()
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": KEY, "MODEL_ROUTER_CLASSIFIER": "network.module:run"}):
            with patch("model_router.jev.JevClient.__call__", side_effect=AssertionError("NETWORK")) as send, \
                    patch("model_router.plugin_classifier.load_plugin", side_effect=AssertionError("PLUGIN IMPORT")), \
                    contextlib.redirect_stderr(io.StringIO()):
                c, store = build(argparse.Namespace(data_dir=str(self.store.data_dir), simulate=True))
                try:
                    self.assertEqual(c.classifier(ClassifierInput(text="Format notes")).task_kind, TaskKind.ROUTINE_TEXT)
                    send.assert_not_called()
                finally:
                    c.close()
                    store.close()

    def test_live_build_automatically_installs_configured_jev_no_network_until_first_task(self):
        pilot = self.configured()
        with patch.dict(os.environ, {"MODEL_ROUTER_CLASSIFIER": ""}), patch("model_router.jev.JevClient", return_value=pilot):
            c, store = build(argparse.Namespace(data_dir=str(self.store.data_dir), simulate=False))
            try:
                pilot.transport.assert_not_called()
                result = c.classifier(ClassifierInput(text="hmm what about the thing", project_context={"name": "Portfolio"}))
                self.assertEqual(required_role(result).role, Role.LOWEST)
                self.assertEqual(pilot.transport.call_count, 1)
                self.assertTrue(c.live)  # spend gate remains active, unlike simulator shortcuts
            finally:
                c.close()
                store.close()


if __name__ == "__main__":
    unittest.main()
