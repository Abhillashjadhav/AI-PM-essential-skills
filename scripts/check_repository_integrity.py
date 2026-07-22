#!/usr/bin/env python3
"""Validate the public marketplace and repository layout without external dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = ROOT / ".claude-plugin" / "marketplace.json"
EXPECTED_PLUGINS = (
    "pm-tactical",
    "pm-verifier",
    "mcp-migration-auditor",
    "loop-designer",
)
STANDALONE_SKILLS = (
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
LINK_PATTERN = re.compile(r"(?<!!)\[[^]]*\]\(([^)]+)\)")
FIXTURE_PATTERN = re.compile(r"(?<![\w.-])((?:context-port/)?fixtures/[\w./-]+)")
HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)


def anchor_slug(heading: str) -> str:
    """Produce the GitHub-style anchor used for the repository's simple headings."""
    normalized = heading.strip().lower()
    normalized = re.sub(r"[^\w\s-]", "", normalized)
    return re.sub(r"[\s-]+", "-", normalized).strip("-")


def readme_paths() -> list[Path]:
    return sorted(path for path in ROOT.rglob("README*.md") if ".git" not in path.parts)


def local_link_target(raw_target: str) -> tuple[str, str] | None:
    target = raw_target.strip().strip("<>")
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None
    if target.startswith(("mailto:", "#")):
        return ("", unquote(parsed.fragment))
    return (unquote(parsed.path), unquote(parsed.fragment))


def validate_readme_link(readme: Path, raw_target: str) -> str | None:
    local_target = local_link_target(raw_target)
    if local_target is None:
        return None
    path_part, fragment = local_target
    destination = readme if not path_part else (readme.parent / path_part).resolve()
    try:
        destination.relative_to(ROOT)
    except ValueError:
        return f"{readme.relative_to(ROOT)}: link escapes repository: {raw_target}"
    if not destination.exists():
        return f"{readme.relative_to(ROOT)}: missing link target: {raw_target}"
    if fragment and destination.suffix.lower() == ".md":
        headings = {
            anchor_slug(match.group(1))
            for match in HEADING_PATTERN.finditer(destination.read_text(encoding="utf-8"))
        }
        if anchor_slug(fragment) not in headings:
            return (
                f"{readme.relative_to(ROOT)}: missing heading #{fragment} in "
                f"{destination.relative_to(ROOT)}"
            )
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


def validate_marketplace() -> list[str]:
    failures: list[str] = []
    if not MARKETPLACE_PATH.is_file():
        return ["missing marketplace manifest: .claude-plugin/marketplace.json"]

    try:
        marketplace = json.loads(MARKETPLACE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [f"invalid marketplace manifest: {exc}"]

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list):
        return ["marketplace manifest: plugins must be a list"]

    by_name: dict[str, dict[str, object]] = {}
    for raw in plugins:
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            failures.append("marketplace manifest: every plugin needs a string name")
            continue
        by_name[str(raw["name"])] = raw

    expected = set(EXPECTED_PLUGINS)
    actual = set(by_name)
    if actual != expected:
        failures.append(
            "marketplace plugin set mismatch: "
            f"missing={sorted(expected - actual)}, unexpected={sorted(actual - expected)}"
        )

    for plugin_name in EXPECTED_PLUGINS:
        entry = by_name.get(plugin_name)
        if entry is None:
            continue
        source = entry.get("source")
        if not isinstance(source, str) or not source.strip():
            failures.append(f"marketplace plugin {plugin_name}: missing source")
            continue
        plugin_dir = (ROOT / source).resolve()
        try:
            plugin_dir.relative_to(ROOT)
        except ValueError:
            failures.append(f"marketplace plugin {plugin_name}: source escapes repository")
            continue
        if not plugin_dir.is_dir():
            failures.append(f"marketplace plugin {plugin_name}: missing source directory {source}")
            continue

        manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
        if not manifest_path.is_file():
            failures.append(f"marketplace plugin {plugin_name}: missing .claude-plugin/plugin.json")
            continue
        try:
            plugin_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            failures.append(f"marketplace plugin {plugin_name}: invalid plugin manifest: {exc}")
            continue
        if plugin_manifest.get("name") != plugin_name:
            failures.append(
                f"marketplace plugin {plugin_name}: plugin manifest name is "
                f"{plugin_manifest.get('name')!r}"
            )
        if not (plugin_dir / "skills").is_dir():
            failures.append(f"marketplace plugin {plugin_name}: missing skills directory")

    return failures


def main() -> int:
    failures = validate_marketplace()

    for skill in STANDALONE_SKILLS:
        directory = ROOT / skill
        if not directory.is_dir():
            failures.append(f"missing standalone skill directory: {skill}")
        elif not (directory / "SKILL.md").is_file():
            failures.append(f"missing standalone skill definition: {skill}/SKILL.md")

    readmes = readme_paths()
    for readme in readmes:
        text = readme.read_text(encoding="utf-8")
        for target in LINK_PATTERN.findall(text):
            failure = validate_readme_link(readme, target)
            if failure:
                failures.append(failure)
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
        f"({len(EXPECTED_PLUGINS)} marketplace plugins, "
        f"{len(STANDALONE_SKILLS)} standalone skills, {len(readmes)} READMEs, "
        f"{len(CONTEXT_PORT_QUICK_START_PATHS)} ContextPort paths)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
