# Jev pilot diagnostics — implementation brief

## Context and evidence

The owner is testing the router on a Mac. The six built-in public synthetic
prompts completed in 0.4666–0.6484 seconds. Five matched the expected tier.
The ordinary implementation case was middle under local rules but became
`unknown` under the Jev adapter and highest under combined policy. No GPT calls
were made. This is owner-reported live evidence, not independently reproduced.

Issue: https://github.com/Abhillashjadhav/AI-PM-essential-skills/issues/73

The first pilot summary hides the distinction between a provider choice of
unknown and an ordinary choice rejected by our confidence/consequence checks.
The private journal already stores scores. It does not store the original
provider choice. The exact cause of the owner's failure is still UNKNOWN.

## Implement

- Preserve the original provider choice separately from the final classification.
- Include typed score diagnostics in future pilot output.
- Add `python3 model-router/router.py jev report`, reading the existing journal
  only for the six known public pilot prompt hashes. It must not send requests,
  start Codex, resume jobs, read a credential or write local state.
- Preserve legacy compatibility: display saved probabilities/confidence/risk;
  label the missing original choice as unknown, never invent it from an argmax.
- Only emit allowlisted validated fields, not arbitrary record fields, paths,
  prompts, keys, errors or unrelated private task records.
- Prefer the latest attempted record per case, including failed/pending attempts.
  Make ambiguous timestamps visible. Older journals have no run grouping: do not
  claim a combined report represents a single run or fresh accuracy result.
- Add regression tests proving these properties and preserve the failing
  ordinary-code test outcome rather than changing its expected result.

## Do not change

Jev questions/version, confidence thresholds, risk floors, first-chat routing,
thread pins, API deadlines, credit handling and the GPT spend gate remain intact.
Five of six is not passing, and the six-case test cannot certify 95% suitability.
Native Codex composer integration and real GPT execution remain separate work.

Work on a feature branch with a draft PR. Do not merge main. After publication,
have the owner run `jev report` on the Mac to provide the saved numeric evidence.
No new paid or free-credit model request is needed for this diagnostic step.
