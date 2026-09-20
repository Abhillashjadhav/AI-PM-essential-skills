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
| UCA-02 | **PASS → FAIL** | `[]`, `{}`, `{}` | same — agrees | 2 pairs | yes | + `guid.KL-RN-NVY-M-010/material [guided_help]`, `guid.KL-RN-NVY-S-011/material [guided_help]` |
| UCA-03 | FAIL → FAIL | `[]`, `{}`, `{}` | same — agrees | 2 pairs | yes | + `guid.SW-PL-BLK-L-020/material [guided_help]`, `guid.SW-PL-BLK-XL-021/material [guided_help]` |
| UCA-04 | PASS → PASS | `["AR-CN-WHT-L-031"]`, `{}`, `{}` | same — agrees | 1 pair | yes | + `guid.AR-CN-WHT-M-030/price [guided_help]` |
| UCA-05 | PASS → PASS | `["BR-VN-RED-M-041"]`, withheld `{BR…: [recommended_browse_nodes]}` | same — agrees | 1 pair | yes | + `guid.BR-VN-RED-M-041/recommended_browse_nodes [seller_warnings+guided_help]` |
| UCA-06 | FAIL → FAIL | `[]`, **withheld `{}`**, `{}` | `[]`, **`{HF…: [recommended_browse_nodes]}`** — **NO, overruled** | 1 pair | yes | `verdict, pub.sku_ids, pub.withheld_fields, pub.parent_links, guid.HF-TK-OLV-M-050/recommended_browse_nodes [seller_warnings+guided_help]` |
| UCA-07 | FAIL → FAIL | `[]`, `{}`, `{}` | same — agrees | none | — | `verdict, pub.sku_ids, pub.withheld_fields, pub.parent_links` |
| UCA-08 | PASS → PASS | `["MT-VN-NAT-M-070"]`, `{}`, `{}` | same — agrees | none | — | `verdict, pub.sku_ids, pub.withheld_fields, pub.parent_links` |
| UCA-09 | PASS → PASS | `[]`, `{}`, `{}` | same — agrees | 1 pair | yes | + `guid.CW-CN-SKY-M-080/measurement:m1 [guided_help]` |

On every case that asserted publication, all three parts — `sku_ids`,
`withheld_fields`, `parent_links` — were compared. Prose keys on guidance
entries (`warning_meaning`, `supplier_action`) are reported as **not compared**
on every entry that carries them; wording is never matched.

### The three denominators, kept separate

| Measurement | Denominator | Agreements | Excluded |
|---|---|---|---|
| Candidate grading | **9** | **8 / 9** | 0 |
| Publication correctness | **9** | **8 / 9** raw · **9 / 9** after the (f) ruling | 0 |
| Seller guidance | **6** | **6 / 6** | 3 (assert no guidance) |

Both publication figures are shown. The raw comparison marks UCA-06 `NO`; the
owner ruling of 2026-09-20 overrules that case's expectation (§3.2). The
adjustment is stated, never absorbed into the raw number.

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

Two disagreements, on UCA-02 and UCA-06. **Both are overruled expectations,
settled by owner ruling against the case rather than against the grader, and
neither case was edited.** A third area — seller guidance — disagreed under the
first run of these cases and no longer does; §3.3 records why, since the reason
was a harness fault rather than anything the grader did.

Nothing is classified IMPLEMENTATION DEFECT, POLICY AMBIGUITY or INVALID CASE.

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

### 3.2 UCA-06, publication — OVERRULED EXPECTATION (not a defect, not counted)

```
expected_publication: {"sku_ids": [], "withheld_fields": {}, "parent_links": {}}
actual sku_ids      : []                      <- agrees
actual parent_links : {}                      <- agrees
actual withheld     : {"HF-TK-OLV-M-050": ["recommended_browse_nodes"]}
```

The author's reading was that nothing published, so nothing was withheld. Owner
ruling 2026-09-20 settles it the other way:

> When a SKU fails and does not publish, `withheld_fields` still names the field
> that was at issue. The seller needs to know which field sank it; an empty list
> tells them nothing.

The grader is right, **the case's `withheld_fields: {}` is overruled by owner
ruling, and the case was not edited.** This was open decision (f), now closed;
no grader change was needed, because naming the field is what the grader already
did.

### 3.3 Seller guidance — RESOLVED, the guidance existed all along

Under the first run of these cases four of six guidance assertions reported `no
seller guidance emitted`. That was the harness reading one channel. Owner ruling
2026-09-20:

> Seller guidance must tell the seller why the record is blocked AND what to do
> about it. Only together is it actionable. The harness therefore reads both
> seller_warnings and guided_help, and names which channel carried each pair, so
> that "this blocks you" and "here is what to do" stay distinguishable.

`compare_guidance` now reads both and names the channel per pair. No expectation
was changed and the grader was not touched:

```
before   SELLER GUIDANCE  denominator 6   agreements 2 / 6
after    SELLER GUIDANCE  denominator 6   agreements 6 / 6
```

| Case | pair | carried by |
|---|---|---|
| UCA-02 | `KL-RN-NVY-M-010/material` | `guided_help` |
| UCA-02 | `KL-RN-NVY-S-011/material` | `guided_help` |
| UCA-03 | `SW-PL-BLK-L-020/material` | `guided_help` |
| UCA-03 | `SW-PL-BLK-XL-021/material` | `guided_help` |
| UCA-04 | `AR-CN-WHT-M-030/price` | `guided_help` |
| UCA-05 | `BR-VN-RED-M-041/recommended_browse_nodes` | `seller_warnings+guided_help` |
| UCA-06 | `HF-TK-OLV-M-050/recommended_browse_nodes` | `seller_warnings+guided_help` |
| UCA-09 | `CW-CN-SKY-M-080/measurement:m1` | `guided_help` |

All eight asserted pairs are carried. Open decision (g) is closed.

### Nothing classified INVALID CASE, and nothing classified IMPLEMENTATION DEFECT

No case was found to contradict a documented rule. Two disagreements are **overruled expectations**, settled by owner ruling
against the case rather than against the grader: UCA-02's verdict (§3.1) and
UCA-06's `withheld_fields` (§3.2). Neither is counted as an error in either
direction, and neither case was edited.

The one defect touching this run — **(k)** — does not cause a wrong verdict on
any of the nine; it miscodes a correct error and abandons the rest of that
record. It remains open and deferred, not closed, and the abandonment is the
reason it is not cosmetic.

---

## 4. What this run establishes, and what it does not

**Establishes.** The grader's verdict was correct on all nine cases. Eight of
the nine were confirmed by an independent author who never saw the code; on the
ninth the author's expectation was overruled by owner ruling. Publication agrees
on all nine once UCA-06's overruled expectation is set aside, and every one of
the eight asserted guidance pairs is carried by the grader. All nine cases
reached the grader; none was excluded by the harness or the fixture format. The
(l) repair is confirmed on an independently authored case.

**Does not establish.** Any rate, in either direction. Nine cases do not
establish the production accuracy targets. The **>98%** publication-correctness
target and the **<0.5%** wrong-rejection guardrail remain unmeasured and nothing
here moves them. Gate 3 is unaffected and remains
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
