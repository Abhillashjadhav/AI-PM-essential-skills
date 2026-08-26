"""Reference JSON-over-stdio adapter for the synthetic return-policy system."""

from __future__ import annotations

import hashlib
import json
import sys


request = json.load(sys.stdin)
case_id = request["case_id"]
if case_id == "A400":
    category, method, message = "electronics", "in-store", "Yes. Return the TV in-store."
elif case_id == "A500":
    category, method, message = "bedding", "mail-back", "Yes. Return the quilt by mail."
else:
    raise SystemExit(f"unknown synthetic case: {case_id}")

print(
    json.dumps(
        {
            "status": "completed",
            "environment_fingerprint": hashlib.sha256(
                b"return-policy-fixture-v1"
            ).hexdigest(),
            "isolation_id": request["trial_id"],
            "outcome": {
                "decision": "ALLOW",
                "method": method,
                "message": message,
            },
            "trajectory": [
                {
                    "index": 1,
                    "type": "tool",
                    "name": "get_policy_doc",
                    "attributes": {"category": category},
                }
            ],
            "metrics": {
                "latency_ms": 1,
                "input_tokens": 1,
                "output_tokens": 1,
                "cost_usd": 0,
                "retries": 0,
            },
            "missing_evidence": [],
        },
        sort_keys=True,
    )
)
