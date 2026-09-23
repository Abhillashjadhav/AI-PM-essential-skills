# JSON array membership gate evidence

Status: VERIFIED by offline synthetic regression tests. This is implementation
evidence, not the independent PR review or a release approval.

## Finding

At upstream main `60b61efb1294c10045f6af11ff07ce5aea5bb03b`, a configured
`contains_all` safety gate requiring `[{"approved": true}]` passed against an
actual array containing `[{"approved": 1}]`. The complete regression evaluator
returned `PASS` with no failed gate IDs. Python's membership operation used
boolean/numeric equality, including inside nested JSON values.

The existing `_json_equal` helper already distinguishes booleans from numbers
for exact-value gates. The correction reuses it for array members and preserves
the existing behavior for strings and object keys. No schemas, thresholds,
release rules, golden fixtures, or skill instructions changed.

## Before and after

The unmodified harness suite passed 92 tests. Tests were committed before the
implementation in `8e2d9bd`. The focused new tests produced seven failures:
six primitive/nested boolean-versus-number mismatches falsely passed, and the
complete evaluator returned `PASS` where the regression expected `FAIL`.

```text
PYTHONPATH=tests/eval-engine python3 -m unittest \
  test_pm_verifier.PMVerifierTest.test_array_membership_distinguishes_booleans_from_numbers \
  test_pm_verifier.PMVerifierTest.test_typed_array_member_mismatch_fails_the_release_gate -v

Before: Ran 2 tests; FAILED (failures=7)
After:  Ran 2 tests; OK
```

The positive controls preserve exact boolean/nested matches, null members,
numeric `1`/`1.0` equivalence, string substring membership, and object-key
membership. The complete evaluator rejects the numeric substitute and accepts
the corresponding boolean evidence under the same suite and release rules.

One implementation attempt was required; no repair retry was used.

## Verification

```text
python3 -m unittest discover -s tests/eval-engine -p 'test_*.py' -q
Ran 94 tests in 3.633s — OK

python3 tests/lint_skill.py pm-verifier/skills/eval-engine/SKILL.md
All 9 lint checks PASS

python3 scripts/check_repository_integrity.py
REPOSITORY INTEGRITY: PASS

git diff --check
PASS
```

The `ERROR: fault output ...` lines during the unittest run are expected stderr
from existing negative CLI tests; the suite exited successfully.

All examples used repository synthetic data. No live model, network, paid call,
or external publication was used. These results establish deterministic harness
behavior only.
