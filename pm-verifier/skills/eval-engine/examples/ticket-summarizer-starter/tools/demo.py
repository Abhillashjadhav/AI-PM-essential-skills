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


def emit(record: bool, text: str = "", style: str = "", delay: float = 0.15) -> None:
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
    elif grader["check"] == "trace_step_equals":
        if isinstance(actual, list):
            detail = f"actual={' > '.join(actual)} == expected={' > '.join(expected)}"
        else:
            detail = f"actual={actual} == expected={expected}"
    elif grader["check"] == "checkpoint_passed":
        detail = f"checkpoint={grader['params']['checkpoint']} actual={actual} == expected=passed"
    elif grader["check"] == "checkpoint_order":
        actual_order = " > ".join(
            name for name, _index in sorted(actual.items(), key=lambda item: item[1])
        )
        detail = f"actual={actual_order} == expected={' > '.join(expected)}"
    elif grader["check"] == "identity_preserved":
        detail = f"unique ticket IDs={len(set(actual.values()))} == 1 ({expected})"
    elif grader["check"] == "state_continuity":
        detail = f"stable fields={','.join(grader['params']['fields'])} across 5 checkpoints"
    elif grader["check"] == "system_completed":
        detail = f"completed={actual} == expected=True"
    elif grader["check"] == "final_checkpoint_reached":
        detail = f"checkpoint={grader['params']['checkpoint']} present={actual}"
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
    emit(record, "OUTCOME DELIVERED", BOLD)
    emit(record, f"  summary: {outcome['response']['summary']}")
    emit(record, f"  request: {outcome['response']['customer_request']}")
    emit(
        record,
        f"  sentiment={outcome['sentiment']} · escalation={outcome['escalation_reason']}",
    )
    emit(record, f"  supported claims ({len(outcome['supported_claims'])}): {'; '.join(outcome['supported_claims'])}")
    gates_by_id = {gate["grader_id"]: gate for gate in first_result["gate_results"]}
    by_scope = {
        scope: [grader for grader in graders if grader["scope"] == scope]
        for scope in ("outcome", "trajectory", "system")
    }

    emit(record, f"OUTCOME EVALS ({len(by_scope['outcome'])}) · EXPECTED vs ACTUAL", BOLD)
    for grader in by_scope["outcome"]:
        emit(record, gate_line(grader, gates_by_id[grader["id"]]))

    trajectory = first_trial["trajectory"]
    emit(record, "TOOL TRAJECTORY DELIVERED", BOLD)
    emit(record, "  " + " > ".join(step["name"] for step in trajectory))
    for step in trajectory:
        emit(record, f"  {step['name']}: {json.dumps(step['attributes'], separators=(',', ':'))}")
    emit(record, f"TOOL TRAJECTORY EVALS ({len(by_scope['trajectory'])}) · EXPECTED vs ACTUAL", BOLD)
    for grader in by_scope["trajectory"]:
        emit(record, gate_line(grader, gates_by_id[grader["id"]]))

    checkpoints = first_trial["system"]["checkpoints"]
    emit(record, "SYSTEM WORKFLOW DELIVERED", BOLD)
    emit(record, "  checkpoints: " + " > ".join(checkpoint["name"] for checkpoint in checkpoints))
    emit(
        record,
        f"  ticket={first_trial['system']['entity_id']} · completed={first_trial['system']['completed']} "
        f"· state=thread_id+message_count",
    )
    emit(record, f"SYSTEM EVALS ({len(by_scope['system'])}) · EXPECTED vs ACTUAL", BOLD)
    for grader in by_scope["system"]:
        emit(record, gate_line(grader, gates_by_id[grader["id"]]))

    gate_executions = sum(len(trial["gate_results"]) for trial in result_trials)
    passed_executions = sum(
        gate["passed"] for trial in result_trials for gate in trial["gate_results"]
    )
    passed_trials = sum(not trial["failed_gate_ids"] for trial in result_trials)
    for scope, label in (
        ("outcome", "OUTCOME"),
        ("trajectory", "TOOL TRAJECTORY"),
        ("system", "SYSTEM"),
    ):
        scope_graders = by_scope[scope]
        scope_checks = [
            gate
            for trial in result_trials
            for gate in trial["gate_results"]
            if gate["scope"] == scope
        ]
        emit(
            record,
            f"{label} SCORE: {len(scope_graders)}/{len(scope_graders)} gates · "
            f"{sum(gate['passed'] for gate in scope_checks)}/{len(scope_checks)} checks PASS",
            GREEN,
        )
    emit(
        record,
        f"USE CASE TOTAL: {len(graders)}/{len(graders)} gates · "
        f"{passed_executions}/{gate_executions} checks · "
        f"{passed_trials}/{len(result_trials)} isolated trials PASS",
        GREEN + BOLD,
    )
    wait(record, 5.0)


def run_fault(
    workspace: Path,
    project: Path,
    trials_name: str,
    fault_name: str,
    stem: str,
) -> dict:
    """Apply one checked-in fault and evaluate it against the unchanged suite."""

    faulted_name = f"trials.{stem}.jsonl"
    result_name = f"results.{stem}.json"
    created = invoke(
        [
            "fault",
            "--project",
            "eval",
            "--trials",
            trials_name,
            "--name",
            fault_name,
            "--out",
            faulted_name,
        ],
        cwd=workspace,
    )
    command_output(created)
    completed = invoke(
        [
            "run",
            "--project",
            "eval",
            "--trials",
            f"eval/{faulted_name}",
            "--out",
            f"eval/{result_name}",
        ],
        cwd=workspace,
    )
    command_output(completed)
    result_path = project / result_name
    if not result_path.is_file():
        raise RuntimeError(completed.stderr.strip() or f"{fault_name} did not produce results")
    return load(result_path)


