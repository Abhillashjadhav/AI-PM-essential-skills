# Sealed evaluation cases — schema and runner

Nine cases, UCA-01 to UCA-09, are authored elsewhere. **No cases live in this
repository** and the builder had not seen them before running them. There is no
tenth case; its absence is not missing data. This file is the published schema;
the runner is aligned to it, so neither side edits after the cases arrive.

Schema per `04_DATA_FORMAT.md`.

## Running them

```bash
python3 run_sealed_cases.py /path/to/cases
python3 run_sealed_cases.py /path/to/cases --json results.json
```

The directory is an argument. Nothing is committed. The grader is imported
unmodified; the runner never retries and never adjusts an expected outcome.

## `input.evidence` — values are machine values, not prose

**This is the rule that rejected all nine cases in the first round, and it was
written nowhere. It is written here now.**

An evidence entry is `{sku, field, value}` plus an optional `source_note`. Its
`value` is the **exact machine value of the field it evidences — the same shape
the record carries**. The grader compares `evidence["P1.material"].value` to
`records[P1].fields.material` directly. A different shape is a mismatched
fixture, and the case is rejected before grading with `SETUP_ERROR`.

### Worked example — a scalar field

```json
"records": [ { "sku": "P1", "fields": { "color": "Navy", "price": "649.00" } } ],
"evidence": {
  "P1.color": { "sku": "P1", "field": "color", "value": "Navy"   },
  "P1.price": { "sku": "P1", "field": "price", "value": "649.00" }
}
```

The evidence `value` is the same `"Navy"` the record carries. Not `"navy per
the colour card"`, not `"Navy (spec sheet A)"`.

### Worked example — `material`

`material` is an object, so its evidence value is that whole object.

```json
"records": [ { "sku": "P1", "fields": {
  "material": { "components": [ { "material": "cotton",    "percent": "60" },
                                { "material": "polyester", "percent": "40" } ] } } } ],
"evidence": {
  "P1.material": { "sku": "P1", "field": "material",
    "value": { "components": [ { "material": "cotton",    "percent": "60" },
                               { "material": "polyester", "percent": "40" } ] } }
}
```

A bare string is refused:

```
"value": "60% cotton / 40% polyester"            SETUP_ERROR: material must be object
"value": "60% cotton / 40% polyester (spec A)"   SETUP_ERROR: material must be object
```

The simple form `{"label": "cotton blend"}` is equally valid where that is what
the record carries. What must match is the record.

### Where the source's own words go — `source_note`

A human description of where the value came from is an optional `source_note` on
the entry. Use it for exactly the text that used to get written into `value`:

```json
"P1.material.a": { "sku": "P1", "field": "material",
  "value": { "components": [ { "material": "cotton",    "percent": "60" },
                             { "material": "polyester", "percent": "40" } ] },
  "source_note": "spec sheet A, page 4" },
"P1.material.b": { "sku": "P1", "field": "material",
  "value": { "components": [ { "material": "cotton",    "percent": "80" },
                             { "material": "polyester", "percent": "20" } ] },
  "source_note": "supplier invoice, 12 Aug" }
```

**`source_note` is never compared and never decides anything.** It is quoted
back in supplier guidance, so a conflict reads

> On material, spec sheet A, page 4 says {...} and supplier invoice, 12 Aug says {...}.

instead of naming internal evidence ids. A case with notes and the same case
without produce an identical verdict, an identical error list and an identical
publication payload — only the guidance wording differs. Proved by
`reproductions/ruling2_source_note_inert.py`.

Attribution is all-or-nothing per conflict: name every cited source or none, so
no sentence names one source and silently drops the other.

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
| `parent_links` | parent links in the payload. **See the table below — `null` and `{}` mean different things.** | depends |
| `parent_links_exhaustive` | optional flag, default `false`. | see below |

**The three are compared separately and reported separately.** Supply only the
parts you want checked — omit one, or set it `null`, and it is not compared and
not counted.

Set the whole object to `null` when the contract does not determine publication.

#### `parent_links` — `null` and `{}` are not the same

This is the pair an author will get wrong, so it is spelled out.

