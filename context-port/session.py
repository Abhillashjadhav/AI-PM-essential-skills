"""Generate deterministic ContextPort repository session memory."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


SESSION_VERSION = "0.1"
PHASES = {
    1: "bootstrap",
    2: "ContextPack schema",
    3: "safe export inspection",
    4: "project segregation",
    5: "human review UI",
    6: "context reconstruction",
    7: "reconciliation reviewer",
    8: "incremental sync",
    9: "ChatGPT adapter",
    10: "CLI",
    11: "packaging",
    12: "installer",
    13: "synthetic demo",
    14: "documentation",
    15: "release readiness",
}
BRANCH_PHASE = re.compile(r"^context-port/(\d{3})-(.+)$")
PROMPT_PHASE = re.compile(r"^context-port/prompts/(\d{3})-.*\.md$")
MERGED_PR = re.compile(r"^(.*) \(#(\d+)\)$")
TEST_COUNT = re.compile(r"Ran (\d+) tests?")

REAL_ZIP_GATE = (
    "Fresh explicit human approval is required before locating, listing, hashing, extracting, "
    "opening, inspecting, parsing, copying, or uploading a real Claude ZIP."
)
BROWSER_WRITE_GATE = (
    "Fresh explicit human approval is required before browser automation or any ChatGPT or Claude write."
)


class SessionError(RuntimeError):
    """Raised when repository state cannot be observed truthfully."""


def _run(repository: Path, *command: str) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        raise SessionError(f"command failed: {' '.join(command)}: {detail}") from exc
    return result.stdout.strip()


def _version(context_port: Path) -> str:
    tree = ast.parse((context_port / "contextport.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "CLI_VERSION" for target in node.targets):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return node.value.value
    raise SessionError("CLI_VERSION was not found")


def _phase_numbers_on_main(repository: Path) -> set[int]:
    paths = _run(repository, "git", "ls-tree", "-r", "--name-only", "main", "--", "context-port/prompts")
    result: set[int] = set()
    for path in paths.splitlines():
        match = PROMPT_PHASE.fullmatch(path)
        if match:
            result.add(int(match.group(1)))
    return result


def _current_phase(branch: str, completed: set[int]) -> dict[str, Any] | None:
    match = BRANCH_PHASE.fullmatch(branch)
    if match:
        number = int(match.group(1))
        return {"number": number, "name": PHASES.get(number, match.group(2).replace("-", " "))}
    remaining = sorted(set(PHASES) - completed)
    return {"number": remaining[0], "name": PHASES[remaining[0]]} if remaining else None


def _merged_prs(repository: Path) -> list[dict[str, Any]]:
    history = _run(
        repository,
        "git",
        "log",
        "--first-parent",
        "--format=%H%x09%s",
        "main",
        "--",
        "context-port",
    )
    records = []
    for line in history.splitlines():
        commit, _, subject = line.partition("\t")
        match = MERGED_PR.fullmatch(subject)
        if match:
            records.append(
                {
                    "number": int(match.group(2)),
                    "title": match.group(1),
                    "commit": commit,
                    "url": f"https://github.com/Abhillashjadhav/AI-PM-essential-skills/pull/{match.group(2)}",
                }
            )
    return records


def _open_prs(repository: Path) -> list[dict[str, Any]]:
    raw = _run(
        repository,
        "gh",
        "pr",
        "list",
        "--state",
        "open",
        "--json",
        "number,title,headRefName,baseRefName,url,isDraft",
    )
    value = json.loads(raw or "[]")
    if not isinstance(value, list):
        raise SessionError("GitHub open PR response was not an array")
    records = [item for item in value if str(item.get("headRefName", "")).startswith("context-port/")]
    return sorted(records, key=lambda item: int(item["number"]))


def _tests(repository: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", "context-port/tests", "-q"],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "CONTEXTPORT_SESSION_TEST": "1"},
    )
    combined = result.stdout + result.stderr
    match = TEST_COUNT.search(combined)
    if result.returncode != 0 or not match:
        raise SessionError(f"test suite did not pass: {combined.strip()}")
    return {"status": "passed", "passed": int(match.group(1)), "command": "python3 -m unittest discover -s context-port/tests -q"}


def _syntax(context_port: Path) -> dict[str, Any]:
    files = sorted(path for path in context_port.rglob("*.py") if "__pycache__" not in path.parts)
    for path in files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {"status": "passed", "python_files": len(files)}


def _unsupported(context_port: Path) -> list[str]:
    lines = (context_port / "docs" / "CAPABILITIES.md").read_text(encoding="utf-8").splitlines()
    capabilities = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[1].startswith("`UNSUPPORTED`"):
            capabilities.append(cells[0])
    return capabilities


def collect_session(
    repository: Path,
    *,
    open_prs: list[dict[str, Any]] | None = None,
    test_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect canonical state. Optional observations support offline synthetic tests."""
    repository = repository.resolve()
    context_port = repository / "context-port"
    branch = _run(repository, "git", "branch", "--show-current")
    latest_merged = _run(repository, "git", "rev-parse", "main")
    completed_numbers = _phase_numbers_on_main(repository)
    current_phase = _current_phase(branch, completed_numbers)
    completed = [{"number": number, "name": PHASES[number]} for number in sorted(completed_numbers) if number in PHASES]
    remaining = [{"number": number, "name": PHASES[number]} for number in sorted(set(PHASES) - completed_numbers)]
    tests = test_result or _tests(repository)
    syntax = _syntax(context_port)
    worktree_clean = _worktree_clean(repository)
    origin_main = _run(repository, "git", "rev-parse", "origin/main") if _has_ref(repository, "origin/main") else None
    license_present = any((repository / name).is_file() for name in ("LICENSE", "LICENSE.md", "LICENSE.txt"))
    blockers = []
    if not license_present:
        blockers.append({"id": "public_license", "status": "decision_required", "detail": "No repository license file is present."})
    blockers.append({"id": "release_publication", "status": "approval_required", "detail": "No release may be published without explicit human approval."})
    health_status = "healthy" if worktree_clean and tests["status"] == "passed" and syntax["status"] == "passed" else "attention_required"
    return {
        "session_version": SESSION_VERSION,
        "contextport_version": _version(context_port),
        "current_phase": current_phase,
        "current_branch": branch,
        "latest_merged_commit": latest_merged,
        "completed_phases": completed,
        "remaining_phases": remaining,
        "open_prs": open_prs if open_prs is not None else _open_prs(repository),
        "merged_prs": _merged_prs(repository),
        "current_blockers": blockers,
        "tests": tests,
        "coverage": {
            "line_coverage": "UNKNOWN",
            "reason": "No coverage instrumentation dependency is configured.",
            "test_files": len(list((context_port / "tests").glob("test_*.py"))),
        },
        "repository_health": {
            "status": health_status,
            "working_tree_clean_at_collection": worktree_clean,
            "syntax": syntax,
            "origin_main_matches_latest_merged": origin_main == latest_merged if origin_main else "UNKNOWN",
            "existing_skill_runtime_dependency": False,
        },
        "resume_command": "cd <public-checkout>/AI-PM-essential-skills && git switch " + branch + " && python3 context-port/contextport.py handoff --check",
        "resume_prompt": _resume_prompt(current_phase, remaining),
        "real_claude_zip_gate": REAL_ZIP_GATE,
        "browser_write_gate": BROWSER_WRITE_GATE,
        "known_unsupported_capabilities": _unsupported(context_port),
    }


