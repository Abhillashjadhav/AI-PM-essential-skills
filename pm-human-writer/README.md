# PM Human Writer

A reusable Claude Code plugin for people who want sharper product writing without losing their own voice.

It supports two connected jobs:

1. Build a portable voice profile from user-supplied writing evidence.
2. Apply that profile to drafts or supplied source material with minimum effective editing.

## Install

```bash
claude plugin marketplace add Abhillashjadhav/AI-PM-essential-skills
claude plugin install pm-human-writer@ai-pm-skills
```

## Build a voice profile

Supply representative samples with stable IDs and ask:

```text
Use human-product-writer to build a voice profile from these prompts,
published posts, and draft-to-final edit pairs.
```

The strongest calibration inputs are the user's own draft-to-final edits and explicitly representative final writing. Raw prompts help recover thinking voice, but they do not automatically define publishing voice. AI drafts count as positive evidence only when the user explicitly accepted them unchanged.

The skill returns a portable profile using the [voice-profile schema](skills/human-product-writer/references/voice-profile.md). Sparse or conflicting evidence remains `provisional`; the skill does not invent certainty.

Raw samples, conversations, names, private metrics, and sensitive anecdotes are excluded from the profile. Save a personal profile only to a user-approved private location. Never commit personal samples or profiles to this public plugin.

## Apply a voice profile

Provide a draft or source article together with a profile:

```text
Use this voice profile to edit the LinkedIn draft. Preserve the facts and
product judgment. Make the minimum change and return it unchanged if it
already fits.
```

The result contains:

1. A complete edited draft.
2. A short `What changed` section.
3. No invented metrics, customer stories, personal experience, credentials, or source claims.

A voice profile controls style; it is never factual evidence. Numbers, mechanisms, quotations, results, and causal claims must remain traceable to supplied material. Missing proof stays visible as `[SOURCE NEEDED]` or `[METRIC NEEDED]`.

## What makes it different

Most rewriting prompts optimize for polish. PM Human Writer separates durable voice signals from accidental roughness.

It preserves:

- reasoning and decision order;
- product judgment and trade-offs;
- vocabulary, cadence, restraint, and uncertainty supported by accepted work;
- factual and structural evidence boundaries.

It cleans:

- typos and transcription errors;
- filler, abandoned starts, and duplicated clauses;
- generic AI-writing patterns;
- inflated language and fake-profound endings.

The plugin does not preserve roughness merely because it appeared in a raw prompt. It looks for repeated, accepted choices across stronger evidence.

## Basic edit without a profile

Paste a draft and ask:

```text
Use human-product-writer on this LinkedIn post.
```

The skill protects signals observable in the supplied draft without claiming deep personalization.

## Pipeline use

When another anti-slop editor runs first, use PM Human Writer as the later voice-fidelity pass:

```text
draft → anti-slop edit → PM Human Writer → factual/evidence/anti-slop rechecks
```

Later edits can reintroduce earlier failures. Re-run all factual, privacy, evidence, and anti-slop gates after the voice pass, and preserve claim IDs when the pipeline supplies them.

## Outcome contract

The primary outcome is that the writer would publish or send the result unchanged.

- Leading measures: editing time and edit distance.
- Guardrails: factual accuracy, privacy, and evidence traceability.

The plugin cannot claim success until the writer actually accepts the result. It does not predict engagement or AI-detector behavior.

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

The repository includes 11 synthetic contract cases:

- five rewrite cases covering trigger, no-trigger, fact preservation, anti-invention, banned-pattern removal, placeholders, and minimum editing;
- six voice cases covering mixed-source calibration, sparse evidence, source weighting, signal-versus-roughness separation, privacy, and profile-guided minimum editing.

Run the dependency-free check:

```bash
python3 scripts/check_pm_human_writer_contract.py
```

The repository integrity workflow runs the same check on every pull request. Deterministic fixtures validate the written contract and reference outputs; they do not certify identical behavior across every live model or environment.

- [`fixtures/fire.md`](fixtures/fire.md) — complete input that should trigger the editing skill.
- [`fixtures/no-fire.md`](fixtures/no-fire.md) — factual request that should not trigger.
- [`fixtures/known-answer.md`](fixtures/known-answer.md) — evidence-bounded reference edit.
- [`fixtures/validation-cases.json`](fixtures/validation-cases.json) — machine-checked rewrite cases.
- [`fixtures/voice-profile-cases.json`](fixtures/voice-profile-cases.json) — machine-checked voice cases.

## Limits

The skill does not verify external facts, infer personality or demographics, predict engagement, detect AI authorship, replace evidence review, or turn a weak idea into a strong one. It structures voice evidence and preserves accountability with the writer.

## Licence

Released under the repository's [MIT License](../LICENSE).
