"""Run separate baseline/fork processes, verify their artifacts, and test guards."""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import fork_graph as graph

ROOT = Path(__file__).resolve().parent


def main(out: Path) -> None:
    checks = []

    def check(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    def refuses(name, operation):
        try:
            operation()
        except (ValueError, KeyError, FileExistsError):
            check(name, True)
        else:
            check(name, False)

    commands = [
        [sys.executable, str(ROOT / "fork_graph.py"), "baseline", "--out", str(out)],
        [sys.executable, str(ROOT / "fork_graph.py"), "fork", "--checkpoint", str(out / "checkpoint-C1.json"),
         "--strategy", "effective_date", "--out", str(out / "fork-effective_date.json")],
        [sys.executable, str(ROOT / "fork_graph.py"), "fork", "--checkpoint", str(out / "checkpoint-C1.json"),
         "--strategy", "text_match", "--out", str(out / "fork-unchanged-control.json")],
    ]
    transcripts = []
    preserved = None
    for index, command in enumerate(commands):
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=15, check=True)
        transcripts.append({"command": command, "returncode": completed.returncode, "stdout": completed.stdout})
        if index == 0:
            preserved = {name: (out / name).read_bytes() for name in ("checkpoint-C1.json", "original.json")}
    for name, original in preserved.items():
        check(f"Fork preserves {name} byte for byte", (out / name).read_bytes() == original)
    original = json.loads((out / "original.json").read_text())
    forked = json.loads((out / "fork-effective_date.json").read_text())
    control = json.loads((out / "fork-unchanged-control.json").read_text())
    checkpoint = json.loads((out / "checkpoint-C1.json").read_text())
    fixture = graph.load_fixture()
    oracle = fixture["oracle"]
    before, after = original["state"]["values"], forked["state"]["values"]
    check("Original selects the outdated policy using actual text overlap", before["retrieve_policy"]["policy"]["id"] == "RET-2025")
    check("Original calculates 1920 from the selected rule", original["proposed_refund_rupees"] == 1920)
    check("Independent verifier blocks the original proposal", original["status"] == "BLOCKED" and original["final_refund_rupees"] is None)
    check("Date-aware fork selects the oracle policy", after["retrieve_policy"]["policy"]["id"] == oracle["policy_id"])
    check("Fork calculates the independently specified fixture refund", forked["final_refund_rupees"] == oracle["refund_rupees"] == 2400)
    check("Fork passes all final verification gates", forked["status"] == "VERIFIED" and all(after["verify_refund"]["gates"].values()))
    check("Fork executes only the three downstream tasks", set(forked["executed"]) == set(graph.SUFFIX))
    check("Fork restores the three distinct completed tasks", forked["restored"] == graph.PREFIX)
    check("Prefix artifacts and producer records are unchanged", all(before[t] == after[t] and original["state"]["records"][t] == forked["state"]["records"][t] for t in graph.PREFIX))
    check("Both forks share the same checkpoint", forked["parent_checkpoint_sha256"] == control["parent_checkpoint_sha256"] == checkpoint["sha256"])
    changes = [e for e in forked["events"] if e["event"] == "fork_created"]
    check("Exactly one declared choice changes", len(changes) == 1 and changes[0]["changed_field"] == "config.retrieval_strategy" and changes[0]["old"] == "text_match" and changes[0]["new"] == "effective_date")
    check("Unchanged-choice control reproduces the original outcome", control["state"]["values"] == original["state"]["values"] and control["status"] == original["status"])
    check("Evaluation oracle is never supplied to workers", "oracle" not in graph.Runner(fixture, "oracle-isolation").worker_fixture)
    check("No model calls or consequential external actions", all(r["model_calls"] == 0 and r["external_actions"] == [] for r in (original, forked, control)))

    corrupted = copy.deepcopy(checkpoint)
    corrupted["payload"]["state"]["values"]["lookup_order"]["paid_rupees"] = 1
    refuses("Corrupted checkpoint is rejected", lambda: graph.validate_checkpoint(corrupted, fixture))
    missing = copy.deepcopy(checkpoint)
    del missing["payload"]["state"]["values"]["inspect_return"]
    missing["sha256"] = graph.digest(missing["payload"])
    refuses("Missing required branch blocks checkpoint admission", lambda: graph.validate_checkpoint(missing, fixture))
    changed_fixture = copy.deepcopy(fixture)
    changed_fixture["orders"]["DEMO-1042"]["paid_rupees"] = 1
    refuses("Changing the dataset cannot masquerade as the same checkpoint", lambda: graph.validate_checkpoint(checkpoint, changed_fixture))
    changed_code = copy.deepcopy(checkpoint)
    changed_code["payload"]["code_sha256"] = "0" * 64
    changed_code["sha256"] = graph.digest(changed_code["payload"])
    refuses("Changed implementation rejects the saved checkpoint", lambda: graph.validate_checkpoint(changed_code, fixture))
    refuses("Unknown retrieval choice is rejected", lambda: graph.Runner(fixture, "unknown", checkpoint, "invent_policy"))
    refuses("Existing execution evidence is never overwritten", lambda: graph.baseline(out))

    failed = graph.Runner(fixture, "required-task-failure", checkpoint, "effective_date", fail_task="calculate_refund")
    failed.run_tasks(graph.SUFFIX)
    failure_result = failed.result()
    check("Failed required task is bounded to two attempts", failure_result["attempts"]["calculate_refund"] == 2)
    check("Failed required task blocks success and its dependent verifier", failure_result["status"] == "BLOCKED" and failure_result["final_refund_rupees"] is None and "verify_refund" not in failure_result["executed"])
    check("Graph dependencies contain six different task contracts", len(graph.DEPENDENCIES) == 6 and graph.DEPENDENCIES["lookup_order"] == ["validate_request"] and graph.DEPENDENCIES["inspect_return"] == ["validate_request"])

    graph.write_new(out / "required-task-failure.json", failure_result)
    graph.write_new(out / "subprocess-transcripts.json", transcripts)
    bundle = {
        "verified": all(c["passed"] for c in checks), "checks": checks,
        "original": original, "fork": forked, "control": control,
        "checkpoint": checkpoint, "fixture_sha256": graph.digest(fixture),
        "implementation_sha256": hashlib.sha256((ROOT / "fork_graph.py").read_bytes()).hexdigest(),
        "dependencies": graph.DEPENDENCIES, "oracle": oracle,
        "difference_rupees": forked["proposed_refund_rupees"] - original["proposed_refund_rupees"],
        "limits": ["Synthetic data and scripted deterministic workers; no live LLM calls.",
                   "One fixture proves this mechanism, not general reliability or causal isolation for live models.",
                   "Downstream tasks rerun. This is not a one-node-only replay.",
                   "Local cooperative execution limits; this is not a production runtime.",
                   "Hashes detect mismatches; they are not adversarial tamper protection.",
                   "No refund is sent and no customer is contacted."]
    }
    graph.write_new(out / "demo-evidence.json", bundle)
    print(json.dumps({"checks_passed": len(checks), "original_proposal": original["proposed_refund_rupees"],
                      "original_status": original["status"], "fork_refund": forked["final_refund_rupees"],
                      "fork_status": forked["status"], "changed_choice": "config.retrieval_strategy"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "evidence")
    main(parser.parse_args().out.resolve())
