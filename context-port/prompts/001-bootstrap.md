# Task title

ContextPort bootstrap: specification, contribution workflow, and permanent Codex rules

## Original task prompt

```text
Work inside the current repository:

Abhillashjadhav/AI-PM-essential-skills

Current branch:

context-port/001-bootstrap

Run this task autonomously. Do not ask about routine implementation choices.

GOAL

Establish the specification, contribution workflow and permanent Codex rules
for ContextPort.

ContextPort must live inside:

context-port/

Do not create another repository.
Do not build the actual migration tool in this phase.
Do not modify any existing AI-PM skill.

INPUT VISIBILITY

Before doing other work, save this complete task prompt in:

context-port/prompts/001-bootstrap.md

Include:

- Task title
- Original task prompt
- Date
- Branch
- Status
- Proposed PR title
- Decisions requested
- Decisions received

CREATE

1. AGENTS.md at the repository root
2. context-port/BUILD_SPEC.md
3. context-port/docs/CONTRIBUTION_WORKFLOW.md
4. context-port/prompts/001-bootstrap.md
5. context-port/decisions/.gitkeep
6. context-port/evals/.gitkeep
7. context-port/reports/.gitkeep
8. .github/pull_request_template.md

AGENTS.MD AUTONOMY RULES

Work autonomously on:

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

When a decision is required, return:

DECISION REQUIRED
Question:
Evidence:
Option A:
Option B:
Recommendation:
Reversibility:

RELIABILITY RULES

- Never invent APIs, export fields, browser selectors or results.
- Label assumptions VERIFIED, INFERRED, UNKNOWN or UNSUPPORTED.
- Never report success based only on an attempted action.
- Never silently discard or truncate content.
- Never commit personal conversations, exports, passwords, cookies or sessions.
- Use synthetic data in committed tests.
- Preserve original project and conversation titles.
- Make reruns idempotent.
- Report everything not copied.
- Allow a maximum of two repair attempts after a failed gate.
- After two failed attempts, return an honest failure report.

CONTRIBUTION WORKFLOW

Every meaningful phase requires:

- One saved prompt
- One branch
- Logical commits
- Tests or evaluation evidence
- One draft pull request
- Human review before merge

Use logical commits such as:

1. prompt and specification
2. tests and fixtures
3. implementation
4. evaluation evidence
5. documentation

Never push directly to main.
Never merge automatically.

PULL REQUEST TEMPLATE

Create these sections:

## Input
## Prompt
## Scope
## Decisions
## Assumptions
## Evidence
## Tests
## Evaluation
## Privacy
## Limitations
## Not completed
## Human approval

BUILD SPECIFICATION

Document:

- Claude export inspection and parsing
- ContextPack neutral format
- Project and conversation segregation
- Human-in-the-loop sample confirmation
- ChatGPT reconstruction
- Independent reconciliation reviewer
- Incremental Claude-to-ChatGPT and ChatGPT-to-Claude syncing
- Privacy and threat model
- Installation
- Truthful demonstration evidence
- Known unsupported behaviours
- Planned PR sequence

GIT AND PR

Create logical commits.

Push the current branch.

Create a draft pull request titled:

chore(context-port): establish build specification and contribution workflow

Do not merge the pull request.

If GitHub CLI is unavailable:

- Do not install it automatically.
- Push the branch.
- Return the GitHub comparison URL required to create the draft PR manually.

FINAL RESPONSE

Return:

- Files created
- Commits created
- Checks run
- Draft PR link or comparison link
- VERIFIED assumptions
- INFERRED assumptions
- UNKNOWN items
- Risks
- Confirmation that existing AI-PM skills were untouched
```

## Date

2026-07-11

## Branch

`context-port/001-bootstrap`

## Status

Specification and workflow complete; publication pending.

## Proposed PR title

`chore(context-port): establish build specification and contribution workflow`

## Decisions requested

None.

## Decisions received

- Run autonomously without asking about routine implementation choices.
- Keep ContextPort in this repository under `context-port/`.
- Do not implement the migration tool in this phase.
- Do not modify existing AI-PM skills.
- Push the current feature branch and create, but do not merge, a draft pull request.
