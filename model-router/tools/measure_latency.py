#!/usr/bin/env python3
"""Measure submit -> durable selection latency with the simulator.

Warm: many submissions in one process. Cold: a fresh process per submission
(includes interpreter start, store open, adapter start and discovery).
This measures the routing path on *this* machine only; it is not evidence
about the owner's Mac or about live provider waits.
"""

from __future__ import annotations

import json
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROMPTS = [
    "Review this product architecture.",
    "Format my private notes into bullet points.",
    "Implement the CSV export per the agreed architecture.",
    "Score my résumé against this job description.",
    "Quick check: is this SQL safe on production?",
]

COLD_SNIPPET = r"""
import sys, time, json
t0 = time.monotonic()
sys.path.insert(0, {root!r})
from model_router.store import Store
from model_router.adapters.fake import FakeAdapter
from model_router.coordinator import Coordinator
from model_router.registry import mapping_hash_for
from model_router.contracts import Role
store = Store({data!r})
c = Coordinator(store, FakeAdapter(), live=False)
t_import = time.monotonic()
c.start()
if c.registry.active_revision(c.account_scope) is None:
    for role, model, effort in ((Role.HIGHEST, "sim-astra-1", "high"), (Role.MIDDLE, "sim-sol-1", "medium"), (Role.LOWEST, "sim-luna-1", "low")):
        c.registry.approve_mapping(c.account_scope, role, model, effort, actor="bench", confirm_hash=mapping_hash_for(c.account_scope, role, model, effort))
if store.project_by_name("Bench") is None:
    c.add_project("Bench", {data!r})
t1 = time.monotonic()
r = c.submit("Bench", {prompt!r})
print(json.dumps({{"process_to_ready_ms": (t1 - t0) * 1000, "imports_ms": (t_import - t0) * 1000, "selection_ms": r.timings_ms["submit_to_selection_ms"]}}))
"""


def pct(values, p):
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, round(p / 100 * (len(ordered) - 1)))], 2)


def summary(values):
    return {"n": len(values), "p50": pct(values, 50), "p90": pct(values, 90), "p99": pct(values, 99), "max": round(max(values), 2),
            "mean": round(statistics.mean(values), 2)}


def main() -> int:
    from model_router.adapters.fake import FakeAdapter
    from model_router.contracts import Role
    from model_router.coordinator import Coordinator
    from model_router.registry import mapping_hash_for
    from model_router.store import Store

    warm_n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    cold_n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "warm")
        coordinator = Coordinator(store, FakeAdapter(), live=False)
        coordinator.start()
        for role, model, effort in (("highest", "sim-astra-1", "high"), ("middle", "sim-sol-1", "medium"), ("lowest", "sim-luna-1", "low")):
            coordinator.registry.approve_mapping(coordinator.account_scope, Role(role), model, effort, actor="bench",
                                                 confirm_hash=mapping_hash_for(coordinator.account_scope, Role(role), model, effort))
        coordinator.add_project("Bench", tmp)
        warm = []
        for i in range(warm_n):
            result = coordinator.submit("Bench", PROMPTS[i % len(PROMPTS)])
            warm.append(result.timings_ms["submit_to_selection_ms"])
        coordinator.close()
        store.close()
        cold_selection, cold_process = [], []
        for i in range(cold_n):
            data = str(Path(tmp) / "cold")
            code = COLD_SNIPPET.format(root=str(ROOT), data=data, prompt=PROMPTS[i % len(PROMPTS)])
            started = time.monotonic()
            out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
            wall = (time.monotonic() - started) * 1000
            values = json.loads(out.stdout.strip().splitlines()[-1])
            cold_selection.append(values["selection_ms"])
            cold_process.append(wall)
    report = {
        "measured": "submit -> durable model selection (simulator adapter; excludes eligibility and output generation)",
        "machine": {"platform": platform.platform(), "python": platform.python_version(), "note": "build container, NOT the owner's Mac"},
        "warm_selection_ms": summary(warm),
        "cold_selection_ms_after_process_ready": summary(cold_selection),
        "cold_process_wall_ms_including_interpreter": summary(cold_process),
        "over_1s": sum(v > 1000 for v in warm + cold_selection),
        "over_4s": sum(v > 4000 for v in warm + cold_selection),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
