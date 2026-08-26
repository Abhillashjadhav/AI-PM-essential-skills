from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
from pathlib import Path
from typing import Any, BinaryIO, Sequence

from .io import EvidenceError, load_json, load_jsonl, write_jsonl


MAX_ADAPTER_OUTPUT_BYTES = 1_000_000
MAX_ADAPTER_ERROR_BYTES = 64_000
MAX_ADAPTER_INPUT_BYTES = 1_000_000


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


def _kill_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except (OSError, ProcessLookupError):
        pass


def _read_bounded(
    stream: BinaryIO,
    limit: int,
    label: str,
    sink: bytearray,
    overflow: list[str],
    process: subprocess.Popen[bytes],
) -> None:
    while True:
        chunk = stream.read(65_536)
        if not chunk:
            return
        remaining = limit - len(sink)
        if remaining > 0:
            sink.extend(chunk[:remaining])
        if len(chunk) > remaining:
            overflow.append(label)
            _kill_process(process)
            return


def _write_request(stream: BinaryIO, payload: bytes) -> None:
    try:
        stream.write(payload)
        stream.flush()
    except (BrokenPipeError, OSError):
        pass
    finally:
        stream.close()


def _invoke_adapter(
    command: Sequence[str], request: dict[str, Any], timeout_seconds: float
) -> dict[str, Any]:
    if not command:
        raise EvidenceError("adapter command is empty")
    payload = json.dumps(request, sort_keys=True).encode("utf-8")
    if len(payload) > MAX_ADAPTER_INPUT_BYTES:
        raise EvidenceError(
            f"adapter input exceeds {MAX_ADAPTER_INPUT_BYTES} bytes"
        )
    try:
        process = subprocess.Popen(
            list(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=os.name == "posix",
        )
    except OSError as exc:
        raise EvidenceError(f"adapter execution failed: {exc}") from exc

    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None
    stdout = bytearray()
    stderr = bytearray()
    overflow: list[str] = []
    threads = [
        threading.Thread(
            target=_read_bounded,
            args=(
                process.stdout,
                MAX_ADAPTER_OUTPUT_BYTES,
                "stdout",
                stdout,
                overflow,
                process,
            ),
            daemon=True,
        ),
        threading.Thread(
            target=_read_bounded,
            args=(
                process.stderr,
                MAX_ADAPTER_ERROR_BYTES,
                "stderr",
                stderr,
                overflow,
                process,
            ),
            daemon=True,
        ),
        threading.Thread(
            target=_write_request,
            args=(process.stdin, payload),
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()
    timed_out = False
    try:
        returncode = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_process(process)
        returncode = process.wait()
    for thread in threads:
        thread.join(timeout=1)
    streams_alive = any(thread.is_alive() for thread in threads)
    process.stdout.close()
    process.stderr.close()
    if timed_out:
        raise EvidenceError(
            f"adapter execution timed out after {timeout_seconds:g} seconds"
        )
    if overflow:
        label = sorted(set(overflow))[0]
        limit = (
            MAX_ADAPTER_OUTPUT_BYTES
            if label == "stdout"
            else MAX_ADAPTER_ERROR_BYTES
        )
        raise EvidenceError(f"adapter {label} exceeds {limit} bytes")
    if streams_alive:
        _kill_process(process)
        raise EvidenceError("adapter streams could not be drained safely")
    if returncode != 0:
        detail = stderr.decode("utf-8", errors="replace").strip()[:500] or "no stderr"
        raise EvidenceError(
            f"adapter exited with code {returncode}: {detail}"
        )
    try:
        decoded = stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceError("adapter stdout must be valid UTF-8") from exc
    try:
        value = json.loads(decoded)
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
