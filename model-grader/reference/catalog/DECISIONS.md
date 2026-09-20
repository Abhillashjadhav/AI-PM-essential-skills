# Owner-approved decisions

Settled by Abhillash Jadhav across two review sessions. These supersede earlier
conflicting interpretations. Do not reopen them to accommodate existing code —
an approved rule implemented wrongly is an implementation defect, reported as one.

## The eight business judgments

| # | Scenario | Required behaviour | Implemented? |
|---|---|---|---|
| 1 | Parent has conflicting material composition | Hold the parent and affected children. A child's own matching evidence does not resolve the parent's conflict in a shared material attribute. | ✅ verified |
| 2 | Parent lacks its own price; shared attributes validated | An otherwise complete child may publish as an individual product. It does not become a parent. **Grouping is a manual supplier action after both SKUs exist — not a grader obligation.** | ✅ implemented |
| 3 | Conflicting descriptions, unapproved authoritative source | Recommend a correction to the seller. A database designation does not substitute for seller approval. | ✅ verified |
| 4 | Only an optional description conflicts | Withhold the disputed description, publish the otherwise valid product, warn the seller. Do not block the whole product. | ✅ implemented (D4) |
| 5 | "60% cotton, polyester" with no polyester percentage | Preserve both internally, mark polyester's percentage not supplied, never infer 40%. Display "60% cotton". | ✅ verified |
| 6 | Certification document uploaded, not approved | Hold the entire product — parent and every variant. An attachment alone is insufficient. | ✅ implemented family-wide (v2.3) |
| 7 | Supplier explicitly chooses US/USD | Use the selected market and currency. India/INR defaults must not override. No invented FX, no relabelling. | ✅ verified |
| 8 | Size chart assigns one measurement to two sizes | Hold the affected SKU and ask the seller to resolve. Never choose automatically. | ✅ verified |

**Standing rule.** Private company notes may exist without failing a correct
catalog, but must not alter public facts, grading, or automated actions.
Publication and action-taking consume an explicit projection of checked data,
never the raw submission.

## The eight adjudications — recorded

The owner adjudicated the eight scenarios above. These are owner judgments on
the presented scenarios, mapped to the fixtures that exercise them.

| # | Adjudication | Fixtures | Mapping |
|---|---|---|---|
| 1 | Unresolved parent material conflict blocks parent and affected children | `parent-conflict-own-evidence-child-blocked`, `parent-conflict-independent-child-cannot-publish`, `parent-conflict-inherited-child-blocked`, `ASTRA_A5_inherit_unvalidated_parent` | clean |
| 2 | A valid child may publish individually while the parent lacks its independent price | `parent-price-missing-child-ready`; `d2-child-publishes-without-dangling-parent` (metadata-26), `d2-link-retained-when-parent-published` (metadata-27) | ADJUDICATED (3) |
| 3 | A designated source does not replace seller approval for a correction | `unapproved-authority-withholds-not-blocks`, `ignored-authoritative-value`, `supplier-designated-authority-resolves-description`, `pending-correction-blocks`, `supplier-approved-correction`, `known-typo-requires-supplier-approval` | clean |
| 4 | Withhold a conflicting optional description, publish the otherwise valid product, warn the seller | `optional-conflict-withheld-silently`, `optional-conflict-withheld-and-reported`, `optional-conflict-must-not-block`, `optional-conflict-must-not-publish-disputed`, `d4-*` in `check_metadata.py` | clean |
| 5 | Preserve all supplied material information internally; do not invent missing percentages. Allow validated seller updates | `partial-parent-display-preserves-unknown-internally`, `partial-display-is-not-permission-to-drop-source`, `compatible-partial-child-inherits-percent`, `ASTRA_A4_drop_material_metadata`, `approved-family-edit-updates-children`, `wrong-derived-remainder-rejected`, `missing-derived-provenance-rejected` | clean |
| 6 | Hold the product until the catalog review team approves the applicable certificate | `certificate-needs-human-review`, `document-alone-is-not-human-approval`, `supplied-human-attestation-allows-claim`, `wrong-document-review-cannot-authorize-claim` | **mismatch — see mismatch B** |
| 7 | Explicit supplier market selection overrides defaults | `explicit-destination`, `supported-us-destination`, `unsupported-currency`, `ASTRA_A2_currency_relabel` | clean |
| 8 | Overlapping size boundaries block the affected SKU pending seller correction | `overlapping-size-bands-block`, `double-owned-size-endpoint-block`, `size-boundary-crossing-still-fails`, `owned-boundary-endpoint-still-passes` | clean |

