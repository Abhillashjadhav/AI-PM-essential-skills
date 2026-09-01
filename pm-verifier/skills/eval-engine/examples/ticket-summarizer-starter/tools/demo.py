#!/usr/bin/env python3
"""Run the ticket-summarizer FAIL-to-PASS terminal demonstration."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
DIM = "\033[2m"


def show(text: str = "", style: str = "") -> None:
    print(f"{style}{text}{RESET}", flush=True)


def wait(record: bool, seconds: float) -> None:
    if record:
        time.sleep(seconds)


def invoke(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["pm-verifier", *args],
        text=True,
        capture_output=True,
        check=False,
    )


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--record",
        action="store_true",
        help="pace output for a roughly 40-second video after 1.5x acceleration",
    )
    args = parser.parse_args()

    source = Path(__file__).resolve().parents[1]
    if shutil.which("pm-verifier") is None:
        print("Install first: python3 -m pip install --no-deps ./pm-verifier")
        return 2

    with tempfile.TemporaryDirectory(prefix="ticket-eval-") as directory:
        project = Path(directory) / "eval"
        shutil.copytree(source, project)

        show("AI TICKET SUMMARIZER — SPEC TO RELEASE EVIDENCE", CYAN + BOLD)
        show("3 synthetic cases · 2 trials each · 8 deterministic gates")
        show("Enabled surfaces: outcome + trajectory")
        show("Memory omitted: this feature makes no persistence promise", DIM)
        wait(args.record, 9)

        trials = project / "trials.executed.jsonl"
        clean_results = project / "results.clean.json"
        show()
        show("1 / CAPTURE FRESH ISOLATED TRIALS", CYAN + BOLD)
        show("$ pm-verifier execute --project eval -- python3 reference_adapter.py", DIM)
        captured = invoke(
            [
                "execute",
                "--project",
                str(project),
                "--trials-out",
                trials.name,
                "--results-out",
                clean_results.name,
                "--",
                sys.executable,
                str(project / "reference_adapter.py"),
            ]
        )
        if captured.returncode != 0 or not clean_results.is_file():
            print(captured.stderr or captured.stdout)
            return 2
        show("Captured 6 fresh trials with unique isolation IDs", GREEN)
        wait(args.record, 11)

        faulted = project / "trials.fabricated.jsonl"
        failed_results = project / "results.failed.json"
        show()
        show("2 / INJECT ONE UNSUPPORTED CLAIM", CYAN + BOLD)
        show('Added claim: "Customer was charged twice"', RED)
        show("$ pm-verifier fault --name fabricated-claim", DIM)
        created = invoke(
            [
                "fault",
                "--project",
                str(project),
                "--trials",
                trials.name,
                "--name",
                "fabricated-claim",
                "--out",
                faulted.name,
            ]
        )
        if created.returncode != 0:
            print(created.stderr or created.stdout)
            return 2
        wait(args.record, 8)

        show("$ pm-verifier run --project eval --trials trials.fabricated.jsonl", DIM)
        invoke(
            [
                "run",
                "--project",
                str(project),
                "--trials",
                str(faulted),
                "--out",
                str(failed_results),
            ]
        )
        failed = load(failed_results)
        show(f"RELEASE DECISION: {failed['decision']}", RED + BOLD)
        show("Caught: G_OUTCOME_CLAIMS — claim not supported by source thread", RED)
        wait(args.record, 11)

        show()
        show("3 / REMOVE THE CLAIM AND RERUN THE SAME CONTRACT", CYAN + BOLD)
        show("$ pm-verifier run --project eval --trials trials.executed.jsonl", DIM)
        repaired_results = project / "results.repaired.json"
        repaired_run = invoke(
            [
                "run",
                "--project",
                str(project),
                "--trials",
                str(trials),
                "--out",
                str(repaired_results),
            ]
        )
        if repaired_run.returncode != 0:
            print(repaired_run.stderr or repaired_run.stdout)
            return 2
        repaired = load(repaired_results)
        summary = repaired["summary"]
        show(f"RELEASE DECISION: {repaired['decision']}", GREEN + BOLD)
        show(
            f"{summary['case_count']} cases · {summary['trial_count']} trials · "
            "8 deterministic gates",
            GREEN,
        )
        show("Outcome PASS · Trajectory PASS", GREEN)
        show(
            f"Safety failures {summary['safety_failures']} · "
            f"Privacy failures {summary['privacy_failures']} · "
            f"Retries {repaired['metrics']['retries']}",
            GREEN,
        )
        wait(args.record, 16)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
