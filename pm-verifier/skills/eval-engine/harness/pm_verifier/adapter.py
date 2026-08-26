from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Sequence

from .io import EvidenceError, load_json, load_jsonl, write_jsonl


MAX_ADAPTER_OUTPUT_BYTES = 1_000_000


def _error_trial(
    case_id: str,
    trial_id: str,
    trial_index: int,
    message: str,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "trial_id": trial_id,
        "trial_index": trial_index,
        "status": "adapter_error",
        "outcome": {},
        "trajectory": [],
        "metrics": {
            "latency_ms": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0,
            "retries": 0,
        },
        "missing_evidence": [message],
    }


def _invoke_adapter(
    command: Sequence[str], request: dict[str, Any], timeout_seconds: float
) -> dict[str, Any]:
    if not command:
        raise EvidenceError("adapter command is empty")
    try:
        completed = subprocess.run(
            list(command),
            input=json.dumps(request, sort_keys=True),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EvidenceError(f"adapter execution failed: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip()[:500] or "no stderr"
        raise EvidenceError(
            f"adapter exited with code {completed.returncode}: {detail}"
        )
    encoded = completed.stdout.encode("utf-8")
    if len(encoded) > MAX_ADAPTER_OUTPUT_BYTES:
        raise EvidenceError(
            f"adapter output exceeds {MAX_ADAPTER_OUTPUT_BYTES} bytes"
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"adapter stdout must be one JSON object: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("adapter stdout must contain a JSON object")
    return value


def execute_trials(
    project: str | Path,
    command: Sequence[str],
    output_path: str | Path,
    *,
    timeout_seconds: float = 60,
) -> list[str]:
    """Run one fresh subprocess per trial and persist canonical JSONL evidence.

    Expected answers are intentionally omitted from the adapter request. The
    harness owns case/trial identifiers so an adapter cannot rewrite selection
    or trial-count provenance.
    """
    root = Path(project)
    suite = load_json(root / "suite.json")
    cases = load_jsonl(root / "cases.jsonl")
    minimum = suite.get("minimum_trials_per_case")
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
        raise EvidenceError("suite.minimum_trials_per_case must be an integer >= 1")
    if timeout_seconds <= 0:
        raise EvidenceError("adapter timeout must be greater than zero")

    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for case in cases:
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise EvidenceError("every adapter case requires a non-empty case_id")
        for trial_index in range(1, minimum + 1):
            trial_id = f"{case_id}-t{trial_index}"
            request = {
                "schema_version": "1.0",
                "case_id": case_id,
                "trial_id": trial_id,
                "trial_index": trial_index,
                "input": case.get("input"),
                "metadata": case.get("metadata", {}),
            }
            try:
                row = _invoke_adapter(command, request, timeout_seconds)
                row = {
                    **row,
                    "case_id": case_id,
                    "trial_id": trial_id,
                    "trial_index": trial_index,
                }
            except EvidenceError as exc:
                message = f"trial {trial_id}: {exc}"
                errors.append(message)
                row = _error_trial(case_id, trial_id, trial_index, message)
            rows.append(row)
    write_jsonl(output_path, rows)
    return errors
