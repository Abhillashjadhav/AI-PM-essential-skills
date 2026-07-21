#!/usr/bin/env python3
"""Validate the public repository layout without external dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "token-cost-estimator",
    "eval-rubric-generator",
    "context-auditor",
    "concise-rewriter",
)
CONTEXT_PORT_QUICK_START_PATHS = (
    "context-port/contextport.py",
    "context-port/demo.py",
    "context-port/tests",
    "context-port/fixtures/contextpack-valid.json",
)
MARKETPLACE_PATH = ".claude-plugin/marketplace.json"
LINK_PATTERN = re.compile(r"(?<!!)\[[^]]*\]\(([^)]+)\)")
FIXTURE_PATTERN = re.compile(r"(?<![\w.-])((?:context-port/)?fixtures/[\w./-]+)")
HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)


def anchor_slug(heading: str) -> str:
    """Produce the GitHub-style anchor used for the repository's simple headings."""
    normalized = heading.strip().lower()
    normalized = re.sub(r"[^\w\s-]", "", normalized)
    return re.sub(r"[\s-]+", "-", normalized).strip("-")


def markdown_paths() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if ".git" not in path.parts and ".agents" not in path.parts
    )


def local_link_target(raw_target: str) -> tuple[str, str] | None:
    target = raw_target.strip().strip("<>")
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None
    if target.startswith(("mailto:", "#")):
        return ("", unquote(parsed.fragment))
    return (unquote(parsed.path), unquote(parsed.fragment))


def validate_markdown_link(document: Path, raw_target: str) -> str | None:
    local_target = local_link_target(raw_target)
    if local_target is None:
        return None
    path_part, fragment = local_target
    destination = document if not path_part else (document.parent / path_part).resolve()
    try:
        destination.relative_to(ROOT)
    except ValueError:
        return f"{document.relative_to(ROOT)}: link escapes repository: {raw_target}"
    if not destination.exists():
        return f"{document.relative_to(ROOT)}: missing link target: {raw_target}"
    if fragment and destination.suffix.lower() == ".md":
        headings = {anchor_slug(match.group(1)) for match in HEADING_PATTERN.finditer(destination.read_text(encoding="utf-8"))}
        if anchor_slug(fragment) not in headings:
            return f"{document.relative_to(ROOT)}: missing heading #{fragment} in {destination.relative_to(ROOT)}"
    return None


def fixture_paths(readme: Path) -> list[Path]:
    """Return fixture paths named in a README, supporting root and local forms."""
    paths: list[Path] = []
    for match in FIXTURE_PATTERN.finditer(readme.read_text(encoding="utf-8")):
        mention = match.group(1).rstrip(".,;:)")
        if mention.startswith("context-port/"):
            paths.append(ROOT / mention)
        else:
            paths.append(readme.parent / mention)
    return paths


def validate_plugin_directories() -> tuple[list[str], int]:
    failures: list[str] = []
    marketplace_path = ROOT / MARKETPLACE_PATH
    try:
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return ([f"cannot read plugin marketplace: {exc}"], 0)

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list):
        return (["plugin marketplace must contain a plugins array"], 0)

    for entry in plugins:
        if not isinstance(entry, dict):
            failures.append("plugin marketplace entry must be an object")
            continue
        name = entry.get("name")
        source = entry.get("source")
        if not isinstance(name, str) or not name or not isinstance(source, str) or not source:
            failures.append("plugin marketplace entry requires string name and source")
            continue
        directory = (ROOT / source).resolve()
        try:
            directory.relative_to(ROOT)
        except ValueError:
            failures.append(f"plugin source escapes repository: {source}")
            continue
        manifest_path = directory / ".claude-plugin" / "plugin.json"
        if not manifest_path.is_file():
            failures.append(f"missing plugin manifest: {manifest_path.relative_to(ROOT)}")
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            failures.append(f"cannot read {manifest_path.relative_to(ROOT)}: {exc}")
            continue
        if manifest.get("name") != name:
            failures.append(
                f"plugin name mismatch: marketplace {name!r}, manifest {manifest.get('name')!r}"
            )
    return (failures, len(plugins))


def main() -> int:
    failures: list[str] = []
    for skill in SKILLS:
        directory = ROOT / skill
        if not directory.is_dir():
            failures.append(f"missing skill directory: {skill}")
        elif not (directory / "SKILL.md").is_file():
            failures.append(f"missing skill definition: {skill}/SKILL.md")

    plugin_failures, plugin_count = validate_plugin_directories()
    failures.extend(plugin_failures)

    documents = markdown_paths()
    for document in documents:
        text = document.read_text(encoding="utf-8")
        for target in LINK_PATTERN.findall(text):
            failure = validate_markdown_link(document, target)
            if failure:
                failures.append(failure)

    readmes = sorted(path for path in documents if path.name.startswith("README"))
    for readme in readmes:
        for fixture in fixture_paths(readme):
            if not fixture.is_file():
                failures.append(
                    f"{readme.relative_to(ROOT)}: missing mentioned fixture: "
                    f"{fixture.relative_to(ROOT) if fixture.is_relative_to(ROOT) else fixture}"
                )

    for path_string in CONTEXT_PORT_QUICK_START_PATHS:
        if not (ROOT / path_string).exists():
            failures.append(f"missing ContextPort quick-start path: {path_string}")

    if failures:
        print("REPOSITORY INTEGRITY: FAIL", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(
        "REPOSITORY INTEGRITY: PASS "
        f"({len(SKILLS)} skills, {plugin_count} plugin directories, "
        f"{len(documents)} Markdown documents, "
        f"{len(CONTEXT_PORT_QUICK_START_PATHS)} ContextPort paths)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
