# Evaluation of `frozen-v2.4` against nine independently authored sealed cases

Run date 2026-09-20. Grader `frozen-v2.4`. `grader.py` was **not modified** for
this run, before it or after it.

Nine cases, UCA-01 to UCA-09, `owner_approval: "APPROVED"` on all nine.

---

## 0. Read this before the numbers

**The input format was documented *after* these cases were first rejected.**

In the first round (`EVALUATION_v2.3.md`) all nine cases were rejected before
grading with `SETUP_ERROR: material must be object`. The grader enforced an
input encoding that no contract, prompt or schema file stated. Ruling 1 of
2026-09-20 wrote that rule down — an evidence entry's `value` is the exact
machine value of the field it evidences — and ruling 2 gave the source's own
words a home in an optional, inert `source_note`. **The rule was published in
response to the cases failing against it.** The cases were then reformatted to
match it.

That is a real weakness in this evidence and it is not softened here: the
format the cases are measured against was fixed after seeing them fail.

**What was NOT changed: any expectation.** `expected_verdict`,
`expected_publication` and `expected_seller_guidance` are byte-identical to what
the independent author wrote before any contact with the grader. Verified by
hashing the expectation keys of both rounds:

```
case      expectations    input       candidate
UCA-01    IDENTICAL       identical   identical
UCA-02    IDENTICAL       reformatted identical
UCA-03    IDENTICAL       reformatted identical
UCA-04    IDENTICAL       identical   identical
UCA-05    IDENTICAL       identical   identical
UCA-06    IDENTICAL       identical   identical
UCA-07    IDENTICAL       reformatted identical
UCA-08    IDENTICAL       identical   identical
UCA-09    IDENTICAL       reformatted identical
```

Every candidate is also byte-identical. Only `input` moved, and only on four of
the nine.

**Nine cases remain an initial independent check.** They do not establish the
**>98%** publication-correctness target or the **<0.5%** wrong-rejection
guardrail, and nothing in this document claims otherwise. No single accuracy
number is computed anywhere here.

---

## 1. The result

```
$ python3 run_sealed_cases.py <cases>
Sealed-case run - grader frozen-v2.4

case                                status       exp.vrd  act.vrd      vrd  pub  guid  checked
UCA-01-HAPPY-PATH                   SETUP_ERROR  PASS     SETUP_ERROR  -    -    -     (nothing)
  -> grader rejected the fixture before grading: material must be object - nothing scored
UCA-02-PARENT-CONFLICT-BLOCK        SCORED       PASS     FAIL         NO   yes  -     verdict,pub.sku_ids,pub.withheld_fields,pub.parent_links
  -> not in the published shape, expected_seller_guidance: ... got list
UCA-03-PARENT-CONFLICT-CHILD-LEAK   SCORED       FAIL     FAIL         yes  yes  -     verdict,pub.sku_ids,pub.withheld_fields,pub.parent_links
  -> not in the published shape, expected_seller_guidance: ... got list
UCA-04-PARENTLESS-PRICE-CHILD       SETUP_ERROR  PASS     SETUP_ERROR  -    -    -     (nothing)
  -> grader rejected the fixture before grading: material must be object - nothing scored
UCA-05-OPTIONAL-CONFLICT-WITHHELD   SETUP_ERROR  PASS     SETUP_ERROR  -    -    -     (nothing)
  -> grader rejected the fixture before grading: material must be object - nothing scored
UCA-06-WITHHELD-FIELD-PUBLISHED     SETUP_ERROR  FAIL     SETUP_ERROR  -    -    -     (nothing)
  -> grader rejected the fixture before grading: material must be object - nothing scored
UCA-07-INVENTED-PERCENTAGE          SCORED       FAIL     FAIL         yes  yes  -     verdict,pub.sku_ids,pub.withheld_fields,pub.parent_links
UCA-08-EXPLICIT-US-CURRENCY         SETUP_ERROR  PASS     SETUP_ERROR  -    -    -     (nothing)
  -> grader rejected the fixture before grading: material must be object - nothing scored
UCA-09-SIZE-CHART-AMBIGUOUS         SETUP_ERROR  PASS     SETUP_ERROR  -    -    -     (nothing)
  -> grader rejected the fixture before grading: material must be object - nothing scored

RUNNER EXIT=1
```

### Per case

