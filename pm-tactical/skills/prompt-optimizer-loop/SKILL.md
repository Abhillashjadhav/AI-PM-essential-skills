---
name: prompt-optimizer-loop
description: Use this skill when the user wants to improve, tune, or optimize an existing prompt or system instruction — phrasings like "improve this prompt", "my prompt works 80% of the time", "optimize my system prompt", "make this prompt more reliable", "tune this instruction". Runs an interactive optimization loop, one mutation per round, scored against a locked binary checklist, keeping only changes that improve the score. Requires three inputs from the user — the target prompt, 2-3 realistic test inputs, and 3-6 binary quality checks (offer to help draft checks if missing). Do NOT use for writing a brand-new prompt from scratch, or for one-off output fixes where the prompt itself isn't the problem.
---

# Prompt Optimizer Loop

Improve a prompt the way engineers improve code: one change at a time, measured against a locked test, keep winners, revert losers. Interactive — the user approves each round.

## Step 0 — Collect the three inputs

1. TARGET: the prompt to improve (verbatim).
2. TEST INPUTS: 2-3 realistic inputs that would hit this prompt in production. If the user has none, help draft them, then confirm.
3. CHECKLIST: 3-6 binary yes/no quality checks (e.g., "output is valid JSON", "response under 100 words", "never invents a source"). If missing, draft candidates from the user's complaints and get approval. Once approved, the checklist is LOCKED — it cannot change during the loop. Changing it starts a new loop.

## Step 1 — Baseline

Run the TARGET prompt against every test input. Score each output against every checklist item. Record the baseline as passes/total (e.g., 9/15 across 3 inputs × 5 checks).

## Step 2 — One mutation

Identify the checklist item failing most often. Propose exactly ONE change to the prompt targeting that failure (add a constraint, reorder, add an example, tighten wording). State the hypothesis: "Adding X should fix check Y because Z." Never bundle multiple changes — attribution dies.

## Step 3 — Re-test

Run the mutated prompt against ALL test inputs (not just the failing one). Score against the full locked checklist.

## Step 4 — Keep or revert

- Score improved AND no previously-passing check broke → KEEP. New version becomes current.
- Score flat or worse, or a regression appeared → REVERT to the previous version. Log why the hypothesis failed.

Show the scoreboard after every round:

```
ROUND N | mutation: <one line> | hypothesis: <one line>
SCORE: X/Y (was X/Y) | regressions: none|<list> | verdict: KEEP|REVERT
```

## Step 5 — Stop conditions

Stop when any of: all checks pass on all inputs; 2 consecutive reverts (diminishing returns); user says stop; 8 rounds reached. Then output: final prompt (clean copy), original prompt (untouched), full round-by-round changelog.

## Limitations

- 2-3 test inputs is a small sample; a prompt passing here can still fail on unseen production inputs. Recommend expanding the test set over time via failure capture.
- Scoring is model-judged against binary checks — objective checks (format, length) are reliable; subjective ones ("is it persuasive") are softer. Prefer objective checks.
- This is an in-session interactive loop, not an overnight autonomous run; expect 5-15 minutes for a full loop.
