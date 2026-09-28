# Catalog grader — marketplace-d4-d2-v1

This reference preserves the internal-metadata boundary and repairs optional-field withholding and parent links. It does not train or call a model.

Run:

    python3 run_checks.py

Python standard library only. Reports include the actual environment and per-check results. The original v1 checker is baseline_v1.py; the prior v2 checker is baseline_v2.py. Both are preserved unchanged.

## Result

Re-run on 2026-09-28: 3/3 approved judgments, 12/12 original faults,
55/55 revision checks and 31/31 metadata/payload checks matched.
`run_checks.py` exits 0. Six publication regression tests also pass.
The repair record explains the two corrected fixture shapes and added controls.
All 30 saved candidate outputs are accepted. These are development checks and
replay, not a measured model score. Metadata checks compare the decision,
supplier guidance and publication data before and after metadata changes.

## Internal versus published

Arbitrary company data can be placed in internal_metadata at the submission or record level. notes, confidence, _debug, warnings and timestamps are also accepted there. They cannot change grading, create public claims, approve a block or trigger an action.

The new publication_payload output is an explicit projection of checked catalog information. Integrations must use that projection rather than forwarding the raw candidate. The package itself publishes nothing and runs no downstream actions. These protections do not claim to control external systems that independently read raw private notes.

Supported extra descriptions remain allowed in fields with evidence. Unknown factual keys on product surfaces are still rejected. A key named notes inside customer-facing display is not exempt.

## Still pending

The 98% publication correctness / 0.5% wrong-rejection targets are not established by these checks. Later grader PRs contain additional adjudication and sealed-case work; this repair does not import or certify it. No fresh model call occurred.

See [SETUP.md](SETUP.md) for source authority setup and [DIVERGENCES.md](DIVERGENCES.md) for known gaps. Independent adjudication remains pending.
