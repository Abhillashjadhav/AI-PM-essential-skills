# R4 AIPM repair evidence

## Scoped result

- **F-C5-1:** the portable package and pilot `bind`, `create`, and `verify`
  reports expose top-level `approval_verified:false`, alongside the retained
  source-level flag. `decision` remains a carried publisher declaration;
  `VERIFIED` describes evidence integrity.
- **F-C5-2:** both SEALED and PENDING receipts use the existing canonical JSON
  comparison. A sealed count `4.0` cannot replace integer `4`; pending `0.0` or
  `false` cannot replace integer `0`. Restoring each integer control succeeds.
  The pending boolean case is an additional regression, not a claim that the
  review's void sealed-boolean probe was reproduced.
- **F-C5-3:** the skill and example README describe carried approval declarations
  and integrity checks. PDC `APPROVED`, legacy `GO`, and the existing question
  admission rules remain unchanged; no receipt authentication was added.

The changes are split into BAR/prompt, RED regression, runtime, and wording
commits. Full validation ran on the recorded source tree after the wording
change. Root must independently review before publication.

## Verification

| Check | Exit | Result |
| --- | ---: | --- |
| Pilot regressions before implementation | 1 | 31 tests, 11 failing subcases |
| Pilot regressions after implementation | 0 | 31 tests pass |
| Full bounded verifier suite | 0 | 108 tests pass |
| Required skill lint | 0 | All checks pass |
| Repository integrity | 0 | Pass |
| Canonical pilot CLI verify | 0 | `VERIFIED`, top-level `approval_verified:false` |
| Whole change whitespace / frozen catalog comparison | 0 / 0 | Pass / unchanged |

[validation.json](validation.json) records exact commands, exit codes, source
tree, and tool/skill hashes. The RED log preserves every line with trailing
spaces removed; [red-capture.json](red-capture.json) records its raw hash.
No repair was needed after a failed GREEN gate.

The tool hash changed, so the checked-in four synthetic trials were honestly
re-executed. The first bind left the old trial bytes unchanged and reported
`BOUND`; execution produced fresh trial bytes, and the second bind sealed them.
The [execution log](synthetic-reexecution.log) records both digests and reports.

## Limits

No approval authentication, live-product quality, fresh approved delivery,
publication, merge, deployment, or independent approval is claimed. There were
no model calls, paid execution, new dependencies, or frozen catalog changes.
Existing pilot packages require rebinding and fresh evidence after the bound
tool/package change. Integer receipt counts produced by the binder remain
compatible; previously accepted type aliases are now rejected.
