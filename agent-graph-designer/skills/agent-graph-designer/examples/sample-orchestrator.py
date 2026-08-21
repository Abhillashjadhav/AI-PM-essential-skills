#!/usr/bin/env python3
"""Run the synthetic graph example without external services or model calls."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


CONTRACT_PATH = Path(__file__).with_name("sample-graph-contract.json")
REVIEW_NODES = (
    "product-outcome-review",
    "model-quality-review",
    "safety-privacy-review",
)


def load_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def review(node_id: str, digest: str) -> dict[str, Any]:
    fixtures = {
        "product-outcome-review": ["outcome threshold present", "evidence links present"],
        "model-quality-review": ["binary gates reported", "uncertainty recorded"],
        "safety-privacy-review": ["restricted-data gate reported", "unsafe-output gate reported"],
    }
    return {
        "node_id": node_id,
        "candidate_digest": digest,
        "schema": "review-v1",
        "status": "PASS",
        "checks": fixtures[node_id],
        "verified_by": f"independent-{node_id}-verifier",
    }


def run() -> dict[str, Any]:
    contract = load_contract()
    if contract["qualification"]["verdict"] != "GRAPH_REQUIRED":
        raise ValueError("sample contract must qualify as GRAPH_REQUIRED")
    if contract["concurrency_cap"] < len(REVIEW_NODES):
        raise ValueError("concurrency cap cannot run the declared fan-out")

    candidate = b"synthetic-support-ticket-summarizer-v1"
    digest = "sha256:" + hashlib.sha256(candidate).hexdigest()

    with ThreadPoolExecutor(max_workers=contract["concurrency_cap"]) as pool:
        futures = {node_id: pool.submit(review, node_id, digest) for node_id in REVIEW_NODES}
        branch_results = {node_id: future.result() for node_id, future in futures.items()}

    join = contract["joins"][0]
    required = set(join["required_branches"])
    if set(branch_results) != required:
        raise ValueError("ALL_REQUIRED join is missing a branch")
    if any(result["candidate_digest"] != digest for result in branch_results.values()):
        raise ValueError("branch candidate digests conflict")
    if any(result["schema"] != join["artifact_schema"] for result in branch_results.values()):
        raise ValueError("branch artifact schema mismatch")
    if any(result["status"] != "PASS" for result in branch_results.values()):
        raise ValueError("a required review did not pass")

    return {
        "contract": contract["name"],
        "candidate_digest": digest,
        "completed_branches": sorted(branch_results),
        "join_policy": join["policy"],
        "recommendation": "EVIDENCE_READY_FOR_HUMAN_DECISION",
        "status": "AWAITING_HUMAN_APPROVAL",
        "external_actions_taken": [],
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
