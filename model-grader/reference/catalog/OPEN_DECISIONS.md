# Open decisions

Raised by review, not settled. Recorded in the owner's terms, never resolved
with a default. A guessed answer looks decided and nobody revisits it.

| # | Question | What it costs to leave open | Who can decide |
|---|---|---|---|
| b | **Adjudication 5's "seller supplies the missing percentage later; validate and update affected records" — grader scope or workflow scope?** No mechanism exists today. | Either an unbuilt requirement sits in the contract, or a real workflow step has no owner. | Owner |

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
- **The eight adjudications.** Complete. Recorded in `DECISIONS.md` with their
  fixture mapping. Mismatch B is now resolved; mismatch A remains open below.

## Not yet built

- **Ten sealed cases.** Input, candidate output, owner verdict, owner one-line
  reason, mixing valid work and plausible mistakes. Must be prepared without
  access to the grader, the revision checks or the attacks, and the verdicts are
  the owner's to assign. **Until these exist and are owner-signed, no accuracy
  claim is possible.**
- **The accuracy targets are unmeasured.** The primary outcome (**> 98%** of
  published SKU records correct) and the guardrail (**< 0.5%** of valid
  submissions wrongly rejected) have never been measured, and nothing currently
  in the repository can measure them. Every number the suite reports is
  self-consistency against builder-authored expectations.
- **Deferred relinking.** Adjudication 2's "link later" — re-linking a child to
  its parent once the parent becomes publishable in a later run — is
  unimplemented and out of scope for the current task. See `DIVERGENCES.md`.
