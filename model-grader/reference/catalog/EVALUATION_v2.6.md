# Evaluation of `frozen-v2.6` against nine independently authored sealed cases

Run date 2026-09-20. Grader `frozen-v2.6`. `grader.py` was **not modified** for
this run, before it or after it. Nine cases, UCA-01 to UCA-09,
`owner_approval: "APPROVED"` on all nine.

---

## 0. Read this before the numbers

**The input format was documented after these cases first failed against it, and
the cases were re-encoded to match it.**

In the first round every case was rejected before grading with
`SETUP_ERROR: material must be object` — a rule the grader enforced and no
document stated. Ruling 1 wrote it down; ruling 2 gave the source's own words a
home in `source_note`. The format these cases now satisfy was therefore fixed
*after* seeing them fail, and that weakens this evidence. It is not softened
here.

**No expectation was ever changed.** `expected_verdict`, `expected_publication`,
`expected_seller_guidance`, `reason` and `candidate` are byte-identical to what
the independent author wrote before any contact with the grader. Verified by
hashing each key independently across all three encodings:

```
$ python3 <hash every immutable key across r1 / r2 / r3>
rounds available: ['r1', 'r2', 'r3']

case      key                         r1    r2    r3    verdict
(only differing rows are printed above)

EVERY IMMUTABLE KEY IDENTICAL ACROSS ALL ROUNDS: True

what changed, per case:
  UCA-01    input re-encoded 1x      UCA-06    input re-encoded 1x
  UCA-02    input re-encoded 1x      UCA-07    input re-encoded 1x
  UCA-03    input re-encoded 1x      UCA-08    input re-encoded 1x
  UCA-04    input re-encoded 1x      UCA-09    input re-encoded 2x
  UCA-05    input re-encoded 1x
```

Eight inputs took two distinct encodings across the three rounds and UCA-09 took
three. Nothing else moved, on any case.

**Nine cases do not establish the >98% publication-correctness target or the
<0.5% wrong-rejection guardrail.** No single accuracy number is computed
anywhere in this document, and the three denominators are never combined.

---

## 1. Exclusions, first

**No case was excluded from any denominator. All nine reached the grader.**

| Measurement | Denominator | Excluded | Why |
|---|---|---|---|
| Candidate grading | **9 of 9** | **0** | — |
| Publication correctness | **9 of 9** | **0** | — |
| Seller guidance | **6 of 9** | **3** | UCA-01, UCA-07 and UCA-08 supply no `expected_seller_guidance` at all. Nothing was asserted, so nothing is measured. |

The three guidance non-entries are cases that assert no guidance, not cases the
harness dropped. Every case that asserts something had that thing compared.

This is the difference from the previous run, where six cases were excluded by
`SETUP_ERROR` and four of those expected SKUs to publish.

---

## 2. The result

```
$ python3 run_sealed_cases.py <cases>
Sealed-case run - grader frozen-v2.6

case                                status  exp.vrd  act.vrd  vrd  pub  guid
UCA-01-HAPPY-PATH                   SCORED  PASS     PASS     yes  yes  -
UCA-02-PARENT-CONFLICT-BLOCK        SCORED  PASS     FAIL     NO   yes  NO
UCA-03-PARENT-CONFLICT-CHILD-LEAK   SCORED  FAIL     FAIL     yes  yes  NO
UCA-04-PARENTLESS-PRICE-CHILD       SCORED  PASS     PASS     yes  yes  NO
UCA-05-OPTIONAL-CONFLICT-WITHHELD   SCORED  PASS     PASS     yes  yes  yes
UCA-06-WITHHELD-FIELD-PUBLISHED     SCORED  FAIL     FAIL     yes  NO   yes
UCA-07-INVENTED-PERCENTAGE          SCORED  FAIL     FAIL     yes  yes  -
UCA-08-EXPLICIT-US-CURRENCY         SCORED  PASS     PASS     yes  yes  -
UCA-09-SIZE-CHART-AMBIGUOUS         SCORED  PASS     PASS     yes  yes  NO

RUNNER EXIT=1
```

### Per case