| Value | Meaning | Denominator |
|---|---|---|
| `null` | **Not asserted.** The comparison is skipped. | **excluded** |
| `{}` | **Asserted: no published SKU carries a parent link.** | included |
| `{"C1": "P1"}` | Asserted for the named SKUs only. Says nothing about others. | included |
| `{"C1": null}` | Asserted: C1 publishes with **no** parent link. | included |

`null` checks nothing. `{}` is a real assertion and can fail.

An author writing `{}` to mean "no links" must not get a silent pass. **A check
that cannot fail is worse than no check**, and this is exactly adjudication 2's
territory — a valid child publishing independently with no parent link.

#### `parent_links_exhaustive`

Optional, default `false` when absent. Only meaningful alongside a non-empty map.

| | Behaviour |
|---|---|
| absent / `false` | Only the SKUs named in the map are compared. A link on an unnamed SKU is ignored. |
| `true` | The map is the complete set. **Any SKU carrying a parent link that the map does not name is a mismatch.** |

`{}` is already exhaustive by meaning, so the flag adds nothing there.

**`parent_links: null` together with `parent_links_exhaustive` is a malformed
case.** The flag is meaningless without a map, and the runner refuses to pick an
interpretation: the case is reported `MALFORMED` and excluded from every
denominator.

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

#### Two accepted shapes — a plain list, or the object

Owner ruling 2026-09-20: **a plain list is valid.** A list *is* the `required`
list written without the wrapper, which is the shape an author reaches for when
every entry simply asserts that guidance exists.

```json
"expected_seller_guidance": [
  { "sku": "P1", "field": "description" },
  { "sku": "C1", "field": "recommended_browse_nodes", "branch": "eligible_for_publication" }
]
```

is compared exactly as

```json
"expected_seller_guidance": {
  "required": [
    { "sku": "P1", "field": "description" },
    { "sku": "C1", "field": "recommended_browse_nodes", "branch": "eligible_for_publication" }
  ]
}
```

Use the object form when you need `must_not_warn` — a bare list cannot express
it.

#### Prose keys are reported, not silently dropped

An entry may carry extra keys describing what the warning should mean, for
example `warning_meaning` or `supplier_action`. They are **not compared** —
"meaning, never wording" still holds — but they are **named in the report** so
the guidance denominator never implies coverage it does not have:

```
-> not compared (prose, never matched by wording): P1/description: supplier_action
-> not compared (prose, never matched by wording): P1/description: warning_meaning
```

The keys that *are* compared are `sku`, `field`, `branch`,
`must_reference_evidence` and `recommended_value`. Everything else is prose.

## Cases that are not run

| Condition | Treatment |
|---|---|
| `owner_approval` != `"APPROVED"` | **Refused.** Reported as `UNAPPROVED`, never scored. |
| `parent_links` `null` **and** `parent_links_exhaustive` supplied | **Malformed.** Reported as `MALFORMED`, no interpretation picked. |
| `review_status` == `"AMBIGUOUS"` | **Not executable.** Listed, never guessed. |
| `expected_verdict` is `null` | Verdict not scored. The case may still be scored on publication or guidance. |
| `expected_publication` is `null` | Publication not scored. |
| unparseable / missing a required key | Listed by filename with the reason. Never silently dropped. |

`UNAPPROVED`, `AMBIGUOUS` and `MALFORMED` are **excluded from every denominator.**

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

## What nine cases establish

An initial independent check that the grader agrees with someone else's judgment
on cases the builder did not author.

**They do not measure the >98% publication-accuracy target or the <0.5%
wrong-rejection target.** Nine cases cannot measure either. Those remain
unmeasured, and a clean run does not change that.

The nine cases have been run. See `EVALUATION_v2.3.md`: all nine were rejected
before grading, and all three denominators are zero.

## Runner branch proof

Every branch was exercised with throwaway inputs the builder invented for that
purpose and then deleted. Executed at `frozen-v2.3`.

### Schema branches

