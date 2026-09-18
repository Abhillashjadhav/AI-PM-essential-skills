# Open decisions

Raised by review, not settled. Recorded in the owner's terms, never resolved
with a default. A guessed answer looks decided and nobody revisits it.

| # | Question | What it costs to leave open | Who can decide |
|---|---|---|---|
| a | **Is a certification claim per-SKU or family-wide?** Adjudication 6 says hold the entire product, but `claims` are per-record and `HUMAN_VALIDATION_REQUIRED` does not propagate to children. Executed: a parent carrying an unapproved certification gets `blocking=[('HUMAN_VALIDATION_REQUIRED','certification')]` while its child gets `blocking=[]` and publishes. `certification` is not in `SHARED`, so nothing propagates. | If certification is family-scoped, the current split publishes an uncertified record alongside a held one. | Owner |
| b | **Adjudication 5's "seller supplies the missing percentage later; validate and update affected records" — grader scope or workflow scope?** No mechanism exists today. | Either an unbuilt requirement sits in the contract, or a real workflow step has no owner. | Owner |
| d | **Is `WITHHELD_FIELD_PUBLISHED` the mechanism the owner wants?** Decision 4 says the withheld field is absent from the candidate's fields; without a check that rule is unenforced, so this code was added. It enforces a stated rule rather than inventing one, but the decision did not name a mechanism. | If the owner wants something else, candidates are being failed against a code they never agreed to. | Owner |

## Settled since the last revision

- **(c) Decision 4's seller-warning channel.** Settled by owner decision:
  grader-generated, deterministic, three branches driven by the computed status.
  Implemented as `warning_branch()`; see `DIVERGENCES.md`.
- **The eight adjudications.** Complete. Recorded in `DECISIONS.md` with their
  fixture mapping and the two mismatches they exposed.

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
