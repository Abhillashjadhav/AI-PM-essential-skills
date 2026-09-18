# Evaluation of `frozen-v2.3` against nine independently authored sealed cases

Run date 2026-09-18. Grader `frozen-v2.3`, commit
`c31cbd94d169ce2f40dc372c5ce4e67b94f2b95b`, `grader.py` blob
`06413b289ef53d0d71aa23aaf9a50b9257c01534`. The grader was **not modified** for
this run and is byte-identical to the freeze:

```
$ git rev-parse c31cbd9:model-grader/reference/catalog/grader.py
06413b289ef53d0d71aa23aaf9a50b9257c01534
$ git hash-object model-grader/reference/catalog/grader.py
06413b289ef53d0d71aa23aaf9a50b9257c01534
$ git diff c31cbd9 -- model-grader/reference/catalog/grader.py
(no output)
```

Nine cases, UCA-01 to UCA-09. Authored by someone who is not the builder and who
had no sight of the grader; owner-approved before execution
(`owner_approval: "APPROVED"` on all nine). The builder read them only to run
them and changed nothing in any case file. The case files are not committed to
this repository.

---

## 1. The result

**Every one of the nine cases was rejected by the grader before grading began.**
Nothing was scored. All three denominators are zero.

```
$ python3 run_sealed_cases.py <cases>
Sealed-case run - grader frozen-v2.3
case                                status            exp.vrd  act.vrd      vrd  pub  guid  checked
UCA-01-HAPPY-PATH                   SETUP_ERROR       PASS     SETUP_ERROR  -    -    -     (nothing)
                                      -> grader rejected the fixture before grading: material must be object - nothing scored
UCA-02-PARENT-CONFLICT-BLOCK        SETUP_ERROR       PASS     SETUP_ERROR  -    -    -     (nothing)
                                      -> grader rejected the fixture before grading: material must be object - nothing scored
UCA-03-PARENT-CONFLICT-CHILD-LEAK   SETUP_ERROR       FAIL     SETUP_ERROR  -    -    -     (nothing)
                                      -> grader rejected the fixture before grading: material must be object - nothing scored
UCA-04-PARENTLESS-PRICE-CHILD       SETUP_ERROR       PASS     SETUP_ERROR  -    -    -     (nothing)
                                      -> grader rejected the fixture before grading: material must be object - nothing scored
UCA-05-OPTIONAL-CONFLICT-WITHHELD   SETUP_ERROR       PASS     SETUP_ERROR  -    -    -     (nothing)
                                      -> grader rejected the fixture before grading: material must be object - nothing scored
UCA-06-WITHHELD-FIELD-PUBLISHED     SETUP_ERROR       FAIL     SETUP_ERROR  -    -    -     (nothing)
                                      -> grader rejected the fixture before grading: material must be object - nothing scored
UCA-07-INVENTED-PERCENTAGE          SETUP_ERROR       FAIL     SETUP_ERROR  -    -    -     (nothing)
                                      -> grader rejected the fixture before grading: material must be object - nothing scored
UCA-08-EXPLICIT-US-CURRENCY         SETUP_ERROR       PASS     SETUP_ERROR  -    -    -     (nothing)
                                      -> grader rejected the fixture before grading: material must be object - nothing scored
UCA-09-SIZE-CHART-AMBIGUOUS         SETUP_ERROR       PASS     SETUP_ERROR  -    -    -     (nothing)
                                      -> grader rejected the fixture before grading: material must be object - nothing scored

CANDIDATE GRADING    denominator 0 case(s) with a settled expected_verdict
  agreements         : 0 / 0
PUBLICATION          denominator 0 case(s) with a structured expected_publication
  agreements         : 0 / 0
SELLER GUIDANCE      denominator 0 case(s) carrying expected_seller_guidance
  agreements         : 0 / 0

INCORRECT APPROVALS  : 0   none
INCORRECT REJECTIONS : 0   none

EXCLUDED FROM EVERY DENOMINATOR: 9
RUNNER EXIT=1
```

