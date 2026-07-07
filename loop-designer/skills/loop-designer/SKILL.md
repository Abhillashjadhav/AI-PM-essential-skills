---
name: loop-designer
description: Use this skill when the user says turn this into a loop, run this on a schedule, automate this daily, build me a loop, make this recurring, design a loop for a task, or loop this task — any request to convert a one-off task into a recurring or autonomous job. Interviews minimally (goal, sources/inputs, output destination, schedule), then generates a complete loop package — a five-part loop spec (Discover, Plan, Execute, Verify with a separate verifier checklist, Stop-or-Repeat), a non-negotiable guardrails block (max-iterations cap, cost/token ceiling, seen-log cross-run dedup, no-destructive-actions allowlist, completion and guardrail-trip notification), and two ready-to-paste artifacts — a Claude Code Routine prompt for cloud scheduled runs and a local cron/launchd variant. Do NOT use for improving an existing prompt ("improve this prompt" is prompt-optimizer-loop's job), for one-off tasks with no recurrence, or for debugging an already-built loop.
---

# Loop Designer

Turn a one-off task into a guarded autonomous loop: five explicit parts, five non-negotiable guardrails, two ready-to-paste artifacts. The architecture is generalized from a production daily-radar loop that has run live — see `references/loop-anatomy.md` for the anatomy and its provenance, `references/guardrail-design.md` for why each guardrail exists.

## Step 0 — Verification first

Before designing anything, ask: **what does a successful run look like, checkably?** If the user's task has no verifiable success condition ("keep an eye on things", "make it better over time"), stop and help define one — a file that exists with required fields, a count within bounds, a claim with a source link. No verifiable condition, no loop: an unverifiable loop is an unattended failure generator.

## Step 1 — Minimal interview

Ask only what the request didn't already say (one message, not a questionnaire):
1. **Goal** — the checkable success condition from Step 0.
2. **Sources/inputs** — what each run scans or consumes (URLs, repos, folders, APIs).
3. **Output destination** — where results land (file path pattern, branch, email, issue).
4. **Schedule** — cron-style cadence, or event-driven.

## Step 2 — Generate the loop spec (five parts, all explicit)

```
LOOP SPEC: <name>
DISCOVER  — what each run scans, with recency/scope cutoffs stated
PLAN      — how findings are filtered and decomposed: dedup against the seen-log
            FIRST, then select/rank what survives (selection criteria explicit)
EXECUTE   — the action, with exact output format and destination
VERIFY    — a separate verifier checklist (3-6 binary checks) run AFTER execute;
            the run only counts as successful if every check passes
STOP-OR-REPEAT — exit conditions: work exhausted, nothing new found (say so
            honestly — an empty run writes "nothing new", never padding),
            iteration cap hit, or ceiling hit
```

Rules for VERIFY:
- The verifier is a **distinct step with its own checklist** — never the executor grading its own output in the same breath. In a Routine, VERIFY is a separately-delimited checklist pass over the produced artifact; in a multi-agent setup, a separate agent.
- Checks must be binary and artifact-inspectable (file exists, fields present, every claim has a source link, item count within bounds, no seen-log duplicates in output).
- A failed check = failed run, reported as such — never silently shipped.

## Step 3 — Guardrails block (all five, always)

Every generated loop includes this block verbatim-adapted — no omissions, no matter how simple the task:

```
GUARDRAILS (non-negotiable)
1. MAX ITERATIONS: <N> items/actions per run; stop and report when hit.
2. COST CEILING: <token/time budget> per run; stop and report when hit.
3. SEEN-LOG: each run starts stateless — cross-run memory lives in <path>
   (create if missing; read before acting; append after acting). Never
   re-process a logged item.
4. NO DESTRUCTIVE ACTIONS: never delete, overwrite, or send beyond this
   explicit allowlist: <allowlist>. Everything else is append/create-only.
5. NOTIFY: on completion AND on any guardrail trip or verify failure, emit
   the notification line to <channel>. Never fail silently.
```

## Step 4 — Emit both artifacts, user picks one

**(a) Claude Code Routine prompt** — a complete, standalone prompt for a scheduled cloud run (each firing starts from zero context, so the prompt carries everything: the five-part spec inline, the guardrails block, the seen-log path, the output destination). Ready to register with a cron expression.

**(b) Local cron/launchd variant** — a shell one-liner invoking `claude -p "<the same prompt>"` plus the crontab line (and the launchd plist snippet if the user is on macOS). Same prompt body — the runner is the only difference.

Label both clearly and tell the user to pick one; running both double-processes the seen-log.

## Hard rules

- **Never generate a loop without all five guardrails.** A request to skip one gets the reason it exists (from `references/guardrail-design.md`) and a loop that still includes it.
- **Never let the executor verify its own work.** VERIFY is a separate checklist pass over the artifact, never a "looks good to me" from the same prompt flow that produced it.
- **Verification first.** No verifiable success condition → help define one before generating; never emit a loop whose success can't be checked from its artifacts.
- **State lives in files.** Each scheduled run starts stateless; anything the loop must remember (seen items, counters, last-run date) is read from and written to files, never assumed from memory.
- **Honest empty runs.** A run that finds nothing new says so in one line and exits — padding an empty run is a verify failure.

## Limitations

- Generated loops are only as safe as their allowlist; the skill defaults to append/create-only and flags any user-requested destructive action for explicit confirmation rather than silently including it.
- Cost ceilings are stated as budgets in the prompt; scheduled runners don't hard-enforce token caps — the ceiling instructs the model to stop, it doesn't meter the account.
- The Routine artifact targets Claude Code scheduled runs; other schedulers (GitHub Actions, Airflow) need adaptation the skill will do on request but doesn't emit by default.
- A loop spec is a design, not a deployment: the skill doesn't register the Routine or install the crontab — it hands over paste-ready artifacts and exact registration steps.
