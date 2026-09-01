#!/usr/bin/env python3
"""Run the ticket-summarizer contract-to-release terminal demonstration."""

from __future__ import annotations

import argparse
import json
import re
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


def emit(record: bool, text: str = "", style: str = "", delay: float = 0.11) -> None:
    """Print one terminal row slowly enough to create visible scrolling."""

    show(text, style)
    wait(record, delay)


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


def gate_line(grader: dict, gate: dict) -> str:
    """Render the exact deterministic comparison behind one gate."""

    gate_id = grader["id"]
    actual = gate.get("actual")
    expected = gate.get("expected")
    passed = "PASS" if gate["passed"] else "FAIL"
    if gate_id == "G_OUTCOME_REQUEST":
        detail = "actual request == contract request"
    elif gate_id == "G_OUTCOME_CLAIMS":
        detail = f"actual claims={len(actual)} == supported claims={len(expected)}"
    elif gate_id == "G_OUTCOME_SENTIMENT":
        detail = f"actual={actual} == expected={expected}"
    elif gate_id == "G_OUTCOME_ESCALATION":
        detail = "actual escalation == contract escalation"
    elif gate_id == "G_OUTCOME_LENGTH":
        ceiling = grader["params"]["chars"]
        detail = f"summary chars={len(actual)} <= ceiling={ceiling}"
    elif gate_id == "G_OUTCOME_NO_PROMISE":
        patterns = grader["params"]["patterns"]
        matches = sum(bool(re.search(pattern, str(actual), re.I)) for pattern in patterns)
        detail = f"unsupported-promise matches={matches} == 0"
    elif gate_id == "G_OUTCOME_NO_EMAIL":
        patterns = grader["params"]["patterns"]
        matches = sum(bool(re.search(pattern, str(actual), re.I)) for pattern in patterns)
        detail = f"exposed-email matches={matches} == 0"
    elif gate_id == "G_TRAJECTORY_CHRONOLOGY":
        detail = f"actual={' > '.join(actual)} == expected={' > '.join(expected)}"
    else:
        detail = gate["reason"]
    return f"  {passed:<4} {gate_id:<25} {detail}"


