---
name: model-complexity-router
description: Use this skill when the user asks which Claude model to use for a task, wants to reduce model spend, mentions burning expensive tokens on simple work, or asks to route/delegate a task to the right model tier. Triggers on phrasings like "which model should I use", "is this an Opus task", "route this to the right model", "am I overpaying for this", "should I use Haiku or Sonnet for this". Classifies the task against a documented complexity rubric, recommends Opus/Sonnet/Haiku with cost-latency-quality reasoning, and offers delegation to a model-pinned subagent so the work executes on the recommended tier. Do NOT use for general "which LLM is best" comparisons across vendors or for tasks with no concrete work item attached.
---

# Model Complexity Router

Classify a concrete task, recommend the right Claude model tier, and optionally delegate execution to a subagent pinned to that tier.

## Why this exists

The main session's model cannot be programmatically switched — no hook, skill, or API changes it mid-session. What IS possible: (a) a documented recommendation the user acts on via `/model`, or (b) delegation to a subagent whose frontmatter pins a model. This skill does both and says so honestly.

## Step 1 — Extract the task

Identify the single concrete work item. If the user gave no concrete task (e.g., "which model is best generally?"), stop and ask for the specific task. Never classify hypotheticals.

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

## Step 3 — Output the recommendation

Always output this exact block:

```
TASK: <one-line restatement>
SCORES: Scope X | Reasoning X | Error-cost X | Context X → TOTAL X/8
RECOMMENDED: <Haiku 4.5 | Sonnet 4.6 | Opus 4.8>
WHY: <2 sentences: quality need vs cost/latency saved>
COST DELTA: <approx. relative cost vs. defaulting to Opus, e.g. "~90% cheaper on Haiku">
EXECUTE: (a) switch via /model, or (b) I delegate to the <tier>-executor subagent now
```

## Step 4 — Delegate if asked

If the user picks (b), invoke the matching subagent (`haiku-executor`, `sonnet-executor`, `opus-executor`) via the Task tool with the full task context. Report the subagent's result back verbatim plus a one-line note of which model executed it.

## Limitations (state these when relevant)

- Cannot silently change the main session's model — only recommend or delegate.
- Rubric scores are judgments, not measurements; two reasonable people may score ±1.
- Cost deltas are relative approximations based on published per-MTok pricing, not billing-exact.
- Subagent delegation isolates context: the subagent won't see full conversation history, only what's passed in.
