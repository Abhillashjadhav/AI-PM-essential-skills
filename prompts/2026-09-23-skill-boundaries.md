# Source task

Resolve four existing skill-lint documentation gaps on verified main
`60b61efb1294c10045f6af11ff07ce5aea5bb03b` (local baseline
`6a8c0d3910e20eb46fac7c9d0172db2730bdac7d`): prd-first's trigger phrase and
limitations heading, ai-feature-kill-criteria's limitations heading,
context-auditor's negative trigger and limitations, and human-product-writer's
limitations heading.

Read the full skills, repository instructions, and skill-creator workflow.
Only clarify existing trigger boundaries and accurate limitations. Preserve
workflows, thresholds, output formats, and product policies. Do not invent
capabilities, claim live calibration, or touch concise-rewriter and
token-cost-estimator, which are covered by a separate change. Flag any required
owner choice instead of deciding it.

Use a separate feature worktree, run existing lint and structural checks, save
evaluation evidence, and commit locally for independent review. No new tests
that merely mirror prose, no live calls, and no publication or merge.

## Verified implementation plan

- Reuse existing limitation text for prd-first, ai-feature-kill-criteria, and
  human-product-writer by naming the section consistently.
- Preserve prd-first's existing trigger cases while using the linter's expected
  phrase, `Use this skill when`.
- Clarify context-auditor's existing diagnose-only role and the limits of a
  review of supplied text, approximate counts, and unmeasured runtime behavior.
- These are repository-owned source skills, not a personal-skill installation.
  Keep their existing paths and metadata and persist the authorized edits in
  this source branch; the coordinating reviewer handles publication.
