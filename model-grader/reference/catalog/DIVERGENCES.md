# Divergences from the approved decisions

Executed against `revised-v2.1`. Every result below came from a run, not a reading.

## D4 · Optional-field conflict blocks the whole SKU — architectural

**Decision 4 requires:** withhold the disputed description, publish the otherwise
valid product, warn the seller.

**Implementation does:** blocks the entire SKU.

**Root cause.** The status rule is `wanted = 'BLOCKED' if expected else 'READY'`.
Any issue blocks the whole record. `SOURCE_CONFLICT` fires on optional fields
exactly as on required ones. The publication payload is all-or-nothing per record.
There is no field-withholding path.

**Executed.** P1 carrying only a disputed `description` → expected status
`BLOCKED`, absent from the publication payload.

**Also:** `revision_checks.json` entry `optional-description-conflict-needs-authority`
encodes the superseded policy — expects `PASS` with P1 `BLOCKED`, rule text
*"Unresolved optional contradiction still needs authority."* It will keep passing
while being wrong. This is a builder-authored expectation standing in for an
owner decision, which the four-gate model exists to make visible.

**Required change.** A `WITHHELD` outcome for a single field, distinct from
blocking the SKU; the withheld field omitted from the payload while the rest
publishes; seller guidance emitted for it. Optional-field conflict blocks
nothing else; required-field conflict still blocks.

**OPEN — how the seller guidance is carried.** Decision 4 says "warn the
seller". It does not say through which channel, and an earlier revision of
this file asserted the warning must be candidate-written and grader-checked.
That was the writer's over-specification, not an owner decision, and it is
withdrawn. Two options, both consistent with decision 4:

| Option | What it means | Cost |
|---|---|---|
| **Grader-computed** | the grader derives the guidance from the conflict it detected and reports it, as it already does for `guided_help` | nothing new for the candidate to get wrong; the grader cannot check whether the model understood the conflict |
| **Candidate-written, grader-checked** | the model must emit the warning and the grader verifies it names the field and the conflicting sources | tests whether the model actually understood; adds a new required output field and a new way to fail |

Unsettled. The owner decides. The D4 implementation should not assume either
until they do.

## D2 · Child publishes, but carries a dangling parent reference — partial

**Decision 2 requires:** the child publishes as an individual product, does not
become a parent, and the intended relationship is retained internally and linked
when the parent is ready.

**Implementation does:** the child publishes correctly. `price` is not in `SHARED`,
so a parent missing price produces no `PARENT_UNRESOLVED` on the child.

**But:** the payload row for the child carries `role: child` and `parent_sku: P1`
while P1 is absent from the payload. A downstream consumer sees a child pointing
at a parent that is not there.

**Executed.** Parent price removed → P1 `BLOCKED`, C1 `READY`, payload `['C1']`,
C1 row `role: child`, `parent_sku: P1`.

## Verified against the decisions

1, 3, 5, 6 (per-SKU), 7, 8 — see `DECISIONS.md` for the evidence per decision.
