---
name: model-complexity-router
description: Use this skill proactively whenever the user hands over any substantial task to execute — not just when they ask about models. Use this skill when a concrete work item is handed over by silently scoring it and emitting one compact line noting the current model, the score, the recommended tier, and the potential savings, without blocking or delaying the task itself. Also fires on direct questions like "which model should I use", "is this an Opus task", "route this to the right model", "am I overpaying for this", "should I use Haiku or Sonnet for this" — those get the full scored breakdown instead of the compact line. Fires once per distinct task, not on every follow-up message within that same task. Do NOT fire on pure knowledge questions, vendor comparisons, hypotheticals with no concrete work item, or repeatedly while a task is still in progress.
---

# Model Complexity Router

Classify a concrete task, recommend the right Claude model tier, and optionally delegate execution to a subagent pinned to that tier.

## Why this exists

The main session's model cannot be programmatically switched — no hook, skill, or API changes it mid-session. What IS possible: (a) a documented recommendation the user acts on via `/model`, or (b) delegation to a subagent whose frontmatter pins a model. This skill does both and says so honestly.

## Step 1 — Detect the trigger mode

Every time the user hands over a substantial task — a concrete thing to build, fix, write, or execute — this fires silently in the background, in parallel with doing the task. It never blocks or delays the response.

Two modes:
- **Direct ask** ("which model should I use", "is this an Opus task", etc.) → full scored breakdown (Step 3a).
- **Task handoff** (any other substantial task, proactively) → silent score, one compact line (Step 3b).

If the user gave no concrete task at all (e.g., "which model is best generally?"), stop and ask for the specific task — never classify hypotheticals. Fire once per distinct task: once a line or block has been shown for a task, do not re-emit on every subsequent message about that same task — only when a new, distinct task is handed over.

## Step 2 — Score against the rubric

Score the task on four dimensions, each 0–2:

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| **Scope** | Single file/artifact, cosmetic | One feature, few files | Multi-file, architecture, cross-system |
| **Reasoning depth** | Mechanical/pattern-match | Some judgment, known patterns | Novel tradeoffs, ambiguity, design decisions |
| **Error cost** | Trivially reversible | Rework hours | Wrong answer compounds (prod, money, public) |
| **Context load** | Fits in one prompt | Needs a few files | Needs large context synthesis |

Total 0–8. Map: **0–2 → Haiku**, **3–5 → Sonnet**, **6–8 → Opus**.

Floor rule: if Error cost = 2, the recommendation can never be Haiku — floor at Sonnet. (Error cost is already in the total; do not bump the tier a second time.)

## Step 3a — Direct ask: full breakdown

```
TASK: <one-line restatement>
SCORES: Scope X | Reasoning X | Error-cost X | Context X → TOTAL X/8
RECOMMENDED: <Haiku 4.5 | Sonnet 4.6 | Opus 4.8>
WHY: <2 sentences: quality need vs cost/latency saved>
COST DELTA: <approx. relative cost vs. defaulting to Opus, e.g. "~90% cheaper on Haiku">
EXECUTE: (a) switch via /model, or (b) I delegate to the <tier>-executor subagent now
```

## Step 3b — Task handoff: one-line header

Emit exactly one line, above or alongside the normal task response — never in place of doing the task:

```
[Model check] Current: <current tier> · Task score: X/8 (<recommended tier>) · Up to Y% cheaper on <tier> · Reply switch / delegate / continue
```

If the recommended tier matches the current tier, state that instead of a savings figure (e.g., "Current: Sonnet · Task score: 4/8 (Sonnet) · Already on the right tier"), and skip the switch/delegate options.

## Step 4 — Delegate if asked

If the user picks (b)/delegate, invoke the matching subagent (`haiku-executor`, `sonnet-executor`, `opus-executor`) via the Task tool with the full task context. Report the subagent's result back verbatim plus a one-line note of which model executed it.

## Limitations (state these when relevant)

- Cannot silently change the main session's model — only recommend or delegate.
- Rubric scores are judgments, not measurements; two reasonable people may score ±1.
- Cost deltas are relative approximations based on published per-MTok pricing, not billing-exact.
- Subagent delegation isolates context: the subagent won't see full conversation history, only what's passed in.
- The compact header is a nudge, not a gate: the task always proceeds on the current model unless the user explicitly switches or delegates.
