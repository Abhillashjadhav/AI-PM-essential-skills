# Codex operating rules

These rules apply throughout this repository. More specific `AGENTS.md` files may add stricter local rules but must not weaken these requirements.

## ContextPort scope

ContextPort lives in `context-port/`. Do not create a separate repository for it. Do not modify existing AI-PM skills while working on ContextPort without explicit human approval.

## Autonomous work

Codex may work autonomously on:

- Reversible code and documentation changes
- Architecture
- Tests
- Synthetic fixtures
- Refactoring
- Linting
- Type checking
- Git commits
- Pushing the current feature branch
- Creating a draft pull request

## Human approval gates

Stop for human approval before:

- Accessing a real Claude or ChatGPT export
- Launching browser automation
- Writing anything into Claude or ChatGPT
- Resolving ambiguous project mappings
- Truncating or summarising conversations
- Adding production dependencies
- Sending private data over the network
- Deleting or overwriting content
- Modifying existing AI-PM skills
- Merging a pull request
- Publishing a release
- Making a material product decision with multiple valid options

When a decision is required, return exactly this structure:

```text
DECISION REQUIRED
Question:
Evidence:
Option A:
Option B:
Recommendation:
Reversibility:
```

## Reliability rules

- Never invent APIs, export fields, browser selectors, or results.
- Label assumptions `VERIFIED`, `INFERRED`, `UNKNOWN`, or `UNSUPPORTED`.
- Never report success based only on an attempted action. Require observable evidence.
- Never silently discard or truncate content.
- Never commit personal conversations, exports, passwords, cookies, or sessions.
- Use synthetic data in committed tests.
- Preserve original project and conversation titles.
- Make reruns idempotent.
- Report everything not copied.
- Allow a maximum of two repair attempts after a failed gate.
- After two failed attempts, return an honest failure report.

## Contribution rules

Every meaningful phase requires one saved prompt, one feature branch, logical commits, tests or evaluation evidence, one draft pull request, and human review before merge.

Use logical commits appropriate to the phase, such as:

1. prompt and specification
2. tests and fixtures
3. implementation
4. evaluation evidence
5. documentation

Never push directly to `main`. Never merge automatically.
