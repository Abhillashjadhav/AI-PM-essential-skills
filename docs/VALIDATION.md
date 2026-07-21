# Validation evidence

This document records what this repository's checks establish and what they do not establish. It applies the evidence labels used by ContextPort: `VERIFIED` means observable repository evidence exists, `UNKNOWN` means the available evidence does not establish the claim, and `UNSUPPORTED` means the product intentionally does not perform the behavior.

## Automatically checked

`VERIFIED` by [`scripts/check_repository_integrity.py`](../scripts/check_repository_integrity.py):

- the four public skill directories exist: `token-cost-estimator`, `eval-rubric-generator`, `context-auditor`, and `concise-rewriter`;
- each of those directories contains `SKILL.md`;
- each local Markdown link in every repository `README*.md` resolves to an existing file or directory, and local README anchors resolve to a heading;
- every fixture path mentioned in a README exists; and
- the ContextPort quick-start entry points and synthetic validation fixture exist.

`VERIFIED` by ContextPort's Python unit-test suite: deterministic local behavior exercised by [`context-port/tests/`](../context-port/tests/) against committed synthetic fixtures in [`context-port/fixtures/`](../context-port/fixtures/). These tests do not call a hosted model, inspect real exports, access an account, or perform destination writes.

## Manually validated material

The Markdown fixture documents under [`tests/`](../tests/) and product example directories provide reviewer prompts, known-answer cases, and expected outputs. They are **manual review material**, not automated behavioural tests: no repository command executes the four standalone Claude Code skills against those documents.

ContextPort's evaluation notes under [`context-port/evals/`](../context-port/evals/) record expected deterministic gates and synthetic-fixture observations. Review them with the corresponding command output; do not treat the documents alone as a passing automated run.

## Recorded behavioural model evidence

No recorded external-model behavioural runs are present for the four standalone skills. The repository therefore makes no evidence-backed claim about their live invocation, output quality, token counting accuracy, pricing accuracy, or interoperability with other Claude Code runtimes.

ContextPort's recorded evidence is local and synthetic. Its [release-readiness report](../context-port/reports/RELEASE_READINESS.md) distinguishes completed automated checks from `UNKNOWN` and `UNSUPPORTED` capabilities. It is not evidence of a real Claude export migration or a consumer ChatGPT reconstruction write.

## Unverified and unsupported behavior

- `UNKNOWN`: compatibility with real Claude or ChatGPT exports, unless separately approved and inspected under the repository rules.
- `UNKNOWN`: current model names, availability, and prices. Any example must be treated as illustrative and checked against current official pricing.
- `UNKNOWN`: whether external or official skill libraries cover equivalent functionality; this is not continuously monitored.
- `UNKNOWN`: invocation, installation, hot-reload, and cross-runtime behavior of the four standalone Claude Code skills.
- `UNSUPPORTED`: ContextPort consumer ChatGPT reconstruction writes, browser automation, and unapproved real-export handling, as documented in [`context-port/docs/CAPABILITIES.md`](../context-port/docs/CAPABILITIES.md).
- `UNKNOWN`: line coverage. No coverage instrumentation is configured; no percentage is claimed.

## Reviewer commands

Run these commands from the repository root after cloning:

```bash
python3 scripts/check_repository_integrity.py
python3 -m unittest discover -s context-port/tests -q
python3 -m compileall -q scripts context-port
git diff --check
```

To verify the documented clone path without using the current working tree, run:

```bash
tmpdir="$(mktemp -d)"
git clone "$(pwd)" "$tmpdir/AI-PM-essential-skills"
cd "$tmpdir/AI-PM-essential-skills"
python3 scripts/check_repository_integrity.py
python3 -m unittest discover -s context-port/tests -q
```

The local clone command verifies the repository layout and commands. It does not prove GitHub network availability or external Claude Code behavior.
