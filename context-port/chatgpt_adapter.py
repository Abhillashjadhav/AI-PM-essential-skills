"""Offline ChatGPT capability adapter; it never performs destination writes."""

from __future__ import annotations

import copy
import re
from typing import Any

from review import canonical_digest


ADAPTER_VERSION = "0.1"
DESTINATION = "chatgpt_consumer"
CAPABILITY_STATUS = "UNSUPPORTED"
SUPPORTED_KINDS = {"ensure_container", "ensure_conversation", "append_message"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_PLAN_FIELDS = {
    "reconstruction_version",
    "status",
    "source_artifact_sha256",
    "segregation_plan_sha256",
    "review_package_sha256",
    "review_decision",
    "operations",
    "dispositions",
    "writes_performed",
    "summary",
    "reconstruction_plan_sha256",
}


class ChatGPTAdapterError(ValueError):
    """Raised when an unsafe or malformed adapter input is supplied."""


def build_chatgpt_adapter_report(plan: dict[str, Any]) -> dict[str, Any]:
    """Classify a reconstruction plan against verified public ChatGPT capabilities."""
    if not isinstance(plan, dict):
        raise ChatGPTAdapterError("reconstruction plan must be an object")
    missing = sorted(REQUIRED_PLAN_FIELDS - plan.keys())
    if missing:
        raise ChatGPTAdapterError(f"reconstruction plan is missing required fields: {', '.join(missing)}")
    if plan.get("reconstruction_version") != "0.1":
        raise ChatGPTAdapterError("unsupported reconstruction plan version")
    if plan.get("status") != "dry_run_ready" or plan.get("review_decision") != "approve":
        raise ChatGPTAdapterError("adapter requires an approved dry-run reconstruction plan")
    if plan.get("writes_performed") is not False:
        raise ChatGPTAdapterError("input plan must not claim destination writes")
    for field in (
        "source_artifact_sha256",
        "segregation_plan_sha256",
        "review_package_sha256",
        "reconstruction_plan_sha256",
    ):
        if not isinstance(plan[field], str) or not SHA256.fullmatch(plan[field]):
            raise ChatGPTAdapterError(f"{field} must be a lowercase SHA-256 digest")
    supplied_digest = plan["reconstruction_plan_sha256"]
    digest_input = {key: value for key, value in plan.items() if key != "reconstruction_plan_sha256"}
    if canonical_digest(digest_input) != supplied_digest:
        raise ChatGPTAdapterError("reconstruction plan digest does not match content")

    if not isinstance(plan["operations"], list):
        raise ChatGPTAdapterError("operations must be an array")
    if not isinstance(plan["dispositions"], list):
        raise ChatGPTAdapterError("dispositions must be an array")
    summary = plan["summary"]
    if not isinstance(summary, dict):
        raise ChatGPTAdapterError("summary must be an object")
    expected_summary = {"operations", "containers", "conversations", "messages"}
    if not expected_summary.issubset(summary):
        raise ChatGPTAdapterError("summary is missing required counts")
    if any(not isinstance(summary[key], int) or isinstance(summary[key], bool) or summary[key] < 0 for key in expected_summary):
        raise ChatGPTAdapterError("summary counts must be non-negative integers")

    assessments: list[dict[str, Any]] = []
    operation_ids: set[str] = set()
    for operation in plan["operations"]:
        if not isinstance(operation, dict):
            raise ChatGPTAdapterError("every operation must be an object")
        required_operation = {"operation_id", "kind", "idempotency_key", "depends_on", "target", "payload"}
        if not required_operation.issubset(operation):
            raise ChatGPTAdapterError("every operation must satisfy the reconstruction operation contract")
        operation_id = operation.get("operation_id")
        kind = operation.get("kind")
        if not isinstance(operation_id, str) or not operation_id:
            raise ChatGPTAdapterError("every operation requires an operation_id")
        if operation_id in operation_ids:
            raise ChatGPTAdapterError(f"duplicate operation_id {operation_id!r}")
        operation_ids.add(operation_id)
        if kind not in SUPPORTED_KINDS:
            raise ChatGPTAdapterError(f"unknown reconstruction operation kind {kind!r}")
        if not isinstance(operation["idempotency_key"], str) or not SHA256.fullmatch(operation["idempotency_key"]):
            raise ChatGPTAdapterError("operation idempotency_key must be a lowercase SHA-256 digest")
        if not isinstance(operation["depends_on"], list) or not all(isinstance(item, str) for item in operation["depends_on"]):
            raise ChatGPTAdapterError("operation depends_on must be an array of strings")
        if not isinstance(operation["target"], dict) or not isinstance(operation["payload"], dict):
            raise ChatGPTAdapterError("operation target and payload must be objects")
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
            "finding": "A bounded review of cited public documentation did not verify an API for creating ChatGPT Projects, chats, or historical messages.",
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
