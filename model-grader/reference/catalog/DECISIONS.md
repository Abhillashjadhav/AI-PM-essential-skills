# Owner-approved decisions

Settled by Abhillash Jadhav across two review sessions. These supersede earlier
conflicting interpretations. Do not reopen them to accommodate existing code —
an approved rule implemented wrongly is an implementation defect, reported as one.

## The eight business judgments

| # | Scenario | Required behaviour | Implemented? |
|---|---|---|---|
| 1 | Parent has conflicting material composition | Hold the parent and affected children. A child's own matching evidence does not resolve the parent's conflict in a shared material attribute. | ✅ verified |
| 2 | Parent lacks its own price; shared attributes validated | An otherwise complete child may publish as an individual product. It does not become a parent. Retain the intended relationship internally and link when the parent is ready. | ⚠️ partial |
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
| 2 | A valid child may publish individually while the parent lacks its independent price; link later | `parent-price-missing-child-ready`; `d2-child-publishes-without-dangling-parent`, `d2-link-retained-when-parent-published` | **partial — see mismatch A** |
| 3 | A designated source does not replace seller approval for a correction | `unapproved-authority-withholds-not-blocks`, `ignored-authoritative-value`, `supplier-designated-authority-resolves-description`, `pending-correction-blocks`, `supplier-approved-correction`, `known-typo-requires-supplier-approval` | clean |
| 4 | Withhold a conflicting optional description, publish the otherwise valid product, warn the seller | `optional-conflict-withheld-silently`, `optional-conflict-withheld-and-reported`, `optional-conflict-must-not-block`, `optional-conflict-must-not-publish-disputed`, `d4-*` in `check_metadata.py` | clean |
| 5 | Preserve all supplied material information internally; do not invent missing percentages. Allow validated seller updates | `partial-parent-display-preserves-unknown-internally`, `partial-display-is-not-permission-to-drop-source`, `compatible-partial-child-inherits-percent`, `ASTRA_A4_drop_material_metadata`, `approved-family-edit-updates-children`, `wrong-derived-remainder-rejected`, `missing-derived-provenance-rejected` | clean |
| 6 | Hold the product until the catalog review team approves the applicable certificate | `certificate-needs-human-review`, `document-alone-is-not-human-approval`, `supplied-human-attestation-allows-claim`, `wrong-document-review-cannot-authorize-claim` | **mismatch — see mismatch B** |
| 7 | Explicit supplier market selection overrides defaults | `explicit-destination`, `supported-us-destination`, `unsupported-currency`, `ASTRA_A2_currency_relabel` | clean |
| 8 | Overlapping size boundaries block the affected SKU pending seller correction | `overlapping-size-bands-block`, `double-owned-size-endpoint-block`, `size-boundary-crossing-still-fails`, `owned-boundary-endpoint-still-passes` | clean |

### Mismatch A — adjudication 2, "link later" is unimplemented

The publish-individually half is covered. The *link later* half is not: nothing
re-links a child to its parent once the parent becomes publishable in a later
run. `d2-link-retained-when-parent-published` covers a parent that is ready in
the same run, which is a different thing. Deferred relinking is out of scope for
this task and is recorded as unaddressed in `DIVERGENCES.md`.

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
