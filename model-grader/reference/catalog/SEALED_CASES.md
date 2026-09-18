# Sealed evaluation cases — format and runner

The ten evaluation cases are authored elsewhere. **No cases live in this
repository**, and the builder has not seen them. This file defines the format so
they can be written without seeing the grader, and run without the author seeing
the fixtures.

## Running them

```bash
python3 run_sealed_cases.py /path/to/cases
python3 run_sealed_cases.py /path/to/cases --json results.json
```

The directory is an argument. Nothing is committed. The runner imports the frozen
grader unmodified, never retries, and never adjusts an expected verdict.

## One case = one JSON file

Any filename ending `.json`. Cases run in filename order; `case01.json` …
`case10.json` keeps that order obvious.

```json
{
  "case_id": "SC-01",
  "expected_verdict": "FAIL",
  "reason": "One line: why this verdict. For the human reading the results.",
  "input": { "...": "the case the system was given" },
  "candidate": { "...": "the output being judged" }
}
```

| Field | Required | Meaning |
|---|---|---|
| `case_id` | yes | Your label. Appears in every report line and in the error lists. |
| `expected_verdict` | yes | `"PASS"` or `"FAIL"` — exactly these, uppercase. Your judgment of the candidate. |
| `reason` | no | One line of rationale. Carried into the output; never used in the comparison. |
| `input` | yes | The case the system was given: sources, evidence, profile, records. |
| `candidate` | yes | The output being judged. |
| `expected_publication` | no | List of SKU ids you expect in the publication payload, e.g. `["P1"]`. Use `[]` for "nothing should publish". **Added after the original format was published** — cases written without it still run, and are reported as `(not specified)` and excluded from the publication denominator rather than counted either way. |

### Two denominators, never merged

Candidate grading and publication correctness are scored separately:

```
CANDIDATE GRADING   denominator = all cases
PUBLICATION         denominator = only cases carrying an expected_publication
```

**A product correctly left unpublished by a candidate that handled it right is an
agreement, not a rejection.** The two error directions are keyed off the
candidate's verdict, never off whether SKUs published. A candidate can correctly
earn `PASS` on a case where nothing publishes.

`PASS` means the candidate handled the case correctly. `FAIL` means it did not.
The verdict is about the candidate's work, not about whether the product should
publish — a candidate that correctly blocks a defective product is a `PASS`.

For the shape of `input` and `candidate`, `gold/S1.json` is a complete worked
example, and `contract.md` defines every field. Writing a case by hand means
copying that shape and changing what the case needs.

## What the runner reports

Per case: expected verdict, actual verdict, agreement.

In aggregate, and **the two error directions are never combined**:

```
INCORRECT APPROVALS : n   [case ids]
   expected FAIL, grader returned PASS
   the grader accepted work that should have been rejected

INCORRECT REJECTIONS: n   [case ids]
   expected PASS, grader returned FAIL
   the grader rejected work that should have been accepted
```

There is deliberately no single accuracy number. The two directions have
different costs and different owners; one figure hides which is happening.

A third line, `OTHER DISAGREEMENTS`, appears only if the grader raises an error
or returns something outside `PASS`/`FAIL`. A crash is reported as a result, not
skipped.

Cases that cannot be loaded — bad JSON, missing a required key, an
`expected_verdict` that is not `PASS` or `FAIL` — are listed by filename with the
reason. They are never silently dropped.

## What ten cases establish

An initial independent check that the grader's verdicts match someone else's
judgment on cases the builder did not author.

**They do not measure the >98% publication-accuracy target or the <0.5%
wrong-rejection target.** Ten cases cannot measure either. Those targets remain
unmeasured, and a clean sealed-case run does not change that.

## Runner smoke test

The runner was proved against six throwaway files the builder invented for that
purpose and then deleted. Executed at `frozen-v2.3`:

```
$ python3 run_sealed_cases.py /tmp/smoke
Sealed-case run - grader frozen-v2.3
case            expected    actual      agreement
SMOKE-01        PASS        PASS        yes
SMOKE-02        FAIL        FAIL        yes
SMOKE-03        FAIL        PASS        NO
SMOKE-04        PASS        FAIL        NO
Total cases        : 4
Agreements         : 2

INCORRECT APPROVALS : 1   ['SMOKE-03']
INCORRECT REJECTIONS: 1   ['SMOKE-04']

CASES THAT COULD NOT BE LOADED: 2
  - case05.json: not valid JSON - Expecting property name enclosed in double quotes...
  - case06.json: missing required key 'expected_verdict'
exit=1
```

**Those six inputs were self-authored and carry no validation weight whatsoever.**
Two of them were deliberately mislabelled — a valid candidate marked `FAIL`, a
broken one marked `PASS` — for the sole purpose of making the two error counters
fire so their wiring could be seen working. They prove the runner reports what it
claims to report. They say nothing about whether the grader is correct, and they
have been deleted.

The grader was byte-identical before and after the run:
`06413b289ef53d0d71aa23aaf9a50b9257c01534`.
