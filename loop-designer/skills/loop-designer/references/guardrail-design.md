# Guardrail Design

Why each of the five guardrails is non-negotiable. When a user asks to skip
one, quote the failure it prevents and keep it in the loop.

## 1. Max-iterations cap

**Prevents:** runaway runs. An unattended loop that discovers 400 items
processes 400 items — burning the budget, flooding the destination, and
turning one bad discovery filter into an incident. The cap turns "unbounded"
into "bounded and reported": process N, then stop and say what was left.
Size N from the PLAN step's selection cap, not from optimism.

## 2. Cost/token ceiling per run

**Prevents:** the silent bill. Scheduled runs multiply: a mildly wasteful run
fired daily is 30 wasteful runs a month, and nobody watches a 6:30am job. The
ceiling is stated in the prompt as a budget the model must respect — stop and
report when approached. Note the honest limitation: a prompt-level ceiling
instructs the model; it doesn't meter the account. Pair it with the runner's
own limits where available.

## 3. Seen-log (cross-run dedup in a file)

**Prevents:** amnesia loops. Each scheduled firing starts stateless; without a
persisted seen-log the loop re-surfaces the same items every run — the fastest
way to get an automation muted or deleted by its own owner. Contract: read
before acting (create if missing), skip anything logged, append every newly
processed item after acting. One file, append-only, human-readable (title +
date + id). This is the pattern the production radar loop runs on daily.

## 4. No destructive actions without an explicit allowlist

**Prevents:** unattended damage. A loop that can delete, overwrite, or send
arbitrarily will eventually do so to the wrong thing, at a time nobody is
watching. Default posture: append/create-only. Anything destructive or
outward-facing (delete, overwrite, email to third parties, posting publicly)
must appear on a per-loop explicit allowlist the user approved at design time.
The skill flags any requested destructive action for confirmation rather than
silently including it — an allowlist entry is a decision, not a default.

## 5. Notification on completion or guardrail trip

**Prevents:** silent death. Unattended loops fail unattended: sources move,
auth expires, formats drift. A loop that only speaks on success disappears
without a trace when it breaks. Every run ends with a notification line —
success (with the one-line result), empty run (honest "nothing new"), or
failure/trip (which guardrail, what was preserved). The production pattern
this generalizes from states it plainly — if anything goes wrong, still send
the notification and flag the issue; don't silently fail.

## The interaction that matters

Guardrails 1+2 bound a single run; guardrail 3 bounds across runs; guardrail 4
bounds blast radius; guardrail 5 makes every outcome observable. Remove any
one and the loop has an unobserved failure mode — which, on a schedule, is a
guaranteed eventual failure. That's why the skill refuses to omit any of the
five: the ask to "keep it simple" is really an ask to fail invisibly later.