### Per case

| Case | Expected verdict | Actual | What was checked | Scored? |
|---|---|---|---|---|
| UCA-01-HAPPY-PATH | PASS | SETUP_ERROR | *(nothing)* | no |
| UCA-02-PARENT-CONFLICT-BLOCK | PASS | SETUP_ERROR | *(nothing)* | no |
| UCA-03-PARENT-CONFLICT-CHILD-LEAK | FAIL | SETUP_ERROR | *(nothing)* | no |
| UCA-04-PARENTLESS-PRICE-CHILD | PASS | SETUP_ERROR | *(nothing)* | no |
| UCA-05-OPTIONAL-CONFLICT-WITHHELD | PASS | SETUP_ERROR | *(nothing)* | no |
| UCA-06-WITHHELD-FIELD-PUBLISHED | FAIL | SETUP_ERROR | *(nothing)* | no |
| UCA-07-INVENTED-PERCENTAGE | FAIL | SETUP_ERROR | *(nothing)* | no |
| UCA-08-EXPLICIT-US-CURRENCY | PASS | SETUP_ERROR | *(nothing)* | no |
| UCA-09-SIZE-CHART-AMBIGUOUS | PASS | SETUP_ERROR | *(nothing)* | no |

`checked` is empty for every row. A `SETUP_ERROR` returns no
`publication_payload`, so there is nothing to compare on any of the three axes.

### The three denominators, kept separate

| Measurement | Denominator | Agreements |
|---|---|---|
| Candidate grading | **0** | 0 / 0 |
| Publication correctness | **0** | 0 / 0 |
| Seller guidance | **0** | 0 / 0 |

### Both error directions

| Direction | Count | Cases |
|---|---|---|
| **Incorrect approvals** (expected FAIL, grader returned PASS) | **0** | none |
| **Incorrect rejections** (expected PASS, grader returned FAIL) | **0** | none |

Both zeros mean *not measured*, not *no errors*. Nothing reached the verdict
stage. No single accuracy number is computed here, and the three denominators are
never combined.

---

## 2. Classification of every disagreement

Seven distinct disagreements. **No case is classified INVALID.** For each, the
question asked was: does the case contradict a rule that is actually written
down? Where the rule exists only in the grader's code and in the shape of the
builder's own fixtures, the case is not invalid — the specification is
incomplete.

### F1 — material evidence values are source prose, not material objects — POLICY AMBIGUITY

**Affects all nine cases. This is the blocker that produced the result above.**

The cases supply `material` evidence values as strings describing what a source
document says:

```
"KL-RN-NVY-M-010.material.a": { ... "value": "60% cotton / 40% polyester (spec sheet A)" }
"BR-VN-RED-M-041.material":   { ... "value": "cotton blend" }
```

`grader.py` requires a material evidence value to be an object:

```python
def material_key(m):
    if not isinstance(m,dict): raise ValueError('material must be object')
```

called from setup validation:

```python
if e['field']=='material': material_key(e['value'])
```

Every fixture shipped in this repository uses the object form
(`{"label": "cotton blend"}` or `{"components": [...]}`).

**Why this is not INVALID CASE.** The convention is real and uniformly followed
by the builder's own fixtures, but it is written nowhere. Searched for a clause
fixing the shape of an input evidence value:

```
$ grep -rn "evidence" contract.md contract_v1.4.md task_prompt.md task_prompt_v1.md \
    | grep -i "value\|shape\|object\|string\|format"
```

Eighteen lines match. Every one of them is about either the *candidate's output*
evidence references or grading policy. `task_prompt.md:17` — "evidence maps every
output field to the source evidence ID" — is the output map, not the input value.
`contract.md:57` says a case "supplies product facts, evidence of
identity/family relationships" and stops there. Nothing in any contract or prompt
version, and nothing in `SEALED_CASES.md`, states what an **input** evidence
`value` must look like for any field. `SEALED_CASES.md` specifies the case wrapper — `case_id`, `input`,
`candidate`, `expected_*` — and treats `input` as opaque.

