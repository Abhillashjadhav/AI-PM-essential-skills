"""Executable terminal UX and handoff regression checks; synthetic data only."""
import argparse
import contextlib
import io
import json
import sqlite3
import unittest
from unittest.mock import patch

from helpers import RouterTestCase
from model_router.cli import _chat_command, _chat_loop, cmd_start, parser
import test_cli as cli_tests

run = cli_tests.run


class StartCommand(unittest.TestCase):
    def test_live_start_never_starts_chat_if_existing_setup_blocks(self):
        args = parser().parse_args(["start", "--path", "."])
        with patch("model_router.cli.sys.stdin.isatty", return_value=True), \
                patch("model_router.jev.JevClient.status", return_value={"enabled": False, "reason": "timeout"}), \
                patch("model_router.cli.cmd_setup", return_value=3), \
                patch("model_router.cli.build", side_effect=AssertionError("chat must not start")), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cmd_start(args), 3)
        self.assertIn("Jev is off (timeout)", output.getvalue())
        self.assertIn("normal Codex chat box is not connected", output.getvalue())
        self.assertIn("live chat was not started", output.getvalue())

    def test_noninteractive_live_start_never_runs_setup_or_sends(self):
        args = parser().parse_args(["start", "--path", "."])
        with patch("model_router.cli.sys.stdin.isatty", return_value=False), \
                patch("model_router.cli.cmd_setup", side_effect=AssertionError("no login/approval")), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cmd_start(args), 2)


class InteractiveStart(unittest.TestCase):
    # Reuse temporary paths and subprocess helper, without inheriting test cases.
    setUp = cli_tests.Cli.setUp
    tearDown = cli_tests.Cli.tearDown
    def test_start_simulation_routes_new_chats_and_pins_followups(self):
        result = run("start", "--simulate", "--path", str(self.project), "--data-dir", str(self.data),
                     stdin="Format my private notes into bullets\nMake them shorter\n/new\nReview the architecture for a reporting app\n/new\nImplement the CSV export per the agreed architecture\n/quit\n", timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SIMULATED INTERACTIVE DEMO", result.stdout)
        for model in ("sim-luna-1", "sim-astra-1", "sim-sol-1"):
            self.assertIn("selected model: " + model, result.stdout)
        self.assertEqual(result.stdout.count("selected model:"), 3)
        db = sqlite3.connect(self.data / "simulator" / "router.sqlite3")
        try:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM threads").fetchone()[0], 3)
        finally:
            db.close()
        self.assertFalse((self.data / "router.sqlite3").exists())

    def test_start_reuses_project_but_refuses_name_collision(self):
        args = ("start", "--simulate", "--project", "Trial", "--path", str(self.project), "--data-dir", str(self.data))
        for _ in range(2):
            result = run(*args, stdin="/quit\n", timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
        result = run("start", "--simulate", "--project", "Trial", "--path", str(self.project.parent),
                     "--data-dir", str(self.data), stdin="/quit\n", timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertIn("different folder", result.stdout)

    def test_start_rejects_missing_folder_without_setup(self):
        result = run("start", "--path", str(self.project / "missing"), "--data-dir", str(self.data), stdin="")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.data.exists())


class ActiveChatHandoff(RouterTestCase):
    def args(self):
        return argparse.Namespace(project="Portfolio", simulate=True)

    def test_approval_text_focuses_implementation_for_next_message(self):
        architecture = self.architecture_thread()
        with patch("builtins.input", side_effect=["Approved, implement this.", "Continue writing the code.", "/quit"]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(_chat_loop(self.args(), self.coordinator, self.store, None, architecture), 0)
        implementation = self.store.one("SELECT id FROM threads WHERE kind='implementation'")["id"]
        self.assertTrue(any(m["content"] == "Continue writing the code." for m in self.store.messages(implementation)))
        self.assertFalse(any(m["content"] == "Continue writing the code." for m in self.store.messages(architecture)))
        self.assertEqual(self.store.thread(architecture)["pinned_model"], "sim-astra-1")
        self.assertEqual(self.store.thread(implementation)["pinned_model"], "sim-sol-1")

    def test_finalise_command_returns_implementation_as_active_chat(self):
        architecture = self.architecture_thread()
        active, stop = _chat_command(self.coordinator, "/finalise", architecture, [], self.args())
        self.assertFalse(stop)
        self.assertNotEqual(active, architecture)
        self.assertEqual(self.store.thread(active)["kind"], "implementation")
        self.assertEqual(self.store.thread(architecture)["pinned_model"], "sim-astra-1")

    def test_held_handoff_does_not_change_active_chat(self):
        architecture = self.submit_and_run("Review this architecture.")[0].thread_id
        active, stop = _chat_command(self.coordinator, "/finalise", architecture, [], self.args())
        self.assertEqual(active, architecture)
        self.assertFalse(stop)

    def test_new_chat_preserves_previous_thread_and_does_not_send(self):
        previous = self.submit_and_run("Format my private notes into bullets")[0].thread_id
        sends = self.adapter.model_sends
        active, stop = _chat_command(self.coordinator, "/new", previous, [], self.args())
        self.assertIsNone(active)
        self.assertFalse(stop)
        self.assertEqual(self.store.thread(previous)["pinned_model"], "sim-luna-1")
        self.assertEqual(self.adapter.model_sends, sends)

    def test_new_chat_does_not_discard_or_reassign_pending_attachments(self):
        previous = self.submit_and_run("Format my private notes into bullets")[0].thread_id
        pending = ["/synthetic/resume.txt"]
        active, _ = _chat_command(self.coordinator, "/new", previous, pending, self.args())
        self.assertEqual(active, previous)
        self.assertEqual(pending, ["/synthetic/resume.txt"])


if __name__ == "__main__":
    unittest.main()
