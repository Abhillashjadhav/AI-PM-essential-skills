#!/usr/bin/env python3
"""Truthful end-to-end synthetic ContextPort demonstration."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import chatgpt_adapter
import contextport
import reconciliation
import reconstruction
import review
import segregation


DEMO_VERSION = "0.1"
REVISION = re.compile(r"^[0-9a-f]{40}$")


class DemoError(ValueError):
    """Raised when the synthetic demonstration cannot prove a stage outcome."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DemoError(f"expected object in {path.name}")
    return value


def _revision(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    )
    revision = result.stdout.strip()
    if not REVISION.fullmatch(revision):
        raise DemoError("git did not return a full lowercase commit revision")
    return revision


def run_demo(root: Path) -> dict[str, Any]:
    """Run every safe synthetic migration stage and return observable evidence."""
    revision = _revision(root)
    fixtures = root / "fixtures"
    source_path = fixtures / "segregation-contextpack.json"
    document = _load(source_path)
    mappings = _load(fixtures / "project-mappings-valid.json")
    decision = _load(fixtures / "review-decision-approved.json")

    validation_errors = contextport.validate(document)
    if validation_errors:
        raise DemoError(f"synthetic ContextPack failed validation: {validation_errors}")
    segregation_plan = segregation.segregate(document, mappings, validator=contextport.validate)
    if segregation_plan["status"] != "ready":
        raise DemoError("synthetic segregation did not become ready")
    review_package = review.build_review_package(document, segregation_plan)
    if review_package != _load(fixtures / "review-package-synthetic.json"):
        raise DemoError("synthetic review package does not match its reviewed fixture")
    validated_decision = review.validate_decision(review_package, decision)
    if validated_decision["decision"] != "approve":
        raise DemoError("synthetic review fixture is not approved")
    reconstruction_plan = reconstruction.build_reconstruction_plan(
        document, segregation_plan, review_package, decision
    )
    reconciliation_report = reconciliation.reconcile(document, reconstruction_plan)
    if reconciliation_report["status"] != "clean":
        raise DemoError("independent synthetic reconciliation found differences")
    adapter_report = chatgpt_adapter.build_chatgpt_adapter_report(reconstruction_plan)
    if adapter_report["status"] != "blocked_unsupported":
        raise DemoError("ChatGPT adapter did not fail closed")

    source_inventory = {
        "projects": len(document["projects"]),
        "conversations": len(document["conversations"]),
        "messages": len(document["messages"]),
        "attachments": len(document["attachments"]),
    }
    source_inventory["inventory_sha256"] = review.canonical_digest(source_inventory)
    stage = lambda name, status="VERIFIED": {
        "stage": name,
        "status": status,
        "exit_state": "completed",
        "exit_code": 0,
    }
    stages = [
        {**stage("contextpack_validation"), "errors": 0},
        {
            **stage("project_segregation"),
            "plan_sha256": segregation_plan["plan_sha256"],
            "groups": segregation_plan["summary"]["project_groups"]
            + segregation_plan["summary"]["ungrouped_groups"],
            "conversations": segregation_plan["summary"]["conversations"],
        },
        {
            **stage("human_review_fixture"),
            "review_package_sha256": review_package["review_package_sha256"],
            "decision": validated_decision["decision"],
        },
        {
            **stage("reconstruction_dry_run"),
            "plan_sha256": reconstruction_plan["reconstruction_plan_sha256"],
            "operations": reconstruction_plan["summary"]["operations"],
            "writes_performed": reconstruction_plan["writes_performed"],
        },
        {
            **stage("independent_reconciliation"),
            "report_sha256": reconciliation_report["reconciliation_report_sha256"],
            "differences": reconciliation_report["summary"]["differences"],
        },
        {
            **stage("chatgpt_capability_assessment", "UNSUPPORTED"),
            "adapter_report_sha256": adapter_report["adapter_report_sha256"],
            "operations_not_written": adapter_report["summary"]["unsupported"],
            "writes_performed": adapter_report["writes_performed"],
        },
    ]
    not_copied = [
        {
            "operation_id": item["operation_id"],
            "kind": item["kind"],
            "status": "unsupported",
            "reason": item["reason_code"],
        }
        for item in adapter_report["operation_assessments"]
    ]
    report = {
        "demo_version": DEMO_VERSION,
        "revision": revision,
        "provenance": "synthetic_committed_fixtures",
        "claims": {
            "synthetic_pipeline": "VERIFIED",
            "real_claude_export_compatibility": "UNKNOWN",
            "chatgpt_reconstruction_writes": "UNSUPPORTED",
        },
        "stages": stages,
        "source": {
            "artifact": source_path.name,
            "artifact_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "declared_source_sha256": document["manifest"]["source"]["artifact_sha256"],
            "inventory": source_inventory,
        },
        "destination_inventory": {
            "status": "UNSUPPORTED",
            "observed": False,
            "projects": None,
            "conversations": None,
            "messages": None,
            "inventory_sha256": None,
            "reason": "PUBLIC_CHATGPT_WRITE_API_NOT_VERIFIED",
        },
        "writes_performed": False,
        "network_calls_performed": False,
        "browser_automation_performed": False,
        "dispositions": {
            "copied": [],
            "transformed": [],
            "skipped": [],
            "ambiguous": [],
            "failed": [],
            "unsupported": not_copied,
        },
        "everything_not_copied": not_copied,
        "environment": {
            "python": platform.python_version(),
            "platform": sys.platform,
            "real_export_access": False,
            "destination_observation": False,
        },
        "limitations": [
            {"capability": "real_claude_export_parsing", "status": "UNKNOWN"},
            {"capability": "consumer_chatgpt_reconstruction", "status": "UNSUPPORTED"},
            {"capability": "destination_inventory_observation", "status": "UNSUPPORTED"},
        ],
    }
    report["demo_report_sha256"] = review.canonical_digest(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="contextport-demo", description=__doc__)
    arguments = parser.parse_args(argv)
    root = Path(__file__).resolve().parent
    try:
        report = run_demo(root)
    except (DemoError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
