from __future__ import annotations

import re
from typing import Any


_PATTERNS = (
    re.compile(
        r"(?i)\b(api[_-]?key|access[_-]?token|secret|password)\s*[:=]\s*[^\s,;]+"
    ),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
)

_SENSITIVE_KEYS = {
    "accesstoken",
    "apikey",
    "authorization",
    "bearertoken",
    "clientsecret",
    "credential",
    "credentials",
    "password",
    "passwd",
    "secret",
    "token",
}


def _sensitive_key(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = re.sub(r"[^a-z0-9]", "", value.lower())
    return (
        normalized in _SENSITIVE_KEYS
        or normalized.endswith(
            (
                "accesskey",
                "apikey",
                "authorization",
                "credential",
                "credentials",
                "password",
                "passwd",
                "privatekey",
                "secret",
                "token",
            )
        )
        or normalized.startswith(("secretkey", "password", "passwd"))
    )


def redact_text(value: str) -> str:
    output = value
    for pattern in _PATTERNS:
        output = pattern.sub("[REDACTED]", output)
    return output


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _sensitive_key(key) else redact_value(item)
            for key, item in value.items()
        }
    return value
