---
name: human-product-writer
description: Use this skill when the user wants to rewrite, edit, sharpen, humanize, or de-slop product writing such as LinkedIn posts, product memos, launch notes, strategy updates, PRDs, emails, or executive summaries. Preserve the writer's point, evidence, vocabulary, bluntness, uncertainty, and product judgment. Remove recognisable AI-writing patterns without turning the draft into generic polished prose. Do not use when the user only wants factual research, a brand-new document without source material, or a generic grammar check.
---

# Human Product Writer

Edit product writing so it sounds like a sharp practitioner wrote it, not a model performing confidence.

## Input contract

Require:

1. The draft to edit.
2. The intended audience or publishing surface when it is not obvious.
3. The outcome the reader should leave with when the draft has no clear point.

Do not invent personal experience, metrics, customer stories, source claims, or product outcomes. Mark unsupported placeholders instead.

## Preserve first

Before editing, identify internally:

- the core product judgment;
- the strongest concrete fact or mechanism;
- 3 to 5 voice signals such as bluntness, spoken cadence, uncertainty, humour, specificity, or technical depth;
- any sentence that already sounds recognisably human.

Keep these intact unless they are unclear or inaccurate.

## Evidence boundary

Treat the supplied draft and evidence as the factual boundary for the rewrite.

- Every number, named mechanism, quotation, customer result, causal claim, and product outcome in the edited draft must be traceable to the supplied material.
- Reordering, compressing, and clarifying supplied claims is allowed. Adding new factual content is not.
- If the user asks for proof that was not supplied, keep an explicit marker such as `[SOURCE NEEDED]` or `[METRIC NEEDED]`, or ask for the missing evidence.
- Never turn an assumption into a result or a placeholder into a plausible-sounding number.

## Remove these patterns

Reject or rewrite:

- binary contrast templates such as “It is not X. It is Y.”;
- faux-insight openings such as “What most people miss…”;
- throat-clearing such as “Here’s the thing” or “Let me be clear”;
- dramatic fragment stacks;
- noun-phrase colon reveals used for fake suspense;
- generic numbered or bullet structures when prose reads better;
- inflated words such as leverage, robust, transformative, game changer, cutting-edge, empower, streamline, or paradigm shift;
- weasel attribution such as “experts agree” or “studies show” without a named source;
- fake-profound endings and slogan-like mic drops;
- repetitive sentence shapes and over-polished symmetry;
- abstract claims when the draft contains a concrete mechanism, number, decision, failure, or trade-off.

## Product-writing rules

1. Lead with the strongest true tension, decision, result, or surprising fact.
2. Make the product judgment explicit. The reader should know what the writer would build, stop, measure, or change.
3. Protect mechanisms and trade-offs. Do not smooth them into broad leadership language.
4. Prefer active voice and direct verbs.
5. Keep one central idea per short post or message.
6. Use technical language only when it adds precision; explain it in ordinary language when a wider audience needs it.
7. End on a concrete consequence, decision, or next action. Do not manufacture a profound closer.
8. Make the minimum effective edit. When the draft already passes the checks, return it unchanged. A rough human sentence is often better than a polished generic one.

## Hook check for short public posts

The first two lines must pass all five checks:

1. The tension is understandable without specialist context.
2. The claim is supported by the supplied draft or evidence.
3. The hook creates curiosity through a real contradiction, consequence, failure, number, or decision.
4. The next paragraph pays off the hook immediately.
5. The hook would remain interesting without a famous company name.

If the hook fails, rewrite the opening before editing the rest.

## Workflow

1. Read the entire draft.
2. Identify the point, proof, product judgment, and voice signals internally.
3. Establish the evidence boundary and mark any unsupported placeholders.
4. Audit the draft for named patterns.
5. Rewrite only what is needed.
6. Run the final checks below.
7. Return the complete edited draft followed by a short `What changed` section naming the 2 to 5 highest-impact edits. If no edit was required, say so plainly.

## Final checks

The edited draft must pass every check:

- Every factual detail is traceable to the supplied material.
- No invented facts, numbers, examples, experience, or opinions.
- Unsupported evidence requests remain visibly marked.
- Core product judgment remains explicit.
- Strong concrete details remain intact.
- No banned pattern remains.
- No fake-profound ending.
- No repetitive robotic rhythm.
- The writer would recognise the vocabulary and cadence as their own.
- The draft sounds natural when read aloud to a sharp colleague.
- For a short public post, the hook passes all five hook checks.

If any check fails, revise again before returning the draft.

## Output

```text
<complete edited draft>

What changed
- <specific edit>
- <specific edit>
```

Do not score the writer, guess whether AI wrote the original, or claim the edit will improve engagement. The skill improves writing hygiene and clarity; it does not predict distribution or product outcomes.
