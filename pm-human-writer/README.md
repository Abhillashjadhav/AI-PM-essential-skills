# PM Human Writer

A reusable Claude Code plugin for product managers who want sharper writing without losing their own voice.

## Install

```bash
claude plugin marketplace add Abhillashjadhav/AI-PM-essential-skills
claude plugin install pm-human-writer@ai-pm-skills
```

Then paste a draft and ask:

```text
Use human-product-writer on this LinkedIn post.
```

The skill returns the edited draft and a short list of the changes it made.

## What makes it different

Most rewriting prompts optimise for polish. This skill protects the product judgment, concrete evidence, spoken cadence, bluntness, and useful rough edges that make the writer recognisable.

It removes recurring machine-writing patterns such as faux-insight openings, binary contrasts, dramatic fragment stacks, inflated language, decorative lists, and fake-profound endings. It also checks whether a short public post pays off its hook with a real product decision.

## Input and output contract

**Input:** an existing draft, plus audience or intended reader outcome when unclear.

**Output:**

1. A complete edited draft.
2. A short `What changed` section.
3. No invented metrics, customer stories, personal experience, or source claims.

Numbers, mechanisms, quotations, results, and causal claims in the output must be traceable to the supplied draft. Missing proof stays visible as `[SOURCE NEEDED]` or `[METRIC NEEDED]`; the skill does not fill gaps with plausible details.

## Example

Before:

```text
An AI feature is a product system, not just a model. A model demo can pass while the full product workflow still fails.

Our evaluation must cover inputs, tool calls, failure handling, latency, cost, and whether the user reaches the intended outcome.
```

After:

```text
An AI feature can pass a model demo and still fail across the product workflow.

Evaluate the inputs, tool calls, failure handling, latency, cost, and whether the user reaches the intended outcome.
```

## Validation

The repository includes five synthetic contract cases covering trigger, no-trigger, fact preservation, anti-invention, banned-pattern removal, and minimum-edit behaviour.

Run the dependency-free check:

```bash
python3 scripts/check_pm_human_writer_contract.py
```

The repository integrity workflow runs the same check on every pull request. The cases validate the written contract and reference outputs; they do not certify identical behaviour across every live model or environment.

- [`fixtures/fire.md`](fixtures/fire.md) — complete input that should trigger the skill.
- [`fixtures/no-fire.md`](fixtures/no-fire.md) — factual request that should not trigger the skill.
- [`fixtures/known-answer.md`](fixtures/known-answer.md) — evidence-bounded reference edit.
- [`fixtures/validation-cases.json`](fixtures/validation-cases.json) — machine-checked contract cases.

## Limits

The skill does not verify external facts, predict engagement, replace evidence review, or turn a weak idea into a strong one. It edits supplied writing and preserves accountability with the writer.

## Licence

Released under the repository's [MIT License](../LICENSE).
