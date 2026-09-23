# Open decisions

Raised by review, not settled. Recorded in the owner's terms, never resolved
with a default. A guessed answer looks decided and nobody revisits it.

| # | Question | What it costs to leave open | Who can decide |
|---|---|---|---|
| b | **Adjudication 5's "seller supplies the missing percentage later; validate and update affected records" — grader scope or workflow scope?** No mechanism exists today. | Either an unbuilt requirement sits in the contract, or a real workflow step has no owner. | Owner |
| k | **`text_parts` raises `ValueError` for candidate text outside the grammar, and the catch-all reports it as `MALFORMED_RECORD`.** The surrounding code's intent is plainly `DISPLAY_VALUE` — it writes `if text_parts(...) != ek: err('DISPLAY_VALUE',...)` — but the parser raises instead of returning, so the comparison never happens. **Deferred by owner 2026-09-20, explicitly not as cosmetic.** | **The verdict is correct** — the candidate's text really is outside the grammar, so `FAIL` is right — but `MALFORMED_RECORD` is raised from the catch-all wrapping the whole per-record block, so **every remaining check on that record is abandoned**. That is the same silent hole as F3: a real defect later in the record is never examined, and it can hide errors in both directions. A right verdict reached with the rest of the record unchecked is not a safe verdict. | Owner |

## Settled since the last revision

- **(h) Is the list form of `expected_seller_guidance` accepted, and is prose
  ever compared.** Settled by owner ruling 2026-09-20: **the plain list is
  valid**, and prose is never compared — "meaning, never wording" still holds,
  so `warning_meaning` and `supplier_action` are named in the report as not
  compared rather than silently ignored. Implemented in `normalise_guidance()`
  and documented in `SEALED_CASES.md`. *Recorded late: the ruling was given and
  implemented before this entry was moved out of the open table.*

- **(f) Is `expected_publication.withheld_fields` scoped to what published.**
  Settled by owner ruling 2026-09-20: **no — the report names the field that
  caused the failure.** "The seller needs to know which field sank it; an empty
  list tells them nothing." Existing grader behaviour; no grader change.
  `UCA-06-WITHHELD-FIELD-PUBLISHED`'s `withheld_fields: {}` is overruled by the
  ruling and the case was not edited.

- **(g) Which channel `expected_seller_guidance` asserts against.** Settled by
  owner ruling 2026-09-20: **both.** "Seller guidance must tell the seller why
  the record is blocked AND what to do about it. Only together is it
  actionable." Fixed in the harness, not the grader; each pair now names the
  channel that carried it. The guidance figure on the nine cases moved 2/6 to
  6/6.

- **(l) What a child's `PARENT_UNRESOLVED` carries.** Settled by owner ruling
  2026-09-20: **the evidence of every parent problem on that field**, not the
  first one encountered. "A candidate that cites the conflicting sources is
  doing what the seller needs, and must never be failed for it." Repaired in
  `frozen-v2.6` by grouping the parent's problems per field and carrying the
  union of their evidence; regression case
  `reproductions/ruling_parent_unresolved_evidence.py`. See `DECISIONS.md`.

- **(i) A required field whose sources conflict: one issue or two.** Settled by
  owner ruling 2026-09-20: **two**. "A record reports every blocking problem
  present on it, not the first one found... When both are true of the same
  record, both are reported." `ISSUE_COVERAGE` demanding both `MISSING_REQUIRED`
  and `SOURCE_CONFLICT` is correct; no grader change was made. The contrary
  expectation in `UCA-02-PARENT-CONFLICT-BLOCK` is overruled by the ruling, and
  its expectation was not edited. See `DECISIONS.md`.

- **(e) What shape an input `evidence` value is.** Settled by owner ruling
  2026-09-20: an evidence entry's `value` is the exact machine value of the field
  it evidences — the same shape the record carries. For `material` that is the
  full object, not prose about the source. Documented as clause 2a in
  `contract.md` and `contract_v1.4.md`, and in `SEALED_CASES.md` with a worked
  scalar example and a worked `material` example. The source's own words now have
  a home: the optional, inert `source_note` on the entry.

- **(j) What makes a parent "live".** Settled by owner ruling 2026-09-20:
  **field-scoped**. Parent-derived logic for a field runs only where the parent
  actually supplies that field — a settled value or a declared conflict on it.
  Where the parent supplies nothing for that field, the child is evaluated on its
  own values alone. The earlier record-scoped phrase "a parent that is not live"
  was imprecise rather than a separate rule; both forms are recorded side by side
  in `DECISIONS.md`. Implemented in `frozen-v2.4` as `supplies()`. Adjudications
  1 and 6 are unaffected and proved so against both versions.

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
