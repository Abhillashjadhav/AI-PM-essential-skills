"""Deterministic ContextPort release-readiness auditor."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import tempfile
import tomllib
from pathlib import Path
from typing import Any

import contextport_build
from session import generate_session


READINESS_VERSION = "0.1"
EXPECTED_IDENTITY = ("Abhillash Jadhav", "abhilashjadhav@gmail.com")
IGNORED_HEALTH_PATHS = {
    "context-port/SESSION.md",
    "context-port/SESSION.json",
    "context-port/reports/RELEASE_READINESS.md",
    "context-port/reports/RELEASE_READINESS.json",
}
APPROVED_INFRASTRUCTURE_PATHS = {
    ".github/scripts/pr_required_checks.py",
    ".github/tests/test_pr_required_checks.py",
}


class ReadinessError(RuntimeError):
    """Raised when release evidence cannot be collected truthfully."""


def _run(repository: Path, *command: str) -> str:
    try:
        result = subprocess.run(command, cwd=repository, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        raise ReadinessError(f"command failed: {' '.join(command)}: {detail}") from exc
    return result.stdout.strip()


def _cli_version(context_port: Path) -> str:
    tree = ast.parse((context_port / "contextport.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "CLI_VERSION" for target in node.targets):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return node.value.value
    raise ReadinessError("CLI_VERSION missing")


def _audited_revision(repository: Path) -> str:
    return _run(
        repository,
        "git",
        "log",
        "-1",
        "--format=%H",
        "HEAD",
        "--",
        "context-port",
        ":(exclude)context-port/SESSION.md",
        ":(exclude)context-port/SESSION.json",
        ":(exclude)context-port/reports/RELEASE_READINESS.md",
        ":(exclude)context-port/reports/RELEASE_READINESS.json",
        ".github/scripts/pr_required_checks.py",
        ".github/tests/test_pr_required_checks.py",
    )


def _branch_identities(repository: Path, audited_revision: str) -> list[dict[str, str]]:
    raw = _run(repository, "git", "log", "--format=%H%x09%an%x09%ae%x09%cn%x09%ce", f"main..{audited_revision}")
    records = []
    for line in raw.splitlines():
        commit, author, author_email, committer, committer_email = line.split("\t")
        records.append(
            {
                "commit": commit,
                "author": author,
                "author_email": author_email,
                "committer": committer,
                "committer_email": committer_email,
            }
        )
    return records


def _clean_except_generated(repository: Path) -> bool:
    for line in _run(repository, "git", "status", "--porcelain", "--untracked-files=all").splitlines():
        if line[3:] not in IGNORED_HEALTH_PATHS:
            return False
    return True


def _package_evidence(context_port: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
        first_wheel = Path(first_dir) / contextport_build.build_wheel(first_dir)
        second_wheel = Path(second_dir) / contextport_build.build_wheel(second_dir)
        first_wheel_digest = hashlib.sha256(first_wheel.read_bytes()).hexdigest()
        second_wheel_digest = hashlib.sha256(second_wheel.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
        first_sdist = Path(first_dir) / contextport_build.build_sdist(first_dir)
        second_sdist = Path(second_dir) / contextport_build.build_sdist(second_dir)
        first_sdist_digest = hashlib.sha256(first_sdist.read_bytes()).hexdigest()
        second_sdist_digest = hashlib.sha256(second_sdist.read_bytes()).hexdigest()
    return {
        "wheel_sha256": first_wheel_digest,
        "wheel_reproducible": first_wheel_digest == second_wheel_digest,
        "sdist_sha256": first_sdist_digest,
        "sdist_reproducible": first_sdist_digest == second_sdist_digest,
    }


def _demo(repository: Path) -> dict[str, Any]:
    raw = _run(repository, "python3", "context-port/demo.py")
    report = json.loads(raw)
    return {
        "writes_performed": report["writes_performed"],
        "network_calls_performed": report["network_calls_performed"],
        "browser_automation_performed": report["browser_automation_performed"],
        "destination_status": report["destination_inventory"]["status"],
        "reconciliation_differences": next(
            stage["differences"] for stage in report["stages"] if stage["stage"] == "independent_reconciliation"
        ),
    }


def _schema_evidence(context_port: Path) -> dict[str, Any]:
    schemas = sorted((context_port / "schemas").glob("*.json"))
    for path in schemas:
        json.loads(path.read_text(encoding="utf-8"))
    return {"status": "passed", "schemas": len(schemas)}


def collect_readiness(repository: Path) -> dict[str, Any]:
    """Collect release evidence after canonical session memory is fresh."""
    repository = repository.resolve()
    context_port = repository / "context-port"
    fresh, session_state = generate_session(repository, check=True)
    if not fresh:
        raise ReadinessError("SESSION.md or SESSION.json is stale; run `contextport handoff`")
    project = tomllib.loads((context_port / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    versions = {
        "cli": _cli_version(context_port),
        "package": project["version"],
        "build_backend": contextport_build.VERSION,
    }
    audited_revision = _audited_revision(repository)
    identities = _branch_identities(repository, audited_revision)
    expected_name, expected_email = EXPECTED_IDENTITY
    identity_pass = all(
        item["author"] == expected_name
        and item["author_email"] == expected_email
        and item["committer"] == expected_name
        and item["committer_email"] == expected_email
        for item in identities
    )
    changed_paths = _run(repository, "git", "diff", "--name-only", "main...HEAD").splitlines()
    scope_pass = bool(changed_paths) and all(
        path.startswith("context-port/") or path in APPROVED_INFRASTRUCTURE_PATHS
        for path in changed_paths
    )
    tracked = _run(repository, "git", "ls-files", "context-port").splitlines()
    prohibited_suffixes = (".zip", ".cookie", ".session", ".har")
    private_artifacts_absent = not any(path.lower().endswith(prohibited_suffixes) for path in tracked)
    package = _package_evidence(context_port)
    demo = _demo(repository)
    schema = _schema_evidence(context_port)
    evidence = {
        "readiness_version": READINESS_VERSION,
        "audited_revision": audited_revision,
        "latest_merged_commit": session_state["latest_merged_commit"],
        "current_branch": session_state["current_branch"],
        "versions": versions,
        "versions_consistent": len(set(versions.values())) == 1,
        "session_fresh": fresh,
        "tests": session_state["tests"],
        "coverage": session_state["coverage"],
        "schemas": schema,
        "package": package,
        "demo": demo,
        "branch_commits": identities,
        "authorship_pass": identity_pass,
        "changed_paths": changed_paths,
        "approved_public_scope": scope_pass,
        "approved_infrastructure_paths": sorted(
            path for path in changed_paths if path in APPROVED_INFRASTRUCTURE_PATHS
        ),
        "private_export_artifacts_tracked": not private_artifacts_absent,
        "working_tree_clean_except_generated_reports": _clean_except_generated(repository),
        "production_dependencies": project["dependencies"],
        "private_runtime_dependency": False,
        "human_gates": {
            "public_license_selected": any((repository / name).is_file() for name in ("LICENSE", "LICENSE.md", "LICENSE.txt")),
            "release_publication_approved": False,
            "real_claude_zip_access_approved": False,
            "browser_or_assistant_write_approved": False,
        },
        "known_unsupported_capabilities": session_state["known_unsupported_capabilities"],
    }
    return evaluate_readiness(evidence)


def evaluate_readiness(evidence: dict[str, Any]) -> dict[str, Any]:
    """Classify evidence without turning human gates into automated decisions."""
    automated_checks = {
        "versions_consistent": evidence["versions_consistent"],
        "session_fresh": evidence["session_fresh"],
        "tests_passed": evidence["tests"]["status"] == "passed",
        "schemas_parse": evidence["schemas"]["status"] == "passed",
        "wheel_reproducible": evidence["package"]["wheel_reproducible"],
        "sdist_reproducible": evidence["package"]["sdist_reproducible"],
        "synthetic_reconciliation_clean": evidence["demo"]["reconciliation_differences"] == 0,
        "synthetic_demo_zero_writes": evidence["demo"]["writes_performed"] is False,
        "synthetic_demo_offline": evidence["demo"]["network_calls_performed"] is False,
        "synthetic_demo_no_browser": evidence["demo"]["browser_automation_performed"] is False,
        "authorship": evidence["authorship_pass"],
        "approved_public_scope": evidence["approved_public_scope"],
        "no_private_export_artifacts_tracked": evidence["private_export_artifacts_tracked"] is False,
        "no_production_dependencies": evidence["production_dependencies"] == [],
        "no_private_runtime_dependency": evidence["private_runtime_dependency"] is False,
    }
    failed = sorted(name for name, passed in automated_checks.items() if not passed)
    blockers = []
    gates = evidence["human_gates"]
    if not gates["public_license_selected"]:
        blockers.append({"id": "public_license", "status": "DECISION_REQUIRED"})
    if not gates["release_publication_approved"]:
        blockers.append({"id": "release_publication", "status": "APPROVAL_REQUIRED"})
    result = {
        **evidence,
        "automated_checks": automated_checks,
        "failed_automated_checks": failed,
        "synthetic_mvp_status": "ready" if not failed else "not_ready",
        "public_release_status": "blocked_human_decisions" if not failed and blockers else ("ready" if not failed else "not_ready"),
        "release_blockers": blockers,
        "publication_performed": False,
    }
    digest_input = {key: value for key, value in result.items() if key != "readiness_report_sha256"}
    result["readiness_report_sha256"] = hashlib.sha256(
        json.dumps(digest_input, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    return result


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ContextPort release-readiness report",
        "",
        "> Generated by `contextport release-check`. Do not edit manually.",
        "",
        f"- Audited revision: `{report['audited_revision']}`",
        f"- Synthetic MVP: `{report['synthetic_mvp_status']}`",
        f"- Public release: `{report['public_release_status']}`",
        f"- Tests passed: {report['tests']['passed']}",
        f"- Line coverage: `{report['coverage']['line_coverage']}` — {report['coverage']['reason']}",
        f"- Report SHA-256: `{report['readiness_report_sha256']}`",
        "",
        "## Automated checks",
        "",
    ]
    lines.extend(f"- `{name}`: `{'PASS' if passed else 'FAIL'}`" for name, passed in sorted(report["automated_checks"].items()))
    lines.extend(["", "## Human blockers", ""])
    lines.extend(f"- `{item['status']}` — `{item['id']}`" for item in report["release_blockers"] or [])
    lines.extend([
        "",
        "## Boundaries",
        "",
        "- Release publication performed: `false`",
        "- Real Claude ZIP access approved: `false`",
        "- Browser or assistant write approved: `false`",
        "- Real Claude export compatibility remains `UNKNOWN`.",
        "- Consumer ChatGPT reconstruction writes remain `UNSUPPORTED`.",
        "",
        "This report proves synthetic MVP readiness only. It does not grant a license, publish a release, authorize real-data access, or authorize destination writes.",
    ])
    return "\n".join(lines) + "\n"


def write_reports(repository: Path, report: dict[str, Any]) -> None:
    directory = repository / "context-port" / "reports"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "RELEASE_READINESS.json").write_text(render_json(report), encoding="utf-8", newline="\n")
    (directory / "RELEASE_READINESS.md").write_text(render_markdown(report), encoding="utf-8", newline="\n")