| Case | exp. verdict | actual | expected publication (`sku_ids`) | actual publication | guidance supplied | `checked` |
|---|---|---|---|---|---|---|
| UCA-01 | PASS | `SETUP_ERROR` | `["KL-RN-CHG-M-001","KL-RN-FGR-M-002"]`, links `{FGR→CHG}` | *not reached* | no | *(nothing)* |
| UCA-02 | PASS | **FAIL** | `[]`, withheld `{}`, links `{}` | `[]`, `{}`, `{}` — **agrees** | yes, list form | `verdict, pub.sku_ids, pub.withheld_fields, pub.parent_links` |
| UCA-03 | FAIL | FAIL | `[]`, withheld `{}`, links `{}` | `[]`, `{}`, `{}` — agrees | yes, list form | `verdict, pub.sku_ids, pub.withheld_fields, pub.parent_links` |
| UCA-04 | PASS | `SETUP_ERROR` | `["AR-CN-WHT-L-031"]`, links `{}` | *not reached* | yes, list form | *(nothing)* |
| UCA-05 | PASS | `SETUP_ERROR` | `["BR-VN-RED-M-041"]`, withheld `{BR-VN-RED-M-041: [recommended_browse_nodes]}` | *not reached* | yes, list form | *(nothing)* |
| UCA-06 | FAIL | `SETUP_ERROR` | `[]`, withheld `{}`, links `{}` | *not reached* | yes, list form | *(nothing)* |
| UCA-07 | FAIL | FAIL | `[]`, withheld `{}`, links `{}` | `[]`, `{}`, `{}` — agrees | no | `verdict, pub.sku_ids, pub.withheld_fields, pub.parent_links` |
| UCA-08 | PASS | `SETUP_ERROR` | `["MT-VN-NAT-M-070"]`, links `{}` | *not reached* | no | *(nothing)* |
| UCA-09 | PASS | `SETUP_ERROR` | `[]`, withheld `{}`, links `{}` | *not reached* | yes, list form | *(nothing)* |

The expected publications for the six unreached cases are printed above so the
scale of what went unmeasured is visible: four of the six expected SKUs to
publish — UCA-01 two SKUs and a parent link, UCA-04, UCA-05 and UCA-08 one each,
with UCA-05 also expecting a withheld field — and none of that was tested.

`checked` names exactly what was compared. A `SETUP_ERROR` returns no
`publication_payload`, so nothing on any axis is comparable for those six.

### The three denominators, kept separate

| Measurement | Denominator | Agreements |
|---|---|---|
| Candidate grading | **3** | **2 / 3** |
| Publication correctness | **3** | **3 / 3** |
| Seller guidance | **0** | 0 / 0 |

Three separate subsets. They are never combined and no single accuracy number is
derived from them.

### Both error directions

| Direction | Count | Cases |
|---|---|---|
| **Incorrect approvals** (expected FAIL, grader returned PASS) | **0** | none |
| **Incorrect rejections** (expected PASS, grader returned FAIL) | **1** | `UCA-02-PARENT-CONFLICT-BLOCK` |

Zero incorrect approvals over a denominator of three is not evidence of a low
false-accept rate. It is three cases.

### Expectation blocks not in the published shape

```
EXPECTATION BLOCKS NOT IN THE PUBLISHED SHAPE: 2
  - UCA-02  expected_seller_guidance: must be an object with "required" and/or "must_not_warn"; got list
  - UCA-03  expected_seller_guidance: must be an object with "required" and/or "must_not_warn"; got list
```

Each costs its own measurement only. UCA-02 and UCA-03 are still scored on
verdict and publication.

---

## 2. Classification of every disagreement

### D1 — `MALFORMED_RECORD` on a well-formed child, where the parent's field is disputed rather than absent — IMPLEMENTATION DEFECT

**Affects UCA-02 and UCA-03. Confirmed. Present in `frozen-v2.4`.**

This is the F3 class, **narrowed by v2.4 but not eliminated.** `supplies()`
correctly reports that a parent declaring a conflict on `material` *has* supplied
it — disputed, not absent — so parent-derived blocking runs and
`PARENT_UNRESOLVED` is correctly expected on the child. But the
`compatible_partial` sub-branch inside `source_ref` needs a settled parent
*value*, and a conflict-only parent has none:

```
File "grader_probe", line 476, in grade
File "grader_probe", line 190, in source_ref
KeyError: 'material'
```

`grader.py:190`:

```python
field=='material' and r['fields'].get(field) and compatible_partial(r['fields'][field],values[parent['sku']][field])
```

with:

```
material in parent values : False
parent declares a conflict: True
supplies(...)             : True
```

`effective()` guards the same comparison correctly — `if cm and pm and
compatible_partial(cm,pm)` — testing the parent value's truthiness before using
it. `source_ref()` does not. The `KeyError` is swallowed by the catch-all at
`grader.py:494` and reported as `MALFORMED_RECORD` against the candidate, whose
record is well formed, and every remaining check on that record is abandoned.

**Not repaired here.** Repair is a separate instruction.

### D2 — a conflicted required field yields two issues, and `ISSUE_COVERAGE` demands both — POLICY AMBIGUITY

**Affects UCA-02 and UCA-03.** Open decision **(i)**, unchanged since
`EVALUATION_v2.3.md`.

UCA-02's parent carries no settled `material` because its two sources disagree.
The grader expects the candidate to report **both**:

```
KL-RN-NVY-M-010  blocking=[('MISSING_REQUIRED','material'), ('SOURCE_CONFLICT','material')]
```

The candidate reports the conflict alone, and the author judged that `PASS`:

