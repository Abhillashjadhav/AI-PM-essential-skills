# PDC repository-pilot compatibility — F-02

## Finding and boundary

The repository pilot required a synthetic `schema_version="1.0"`,
`decision="GO"`, `requirements[].intent`, and AC `requirement_ids` document.
The real PMOS publisher produces ProductDecisionContract v1 with
`contract_version=1`, `contract_status="APPROVED"`, `functional_requirements`,
and AC `requirement`/`criterion` fields. The unchanged PMOS health fixture failed
before repair with `PMOS contract schema_version must be '1.0'`.

The adapter now validates and binds actual PDCs without changing their bytes.
It preserves native source identity separately from the configured candidate
product ID and labels the existing synthetic dialect explicitly. The verifier
runtime, catalog grader, frozen PMOS contracts, and product policy are unchanged.
The four checked-in synthetic trials were re-executed locally because the
tool's bound digest changed; stale trial provenance was not relabeled.

PDC binding requires supported version/approval fields, required field shapes,
unique IDs, complete and relationally correct FR/AC/case/grader coverage, and no
unresolved product-critical questions. It rejects mixed dialects and duplicate
JSON keys. Optional gate `acceptance_criterion_refs` are checked against actual
AC IDs. Described gates remain source intent at this boundary; this adapter does
not execute them, authenticate an approval receipt, or claim release authority.

## Source and fixture provenance

- Repository base: PR 57 commit `3d5fb2b5ea200b93cccc7695e4d0258691fa5ac5`.
- Exact base tree: `3e9cdc2d01dd28d8022d13380b7d4209c335d587`.
- All 428 source blobs were materialized and checked against their Git blob
  hashes, including four binary fixtures fetched as base64. `git write-tree`
  reproduced the exact base tree before any edits. The original commit object
  was also recovered with its original `+0530` author/committer offsets.
- `tests/eval-engine/fixtures/pmos-pdc-v1.json` is a byte-for-byte copy of PMOS
  `tests/decision-to-contract/valid-contract.json`; SHA-256
  `0339adbc2c54acf58646ecbdd2e76d53e659e4c0999a19706ed81506ca4797d7`.
- The current PMOS PR 58 frozen Task Tracker contract was additionally validated
  read-only: SHA-256
  `41f93f23ca57cef11201fe685b18d66be882c122e5a3c7192e37e9018de0f0e2`,
  six requirements, fourteen criteria, five gate descriptions. This confirms
  adapter acceptance, not execution or release readiness.

## Test evidence

Prompt and regression commits precede the implementation commit. The new tests
first produced four errors and one failure in the 24-test repository-pilot
suite. After repair, all 24 pass. The exact health fixture maps to `FR-001` and
`AC-001` without inventing a product-ID equivalence. A synthetic support PDC
derived from the existing support intent also passes bind → execute → verify →
standalone evaluation. Negative tests cover each missing required field,
unsupported/boolean versions, malformed shapes, unapproved status, duplicate or
unknown IDs, unresolved critical questions, invalid optional gate refs, source
intent/approval tampering, and duplicate JSON keys.

Commands run:

```bash
python -m unittest discover -s tests/eval-engine -p test_repository_pilot.py -v
python -m unittest discover -s tests/eval-engine -p 'test_*.py' -v
python scripts/check_repository_integrity.py
python tests/lint_skill.py pm-verifier/skills/eval-engine/SKILL.md
git diff --check
```

Results: **101/101 verifier tests pass**, including all 24 repository-pilot
tests; repository integrity, skill lint, and diff whitespace checks pass.
No production dependency, model call, paid execution, or remote write was used.

Full RED/GREEN logs and source verification are under
[`pdc-alignment-20260924/`](pdc-alignment-20260924/). Independent root review is
required before publication or merge.