def _has_ref(repository: Path, ref: str) -> bool:
    result = subprocess.run(["git", "show-ref", "--verify", "--quiet", f"refs/remotes/{ref}"], cwd=repository)
    return result.returncode == 0


def _worktree_clean(repository: Path) -> bool:
    generated = {
        "context-port/SESSION.md",
        "context-port/SESSION.json",
        "context-port/reports/RELEASE_READINESS.md",
        "context-port/reports/RELEASE_READINESS.json",
    }
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=repository,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.decode(errors="replace").strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        raise SessionError(f"command failed: git status --porcelain=v1 -z --untracked-files=all: {detail}") from exc
    for entry in result.stdout.split(b"\0"):
        if not entry:
            continue
        line = entry.decode("utf-8", errors="surrogateescape")
        path = line[3:]
        if " -> " in path:
            return False
        if path not in generated:
            return False
    return True


def _resume_prompt(current_phase: dict[str, Any] | None, remaining: list[dict[str, Any]]) -> str:
    if current_phase:
        phase = f"Phase {current_phase['number']} ({current_phase['name']})"
        return f"Resume ContextPort {phase} from SESSION.json. Verify repository health and approval gates before continuing."
    if remaining:
        phase = remaining[0]
        return f"Start ContextPort Phase {phase['number']} ({phase['name']}) from SESSION.json after verifying main."
    return "ContextPort phases are complete. Stop at the documented human approval gates; do not publish or access real data automatically."


