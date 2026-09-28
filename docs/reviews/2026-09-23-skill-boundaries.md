# Skill boundary alignment evidence

VERIFIED scope: four existing documentation gaps on local baseline
`6a8c0d3910e20eb46fac7c9d0172db2730bdac7d`, representing verified main
`60b61efb1294c10045f6af11ff07ce5aea5bb03b`.

| Skill | Existing gap | Change and source basis |
| --- | --- | --- |
| prd-first | Trigger phrase; limitations heading | Preserve the same trigger cases with `Use this skill when`; rename the existing exclusions section to `Limitations`. |
| ai-feature-kill-criteria | Limitations heading | Rename `Limits` to `Limitations`; keep the existing limitation text. |
| context-auditor | Negative trigger; limitations | State the existing diagnose-only boundary in frontmatter; clarify that supplied-text review and approximate counts do not execute an agent or measure runtime reliability. |
| human-product-writer | Limitations heading | Place the heading above the existing prohibition on scoring the writer, guessing AI authorship, or promising engagement and product outcomes. |

VERIFIED: No workflow steps, thresholds, output formats, metadata keys, or skill
names changed. No capabilities or calibration results were added. The two source
skills owned by the token-guidance change remain byte-identical to the baseline.
No owner choice was needed to describe these existing limits.

## Validation

- Before editing, `python3 tests/lint_skill.py <path>` returned 1 for each of the
  four files and identified exactly the gaps above. After editing, it returned 0
  for all four on the first implementation attempt.
- YAML parsing and structural checks pass: metadata key sets and names are
  unchanged, all descriptions are below 1,024 characters, all files are below
  500 lines, and every file has a `Limitations` section.
- Skill-creator's `quick_validate.py` passes prd-first, ai-feature-kill-criteria,
  and human-product-writer. It rejects context-auditor's existing `argument-hint`
  metadata before and after this change. The repository's CLAUDE.md expects that
  field, so it is preserved. This generic schema incompatibility is not reported
  as a successful validation or worked around by changing the skill contract.
- `python3 scripts/check_repository_integrity.py` passes for eight plugins,
  three standalone skills, 17 READMEs, and four ContextPort paths.
- `git diff --check` passes.

These are lint and documentation-consistency checks. No behavioral evaluation,
live calibration, or production reliability measurement was performed or
claimed. No new tests were added to mirror the prose. The coordinating reviewer
will independently review this source change before publication or merge.
