# Sealed evaluation cases — schema and runner

Ten cases are authored elsewhere. **No cases live in this repository** and the
builder has not seen them. This file is the published schema; the runner is
aligned to it, so neither side edits after the cases arrive.

Schema per `04_DATA_FORMAT.md`.

## Running them

```bash
python3 run_sealed_cases.py /path/to/cases
python3 run_sealed_cases.py /path/to/cases --json results.json
```

The directory is an argument. Nothing is committed. The grader is imported
unmodified; the runner never retries and never adjusts an expected outcome.

## One case = one JSON object, one file

```json
{
  "case_id": "SC-01",
  "input":     { "...": "the case the system was given" },
  "candidate": { "...": "the output being judged" },

  "expected_verdict": "FAIL",
  "reason": "One line plus the governing clause or decision ID.",

  "expected_publication": {
    "sku_ids":         ["P1"],
    "withheld_fields": { "P1": ["description"] },
    "parent_links":    { "C1": null }
  },

  "expected_seller_guidance": {
    "required": [
      { "sku": "P1", "field": "description",
        "branch": "eligible_for_publication",
        "must_reference_evidence": ["P1.description", "P1.description.spec"] }
    ],
    "must_not_warn": [ { "sku": "C1", "field": "price" } ]
  },

  "owner_approval": "APPROVED",
  "review_status":  "SETTLED"
}
```

| Key | Required | Meaning |
|---|---|---|
| `case_id` | yes | Your label. Appears in every report line and error list. |
| `input` | yes | The case the system was given. |
| `candidate` | yes | The output being judged. |
| `expected_verdict` | yes | `"PASS"` / `"FAIL"` for the candidate's **handling**, or `null` when unsettled. |
| `reason` | yes | One line plus the governing clause or decision ID. |
| `expected_publication` | yes | Structured object (below), or `null` when the contract does not determine it. |
| `expected_seller_guidance` | no | Structured requirement (below). Omit or `null` when not asserted. |
| `owner_approval` | yes | `"APPROVED"` once you approve it; `"PENDING"` until then. |
| `review_status` | yes | `"AMBIGUOUS"` when the expectation is deliberately unset; otherwise `"SETTLED"`. |

`PASS` is about the candidate's work, not about whether SKUs published. **A
candidate that correctly blocks a defective product is a `PASS`.**

### `expected_publication` — an object, compared in three parts

| Part | Meaning | Compared as |
|---|---|---|
| `sku_ids` | SKUs expected in the payload. `[]` means nothing publishes. | whole set |
| `withheld_fields` | `{sku: [fields]}` expected withheld. `{}` means none. | whole map, empties dropped |
| `parent_links` | `{sku: parent_sku-or-null}` in the payload. | **only the SKUs you name** |

**The three are compared separately and reported separately.** Supply only the
parts you want checked — omit one, or set it `null`, and it is not compared and
not counted. `parent_links` is narrowed to the SKUs you name, so a case can
assert one link without restating the whole payload.

Set the whole object to `null` when the contract does not determine publication.

### `expected_seller_guidance` — meaning, never wording

Each `required` entry asserts guidance exists for a named `sku` + `field`, and
optionally that it carries a `branch`, references given evidence ids, or
recommends a given value.

| Field | Checked as |
|---|---|
| `sku`, `field` | a warning exists for that pair |
| `branch` | one of `blocked`, `eligible_for_publication`, `awaiting_approval` |
| `must_reference_evidence` | those evidence ids appear in the warning's conflicting values |
| `recommended_value` | the recommended value matches |

`must_not_warn` asserts **no** guidance for a named `sku` + `field`.

**Wording is never compared.** No string match on prose, ever. Only the required
meaning and the named SKU/field.

## Cases that are not run

| Condition | Treatment |
|---|---|
| `owner_approval` != `"APPROVED"` | **Refused.** Reported as `UNAPPROVED`, never scored. |
| `review_status` == `"AMBIGUOUS"` | **Not executable.** Listed, never guessed. |
| `expected_verdict` is `null` | Verdict not scored. The case may still be scored on publication or guidance. |
| `expected_publication` is `null` | Publication not scored. |
| unparseable / missing a required key | Listed by filename with the reason. Never silently dropped. |

