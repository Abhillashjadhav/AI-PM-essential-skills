"""A real, local checkpoint/fork runner with six distinct scripted workers.

No LLM or external service is called. This tests the orchestration mechanism,
not model quality. The fixture and every consequential action are synthetic.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DEPENDENCIES = {
    "validate_request": [],
    "lookup_order": ["validate_request"],
    "inspect_return": ["validate_request"],
    "retrieve_policy": ["lookup_order", "inspect_return"],
    "calculate_refund": ["retrieve_policy", "lookup_order", "inspect_return"],
    "verify_refund": ["calculate_refund", "retrieve_policy"],
}
PREFIX = ["validate_request", "lookup_order", "inspect_return"]
SUFFIX = ["retrieve_policy", "calculate_refund", "verify_refund"]
STRATEGIES = {"text_match", "effective_date"}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def load_fixture(path: Path = ROOT / "fixture.json") -> dict:
    return json.loads(path.read_text())


def applicable(policy: dict, as_of: str) -> bool:
    today = date.fromisoformat(as_of)
    return (date.fromisoformat(policy["effective_from"]) <= today
            and (policy["effective_to"] is None
                 or today <= date.fromisoformat(policy["effective_to"])))


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


def execute_task(task: str, state: dict, fixture: dict) -> Any:
    """Workers never receive the evaluation oracle."""
    values = state["values"]
    if task == "validate_request":
        req = copy.deepcopy(fixture["request"])
        for field in ("order_id", "customer_id", "question", "retrieval_query"):
            if not isinstance(req[field], str) or not req[field].strip():
                raise ValueError(f"Missing {field}")
        date.fromisoformat(req["as_of"])
        return req
    request = values["validate_request"]
    if task == "lookup_order":
        order = copy.deepcopy(fixture["orders"][request["order_id"]])
        if order["customer_id"] != request["customer_id"]:
            raise ValueError("Order ownership mismatch")
        if type(order["paid_rupees"]) is not int or order["paid_rupees"] <= 0:
            raise ValueError("Invalid paid amount")
        return order
    if task == "inspect_return":
        evidence = copy.deepcopy(fixture["return_evidence"][request["order_id"]])
        if evidence["inspection_confirmed"] is not True:
            raise ValueError("Return evidence is unconfirmed")
        if evidence["condition"] not in {"arrived_damaged", "change_of_mind"}:
            raise ValueError("Unknown condition")
        return evidence
    if task == "retrieve_policy":
        strategy = state["config"]["retrieval_strategy"]
        if strategy not in STRATEGIES:
            raise ValueError("Unsupported strategy")
        query = tokens(request["retrieval_query"])
        candidates = []
        for policy in fixture["policies"]:
            current = applicable(policy, request["as_of"])
            if strategy == "effective_date" and not current:
                continue
            score = len(query & tokens(policy["title"] + " " + policy["text"]))
            candidates.append({"policy": copy.deepcopy(policy), "score": score,
                               "date_applicable": current})
        if not candidates:
            raise ValueError("No applicable policy")
        candidates.sort(key=lambda row: (-row["score"], row["policy"]["id"]))
        chosen = candidates[0]
        return {"strategy": strategy, "policy": chosen["policy"],
                "ranked_candidates": [{"id": c["policy"]["id"], "score": c["score"],
                                       "date_applicable": c["date_applicable"]} for c in candidates]}
    if task == "calculate_refund":
        order, inspection = values["lookup_order"], values["inspect_return"]
        policy = values["retrieve_policy"]["policy"]
        age = (date.fromisoformat(request["as_of"]) - date.fromisoformat(order["delivered_on"])).days
        eligible = 0 <= age <= policy["return_window_days"]
        exempt = inspection["condition"] == "arrived_damaged" and policy["damaged_item_exempt"]
        fee_percent = 0 if exempt else policy["restocking_percent"]
        amount = order["paid_rupees"] * (100 - fee_percent) // 100 if eligible else 0
        return {"policy_id": policy["id"], "eligible": eligible,
                "fee_percent": fee_percent, "refund_rupees": amount}
    if task == "verify_refund":
        # This independent verifier reads the source policies directly. It does
        # not accept the worker's selected policy as the applicable-policy oracle.
        current = [p for p in fixture["policies"] if applicable(p, request["as_of"])]
        if len(current) != 1:
            raise ValueError("Ambiguous current policy")
        rule, proposal = current[0], values["calculate_refund"]
        order = fixture["orders"][request["order_id"]]
        inspection = fixture["return_evidence"][request["order_id"]]
        days = (date.fromisoformat(request["as_of"]) - date.fromisoformat(order["delivered_on"])).days
        eligible = 0 <= days <= rule["return_window_days"]
        full = inspection["condition"] == "arrived_damaged" and rule["damaged_item_exempt"]
        expected = (order["paid_rupees"] if full else order["paid_rupees"] - order["paid_rupees"] * rule["restocking_percent"] // 100) if eligible else 0
        gates = {
            "applicable_policy": proposal["policy_id"] == rule["id"],
            "eligibility_matches": proposal["eligible"] == eligible,
            "amount_matches": proposal["refund_rupees"] == expected,
        }
        return {"status": "PASS" if all(gates.values()) else "FAIL", "gates": gates,
                "expected_refund_rupees": expected, "expected_policy_id": rule["id"]}
    raise ValueError(f"Unknown task {task}")


def validate_artifact(task: str, value: Any, fixture: dict) -> None:
    """Coordinator admission checks, separate from the task implementations."""
    if not isinstance(value, dict):
        raise ValueError("Artifact must be an object")
    if task == "validate_request" and value != fixture["request"]:
        raise ValueError("Request changed")
    if task == "lookup_order" and value != fixture["orders"][fixture["request"]["order_id"]]:
        raise ValueError("Order artifact changed")
    if task == "inspect_return" and value != fixture["return_evidence"][fixture["request"]["order_id"]]:
        raise ValueError("Return evidence changed")
    if task == "retrieve_policy" and value["policy"] not in fixture["policies"]:
        raise ValueError("Invented policy")
    if task == "calculate_refund" and (type(value["refund_rupees"]) is not int or value["refund_rupees"] < 0):
        raise ValueError("Invalid refund")
    if task == "verify_refund":
        if value["status"] not in {"PASS", "FAIL"} or not value["gates"]:
            raise ValueError("Invalid verification record")
        if (value["status"] == "PASS") != all(value["gates"].values()):
            raise ValueError("Verifier status contradicts its gates")


class Runner:
    def __init__(self, fixture: dict, run_id: str, checkpoint: dict | None = None,
                 strategy: str = "text_match", fail_task: str | None = None):
        if strategy not in STRATEGIES:
            raise ValueError("Unknown retrieval strategy")
        self.fixture = copy.deepcopy(fixture)
        self.worker_fixture = {key: value for key, value in self.fixture.items() if key != "oracle"}
        self.run_id, self.events, self.executed = run_id, [], []
        self.attempts, self.failures = {}, {}
        self.fail_task = fail_task
        self.started = time.monotonic()
        if checkpoint is None:
            self.state = {"values": {}, "records": {}, "config": {"retrieval_strategy": strategy}}
            self.parent = None
        else:
            validate_checkpoint(checkpoint, fixture)
            self.state = copy.deepcopy(checkpoint["payload"]["state"])
            self.parent = checkpoint["sha256"]
            old = self.state["config"]["retrieval_strategy"]
            self.state["config"]["retrieval_strategy"] = strategy
            self.event("fork_created", parent_checkpoint_sha256=self.parent,
                       changed_field="config.retrieval_strategy", old=old, new=strategy)
            for task in PREFIX:
                self.event("task_restored", task=task,
                           artifact_sha256=self.state["records"][task]["artifact_sha256"])

    def event(self, event: str, **fields) -> None:
        self.events.append({"sequence": len(self.events) + 1, "run_id": self.run_id,
                            "event": event, **fields})

    def worker(self, task: str, input_state: dict) -> tuple[Any, int]:
        for attempt in range(1, 3):
            try:
                if task == self.fail_task:
                    raise ValueError("Injected fixture failure")
                value = execute_task(task, copy.deepcopy(input_state), self.worker_fixture)
                validate_artifact(task, value, self.worker_fixture)
                return value, attempt
            except (ValueError, KeyError, TypeError) as exc:
                if attempt == 2:
                    raise RuntimeError(str(exc)) from exc
        raise AssertionError("Unreachable")

    def run_tasks(self, tasks: list[str]) -> bool:
        pending = set(tasks)
        while pending:
            if time.monotonic() - self.started > 10:
                self.failures["graph"] = "Cooperative graph budget exceeded"
                return False
            ready = [t for t in DEPENDENCIES if t in pending and all(d in self.state["values"] for d in DEPENDENCIES[t])]
            if not ready:
                self.event("join_blocked", missing_tasks=sorted(pending))
                return False
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs = {}
                for task in ready:
                    self.event("task_started", task=task)
                    jobs[pool.submit(self.worker, task, copy.deepcopy(self.state))] = task
                for future in as_completed(jobs):
                    task = jobs[future]
                    pending.remove(task)
                    self.executed.append(task)
                    try:
                        value, attempt = future.result()
                    except RuntimeError as exc:
                        self.attempts[task] = 2
                        self.failures[task] = str(exc)
                        self.event("task_failed", task=task, attempts=2, reason=str(exc))
                        continue
                    self.attempts[task] = attempt
                    self.state["values"][task] = value
                    self.state["records"][task] = {"producer": task, "origin_run": self.run_id,
                        "artifact_sha256": digest(value), "recorded_at": datetime.now(timezone.utc).isoformat(),
                        "admission_check": "PASS"}
                    self.event("task_completed", task=task, value=value)
            if self.failures:
                self.event("run_blocked", failures=copy.deepcopy(self.failures))
                return False
        return True

    def snapshot(self) -> dict:
        if set(self.state["values"]) != set(PREFIX):
            raise ValueError("Checkpoint C1 requires all three prefix tasks, and no suffix")
        payload = {"checkpoint_id": "C1", "schema_version": 1,
                   "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   "fixture_sha256": digest(self.fixture), "source_run": self.run_id,
                   "next_tasks": ["retrieve_policy"], "state": copy.deepcopy(self.state)}
        snapshot = {"sha256": digest(payload), "payload": payload}
        self.event("checkpoint_saved", checkpoint_id="C1", sha256=snapshot["sha256"])
        return snapshot

    def result(self) -> dict:
        verification = self.state["values"].get("verify_refund", {})
        complete = not self.failures and set(self.state["values"]) == set(DEPENDENCIES) and verification.get("status") == "PASS"
        proposed = self.state["values"].get("calculate_refund", {}).get("refund_rupees")
        return {"run_id": self.run_id, "status": "VERIFIED" if complete else "BLOCKED",
                "parent_checkpoint_sha256": self.parent, "state": copy.deepcopy(self.state),
                "executed": self.executed, "restored": PREFIX if self.parent else [],
                "attempts": self.attempts, "failures": self.failures,
                "proposed_refund_rupees": proposed, "final_refund_rupees": proposed if complete else None,
                "events": self.events, "model_calls": 0, "external_actions": []}


def validate_checkpoint(checkpoint: dict, fixture: dict) -> None:
    payload = checkpoint["payload"]
    if digest(payload) != checkpoint["sha256"]:
        raise ValueError("Checkpoint digest mismatch")
    if payload["schema_version"] != 1 or payload["checkpoint_id"] != "C1":
        raise ValueError("Unsupported checkpoint")
    if payload["code_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise ValueError("Implementation changed since checkpoint")
    if payload["fixture_sha256"] != digest(fixture):
        raise ValueError("Fixture changed since checkpoint")
    if set(payload["state"]["values"]) != set(PREFIX):
        raise ValueError("Incomplete checkpoint join")
    for task in PREFIX:
        record = payload["state"]["records"][task]
        value = payload["state"]["values"][task]
        if record["artifact_sha256"] != digest(value) or record["admission_check"] != "PASS":
            raise ValueError("Invalid checkpoint artifact")
        validate_artifact(task, value, {k: v for k, v in fixture.items() if k != "oracle"})


def baseline(out: Path) -> dict:
    if out.exists():
        raise FileExistsError("Choose a new output folder; evidence is never overwritten")
    out.mkdir(parents=True)
    fixture = load_fixture()
    run = Runner(fixture, "original")
    if not run.run_tasks(PREFIX):
        raise RuntimeError("Cannot create a checkpoint from incomplete prefix tasks")
    snapshot = run.snapshot()
    write_new(out / "checkpoint-C1.json", snapshot)
    run.run_tasks(SUFFIX)
    result = run.result()
    write_new(out / "original.json", result)
    return result


def fork(checkpoint_path: Path, out: Path, strategy: str = "effective_date") -> dict:
    checkpoint = json.loads(checkpoint_path.read_text())
    run = Runner(load_fixture(), "fork-" + strategy, checkpoint, strategy)
    run.run_tasks(SUFFIX)
    result = run.result()
    write_new(out, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("baseline")
    start.add_argument("--out", type=Path, required=True)
    resume = sub.add_parser("fork")
    resume.add_argument("--checkpoint", type=Path, required=True)
    resume.add_argument("--out", type=Path, required=True)
    resume.add_argument("--strategy", choices=sorted(STRATEGIES), default="effective_date")
    args = parser.parse_args()
    result = baseline(args.out) if args.command == "baseline" else fork(args.checkpoint, args.out, args.strategy)
    for event in result["events"]:
        print(json.dumps(event, ensure_ascii=False))
    print(json.dumps({k: result[k] for k in ("run_id", "status", "proposed_refund_rupees", "final_refund_rupees", "executed", "restored")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
