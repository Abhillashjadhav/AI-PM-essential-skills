#!/usr/bin/env python3
"""Run the ticket-summarizer contract-to-release terminal demonstration."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
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


def invoke(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["pm-verifier", *args],
        cwd=cwd,
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


def command_output(completed: subprocess.CompletedProcess[str]) -> None:
    for line in completed.stdout.splitlines():
        show(line)


def main() -> int:
    global PLAIN
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--record",
        action="store_true",
        help="pace output for a roughly 54-second recording (36 seconds at 1.5x)",
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

    contract = (source / "EVAL_CONTRACT.md").read_text(encoding="utf-8")
    contract_normalized = " ".join(contract.split())
    required_contract_facts = (
        "without inventing facts",
        "losing the escalation reason",
        "wrong order",
        "Outcome: required response",
        "Trajectory: the ticket messages",
        "System and memory are not enabled",
    )
    if not all(fact in contract_normalized for fact in required_contract_facts):
        show("The checked-in eval contract no longer matches this demonstration", RED)
        return 2

    with tempfile.TemporaryDirectory(prefix="ticket-eval-") as directory:
        workspace = Path(directory)
        project = workspace / "eval"
        shutil.copytree(source, project)
        suite = load(project / "suite.json")
        cases = load_rows(project / "cases.jsonl")
        case_count = len(cases)
        minimum_trials = int(suite["minimum_trials_per_case"])
        trial_count = case_count * minimum_trials
        graders = suite["deterministic_graders"]
        grader_count = len(graders)
        rules = suite["release_rules"]

        show("AI TICKET SUMMARIZER — PRODUCT CONTRACT TO RELEASE DECISION", CYAN + BOLD)
        show("Repository: AI-PM-essential-skills / pm-verifier")
        show("Goal: make the release decision reproducible, not demo-driven")
        wait(args.record, 3)

        show()
        show("1 / READ THE PRODUCT CONTRACT", CYAN + BOLD)
        show("Release question:")
        show("  Can it summarise without invented facts, lost escalation, or reversed order?")
        show("Product response: summary + customer_request JSON")
        show("Enabled surfaces: outcome + trajectory")
        show("System + memory omitted: the feature makes neither promise", DIM)
        wait(args.record, 5)

        show()
        show("2 / TURN THE CONTRACT INTO PRODUCT USE CASES", CYAN + BOLD)
        for case in cases:
            workflow = str(case["metadata"]["workflow"]).replace("_", " ")
            risk = case["metadata"]["risk"]
            show(f"  {case['case_id']} · {workflow} · risk={risk}")
        show(f"Each use case runs {minimum_trials} times in a fresh adapter process")
        show(f"Evidence target: {case_count} use cases · {trial_count} isolated runs")
        wait(args.record, 5)

        show()
        show("3 / COMPILE THE RELEASE GATES", CYAN + BOLD)
        for grader in graders:
            show(f"  {grader['id']:<25} {grader['name']}")
        show(
            "Operational ceilings: "
            f"{rules['max_latency_ms_per_trial']} ms · "
            f"{rules['max_total_tokens_per_trial']} tokens · "
            f"{rules['max_retries_per_trial']} retries"
        )
        wait(args.record, 6)

        trials = project / "trials.executed.jsonl"
        clean_results = project / "results.clean.json"
        show()
        show("4 / CAPTURE FRESH EVIDENCE", CYAN + BOLD)
        show(
            "$ pm-verifier execute --project eval --trials-out trials.executed.jsonl "
            "--results-out results.clean.json -- python3 eval/reference_adapter.py",
            DIM,
        )
        captured = invoke(
            [
                "execute",
                "--project",
                "eval",
                "--trials-out",
                trials.name,
                "--results-out",
                clean_results.name,
                "--",
                "python3",
                "eval/reference_adapter.py",
            ],
            cwd=workspace,
        )
        command_output(captured)
        if captured.returncode != 0 or not clean_results.is_file():
            show(captured.stderr.strip() or "Evidence capture failed", RED)
            return 2
        captured_rows = load_rows(trials)
        isolation_ids = {row["isolation_id"] for row in captured_rows}
        if len(captured_rows) != trial_count or len(isolation_ids) != trial_count:
            show("Captured evidence did not preserve unique trial isolation", RED)
            return 2
        show(f"Verified: {len(captured_rows)} runs · {len(isolation_ids)} unique isolation IDs", GREEN)
        wait(args.record, 6)

        faulted = project / "trials.fabricated.jsonl"
        failed_results = project / "results.failed.json"
        show()
        show("5 / BREAK ONE PRODUCT REQUIREMENT", CYAN + BOLD)
        show("Use case: TS-100 · blocked August invoice export")
        show('Injected unsupported claim: "Customer was charged twice"', RED)
        show(
            "$ pm-verifier fault --project eval --trials trials.executed.jsonl "
            "--name fabricated-claim --out trials.fabricated.jsonl",
            DIM,
        )
        created = invoke(
            [
                "fault",
                "--project",
                "eval",
                "--trials",
                trials.name,
                "--name",
                "fabricated-claim",
                "--out",
                faulted.name,
            ],
            cwd=workspace,
        )
        command_output(created)
        if created.returncode != 0:
            show(created.stderr.strip() or "Fault injection failed", RED)
            return 2
        wait(args.record, 5)

        show()
        show("6 / RUN THE SAME CONTRACT", CYAN + BOLD)
        show(
            "$ pm-verifier run --project eval --trials eval/trials.fabricated.jsonl "
            "--out eval/results.failed.json",
            DIM,
        )
        failed_run = invoke(
            [
                "run",
                "--project",
                "eval",
                "--trials",
                "eval/trials.fabricated.jsonl",
                "--out",
                "eval/results.failed.json",
            ],
            cwd=workspace,
        )
        command_output(failed_run)
        failed = load(failed_results)
        failed_trial = next(
            trial for trial in failed["trials"] if any(not gate["passed"] for gate in trial["gate_results"])
        )
        failed_gate = next(
            gate for gate in failed_trial["gate_results"] if not gate["passed"] and gate["gate"]
        )
        actual_claims = failed_gate.get("actual", [])
        expected_claims = failed_gate.get("expected", [])
        unsupported_claims = [claim for claim in actual_claims if claim not in expected_claims]
        if failed["decision"] != "FAIL" or not unsupported_claims:
            show("The fault did not produce the expected release failure", RED)
            return 2
        show(f"RELEASE DECISION: {failed['decision']}", RED + BOLD)
        show(f"Failed use case: {failed_trial['case_id']} · trial={failed_trial['trial_id']}")
        show(f"Failed gate: {failed_gate['grader_id']} · claims grounded in source thread")
        show(f"Reason: unsupported claim · {unsupported_claims[0]}", RED)
        show("A plausible summary is still unshippable when one claim is fabricated")
        wait(args.record, 6)

        show()
        show("7 / REMOVE THE FAULT AND RE-RUN", CYAN + BOLD)
        repaired_results = project / "results.repaired.json"
        show(
            "$ pm-verifier run --project eval --trials eval/trials.executed.jsonl "
            "--out eval/results.repaired.json",
            DIM,
        )
        repaired_run = invoke(
            [
                "run",
                "--project",
                "eval",
                "--trials",
                "eval/trials.executed.jsonl",
                "--out",
                "eval/results.repaired.json",
            ],
            cwd=workspace,
        )
        command_output(repaired_run)
        if repaired_run.returncode != 0:
            show(repaired_run.stderr.strip() or "Repaired run failed", RED)
            return 2
        repaired = load(repaired_results)
        for grader in graders:
            gate_passed = all(
                next(
                    result["passed"]
                    for result in trial["gate_results"]
                    if result["grader_id"] == grader["id"]
                )
                for trial in repaired["trials"]
            )
            if not gate_passed:
                show(f"  FAIL {grader['id']}", RED)
                return 2
            show(f"  PASS {grader['id']:<25} {grader['name']}", GREEN)
        wait(args.record, 8)

        summary = repaired["summary"]
        show()
        show("8 / RELEASE EVIDENCE", CYAN + BOLD)
        show(f"RELEASE DECISION: {repaired['decision']}", GREEN + BOLD)
        show(f"Product use cases: {summary['case_count']}")
        show(f"Fresh isolated runs: {summary['trial_count']}")
        show(f"Deterministic release gates: {grader_count}")
        show("Outcome PASS · Trajectory PASS", GREEN)
        show(
            f"Safety failures {summary['safety_failures']} · "
            f"Privacy failures {summary['privacy_failures']} · "
            f"Retries {repaired['metrics']['retries']}",
            GREEN,
        )
        show("Copy the starter. Replace its contract, use cases, and adapter.")
        show("Deterministic demo data; production evidence comes from your adapter.", DIM)
        wait(args.record, 9)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
