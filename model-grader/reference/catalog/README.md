# Reference implementation — supplier catalog grader

A runnable catalog-grading reference used to develop the interview's questions.
It illustrates implementation and failure cases; it does not establish that a
new owner can complete the interview and hand off a buildable contract.
The reference still has the D4/D2 gaps in [DIVERGENCES.md](DIVERGENCES.md).

Python standard library only. No API keys, no network, no model calls.

```bash
cd model-grader/reference/catalog
python3 run_checks.py
```

## Why it is worth reading

The recorded exercise includes five wrong acceptances (`ASTRA_A1` through
`ASTRA_A5`) and two wrong rejections (`FR1`, `FR2`). They motivate B1, B3,
B4, B5 and B7; B3 covers both directions. B2 and B6 are reasoning-led questions
without shipped attack fixtures on this branch. B8 was preventive.

The [plugin README](../../README.md) maps the recorded probes to questions.
These are development findings from one domain, not an independent benchmark.

It also produced the two questions the bank was missing entirely. An audit of
this grader's 45 extracted inputs and 43 issue codes found three with no question
behind them — operations and record states, authority and resolution, pending
corrections. That is where **A9** and **A10** came from, and why both are marked
found-by-audit rather than reasoned.

## What is here

| Path | What it is |
|---|---|
| `grader.py` | the current grader, `revised-v2.1` |
| `baseline_v1.py`, `baseline_v2.py` | earlier versions, kept for comparison |
| `contract.md` | the contract it implements |
| `task_prompt.md` | what the candidate model is told |
| `inputs/`, `candidates/`, `gold/` | 30 development cases, 12 fault injections, 3 owner-approved judgments |
| `attacks/` | the five supplied attacks and two alternative probes |
| `revision_checks.json` | 52 checks, each labelled *development expectation derived from owner rules; not independently adjudicated* |
| `DECISIONS.md` | the eight owner-approved business judgments, targets, error ranking |
| `DIVERGENCES.md` | two executed divergences between decisions and implementation |
| `OPEN_DECISIONS.md` | three questions the owner has not settled, and two unbuilt evidence sets |

## What it does not establish

The 2026-09-28 replay exits 1: 50/52 revision expectations match. The two
failures concern D4's optional-field withholding. Approved cases (3/3),
injected faults (12/12), metadata checks (25/25), and saved-candidate replay
(30/30 accepted) do not cancel those failures or resolve D2.

Its two accuracy targets — >98% of published records correct, <0.5% of valid
submissions wrongly blocked — are **not measured, and cannot be** from what is
here. Both need a population with independent ground truth. There is none: zero
sealed cases, and every one of the 52 checks was written by the same builder that
wrote the grader.

Gate 3 remains open. The plugin version (0.1.0), reference implementation
(revised-v2.1), and contract (v1.5.1) version different artifacts.
