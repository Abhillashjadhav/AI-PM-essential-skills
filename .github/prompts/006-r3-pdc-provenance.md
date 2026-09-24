# Authorized engineering correction: F-R3-04 and F-R3-07

Validate PDC `source_digest` syntax as exactly `sha256:` plus 64 lowercase hex
characters. Treat this value as carried upstream metadata, not an authenticated
or recomputed digest. Expose `source_contract.approval_verified: false` for both
supported dialects and `source_digest_verification: FORMAT_ONLY` for PDCs.
`approval_status` remains publisher-declared; receipt authentication is out of
scope. The raw source-file SHA-256 binding remains separate and enforced.

Add RED regressions before implementation, preserve legacy compatibility, and
rerun synthetic evidence rather than relabeling its provenance after the bound
tool changes. Do not change frozen catalog content or product contracts. Keep
runtime/evidence changes separate from narrative documentation. Document the
scope and add the existing local-to-published commit mapping without rewriting
historical review identities. No remote publication, merge, paid/model calls,
or new approval authentication. Root independently reviews the result.

Base: local `58dbb0a5c511cacdebe3560f55358b81351da889`, published AIPM PR 64
`155bc180a33b5917808f472718484a23beafac63`, matching tree
`166e242dd98f78a0076712a060b7987e037c2924`.
