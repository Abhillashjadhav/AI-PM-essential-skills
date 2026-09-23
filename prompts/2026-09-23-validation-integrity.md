# Validation integrity review prompt

Review the verified 426-file source snapshot of main
`60b61efb1294c10045f6af11ff07ce5aea5bb03b` (local baseline
`6a8c0d3910e20eb46fac7c9d0172db2730bdac7d`) for concrete false acceptance in
`scripts/check_repository_integrity.py`, `.github/scripts/pr_required_checks.py`,
and `tests/lint_skill.py`.

Use an isolated feature branch. Read AGENTS.md and CLAUDE.md. Use only offline
synthetic fixtures; do not call paid models, access credentials, change existing
skill policies, add dependencies, publish, or merge. Preserve the existing gates
and thresholds. Save meaningful failing-before and positive-control tests, allow
at most two implementation repair attempts per failed gate, and record results.
The coordinating reviewer will independently review the local commits.

## Verified reproduction scope

- VERIFIED: Duplicate marketplace names pass the integrity checker, but the
  public-smoke installation loop fails when two entries copy to the same target.
- VERIFIED: Skill frontmatter containing a top-level list or a boolean
  description exits successfully because an exception leaves mandatory checks
  absent from the result.
- VERIFIED: A committed `café.py` containing invalid Python passes the complete
  PR checks CLI because Git's default name quoting hides the actual file path.
- VERIFIED: Draft PR #27 at `f9a0f80daf03a2ab0dcfe60309ac863b500acae3`
  contains neither duplicate-name validation nor these regression cases. Use a
  distinct new regression test file to avoid its pending test-file collision.

## Acceptance

1. Reject duplicate names before constructing an ambiguous marketplace lookup.
2. Require every current lint check to complete successfully. Non-mapping YAML
   and non-string name or description values must fail without relaxing current
   trigger, length, or limitations requirements.
3. Preserve actual Git paths, including non-ASCII characters and newlines, for
   syntax, privacy, and existing-skill checks.
4. Keep valid unique marketplaces, valid skill metadata, and valid Python paths
   passing. Run the actual repository integrity audit and existing PR tests.
5. Change validators, focused tests, this prompt, and evaluation evidence only.
   Do not modify source SKILL.md files or any pending product-policy decisions.
