# Review and evidence — catalog follow-through

Base: `b79a57e93c586e84746f47ca9d0e142f3b58c9be`, after #76, #77 and #78
merged in that order under the owner's explicit authorization.

## Change and source

Integrate D4/D2 runtime and fixture repairs from the existing #54 work through
`c612f67`. These are repairs to recorded owner decisions, not new product policy.
The imported changes include the three follow-up D4 repairs. The source and
later owner rulings are identified in the catalog's `DIVERGENCES.md`.

The first runtime-only replay still failed the two original cases because they
carried an obsolete candidate `withheld` key. The existing fixture repair in
`c522a9d` records the owner ruling requiring field absence, with grader-generated
warnings. Imported that repair without changing those expected PASS outcomes;
it adds three checks for both acceptance and rejection. No expectation was
changed merely to make the implementation pass.

One additional defect appeared during integration: the imported warning code
described a READY source as published even when the candidate or batch failed.
Warnings now use the final payload eligibility. A control using the unmodified
imported logic fails three rejection subcases; the repaired logic passes all
four, including an omitted SKU. This control uses no live model or service.

## Executed validation

| Check | Result |
|---|---|
| Verifier / validator / ContextPort / publication unit suites | 95 + 24 + 107 + 6 = 232 passed |
| Catalog approved / fault / revision / metadata-payload checks | 3/3 + 12/12 + 55/55 + 31/31 matched; command exits 0 |
| Saved candidate replay | 30/30 accepted; not an accuracy estimate |
| Metadata lint | 16/16 skills pass |
| Repository integrity | 8 plugins, 3 standalone skills, 19 READMEs pass |
| Coverage extraction | 45/45 inputs, 44/44 codes mapped to 20/26 questions; mappings remain author judgments |
| Diff whitespace | PASS |

CI now runs the catalog command and publication regressions on every PR.
Final GitHub checks must pass on the exact published head before merge.

## PR review

This is a Codex self-review using `.claude/commands/pr-review.md`, not independent
adjudication or a review by the prospective hiring manager.

```text
PR REVIEW: catalog D4/D2 follow-through
SPEC COMPLIANCE    PASS — no skill metadata changed; runtime and prompt agree.
NOVELTY            PASS for this repair — existing repository work is attributed.
HARD RULES         PASS — required fields block; disputed values stay out of payloads.
TESTABILITY        PASS — both-sided checks, payload assertions and warning control.
BLOAT              PASS — scoped runtime repair; most added lines are existing fixtures.
VERDICT: APPROVE
Required changes before merge: none from this review; final CI must pass.
```

## Limits

No frozen historical grader was rewritten. Family-wide certification and later
grader policy, sealed-case and runner work remain in their existing PRs for a
separate combined review. The current certification code remains per-SKU.
The interview's filled-contract exit test and independent holdout are still
unproven; neither accuracy target is measured. These limits remain public.

The marketplace repair is not a release, live installation, production
certification, plagiarism guarantee or independent model-quality evaluation.