`UNAPPROVED` and `AMBIGUOUS` are **excluded from every denominator.**

## Three measurements, three subsets, three denominators

```
CANDIDATE GRADING    cases with a settled expected_verdict
PUBLICATION          cases with a structured expected_publication
SELLER GUIDANCE      cases carrying expected_seller_guidance
```

A case can be in one, two or all three. **They are never combined into one
number.** There is no accuracy figure anywhere in the output.

The report states per case exactly which expectations were compared, in a
`checked` column. **A verdict agreement says nothing about payload or guidance
correctness** — only the columns marked `yes`/`NO` were checked.

The two error directions are keyed off the candidate's verdict, never off
publication:

```
INCORRECT APPROVALS   expected FAIL, grader returned PASS
INCORRECT REJECTIONS  expected PASS, grader returned FAIL
```

A product correctly left unpublished by a candidate that handled it right is an
**agreement**, not a rejection.

## What ten cases establish

An initial independent check that the grader agrees with someone else's judgment
on cases the builder did not author.

**They do not measure the >98% publication-accuracy target or the <0.5%
wrong-rejection target.** Ten cases cannot measure either. Those remain
unmeasured, and a clean run does not change that.

## Runner branch proof

Every branch was exercised with throwaway inputs the builder invented for that
purpose and then deleted. Executed at `frozen-v2.3`:

```
case      status          exp.vrd  act.vrd  vrd  pub  guid  checked
T-01      SCORED          PASS     PASS     yes  yes  -     verdict,pub.sku_ids,pub.withheld_fields,pub.parent_links
T-02      SCORED          PASS     PASS     yes  NO   -     verdict,pub.sku_ids,pub.withheld_fields,pub.parent_links
            -> sku_ids expected ['P1'] got ['C1', 'P1']
            -> parent_links expected {'C1': None} got {'C1': 'P1'}
T-03      SCORED          FAIL     FAIL     yes  -    -     verdict
T-04      NOT EXECUTABLE  -        -        -    -    -     (nothing)
            -> review_status AMBIGUOUS - expectation deliberately unset
T-05      UNAPPROVED      -        -        -    -    -     (nothing)
            -> owner_approval is 'PENDING', not APPROVED - refused
T-06      SCORED          None     PASS     -    yes  -     pub.sku_ids
T-07      SCORED          PASS     PASS     yes  -    NO    verdict,guid.P1/description
            -> P1/description: no seller guidance emitted
T-08      SCORED          PASS     PASS     yes  -    yes   verdict,guid.!P1/description

CANDIDATE GRADING    denominator 5   agreements 5 / 5
PUBLICATION          denominator 3   agreements 2 / 3
  parts compared     : ['parent_links', 'sku_ids', 'withheld_fields']
SELLER GUIDANCE      denominator 2   agreements 1 / 2

EXCLUDED FROM EVERY DENOMINATOR: 2   (T-05 unapproved, T-04 ambiguous)
CASES THAT COULD NOT BE LOADED: 2   (bad JSON, missing required keys)
```

Both error counters were proved separately, since neither fired above:

```
E-APPROVE SCORED  FAIL PASS  NO   ->  INCORRECT APPROVALS  : 1 ['E-APPROVE']
E-REJECT  SCORED  PASS FAIL  NO   ->  INCORRECT REJECTIONS : 1 ['E-REJECT']
```

**Those inputs were self-authored and carry no validation weight whatsoever.**
Several were deliberately mislabelled — a valid candidate marked `FAIL`, a
correct payload asserted wrong — for the sole purpose of making each branch and
counter fire so the wiring could be seen working. They show the runner reports
what it claims to report. They say nothing about whether the grader is correct,
and they have been deleted.

`grader.py` was byte-identical before and after:
`06413b289ef53d0d71aa23aaf9a50b9257c01534`.