The authors' model is coherent and arguably the better one: `evidence` is what a
source says, in the source's own words, with its provenance ("spec sheet A");
`fields` is the structured value derived from it. The grader's model is that the
two are the same object. Neither is written down, so the case cannot be faulted
against the specification.

**Needs an owner decision, recorded as (e) in `OPEN_DECISIONS.md`.**

### F2 — an evidence value must equal the record field value byte-for-byte — POLICY AMBIGUITY

**Affects UCA-02, UCA-03, UCA-07.** Same missing specification, different clause.
Setup validation requires:

```python
for f,v in r['fields'].items():
    e=evidence.get(f'{sku}.{f}')
    if not e or e!={'sku':sku,'field':f,'value':v}: raise SetupError('fixture evidence mismatch')
```

So an input can never carry a source's own wording for a field it also states
structurally. UCA-07 states `fields.material` as components and the evidence as
`"60% cotton, polyester (percentage not supplied)"` — which is exactly the thing
the case exists to test, and exactly what this rule forbids.

This surfaced only once F1 was lifted; see the diagnosis in section 4.
**Same owner decision, (e).**

### F3 — `MALFORMED_RECORD` blamed on a well-formed candidate record — IMPLEMENTATION DEFECT

**Confirmed. Reproduced from a fixture shipped in this repository, with no UCA
case involved.**

`source_ref()` reads the parent's effective value without checking it exists:

```python
if (field in r.get('inherit_fields',[]) and field not in r['fields']) or (
    field=='material' and r['fields'].get(field) and compatible_partial(r['fields'][field],values[parent['sku']][field])):
```

When a child carries a `material` and its flagship parent has none,
`values[parent['sku']]['material']` raises `KeyError`. The catch-all at
`grader.py:494` converts it into an error against the **candidate**:

```python
except (KeyError,TypeError,ValueError,InvalidOperation,AttributeError) as e: err('MALFORMED_RECORD',sku,detail=str(e))
```

Reproduction, taking shipped `inputs/D01.json` and removing only the parent's
material:

```
$ python3 -c "... del P1.fields['material']; evidence.pop('P1.material'); grade(...)"
verdict: FAIL
errors : [
 {"code": "FALSE_READY",      "sku": "P1", "detail": "Expected BLOCKED"},
 {"code": "ISSUE_COVERAGE",   "sku": "P1", "detail": ""},
 {"code": "FALSE_READY",      "sku": "C1", "detail": "Expected BLOCKED"},
 {"code": "MALFORMED_RECORD", "sku": "C1", "detail": "'material'"}
]
```

Traced by re-raising instead of swallowing (in memory; `grader.py` untouched):

```
File "grader_probe", line 435, in grade
File "grader_probe", line 163, in source_ref
KeyError: 'material'
```

`C1`'s record is well formed. The fault is a grader lookup on absent parent data,
reported as a defect in the candidate's output.

**Why it matters beyond the wrong label.** `MALFORMED_RECORD` is raised from the
catch-all wrapping the whole per-record block, so every remaining check on that
record is abandoned. A real defect on that record is never examined. It can
therefore hide errors in **both** directions.

**Why the shipped suite never caught it.** Every parent/child fixture in
`inputs/` gives the parent a material:

```
inputs/D01.json [('P1','parent',True), ('C1','child',True)]
... all 20 identical in this respect
```

The independent authors reached the shape on their second and third cases.

**Not repaired here.** `frozen-v2.3` is preserved unchanged, as instructed.

### F4 — is `expected_publication.withheld_fields` scoped to what published? — POLICY AMBIGUITY

**Affects UCA-06.** The case expects `sku_ids: []` and `withheld_fields: {}` — the
SKU fails and does not publish, so on the author's reading there is no published
field to withhold. The grader returns:

```
withheld: {"HF-TK-OLV-M-050": ["recommended_browse_nodes"]}
```

