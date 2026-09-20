---
name: human-product-writer
description: Use this skill when the user wants to build or refresh a reusable writing-voice profile from supplied samples, or rewrite, adapt, sharpen, humanize, or de-slop product writing such as LinkedIn posts, product memos, launch notes, strategy updates, PRDs, emails, or executive summaries. Preserve the writer's point, evidence, vocabulary, cadence, uncertainty, and product judgment without preserving typos or accidental roughness. Do not use for factual research alone, a brand-new document without source material or voice evidence, generic grammar checks, or AI-authorship detection.
---

# Human Product Writer

Calibrate a portable voice profile or edit product writing so the result carries the writer's judgment and sounds natural rather than generically polished.

## Choose the mode

- **Calibrate:** build, refresh, compare, or validate a voice profile from user-supplied samples. Read [references/voice-profile.md](references/voice-profile.md) before producing the profile.
- **Apply:** use a supplied voice profile to edit a draft or adapt supplied source material.
- **Basic edit:** when no profile is supplied, protect the strongest signals observable in the draft without claiming deep personalization.

Do not silently treat assistant-written or AI-generated text as the user's voice. It becomes positive evidence only when the user explicitly accepted it unchanged or their final edits establish what they kept.

## Shared boundaries

Treat supplied source material as the factual boundary.

- Every number, named mechanism, quotation, customer result, causal claim, personal experience, credential, and product outcome in edited writing must be traceable to supplied material.
- A voice profile controls style and judgment expression; it is never factual evidence.
- Preserve claim IDs, citations, placeholders, and evidence mappings when supplied.
- Reordering, compressing, translating, and clarifying supplied claims is allowed. Adding factual content is not.
- Keep missing proof visible as `[SOURCE NEEDED]` or `[METRIC NEEDED]`.
- Never turn an assumption into a result or a placeholder into a plausible detail.
- Do not guess whether text was written by AI or promise that detectors, readers, or platforms will classify it as human.

## Calibration mode

Use only samples the user supplied or explicitly authorized.

### Weight the evidence

Prefer evidence in this order:

1. Draft-to-final pairs showing the user's own edits and explicit accept/reject feedback.
2. Multiple final or published pieces the user identifies as representative.
3. Raw prompts, transcripts, or messages that show natural reasoning.
4. AI drafts and reference copy, which are negative or neutral evidence unless explicitly accepted.

Final writing reveals publishing voice; prompts reveal thinking voice. Keep the distinction visible. When sources conflict, prefer explicit current instructions, then the higher-ranked source. Report material conflicts instead of averaging them away.

### Separate signal from roughness

Preserve durable choices such as:

- causal and decision structure;
- directness, restraint, uncertainty, humour, or technical depth;
- sentence-length variation and spoken cadence;
- recurring transitions or framing moves;
- preferred mechanisms, trade-offs, examples, and endings;
- vocabulary the writer repeatedly chooses in accepted work.

Clean accidental noise such as:

- typos and transcription errors;
- filler and abandoned starts;
- duplicated clauses;
- broken grammar that obscures meaning;
- inconsistent formatting not repeated in accepted work.

Do not infer demographics, personality, expertise, or identity from language. Do not convert one memorable phrase into a universal rule.

### Confidence and privacy

- Support every profile signal with sample IDs, not private quotations.
- Mark a signal `observed` only when at least three independent positive samples support it without strong counterevidence. Otherwise mark it `provisional`.
- Mark the whole profile `calibrated` only when at least three observed signals span at least two positive source types; otherwise mark it `provisional`.
- Do not persist raw conversations, full samples, names, customer details, private metrics, or sensitive anecdotes in the profile.
- If the user asks to save a profile, use a user-approved private location. Never add personal samples or profiles to a public skill or fixture repository.

Return the portable profile defined in the reference, followed by a short evidence-gap note. Do not write the profile as flattering personality analysis.

## Apply mode

Before editing:

1. Read the full draft, supplied evidence, current instruction, and voice profile.
2. Identify the core judgment, strongest fact or mechanism, intended reader outcome, and applicable profile signals.
3. Resolve conflicts in this order: current user instruction, factual evidence, accepted voice signals, provisional signals.
4. Decide whether any edit is necessary.

Apply the smallest change that improves voice fidelity or clarity.

- Preserve meaning, evidence, vocabulary, directness, and useful cadence.
- Correct accidental roughness without flattening the writer's reasoning.
- Use provisional signals lightly.
- Never force every signature move into one piece.
- If the draft already fits the profile and passes the checks, return it unchanged.
- When adapting an article or other supplied source, express its supported ideas in the writer's structure without claiming the writer personally experienced or discovered them.
- If no usable profile exists, say the edit is draft-grounded rather than personally calibrated.

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
- abstract claims when the supplied material contains a concrete mechanism, number, decision, failure, or trade-off.

A profile does not authorize a banned pattern merely because one raw prompt contains it. Preserve an intentional recurring move only when accepted final work supports it and it remains clear.

## Product-writing rules

1. Lead with the strongest true tension, decision, result, or surprising fact.
2. Make the product judgment explicit. The reader should know what the writer would build, stop, measure, or change.
3. Protect mechanisms and trade-offs. Do not smooth them into broad leadership language.
4. Prefer active voice and direct verbs.
5. Keep one central idea per short post or message.
6. Use technical language only when it adds precision; explain it in ordinary language when a wider audience needs it.
7. End on a concrete consequence, decision, or next action. Do not manufacture a profound closer.
8. Make the minimum effective edit.

## Hook check for short public posts

The first two lines must pass all five checks:

1. The tension is understandable without specialist context.
2. The claim is supported by supplied evidence.
3. Curiosity comes from a real contradiction, consequence, failure, number, or decision.
4. The next paragraph pays off the hook immediately.
5. The hook would remain interesting without a famous company name.

If the hook fails, rewrite the opening before editing the rest.

## Pipeline use

When this skill follows an anti-slop editor, treat it as the voice-fidelity pass. Run factual, evidence, privacy, and anti-slop checks again after any change because a later edit can reintroduce an earlier failure. Preserve all structural claim IDs across the pass.

## Final checks

Edited writing must pass every check:

- Every factual detail is traceable to supplied material.
- No invented facts, numbers, examples, experience, credentials, or opinions.
- Unsupported evidence requests remain visible.
- Core product judgment remains explicit.
- Strong concrete details and structural evidence IDs remain intact.
- Applied voice signals are supported by the profile.
- Accidental roughness is cleaned without genericizing the reasoning.
- No banned pattern, fake-profound ending, or repetitive robotic rhythm remains.
- The result sounds natural when read aloud.
- For a short public post, the hook passes all five hook checks.

If any check fails, revise again.

## Output

For calibration:

```text
<portable voice profile>

Evidence gaps
- <important missing or conflicting evidence>
```

For writing:

```text
<complete edited draft>

What changed
- <specific edit>
- <specific edit>
```

If no edit was required, return the draft unchanged and say so plainly.

The primary outcome is that the writer would publish or send the result unchanged. Editing time and edit distance are leading measures; factual accuracy and privacy are guardrails. Do not claim the outcome was achieved without the writer's actual decision.
