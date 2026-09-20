# Portable voice profile

Read this reference only when building, refreshing, comparing, or validating a voice profile.

The profile records reusable writing decisions, not raw samples or personality claims. Produce YAML using this schema.

```yaml
voice_profile_version: 1
profile_status: provisional | calibrated
profile_name: <user-chosen neutral label>
target_surfaces:
  - <surface such as LinkedIn, memo, or email>

source_summary:
  draft_final_pairs: <non-negative integer>
  accepted_final_pieces: <non-negative integer>
  raw_prompts_or_transcripts: <non-negative integer>
  accepted_ai_drafts: <non-negative integer>
  excluded_or_uncertain_sources:
    - <source ID and reason>

core_stance:
  description: <how the writer tends to position judgment>
  evidence_ids: [<sample IDs>]
  confidence: provisional | observed

reasoning_pattern:
  description: <typical causal, comparative, narrative, or decision progression>
  evidence_ids: [<sample IDs>]
  confidence: provisional | observed

structure:
  openings:
    prefer: [<supported moves>]
    avoid: [<unsupported or rejected moves>]
  development:
    prefer: [<supported moves>]
    avoid: [<unsupported or rejected moves>]
  endings:
    prefer: [<supported moves>]
    avoid: [<unsupported or rejected moves>]

cadence:
  sentence_pattern: <supported description>
  paragraph_pattern: <supported description>
  transitions:
    prefer: [<supported transitions or transition types>]
    use_sparingly: [<moves that become repetitive>]
  evidence_ids: [<sample IDs>]
  confidence: provisional | observed

lexicon:
  prefer: [<recurring accepted words or word types>]
  avoid: [<rejected or generic words>]
  spelling_or_locale: <only when explicitly requested or repeatedly evidenced>
  evidence_ids: [<sample IDs>]
  confidence: provisional | observed

signature_moves:
  - move: <one optional recurring writing decision>
    use_when: <context where it helps>
    avoid_when: <context where it becomes formulaic>
    evidence_ids: [<sample IDs>]
    confidence: provisional | observed

polish_boundary:
  preserve:
    - <durable voice signal>
  clean:
    - <typo, filler, repetition, or other accidental roughness>
  evidence_ids: [<sample IDs>]

non_negotiables:
  preserve:
    - <meaning, evidence, uncertainty, judgment, or other invariant>
  never_add:
    - <unsupported personal experience, metric, source, or claim>

validation:
  north_star: writer_would_publish_or_send_unchanged
  leading_measures:
    - editing_time
    - edit_distance
  guardrails:
    - factual_accuracy
    - privacy
    - evidence_traceability
  unresolved_questions:
    - <material question that more samples must answer>
```

## Evidence rules

Use stable synthetic or user-provided sample IDs. Do not copy full sentences into the profile.

Positive evidence types, strongest first:

1. `draft_final_pair`: the user's changes expose active preferences.
2. `accepted_final`: final or published work the user identifies as representative.
3. `raw_prompt` or `transcript`: natural thinking voice, not automatically publishing voice.
4. `accepted_ai_draft`: positive only when the user explicitly accepted it unchanged.

An AI draft without acceptance is not positive evidence. A reference author is never evidence of the user's voice.

A signal is `observed` only when at least three independent positive samples support it without strong counterevidence. Otherwise it is `provisional`. The profile is `calibrated` only when at least three observed signals span at least two positive source types.

When samples conflict:

- current explicit user instruction wins;
- stronger evidence types win over weaker types;
- repeated recent evidence may supersede older evidence when the user confirms the change;
- unresolved material conflicts remain in `validation.unresolved_questions`.

## Privacy rules

Do not include raw conversations, full excerpts, names, customer details, private metrics, credentials, or sensitive anecdotes. Evidence IDs should remain meaningful only within the user's private corpus.

If the user requests a saved profile, write it only to a user-approved private location. A public skill repository may contain this schema and synthetic fixtures, never a person's actual profile or samples.

## Comparison and refresh

When refreshing a profile:

- preserve the version and stable signal IDs when meanings have not changed;
- show added, strengthened, weakened, and removed signals;
- do not silently erase counterevidence;
- ask the writer to confirm material changes before treating them as calibrated.

When comparing profiles, compare writing decisions by surface. Do not rank people, infer personality, or score who sounds “more human.”
