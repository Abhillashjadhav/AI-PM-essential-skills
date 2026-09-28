# Reference implementation — supplier catalog grader

A runnable catalog-grading reference used to develop the interview's questions.
It illustrates implementation and failure cases; it does not establish that a
new owner can complete the interview and hand off a buildable contract.
The D4/D2 repairs and remaining scope are recorded in [DIVERGENCES.md](DIVERGENCES.md).

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
| `grader.py` | the current grader, `marketplace-d4-d2-v1` |
| `baseline_v1.py`, `baseline_v2.py` | earlier versions, kept for comparison |
| `contract.md` | the contract it implements |
| `task_prompt.md` | what the candidate model is told |
| `inputs/`, `candidates/`, `gold/` | 30 development cases, 12 fault injections, 3 owner-approved judgments |
| `attacks/` | the five supplied attacks and two alternative probes |
| `revision_checks.json` | 55 checks, each labelled *development expectation derived from owner rules; not independently adjudicated* |
| `DECISIONS.md` | the eight owner-approved business judgments, targets, error ranking |
| `DIVERGENCES.md` | D4/D2 repair evidence, source decisions and remaining scope |
| `OPEN_DECISIONS.md` | remaining workflow scope and evidence/integration limits |

## What it does not establish

The repaired 2026-09-28 replay exits 0: 55/55 revision expectations match,
3/3 approved cases, 12/12 injected faults and 31/31 metadata/payload checks pass.
All 30 saved candidates are accepted. Six additional publication regressions
check withholding, required fields, family comparisons, warning branches and
parent links. CI runs the replay and regressions on every PR.

The two formerly failing D4 fixtures carried an obsolete candidate `withheld`
key. The imported #54 fixtures remove that key under the recorded owner ruling,
keep the expected PASS outcomes, and add both acceptance and rejection controls.

Its two accuracy targets — >98% of published records correct, <0.5% of valid
submissions wrongly blocked — are **not measured, and cannot be** from what is
this suite. Both need a population with independent ground truth. No independent
holdout is packaged here; the 55 revision checks are development expectations.
Later grader PRs contain additional decision and evaluation work requiring
separate integration; this repair does not claim their evidence.

Gate 3 remains open. The plugin version (0.1.0), reference implementation
(marketplace-d4-d2-v1), and contract (v1.5.1) version different artifacts.
