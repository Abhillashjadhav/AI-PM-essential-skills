"""Deterministic JSON-over-stdio adapter for the ticket-summarizer starter."""

from __future__ import annotations

import hashlib
import json
import sys


OUTPUTS = {
    "TS-100": {
        "summary": "The customer needs an August invoice export. Three timeout failures are blocking month-end close, and the customer requested escalation.",
        "customer_request": "Escalate the failed August invoice export.",
        "sentiment": "frustrated",
        "escalation_reason": "Repeated export failures are blocking month-end close.",
        "supported_claims": [
            "August invoice export requested",
            "Export failed three times",
            "Month-end close is blocked",
            "Customer requested escalation",
        ],
    },
    "TS-200": {
        "summary": "The team is evaluating SSO and wants to know whether it supports Okta. The request is not urgent.",
        "customer_request": "Confirm whether SSO supports Okta.",
        "sentiment": "neutral",
        "escalation_reason": "NONE",
        "supported_claims": [
            "Team is evaluating SSO",
            "Customer asked about Okta compatibility",
            "Request is not urgent",
        ],
    },
    "TS-300": {
        "summary": "The customer was locked out after enabling MFA. A password reset completed, but account access is still blocked.",
        "customer_request": "Restore account access after MFA lockout and a failed password reset.",
        "sentiment": "frustrated",
        "escalation_reason": "Account access remains blocked after a completed reset.",
        "supported_claims": [
            "MFA preceded the lockout",
            "Password reset completed",
            "Customer still cannot sign in",
        ],
    },
}


request = json.load(sys.stdin)
case_id = request["case_id"]
case_input = request["input"]
configured = OUTPUTS.get(case_id)
if configured is None:
    raise SystemExit(f"unknown product use case: {case_id}")

chronological_ids = [row["id"] for row in reversed(case_input["messages"])]
checkpoint_names = ["intake", "order", "summarize", "validate", "deliver"]
continuous_state = {
    "thread_id": case_id,
    "message_count": len(case_input["messages"]),
}
print(
    json.dumps(
        {
            "status": "completed",
            "environment_fingerprint": hashlib.sha256(
                b"ticket-summarizer-starter-v1"
            ).hexdigest(),
            "isolation_id": request["trial_id"],
            "outcome": {
                "response": {
                    "summary": configured["summary"],
                    "customer_request": configured["customer_request"],
                },
                "sentiment": configured["sentiment"],
                "escalation_reason": configured["escalation_reason"],
                "supported_claims": configured["supported_claims"],
            },
            "trajectory": [
                {
                    "index": 1,
                    "type": "tool",
                    "name": "order_messages",
                    "attributes": {
                        "chronological_ids": chronological_ids,
                        "source_message_count": len(case_input["messages"]),
                    },
                },
                {
                    "index": 2,
                    "type": "model",
                    "name": "summarize_thread",
                    "attributes": {"case_id": case_id},
                },
                {
                    "index": 3,
                    "type": "tool",
                    "name": "validate_claims",
                    "attributes": {
                        "supported_claim_count": len(configured["supported_claims"])
                    },
                },
                {
                    "index": 4,
                    "type": "tool",
                    "name": "deliver_summary",
                    "attributes": {"case_id": case_id},
                },
            ],
            "system": {
                "checkpoints": [
                    {
                        "entity_id": case_id,
                        "index": index,
                        "name": name,
                        "reason": "required ticket-summarizer stage completed",
                        "state": continuous_state,
                        "status": "passed",
                    }
                    for index, name in enumerate(checkpoint_names, 1)
                ],
                "completed": True,
                "consequences": [],
                "entity_id": case_id,
                "first_failure_stage": None,
            },
            "metrics": {
                "latency_ms": 4,
                "input_tokens": 50,
                "output_tokens": 35,
                "cost_usd": 0,
                "retries": 0,
            },
            "missing_evidence": [],
        },
        sort_keys=True,
    )
)