| Case | exp → act verdict | expected publication | actual publication | guidance asserted | result | `checked` |
|---|---|---|---|---|---|---|
| UCA-01 | PASS → PASS | `["KL-RN-CHG-M-001","KL-RN-FGR-M-002"]`, withheld `{}`, links `{FGR→CHG}` | same — **agrees** | none | — | `verdict, pub.sku_ids, pub.withheld_fields, pub.parent_links` |
| UCA-02 | **PASS → FAIL** | `[]`, `{}`, `{}` | same — agrees | 2 pairs | **NO** | + `guid.KL-RN-NVY-M-010/material`, `guid.KL-RN-NVY-S-011/material` |
| UCA-03 | FAIL → FAIL | `[]`, `{}`, `{}` | same — agrees | 2 pairs | **NO** | + `guid.SW-PL-BLK-L-020/material`, `guid.SW-PL-BLK-XL-021/material` |
| UCA-04 | PASS → PASS | `["AR-CN-WHT-L-031"]`, `{}`, `{}` | same — agrees | 1 pair | **NO** | + `guid.AR-CN-WHT-M-030/price` |
| UCA-05 | PASS → PASS | `["BR-VN-RED-M-041"]`, withheld `{BR…: [recommended_browse_nodes]}` | same — agrees | 1 pair | **yes** | + `guid.BR-VN-RED-M-041/recommended_browse_nodes` |
| UCA-06 | FAIL → FAIL | `[]`, **withheld `{}`**, `{}` | `[]`, **`{HF…: [recommended_browse_nodes]}`** — **NO** | 1 pair | yes | `verdict, pub.sku_ids, pub.withheld_fields, pub.parent_links, guid.HF-TK-OLV-M-050/recommended_browse_nodes` |
| UCA-07 | FAIL → FAIL | `[]`, `{}`, `{}` | same — agrees | none | — | `verdict, pub.sku_ids, pub.withheld_fields, pub.parent_links` |
| UCA-08 | PASS → PASS | `["MT-VN-NAT-M-070"]`, `{}`, `{}` | same — agrees | none | — | `verdict, pub.sku_ids, pub.withheld_fields, pub.parent_links` |
| UCA-09 | PASS → PASS | `[]`, `{}`, `{}` | same — agrees | 1 pair | **NO** | + `guid.CW-CN-SKY-M-080/measurement:m1` |

On every case that asserted publication, all three parts — `sku_ids`,
`withheld_fields`, `parent_links` — were compared. Prose keys on guidance
entries (`warning_meaning`, `supplier_action`) are reported as **not compared**
on every entry that carries them; wording is never matched.

### The three denominators, kept separate

| Measurement | Denominator | Agreements | Excluded |
|---|---|---|---|
| Candidate grading | **9** | **8 / 9** | 0 |
| Publication correctness | **9** | **8 / 9** | 0 |
| Seller guidance | **6** | **2 / 6** | 3 (assert no guidance) |

### Both error directions

The runner tallies UCA-02 as an incorrect rejection because it compares the
case's `expected_verdict` and nothing else:

```
INCORRECT APPROVALS  : 0   none
INCORRECT REJECTIONS : 1   ['UCA-02-PARENT-CONFLICT-BLOCK']
```

Applying the D2 ruling, which overrules that expectation (§3.1):

| Direction | Count | Cases |
|---|---|---|
| **Incorrect approvals** (expected FAIL, got PASS) | **0** | none |
| **Incorrect rejections** (expected PASS, got FAIL) | **0** | none — UCA-02 excluded as an overruled expectation |

Both the raw tally and the adjusted count are shown so the adjustment is
visible rather than absorbed. **Zero incorrect approvals over a denominator of
nine is not evidence of a low false-accept rate.** It is nine cases.

---

## 3. Classification of every disagreement

Four disagreements across three cases.

### 3.1 UCA-02, verdict — OVERRULED EXPECTATION (not a defect, not counted)

Expected `PASS`, got `FAIL`. Two independent errors, **both substantively
correct**:

```
{"code": "ISSUE_COVERAGE",   "sku": "KL-RN-NVY-M-010"}
{"code": "MALFORMED_RECORD", "sku": "KL-RN-NVY-S-011",
 "detail": "composition text outside declared grammar"}
```

**(a) `ISSUE_COVERAGE` — the overruled expectation.** The parent's material is
disputed, so it trips two problems; the candidate reports one:

```
parent expected blocking: [('MISSING_REQUIRED','material'), ('SOURCE_CONFLICT','material')]
parent candidate issues : [('SOURCE_CONFLICT','material')]
```

The owner ruling of 2026-09-20 — "a record reports every blocking problem
present on it, not the first one found... when both are true of the same record,
both are reported" — makes this candidate incomplete and `ISSUE_COVERAGE`
correct. The case's `expected_verdict: "PASS"` is overruled by ruling, the case
is **not** edited, and this is **not** counted as an incorrect rejection.

**(b) A second, independent cause that is not the overruled expectation.** The
candidate's child display text is genuinely outside the declared grammar:

```
child candidate display text: "60% cotton, 40% polyester (pending family resolution)"
text_parts raises: ValueError - composition text outside declared grammar
```

This alone forces `FAIL`. So UCA-02 would not have passed even if D2 had gone
the other way. It is reported under open decision **(k)**: the error is
substantively right, but `MALFORMED_RECORD` is the wrong code — the surrounding
code intends `DISPLAY_VALUE` — and it abandons the record's remaining checks.

**Stated plainly because it qualifies the instruction for this run:** UCA-02's
`FAIL` is correct, and no grader defect produces a wrong verdict here — but the
verdict is not attributable to the D2 ruling alone. A second candidate defect
forces it independently, and that defect reaches the report through a known
miscoding.

**What the (l) repair changed on this case.** Under `frozen-v2.5` the child also
drew `ISSUE_EVIDENCE` for citing the conflicting sources. It no longer does:

```
ISSUE_EVIDENCE against the child now: False
child PARENT_UNRESOLVED evidence : ['KL-RN-NVY-M-010.material.a', 'KL-RN-NVY-M-010.material.b']
child candidate cites            : ['KL-RN-NVY-M-010.material.a', 'KL-RN-NVY-M-010.material.b']
```

The repair is confirmed on an independently authored case, not only on its own
regression fixture.

### 3.2 UCA-06, publication — POLICY AMBIGUITY

Open decision **(f)**, unchanged.

```
expected_publication: {"sku_ids": [], "withheld_fields": {}, "parent_links": {}}
actual sku_ids      : []
actual withheld     : {"HF-TK-OLV-M-050": ["recommended_browse_nodes"]}
```

`sku_ids` and `parent_links` agree. The author's reading is that nothing
published, so nothing was withheld *from a publication*. The grader's `withheld`
is a global analysis map covering every record regardless of publication.
`SEALED_CASES.md` does not say which the key means, and the runner's choice to
compare against `result['withheld']` rather than a payload-scoped map was a
builder decision. Two defensible readings, no owner choice yet.

**Not an implementation defect:** the grader's map is self-consistent and the
SKU genuinely is withholding that field. **Not an invalid case:** the key sits
inside `expected_publication`, which favours the author's reading.

### 3.3 UCA-02, UCA-03, UCA-04, UCA-09, seller guidance — POLICY AMBIGUITY

Open decision **(g)**, unchanged. Four of the six guidance disagreements report
`no seller guidance emitted`. **That conclusion is an artefact of which channel
the harness reads, and the guidance exists:**

```
case                              sku/field                                   seller_warnings  guided_help
UCA-02-PARENT-CONFLICT-BLOCK      KL-RN-NVY-M-010/material                    NO               yes
UCA-02-PARENT-CONFLICT-BLOCK      KL-RN-NVY-S-011/material                    NO               yes
UCA-03-PARENT-CONFLICT-CHILD-LEAK SW-PL-BLK-L-020/material                    NO               yes
UCA-03-PARENT-CONFLICT-CHILD-LEAK SW-PL-BLK-XL-021/material                   NO               yes
UCA-04-PARENTLESS-PRICE-CHILD     AR-CN-WHT-M-030/price                       NO               yes
UCA-05-OPTIONAL-CONFLICT-WITHHELD BR-VN-RED-M-041/recommended_browse_nodes    yes              yes
UCA-06-WITHHELD-FIELD-PUBLISHED   HF-TK-OLV-M-050/recommended_browse_nodes    yes              yes
UCA-09-SIZE-CHART-AMBIGUOUS       CW-CN-SKY-M-080/measurement:m1              NO               yes

asserted pairs 8 | in seller_warnings 2 | in guided_help 8
```

`seller_warnings()` covers withheld optional fields only, per Decision 4;
blocking issues are carried by `guided_help()`. `compare_guidance` reads
`seller_warnings` alone. **All eight asserted pairs are covered by the grader,
including UCA-09's `measurement:m1`.** Under a both-channel reading the guidance
figure would be 6/6 rather than 2/6.

The harness was **not** changed to read both channels, because which channel an
expectation asserts against is an owner question, not the builder's. Until (g)
is settled the seller-guidance denominator says little: its 2/6 measures a
channel choice, not the grader's guidance.

### Nothing classified INVALID CASE, and nothing classified IMPLEMENTATION DEFECT

No case was found to contradict a documented rule. The one defect touching this
run — **(k)** — does not cause a wrong verdict on any of the nine; it miscodes a
correct error and abandons the rest of that record. It remains open and
deferred, not closed, and the abandonment is the reason it is not cosmetic.

---

## 4. What this run establishes, and what it does not

**Establishes.** All nine cases reached the grader; none was excluded by the
harness or the fixture format. The verdict and publication axes agree on eight
of nine each, with the single verdict disagreement resolved by owner ruling
against the case rather than against the grader. The (l) repair is confirmed on
an independently authored case.

**Does not establish.** Any rate, in either direction. Nine cases in the verdict
and publication denominators, six in guidance, of which four disagreements turn
on an unsettled channel question. The **>98%** and **<0.5%** targets remain
unmeasured and nothing here moves them. Gate 3 is unaffected and remains
**NOT MET**: 60 of 102 fixtures are still builder-authored and unadjudicated,
and running cases against the grader is a different check from reviewing those
expectations.

**And section 0 stands over all of it.** The input format these cases satisfy
was written down after they failed against it. That every expectation is
hash-identical to the author's original is what keeps the exercise independent;
it does not make the format rule independently arrived at.

---

## 5. Integrity of this run

- `grader.py` was not modified for this run, before it or after it.
- `frozen-v2.3` is intact: `grader.py` at `c31cbd9` is blob
  `06413b289ef53d0d71aa23aaf9a50b9257c01534`.
- No case file was edited. The cases were unzipped outside the repository and
  none is committed here.
- Every immutable key of every case hashes identically across all three
  encodings; only `input` ever changed.
- Every number above comes from a command that was run.
