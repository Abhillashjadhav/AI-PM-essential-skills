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

## Example

Before:

```text
What most people miss is that AI safety is not a model problem. It is a product architecture problem.
```

After:

```text
AI safety fails when each product flow implements its own rules.

A shared safety layer keeps permissions, access limits, response policies, and escalation behaviour consistent across the product.
```

## Validation fixtures

- [`fixtures/fire.md`](fixtures/fire.md) — should trigger the skill.
- [`fixtures/no-fire.md`](fixtures/no-fire.md) — should not trigger the skill.
- [`fixtures/known-answer.md`](fixtures/known-answer.md) — shows the expected editing behaviour.

## Limits

The skill does not verify facts, predict engagement, replace evidence review, or turn a weak idea into a strong one. It edits supplied writing and preserves accountability with the writer.
