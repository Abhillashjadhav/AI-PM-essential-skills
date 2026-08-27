# Complete four-surface example

This synthetic support workflow shows the end-to-end contract:

`PMOS decision contract → engineering contract → execute → outcome + trajectory + system + memory evidence → PASS / FAIL / BLOCKED`

It contains no real customer or personal data. The adapter is deterministic and does not call a model or network service.

Run it after installing `pm-verifier`:

```bash
pm-verifier execute --project . \
  --trials-out trials.executed.jsonl --results-out results.json \
  -- python3 reference_adapter.py
pm-verifier report --results results.json --out report.md
pm-verifier inspect --results results.json \
  --trials trials.executed.jsonl --trial SUPPORT-100-t1
```

The suite promises durable preference behavior through `state_contract`, so memory evidence is required. Remove the memory surface and state contract when a product makes no persistence promise.

Named mutations in `faults/specs.json` cover system discovery, incomplete workflow, identity, content cross-wire, wrong path, silent disappearance, missing system evidence, forgetting, isolation, staleness, conflict resolution, temporal order, and missing memory evidence.
