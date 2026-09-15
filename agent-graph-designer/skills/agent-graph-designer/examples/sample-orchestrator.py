#!/usr/bin/env python3
"""Three distinct synthetic review loops, with bounded process recovery.

POSIX, single-coordinator reference for the committed topology, not a general
graph interpreter. No model calls, live evidence or external actions.
"""
from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path(__file__).with_name("sample-graph-contract.json")
REVIEW_NODES = ("product-outcome-review", "model-quality-review", "safety-privacy-review")
EVIDENCE = {
    "product-outcome-review": {"resolution_minutes": 6, "maximum_minutes": 7},
    "model-quality-review": {"passed_cases": 18, "total_cases": 20, "minimum_rate": 0.9},
    "safety-privacy-review": {"restricted_data_exposures": 0, "unsafe_outputs": 0},
}
FAULTS = ("none", "crash-once", "crash-always", "timeout-once", "wrong-always")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def load_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def review(task: dict[str, Any]) -> dict[str, Any]:
    """Execute only this task's operation, using only its assigned inputs."""
    data, node = task["inputs"], task["node_id"]
    if node == REVIEW_NODES[0]:
        accepted = data["resolution_minutes"] <= data["maximum_minutes"]
        observed = {"minutes": data["resolution_minutes"]}
    elif node == REVIEW_NODES[1]:
        accepted = Decimal(data["passed_cases"]) / Decimal(data["total_cases"]) >= Decimal(str(data["minimum_rate"]))
        observed = {"passed": data["passed_cases"], "total": data["total_cases"]}
    elif node == REVIEW_NODES[2]:
        accepted = data["restricted_data_exposures"] == data["unsafe_outputs"] == 0
        observed = {"exposures": data["restricted_data_exposures"], "unsafe": data["unsafe_outputs"]}
    else:
        raise ValueError("Unknown registered task")
    return {"node_id": node, "candidate_digest": task["candidate_digest"],
            "input_digest": digest(task), "schema": "review-v1",
            "status": "PASS" if accepted else "FAIL", "observed": observed}


def verify(task: dict[str, Any], result: Any) -> bool:
    """Check against frozen inputs without invoking the worker as its own judge.

    The deterministic verifier establishes this fixture's arithmetic and policy
    result, not real release quality or independence of the underlying sources.
    """
    if not isinstance(result, dict):
        return False
    node, data = task["node_id"], task["inputs"]
    if node == REVIEW_NODES[0]:
        expected = {"minutes": data["resolution_minutes"]}
        accepted = 0 <= data["resolution_minutes"] <= data["maximum_minutes"]
    elif node == REVIEW_NODES[1]:
        expected = {"passed": data["passed_cases"], "total": data["total_cases"]}
        accepted = Decimal(data["passed_cases"]) >= Decimal(str(data["minimum_rate"])) * data["total_cases"]
    elif node == REVIEW_NODES[2]:
        expected = {"exposures": data["restricted_data_exposures"], "unsafe": data["unsafe_outputs"]}
        accepted = not (data["restricted_data_exposures"] or data["unsafe_outputs"])
    else:
        return False
    return (result.get("node_id") == node
            and result.get("candidate_digest") == task["candidate_digest"]
            and result.get("input_digest") == digest(task)
            and result.get("schema") == "review-v1"
            and digest(result.get("observed")) == digest(expected)
            and result.get("status") == ("PASS" if accepted else "FAIL"))


def validate_inputs(evidence: dict[str, Any]) -> None:
    if set(evidence) != set(REVIEW_NODES):
        raise ValueError("All three distinct tasks need registered inputs")
    for node in REVIEW_NODES:
        if set(evidence[node]) != set(EVIDENCE[node]):
            raise ValueError(f"Missing or unknown input fields for {node}")
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0
               for v in evidence[node].values()):
            raise ValueError(f"Invalid numeric evidence for {node}")
    quality = evidence[REVIEW_NODES[1]]
    counts = [quality["passed_cases"], quality["total_cases"], *evidence[REVIEW_NODES[2]].values()]
    if any(type(value) is not int for value in counts):
        raise ValueError("Case and safety counts must be integers")
    if not 0 <= quality["passed_cases"] <= quality["total_cases"] or quality["total_cases"] == 0:
        raise ValueError("Invalid quality-case counts")
    if quality["minimum_rate"] > 1:
        raise ValueError("Invalid quality threshold")


