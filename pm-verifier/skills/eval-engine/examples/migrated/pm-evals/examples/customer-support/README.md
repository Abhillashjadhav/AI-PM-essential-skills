# Case study #1 — Brightline customer support

A synthetic but realistic eval set for **Brightline AI**, a hypothetical
project-management SaaS whose support chatbot answers questions over chat,
email, and in-app channels. 500 traces, a 10-criterion plain-English rubric,
and a known ground-truth label on every trace so you can check pm-evals against
the answer key.

## What this simulates

A production customer-support assistant with RAG. ~75% of traces include
`retrieved_context` (3-5 passages of real Brightline docs). Conversations span
14 product topics: project setup, billing, the Slack/Jira/Linear/GitHub
integrations, team management, time tracking, reports, the mobile app, API
usage, custom workflows, webhooks, and automations.

- **350 single-turn** traces and **150 multi-turn** traces grouped into ~50
  conversations of 2-4 turns (`conversation_id` / `turn_index`).
- Multi-turn realism: ~10 conversations exhibit **drift** (the agent forgets
  earlier context and answers a different topic), and ~20 conversations contain
  follow-ups that **require earlier context** to make sense ("what about the
  second option you mentioned earlier?").
- Metadata on every trace: `channel`, `user_tier`, `response_latency_ms`,
  `model`, plus a `quality_label` ground-truth tag and the `topic`.

## Where each failure mode appears

`metadata.quality_label` tags the intended failure mode of each trace. The
named failure buckets are exact; the high-quality bucket fills the remainder
(nominally 200, trimmed so the buckets sum to 500). Drift turns are relabeled
`off_topic`, which is why the realized counts shift a little from the nominal:

| Label | Nominal | What it demonstrates |
|---|---:|---|
| `high_quality` | 160 | Grounded, on-topic, complete answers |
| `off_topic` | 100 | Drift away from the user's actual question |
| `hallucination` | 80 | Fake "Project Phases", invented Asana sync, wrong pricing |
| `refusal` | 50 | Over-cautious refusals of benign, in-scope asks |
| `sycophancy` | 40 | Excessive apology, flattery, reflexive agreement |
| `injection` | 30 | Prompt-injection attempts correctly ignored |
| `pii` | 20 | PII reflected back (email, card, phone, address) |
| `tone` | 20 | Register mismatched to channel/tier |

The hallucinations target specific, checkable fabrications — a fake **Project
Phases** feature, a hallucinated **Asana** integration, a non-existent
**Growth** plan, and wrong pricing — so you can verify whether your judge
catches concrete factual errors, not just vibes.

## Rubric

See `rubric.md` — ten criteria covering on-topic, no fabricated features,
context citation, appropriate refusal, no sycophancy, no PII reflection, tone
match, task completion, calibrated confidence, and safety.

## Run it

```bash
pm-evals score   --traces examples/customer-support/traces.jsonl \
                 --rubric examples/customer-support/rubric.md \
                 --out cs_results.json
pm-evals cluster --results cs_results.json
pm-evals report  --results cs_results.json \
                 --rubric examples/customer-support/rubric.md \
                 --cluster --out cs_report.md
```

> The bundled `stub` judge is deterministic and prompt-hashed — great for
> exercising the pipeline, but **not a real quality signal**. For real numbers,
> run `--judge claude` inside a Claude Code session (see `pm_evals/scorer.py`).

## Suggested experiments

1. **Judge agreement vs ground truth.** Score with `--judge claude`, then
   compare per-trace pass/fail against `metadata.quality_label`. Which failure
   modes does the judge miss?
2. **Does retrieval help?** Split by presence of `retrieved_context` and compare
   the `cites retrieved context` and `no fabricated features` pass rates.
3. **Multi-turn vs single-turn.** Compare pass rates on `conversation_id`
   starting with `conv_` (multi-turn) vs `single_`. Does drift show up as lower
   on-topic scores on later turns?
4. **Tier sensitivity.** Group by `user_tier` — is tone-match worse for one tier?
5. **Cluster recovery.** Run `cluster` and check whether the discovered clusters
   line up with the eight ground-truth labels.
