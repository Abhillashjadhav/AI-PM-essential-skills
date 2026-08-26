# golden/ — judge validation dataset

## What this folder is

A 20-trace **golden subset** sampled from `examples/customer-support/traces.jsonl`,
with a human-grading template, a `golden_scores.json` skeleton, and the schema
that `pm-evals validate-judge` consumes.

## Why it exists

An LLM judge without a meta-eval is "trust me bro." If the judge disagrees with
human graders systematically, every downstream report is unreliable — fluent,
authoritative, and wrong. `validate-judge` measures judge-vs-human agreement on
this golden subset and emits a trust verdict before you run the full eval.

## Files

| File | Role |
|---|---|
| `golden_traces.jsonl` | 20 traces, diverse labels (clear pass, clear fail, borderline). |
| `golden_grading_template.md` | One section per trace; fill 0-5 ints + rationale. |
| `golden_scores.json` | Skeleton scored synthetically so the pipeline runs end-to-end. **Replace with human grades before trusting any result.** |
| `README.md` | This file. |

## How to replace synthetic scores with real ones

1. Open `golden/golden_grading_template.md`.
2. For each of the 20 traces: read input + output, score each criterion `0-5`
   against `examples/customer-support/rubric.md`, write a one-line rationale if
   any criterion is `< 3`.
3. Copy your scores into `golden/golden_scores.json`, replacing each
   `"source": "synthetic_demo"` with `"source": "human"`.
4. `pm-evals validate-judge` will then run; until every entry is human-sourced
   it refuses.

Plan ~30-45 minutes for the one-time grading pass.

## Trust thresholds

`validate-judge` aggregates per-criterion agreement (judge score within `±1` of
human score) into an overall agreement rate and emits a verdict:

| Agreement | Verdict | What to do |
|---|---|---|
| `>= 80%` | **TRUSTED** | Proceed with the full eval. |
| `70-80%` | **MARGINAL** | Review the disagreement cases; refine the rubric or judge prompt; re-validate. |
| `< 70%`  | **NOT TRUSTED** | Do not proceed. Fix and re-validate before reporting any numbers. |

Pass-mismatch metrics (false positive: judge says pass, human says fail; false
negative: the reverse) are reported alongside the headline so you see *how* the
judge disagrees, not just whether.