```
KL-RN-NVY-M-010  status=BLOCKED  issues=[('SOURCE_CONFLICT','material')]
```

→ `ISSUE_COVERAGE`. Whether the absence is a second defect or a consequence of
the first has two defensible answers and the owner has not chosen one.

**UCA-02 needs both D1 and D2 resolved.** Either error alone produces `FAIL`, so
repairing D1 would not by itself turn UCA-02 into an agreement.

### D3 — six cases still carry `material` evidence as a bare string — INVALID CASE (input encoding only)

**Affects UCA-01, UCA-04, UCA-05, UCA-06, UCA-08, UCA-09.**

This is **not** the grader disagreeing with an expectation. It is an input that
contradicts a rule which is now published, with a worked `material` example, in
`SEALED_CASES.md` and in clause 2a of both contracts:

```
case    sku                  record                        evidence
UCA-01  KL-RN-CHG-M-001      {"label": "cotton blend"}     "cotton blend"
UCA-04  AR-CN-WHT-M-030      {"label": "cotton"}           "cotton"
UCA-05  BR-VN-RED-M-041      {"label": "cotton blend"}     "cotton blend"
UCA-06  HF-TK-OLV-M-050      {"label": "cotton blend"}     "cotton blend"
UCA-08  MT-VN-NAT-M-070      {"label": "cotton"}           "cotton"
UCA-09  CW-CN-SKY-M-080      {"label": "cotton blend"}     "cotton blend"
```

The rule is that the evidence value is the same shape the record carries. These
six supply the label without the object around it.

**Only the input encoding is at fault.** Every expectation in these six is
untouched, still owner-approved, and still measurable: the fix is one value per
case, `"cotton blend"` → `{"label": "cotton blend"}`, changing no expectation.
The builder has not made that edit — editing owner-approved cases is not the
builder's to do, and six of nine remaining unmeasured is the honest result of
this run.

Four of the nine inputs were reformatted (UCA-02, 03, 07, 09); five were
byte-identical to round one. UCA-09's input was reformatted — a `source_note` was
added — but its `material` evidence value was not converted.

### D4 — `expected_seller_guidance` supplied as a list — POLICY AMBIGUITY

**Affects UCA-02, 03, 04, 05, 06, 09.** Open decision **(h)**, unchanged.

The published schema is `{"required": [...], "must_not_warn": [...]}`; the cases
supply `[{sku, field, warning_meaning, supplier_action}]`. The `sku`+`field` part
maps over cleanly; `warning_meaning` and `supplier_action` are prose, and the
schema rule is "meaning, never wording". The runner reports the shape and scores
nothing for that block rather than reinterpreting it. The seller-guidance
denominator is therefore **0** and stays uninformative until (h) is settled.

Open decision **(g)** — which channel guidance is asserted against — is also
still open and would bear on the same denominator.

### Nothing else disagreed

UCA-03 and UCA-07 agree on verdict, and all three scored cases agree on
publication. UCA-07 is the one case measured cleanly end to end: it catches the
invented percentage the case was built to test, with `WRONG_VALUE` and
`DISPLAY_VALUE` on `material`, and publishes nothing, as expected.

UCA-03's agreement is worth one qualification: the verdict is `FAIL` and `FAIL`
was expected, and the grader does catch the intended defect —
`FALSE_READY` on the child, the false accept the case exists to test. But its
error list is contaminated by the D1 `MALFORMED_RECORD` and the D2
`ISSUE_COVERAGE`. The verdict agrees; the reasoning behind it is not entirely
the case author's.

---

## 3. What this run establishes, and what it does not

**Establishes.** One confirmed implementation defect surviving in `frozen-v2.4`
(D1), reproduced with a traceback and a named line. One wrong rejection, with
both of its causes identified. That three cases reached the grader at all is new
— in round one, zero did.

**Does not establish.** Any rate, in either direction. Three cases in the
candidate-grading denominator, three in publication, zero in guidance. The
**>98%** and **<0.5%** targets remain unmeasured and nothing here moves them.
Gate 3 is unaffected and remains **NOT MET**: 60 of 102 fixtures are still
builder-authored and unadjudicated, and running cases against the grader is a
different check from reviewing those expectations.

**And the caveat from section 0 stands over all of it.** The input format these
cases now satisfy was written down after they failed against it. That the
expectations never moved is what keeps the exercise independent; it does not make
the format rule independently arrived at.

---

## 4. Integrity of this run

- `grader.py` was not modified for this run, before it or after it.
- `frozen-v2.3` is intact: `grader.py` at `c31cbd9` is blob
  `06413b289ef53d0d71aa23aaf9a50b9257c01534`.
- No case file was edited by the builder. The cases are not committed to this
  repository.
- One harness change was made and committed separately: a nonconforming
  expectation block now costs its own measurement only, instead of excluding the
  whole case. That change is what surfaced the UCA-02 wrong rejection, which the
  previous behaviour concealed.
- Every number above comes from a command that was run.
