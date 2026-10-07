# AI Workflow Comparison validation

Scope: the installable `pm-tactical` comparison skill for issue #94. The
separate UI and video are optional work and are excluded from this change.

## Fresh checks on 2026-10-07

The coordinating agent reran these checks after resuming the preserved
implementation at `e8aeb823f58408c18a84c1fdfa198ece583d44cf`, including the
five new copied-plugin regressions. All checks passed before this validation
record and the regression/evidence commit were created.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/ai-workflow-trial -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 pm-tactical/skills/ai-workflow-trial/tools/run_uat.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/tests -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_repository_integrity.py
PYTHONDONTWRITEBYTECODE=1 python3 tests/lint_skill.py pm-tactical/skills/ai-workflow-trial/SKILL.md
```

Results: **32 comparison unit tests** (27 accounting and 5 copied-plugin),
**9 CLI UAT checks**, **24 gate tests**, repository integrity and skill lint.
The runner used Python 3.12 with a minimal subprocess environment. None of
these checks made a model or provider request.

## Installed-copy coverage

The new suite resolves the marketplace source and copies only `pm-tactical`
into a temporary installation directory. From an unrelated project directory
with spaces, isolated Python subprocesses check:

- The catalog/plugin names and explicit
  `/pm-tactical:ai-workflow-comparison` command, using the skill frontmatter
  name while retaining the compatible folder and schema identifiers.
- Bundled instructions, runtime, templates, examples, UAT and local links.
- The exact skill command recipes after documented path/cutoff substitution,
  with inputs and outputs outside the plugin cache.
- All three synthetic scenarios, missing data, immature cutoffs, unresolved
  templates and frozen-plan overwrite refusal.
- A custom four-unit comparison retaining unfinished mixed-workflow tasks
  under original assignment, with all four measured labor stages.
- Bundled UAT and walkthrough execution without a repository dependency.
- Unchanged installed bundle bytes after each workflow.

The public smoke workflow discovers `test_*.py`, so it includes the new
copied-plugin regressions without another workflow or dependency.

## What this evidence establishes

The local package can guide manual collection and execute its deterministic
plan/template/audit workflow when Python and ordinary file access are
available. The calculator preserves assigned denominators, failed and
unfinished work, deviations, customer outcomes, measured labor and declared
omissions. Its examples remain synthetic teaching data.

Claude Code is absent in this executor. These are **offline copied-plugin
checks**, not a native installer, skill-loader, trigger-quality or paid/included
host-usage test. They establish no measured customer savings, causal effect,
workflow winner, ROI or launch verdict. Remote publication, draft PR checks
and review must be verified separately; this file does not assert that they
occurred.

An earlier independent source review reported 32 tests, 28 copied-package
checks and 19 local links passing with no remaining findings. That is prior
working-tree review evidence, not a new review or the fresh checks above.
