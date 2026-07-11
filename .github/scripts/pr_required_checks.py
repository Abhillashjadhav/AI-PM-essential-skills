#!/usr/bin/env python3
"""Run dependency-free, deterministic pull-request quality gates."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "Anthropic API key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
}
PRIVATE_FILENAMES = {
    ".env",
    "cookies.sqlite",
    "credentials.json",
    "session.json",
}


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=check,
        capture_output=True,
        text=True,
    )


def changed_paths(base: str, head: str) -> list[str]:
    result = git("diff", "--name-only", f"{base}...{head}")
    return [line for line in result.stdout.splitlines() if line]


def existing_skill_roots(base: str) -> set[str]:
    result = git("ls-tree", "-r", "--name-only", base)
    return {
        str(Path(path).parent)
        for path in result.stdout.splitlines()
        if path == "SKILL.md" or path.endswith("/SKILL.md")
    }


def impacted_skills(paths: list[str], roots: set[str]) -> list[str]:
    return sorted(
        root
        for root in roots
        if any(path == f"{root}/SKILL.md" or path.startswith(f"{root}/") for path in paths)
    )


def added_lines(base: str, head: str) -> list[str]:
    result = git("diff", "--unified=0", "--no-color", f"{base}...{head}")
    return [
        line[1:]
        for line in result.stdout.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def privacy_findings(paths: list[str], lines: list[str]) -> list[str]:
    findings = [f"private filename: {path}" for path in paths if Path(path).name.lower() in PRIVATE_FILENAMES]
    for number, line in enumerate(lines, start=1):
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(line):
                findings.append(f"{label} pattern in added line {number}")
    return findings


def syntax_errors(paths: list[str]) -> list[str]:
    errors: list[str] = []
    for path_string in paths:
        path = Path(path_string)
        if path.suffix != ".py" or not path.is_file():
            continue
        try:
            compile(path.read_text(encoding="utf-8"), path_string, "exec")
        except (OSError, UnicodeError, SyntaxError) as exc:
            errors.append(f"{path_string}: {exc}")
    return errors


def run_tests() -> int:
    commands: list[list[str]] = []
    if any(Path(".github/tests").rglob("test*.py")):
        commands.append([sys.executable, "-m", "unittest", "discover", "-s", ".github/tests", "-v"])
    if any(Path("context-port/tests").rglob("test*.py")):
        commands.append([sys.executable, "-m", "unittest", "discover", "-s", "context-port/tests", "-v"])
    for command in commands:
        completed = subprocess.run(command, check=False)
        if completed.returncode:
            return completed.returncode
    if not commands:
        print("TESTS: PASS (no test directories present)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--head-ref", required=True)
    arguments = parser.parse_args(argv)

    failures: list[str] = []
    paths = changed_paths(arguments.base, arguments.head)

    diff_check = git("diff", "--check", f"{arguments.base}...{arguments.head}", check=False)
    if diff_check.returncode:
        failures.append(f"git diff check failed:\n{diff_check.stdout}{diff_check.stderr}")
    else:
        print("GIT DIFF CHECK: PASS")

    syntax = syntax_errors(paths)
    if syntax:
        failures.extend(f"compilation failed: {error}" for error in syntax)
    else:
        print(f"COMPILATION: PASS ({sum(path.endswith('.py') for path in paths)} changed Python path(s))")

    privacy = privacy_findings(paths, added_lines(arguments.base, arguments.head))
    if privacy:
        failures.extend(f"privacy check failed: {finding}" for finding in privacy)
    else:
        print("PRIVACY CHECK: PASS")

    skills = impacted_skills(paths, existing_skill_roots(arguments.base))
    if skills:
        print(f"EXISTING-SKILL IMPACT: {', '.join(skills)}")
    else:
        print("EXISTING-SKILL IMPACT: NONE")
    if arguments.head_ref.startswith("context-port/") and skills:
        failures.append("ContextPort change modifies existing skill content")

    if run_tests():
        failures.append("test suite failed")
    else:
        print("TESTS: PASS")

    if failures:
        print("REQUIRED CHECKS: FAIL", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("REQUIRED CHECKS: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
