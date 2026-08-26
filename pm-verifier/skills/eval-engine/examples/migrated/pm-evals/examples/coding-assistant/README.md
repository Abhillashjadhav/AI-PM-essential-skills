# Case study #2 — Coding assistant

500 synthetic traces from an AI pair-programmer working across six languages —
**Python, JavaScript, TypeScript, Go, Rust, and SQL** — split roughly evenly.
Each trace pairs a request and input `code_snippet` with the assistant's
`generated_code` and an `expected_behavior` description, plus a ground-truth
`quality_label`.

## Schema (in addition to the common trace fields)

- `language` — one of python/javascript/typescript/go/rust/sql
- `task_type` — bug_fix / new_feature / refactor / explain / test
- `code_snippet` — the input the user provided
- `generated_code` — the assistant's output (10-80 lines)
- `expected_behavior` — what a correct answer should do

## Quality distribution (ground truth in `metadata.quality_label`)

| Label | Count | What it demonstrates |
|---|---:|---|
| `correct` | 160 | Idiomatic code that runs and solves the task |
| `subtle_bug` | 100 | Plausible code with off-by-one, wrong var, or deprecated API |
| `hallucinated_lib` | 80 | Calls to packages/methods that do not exist |
| `overconfident_wrong` | 50 | Confident framing wrapped around a real bug |
| `incomplete` | 40 | Signature plus `TODO` / `NotImplementedError` |
| `wrong_question` | 30 | Correct explanation of the *wrong* concept |
| `security` | 20 | SQLi, `eval`, hardcoded secrets, log/format-string injection |
| `outdated` | 20 | Python 2 `print`, `var`/`arguments`, React class components, `ioutil` |

The named buckets sum to exactly 500; `correct` was trimmed from a nominal 200
so the totals balance.

## What this case study reveals about evaluating code-gen LLMs

Code is the domain where **"looks right" and "is right" diverge most sharply**.
A subtle off-by-one or a `% 2 == 1` typo reads as fluent, idiomatic code — a
human reviewer skimming 80 lines will nod past it. The hard failure modes here
aren't ugly code; they're *confident, well-formatted wrongness*:

- **Hallucinated libraries** pass every stylistic check and only fail at import
  time — a judge that doesn't actually know the language's ecosystem will miss
  them.
- **Security anti-patterns** (`eval`, string-built SQL) are often the *shortest,
  clearest* way to express the intent, so quality-by-readability scores them
  well. They need a dedicated criterion.
- **Right-but-wrong-question** answers are individually flawless and globally
  useless — they expose whether your judge checks the response against the
  *request*, not just against "is this good code?".

These are exactly the failures that erode trust in a coding assistant, and
exactly the ones a naive thumbs-up/thumbs-down metric hides.

## Run it

```bash
pm-evals score   --traces examples/coding-assistant/traces.jsonl \
                 --rubric examples/coding-assistant/rubric.md \
                 --out ca_results.json
pm-evals cluster --results ca_results.json
pm-evals report  --results ca_results.json \
                 --rubric examples/coding-assistant/rubric.md \
                 --cluster --out ca_report.md
```

> The `stub` judge is deterministic and offline (not a real quality signal).
> For meaningful scores, run `--judge claude` in a Claude Code session.

## Suggested experiments

1. **Per-language pass rates.** Group by `language` — does the judge catch
   hallucinated crates in Rust as reliably as fake npm packages in JS?
2. **Security recall.** Filter to `quality_label == "security"` and check the
   `no security anti-patterns` criterion. A judge that misses these is unsafe to
   ship behind.
3. **Bug detection vs style.** Compare `runs without errors` pass rate on
   `subtle_bug` vs `correct`. How much does fluent formatting mask real bugs?
4. **Explanation faithfulness.** On `wrong_question` traces, does
   `explanation matches implementation` correctly fail?
5. **Cluster the failures** and see whether "hallucinated API", "security", and
   "incomplete" emerge as distinct bottom-up clusters.