### Mismatch A — adjudication 2 scope — **RESOLVED 2026-09-18**

Previously disclosed: the publish-individually half was covered, the "link
later" half was not, and nothing re-linked a child once its parent became
publishable in a later run.

**Resolved by owner scope ruling on 2026-09-18. It was never a grader
obligation.**

> **Owner's ruling, recorded verbatim:** Grouping a child SKU under a parent is
> a manual supplier action performed after both SKUs exist as independent
> published SKUs. It is not a grader obligation. A child whose parent is not
> ready publishes as an individual SKU; the grader has no retain-and-relink
> requirement and no later-run obligation of any kind.

**This supersedes adjudication 2's "link later" clause as a grader
requirement.** There is no gap to close, because there was never a requirement.

What remains, unchanged and covered:

| Case | Behaviour | Fixture |
|---|---|---|
| Parent not ready | the child publishes as an individual SKU with no parent link | `d2-child-publishes-without-dangling-parent` (metadata-26) |
| Parent and child both publish in the same run | the payload carries the link | `d2-link-retained-when-parent-published` (metadata-27) |

Both pass at `frozen-v2.3`. No code changed for this ruling — the grader already
behaved this way; what changed is that the behaviour is now correct by decision
rather than incomplete against one.

### Mismatch B — adjudication 6 scope — **RESOLVED 2026-09-18**

Previously disclosed: the adjudication said hold the entire product, the grader
held only the SKU carrying the claim.

**Resolved in favour of family-wide**, by the owner, on 2026-09-18.

> **Owner's reasoning, recorded verbatim:** a certification applies to a group,
> not to an individual SKU. It does not come individually, so it must be
> evaluated at group level.

**Recorded decision.** Certification approval is a family-wide publication
requirement. Until the catalog review team approves the certificate's validity
and applicability, the parent and all variants are held.

**It is a hold, not a pass.** After approval the block lifts and each SKU must
still satisfy every other check it was already subject to. Approval of the
certificate is not approval of the SKU.

Implemented in `frozen-v2.3`. Executed:

```
pending certificate on the parent
  v2.2   P1 blocking=[HUMAN_VALIDATION_REQUIRED certification]  C1 blocking=[]
         publication_payload = ['C1']
  v2.3   P1 blocking=[HUMAN_VALIDATION_REQUIRED certification]
         C1 blocking=[HUMAN_VALIDATION_REQUIRED certification]
         publication_payload = []

after approval, C1 independently broken on a required field
  P1 blocking=[]  C1 blocking=[SOURCE_CONFLICT price]
  publication_payload = ['P1']   verdict=PASS
```

Only certification is scoped this way. `SHARED` is unchanged and no other field
became family-wide.

### WITHHELD_FIELD_PUBLISHED — **APPROVED 2026-09-18**

The owner has approved the mechanism as implemented. It was added because
decision 4 says the withheld field is absent from the candidate's fields, and
without a check that rule was unenforced.

**What the code actually does**, so the record says what was approved rather than
only that approval happened. Executed against `frozen-v2.3`:

```
candidate publishes a field whose sources disagree, instead of withholding it
  errors       : [('WITHHELD_FIELD_PUBLISHED', 'P1', 'description')]
  P1 expected  : READY | candidate: READY | handling: FAIL
  verdict      : FAIL
  payload SKUs : ['C1']          <- P1 dropped out entirely
  P1 payload has 'description'? : False
```

**It fails the whole SKU.** Not that field alone, and not a warning without
penalty. The SKU's *expected* status stays `READY` — the policy does not block it
— but the candidate's handling of it fails, the run verdict is `FAIL`, and the
SKU does not reach the publication payload at all. The disputed value never
reaches the payload either way, because payload construction strips withheld
fields independently of what the candidate sent.

**These eight adjudications establish expected behaviour for the scenarios they
cover. They do not mean all 52 revision checks were independently validated. The
remaining checks are builder-authored and have not been independently
adjudicated.**

(The suite is now 55 revision checks, not 52; the three added by the D4 work are
builder-authored like the rest.)

## Publishing and grouping are separate acts — **OWNER RULING 2026-09-20**

### The rule, as it is implemented

> Parent-derived logic for a field runs only where the parent actually supplies
> that field — a settled value or a declared conflict on it. Where the parent
> supplies nothing for that field, the child is evaluated on its own values
> alone.