def render_json(state: dict[str, Any]) -> str:
    return json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_markdown(state: dict[str, Any]) -> str:
    phase = state["current_phase"]
    phase_text = f"Phase {phase['number']} — {phase['name']}" if phase else "No active phase"
    lines = [
        "# ContextPort session",
        "",
        "> Generated by `contextport handoff`. Do not edit manually.",
        "",
        f"- ContextPort version: `{state['contextport_version']}`",
        f"- Current phase: {phase_text}",
        f"- Current branch: `{state['current_branch']}`",
        f"- Latest merged commit: `{state['latest_merged_commit']}`",
        f"- Tests passed: {state['tests']['passed']}",
        f"- Line coverage: `{state['coverage']['line_coverage']}` — {state['coverage']['reason']}",
        f"- Repository health: `{state['repository_health']['status']}`",
        "",
        "## Completed phases",
        "",
    ]
    lines.extend(f"- Phase {item['number']}: {item['name']}" for item in state["completed_phases"])
    lines.extend(["", "## Remaining phases", ""])
    lines.extend(f"- Phase {item['number']}: {item['name']}" for item in state["remaining_phases"] or [{"number": "—", "name": "None"}])
    lines.extend(["", "## Open PRs", ""])
    lines.extend(_pr_lines(state["open_prs"]) or ["- None"])
    lines.extend(["", "## Merged PRs", ""])
    lines.extend(f"- [#{item['number']}]({item['url']}) — {item['title']} (`{item['commit'][:12]}`)" for item in state["merged_prs"])
    lines.extend(["", "## Current blockers", ""])
    lines.extend(f"- `{item['status']}` — {item['detail']}" for item in state["current_blockers"] or [])
    lines.extend([
        "",
        "## Repository health",
        "",
        f"- Tests: `{state['tests']['status']}` ({state['tests']['passed']})",
        f"- Syntax: `{state['repository_health']['syntax']['status']}` ({state['repository_health']['syntax']['python_files']} Python files)",
        f"- Working tree clean at collection: `{str(state['repository_health']['working_tree_clean_at_collection']).lower()}`",
        f"- `origin/main` matches latest merged commit: `{str(state['repository_health']['origin_main_matches_latest_merged']).lower()}`",
        "- Existing AI-PM skill runtime dependency: `false`",
        "",
        "## Resume",
        "",
        "```sh",
        state["resume_command"],
        "```",
        "",
        "```text",
        state["resume_prompt"],
        "```",
        "",
        "## Approval gates",
        "",
        f"- Real Claude ZIP: {state['real_claude_zip_gate']}",
        f"- Browser/write: {state['browser_write_gate']}",
        "",
        "## Known unsupported capabilities",
        "",
    ])
    lines.extend(f"- {item}" for item in state["known_unsupported_capabilities"])
    return "\n".join(lines) + "\n"


def _pr_lines(records: list[dict[str, Any]]) -> list[str]:
    return [f"- [#{item['number']}]({item['url']}) — {item['title']} (`{item['headRefName']}`)" for item in records]


def generate_session(
    repository: Path,
    *,
    check: bool = False,
    open_prs: list[dict[str, Any]] | None = None,
    test_result: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, Any]]:
    state = collect_session(repository, open_prs=open_prs, test_result=test_result)
    outputs = {
        repository / "context-port" / "SESSION.json": render_json(state),
        repository / "context-port" / "SESSION.md": render_markdown(state),
    }
    current = {path: path.read_text(encoding="utf-8") if path.exists() else None for path in outputs}
    fresh = all(current[path] == content for path, content in outputs.items())
    if check:
        return fresh, state
    for path, content in outputs.items():
        _atomic_write(path, content)
    return True, state


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
