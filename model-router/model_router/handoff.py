"""Architecture record, completion checks, clarity/risk evidence, and the
versioned, hashed handoff package.

The model may propose that a record is complete; it can never supply owner
acceptance. Clarity is proved by evidence in the record, never by a model
saying "this is easy".
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .classifier import ClassifierInput, classify
from .contracts import (
    ARCHITECTURE_REQUIRED_FIELDS,
    HANDOFF_SCHEMA_VERSION,
    AcceptanceEvidence,
    ArchitectureRecord,
    Clarity,
    ContractError,
    RiskFlag,
    RiskLevel,
    canonical_json,
    content_hash,
    utc_now,
)

RECORD_FENCE = re.compile(r"```architecture-record\s*\n(.*?)\n```", re.DOTALL)
# Explicit owner instructions to implement an architecture. Matched on the
# owner's own message (never on model output or quoted material).
ACCEPTANCE_PATTERNS = (
    re.compile(r"\b(approved|accepted|agreed|looks good|lgtm)\b[^.?!\n]{0,40}\b(implement|build|go ahead|ship it)\b", re.I),
    re.compile(r"\b(go ahead and|please)\s+(implement|build)\s+(this|it|the architecture)\b", re.I),
    re.compile(r"^\s*(approved|accepted)[,.!\s]*(implement|build)", re.I),
)
NEGATION = re.compile(r"\b(not|don't|do not|isn't|no)\b[^.?!\n]{0,20}\b(approved|accepted|implement|build)\b", re.I)

# Documented hypotheses for "straightforward bounded implementation".
MAX_SIMPLE_STEPS = 8
MAX_SIMPLE_FILES = 12
DEFAULT_CONTEXT_BUDGET_CHARS = 400_000


class HandoffHold(ContractError):
    """The handoff cannot proceed; ``reasons`` are precise and user-facing."""

    def __init__(self, reasons: list[str]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = reasons


def extract_record(text: str) -> tuple[dict[str, Any] | None, str | None]:
    """Find a fenced ```architecture-record JSON block. Returns (payload, error)."""
    matches = RECORD_FENCE.findall(text or "")
    if not matches:
        return None, None
    try:
        payload = json.loads(matches[-1])
    except json.JSONDecodeError as exc:
        return None, f"architecture record is not valid JSON: {exc.msg} at line {exc.lineno}"
    if not isinstance(payload, dict):
        return None, "architecture record must be a JSON object"
    return payload, None


def detect_acceptance(owner_text: str) -> bool:
    if not owner_text or NEGATION.search(owner_text):
        return False
    return any(pattern.search(owner_text) for pattern in ACCEPTANCE_PATTERNS)


def validate_record(payload: dict[str, Any]) -> tuple[ArchitectureRecord | None, list[str]]:
    missing = [name for name in ARCHITECTURE_REQUIRED_FIELDS if name not in payload]
    if missing:
        return None, [f"architecture record is missing required section(s): {', '.join(missing)}"]
    try:
        record = ArchitectureRecord.from_dict(payload)
    except (ContractError, TypeError) as exc:
        return None, [f"architecture record is invalid: {exc}"]
    problems: list[str] = []
    if record.blocking_questions:
        problems.append("blocking questions remain: " + "; ".join(record.blocking_questions))
    unresolved = [d for d in record.decisions if str(d.get("status", "decided")).lower() not in {"decided", "accepted", "final"}]
    if unresolved:
        problems.append(
            "unresolved decisions: " + "; ".join(str(d.get("title") or d.get("decision") or d) for d in unresolved)
        )
    if not record.steps:
        problems.append("no implementation steps")
    if not record.tests:
        problems.append("no acceptance tests")
    return record, problems


@dataclass
class ClarityAssessment:
    clarity: Clarity
    evidence: list[str]
    gaps: list[str]


def assess_clarity(record: ArchitectureRecord) -> ClarityAssessment:
    evidence: list[str] = []
    gaps: list[str] = []
    steps_explicit = bool(record.steps) and all(str(s.get("description", "")).strip() for s in record.steps)
    (evidence if steps_explicit else gaps).append(
        f"{len(record.steps)} explicit step(s)" if steps_explicit else "steps missing or without descriptions"
    )
    interfaces_explicit = bool(record.interfaces) and all(
        str(i.get("name", "")).strip() and (i.get("signature") or i.get("contract") or i.get("shape"))
        for i in record.interfaces
    )
    (evidence if interfaces_explicit else gaps).append(
        "interfaces have names and contracts" if interfaces_explicit else "interfaces missing names/contracts"
    )
    if record.blocking_questions:
        gaps.append("blocking questions remain")
    else:
        evidence.append("no blocking questions")
    unresolved = [d for d in record.decisions if str(d.get("status", "decided")).lower() not in {"decided", "accepted", "final"}]
    if unresolved:
        gaps.append("unresolved product/architecture decisions")
    else:
        evidence.append("all decisions resolved")
    bounded = len(record.steps) <= MAX_SIMPLE_STEPS and len(record.files) <= MAX_SIMPLE_FILES and bool(record.files)
    (evidence if bounded else gaps).append(
        f"bounded: {len(record.steps)} steps, {len(record.files)} files"
        if bounded
        else f"not bounded (steps {len(record.steps)}/{MAX_SIMPLE_STEPS}, files {len(record.files)}/{MAX_SIMPLE_FILES})"
    )
    concrete_tests = bool(record.tests) and all(
        str(t.get("check") or t.get("command") or t.get("expect") or "").strip() for t in record.tests
    )
    (evidence if concrete_tests else gaps).append(
        "tests state observable checks" if concrete_tests else "tests are not concrete observable checks"
    )
    if record.self_assessed_simple:
        evidence.append("model self-assessment recorded but not used as evidence")
    clarity = Clarity.CLEAR_AND_SIMPLE if not gaps else Clarity.UNCLEAR
    return ClarityAssessment(clarity=clarity, evidence=evidence, gaps=gaps)


def assess_risk(record: ArchitectureRecord, prose: str) -> tuple[RiskLevel, list[str], list[str]]:
    """Returns (risk level, highest-required reasons, all risk notes)."""
    notes: list[str] = []
    highest: list[str] = []
    kinds = {str(r.get("kind", "")).lower() for r in record.risks}
    for kind in sorted(kinds):
        notes.append(f"declared risk: {kind}")
    for kind in ("money_movement", "money", "payments", "privacy", "security"):
        if kind in kinds:
            highest.append(f"architecture declares {kind} risk")
    text = " ".join([record.goal, record.scope, *[str(s.get("description", "")) for s in record.steps]])
    assessment = classify(ClassifierInput(text=text))
    for flag in assessment.risk_flags:
        if flag in {RiskFlag.MONEY_MOVEMENT, RiskFlag.PRIVACY, RiskFlag.SECURITY}:
            highest.append(f"implementation text involves {flag.value.replace('_', ' ')}")
    risky = bool(highest) or bool(kinds & {"destructive", "data_loss", "migration", "production"})
    return (RiskLevel.HIGH_RISK if risky else RiskLevel.LOW_RISK), sorted(set(highest)), notes


def git_identity(root: str) -> dict[str, Any]:
    info: dict[str, Any] = {"root": root}
    try:
        head = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        branch = subprocess.run(["git", "-C", root, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=5)
        top = subprocess.run(["git", "-C", root, "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        info["git"] = "unavailable"
        return info
    if head.returncode == 0:
        info.update(git_head=head.stdout.strip(), branch=branch.stdout.strip(), toplevel=top.stdout.strip())
    else:
        info["git"] = "not a git repository"
    return info


def check_project_association(record: ArchitectureRecord, project_root: str) -> list[str]:
    problems: list[str] = []
    root = Path(project_root).resolve()
    if record.repository:
        named = Path(record.repository).expanduser()
        if named.is_absolute() and named.resolve() != root and root not in named.resolve().parents:
            problems.append(
                f"architecture names repository {record.repository!r}, but this router project is {project_root!r}; "
                "which project should receive the implementation thread?"
            )
    for file_path in record.files:
        candidate = Path(file_path)
        if candidate.is_absolute():
            try:
                candidate.resolve().relative_to(root)
            except ValueError:
                problems.append(f"file {file_path!r} is outside the project root {project_root!r}")
    return problems


def build_package(
    *,
    record: ArchitectureRecord,
    prose: str,
    acceptance: AcceptanceEvidence,
    source_thread_id: str,
    project: dict[str, Any],
    architecture_version: int,
    attachments: list[dict[str, Any]],
    clarity: ClarityAssessment,
    risk: RiskLevel,
    risk_notes: list[str],
) -> tuple[dict[str, Any], str]:
    package = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "architecture_version": architecture_version,
        "source_thread_id": source_thread_id,
        "project": {"id": project["id"], "name": project["name"], "root": project["root"], "worktree": project.get("worktree")},
        "repository": git_identity(project.get("worktree") or project["root"]),
        "architecture_prose": prose,
        "architecture_record": record.to_dict(),
        "decisions": record.decisions,
        "constraints": record.constraints,
        "approved_scope": record.scope,
        "acceptance_tests": record.tests,
        "attachments": attachments,
        "nonblocking_items": record.nonblocking_items,
        "owner_acceptance": acceptance.to_dict(),
        "clarity": {"value": clarity.clarity.value, "evidence": clarity.evidence, "gaps": clarity.gaps},
        "risk": {"value": risk.value, "notes": risk_notes},
        "created_at": utc_now(),
    }
    return package, content_hash(package)


def render_initial_context(package: dict[str, Any], package_hash: str) -> str:
    """The implementation thread's first input: the full package, not a summary."""
    return (
        "You are implementing an architecture the owner has accepted. The complete handoff package follows; "
        "treat it as the source of truth. Stay within the approved scope and the project root. Do not commit, "
        "push, or delete files unless the owner asks. Report changed files and test results.\n\n"
        f"Handoff package sha256: {package_hash}\n\n"
        "```json\n" + json.dumps(package, indent=2, ensure_ascii=False) + "\n```\n"
    )


def context_fits(text: str, budget_chars: int) -> tuple[bool, str]:
    size = len(text)
    if size <= budget_chars:
        return True, f"{size} characters within the configured {budget_chars}-character budget"
    return False, (
        f"handoff needs {size} characters but the configured provider context budget is {budget_chars}. "
        "The full package is saved locally and nothing was cut. Options: raise the budget if the model supports it, "
        "or approve a staged context plan (send sections in order, each acknowledged)."
    )


def canonical(value: Any) -> str:
    return canonical_json(value)
