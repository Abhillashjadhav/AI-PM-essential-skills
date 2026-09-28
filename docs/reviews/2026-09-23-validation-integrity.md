# Validation integrity evidence

Scope: three deterministic validator defects in the verified 426-file main
snapshot `60b61efb1294c10045f6af11ff07ce5aea5bb03b` (local base
`6a8c0d3910e20eb46fac7c9d0172db2730bdac7d`). All fixtures are synthetic and
offline. No dependencies, SKILL.md files, gate thresholds, or product policies
were changed. No branch was published.

## Reproductions and narrow corrections

| Defect | Reproduction on baseline | Correction |
| --- | --- | --- |
| Duplicate marketplace names | Insert a second copy of the first entry. Integrity exits 0, while the public-smoke copy loop raises `FileExistsError`. A bad first source is also hidden by a valid later entry. | Reject duplicate names before the name lookup can overwrite an earlier entry. |
| Incomplete skill metadata checks | Supply a YAML list, numeric name, boolean description, or list description with an otherwise valid synthetic body. Lint exits 0. | Initialize every required metadata check to false and validate mapping/string types before evaluation. |
| Git filename quoting bypass | Commit invalid Python in `café.py`, a newline filename, or a carriage-return filename. The entire required-checks CLI exits 0 and reports zero Python files. Quoting also hides private filenames and base skill roots. | Consume NUL-delimited path bytes and decode with the filesystem codec, preserving filenames without text-mode newline conversion. |

Draft PR #27 was checked at `f9a0f80daf03a2ab0dcfe60309ac863b500acae3`.
Its older directory checker and two tests do not reject duplicate names or test
these failures. The new test filename is distinct from that PR's pending file.

## RED and GREEN evidence

- VERIFIED: At tests-only commit `f8adb29`, running
  `python3 -m unittest discover -s .github/tests -p test_validation_integrity.py -v`
  ran 11 tests and failed at 19 assertion sites. The unique marketplace install,
  valid metadata, and existing invalid-input controls passed.
- VERIFIED: At implementation commit `2a0d578`, running
  `python3 -m unittest discover -s .github/tests -v` passed all 16 tests.
- VERIFIED: `python3 -S -m unittest discover -s .github/tests -q` also passed all
  16 tests with site packages disabled. Metadata type tests inject parser return
  values to keep this gate dependency-free; they do not claim to test YAML parsing.
- VERIFIED: Independent CLI checks with the installed PyYAML 6.0.3 exercised real
  YAML parsing. List metadata, numeric names, boolean descriptions, and list
  descriptions changed from exit 0 to exit 1. Valid metadata and a valid inline
  comment stayed at exit 0. Missing negative triggers stayed at exit 1.
- VERIFIED: `python3 scripts/check_repository_integrity.py` passed against the
  actual source tree: eight marketplace plugins, three standalone skills,
  17 READMEs, and four ContextPort paths.
- VERIFIED: The public-smoke copy loop installed all eight actual marketplace
  sources into a disposable directory and found every plugin manifest and skills
  directory.
- VERIFIED: The complete gate passed at implementation commit `2a0d578`:

  ```sh
  python3 .github/scripts/pr_required_checks.py \
    --base 6a8c0d3910e20eb46fac7c9d0172db2730bdac7d \
    --head HEAD --head-ref fix/aipm-validation-integrity-20260923
  ```

  It passed compilation for four changed Python paths, diff checks, privacy
  checks, 16 gate tests, and 107 ContextPort tests. Existing-skill impact was NONE.
- VERIFIED: All repaired gates passed the first implementation attempt. No
  second repair attempt was needed.

## Existing limitations

A baseline-versus-fixed CLI comparison across all 16 tracked SKILL.md files
produced identical lint output. Ten pass; six already fail the current linter:

| Existing skill | Existing failed checks |
| --- | --- |
| prd-first | Trigger phrase; limitations section |
| ai-feature-kill-criteria | Limitations section |
| concise-rewriter | Negative trigger; limitations section |
| context-auditor | Negative trigger; limitations section |
| human-product-writer | Limitations section |
| token-cost-estimator | Trigger phrase; negative trigger; limitations section |

These source-policy inconsistencies remain unchanged and require a separately
scoped decision or repair. Passing repository integrity does not certify every
skill's behavior or claim that all existing skill lint checks pass. This review
does not validate paid model behavior, live integrations, or pending PR content.

The coordinating reviewer must independently review the local change before
publication or merge. A remote draft PR was intentionally not created under the
review instruction to keep the work local.