`result['withheld']` is a global analysis map built for every record regardless of
publication; the payload separately just omits withheld fields from published
records. `SEALED_CASES.md` says only "`{sku: [fields]}` expected withheld. `{}`
means none" and does not say whether an unpublished SKU contributes.

The key sits inside `expected_publication`, which favours the author's reading.
The runner's choice to compare against `result['withheld']` rather than a
payload-scoped map is a builder decision made when aligning the harness, and is
part of what needs settling. **Recorded as (f).**

### F5 — seller guidance exists, in the other channel — EVALUATION-HARNESS DEFECT, not a grader gap

**Affects UCA-02, UCA-03, UCA-04, UCA-09.** Under the diagnosis run these four
report `no seller guidance emitted`. That conclusion is wrong, and the harness
produced it.

`seller_warnings()` iterates only the *withholding* partition — optional-field
conflicts, per Decision 4. Blocking issues are carried by `guided_help()`
instead. `compare_guidance()` looks at `seller_warnings` only. Measured:

```
case                                sku/field                                 seller_warnings  guided_help
UCA-02-PARENT-CONFLICT-BLOCK        KL-RN-NVY-M-010/material                  NO               yes
UCA-02-PARENT-CONFLICT-BLOCK        KL-RN-NVY-S-011/material                  NO               yes
UCA-03-PARENT-CONFLICT-CHILD-LEAK   SW-PL-BLK-L-020/material                  NO               yes
UCA-03-PARENT-CONFLICT-CHILD-LEAK   SW-PL-BLK-XL-021/material                 NO               yes
UCA-04-PARENTLESS-PRICE-CHILD       AR-CN-WHT-M-030/price                     NO               yes
UCA-05-OPTIONAL-CONFLICT-WITHHELD   BR-VN-RED-M-041/recommended_browse_nodes  yes              yes
UCA-06-WITHHELD-FIELD-PUBLISHED     HF-TK-OLV-M-050/recommended_browse_nodes  yes              yes
UCA-09-SIZE-CHART-AMBIGUOUS         CW-CN-SKY-M-080/measurement:m1            NO               yes

asserted sku+field pairs: 8
  present in seller_warnings only-channel reading : 2/8
  present in guided_help                          : 8/8
  present in EITHER channel                       : 8/8
```

Every pair the authors asserted is covered, including UCA-09's
`measurement:m1`. `SEALED_CASES.md` never names a channel, and the harness was
not changed to look at both, because which channel `expected_seller_guidance`
asserts against is not the builder's to decide. **Recorded as (g).**

### F6 — `expected_seller_guidance` block shape — POLICY AMBIGUITY

**Affects UCA-02, 03, 04, 05, 06, 09.** The published schema is
`{"required": [{sku, field, branch?, must_reference_evidence?, recommended_value?}],
"must_not_warn": [...]}`. The cases supply a list:

```json
[{ "sku": "...", "field": "recommended_browse_nodes",
   "warning_meaning": "Two supplied sources give different ...",
   "supplier_action": "Approve one of the cited sources, ..." }]
```

The `sku` + `field` part maps directly onto a `required` entry. `warning_meaning`
and `supplier_action` are prose, and the published rule is "meaning, never
wording" — so under the current schema they could not be compared even if the
block were reshaped. The runner does not reinterpret the block; it reports
`CASE_SCHEMA_ERROR` and scores nothing. **Recorded as (h).**

### F7 — one conflicted required field yields two issues — POLICY AMBIGUITY

**Affects UCA-02.** Where a required field's sources disagree and no settled value
is therefore carried, the grader expects the candidate to report **both**
`MISSING_REQUIRED` and `SOURCE_CONFLICT`, and `ISSUE_COVERAGE` (expected ⊆
actual) fails if either is absent. UCA-02's candidate reports the conflict alone
and its author judged that a PASS.

Reproduced on a shipped fixture, no UCA case involved — `inputs/D01.json` with
the parent's material replaced by two conflicting sources:

