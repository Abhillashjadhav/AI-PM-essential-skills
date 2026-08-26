from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class EvidenceError(ValueError):
    """Raised when supplied evaluation evidence cannot support a claim."""


def _read_utf8(source: Path) -> str:
    try:
        return source.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceError(f"invalid UTF-8 evidence in {source}: {exc}") from exc
    except OSError as exc:
        raise EvidenceError(f"unable to read evidence {source}: {exc}") from exc


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def rubric_hash(suite: dict[str, Any]) -> str:
    return canonical_hash(
        {
            "model_graders": suite.get("model_graders", []),
            "rubric": suite.get("rubric", []),
        }
    )


def load_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        raise EvidenceError(f"missing JSON evidence: {source}")
    try:
        value = json.loads(_read_utf8(source))
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"invalid JSON in {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{source} must contain a JSON object")
    return value


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise EvidenceError(f"missing JSONL evidence: {source}")
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(_read_utf8(source).splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EvidenceError(
                f"invalid JSONL in {source} line {line_number}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise EvidenceError(
                f"{source} line {line_number} must contain a JSON object"
            )
        rows.append(value)
    return rows


def write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "".join(
            json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows
        ),
        encoding="utf-8",
    )


def get_path(value: Any, path: str) -> Any:
    current = value
    if not path:
        return current
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                raise KeyError(path)
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            if index >= len(current):
                raise KeyError(path)
            current = current[index]
        else:
            raise KeyError(path)
    return current


def valid_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value.lower())
