# Loop Anatomy

The five-part architecture loop-designer generates, and where it comes from.

## Provenance

This anatomy is generalized from a production loop that runs live: a daily
GenAI-radar Routine that scans sources on a recency window, dedups against a
seen-log file, writes a structured dated brief, enforces anti-fabrication
rules, and exits honestly when nothing new shipped. It also borrows the
locked-checklist discipline from this marketplace's `prompt-optimizer-loop`
(pm-tactical): the criteria a loop is judged against are fixed before the run,
not negotiated by the run. Nothing here is invented architecture — every part
earned its place in a loop that actually fires on a schedule.

## The five parts

### 1. DISCOVER — what each run scans

Bound it two ways or it grows without limit:
- **Scope**: the exact sources (named URLs, repos, folders, APIs). "Search the
  web" is not a scope; a prioritized source list is.
- **Recency/novelty cutoff**: a time window ("last 48 hours", "since last run")
  or a state boundary ("issues without the triaged label"). Without a cutoff,
  every run re-discovers the world.

### 2. PLAN — how findings become work items

Two ordered moves:
1. **Dedup first**: read the seen-log; drop anything already processed. Dedup
   before ranking — ranking seen items wastes the budget on discards.
2. **Select/rank**: explicit criteria ("top 3-5 by durability and PM value",
   "all critical-severity, max 10"). The cap here feeds guardrail #1.

### 3. EXECUTE — the action

- Exact output format (named fields, required per item — a schema, not "write
  a summary").
- Exact destination (dated file path pattern like `radar/YYYY-MM-DD.md`, a
  branch naming scheme, an email subject format).
- Content rules inline where the model needs them ("every claim needs a source
  link", "if no real incident exists, say so — do not fabricate one").

### 4. VERIFY — the separate pass

The defining feature of a loop that can run unattended. After EXECUTE, a
distinct checklist pass inspects the artifact:
- Binary checks only: file exists at the expected path; every required field
  present per item; every claim carries a source link; item count within the
  cap; no output item appears in the seen-log.
- The verifier is not the executor: in a single-prompt Routine this is a
  separately-delimited "VERIFY:" checklist the run must walk through against
  the produced artifact before it may report success; in multi-agent setups
  it's a different agent. The executor never gets to say "looks good" about
  its own output in the same breath it produced it — the same separation
  builder-validator (pm-verifier) enforces for one-off artifacts.
- Verify failure = run failure = notification. Not a silent retry, not a ship.

### 5. STOP-OR-REPEAT — exit conditions

Every loop states all of its exits:
- **Work exhausted** — the selected items are processed and verified.
- **Nothing new** — discovery minus seen-log is empty: write the one-line
  honest exit ("No significant items in the last 48 hours") and stop. Padding
  an empty run is a verify failure, not a success.
- **Cap hit** — max iterations or cost ceiling reached: stop, report what was
  done and what was left.
- **Repeat** applies only to in-run iteration (per-item processing); the
  cross-run repeat is the scheduler's job, not the prompt's.

## Why runs are stateless and state lives in files

A scheduled run starts with zero conversation memory. Everything the loop must
remember across runs — what it has seen, counters, the last run date — must be
read from a file at run start and written back before run end. The seen-log is
the minimum viable memory: read before acting, append after acting. A loop
that "remembers" in any other way doesn't remember at all — it re-processes,
re-sends, and re-announces the same items on every firing.