**This is field-scoped.** It is the operative form of the ruling and the one the
grader implements, in `supplies()`.

### The ruling as first stated, and why the wording changed

The owner's original wording was record-scoped:

> Publishing and grouping are separate acts. A SKU is evaluated and published on
> its own values alone. A parent-child relationship may be declared by the seller
> at submission or after both SKUs are already live — either is valid. A record
> naming a parent that is not live has no parent for grading purposes: no
> inheritance, no family comparison, no parent-derived blocking. It publishes if
> its own values are valid. A parent that is missing or wrong is a partial
> submission and is the seller's to complete; it never holds back a valid child.
> Family rules — shared-field conflicts, certification holds — apply only among
> SKUs that are live together.

The intent of that paragraph stands unchanged. Its phrase **"a parent that is not
live" was imprecise, not a separate rule** — owner clarification 2026-09-20. Read
record-scoped it could not be implemented: measured on the shipped fixtures, the
parents in the adjudication 1 fixtures and the parent in the adjudication 2
fixture are *all* `record_status: existing` and *all* invalid on their own
values, so no record-level test of "live" separates them. What separates them,
and always has, is the field:

```
adjudication 1  P1 parent existing  SOURCE_CONFLICT material   C1 PARENT_UNRESOLVED
adjudication 2  P1 parent existing  MISSING_REQUIRED price     C1 blocking=[]
```

`material` is in `SHARED` and propagates; `price` is not and never did. The
field-scoped rule above states that directly.

### What the two forms agree on

- A partial parent never holds back a valid child. The child publishes on its
  own values.
- A parent that is missing or wrong is the seller's to complete.
- Publishing and grouping stay separate acts; the relationship may be declared
  at submission or after both SKUs are live.

### The boundary the rule creates

A parent that carries **no settled value but declares a conflict** on the field
*has* supplied it — the value is disputed, not absent — so it still blocks the
child. Only a parent that supplies nothing at all makes the child standalone.
Proved both ways in `reproductions/ruling3_preserves_adjudications.py`
(ADJ 1b and its discriminator).

### What this supersedes

It supersedes the F3 finding in `EVALUATION_v2.3.md`. F3 reported that
`source_ref` reads `values[parent['sku']]['material']` and raises `KeyError`
when the parent has no material, and that the catch-all in `grade()` reports
that as `MALFORMED_RECORD` against a well-formed candidate record.

F3 was **not a missing guard**. The lookup should never happen, and it no longer
can: `supplies()` is asked before resolution enters the parent branch at all, so
the branch is unreachable for a field the parent does not supply. No `try`/`except`
was added — that would have preserved the wrong question and hidden the error.

Reproduced from a shipped fixture (`inputs/D01.json` with the parent's material
removed), before and after:

```
frozen-v2.3                                    frozen-v2.4
MALFORMED_RECORD C1 detail "'material'"        no MALFORMED_RECORD against C1
C1 blocking [('PARENT_UNRESOLVED','material')] C1 blocking []
published []                                   published ['C1']
later checks abandoned:                        later checks run:
  wrong composition text gives                   wrong composition text gives
  [FALSE_READY, MALFORMED_RECORD]                 [DISPLAY_VALUE, 'material']
P1 blocking [('MISSING_REQUIRED','material')]  P1 blocking [('MISSING_REQUIRED','material')]
```

The last line is the point of the ruling: the partial parent is still the
seller's to complete, and it no longer takes the valid child down with it.

### What is unchanged

- **Adjudication 1.** When parent and child are both live, an unresolved parent
  conflict still blocks the child. The four fixtures the decision record names
  pass identically on v2.3 and v2.4.
- **Adjudication 6.** A certification still holds a live family: a pending
  certificate on any live member holds the parent and every live variant.

Both proved in `reproductions/ruling3_preserves_adjudications.py`, which reports
ALL PRESERVED against frozen-v2.3 and frozen-v2.4 alike.

### Implemented in `frozen-v2.4`

`supplies(case,values,sku,field)`, consulted at the two places parent-derived
logic begins: the child branch of `source_ref()`, and the parent-problem
propagation loop in `expected_issues()`. Full suite unchanged — 3/3, 13/13,
55/55, 30/30, 31/31 — with the regression set growing 5 → 8 as the new proofs
joined it. No check changed verdict.

### Still open, and not part of this ruling

