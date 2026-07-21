# Validation evidence

This document records what this repository's checks establish and what they do not establish. Portfolio claims use five levels:

- `STRUCTURAL`: deterministic inspection establishes that declared files, manifests, paths, links, or fields exist.
- `VERIFIED`: a committed, repeatable check establishes the stated behavior on its declared inputs.
- `RECORDED`: a public record describes an observation, but an intentionally private input or output prevents independent reproduction from the checkout.
- `UNKNOWN`: available evidence does not establish the claim.
- `UNSUPPORTED`: the product intentionally does not perform the behavior.

## Automatically checked

`VERIFIED` by [`scripts/check_repository_integrity.py`](../scripts/check_repository_integrity.py):

- the four public skill directories exist: `token-cost-estimator`, `eval-rubric-generator`, `context-auditor`, and `concise-rewriter`;
- each of those directories contains `SKILL.md`;
- the marketplace declares four plugin directories, each source stays inside the repository, and each contains a parseable, name-matching plugin manifest;
- each local Markdown link in every repository Markdown document resolves to an existing file or directory, and local Markdown anchors resolve to a heading;
- every fixture path mentioned in a README exists; and
- the ContextPort quick-start entry points and synthetic validation fixture exist.

`VERIFIED` by ContextPort's Python unit-test suite: deterministic local behavior exercised by [`context-port/tests/`](../context-port/tests/) against committed synthetic fixtures in [`context-port/fixtures/`](../context-port/fixtures/). These tests do not call a hosted model, inspect real exports, access an account, or perform destination writes.

## Manually validated material

The Markdown fixture documents under [`tests/`](../tests/) and product example directories provide reviewer prompts, known-answer cases, and expected outputs. They are **manual review material**, not automated behavioural tests: no repository command executes the four standalone Claude Code skills against those documents.

ContextPort's evaluation notes under [`context-port/evals/`](../context-port/evals/) record expected deterministic gates and synthetic-fixture observations. Review them with the corresponding command output; do not treat the documents alone as a passing automated run.

## Recorded behavioural model evidence

No recorded external-model behavioural runs are present for the four standalone skills. The repository therefore makes no evidence-backed claim about their live invocation, output quality, token counting accuracy, pricing accuracy, or interoperability with other Claude Code runtimes.

ContextPort's deterministic evidence is local and synthetic. Its [release-readiness report](../context-port/reports/RELEASE_READINESS.md) is revision-bound and predates the converter merged in PR #24. It distinguishes completed automated checks from `UNKNOWN` and `UNSUPPORTED` capabilities at its audited revision; it is not evidence of a consumer ChatGPT reconstruction write.

## Recorded real-export observation

Merged [PR #24](https://github.com/Abhillashjadhav/AI-PM-essential-skills/pull/24) publicly records one approved local run of the generic Claude export converter. The PR reports:

- 43 source projects preserved, plus one generated `Unmapped Conversations` project;
- 1,434 conversations preserved;
- 36,264 messages preserved;
- 7,538 attachment records preserved;
- one design chat and one memory container preserved;
- zero reported losses; and
- deterministic repeated conversion.

These aggregates are public-safe because the merged PR already discloses them without names, content, paths, or hashes. The private export and generated migration package remain outside the repository. The observation is therefore `RECORDED`, not independently reproducible `VERIFIED` evidence. Committed synthetic tests verify the converter's count invariants, exact embedded source snapshot, zero-loss decision, and byte-identical repeated writes. They do not reproduce the private counts, prove compatibility with every Claude export shape, copy attachment payloads into a destination, or perform an assistant write.

## Unverified and unsupported behavior

- `UNKNOWN`: general compatibility with Claude or ChatGPT export shapes beyond the one recorded Claude observation.
- `UNKNOWN`: current model names, availability, and prices. Any example must be treated as illustrative and checked against current official pricing.
- `UNKNOWN`: whether external or official skill libraries cover equivalent functionality; this is not continuously monitored.
- `UNKNOWN`: invocation, installation, hot-reload, and cross-runtime behavior of the four standalone Claude Code skills.
- `UNSUPPORTED`: ContextPort consumer ChatGPT reconstruction writes and browser automation, as documented in [`context-port/docs/CAPABILITIES.md`](../context-port/docs/CAPABILITIES.md). Future real-export access remains approval-gated rather than generally supported.
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