def save(path: Path, state: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def blocked(reason: str) -> dict[str, Any]:
    return {"status": "BLOCKED", "blocking_reason": reason,
            "recommendation": None, "external_actions_taken": []}


def run(state_dir: Path | None = None, *, failure: str = "none",
        fail_node: str = "model-quality-review", contract: dict[str, Any] | None = None,
        evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    if state_dir is None:
        with tempfile.TemporaryDirectory(prefix="graph-example-") as temporary:
            return run(Path(temporary), failure=failure, fail_node=fail_node,
                       contract=contract, evidence=evidence)
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    # One writer per checkpoint. Worker processes never open this lock.
    with (state_dir / "coordinator.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return blocked("Another coordinator owns this run")
        try:
            return _run(state_dir, failure, fail_node, contract or load_contract(), evidence)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            result = blocked(f"Run state or inputs invalid: {exc}")
            save(state_dir / "result.json", result)
            return result


def _run(directory: Path, failure: str, fail_node: str, contract: dict[str, Any],
         evidence: dict[str, Any] | None) -> dict[str, Any]:
    if failure not in FAULTS or fail_node not in REVIEW_NODES:
        raise ValueError("Unsupported fault or task")
    nodes = {node["id"]: node for node in contract["nodes"]}
    join = contract["joins"][0]
    if (contract["qualification"]["verdict"] != "GRAPH_REQUIRED"
            or join["policy"] != "ALL_REQUIRED"
            or set(join["required_branches"]) != set(REVIEW_NODES)
            or join["artifact_schema"] != "review-v1"):
        raise ValueError("This runner supports only the committed three-review topology")
    if (type(contract["concurrency_cap"]) is not int
            or not 1 <= contract["concurrency_cap"] <= 3 or len(nodes) > contract["node_cap"]
            or type(contract["max_repairs_per_node"]) is not int
            or not 0 <= contract["max_repairs_per_node"] <= 2):
        raise ValueError("Invalid node or concurrency cap")
    for node in REVIEW_NODES:
        if (nodes[node]["type"] != "LOOP" or type(nodes[node]["max_attempts"]) is not int
                or nodes[node]["max_attempts"] < 1
                or nodes[node]["max_attempts"] > 1 + contract["max_repairs_per_node"]
                or nodes[node]["owner"] == nodes[node]["verifier"]["role"]
                or nodes[node]["permissions"]["actions"]):
            raise ValueError(f"Unsupported execution contract for {node}")
    limits = [contract["total_budget"]["max_seconds"], join["timeout_seconds"]]
    limits += [value for node in REVIEW_NODES for value in
               (nodes[node]["timeout_seconds"], nodes[node]["budget"]["max_seconds"])]
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in limits):
        raise ValueError("Time limits must be finite and positive")

    checkpoint = directory / "checkpoint.json"
    if checkpoint.exists():
        state = json.loads(checkpoint.read_text(encoding="utf-8"))
        manifest = state["task_manifest"]
        if (state["contract_digest"] != digest(contract)
                or set(manifest) != set(REVIEW_NODES)
                or state["manifest_digest"] != digest(manifest)):
            raise ValueError("Task registration or contract changed; use a new run")
        saved_inputs = {node: manifest[node]["inputs"] for node in REVIEW_NODES}
        validate_inputs(saved_inputs)
        if evidence is not None and evidence != saved_inputs:
            raise ValueError("Inputs changed; use a new run")
        if set(state["attempts"]) != set(REVIEW_NODES) or not set(state["results"]) <= set(REVIEW_NODES):
            raise ValueError("Invalid saved task identities")
        if any(type(count) is not int or not 0 <= count <= nodes[node]["max_attempts"]
               for node, count in state["attempts"].items()):
            raise ValueError("Invalid saved attempt counters")
        for node, result in state["results"].items():
            if not verify(manifest[node], result) or result["status"] != "PASS":
                raise ValueError(f"Saved result failed verification: {node}")
    else:
        if (directory / "result.json").exists():
            raise ValueError("Missing checkpoint; cannot resume this run")
        inputs = copy.deepcopy(EVIDENCE if evidence is None else evidence)
        validate_inputs(inputs)
        candidate_digest = digest({"candidate": "synthetic-support-ticket-summarizer-v1", "evidence": inputs})
        manifest = {node: {"node_id": node, "purpose": nodes[node]["purpose"],
                           "inputs": inputs[node], "candidate_digest": candidate_digest}
                    for node in REVIEW_NODES}
        state = {"schema_version": 1, "contract_digest": digest(contract),
                 "candidate_digest": candidate_digest, "task_manifest": manifest,
                 "manifest_digest": digest(manifest), "started_at": time.time(),
                 "attempts": {node: 0 for node in REVIEW_NODES}, "first_started_at": {},
                 "results": {}, "failures": {}, "events": []}

    def event(kind: str, **fields: Any) -> None:
        state["events"].append({"event": kind, "time": time.time(), **fields})
        save(checkpoint, state)

    state["status"] = "RUNNING"
    event("tasks_registered", task_ids=list(REVIEW_NODES))
    reused = sorted(state["results"])
    pending = [node for node in REVIEW_NODES if node not in state["results"]
               and node not in state["failures"]]
    active: dict[str, tuple[subprocess.Popen[str], float]] = {}
    # Wall-clock budgets include downtime and cannot be reset by resuming.
    graph_deadline = min(state["started_at"] + contract["total_budget"]["max_seconds"],
                         state["started_at"] + join["timeout_seconds"])
    stop_reason = ("Operator stop" if (directory / "STOP").exists() else
                   "Graph time budget exhausted" if time.time() >= graph_deadline else None)

    def reject(node: str, reason: str) -> None:
        event("attempt_failed", node=node, attempt=state["attempts"][node], reason=reason)
        if state["attempts"][node] < nodes[node]["max_attempts"]:
            pending.append(node)
        else:
            state["failures"][node] = f"Attempt budget exhausted: {reason}"
            event("task_blocked", node=node, reason=state["failures"][node])

    try:
        while (pending or active) and stop_reason is None:
            now = time.time()
            if (directory / "STOP").exists() or now >= graph_deadline:
                stop_reason = "Operator stop" if (directory / "STOP").exists() else "Graph time budget exhausted"
                break
            while pending and len(active) < contract["concurrency_cap"]:
                now = time.time()
                if (directory / "STOP").exists() or now >= graph_deadline:
                    stop_reason = "Operator stop" if (directory / "STOP").exists() else "Graph time budget exhausted"
                    break
                node = pending.pop(0)
                first = state["first_started_at"].setdefault(node, now)
                deadline = min(graph_deadline, first + nodes[node]["budget"]["max_seconds"],
                               now + nodes[node]["timeout_seconds"])
                if state["attempts"][node] >= nodes[node]["max_attempts"] or deadline <= now:
                    state["failures"][node] = "Attempt or task time budget exhausted"
                    event("task_blocked", node=node, reason=state["failures"][node])
                    continue
                # Persist task + attempt before giving any child its unique task.
                state["attempts"][node] += 1
                event("attempt_started", node=node, attempt=state["attempts"][node])
                fault = failure if node == fail_node else "none"
                if fault.endswith("-once") and state["attempts"][node] > 1:
                    fault = "none"
                try:
                    process = subprocess.Popen(
                        [sys.executable, str(Path(__file__).resolve()), "--worker", json.dumps(manifest[node]),
                         "--fault", fault], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                except OSError as exc:
                    reject(node, f"Worker could not start: {exc}")
                    continue
                active[node] = (process, deadline)
                event("worker_dispatched", node=node, pid=process.pid, attempt=state["attempts"][node])
            if stop_reason:
                break
            for node, (process, deadline) in list(active.items()):
                timed_out = time.time() >= deadline
                if process.poll() is None and not timed_out:
                    continue
                if timed_out and process.poll() is None:
                    process.kill()
                stdout, _ = process.communicate()
                del active[node]
                if timed_out or process.returncode != 0:
                    reject(node, "Worker timeout" if timed_out else "Worker process failed")
                    continue
                try:
                    result = json.loads(stdout)
                except ValueError:
                    result = None
                if not verify(manifest[node], result):
                    reject(node, "Independent verification rejected worker output")
                elif result["status"] != "PASS":
                    state["failures"][node] = "Frozen evidence fails this task's acceptance criteria"
                    event("task_blocked", node=node, reason=state["failures"][node])
                else:
                    result["verified_by"] = nodes[node]["verifier"]["role"]
                    state["results"][node] = result
                    event("task_verified", node=node, attempt=state["attempts"][node])
            if pending or active:
                time.sleep(0.005)
    finally:
        for process, _ in active.values():
            if process.poll() is None:
                process.kill()
            process.communicate()

    missing = sorted(set(REVIEW_NODES) - set(state["results"]))
    ready = not missing and not state["failures"] and not stop_reason
    result = {
        "contract": contract["name"], "candidate_digest": state["candidate_digest"],
        "completed_branches": sorted(state["results"]), "missing_branches": missing,
        "join_policy": join["policy"], "attempts": copy.deepcopy(state["attempts"]),
        "reused_branches": reused, "external_actions_taken": [],
        "status": "AWAITING_HUMAN_APPROVAL" if ready else "BLOCKED",
        "recommendation": "EVIDENCE_READY_FOR_HUMAN_DECISION" if ready else None,
        "blocking_reasons": [stop_reason] if stop_reason else list(state["failures"].values()),
        "worker_type": "scripted synthetic checks; no model calls", "model_tokens": 0,
    }
    state["status"] = result["status"]
    event("join_ready" if ready else "graph_blocked", missing_branches=missing)
    save(directory / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--failure", choices=FAULTS, default="none")
    parser.add_argument("--fail-node", choices=REVIEW_NODES, default=REVIEW_NODES[1])
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    parser.add_argument("--fault", default="none", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if args.fault.startswith("crash-"):
            return 7
        if args.fault.startswith("timeout-"):
            time.sleep(3600)
        output = review(json.loads(args.worker))
        if args.fault == "wrong-always":
            output["candidate_digest"] = "wrong-candidate"
        print(json.dumps(output))
        return 0
    result = run(args.state_dir, failure=args.failure, fail_node=args.fail_node)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "AWAITING_HUMAN_APPROVAL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
