# T-shirt grader v2.1

This update fixes rejection of harmless internal company information. It does not train or call a model.

Run:

    python3 run_checks.py

Python standard library only. Reports include the actual environment and per-check results. The original v1 checker is baseline_v1.py; the prior v2 checker is baseline_v2.py. Both are preserved unchanged.

## Result

All 3 approved judgments, 12 original faults, 52 revision checks and 25 new metadata-boundary checks matched their expectations. All 30 saved candidate outputs still pass. These are development checks and replay, not a measured model score. The 25 new checks compare the full decision, supplier guidance and publication data before and after metadata changes.

## Internal versus published

Arbitrary company data can be placed in internal_metadata at the submission or record level. notes, confidence, _debug, warnings and timestamps are also accepted there. They cannot change grading, create public claims, approve a block or trigger an action.

The new publication_payload output is an explicit projection of checked catalog information. Integrations must use that projection rather than forwarding the raw candidate. The package itself publishes nothing and runs no downstream actions. These protections do not claim to control external systems that independently read raw private notes.

Supported extra descriptions remain allowed in fields with evidence. Unknown factual keys on product surfaces are still rejected. A key named notes inside customer-facing display is not exempt.

## Still pending

The independent reviewer should adjudicate fresh variants; the owner still needs the agreed sample of eight judgments; the nine sealed cases prepared outside this builder thread have been run and none was scored (`EVALUATION_v2.3.md`). The 98% publication correctness / 0.5% wrong-rejection targets are not established by these checks. No fresh Sol, Sonnet, Astra or Fable call occurred.

See REVIEW_WITH_CLAUDE.md for independent execution and SETUP.md for source authority setup.
