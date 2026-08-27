#!/usr/bin/env python3
"""Create, bind, and verify the customer-support repository pilot kit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence


TEMPLATE_ID = "customer-support-agent"
FR_RE = re.compile(r"^FR-[0-9]{3,}$")
AC_RE = re.compile(r"^AC-[0-9]{3,}$")
REQUIRED_PATH_KEYS = {
    "adapter",
    "cases",
    "ci",
    "dataset",
    "evidence_receipt",
    "engineering_contract",
    "eval_contract",
    "pmos_contract",
    "portable_package",
    "run",
    "suite",
    "tooling",
    "trials",
}
HARNESS_PATHS = {
    "cases": "cases.jsonl",
    "dataset": "dataset.json",
    "run": "run.json",
    "suite": "suite.json",
}


class PilotError(ValueError):
    """Raised when a pilot package is ambiguous, unsafe, or unbound."""


def _reject_constant(value: str) -> None:
    raise PilotError(f"non-standard JSON constant is not allowed: {value}")


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"), parse_constant=_reject_constant
        )
    except PilotError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PilotError(f"{label} is not readable strict JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PilotError(f"{label} must be a JSON object")
    return payload


def _load_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise PilotError(f"{label} is not readable JSONL: {exc}") from exc
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            raise PilotError(f"{label} line {number} must not be blank")
        try:
            row = json.loads(line, parse_constant=_reject_constant)
        except PilotError:
            raise
        except json.JSONDecodeError as exc:
            raise PilotError(f"{label} line {number} is invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise PilotError(f"{label} line {number} must be an object")
        rows.append(row)
    if not rows:
        raise PilotError(f"{label} must contain at least one row")
    return rows


def _atomic_write(path: Path, content: str) -> None:
    if path.is_symlink():
        raise PilotError(f"refusing to replace symbolic link: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
    except OSError as exc:
        raise PilotError(f"cannot write {path}: {exc}") from exc
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write(path, _canonical_json(payload))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise PilotError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def _tree_sha256(root: Path, relative_paths: Sequence[str]) -> str:
    rows = [
        {"path": relative, "sha256": _sha256(_resolve_file(root, relative, relative))}
        for relative in sorted(relative_paths)
    ]
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _non_empty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PilotError(f"{label} must be a non-empty string")
    return value


def _relative(value: Any, label: str) -> Path:
    text = _non_empty(value, label)
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        raise PilotError(f"{label} must be a safe relative path")
    return path


def _resolve_file(root: Path, value: Any, label: str) -> Path:
    relative = _relative(value, label)
    try:
        resolved_root = root.resolve(strict=True)
        candidate = root / relative
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PilotError(f"{label} cannot be resolved: {exc}") from exc
    if resolved == resolved_root or resolved_root not in resolved.parents:
        raise PilotError(f"{label} escapes its allowed root")
    if candidate.is_symlink() or not resolved.is_file():
        raise PilotError(f"{label} must be a regular, non-symlink file")
    return resolved


def _resolve_optional_file(root: Path, value: Any, label: str) -> Path:
    relative = _relative(value, label)
    candidate = root / relative
    if candidate.exists() or candidate.is_symlink():
        return _resolve_file(root, value, label)
    try:
        resolved_root = root.resolve(strict=True)
        resolved_parent = candidate.parent.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PilotError(f"{label} parent cannot be resolved: {exc}") from exc
    if resolved_parent != resolved_root and resolved_root not in resolved_parent.parents:
        raise PilotError(f"{label} escapes its allowed root")
    return resolved_parent / candidate.name


def _project_and_repository(
    project: Path, repository_root: Path | None
) -> tuple[Path, Path]:
    try:
        resolved_project = project.resolve(strict=True)
        resolved_repository = (
            repository_root.resolve(strict=True)
            if repository_root is not None
            else resolved_project
        )
    except (OSError, RuntimeError) as exc:
        raise PilotError(f"pilot roots cannot be resolved: {exc}") from exc
    if not resolved_project.is_dir() or not resolved_repository.is_dir():
        raise PilotError("pilot project and repository root must be directories")
    if (
        resolved_project != resolved_repository
        and resolved_repository not in resolved_project.parents
    ):
        raise PilotError("pilot project must stay within the selected repository root")
    return resolved_project, resolved_repository


def _config(project: Path) -> dict[str, Any]:
    config = _load_json(
        _resolve_file(project, "pilot.json", "pilot.json"),
        "pilot.json",
    )
    if config.get("schema_version") != "1.0":
        raise PilotError("pilot.schema_version must be '1.0'")
    if config.get("template_id") != TEMPLATE_ID:
        raise PilotError(f"pilot.template_id must be {TEMPLATE_ID!r}")
    product = config.get("product")
    if not isinstance(product, dict):
        raise PilotError("pilot.product must be an object")
    _non_empty(product.get("id"), "pilot.product.id")
    _non_empty(product.get("version"), "pilot.product.version")
    if not isinstance(config.get("synthetic_fixture"), bool):
        raise PilotError("pilot.synthetic_fixture must be boolean")
    paths = config.get("paths")
    if not isinstance(paths, dict) or set(paths) != REQUIRED_PATH_KEYS:
        raise PilotError(
            f"pilot.paths must contain exactly {sorted(REQUIRED_PATH_KEYS)}"
        )
    for key, value in paths.items():
        _relative(value, f"pilot.paths.{key}")
    for key, expected in HARNESS_PATHS.items():
        if paths[key] != expected:
            raise PilotError(
                f"pilot.paths.{key} must be {expected!r}; the evaluation harness "
                "owns this filename"
            )
    candidates = config.get("candidate_files")
    if (
        not isinstance(candidates, list)
        or not candidates
        or not all(isinstance(item, str) and item for item in candidates)
        or len(candidates) != len(set(candidates))
    ):
        raise PilotError("pilot.candidate_files must be a non-empty unique string list")
    for index, value in enumerate(candidates):
        _relative(value, f"pilot.candidate_files[{index}]")
    return config


def _project_paths(
    project: Path,
    config: dict[str, Any],
    *,
    require_receipt: bool,
    require_trials: bool,
) -> dict[str, Path]:
    paths = config["paths"]
    optional = set()
    if not require_receipt:
        optional.add("evidence_receipt")
    if not require_trials:
        optional.add("trials")
    resolved = {
        key: (
            _resolve_optional_file(project, value, f"pilot.paths.{key}")
            if key in optional
            else _resolve_file(project, value, f"pilot.paths.{key}")
        )
        for key, value in paths.items()
    }
    _reject_aliases(
        [
            ("pilot.json", _resolve_file(project, "pilot.json", "pilot.json")),
            *[(f"pilot.paths.{key}", path) for key, path in resolved.items()],
        ],
        "pilot paths",
    )
    return resolved


def _reject_aliases(entries: Sequence[tuple[str, Path]], label: str) -> None:
    """Reject lexical aliases and hard links before any binder write occurs."""

    seen_paths: dict[Path, str] = {}
    seen_files: dict[tuple[int, int], str] = {}
    for name, path in entries:
        previous = seen_paths.get(path)
        if previous is not None:
            raise PilotError(f"{label} alias the same path: {previous} and {name}")
        seen_paths[path] = name
        if not path.exists():
            continue
        try:
            stat = path.stat()
        except OSError as exc:
            raise PilotError(f"cannot inspect {name}: {exc}") from exc
        identity = (stat.st_dev, stat.st_ino)
        previous = seen_files.get(identity)
        if previous is not None:
            raise PilotError(f"{label} alias the same file: {previous} and {name}")
        seen_files[identity] = name


def _candidate_paths(
    repository: Path,
    project: Path,
    config: dict[str, Any],
    managed_paths: dict[str, Path],
) -> list[Path]:
    candidates = [
        _resolve_file(repository, value, f"pilot.candidate_files[{index}]")
        for index, value in enumerate(config["candidate_files"])
    ]
    _reject_aliases(
        [
            ("pilot.json", _resolve_file(project, "pilot.json", "pilot.json")),
            *[(f"pilot.paths.{key}", path) for key, path in managed_paths.items()],
            *[
                (f"pilot.candidate_files[{index}]", path)
                for index, path in enumerate(candidates)
            ],
        ],
        "candidate and managed paths",
    )
    return candidates


def _ids(rows: Any, pattern: re.Pattern[str], label: str) -> tuple[str, ...]:
    if not isinstance(rows, list) or not rows:
        raise PilotError(f"{label} must be a non-empty list")
    values: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise PilotError(f"{label}[{index}] must be an object")
        identifier = row.get("id")
        if not isinstance(identifier, str) or pattern.fullmatch(identifier) is None:
            raise PilotError(f"{label}[{index}].id has an invalid stable identifier")
        _non_empty(row.get("intent"), f"{label}[{index}].intent")
        values.append(identifier)
    if len(values) != len(set(values)):
        raise PilotError(f"{label} contains duplicate stable identifiers")
    return tuple(values)


def _validate_pmos(
    pmos: dict[str, Any], product_id: str
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, frozenset[str]]]:
    if pmos.get("schema_version") != "1.0":
        raise PilotError("PMOS contract schema_version must be '1.0'")
    if pmos.get("product_id") != product_id:
        raise PilotError("PMOS contract product_id does not match pilot product")
    _non_empty(pmos.get("contract_id"), "PMOS contract_id")
    _non_empty(pmos.get("version"), "PMOS version")
    if pmos.get("decision") != "GO":
        raise PilotError("PMOS decision must be explicitly approved as GO")
    _non_empty(pmos.get("accountable_approver"), "PMOS accountable_approver")
    questions = pmos.get("unresolved_questions")
    if questions != []:
        raise PilotError("PMOS unresolved_questions must be an empty list before binding")
    requirement_ids = _ids(pmos.get("requirements"), FR_RE, "PMOS requirements")
    acceptance_ids = _ids(
        pmos.get("acceptance_criteria"), AC_RE, "PMOS acceptance_criteria"
    )
    requirement_set = set(requirement_ids)
    acceptance_links: dict[str, frozenset[str]] = {}
    for index, criterion in enumerate(pmos["acceptance_criteria"]):
        linked = criterion.get("requirement_ids")
        if (
            not isinstance(linked, list)
            or not linked
            or not all(isinstance(item, str) for item in linked)
            or len(linked) != len(set(linked))
            or not set(linked) <= requirement_set
        ):
            raise PilotError(
                f"PMOS acceptance_criteria[{index}].requirement_ids must reference known FR IDs"
            )
        acceptance_links[criterion["id"]] = frozenset(linked)
    linked_requirements = set().union(*acceptance_links.values())
    if linked_requirements != requirement_set:
        raise PilotError("PMOS acceptance criteria do not link every requirement")
    for field in (
        "customer_problem",
        "target_user",
        "product_hypothesis",
        "expected_ai_outcome",
        "expected_trajectory",
        "human_review_or_escalation",
    ):
        _non_empty(pmos.get(field), f"PMOS {field}")
    for field in ("metrics", "guardrails", "scope", "trade_offs"):
        if not isinstance(pmos.get(field), dict):
            raise PilotError(f"PMOS {field} must be an object")
    return requirement_ids, acceptance_ids, acceptance_links


def _validate_traceability(
    cases: list[dict[str, Any]],
    suite: dict[str, Any],
    eval_contract: dict[str, Any],
    requirement_ids: Sequence[str],
    acceptance_ids: Sequence[str],
    acceptance_links: dict[str, frozenset[str]],
) -> dict[str, int]:
    requirement_set = set(requirement_ids)
    acceptance_set = set(acceptance_ids)
    case_ids: list[str] = []
    case_links: dict[str, tuple[set[str], set[str]]] = {}
    case_requirement_coverage: set[str] = set()
    case_acceptance_coverage: set[str] = set()
    for index, case in enumerate(cases):
        case_id = _non_empty(case.get("case_id"), f"cases[{index}].case_id")
        case_ids.append(case_id)
        trace = case.get("traceability")
        if not isinstance(trace, dict):
            raise PilotError(f"case {case_id} requires traceability")
        linked_requirements = trace.get("requirement_ids")
        linked_acceptance = trace.get("acceptance_criteria_ids")
        if (
            not isinstance(linked_requirements, list)
            or not linked_requirements
            or not all(isinstance(item, str) for item in linked_requirements)
            or len(linked_requirements) != len(set(linked_requirements))
            or not set(linked_requirements) <= requirement_set
        ):
            raise PilotError(f"case {case_id} has invalid requirement traceability")
        if (
            not isinstance(linked_acceptance, list)
            or not linked_acceptance
            or not all(isinstance(item, str) for item in linked_acceptance)
            or len(linked_acceptance) != len(set(linked_acceptance))
            or not set(linked_acceptance) <= acceptance_set
        ):
            raise PilotError(f"case {case_id} has invalid acceptance traceability")
        linked_requirement_set = set(linked_requirements)
        linked_acceptance_set = set(linked_acceptance)
        for requirement_id in linked_requirement_set:
            if not any(
                requirement_id in acceptance_links[acceptance_id]
                for acceptance_id in linked_acceptance_set
            ):
                raise PilotError(
                    f"case {case_id} does not relate {requirement_id} "
                    "to an acceptance criterion"
                )
        for acceptance_id in linked_acceptance_set:
            if not acceptance_links[acceptance_id] & linked_requirement_set:
                raise PilotError(
                    f"case {case_id} acceptance criterion {acceptance_id} "
                    "does not relate to a listed requirement"
                )
        case_links[case_id] = (linked_requirement_set, linked_acceptance_set)
        case_requirement_coverage.update(linked_requirement_set)
        case_acceptance_coverage.update(linked_acceptance_set)
    if len(case_ids) != len(set(case_ids)):
        raise PilotError("cases contain duplicate case_id values")
    if case_requirement_coverage != requirement_set:
        raise PilotError("cases do not cover every PMOS requirement")
    if case_acceptance_coverage != acceptance_set:
        raise PilotError("cases do not cover every PMOS acceptance criterion")

    graders = suite.get("deterministic_graders")
    if not isinstance(graders, list) or not graders:
        raise PilotError("suite deterministic_graders must be a non-empty list")
    grader_ids = [_non_empty(row.get("id"), "grader.id") for row in graders if isinstance(row, dict)]
    if len(grader_ids) != len(graders) or len(grader_ids) != len(set(grader_ids)):
        raise PilotError("suite grader IDs must be complete and unique")

    rows = eval_contract.get("traceability")
    if not isinstance(rows, list) or not rows:
        raise PilotError("eval contract traceability must be a non-empty list")
    seen_requirements: set[str] = set()
    seen_acceptance: set[str] = set()
    seen_cases: set[str] = set()
    seen_graders: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise PilotError(f"eval traceability[{index}] must be an object")
        requirement_id = row.get("requirement_id")
        if requirement_id not in requirement_set or requirement_id in seen_requirements:
            raise PilotError(f"eval traceability[{index}] has invalid requirement_id")
        seen_requirements.add(requirement_id)
        expected_acceptance = {
            acceptance_id
            for acceptance_id, linked in acceptance_links.items()
            if requirement_id in linked
        }
        for key, known, seen in (
            ("acceptance_criteria_ids", acceptance_set, seen_acceptance),
            ("case_ids", set(case_ids), seen_cases),
            ("grader_ids", set(grader_ids), seen_graders),
        ):
            values = row.get(key)
            if (
                not isinstance(values, list)
                or not values
                or not all(isinstance(item, str) for item in values)
                or len(values) != len(set(values))
                or not set(values) <= known
            ):
                raise PilotError(f"eval traceability[{index}].{key} is incomplete")
            seen.update(values)
        row_acceptance = set(row["acceptance_criteria_ids"])
        if row_acceptance != expected_acceptance:
            raise PilotError(
                f"eval traceability[{index}] acceptance criteria do not match "
                f"PMOS links for {requirement_id}"
            )
        for case_id in row["case_ids"]:
            case_requirements, case_acceptance = case_links[case_id]
            if (
                requirement_id not in case_requirements
                or not row_acceptance <= case_acceptance
            ):
                raise PilotError(
                    f"eval traceability[{index}] case {case_id} does not carry "
                    "its FR/AC relationship"
                )
    if seen_requirements != requirement_set:
        raise PilotError("eval contract does not trace every requirement")
    if seen_acceptance != acceptance_set:
        raise PilotError("eval contract does not trace every acceptance criterion")
    if seen_cases != set(case_ids):
        raise PilotError("eval contract does not trace every representative case")
    if seen_graders != set(grader_ids):
        raise PilotError("eval contract does not trace every deterministic grader")
    return {
        "requirement_count": len(requirement_ids),
        "acceptance_criteria_count": len(acceptance_ids),
        "case_count": len(case_ids),
        "grader_count": len(grader_ids),
    }


def _expected_package(
    project: Path,
    config: dict[str, Any],
    paths: dict[str, Path],
    pmos: dict[str, Any],
    eval_contract: dict[str, Any],
    engineering: dict[str, Any],
    candidate_sha: str,
) -> dict[str, Any]:
    product = config["product"]
    path_values = config["paths"]
    return {
        "adapter": {
            "path": path_values["adapter"],
            "sha256": _sha256(paths["adapter"]),
        },
        "automation": {
            "path": path_values["ci"],
            "sha256": _sha256(paths["ci"]),
        },
        "candidate": {
            "files": sorted(config["candidate_files"]),
            "root": "repository",
            "sha256": candidate_sha,
        },
        "contracts": {
            "engineering": {
                "id": engineering["contract_id"],
                "path": path_values["engineering_contract"],
                "sha256": _sha256(paths["engineering_contract"]),
                "version": engineering["version"],
            },
            "eval": {
                "id": eval_contract["contract_id"],
                "path": path_values["eval_contract"],
                "sha256": _sha256(paths["eval_contract"]),
                "version": eval_contract["version"],
            },
            "pmos": {
                "id": pmos["contract_id"],
                "path": path_values["pmos_contract"],
                "sha256": _sha256(paths["pmos_contract"]),
                "version": pmos["version"],
            },
        },
        "decision": pmos["decision"],
        "package_id": f"{product['id']}-portable-package",
        "pilot_config": {
            "path": "pilot.json",
            "sha256": _sha256(project / "pilot.json"),
        },
        "product_id": product["id"],
        "schema_version": "1.0",
        "synthetic_fixture": config["synthetic_fixture"],
        "template_id": config["template_id"],
        "tooling": {
            "path": path_values["tooling"],
            "sha256": _sha256(paths["tooling"]),
        },
        "version": product["version"],
    }


def _load_context(
    project: Path,
    repository_root: Path | None,
    *,
    require_receipt: bool,
    require_trials: bool,
) -> tuple[
    Path,
    Path,
    dict[str, Any],
    dict[str, Path],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    tuple[str, ...],
    tuple[str, ...],
    dict[str, frozenset[str]],
    dict[str, int],
]:
    project, repository = _project_and_repository(project, repository_root)
    config = _config(project)
    paths = _project_paths(
        project,
        config,
        require_receipt=require_receipt,
        require_trials=require_trials,
    )
    product_id = config["product"]["id"]
    pmos = _load_json(paths["pmos_contract"], "PMOS contract")
    requirements, acceptance, acceptance_links = _validate_pmos(pmos, product_id)
    suite = _load_json(paths["suite"], "suite")
    if suite.get("schema_version") != "1.1":
        raise PilotError("suite schema_version must be '1.1'")
    _non_empty(suite.get("suite_id"), "suite.suite_id")
    _non_empty(suite.get("suite_version"), "suite.suite_version")
    cases = _load_jsonl(paths["cases"], "cases")
    eval_contract = _load_json(paths["eval_contract"], "eval contract")
    if eval_contract.get("schema_version") != "1.0":
        raise PilotError("eval contract schema_version must be '1.0'")
    if eval_contract.get("product_id") != product_id:
        raise PilotError("eval contract product_id does not match pilot product")
    _non_empty(eval_contract.get("contract_id"), "eval contract_id")
    _non_empty(eval_contract.get("version"), "eval version")
    counts = _validate_traceability(
        cases,
        suite,
        eval_contract,
        requirements,
        acceptance,
        acceptance_links,
    )
    return (
        project,
        repository,
        config,
        paths,
        pmos,
        suite,
        eval_contract,
        cases,
        requirements,
        acceptance,
        acceptance_links,
        counts,
    )


def _validate_dataset(dataset: dict[str, Any]) -> None:
    if dataset.get("schema_version") != "1.1":
        raise PilotError("dataset schema_version must be '1.1'")
    _non_empty(dataset.get("dataset_id"), "dataset.dataset_id")
    _non_empty(dataset.get("dataset_version"), "dataset.dataset_version")


def _validate_engineering(engineering: dict[str, Any], product_id: str) -> None:
    if engineering.get("schema_version") != "1.0":
        raise PilotError("engineering contract schema_version must be '1.0'")
    if engineering.get("product_id") not in (None, product_id):
        raise PilotError("engineering contract product_id does not match pilot product")
    _non_empty(engineering.get("contract_id"), "engineering contract_id")
    _non_empty(engineering.get("version"), "engineering version")


def _validate_run(run: dict[str, Any]) -> None:
    if run.get("schema_version") != "1.1":
        raise PilotError("run schema_version must be '1.1'")
    for field in ("created_at", "harness", "model"):
        if field not in run:
            raise PilotError(f"run.{field} is required")


def _evidence_receipt(
    config: dict[str, Any],
    candidate_sha: str,
    run: dict[str, Any],
    *,
    run_sha: str,
    trials_sha: str | None,
    trial_count: int,
) -> dict[str, Any]:
    sealed = trials_sha is not None
    return {
        "candidate_sha256": candidate_sha,
        "evidence_status": "SEALED" if sealed else "PENDING",
        "product_id": config["product"]["id"],
        "run_id": run["run_id"],
        "run_sha256": run_sha,
        "schema_version": "1.0",
        "trial_count": trial_count if sealed else 0,
        "trials_path": config["paths"]["trials"],
        "trials_sha256": trials_sha,
    }


def _load_canonical_json(path: Path, label: str) -> dict[str, Any]:
    payload = _load_json(path, label)
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PilotError(f"{label} cannot be read canonically: {exc}") from exc
    if content != _canonical_json(payload):
        raise PilotError(f"{label} is not canonical JSON")
    return payload


def _trials_match_run(
    trials: Sequence[dict[str, Any]],
    run_id: str,
    run_sha: str,
    *,
    environment_fingerprint: str | None,
) -> bool:
    return all(
        row.get("run_id") == run_id
        and row.get("run_sha256") == run_sha
        and (
            environment_fingerprint is None
            or row.get("status") != "completed"
            or row.get("environment_fingerprint") == environment_fingerprint
        )
        for row in trials
    )


def bind_pilot(
    project: Path, repository_root: Path | None = None
) -> dict[str, Any]:
    (
        project,
        repository,
        config,
        paths,
        pmos,
        suite,
        eval_contract,
        cases,
        requirement_ids,
        acceptance_ids,
        _,
        _,
    ) = _load_context(
        project,
        repository_root,
        require_receipt=False,
        require_trials=False,
    )

    _candidate_paths(repository, project, config, paths)
    candidate_sha = _tree_sha256(repository, config["candidate_files"])

    # Validate every mutable input before the first write. In particular, a
    # malformed downstream contract must not leave an upstream file rebound.
    product_id = config["product"]["id"]
    dataset = _load_json(paths["dataset"], "dataset")
    _validate_dataset(dataset)
    engineering = _load_json(paths["engineering_contract"], "engineering contract")
    _validate_engineering(engineering, product_id)
    run = _load_json(paths["run"], "run")
    _validate_run(run)
    trials: list[dict[str, Any]] | None = None
    if paths["trials"].exists():
        trials = _load_jsonl(paths["trials"], "trials")

    cases_sha = _sha256(paths["cases"])
    dataset["cases_path"] = paths["cases"].name
    dataset["cases_sha256"] = cases_sha
    _write_json(paths["dataset"], dataset)

    eval_contract["product_id"] = product_id
    eval_contract["pmos_contract"] = {
        "path": config["paths"]["pmos_contract"],
        "sha256": _sha256(paths["pmos_contract"]),
    }
    eval_contract["suite"] = {
        "path": config["paths"]["suite"],
        "sha256": _sha256(paths["suite"]),
    }
    eval_contract["dataset"] = {
        "path": config["paths"]["dataset"],
        "sha256": _sha256(paths["dataset"]),
    }
    eval_contract["cases"] = {
        "path": config["paths"]["cases"],
        "sha256": cases_sha,
    }
    _write_json(paths["eval_contract"], eval_contract)

    engineering["product_id"] = product_id
    engineering["pmos_contract_sha256"] = _sha256(paths["pmos_contract"])
    engineering["eval_contract_sha256"] = _sha256(paths["eval_contract"])
    engineering["requirement_ids"] = list(requirement_ids)
    engineering["acceptance_criteria_ids"] = list(acceptance_ids)
    _write_json(paths["engineering_contract"], engineering)

    package = _expected_package(
        project, config, paths, pmos, eval_contract, engineering, candidate_sha
    )
    _write_json(paths["portable_package"], package)
    package_sha = _sha256(paths["portable_package"])

    run["candidate"] = {
        "id": product_id,
        "sha256": candidate_sha,
        "version": config["product"]["version"],
    }
    run["configuration"] = {
        "id": suite["suite_id"],
        "sha256": _sha256(paths["suite"]),
        "version": suite["suite_version"],
    }
    run["contract_lineage"] = [
        {
            "id": pmos["contract_id"],
            "path": config["paths"]["pmos_contract"],
            "role": "pmos",
            "sha256": _sha256(paths["pmos_contract"]),
            "version": pmos["version"],
        },
        {
            "id": engineering["contract_id"],
            "path": config["paths"]["engineering_contract"],
            "role": "engineering",
            "sha256": _sha256(paths["engineering_contract"]),
            "version": engineering["version"],
        },
    ]
    run["dataset"] = {
        "cases_sha256": cases_sha,
        "id": dataset["dataset_id"],
        "version": dataset["dataset_version"],
    }
    run["prompt"] = {
        "id": pmos["contract_id"],
        "sha256": _sha256(paths["pmos_contract"]),
        "version": pmos["version"],
    }
    run["run_id"] = f"{product_id}-{candidate_sha[:12]}"
    run["tools"] = [
        {
            "name": "portable-product-package",
            "sha256": package_sha,
            "version": config["product"]["version"],
        },
        {
            "name": "evidence-adapter",
            "sha256": _sha256(paths["adapter"]),
            "version": config["product"]["version"],
        },
    ]
    _write_json(paths["run"], run)

    run_sha = _sha256(paths["run"])
    sealed = False
    environment_fingerprint = (
        _sha256(paths["adapter"]) if config["synthetic_fixture"] else None
    )
    if trials is not None and _trials_match_run(
        trials,
        run["run_id"],
        run_sha,
        environment_fingerprint=environment_fingerprint,
    ):
        sealed = True

    receipt = _evidence_receipt(
        config,
        candidate_sha,
        run,
        run_sha=run_sha,
        trials_sha=_sha256(paths["trials"]) if sealed else None,
        trial_count=len(trials) if sealed and trials is not None else 0,
    )
    _write_json(paths["evidence_receipt"], receipt)

    return _verify_pilot(
        project,
        repository,
        require_trials=sealed,
    )


def _verify_pilot(
    project: Path,
    repository_root: Path | None,
    *,
    require_trials: bool,
) -> dict[str, Any]:
    (
        project,
        repository,
        config,
        paths,
        pmos,
        suite,
        eval_contract,
        cases,
        requirement_ids,
        acceptance_ids,
        _,
        counts,
    ) = _load_context(
        project,
        repository_root,
        require_receipt=True,
        require_trials=False,
    )
    _candidate_paths(repository, project, config, paths)
    candidate_sha = _tree_sha256(repository, config["candidate_files"])

    dataset = _load_json(paths["dataset"], "dataset")
    _validate_dataset(dataset)
    cases_sha = _sha256(paths["cases"])
    if dataset.get("cases_path") != paths["cases"].name:
        raise PilotError("dataset does not point to the configured cases file")
    if dataset.get("cases_sha256") != cases_sha:
        raise PilotError("dataset cases digest does not match cases.jsonl")

    expected_eval_links = {
        "pmos_contract": (paths["pmos_contract"], config["paths"]["pmos_contract"]),
        "suite": (paths["suite"], config["paths"]["suite"]),
        "dataset": (paths["dataset"], config["paths"]["dataset"]),
        "cases": (paths["cases"], config["paths"]["cases"]),
    }
    for key, (path, declared_path) in expected_eval_links.items():
        value = eval_contract.get(key)
        if not isinstance(value, dict):
            raise PilotError(f"eval contract {key} binding is missing")
        if value.get("path") != declared_path or value.get("sha256") != _sha256(path):
            raise PilotError(f"eval contract {key} binding does not match its artifact")

    engineering = _load_json(paths["engineering_contract"], "engineering contract")
    _validate_engineering(engineering, config["product"]["id"])
    if engineering.get("product_id") != config["product"]["id"]:
        raise PilotError("engineering contract product_id does not match pilot product")
    if engineering.get("pmos_contract_sha256") != _sha256(paths["pmos_contract"]):
        raise PilotError("engineering contract does not bind the exact PMOS contract")
    if engineering.get("eval_contract_sha256") != _sha256(paths["eval_contract"]):
        raise PilotError("engineering contract does not bind the exact eval contract")
    if engineering.get("requirement_ids") != list(requirement_ids):
        raise PilotError("engineering contract requirement IDs do not match PMOS")
    if engineering.get("acceptance_criteria_ids") != list(acceptance_ids):
        raise PilotError("engineering contract acceptance IDs do not match PMOS")

    expected_package = _expected_package(
        project, config, paths, pmos, eval_contract, engineering, candidate_sha
    )
    package = _load_json(paths["portable_package"], "portable product package")
    if package != expected_package:
        raise PilotError("portable product package does not match the bound artifacts")

    run = _load_json(paths["run"], "run")
    _validate_run(run)
    if run.get("candidate") != {
        "id": config["product"]["id"],
        "sha256": candidate_sha,
        "version": config["product"]["version"],
    }:
        raise PilotError("run candidate binding does not match configured candidate files")
    if run.get("configuration") != {
        "id": suite["suite_id"],
        "sha256": _sha256(paths["suite"]),
        "version": suite["suite_version"],
    }:
        raise PilotError("run configuration does not bind the exact eval suite")
    if run.get("dataset") != {
        "cases_sha256": cases_sha,
        "id": dataset["dataset_id"],
        "version": dataset["dataset_version"],
    }:
        raise PilotError("run dataset binding does not match the exact cases")
    expected_lineage = [
        {
            "id": pmos["contract_id"],
            "path": config["paths"]["pmos_contract"],
            "role": "pmos",
            "sha256": _sha256(paths["pmos_contract"]),
            "version": pmos["version"],
        },
        {
            "id": engineering["contract_id"],
            "path": config["paths"]["engineering_contract"],
            "role": "engineering",
            "sha256": _sha256(paths["engineering_contract"]),
            "version": engineering["version"],
        },
    ]
    if run.get("contract_lineage") != expected_lineage:
        raise PilotError("run contract lineage does not match PMOS and engineering")
    expected_prompt = {
        "id": pmos["contract_id"],
        "sha256": _sha256(paths["pmos_contract"]),
        "version": pmos["version"],
    }
    if run.get("prompt") != expected_prompt:
        raise PilotError("run prompt binding does not match PMOS")
    expected_tools = [
        {
            "name": "portable-product-package",
            "sha256": _sha256(paths["portable_package"]),
            "version": config["product"]["version"],
        },
        {
            "name": "evidence-adapter",
            "sha256": _sha256(paths["adapter"]),
            "version": config["product"]["version"],
        },
    ]
    if run.get("tools") != expected_tools:
        raise PilotError("run tools do not bind the package and evidence adapter")
    expected_run_id = f"{config['product']['id']}-{candidate_sha[:12]}"
    if run.get("run_id") != expected_run_id:
        raise PilotError("run_id does not match the candidate digest")

    receipt = _load_canonical_json(paths["evidence_receipt"], "evidence receipt")
    status = receipt.get("evidence_status")
    run_sha = _sha256(paths["run"])
    trials: list[dict[str, Any]] = []
    verified = False
    if status == "SEALED":
        trials = _load_jsonl(paths["trials"], "trials")
        for index, row in enumerate(trials):
            if row.get("run_id") != expected_run_id or row.get("run_sha256") != run_sha:
                raise PilotError(f"trial {index} is not bound to the exact run")
            if (
                config["synthetic_fixture"]
                and row.get("status") == "completed"
                and row.get("environment_fingerprint") != _sha256(paths["adapter"])
            ):
                raise PilotError(f"synthetic trial {index} is not bound to the adapter")
        expected_receipt = _evidence_receipt(
            config,
            candidate_sha,
            run,
            run_sha=run_sha,
            trials_sha=_sha256(paths["trials"]),
            trial_count=len(trials),
        )
        if receipt != expected_receipt:
            raise PilotError("evidence receipt does not seal the exact trial contents")
        verified = True
    elif status == "PENDING":
        expected_receipt = _evidence_receipt(
            config,
            candidate_sha,
            run,
            run_sha=run_sha,
            trials_sha=None,
            trial_count=0,
        )
        if receipt != expected_receipt:
            raise PilotError("pending evidence receipt does not match the exact run")
        if require_trials:
            raise PilotError(
                "candidate evidence is pending; execute trials and bind again"
            )
    else:
        raise PilotError("evidence receipt status must be PENDING or SEALED")

    return {
        **counts,
        "candidate_sha256": candidate_sha,
        "decision": pmos["decision"],
        "product_id": config["product"]["id"],
        "status": "VERIFIED" if verified else "BOUND",
        "template_id": config["template_id"],
        "trial_count": len(trials),
    }


def verify_pilot(
    project: Path, repository_root: Path | None = None
) -> dict[str, Any]:
    return _verify_pilot(project, repository_root, require_trials=True)


def create_pilot(destination: Path) -> dict[str, Any]:
    if destination.exists() or destination.is_symlink():
        raise PilotError(f"destination already exists; refusing to overwrite: {destination}")
    source = Path(__file__).resolve().parents[1]
    try:
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    except OSError as exc:
        raise PilotError(f"cannot create pilot at {destination}: {exc}") from exc
    try:
        return verify_pilot(destination)
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create, bind, or verify the customer-support repository pilot"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--destination", type=Path, required=True)
    for command in ("bind", "verify"):
        child = subparsers.add_parser(command)
        child.add_argument("--project", type=Path, required=True)
        child.add_argument("--repository-root", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "create":
            result = create_pilot(args.destination)
        elif args.command == "bind":
            result = bind_pilot(args.project, args.repository_root)
        else:
            result = verify_pilot(args.project, args.repository_root)
    except PilotError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