A child naming a parent **absent from the submission entirely** is still a
`SetupError` (`source parent absent`), and a child declaring `inherit_fields`
for a field its parent lacks is still a `SetupError` (`missing inherited parent
fact`). Both are fixture-validity rules that predate this ruling and neither
produces the false `MALFORMED_RECORD` this repair removes. Left untouched
deliberately; raise them separately if they should change.

## A record reports every blocking problem present on it — **OWNER RULING 2026-09-20**

Recorded verbatim.

> A record reports every blocking problem present on it, not the first one
> found. A missing required field is rejected and the seller is asked for the
> data. Conflicting sources are reported to the seller showing where the
> conflict is. When both are true of the same record, both are reported.
> Capabilities are evaluated atomically, but one record may trip several at
> once; each capability reports whenever it applies. No separate
> combined-capability case is needed.

### What this settles

`ISSUE_COVERAGE` demanding **both** `MISSING_REQUIRED` and `SOURCE_CONFLICT` on
a required field whose sources disagree is **correct**. Open decision (i) is
closed in favour of the existing behaviour. **No grader change was made for this
ruling.**

A required field whose sources disagree carries no settled value, so both are
true of that record at once:

```
KL-RN-NVY-M-010  blocking=[('MISSING_REQUIRED','material'), ('SOURCE_CONFLICT','material')]
```

Each says something the seller needs and neither substitutes for the other: the
first says the data is not usable as submitted, the second says where the
disagreement is.

### Whose expectation this overrules, and where

**`UCA-02-PARENT-CONFLICT-BLOCK`.** Its independently authored candidate reports
the conflict alone:

```
KL-RN-NVY-M-010  status=BLOCKED  issues=[('SOURCE_CONFLICT','material')]
```

and its author judged that `PASS`. Under this ruling that candidate is
incomplete and `ISSUE_COVERAGE` is right to fail it, so **the case's
`expected_verdict: "PASS"` is overruled by owner ruling.** The expectation is
not edited — it stands as the author wrote it, and this record is where the
disagreement is resolved.

`UCA-03-PARENT-CONFLICT-CHILD-LEAK` carries the same `ISSUE_COVERAGE` on its
parent. Its `expected_verdict` is `FAIL` and the grader returns `FAIL`, so the
ruling changes nothing about that case's outcome.

This was the sole POLICY AMBIGUITY behind the one incorrect rejection recorded
in `EVALUATION_v2.4.md`; with the D1 crash repaired and this ruling applied,
UCA-02's disagreement is settled against the case rather than against the
grader.

## A child's `PARENT_UNRESOLVED` carries every parent problem's evidence — **OWNER RULING 2026-09-20**

Recorded verbatim.

> A child's PARENT_UNRESOLVED carries the evidence of every parent problem on
> that field, not the first one encountered. This is the same principle as the
> ruling on reporting every blocking problem present: a candidate that cites the
> conflicting sources is doing what the seller needs, and must never be failed
> for it.

### What was wrong

A required shared field whose sources disagree trips two problems on the parent,
and `expected_issues` builds them in this order because the required-field loop
runs before conflicts are appended:

```
MISSING_REQUIRED  material  evidence []
SOURCE_CONFLICT   material  evidence ['P1.material.a', 'P1.material.b']
```

The propagation loop took the **first** problem for the field and skipped the
rest, so the child's `PARENT_UNRESOLVED` inherited the empty evidence and the
disagreeing sources were discarded. `ISSUE_EVIDENCE` compares in both directions,
so a candidate that cited them was failed:

```
child's PARENT_UNRESOLVED expected evidence: []
candidate cites:                             ['P1.material.a', 'P1.material.b']
-> ISSUE_EVIDENCE  C1  material
```

### The repair, in `frozen-v2.6`

The parent's problems are grouped by field before anything is emitted, and one
issue per field carries the **union** of every problem's evidence, in stable
order, deduplicated. Not the first one found, and not a special case for
`MISSING_REQUIRED` — any number of problems on a field contribute.

Decision 4's withhold/block split is preserved explicitly: a field propagates as
`SOURCE_CONFLICT` only when **all** of the parent's problems on it withhold. One
blocking problem is enough to block; withholding is the weaker outcome and
cannot override it.

Regression case: `reproductions/ruling_parent_unresolved_evidence.py`, which
reports `DEFECT PRESENT` on `frozen-v2.5` and `DEFECT ABSENT` on `frozen-v2.6`,
and asserts both that the evidence is complete and that the propagation still
fires.

### Why this is the same principle

