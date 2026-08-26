# Case study #3 — Summarization agent

500 synthetic traces from an AI summarizer working over five source types:
**meeting transcripts, email threads, articles, research papers, and Slack
threads**. We synthesized **30 unique source documents** (903-4395 words) and
generated multiple summarization attempts per source, each tagged with a
ground-truth `quality_label`.

Every trace embeds its full source document in `retrieved_context`, so the set
is self-contained: a faithfulness judge has the exact ground truth to check the
summary against. The 30 sources are also written to `sources.jsonl` for
convenience.

## Schema (in addition to the common trace fields)

- `source_type` — meeting_transcript / email_thread / article / research_paper / slack_thread
- `source_length_words` — word count of the source
- `summary_length_words` — word count of the produced summary
- `compression_ratio` — summary length / source length
- `source_id` — which of the 30 sources this trace summarizes

## Quality distribution (ground truth in `metadata.quality_label`)

| Label | Count | What it demonstrates |
|---|---:|---|
| `faithful` | 160 | Concise, accurate, correctly emphasized |
| `omission` | 100 | Drops the key decision/finding |
| `fabrication` | 80 | Asserts a fact (budget, hire) not in the source |
| `wrong_emphasis` | 50 | Leads with a detail, buries the decision |
| `over_long` | 40 | Restates the source — no compression value |
| `stylistic_mismatch` | 30 | Formal summary of casual content (or vice versa) |
| `unattributed_quote` | 20 | Presents a paraphrase as a verbatim quote |
| `hallucinated_participant` | 20 | Adds a person who was never present |

Each source carries explicit `key_decision`, `key_facts`, `participants`, and a
`real_quote`, which is exactly what the failure generators violate — so the
failures are *checkable*, not subjective.

## Why summarization eval is uniquely hard

Summarization has **no single reference answer**. Two faithful summaries can
share zero sentences, so string-overlap metrics (ROUGE/BLEU) reward surface
similarity rather than truth — a fluent fabrication can out-score a terse,
correct summary. The failure modes here are *relational*: they only exist
relative to the source.

- **Omissions** are invisible without reading the source — the summary itself
  looks complete and well-formed.
- **Fabrications** are the inverse: every sentence is grammatical and plausible;
  only cross-checking against the source reveals the invented budget or hire.
- **Wrong emphasis** produces a summary where every individual fact is true but
  the *gestalt* is misleading — the hardest case for any rubric.

### Why human-as-judge struggles here

To judge a summary, a human reviewer must **re-read the entire source** —
otherwise they're scoring fluency, not faithfulness. That makes human eval
slow, expensive, and inconsistent: reviewers anchor on whether the summary
"reads well", miss quiet omissions, and disagree on emphasis. This is precisely
the setting where a source-grounded LLM judge with an explicit rubric can be
*more* consistent than a hurried human — and where pm-evals' "cite the source"
and "no fabrication" criteria earn their keep.

## Run it

```bash
pm-evals score   --traces examples/summarization/traces.jsonl \
                 --rubric examples/summarization/rubric.md \
                 --out sm_results.json
pm-evals cluster --results sm_results.json
pm-evals report  --results sm_results.json \
                 --rubric examples/summarization/rubric.md \
                 --cluster --out sm_report.md
```

> The `stub` judge is deterministic and offline (not a real quality signal).
> Run `--judge claude` in a Claude Code session for meaningful scores.

## Suggested experiments

1. **Faithfulness vs fluency.** On `fabrication` traces, check the
   `factual accuracy` criterion. Does the judge catch invented facts, or reward
   fluent prose?
2. **Compression sanity.** Plot `compression_ratio` against the `appropriate
   compression ratio` pass rate — does the judge flag `over_long` summaries?
3. **Emphasis detection.** Compare `correct emphasis hierarchy` pass rate on
   `wrong_emphasis` vs `faithful`. This is the subtlest criterion.
4. **Quote integrity.** Filter to `unattributed_quote` and check the
   `attributes quotes correctly` criterion.
5. **Per-source-type difficulty.** Group by `source_type` — are research papers
   harder to summarize faithfully than Slack threads?
