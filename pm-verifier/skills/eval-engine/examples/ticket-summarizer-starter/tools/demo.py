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
PLAIN = False


def show(text: str = "", style: str = "") -> None:
    print(text if PLAIN else f"{style}{text}{RESET}", flush=True)


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


def load_rows(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    global PLAIN
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--record",
        action="store_true",
        help="pace output for a roughly 55-second recording (about 36 seconds at 1.5x)",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="use only the terminal's existing foreground and background colours",
    )
    args = parser.parse_args()
    PLAIN = args.plain

    source = Path(__file__).resolve().parents[1]
    if shutil.which("pm-verifier") is None:
        print("Install first: python3 -m pip install --no-deps ./pm-verifier")
        return 2

    with tempfile.TemporaryDirectory(prefix="ticket-eval-") as directory:
        project = Path(directory) / "eval"
        shutil.copytree(source, project)
        suite = load(project / "suite.json")
        case_count = sum(
            1 for line in (project / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()
        )
        trial_count = case_count * int(suite["minimum_trials_per_case"])
        grader_count = len(suite["deterministic_graders"])

        show("AI TICKET SUMMARIZER — SPEC TO RELEASE EVIDENCE", CYAN + BOLD)
        show(
            f"{case_count} synthetic cases · {suite['minimum_trials_per_case']} trials each · "
            f"{grader_count} deterministic gates"
        )
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
        captured_rows = load_rows(trials)
        isolation_ids = {row["isolation_id"] for row in captured_rows}
        if len(captured_rows) != trial_count or len(isolation_ids) != trial_count:
            show("Captured evidence did not preserve unique trial isolation")
            return 2
        show(f"Captured {len(captured_rows)} fresh trials with unique isolation IDs", GREEN)
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
        failed_gate = next(
            gate
            for trial in failed["trials"]
            for gate in trial["gate_results"]
            if not gate["passed"] and gate["gate"]
        )
        actual_claims = failed_gate.get("actual", [])
        expected_claims = failed_gate.get("expected", [])
        unsupported_claims = [
            claim
            for claim in actual_claims
            if claim not in expected_claims
        ]
        if not unsupported_claims:
            show("Failed gate did not expose the unsupported claim", RED)
            return 2
        show(
            f"Caught: {failed_gate['grader_id']} — unsupported claim: "
            f"{unsupported_claims[0]}",
            RED,
        )
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
            f"{grader_count} deterministic gates",
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
