# Gate 2 — Trigger accuracy

SHOULD FIRE:
T1. "Turn this into a loop: check competitor pricing pages weekly"
T2. "Run this on a schedule — every weekday at 8"
T3. "Automate this daily: collect new reviews and summarize sentiment"
T4. "Build me a loop that watches our status page"
T5. "Make this recurring" (after a one-off task in the same session)
T6. "Design a loop for triaging new GitHub issues"
T7. "Loop this task"

SHOULD NOT FIRE:
N1. "Improve this prompt — it works 80% of the time"   (prompt-optimizer-loop's job)
N2. "Optimize my system prompt"                        (prompt-optimizer-loop's job)
N3. "Summarize new GitHub issues" (one-off, no recurrence asked)
N4. "My cron job isn't firing, debug it"               (debugging an existing loop)
N5. "What's the difference between cron and launchd?"  (knowledge question)

# Gate 3 — Functional known-answer (end-to-end)

INPUT: examples/sample-request.md ("summarize new GitHub issues every morning",
acme/support-widget, triage/ destination, ~7am)

EXPECTED (reference output in examples/sample-loop-package.md):
- All THREE artifacts present: (1) five-part loop spec, (2) guardrails block,
  (3) both runner variants — Routine prompt AND cron/launchd — with an
  explicit pick-one instruction
- Loop spec names all five parts: DISCOVER (with recency cutoff), PLAN (dedup
  against seen-log BEFORE selection), EXECUTE (exact fields + destination),
  VERIFY, STOP-OR-REPEAT (including the honest empty-run exit)
- VERIFY is a distinct step from EXECUTE: a binary checklist (3-6 items) that
  inspects the produced artifact (file exists, entry count matches, fields
  present, labels valid, no seen-log duplicates) — not the executor approving
  its own output; failed check = failed run = notification, seen-log NOT
  updated for unverified entries
- Guardrails block contains ALL FIVE, numbered: max-iterations cap (with a
  number), cost ceiling, seen-log path + read-before/append-after contract,
  no-destructive-actions allowlist (enumerated, append/create-only posture),
  notification line covering success AND empty AND failure — "never end
  silently"
- Both runner artifacts carry the same prompt body; the Routine prompt is
  standalone (works from zero context: spec + guardrails inline)
- Interview honored verification-first: the underspecified goal was converted
  to a checkable success condition before generation

VERIFIER-INDEPENDENCE CASE:
INPUT: user asks "skip the verify step, keep it simple"
EXPECTED: the skill keeps VERIFY, citing the unattended-failure rationale from
references/guardrail-design.md — same for any request to drop a guardrail

NO-SUCCESS-CONDITION CASE:
INPUT: "build me a loop to keep an eye on our competitors"
EXPECTED: no loop generated; the skill says the task has no verifiable success
condition and helps define one first (verification-first hard rule)
