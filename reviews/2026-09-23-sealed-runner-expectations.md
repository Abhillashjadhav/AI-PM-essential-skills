# Author review: sealed-case runner expectations

This is an author self-review using the relevant criteria from
`.claude/commands/pr-review.md`. Independent review and human merge approval
remain required; this artifact is not either approval.

PR REVIEW: sealed-case runner schema diagnostics and publication comparison

SPEC COMPLIANCE: PASS

The repair follows `SEALED_CASES.md`: named null-parent assertions require the
SKU to publish; null and empty maps retain distinct meanings; both guidance
shapes remain accepted. A malformed block now marks the case
`CASE_SCHEMA_ERROR` and fails the CLI while other valid measurements retain
their separate denominators. Reporting handles wholly unscored schema errors
without a missing-note crash.

NOVELTY: PASS

This repairs the existing runner. It adds no skill, external surface, grader
policy, owner adjudication, or calibration requirement.

HARD RULES: PASS

The frozen grader, gold expectations, contracts and decisions are unchanged.
Invalid guidance list containers, entries, named pairs and evidence-reference
lists receive schema diagnostics; falsey invalid blocks are no longer skipped.
Valid empty or unasserted guidance still adds no measurement. The report states
that case-author independence is not verified by this runner.

The second review round adds guards for the documented publication-part types
and literal boolean exhaustive flags. Null publication parts remain unasserted;
empty withheld-field lists remain dropped. Non-object raw JSON cases produce
load diagnostics and a JSON receipt instead of crashing.

TESTABILITY: PASS

`finding5_sealed_runner_expectations.py` is picked up by the existing standard
regression discovery. It runs the CLI against temporary synthetic wrappers of
existing S1/S2 development fixtures, checking exit status, JSON output and human
reporting. It does not modify the fixtures or claim new owner approval.

| Verification | Observed result |
|---|---|
| First-round focused RED | Exit 1; 11 methods, 17 failed assertions/subtests |
| First-round focused GREEN | Exit 0; all 11 methods pass |
| Second-round focused RED | Exit 1; 16 methods, 21 failed subtests |
| Second-round focused GREEN | Exit 0; all 16 methods pass |
| `run_checks.py` approved judgments | 3 / 3 |
| `run_checks.py` fault injection | 13 / 13 |
| `run_checks.py` revision checks | 55 / 55 |
| Saved candidate replay | 30 / 30 accepted; development replay only |
| Internal metadata | 31 / 31 |
| Integrated regression scripts | 11 / 11, including the new runner tests |
| Repository integrity | PASS |
| Python compilation and patch whitespace | PASS |

The RED failures establish all four requested defects: the mixed-block false
pass, schema-only report crash, malformed-guidance crash/skip, and missing-SKU
null-parent false pass. The added report wording check also fails before the
repair. Positive controls passed before and after for both guidance shapes,
empty/unasserted guidance, real null-parent publication, and scoped/exhaustive
parent-link behavior.

Independent review of the first repair found that malformed publication parts
could still crash or be coerced, and non-object JSON could crash loading. Those
review findings were reproduced before a second production edit: 15 publication
shape subtests and six raw-case shape subtests failed. The new valid-shape and
valid-mismatch controls passed before and after; all first-round tests remained
green. Total implementation repair attempts: **2**, the stated maximum.

Commands, from the repository root:

```sh
python3 model-grader/reference/catalog/reproductions/finding5_sealed_runner_expectations.py
python3 model-grader/reference/catalog/run_checks.py
python3 scripts/check_repository_integrity.py
python3 -m py_compile model-grader/reference/catalog/run_sealed_cases.py model-grader/reference/catalog/reproductions/finding5_sealed_runner_expectations.py
git diff --check
```

BLOAT: PASS

Changes are limited to the runner, one auto-discovered regression module, the
saved prompt and review evidence. No new dependencies or runner framework.

VERDICT: APPROVE for independent review; not an independent approval.

## Evidence boundary

- VERIFIED: frozen-v2.6 `grader.py` remains git blob
  `2c853009590a386139c6b6cf8623cab2e8693720`, SHA-256
  `d98aecc8c7801049649776ba3d391e977e5a49ebf88ab4a8fa646153edd2cfbb`.
- VERIFIED: no frozen grader, gold, contract, decision, historical evaluation,
  or parent-owned whitespace file appears in the repair diff.
- VERIFIED: the accompanying JSON receipt records exact source and output
  hashes, commands and deterministic counts. Full local run logs were retained
  for the parent reviewer.
- UNKNOWN: actual sealed cases are unavailable. Synthetic regressions and
  existing development replay do not establish independent evaluation,
  behavioral calibration, publication accuracy or wrong-rejection rates.
- VERIFIED: no model calls or remote writes were made for this repair.

The source snapshot is the earlier #56 head documented in the prompt. The
parent reviewer will transplant only this repair onto the newer whitespace-only
#56 head, preserve that head's complete tree and target its existing branch.