The ruling above on reporting every blocking problem says a record reports every
problem present on it, not the first one found. This says the same thing about
what a propagated issue carries. In both cases the failure mode was the grader
stopping at the first thing it found and penalising a candidate for being more
complete than it was.

## The report names the field that caused the failure — **OWNER RULING 2026-09-20**

> When a SKU fails and does not publish, `withheld_fields` still names the field
> that was at issue. The seller needs to know which field sank it; an empty list
> tells them nothing.

This is existing grader behaviour and **no grader change was made**. `withheld`
is built for every record regardless of publication, so a SKU that fails still
reports the field that was withheld.

**Whose expectation this overrules, and where.**
`UCA-06-WITHHELD-FIELD-PUBLISHED` expects `withheld_fields: {}` on the reasoning
that nothing published, so nothing was withheld. The grader returns:

```
expected_publication: {"sku_ids": [], "withheld_fields": {}, "parent_links": {}}
actual sku_ids      : []                      <- agrees
actual withheld     : {"HF-TK-OLV-M-050": ["recommended_browse_nodes"]}
```

Under this ruling the grader is right and **the case's `withheld_fields: {}` is
overruled by owner ruling.** The case is not edited. Open decision (f) is
closed.

## Seller guidance must say why and what to do — **OWNER RULING 2026-09-20**

Recorded verbatim.

> Seller guidance must tell the seller why the record is blocked AND what to do
> about it. Only together is it actionable. The harness therefore reads both
> seller_warnings and guided_help, and names which channel carried each pair, so
> that "this blocks you" and "here is what to do" stay distinguishable.

Fixed in the harness, not the grader: `compare_guidance` read `seller_warnings`
alone and reported "no seller guidance emitted" for guidance the grader does
emit through `guided_help`. On the nine sealed cases that cost four of six:

```
before   SELLER GUIDANCE  denominator 6   agreements 2 / 6
after    SELLER GUIDANCE  denominator 6   agreements 6 / 6
```

Each pair now names its channel, so the two halves stay distinguishable:

```
guid.KL-RN-NVY-M-010/material [guided_help]
guid.BR-VN-RED-M-041/recommended_browse_nodes [seller_warnings+guided_help]
```

Open decision (g) is closed.

## Rendering guidance for a seller is downstream — **OWNER NOTE 2026-09-20**

The grader emits **structured** guidance: `seller_warnings` carries the SKU, the
field, the branch, the conflicting values with their evidence ids and any
`source_note`, and the required action. Rendering that conversationally for a
seller-facing chat is a downstream concern and is not this grader's job. Nothing
in the grader should be shaped by how the text will eventually read to a seller
beyond being complete, deterministic and attributable.

## Accuracy targets

**Primary outcome:** correct published SKU records ÷ all published SKU records **> 98%**

**Guardrail:** incorrectly blocked valid submissions ÷ all valid submissions **< 0.5%**

Different denominators. Do not combine them into 97.5%. Correctly blocking an
incomplete product is correct handling but is not successful publication. These
are evaluation targets, not permission to knowingly publish incorrect products.

**Neither is measured.** See `VERIFICATION.md`.

## Error ranking

| Rank | Error | Why it sits here |
|---|---|---|
| 1 | Reject correct work | Wastes completed effort, withholds an earned outcome, damages credibility |
| 2 | Silently resolve a conflict | Conceals a decision that needs supplier clarification |
| 3= | Merge unrelated products / split genuine variants | Misrepresents the family in either direction |
| 4 | Omit a required fact or an assigned record | Leaves work incomplete while concealing what was not handled |
| 5 | Copy a fact from the wrong SKU | Attaches real evidence to the wrong product |
| 6 | Invent an unsupported value | Creates facts the evidence cannot substantiate |
| P2 | Conversion error | Small permitted deviations warn; wrong evidence, boundary violations or errors beyond tolerance fail |

All blocking rules apply regardless of rank. Ranking informs strictness; it never
licenses trading a lower-ranked error for completion.

## Grader architecture

- **Interface:** Python `grade(case, candidate)`
- **Inputs:** supplier source records, evidence, relationships, destination config, candidate catalog output
- **Method:** deterministic rules checked against supplied evidence. Not exact-match to one gold answer. Not an LLM judge.
- **Outputs:** overall verdict, per-SKU handling, errors, warnings, supplier guidance, publication payload, completion counts
- **Distinction:** correctly handling a blocked product may pass evaluation while that product remains unpublished

Each evaluation case needs an independently approved **expected grading result**
and **publication outcome**. Both are recorded in the completed contract.
