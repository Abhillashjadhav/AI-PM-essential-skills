# AI ticket-summarizer eval starter

Copy this directory when you want to turn one AI feature specification into a
runnable local evaluation.

This use case evaluates only `outcome` and `trajectory`. The product does not
promise a multi-stage system contract or persistent memory, so those surfaces
are deliberately absent.

## What ships

- `EVAL_CONTRACT.md` — the PM-readable contract to replace with your feature;
- `suite.json` — eight deterministic release gates;
- `cases.jsonl` — three synthetic ticket threads;
- `reference_adapter.py` — a dependency-free JSON-over-stdio adapter;
- `faults/specs.json` — fabricated-claim, missing-escalation, and wrong-order faults;
- `tools/demo.py` — one command that produces a real FAIL and repaired PASS.

## Run the use case

From the repository root:

```bash
python3 -m pip install --no-deps ./pm-verifier
python3 pm-verifier/skills/eval-engine/examples/ticket-summarizer-starter/tools/demo.py
```

The demo works in a temporary copy. It does not modify the checked-in package.

## Use it for your feature

1. Copy this directory.
2. Replace the product contract in `EVAL_CONTRACT.md`.
3. Replace `cases.jsonl` with real, approved cases and update `dataset.json`.
4. Change `suite.json` only for requirements your product actually promises.
5. Make `reference_adapter.py` expose your real outcome, critical trajectory,
   metrics, environment fingerprint, and a unique isolation ID.
6. Execute the adapter and review `results.json` plus `report.md` before release.

Never rewrite expected answers to fit an existing output. Missing required
evidence must remain `BLOCKED`.

The supplied threads, outputs, latency, tokens, and faults are synthetic. The
adapter makes no model or network call.
