"""Run the real graph with readable, immediate terminal output.

The optional reading delay pauses the coordinator after a printed event. It is
excluded from the core cooperative work clock and is not a latency benchmark.
All task results are computed by fork_graph.Runner during this invocation.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import fork_graph as graph

ROOT = Path(__file__).resolve().parent
RESET, BOLD, GRAY = "\033[0m", "\033[1m", "\033[90m"
GREEN, RED, AMBER = "\033[92m", "\033[91m", "\033[93m"
LABELS = {"validate_request": "Validate request", "lookup_order": "Retrieve order",
          "inspect_return": "Check return evidence", "retrieve_policy": "Retrieve policy",
          "calculate_refund": "Calculate refund", "verify_refund": "Verify proposal"}


def say(line="", tone="", delay=0.0):
    print(tone + line + RESET, flush=True)
    if delay:
        time.sleep(delay)


def amount(value):
    return f"₹{value:,}"


class TerminalRunner(graph.Runner):
    def __init__(self, *args, reading_delay=0.65, **kwargs):
        self.reading_delay = reading_delay
        super().__init__(*args, **kwargs)

    def event(self, event, **fields):
        super().event(event, **fields)
        began = time.monotonic()
        task = fields.get("task")
        if event == "task_started":
            number = list(graph.DEPENDENCIES).index(task) + 1
            say(f"[{number}/6] {LABELS[task]} ...", GRAY, self.reading_delay)
        elif event == "task_completed":
            value = fields["value"]
            if task == "validate_request":
                say("      request validated", delay=self.reading_delay)
            elif task == "lookup_order":
                say(f"      order {amount(value['paid_rupees'])}", delay=self.reading_delay)
            elif task == "inspect_return":
                say("      arrival damage confirmed" if value["condition"] == "arrived_damaged" else "      change of mind", delay=self.reading_delay)
            elif task == "retrieve_policy":
                policy = value["policy"]
                say(f"      selected {policy['id']}", BOLD, self.reading_delay)
                if policy["effective_to"]:
                    say(f"      expired {policy['effective_to']}", AMBER, self.reading_delay)
                else:
                    say(f"      valid from {policy['effective_from']}", delay=self.reading_delay)
            elif task == "calculate_refund":
                say(f"      proposed refund: {amount(value['refund_rupees'])}", BOLD, self.reading_delay)
            elif task == "verify_refund":
                passed = value["status"] == "PASS"
                say("      PASS: policy + amount agree" if passed else "      FAIL: expired policy / wrong amount", GREEN if passed else RED, self.reading_delay)
        elif event == "checkpoint_saved":
            # The core signals a snapshot; the wrapper announces SAVED only
            # after the file has actually been written by graph.write_new.
            pass
        elif event == "fork_created":
            say(f"Restored C1: {fields['parent_checkpoint_sha256'][:12]}", delay=self.reading_delay)
            say(f"Changed: {fields['old']} -> {fields['new']}", AMBER, self.reading_delay)
        elif event == "task_restored":
            say(f"KEPT  {LABELS[task]}", GRAY, self.reading_delay)
        elif event == "task_failed":
            say(f"FAILED {LABELS[task]}: {fields['reason']}", RED)
        elif event in {"join_blocked", "run_blocked"}:
            say("BLOCKED: required evidence is missing", RED)
        self.started += time.monotonic() - began


def initial(out, delay):
    if out.exists():
        raise FileExistsError("Use a new output directory")
    out.mkdir(parents=True)
    fixture = graph.load_fixture()
    say("Fresh run | fictional damaged return", BOLD, delay)
    say("Lookup: text match only", GRAY, delay)
    run = TerminalRunner(fixture, "recorded-original", reading_delay=delay)
    if not run.run_tasks(graph.PREFIX):
        raise RuntimeError("Required prefix task failed")
    cp = run.snapshot()
    graph.write_new(out / "checkpoint-C1.json", cp)
    paused = time.monotonic()
    say(f"SAVED C1: {cp['sha256'][:12]}", AMBER, delay*2)
    say("Continuing from the saved decision point", GRAY, delay)
    run.started += time.monotonic() - paused
    run.run_tasks(graph.SUFFIX)
    result = run.result()
    graph.write_new(out / "original.json", result)
    protected = {name: hashlib.sha256((out/name).read_bytes()).hexdigest()
                 for name in ("checkpoint-C1.json", "original.json")}
    graph.write_new(out / "preserved-hashes.json", protected)
    say(f"RESULT {result['status']} | no refund sent", RED, delay)
    say("Original run and checkpoint saved.", GRAY)


def resume(out, delay):
    cp = json.loads((out / "checkpoint-C1.json").read_text())
    say("Fork the saved run | same customer facts", BOLD, delay)
    run = TerminalRunner(graph.load_fixture(), "recorded-fork", cp, "effective_date", reading_delay=delay)
    run.run_tasks(graph.SUFFIX)
    result = run.result()
    graph.write_new(out / "fork-effective_date.json", result)
    say(f"RESULT {result['status']} | {amount(result['final_refund_rupees'])}", GREEN, delay)
    say("Separate fork saved. No refund sent.", GRAY)


def verify(out, delay):
    a = json.loads((out / "original.json").read_text())
    b = json.loads((out / "fork-effective_date.json").read_text())
    cp = json.loads((out / "checkpoint-C1.json").read_text())
    protected = json.loads((out / "preserved-hashes.json").read_text())
    tests = {
        "original proposal blocked": a["proposed_refund_rupees"] == 1920 and a["final_refund_rupees"] is None and a["status"] == "BLOCKED",
        "fork verified at the fixture amount": b["final_refund_rupees"] == graph.load_fixture()["oracle"]["refund_rupees"] == 2400 and b["status"] == "VERIFIED",
        "same saved starting point": b["parent_checkpoint_sha256"] == cp["sha256"],
        "prefix artifacts unchanged": all(a["state"]["values"][t] == b["state"]["values"][t] and a["state"]["records"][t] == b["state"]["records"][t] for t in graph.PREFIX),
        "only downstream tasks rerun": set(b["executed"]) == set(graph.SUFFIX),
        "one retrieval choice changed": a["state"]["config"] == {"retrieval_strategy":"text_match"} and b["state"]["config"] == {"retrieval_strategy":"effective_date"},
        "both original files preserved": all(hashlib.sha256((out/name).read_bytes()).hexdigest() == expected for name,expected in protected.items()),
        "no live model or external action": a["model_calls"] == b["model_calls"] == 0 and a["external_actions"] == b["external_actions"] == [],
    }
    assert all(tests.values()), tests
    say(f"Recorded-run checks: {len(tests)}/{len(tests)} PASS", GREEN, delay)
    say("Checking the core implementation ...", GRAY, delay)
    core_out = out / "core-verification"
    result = subprocess.run([sys.executable, str(ROOT/"verify_demo.py"), "--out", str(core_out)],
                            cwd=ROOT, check=True, capture_output=True, text=True, timeout=20)
    core = json.loads(result.stdout)
    say(f"Core checks: {core['checks_passed']}/{core['checks_passed']} PASS", GREEN, delay)
    difference = b["final_refund_rupees"] - a["proposed_refund_rupees"]
    say(f"One lookup choice changed the proposal by {amount(difference)}.", BOLD, delay)
    say("Original history and C1 are unchanged.", delay=delay)
    graph.write_new(out/"recording-verification.json", {"passed":True,"checks":tests,
                    "core_checks_passed":core["checks_passed"],"difference_rupees":difference,
                    "reading_delays_excluded_from_work_clock":True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["baseline","fork","check"])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--delay", type=float, default=0.65)
    args = parser.parse_args()
    if not 0 <= args.delay <= 2:
        raise ValueError("Reading delay must be between zero and two seconds")
    {"baseline":initial,"fork":resume,"check":verify}[args.command](args.out.resolve(), args.delay)


if __name__ == "__main__":
    main()
