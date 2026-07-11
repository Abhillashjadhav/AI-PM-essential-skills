# ContextPort contribution workflow

## Phase contract

Every meaningful phase requires:

1. One complete task prompt saved under `context-port/prompts/` before other phase work.
2. One feature branch dedicated to that phase.
3. Logical commits containing only the intended scope.
4. Tests or evaluation evidence proportionate to the change.
5. One draft pull request using the repository template.
6. Human review and explicit approval before merge.

Never push directly to `main`. Never merge automatically.

## Before implementation

- Record the task title, original prompt, date, branch, status, proposed PR title, decisions requested, and decisions received.
- Inspect repository status and preserve unrelated changes.
- State phase scope, exclusions, acceptance gates, and privacy classification.
- Use synthetic fixtures unless a human has explicitly approved access to real data.
- Record material decisions in `context-port/decisions/` without including private content.

## Decision gates

Routine reversible implementation choices are autonomous. Stop for every approval gate in the root `AGENTS.md`, including real-export access, browser automation, destination writes, ambiguous mappings, content reduction, production dependencies, private network transmission, destructive behavior, changes to existing AI-PM skills, merge, release, or material product choices.

Use this response structure:

```text
DECISION REQUIRED
Question:
Evidence:
Option A:
Option B:
Recommendation:
Reversibility:
```

Record the response in both the saved prompt's decision section and an appropriate decision artifact when it affects architecture or product behavior.

## Commit structure

Keep commits reviewable and logically ordered. A phase may use only the categories it needs:

1. `prompt and specification`
2. `tests and fixtures`
3. `implementation`
4. `evaluation evidence`
5. `documentation`

Stage explicit paths when the worktree contains unrelated changes. Never commit real conversations, exports, credentials, cookies, sessions, or other private data.

## Checks and repair budget

- Run the most relevant lint, type, test, schema, privacy, and documentation checks available.
- Capture completed commands, exit status, and pertinent evidence.
- Do not equate an attempted operation with success.
- After a gate fails, make at most two repair attempts.
- If the gate still fails, stop and provide an honest failure report with observed evidence, attempts, remaining risk, and all incomplete work.

Evaluation reports belong in `context-port/evals/`; other generated or reviewed evidence belongs in `context-port/reports/`. Reports must label assumptions and list everything not copied or verified.

## Draft pull request

- Push only the current feature branch.
- Open one draft PR; never mark it ready, merge it, or publish a release without approval.
- Complete every PR-template section. Use `None` only when supported by evidence.
- Link the saved prompt, decisions, tests, evaluations, and reports.
- Separate verified results from inferred assumptions, unknowns, and unsupported behavior.
- Keep the PR draft until human review is complete.

If GitHub CLI is unavailable, do not install it automatically. Push the branch and provide the repository comparison URL so a human can create the draft PR manually.

## Completion report

Report files changed, commits, checks, PR or comparison link, verified and inferred assumptions, unknowns, risks, limitations, and items not completed. Explicitly confirm whether existing AI-PM skills were untouched.
