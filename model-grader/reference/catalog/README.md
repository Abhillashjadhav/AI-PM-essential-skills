# Reference implementation — supplier catalog grader

A real, runnable grader, built from answers to this skill's question bank. It is
here as evidence, not as a product: nobody installs a plugin to grade T‑shirts.
What it demonstrates is that answering the 26 questions produces something an
implementer can actually build, and what it costs when a question goes unasked.

Python standard library only. No API keys, no network, no model calls.

```bash
cd reference/catalog
python3 run_checks.py
```

## Why it is worth reading

This grader caught **12 of 12** deliberately injected faults, then missed
**8 of 8** real exploits. Every miss traced to a decision its contract never made —
which is the whole argument for the question bank. The eight, and the questions
that would have caught them:

| What got through | Question that was never asked |
|---|---|
| an invented label contradicting its own numbers | **B1** what may the output add that the source did not |
| one answer passed as the answer to four different cases | **B2** what binds an answer to its request |
| a correct answer rejected over `10.0` vs `10` | **B3** which values compare as numbers, which as text |
| a rule evaded by capitalising one word | **B3** where casing carries meaning |
| supplied metadata silently dropped | **B4** what must be preserved when unused |
| a record inherited from a blocked parent and published | **B5** what makes a source fit to depend on |
| claims parked outside the expected structure | **B6** is the output schema closed or open |
| currency relabelled, amounts intact | **B7** which request values may never change |

It also produced the two questions the bank was missing entirely. An audit of
this grader's 47 consumed inputs and 39 issue codes found three with no question
behind them — operations and record states, authority and resolution, pending
corrections. That is where **A9** and **A10** came from, and why both are marked
found-by-audit rather than reasoned.

## What is here

| Path | What it is |
|---|---|
| `grader.py` | the current reference grader, `frozen-v2.6`; earlier frozen versions remain historical artifacts |
| `baseline_v1.py`, `baseline_v2.py` | earlier versions, kept for comparison |
| `contract.md` | the contract it implements |
| `task_prompt.md` | what the candidate model is told |
| `inputs/`, `candidates/`, `gold/` | 30 saved development cases, 13 fault injections, 3 owner-approved judgments |
| `attacks/` | the five supplied attacks and two alternative probes |
| `revision_checks.json` | 55 development checks; these are not independent adjudications |
| `DECISIONS.md` | the eight owner-approved business judgments, targets, error ranking |
| `DIVERGENCES.md` | two executed divergences between decisions and implementation |
| `OPEN_DECISIONS.md` | unresolved scope decision (b), explicitly deferred defect (k), and remaining evidence work |
| `SEALED_CASES.md`, `run_sealed_cases.py` | published case format and comparison harness; case inputs are supplied separately |
| `EVALUATION_v2.3.md`, `EVALUATION_v2.4.md`, `EVALUATION_v2.6.md` | historical reports of three rounds using nine externally authored cases |

## What it does not establish

Its two accuracy targets — >98% of published records correct, <0.5% of valid
submissions wrongly blocked — are **not measured, and cannot be** from what is
here. Both need a suitable population with independent ground truth. The latest
recorded nine-case run reports raw verdict agreement 8/9, raw publication
agreement 8/9, and guidance agreement 6/6. Two expectations were overruled by
owner rulings; those adjustments are not independent agreements. The input format
was documented after the cases first failed, and inputs were re-encoded. These
limitations remain even though the reports record unchanged expectation hashes.

The case files are not committed here, so the historical run cannot be rerun from
this checkout alone. The development suite is reproducible self-consistency
evidence, not a production accuracy measurement.

Gate 3 is open. That is the honest state, and leaving it visible is the point.

## Frozen for independent evaluation

`grader.py` identifies the current reference artifact as **`frozen-v2.6`**.
Do not modify a frozen grader in place or present an old evaluation as evidence
about a later artifact.

`frozen-v2.2` (commit `a792f76`) is preserved unchanged as the historical record.
`frozen-v2.3` (commit `c31cbd9`) and the later versions are also preserved in
history. The v2.6 report names the later run; it does not alter the v2.3 record.

Any subsequent fix goes into a new version. Editing this one voids the
evaluation: a sealed-case run is only evidence about the artifact it was run
against, and an artifact that moves under the evaluation proves nothing about
either version.

What is frozen: `grader.py`. What is not: the fixtures, the documents, and the
reproductions, which may still gain cases — but a change that alters a verdict
the frozen grader produces is a change to the grader by another route, and belongs
in the next version too.
