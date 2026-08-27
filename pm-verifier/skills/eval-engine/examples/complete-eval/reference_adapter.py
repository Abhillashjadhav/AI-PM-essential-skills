"""Deterministic four-surface adapter for a synthetic support workflow."""

from __future__ import annotations

import hashlib
import json
import sys


request = json.load(sys.stdin)
payload = request["input"]
ticket_id = payload["ticket_id"]
customer_id = payload["customer_id"]
content_id = payload["content_id"]
memory_script = payload["memory_script"]

rules = {
    "refund": ("REFUND", "refund-policy-v3", "The eligible order will be refunded."),
    "missing_delivery": (
        "REPLACE",
        "delivery-policy-v2",
        "A replacement shipment will be created.",
    ),
}
try:
    decision, policy_id, message = rules[payload["issue_type"]]
except KeyError as exc:
    raise SystemExit(f"unknown synthetic issue type: {payload.get('issue_type')}") from exc

checkpoint_names = ["intake", "identity", "policy", "decision", "delivery"]
continuous_state = {"customer_id": customer_id, "content_id": content_id}
scope = {
    "session_id": f"session-{request['trial_id']}",
    "user_id": customer_id,
    "project_id": "synthetic-support-project",
}
updated_language = memory_script["updated_language"]

print(
    json.dumps(
        {
            "environment_fingerprint": hashlib.sha256(
                b"synthetic-support-complete-v1"
            ).hexdigest(),
            "isolation_id": f"isolation-{request['trial_id']}",
            "memory": {
                "conflicts": [
                    {
                        "key": "language",
                        "policy": "latest_write_wins",
                        "status": "resolved",
                        "winner_version": 2,
                    }
                ],
                "events": [
                    {
                        "index": 1,
                        "key": "language",
                        "occurred_at": "2026-08-27T00:00:01+00:00",
                        "operation": "write",
                        "scope": scope,
                        "status": "passed",
                        "value": memory_script["initial_language"],
                        "version": 1,
                    },
                    {
                        "age_seconds": 0,
                        "index": 2,
                        "key": "language",
                        "occurred_at": "2026-08-27T00:00:02+00:00",
                        "operation": "retrieve",
                        "scope": scope,
                        "status": "passed",
                        "value": memory_script["initial_language"],
                        "version": 1,
                    },
                    {
                        "index": 3,
                        "key": "language",
                        "occurred_at": "2026-08-27T00:00:03+00:00",
                        "operation": "update",
                        "scope": scope,
                        "status": "passed",
                        "value": updated_language,
                        "version": 2,
                    },
                    {
                        "age_seconds": 0,
                        "index": 4,
                        "key": "language",
                        "occurred_at": "2026-08-27T00:00:04+00:00",
                        "operation": "retrieve",
                        "scope": scope,
                        "status": "passed",
                        "value": updated_language,
                        "version": 2,
                    },
                    {
                        "index": 5,
                        "key": "language",
                        "occurred_at": "2026-08-27T00:00:05+00:00",
                        "operation": "delete",
                        "scope": scope,
                        "status": "passed",
                        "value": None,
                        "version": 3,
                    },
                ],
                "final_state": {},
                "isolation_checks": [
                    {
                        "dimension": dimension,
                        "passed": True,
                        "reason": "no cross-scope read observed",
                    }
                    for dimension in ("session", "user", "project")
                ],
            },
            "metrics": {
                "cost_usd": 0,
                "input_tokens": 12,
                "latency_ms": 5,
                "output_tokens": 8,
                "retries": 0,
            },
            "missing_evidence": [],
            "outcome": {"decision": decision, "message": message, "ticket_id": ticket_id},
            "status": "completed",
            "system": {
                "checkpoints": [
                    {
                        "entity_id": ticket_id,
                        "index": index,
                        "name": name,
                        "reason": "synthetic checkpoint completed",
                        "state": continuous_state,
                        "status": "passed",
                    }
                    for index, name in enumerate(checkpoint_names, 1)
                ],
                "completed": True,
                "consequences": [],
                "entity_id": ticket_id,
                "first_failure_stage": None,
            },
            "trajectory": [
                {
                    "attributes": {"ticket_id": ticket_id},
                    "index": 1,
                    "name": "intake_ticket",
                    "type": "tool",
                },
                {
                    "attributes": {"customer_id": customer_id},
                    "index": 2,
                    "name": "resolve_identity",
                    "type": "tool",
                },
                {
                    "attributes": {"policy_id": policy_id},
                    "index": 3,
                    "name": "load_policy",
                    "type": "tool",
                },
                {
                    "attributes": {"decision": decision},
                    "index": 4,
                    "name": "decide",
                    "type": "decision",
                },
                {
                    "attributes": {"ticket_id": ticket_id},
                    "index": 5,
                    "name": "deliver",
                    "type": "tool",
                },
            ],
        },
        sort_keys=True,
    )
)
