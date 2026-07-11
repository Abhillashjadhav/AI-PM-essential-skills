"""Offline ChatGPT capability adapter; it never performs destination writes."""

from __future__ import annotations

import copy
from typing import Any

from review import canonical_digest


ADAPTER_VERSION = "0.1"
DESTINATION = "chatgpt_consumer"
CAPABILITY_STATUS = "UNSUPPORTED"
SUPPORTED_KINDS = {"ensure_container", "ensure_conversation", "append_message"}


class ChatGPTAdapterError(ValueError):
    """Raised when an unsafe or malformed adapter input is supplied."""


def build_chatgpt_adapter_report(plan: dict[str, Any]) -> dict[str, Any]:
    """Classify a reconstruction plan against verified public ChatGPT capabilities."""
    if plan.get("reconstruction_version") != "0.1":
        raise ChatGPTAdapterError("unsupported reconstruction plan version")
    if plan.get("status") != "dry_run_ready" or plan.get("review_decision") != "approve":
        raise ChatGPTAdapterError("adapter requires an approved dry-run reconstruction plan")
    if plan.get("writes_performed") is not False:
        raise ChatGPTAdapterError("input plan must not claim destination writes")
    supplied_digest = plan.get("reconstruction_plan_sha256")
    if not isinstance(supplied_digest, str):
        raise ChatGPTAdapterError("reconstruction plan digest is required")
    digest_input = {key: value for key, value in plan.items() if key != "reconstruction_plan_sha256"}
    if canonical_digest(digest_input) != supplied_digest:
        raise ChatGPTAdapterError("reconstruction plan digest does not match content")

    assessments: list[dict[str, Any]] = []
    operation_ids: set[str] = set()
    for operation in plan.get("operations", []):
        operation_id = operation.get("operation_id")
        kind = operation.get("kind")
        if not isinstance(operation_id, str) or not operation_id:
            raise ChatGPTAdapterError("every operation requires an operation_id")
        if operation_id in operation_ids:
            raise ChatGPTAdapterError(f"duplicate operation_id {operation_id!r}")
        operation_ids.add(operation_id)
        if kind not in SUPPORTED_KINDS:
            raise ChatGPTAdapterError(f"unknown reconstruction operation kind {kind!r}")
        assessments.append(
            {
                "operation_id": operation_id,
                "kind": kind,
                "capability_status": CAPABILITY_STATUS,
                "reason_code": "PUBLIC_CHATGPT_WRITE_API_NOT_VERIFIED",
                "source_operation": copy.deepcopy(operation),
                "write_attempted": False,
            }
        )

    report = {
        "adapter_version": ADAPTER_VERSION,
        "destination": DESTINATION,
        "status": "blocked_unsupported",
        "source_reconstruction_plan_sha256": supplied_digest,
        "capability_evidence": {
            "classification": CAPABILITY_STATUS,
            "verified_at": "2026-07-11",
            "scope": "public consumer ChatGPT Projects reconstruction",
            "finding": "No public API for creating ChatGPT Projects, chats, or historical messages was verified.",
            "api_platform_projects_are_destination_equivalent": False,
        },
        "operation_assessments": assessments,
        "writes_performed": False,
        "network_calls_performed": False,
        "browser_automation_performed": False,
        "summary": {
            "operations": len(assessments),
            "supported": 0,
            "unsupported": len(assessments),
        },
    }
    report["adapter_report_sha256"] = canonical_digest(report)
    return report
