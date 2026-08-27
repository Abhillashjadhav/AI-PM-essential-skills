"""Deterministic candidate behavior for the synthetic support pilot."""

from __future__ import annotations


SUPPORT_RULES = {
    "refund": ("REFUND", "refund-policy-v3", "The eligible order will be refunded."),
    "missing_delivery": (
        "REPLACE",
        "delivery-policy-v2",
        "A replacement shipment will be created.",
    ),
}


def resolve_support_issue(issue_type: str) -> tuple[str, str, str]:
    """Return the approved synthetic decision, policy, and customer message."""

    try:
        return SUPPORT_RULES[issue_type]
    except KeyError as exc:
        raise ValueError(f"unknown synthetic issue type: {issue_type}") from exc