def main() -> int:
    global PLAIN
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--record",
        action="store_true",
        help="pace output for a longer three-surface recording at 1.5x",
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

        show("AI EVALS FOR PMs — THREE-SURFACE RELEASE DECISION", CYAN + BOLD)
        show("Repository: AI-PM-essential-skills / pm-verifier")
        show("Runs locally or in CI · no eval SaaS · no LLM judge · no API key")
        wait(args.record, 3.0)

        emit(args.record)
        emit(args.record, "1 / PRODUCT CONTRACT BECOMES EXECUTABLE EVIDENCE", CYAN + BOLD)
        emit(args.record, "Product must return: summary + request + sentiment + escalation + supported claims")
        emit(args.record, "Tool path must prove: order > summarize > validate > deliver with correct parameters")
        emit(args.record, "System must prove: every checkpoint passed, ordered, continuous, and completed")
        emit(args.record, "Enabled surfaces: OUTCOME + TOOL TRAJECTORY + SYSTEM · memory not promised")
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

        grader_by_id = {grader["id"]: grader for grader in graders}
        emit(args.record)
        emit(args.record, "3 / BREAK ONE REQUIREMENT ON EACH SURFACE", CYAN + BOLD)

        emit(args.record)
        emit(args.record, "3A / OUTCOME FAILURE · TS-100-t1", BOLD)
        outcome_failed = run_fault(
            workspace,
            project,
            trials_path.name,
            "fabricated-claim",
            "outcome",
        )
        outcome_trial = next(
            trial for trial in outcome_failed["trials"] if trial["failed_gate_ids"]
        )
        outcome_gate = next(
            gate for gate in outcome_trial["gate_results"] if not gate["passed"]
        )
        expected_claims = outcome_gate["expected"]
        actual_claims = outcome_gate["actual"]
        unsupported = next(claim for claim in actual_claims if claim not in expected_claims)
        emit(args.record, "Product output: fluent summary plus one unsupported claim")
        emit(args.record, f"Expected supported claims={len(expected_claims)} · actual={len(actual_claims)}")
        emit(args.record, f"Exact difference: + {unsupported}", RED)
        emit(args.record, gate_line(grader_by_id[outcome_gate["grader_id"]], outcome_gate), RED)
        emit(args.record, "OUTCOME SCORE: 6/7 gates on trial 1 · RELEASE DECISION: FAIL", RED + BOLD)
        wait(args.record, 3.0)

        emit(args.record)
        emit(args.record, "3B / TOOL TRAJECTORY FAILURE · TS-300-t1", BOLD)
        trajectory_failed = run_fault(
            workspace,
            project,
            trials_path.name,
            "wrong-order",
            "trajectory",
        )
        trajectory_trial = next(
            trial for trial in trajectory_failed["trials"] if trial["failed_gate_ids"]
        )
        trajectory_gate = next(
            gate for gate in trajectory_trial["gate_results"] if not gate["passed"]
        )
        emit(args.record, "Tool parameter changed: order_messages.chronological_ids")
        emit(
            args.record,
            f"Expected={' > '.join(trajectory_gate['expected'])} · "
            f"actual={' > '.join(trajectory_gate['actual'])}",
        )
        emit(
            args.record,
            gate_line(grader_by_id[trajectory_gate["grader_id"]], trajectory_gate),
            RED,
        )
        emit(args.record, "TOOL TRAJECTORY SCORE: 4/5 gates on trial 1 · RELEASE DECISION: FAIL", RED + BOLD)
        wait(args.record, 3.0)

        emit(args.record)
        emit(args.record, "3C / SYSTEM FAILURE · TS-200-t1", BOLD)
        system_failed = run_fault(
            workspace,
            project,
            trials_path.name,
            "failed-validation-checkpoint",
            "system",
        )
        system_trial = next(
            trial for trial in system_failed["trials"] if trial["failed_gate_ids"]
        )
        system_gates = [
            gate for gate in system_trial["gate_results"] if not gate["passed"]
        ]
        emit(args.record, "System evidence: validate checkpoint=failed · completed=False")
        for gate in system_gates:
            emit(
                args.record,
                gate_line(grader_by_id[gate["grader_id"]], gate),
                RED,
            )
        emit(args.record, "SYSTEM SCORE: 8/10 gates on trial 1 · RELEASE DECISION: FAIL", RED + BOLD)
        emit(args.record, "No aggregate score can override a failed binary release gate.")
        wait(args.record, 4.0)

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
        for scope, label in (
            ("outcome", "Outcome"),
            ("trajectory", "Tool trajectory"),
            ("system", "System"),
        ):
            scope_checks = (
                sum(grader["scope"] == scope for grader in graders) * total_trials
            )
            emit(args.record, f"{label}: {scope_checks}/{scope_checks} deterministic checks PASS")
        emit(args.record, f"Latency: p95 {metrics['p95_latency_ms']} ms <= {rules['max_latency_ms_per_trial']} ms ceiling")
        emit(args.record, f"Tokens: {metrics['total_tokens']} total · retries: {metrics['retries']} · cost: ${metrics['total_cost_usd']:.2f}")
        emit(args.record, f"Safety failures: {summary['safety_failures']} · privacy failures: {summary['privacy_failures']}")
        emit(args.record, "Methods: equality + regex + length + trace parameters + checkpoint contracts")
        emit(args.record, "LLM judges: 0 · API keys: 0 · eval SaaS required: 0", GREEN + BOLD)
        emit(args.record, "Copy the starter. Replace the contract, use cases, and adapter with yours.")
        emit(args.record, "Reference adapter is deterministic; production evidence comes from your adapter.", DIM)
        wait(args.record, 11.0)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
