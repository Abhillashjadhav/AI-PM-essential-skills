# BAR — R4 repository-pilot reporting and receipt integrity

Written before implementation for F-C5-1, F-C5-2, and F-C5-3.

1. **Existing behavior:** qualify existing pilot package/reports and enforce exact
   JSON receipt values; preserve both source dialects and the standalone verifier.
2. **No duplicated product:** use the existing binder, verifier, canonical JSON
   serializer, tests, skill, and README. No dependency or new authentication API.
3. **Observable bar:** a top-level `approval_verified` is exactly `false` in
   package and bind/create/verify summaries. A receipt count cannot change from
   integer to float/boolean and remain accepted. Existing integer controls pass.
4. **Failure guardrails:** do not infer approval from `VERIFIED`; preserve source
   declarations and full-file digest checks. No frozen catalog edits, source
   approval fabrication, paid/model calls, publication, merge, or extra workers.
5. **Smallest deliverable:** RED tests, bounded runtime patch, genuinely rerun
   synthetic evidence, passing bounded verifier suite and skill lint, then a
   separate wording commit. Root independently reviews and handles publication.

Allow at most two repairs after each concrete failed gate; report a persistent
failure to the coordinator rather than weakening a gate.
