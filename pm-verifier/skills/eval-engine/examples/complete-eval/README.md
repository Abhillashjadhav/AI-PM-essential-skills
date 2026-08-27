# Customer-support repository pilot

This is the first guided, portable AI product package for **AI Evals for PMs**.
It binds one synthetic product identity across:

`PMOS decision → eval contract → Engineering AgentOS contract → candidate + adapter → run evidence → PASS / FAIL / BLOCKED`

The package proves the handoff and verifier mechanics. It does not prove the
quality of an untested repository. It contains no real customer or personal
data, and its reference adapter makes no model or network call.

## What is bound

| Artifact | Authority |
|---|---|
| `contracts/pmos-contract.json` | Approved problem, scope, guardrails, `FR-*`, and `AC-*` intent |
| `contracts/eval-contract.json` | Exact suite, dataset, cases, graders, and FR/AC traceability |
| `contracts/engineering-contract.json` | Exact PMOS/eval digests, checkpoints, and required evidence |
| `product-package.json` | Product identity, all three contracts, candidate tree, adapter, pilot config, CI, and verifier tool |
| `run.json` and `trials.jsonl` | Candidate-bound execution and observed four-surface evidence |

`tools/repository_pilot.py` provides three skill-owned operations without
changing the stable public `pm-verifier` CLI:

- `create` copies this one canonical template and refuses an existing target;
- `bind` validates approved intent and writes the digest chain deterministically;
- `verify` is read-only and rejects stale, ambiguous, escaped, or tampered inputs.

## Verify and run the canonical package

After installing `pm-verifier`, run from this directory:

```bash
python3 tools/repository_pilot.py verify --project .
pm-verifier execute --project . \
  --trials-out trials.executed.jsonl --results-out results.json \
  -- python3 reference_adapter.py
pm-verifier report --results results.json --out report.md
pm-verifier inspect --results results.json \
  --trials trials.executed.jsonl --trial SUPPORT-100-t1
```

The canonical summary is `GO`, 3 requirements, 3 acceptance criteria, 2
representative cases, 24 deterministic graders, and 4 checked-in trials. The
known-good evidence returns `PASS`.

The suite promises durable preference behavior through `state_contract`, so
memory evidence is required. Remove the memory surface and state contract when
a real product makes no persistence promise.

Named mutations in `faults/specs.json` cover system discovery, incomplete
workflow, identity, content cross-wire, wrong path, silent disappearance,
missing system evidence, forgetting, isolation, staleness, conflict resolution,
temporal order, and missing memory evidence.

For a second repository, follow the complete adaptation and first-evidence
sequence in [`../../references/repository-pilot.md`](../../references/repository-pilot.md).
