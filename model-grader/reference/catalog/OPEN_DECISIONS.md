# Open decisions

Raised by review, not settled. Recorded in the owner's terms, never resolved
with a default. A guessed answer looks decided and nobody revisits it.

| # | Question | What it costs to leave open | Who can decide |
|---|---|---|---|
| a | **Is a certification claim per-SKU or family-wide?** Decision 6 says hold the entire product, but `claims` are per-record and `HUMAN_VALIDATION_REQUIRED` does not propagate to children. Today a held parent can sit beside a published child. | If certification is family-scoped, the current split publishes an uncertified record alongside a held one. | Owner |
| b | **Decision 5's "seller supplies the missing percentage later; validate and update affected records" — grader scope or workflow scope?** No mechanism exists today. | Either an unbuilt requirement sits in the contract, or a real workflow step has no owner. | Owner |
| c | **Decision 4's seller warning — which channel, and what must it carry?** A withheld-field warning has to reach the candidate output to be checkable at all. | Without this, decision 4 cannot be implemented as stated — the withholding is buildable, the warning is not. | Owner |

## Not yet built

- **Ten sealed cases.** Input, candidate output, owner verdict, owner one-line
  reason, mixing valid work and plausible mistakes. Must be prepared without
  access to the grader, the revision checks or the attacks, and the verdicts are
  the owner's to assign.
- **Eight adjudications.** A sample of the 52 revision checks, judged by the
  owner rather than the builder.
