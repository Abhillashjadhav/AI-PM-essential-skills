# Catalog repair status

Checked on 2026-09-28 against `marketplace-d4-d2-v1`.

## D4 — optional-field withholding repaired

A conflict on an optional field withholds that field and leaves an otherwise
valid SKU eligible for publication. Required-field conflicts still block.
Candidate reporting of the optional conflict is permitted but not required;
the grader generates the seller warning from the source evidence. Publishing
the disputed field fails the SKU and excludes it from the payload.

The implementation includes the existing follow-up repairs for inherited
optional fields, family comparisons and optional issue reporting. Warnings now
also use final payload eligibility: a source classified READY whose candidate
fails validation is not described as published.

## D2 — dangling payload links repaired

The candidate retains its intended parent relationship. The payload includes
the parent link only when that parent also publishes in the same result;
otherwise `parent_sku` is null and the child's role is preserved. Inputs are not
mutated. Later relinking is a manual supplier action under the recorded owner
scope ruling, not an asynchronous feature of this grader.

## Source and fixture changes

This repair reuses the repository's existing work in
[PR #54](https://github.com/Abhillashjadhav/AI-PM-essential-skills/pull/54):

- Runtime and D4/D2 checks through `c612f67` include the three follow-up repairs.
- `c522a9d` records the owner ruling that withholding means field absence, without
  a candidate-written `withheld` marker. The two old failing fixture shapes are
  corrected accordingly; their expected PASS outcomes are preserved. Three new
  cases check both acceptance and rejection, giving 55 revision checks.
- The owner approved `WITHHELD_FIELD_PUBLISHED` in `5cf24e4`; it fails the SKU,
  rather than silently sanitizing and approving the submitted record.
- `f2aaec8` records that later relinking is outside the grader's obligations.

The imported source remains attributed. This integration is a new version;
it does not rewrite or claim to be frozen v2.2/v2.3 or the later v2.6 work.

## Executed evidence

- Reference command exits 0: 3/3 approved cases, 12/12 original faults,
  55/55 revision checks and 31/31 metadata/payload checks match.
- All 30 saved candidates are accepted; no fresh model run occurred.
- Six publication regression tests pass, including source/candidate rejection,
  inherited fields and both parent-link directions. CI runs them and the
  reference command on every PR.

## Remaining scope

The later family-wide certification decision and implementation in #54 are not
part of this narrow D4/D2 integration. The current certification behavior is
still per-SKU. Later grader PRs also contain input-format, sealed-case and
additional ruling work that needs its own combined review. None of those PRs
was bulk-merged or marked obsolete by this repair.

The interview's exit test on a filled contract and an independently adjudicated
holdout are not established here. The >98% correct-publication and <0.5% wrong-
rejection targets remain unmeasured. A passing development suite does not
certify the reference for production use.
