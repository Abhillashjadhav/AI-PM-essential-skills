# Open decisions

Raised by review, not settled. Recorded in the owner's terms, never resolved
with a default. A guessed answer looks decided and nobody revisits it.

| # | Question | What it costs to leave open | Who can decide |
|---|---|---|---|
| b | **Adjudication 5's "seller supplies the missing percentage later; validate and update affected records" — grader scope or workflow scope?** No mechanism exists today. | Either an unbuilt requirement sits in the contract, or a real workflow step has no owner. | Owner |
| e | **What shape is an input `evidence` value?** The grader requires a `material` evidence value to be an object (`material_key`: `material must be object`) and requires `evidence[f'{sku}.{field}'].value` to equal the record's field value exactly. No contract, prompt or `SEALED_CASES.md` clause says so. The nine sealed-case authors wrote source prose (`"60% cotton / 40% polyester (spec sheet A)"`), modelling evidence as what a source says and `fields` as the value derived from it. | All nine cases were rejected before grading. Until this is written down and published, no one outside the builder can author a case the grader will read. | Owner |
| f | **Is `expected_publication.withheld_fields` scoped to what published?** A SKU that fails and does not publish still appears in the grader's `withheld` map. UCA-06's author expected `{}` — nothing published, so nothing withheld. `SEALED_CASES.md` does not say, and the runner's choice to compare against `result['withheld']` rather than a payload-scoped map was a builder decision. | A publication check that means two things measures neither. | Owner |
| g | **Which channel does `expected_seller_guidance` assert against?** `seller_warnings()` covers withheld optional fields only (Decision 4); blocking issues are carried by `guided_help()`. Of the 8 sku+field pairs the authors asserted, 8 are in `guided_help` and 2 in `seller_warnings`. | The harness currently reports "no seller guidance emitted" for guidance that exists. Left open, the guidance denominator is meaningless. | Owner |
| h | **Is the list form of `expected_seller_guidance` accepted, and is prose ever compared?** The cases supply `[{sku, field, warning_meaning, supplier_action}]`; the published schema is `{required, must_not_warn}` and forbids wording comparison. `sku` + `field` maps over cleanly; the two prose keys cannot be compared under the current rule. | Six cases score no guidance at all. Either the schema accepts the list form or case authors must be told otherwise before the next round. | Owner |
| i | **A required field whose sources conflict and which therefore carries no value: one issue or two?** The grader expects both `MISSING_REQUIRED` and `SOURCE_CONFLICT`, and `ISSUE_COVERAGE` fails if either is missing. UCA-02's candidate reported the conflict alone and its author judged that a PASS. Reproduced on shipped `inputs/D01.json`. | A candidate that diagnoses the problem correctly is marked wrong for not also reporting its consequence. Drives a wrong rejection. | Owner |

## Settled since the last revision

- **(a) Certification scope.** Settled by owner decision 2026-09-18:
  **family-wide**. A certification applies to a group, not an individual SKU, so
  it is evaluated at group level. Implemented in `frozen-v2.3`; recorded in
  `DECISIONS.md` with the executed evidence.
- **(c) Decision 4's seller-warning channel.** Settled by owner decision:
  grader-generated, deterministic, three branches driven by the computed status.
  Implemented as `warning_branch()`; see `DIVERGENCES.md`.
- **(d) `WITHHELD_FIELD_PUBLISHED`.** Approved by the owner 2026-09-18 as
  implemented. `DECISIONS.md` records what it actually does — it fails the whole
  SKU, which drops out of the publication payload — rather than only that
  approval happened.
- **Deferred relinking.** Closed by owner scope ruling 2026-09-18: grouping a
  child under a parent is a manual supplier action after both SKUs exist, not a
  grader obligation. There is no later-run requirement of any kind, so there is
  no gap. See `DECISIONS.md`, Mismatch A.
- **The eight adjudications.** Complete. Recorded in `DECISIONS.md` with their
  fixture mapping. Mismatch B is now resolved; mismatch A remains open below.

## Not yet built

- **A published input format.** See (e). The format exists in code and in the
  shape of 102 builder-authored fixtures, and nowhere a case author can read.
  This is the single finding of the nine-case run.

- **Sealed cases that the grader can read.** Nine were authored, owner-signed
  and run; all nine were rejected before grading (`EVALUATION_v2.3.md`). There is
  no tenth case and none is outstanding. **Until cases exist that both parties
  can produce and consume, no accuracy claim is possible.**
- **The accuracy targets are unmeasured.** The primary outcome (**> 98%** of
  published SKU records correct) and the guardrail (**< 0.5%** of valid
  submissions wrongly rejected) have never been measured, and nothing currently
  in the repository can measure them. Every number the suite reports is
  self-consistency against builder-authored expectations.