```
P1 blocking: [('MISSING_REQUIRED', 'material'), ('SOURCE_CONFLICT', 'material')]
C1 blocking: [('MISSING_REQUIRED', 'material')]
```

Whether the absence is a second defect or a consequence of the first is a policy
question with two defensible answers. **Recorded as (i).**

### Cases 5 and 6 and `recommended_browse_nodes`

Checked first, before drawing any conclusion, exactly as instructed: does the
grader handle that field at all?

**It does, and identically to `description`.** There is no per-field list
anywhere in the grader; optionality is computed:

```python
def withholds(issue,p):
    return issue['code']=='SOURCE_CONFLICT' and issue['field'] not in required_fields(p)
```

`REQUIRED` is a nine-field tuple; anything outside it, plus `subbrand` when
inapplicable, is optional. Empirically, running UCA-05 with the field renamed:

```
IDENTICAL modulo the field name: True
```

Same verdict, same `withheld` map, same seller warning with the same branch and
the same conflicting values, same published field list. **Nothing observed in
UCA-05 or UCA-06 is attributable to the choice of field.**

### Nothing classified INVALID CASE

No case was found to contradict a written rule. F1, F2, F4, F6 and F7 are places
where the specification does not say what the grader enforces; F3 is a grader
defect; F5 is a defect in this harness. Where the evidence did not decide the
question, that is stated rather than resolved by defaulting against the authors.

---

## 3. What this run does and does not establish

It establishes that **`frozen-v2.3` cannot read cases written by someone who has
not seen its fixtures.** That is a real and serious finding about the system as a
whole: an input format enforced by code and by example, but never written down,
is not a format anyone else can hit.

It establishes **nothing** about grading accuracy in either direction. All three
denominators are zero.

---

## 4. Diagnosis — NOT A RESULT

Everything in this section rests on **builder edits to owner-approved cases** and
is therefore not evidence of grader correctness. It exists to answer one
question: once the first blocker is lifted, is there a second one behind it?
Three normalisations were applied cumulatively, one per layer, and the run
repeated. The case files themselves were never modified; copies were.

| Layer | Normalisation applied | Edits | Outcome |
|---|---|---|---|
| 0 | none — as authored | 0 | 9 SETUP_ERROR. **This is the result in section 1.** |
| 1 | material evidence value `"x"` → `{"label": "x"}` | 15 | 2 scored, 3 SETUP_ERROR (`fixture evidence mismatch`), 4 CASE_SCHEMA_ERROR |
| 2 | + guidance list → `{"required": [{sku, field}]}` | 23 | 6 scored, 3 SETUP_ERROR |
| 3 | + evidence value := the record's field value | 26 | 9 scored |

At layer 3 the runner reports, **under builder reinterpretation**:

```
CANDIDATE GRADING    denominator 9    agreements 8 / 9
PUBLICATION          denominator 9    agreements 8 / 9
SELLER GUIDANCE      denominator 6    agreements 2 / 6
INCORRECT APPROVALS  : 0   none
INCORRECT REJECTIONS : 1   ['UCA-02-PARENT-CONFLICT-BLOCK']
```

The one incorrect rejection is UCA-02, caused by F3 and F7 together. The
publication miss is UCA-06 (F4). Four of the six guidance misses are F5, the
harness looking at one channel — under a both-channel reading that figure is
6/6.

**These numbers are not the evaluation.** They measure a grader against cases the
builder rewrote to fit it. They are recorded so the defects behind the blocker
are visible, not to claim a score. The evaluation result is section 1: zero, zero
and zero.

---

## 5. Instructions honoured

- `grader.py` unchanged and byte-identical to `c31cbd9`; no amend, no rebase, no
  force-push. F3 is reported as a finding, not repaired.
- No case file was edited. Diagnosis operated on copies outside the repository.
  No case is committed here.
- Every number above comes from a command that was run, shown with its output.
- Three denominators kept separate. No single accuracy number is computed
  anywhere in this document.
- Where a question needed an owner decision, it went to `OPEN_DECISIONS.md`
  rather than being decided here.