```
case      status          exp.vrd  act.vrd  vrd  pub  guid  checked
T-01      SCORED          PASS     PASS     yes  yes  -     verdict,pub.sku_ids,pub.withheld_fields,pub.parent_links
T-02      SCORED          PASS     PASS     yes  NO   -     verdict,pub.sku_ids,pub.withheld_fields,pub.parent_links
T-03      SCORED          FAIL     FAIL     yes  -    -     verdict
T-04      NOT EXECUTABLE  -        -        -    -    -     (nothing)   review_status AMBIGUOUS
T-05      UNAPPROVED      -        -        -    -    -     (nothing)   owner_approval 'PENDING'
T-06      SCORED          None     PASS     -    yes  -     pub.sku_ids
T-07      SCORED          PASS     PASS     yes  -    NO    verdict,guid.P1/description
T-08      SCORED          PASS     PASS     yes  -    yes   verdict,guid.!P1/description
c09/c10   load errors: bad JSON; missing required keys
```

Both error counters, proved separately since neither fired above:

```
E-APPROVE  FAIL/PASS  ->  INCORRECT APPROVALS  : 1 ['E-APPROVE']
E-REJECT   PASS/FAIL  ->  INCORRECT REJECTIONS : 1 ['E-REJECT']
```

### `parent_links` branches

`PL-1` uses a payload with no parent links at all — the parent blocked on a
required-field conflict, the child publishing alone. That is adjudication 2's
scenario, and the case `{}` exists to check.

```
case      status          exp.vrd  act.vrd  vrd  pub  guid  checked
PL-1      SCORED          PASS     PASS     yes  yes  -     verdict,pub.parent_links
PL-2      SCORED          PASS     PASS     yes  NO   -     verdict,pub.parent_links
            -> parent_links {} asserts no published SKU carries a parent link, but {'C1': 'P1'} does
PL-3      SCORED          PASS     PASS     yes  yes  -     verdict,pub.parent_links
PL-4      SCORED          PASS     PASS     yes  NO   -     verdict,pub.parent_links
            -> parent_links_exhaustive: {'C1': 'P1'} carries a parent link and is not named in the map
PL-5      SCORED          PASS     PASS     yes  NO   -     verdict,pub.parent_links
            -> parent_links expected {'C1': None} got {'C1': 'P1'}
PL-6      SCORED          PASS     PASS     yes  yes  -     verdict,pub.sku_ids
PL-7      MALFORMED       -        -        -    -    -     (nothing)
            -> parent_links is null but parent_links_exhaustive is supplied - the flag is
               meaningless without a map; not interpreting it
PL-8      SCORED          PASS     PASS     yes  yes  -     verdict,pub.parent_links

CANDIDATE GRADING    denominator 7   agreements 7 / 7
PUBLICATION          denominator 7   agreements 4 / 7
  parts compared     : ['parent_links', 'sku_ids']
EXCLUDED FROM EVERY DENOMINATOR: 1   (PL-7 malformed)
```

| Case | Branch | Result |
|---|---|---|
| PL-1 | `{}` with no links in the payload | passes |
| PL-2 | `{}` with `C1 -> P1` present | **fails** — the silent pass is closed |
| PL-3 | map names `P1` only, flag absent, `C1` linked | passes, `C1` ignored |
| PL-4 | same map, flag `true` | **fails** — unnamed link caught |
| PL-5 | `{"C1": null}` but `C1` publishes linked | **fails** |
| PL-6 | `parent_links: null` | skipped — `checked` shows `pub.sku_ids` only |
| PL-7 | `null` + `parent_links_exhaustive` | `MALFORMED`, excluded |
| PL-8 | `{"C1": "P1"}` correct | passes |

`PL-6`'s machine record confirms the exclusion rather than only the display:
`checked ['verdict', 'pub.sku_ids'] | parts ['sku_ids']` — `parent_links` absent.

**All of these inputs were self-authored and carry no validation weight
whatsoever.** Several were deliberately mislabelled or given deliberately wrong
expectations, for the sole purpose of making each branch and counter fire so the
wiring could be seen working. They show the runner reports what it claims to
report. They say nothing about whether the grader is correct, and they have been
deleted.

`grader.py` was byte-identical before and after:
`06413b289ef53d0d71aa23aaf9a50b9257c01534`.
