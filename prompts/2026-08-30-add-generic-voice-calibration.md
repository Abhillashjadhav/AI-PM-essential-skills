# Prompt: add generic voice calibration to PM Human Writer

Extend the existing `pm-human-writer` plugin without changing its evidence, anti-invention, or minimum-edit guarantees.

Requirements:

- add a generic calibration mode that builds a reusable voice profile from user-supplied prompts, published writing, draft-to-final edit pairs, and explicit feedback;
- keep personal samples and profiles separate from the public plugin and never commit private conversations;
- distinguish durable voice signals from typos, filler, repetition, and broken syntax;
- weight accepted final writing and user edits more strongly than raw prompts or AI drafts;
- mark sparse or conflicting evidence as provisional instead of inventing certainty;
- add an application mode that uses a supplied voice profile to edit drafts or adapt supplied source material;
- preserve factual traceability, placeholders, product judgment, and minimum-effective-edit behaviour;
- define “publish unchanged” as the primary outcome, with editing time/edit distance as leading measures and factual accuracy/privacy as guardrails;
- add dependency-free synthetic contract validation for profile creation, sparse evidence, privacy, source weighting, and voice-guided editing;
- update plugin documentation and metadata without adding production dependencies.

Use only synthetic fixtures. Do not add Abhillash's private prompts, conversations, or voice profile to the repository.