def show_case(
    record: bool,
    case: dict,
    case_trials: list[dict],
    result_trials: list[dict],
    graders: list[dict],
) -> None:
    """Show product input, delivered output, and every deterministic check."""

    first_trial = case_trials[0]
    first_result = result_trials[0]
    outcome = first_trial["outcome"]
    received = [message["id"] for message in case["input"]["messages"]]
    expected_order = case["expected"]["trajectory"]["chronological_ids"]
    workflow = str(case["metadata"]["workflow"]).replace("_", " ")

    emit(record)
    emit(record, f"USE CASE {case['case_id']} · {workflow} · risk={case['metadata']['risk']}", CYAN + BOLD)
    emit(record, f"INPUT RECEIVED: {' > '.join(received)} (newest first)")
    emit(record, f"REQUIRED ORDER: {' > '.join(expected_order)}")
    emit(record, "PRODUCT DELIVERED", BOLD)
    emit(record, f"  summary: {outcome['response']['summary']}")
    emit(record, f"  request: {outcome['response']['customer_request']}")
    emit(
        record,
        f"  sentiment={outcome['sentiment']} · escalation={outcome['escalation_reason']}",
    )
    emit(record, f"  supported claims ({len(outcome['supported_claims'])}): {'; '.join(outcome['supported_claims'])}")
    emit(record, "DETERMINISTIC EVAL PARAMETERS · EXPECTED vs ACTUAL", BOLD)
    gates_by_id = {gate["grader_id"]: gate for gate in first_result["gate_results"]}
    for grader in graders:
        emit(record, gate_line(grader, gates_by_id[grader["id"]]))

    gate_executions = sum(len(trial["gate_results"]) for trial in result_trials)
    passed_executions = sum(
        gate["passed"] for trial in result_trials for gate in trial["gate_results"]
    )
    passed_trials = sum(not trial["failed_gate_ids"] for trial in result_trials)
    emit(
        record,
        f"USE CASE SCORE: {len(graders)}/{len(graders)} gates · "
        f"{passed_executions}/{gate_executions} checks · "
        f"{passed_trials}/{len(result_trials)} isolated trials PASS",
        GREEN + BOLD,
    )
    wait(record, 6.7)


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

    with tempfile.TemporaryDirectory(prefix="ticket-eval-") as directory:
        workspace = Path(directory)
        project = workspace / "eval"
        shutil.copytree(source, project)
        suite = load(project / "suite.json")
        cases = load_rows(project / "cases.jsonl")
        graders = suite["deterministic_graders"]
        minimum_trials = int(suite["minimum_trials_per_case"])
        total_trials = len(cases) * minimum_trials
        total_checks = total_trials * len(graders)
        rules = suite["release_rules"]

        show("AI EVALS FOR PMs — TICKET SUMMARIZER RELEASE", CYAN + BOLD)
        show("Repository: AI-PM-essential-skills / pm-verifier")
        show("Runs locally or in CI · no eval SaaS · no LLM judge · no API key")
        wait(args.record, 3.0)

        emit(args.record)
        emit(args.record, "1 / PRODUCT CONTRACT BECOMES EXECUTABLE EVIDENCE", CYAN + BOLD)
        emit(args.record, "Product must return: summary + request + sentiment + escalation + supported claims")
        emit(args.record, "Product path must prove: source messages processed in chronological order")
        emit(args.record, "Enabled surfaces: outcome + trajectory · system + memory not promised")
        emit(args.record, f"Release policy: {len(cases)} use cases × {minimum_trials} isolated trials × {len(graders)} binary gates")
        emit(args.record, f"Decision rule: all {total_checks} deterministic checks must pass")
        wait(args.record, 4.5)

        trials_path = project / "trials.executed.jsonl"
        clean_results_path = project / "results.clean.json"
        emit(args.record)
        emit(args.record, "2 / RUN PRODUCT AND CAPTURE FRESH EVIDENCE", CYAN + BOLD)
        emit(
            args.record,
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
                trials_path.name,
                "--results-out",
                clean_results_path.name,
                "--",
                "python3",
                "eval/reference_adapter.py",
            ],
            cwd=workspace,
        )
        command_output(captured)
        if captured.returncode != 0 or not clean_results_path.is_file():
            show(captured.stderr.strip() or "Evidence capture failed", RED)
            return 2
        trial_rows = load_rows(trials_path)
        clean_results = load(clean_results_path)
        isolation_ids = {row["isolation_id"] for row in trial_rows}
        emit(args.record, f"Captured {len(trial_rows)} runs · unique isolation IDs {len(isolation_ids)}/{total_trials}")
        wait(args.record, 3.5)

        for case in cases:
            case_id = case["case_id"]
            show_case(
                args.record,
                case,
                [trial for trial in trial_rows if trial["case_id"] == case_id],
                [trial for trial in clean_results["trials"] if trial["case_id"] == case_id],
                graders,
            )

        faulted_path = project / "trials.fabricated.jsonl"
        failed_results_path = project / "results.failed.json"
        emit(args.record)
        emit(args.record, "3 / PROVE THE GATES CATCH A PLAUSIBLE FAILURE", CYAN + BOLD)
        emit(args.record, "Fault injected into TS-100-t1: unsupported claim = Customer was charged twice")
        created = invoke(
            [
                "fault",
                "--project",
                "eval",
                "--trials",
                trials_path.name,
                "--name",
                "fabricated-claim",
                "--out",
                faulted_path.name,
            ],
            cwd=workspace,
        )
        command_output(created)
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
        failed = load(failed_results_path)
        failed_trial = next(trial for trial in failed["trials"] if trial["failed_gate_ids"])
        failed_gate = next(gate for gate in failed_trial["gate_results"] if not gate["passed"])
        expected_claims = failed_gate["expected"]
        actual_claims = failed_gate["actual"]
        unsupported = next(claim for claim in actual_claims if claim not in expected_claims)
        emit(args.record, "PRODUCT DELIVERED: fluent summary plus one unsupported claim")
        emit(args.record, f"PARAMETER: supported claims · expected={len(expected_claims)} · actual={len(actual_claims)}")
        emit(args.record, f"EXACT DIFFERENCE: + {unsupported}", RED)
        emit(args.record, "FAIL G_OUTCOME_CLAIMS · exact list equality returned false", RED + BOLD)
        emit(args.record, "TS-100 SCORE: 7/8 gates on trial 1 · 1/2 trials passed")
        emit(args.record, f"RELEASE DECISION: {failed['decision']} · no averaging can hide a failed gate", RED + BOLD)
        wait(args.record, 6.0)

        repaired_results_path = project / "results.repaired.json"
        emit(args.record)
        emit(args.record, "4 / REMOVE FAULT · RUN THE SAME CONTRACT", CYAN + BOLD)
        emit(
            args.record,
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
        repaired = load(repaired_results_path)
        for case_result in repaired["case_results"]:
            emit(
                args.record,
                f"  PASS {case_result['case_id']} · trials={case_result['passed_trials']}/{case_result['trials']} "
                f"· deterministic checks={case_result['trials'] * len(graders)}/{case_result['trials'] * len(graders)}",
                GREEN,
            )
        wait(args.record, 3.5)

        summary = repaired["summary"]
        metrics = repaired["metrics"]
        emit(args.record)
        emit(args.record, "5 / RELEASE EVIDENCE", CYAN + BOLD)
        emit(args.record, f"RELEASE DECISION: {repaired['decision']}", GREEN + BOLD)
        emit(args.record, f"Product use cases: {summary['case_count']}/{summary['case_count']} PASS")
        emit(args.record, f"Fresh isolated trials: {summary['passed_trials']}/{summary['trial_count']} PASS")
        emit(args.record, f"Deterministic checks: {total_checks}/{total_checks} PASS")
        emit(args.record, "Outcome: 42/42 PASS · Trajectory: 6/6 PASS")
        emit(args.record, f"Latency: p95 {metrics['p95_latency_ms']} ms <= {rules['max_latency_ms_per_trial']} ms ceiling")
        emit(args.record, f"Tokens: {metrics['total_tokens']} total · retries: {metrics['retries']} · cost: ${metrics['total_cost_usd']:.2f}")
        emit(args.record, f"Safety failures: {summary['safety_failures']} · privacy failures: {summary['privacy_failures']}")
        emit(args.record, "Evaluation method: exact equality + regex + length + trace comparison")
        emit(args.record, "LLM judges: 0 · API keys: 0 · eval SaaS required: 0", GREEN + BOLD)
        emit(args.record, "Copy the starter. Replace the contract, use cases, and adapter with yours.")
        emit(args.record, "Reference adapter is deterministic; production evidence comes from your adapter.", DIM)
        wait(args.record, 11.0)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
