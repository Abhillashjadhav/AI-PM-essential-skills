#!/usr/bin/env python3
"""Truthful end-to-end synthetic ContextPort demonstration."""

from __future__ import annotations

import argparse
import json
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


def run_demo(root: Path, revision: str) -> dict[str, Any]:
    """Run every safe synthetic migration stage and return observable evidence."""
    if not REVISION.fullmatch(revision):
        raise DemoError("revision must be a full lowercase Git commit")
    fixtures = root / "fixtures"
    document = _load(fixtures / "segregation-contextpack.json")
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

    report = {
        "demo_version": DEMO_VERSION,
        "revision": revision,
        "provenance": "synthetic_committed_fixtures",
        "claims": {
            "synthetic_pipeline": "VERIFIED",
            "real_claude_export_compatibility": "UNKNOWN",
            "chatgpt_reconstruction_writes": "UNSUPPORTED",
        },
        "stages": [
            {"stage": "contextpack_validation", "status": "VERIFIED", "errors": 0},
            {
                "stage": "project_segregation",
                "status": "VERIFIED",
                "plan_sha256": segregation_plan["plan_sha256"],
                "groups": (
                    segregation_plan["summary"]["project_groups"]
                    + segregation_plan["summary"]["ungrouped_groups"]
                ),
                "conversations": segregation_plan["summary"]["conversations"],
            },
            {
                "stage": "human_review_fixture",
                "status": "VERIFIED",
                "review_package_sha256": review_package["review_package_sha256"],
                "decision": validated_decision["decision"],
            },
            {
                "stage": "reconstruction_dry_run",
                "status": "VERIFIED",
                "plan_sha256": reconstruction_plan["reconstruction_plan_sha256"],
                "operations": reconstruction_plan["summary"]["operations"],
                "writes_performed": reconstruction_plan["writes_performed"],
            },
            {
                "stage": "independent_reconciliation",
                "status": "VERIFIED",
                "report_sha256": reconciliation_report["reconciliation_report_sha256"],
                "differences": reconciliation_report["summary"]["differences"],
            },
            {
                "stage": "chatgpt_capability_assessment",
                "status": "UNSUPPORTED",
                "adapter_report_sha256": adapter_report["adapter_report_sha256"],
                "operations_not_written": adapter_report["summary"]["unsupported"],
                "writes_performed": adapter_report["writes_performed"],
            },
        ],
        "source_inventory": {
            "projects": len(document["projects"]),
            "conversations": len(document["conversations"]),
            "messages": len(document["messages"]),
            "attachments": len(document["attachments"]),
        },
        "writes_performed": False,
        "network_calls_performed": False,
        "browser_automation_performed": False,
        "everything_not_copied": [
            {
                "destination": "chatgpt_consumer",
                "count": adapter_report["summary"]["unsupported"],
                "reason": "PUBLIC_CHATGPT_WRITE_API_NOT_VERIFIED",
            }
        ],
    }
    report["demo_report_sha256"] = review.canonical_digest(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="contextport-demo", description=__doc__)
    parser.add_argument("--revision", help="full Git revision; defaults to the current checkout HEAD")
    arguments = parser.parse_args(argv)
    root = Path(__file__).resolve().parent
    try:
        revision = arguments.revision or _revision(root)
        report = run_demo(root, revision)
    except (DemoError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
