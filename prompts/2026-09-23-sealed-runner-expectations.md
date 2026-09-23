# Sealed-case runner expectation and reporting repair

## Requested scope

Repair the four reproduced runner defects on PR #56's frozen-v2.6 source:

1. A malformed expectation block alongside a valid measurement must make the
   case `CASE_SCHEMA_ERROR` and the CLI fail, while retaining valid measurements
   in their separate denominators.
2. A case with only schema errors must report diagnostics and write JSON without
   crashing on a missing report note.
3. Invalid guidance containers or entries must produce schema diagnostics rather
   than an exception or silently skipped assertion. Preserve both documented
   guidance shapes and empty/unasserted guidance.
4. A named SKU with an expected null parent must actually publish. Preserve the
   documented null, empty-map, scoped-map and exhaustive-map distinctions.

Also replace the report's unconditional independence claim with a neutral case
comparison description: the runner does not verify case-author independence.

Do not modify the frozen grader, expectations, owner decisions, or policy. No
model calls, new sealed cases, remote writes or publication. Use synthetic
regression wrappers around existing development fixtures, record RED first,
then positive controls and the standard deterministic checks. At most two
implementation repair attempts. Save a review and commit locally for independent
review before a draft targeting `claude/model-grader-skill-three-hand`.

## Source boundary recorded before edits

- VERIFIED: upstream PR #56 source head
  `686203f810370ccfb2bf11d607429554fdc7a70a`; all 42 changed file blobs in its full
  diff were verified after applying to the verified main source snapshot.
- VERIFIED: isolated local source snapshot
  `8f2e4931f05cc64fe0f88356458c0e1bcd4f5ea4`, tree
  `2e448bb7dbd799502423dd5d7ae20517b862ee75`. This identifies source content,
  not upstream commit ancestry.
- VERIFIED: frozen `grader.py` git blob
  `2c853009590a386139c6b6cf8623cab2e8693720`.
- VERIFIED: the parent reviewer separately advanced #56 to
  `bac80b7b7c9267f1911a19cda91e663636fd9433` with two whitespace-only changes.
  This repair does not edit those files; publication will preserve that head.
- UNKNOWN: actual sealed cases are unavailable. These regressions cannot
  establish independent evaluation, calibration, or target accuracy.

The applicable instructions are `AGENTS.md`, `CLAUDE.md`, and the relevant
review criteria in `.claude/commands/pr-review.md`. This is one runner
correctness concern; no skill or contract revision is included.

## Independent review: second repair round

The parent review reproduced additional shape failures in the same runner:
`withheld_fields: []` and `sku_ids: 1` crash; `parent_links: []` can be coerced
to an empty map and pass; a non-boolean exhaustive flag is coerced by truthiness.
A raw case containing JSON null or some other non-object shapes also crashes.

Add RED controls, then validate only the documented shapes before comparison:
SKU lists contain strings; withheld-field maps contain lists of strings;
parent-link maps contain strings or null; an exhaustive flag is a literal
boolean. Omitted or null publication parts remain unasserted, empty field lists
remain dropped, and all existing parent-link semantics remain intact. Reject a
non-object raw case as a load diagnostic. Preserve valid measurements on other
axes and the frozen grader. This is the second and final repair attempt.
