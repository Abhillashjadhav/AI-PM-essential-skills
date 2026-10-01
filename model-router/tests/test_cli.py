"""The terminal entry point, run as a real subprocess."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT

ROUTER = ROOT / "router.py"


def run(*args, stdin=None, env=None, timeout=120):
    return subprocess.run(
        [sys.executable, str(ROUTER), *args], input=stdin, capture_output=True, text=True, timeout=timeout,
        env={**os.environ, **(env or {})},
    )


class Cli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data = Path(self._tmp.name) / "data"
        self.project = Path(self._tmp.name) / "project"
        self.project.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_help(self):
        result = run("--help")
        self.assertEqual(result.returncode, 0)
        for command in ("doctor", "demo", "chat", "threads", "resume", "models", "eval", "status", "serve"):
            self.assertIn(command, result.stdout)

    def test_demo(self):
        result = run("demo")
        self.assertEqual(result.returncode, 0, result.stderr)
        for expected in (
            "SIMULATED DEMO",
            "Router: Highest reasoning — architecture decision. Model stays fixed for this chat.",
            "Router: Architecture saved. Opening implementation in this project.",
            "Router: Middle reasoning — implementation from the agreed architecture.",
            "Router: Included usage is unavailable. Work is saved.",
            "Router: Using the approved lower model for this new coding chat:",
            "repeated finalise → EXISTING",
            "(no blind resend)",
        ):
            self.assertIn(expected, result.stdout)

    def test_doctor_without_codex_is_blocked_not_failed(self):
        result = run("doctor", "--data-dir", str(self.data), "--no-connect", env={"PATH": "/usr/bin:/bin"})
        self.assertEqual(result.returncode, 0)
        self.assertIn("BLOCKED   codex cli", result.stdout)
        self.assertIn("Live model sends stay blocked", result.stdout)

    def test_simulated_chat_session(self):
        base = ["--data-dir", str(self.data), "--simulate"]
        self.assertEqual(run("project", "add", "--name", "Portfolio", "--path", str(self.project), *base).returncode, 0)
        setup = run("models", "list", *base)
        self.assertIn("not set up", setup.stdout)
        # approve a middle and lowest mapping through the CLI's two-step flow
        for role, model, effort in (("lowest", "sim-luna-1", "low"), ("highest", "sim-astra-1", "high")):
            review = run("models", "approve", "--role", role, "--model", model, "--effort", effort, *base)
            confirm = review.stdout.split("--confirm ")[1].split()[0]
            done = run("models", "approve", "--role", role, "--model", model, "--effort", effort, "--confirm", confirm, *base)
            self.assertIn("approved", done.stdout)
        chat = run("chat", "--project", "Portfolio", *base, stdin="Format my private notes into bullets\n/history\n/done resolved 5\n/quit\n")
        self.assertEqual(chat.returncode, 0, chat.stderr)
        self.assertIn("Router: Lowest reasoning — routine text work. Model stays fixed for this chat.", chat.stdout)
        self.assertIn("[SIMULATED sim-luna-1]", chat.stdout)
        self.assertIn("recorded resolved", chat.stdout)
        threads = run("threads", *base)
        thread_id = threads.stdout.split()[0]
        self.assertIn("sim-luna-1", threads.stdout)
        resumed = run("resume", thread_id, *base, stdin="and shorter\n/quit\n")
        self.assertIn("continuing chat", resumed.stdout)
        self.assertIn("[SIMULATED sim-luna-1]", resumed.stdout)
        changed = run("model", "set", thread_id, "sim-astra-1", "--reason", "quality", *base)
        self.assertIn("moves from sim-luna-1 to sim-astra-1", changed.stdout)
        report = run("eval", "report", *base)
        self.assertIn("Owner guardrail", report.stdout)
        offline = run("eval", "run", "--offline", *base)
        self.assertIn("Offline evaluation PASSED", offline.stdout)
        status = run("status", *base)
        self.assertIn('"live": false', status.stdout)
        self.assertIn("runs only while a router process is open", status.stdout, "chat ran the auto-resumer")


if __name__ == "__main__":
    unittest.main()
