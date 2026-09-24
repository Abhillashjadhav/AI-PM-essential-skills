# R3 PDC provenance correction — F-R3-04 / F-R3-07

The repository-pilot adapter now rejects malformed PDC `source_digest` strings
before any binding write. Valid syntax is exactly `sha256:` plus 64 lowercase
hexadecimal characters. Valid syntax does not establish provenance: the value
is carried unchanged with `source_digest_verification="FORMAT_ONLY"`.

Both dialects explicitly emit `source_contract.approval_verified=false`.
`approval_status` remains publisher-declared; fabricated but structurally valid
claims are not authenticated by this adapter. The raw contract-file digest in
`contracts.pmos.sha256` remains independently computed and bound. Package
verification uses canonical JSON comparison so numeric `0` cannot replace the
new boolean `false` field, and a caller cannot promote the reported status.

RED tests were committed before implementation: nine malformed digest cases
were admitted and both dialects lacked explicit approval-verification labels.
The repaired full verifier suite passes **105 tests**, including **28 pilot
tests**. Regressions cover rejection before writes, unchanged upstream metadata,
unverified fabricated claims, spoofed status fields, raw-file digest binding,
and tampered/type-aliased verification labels. Repository integrity, skill lint,
and whitespace checks pass. The frozen catalog tree is unchanged.

Changing the bound tool correctly made the four synthetic trials stale. Binding
left their bytes untouched; the adapter was executed again locally and the new
trials were sealed. No evidence was relabeled, no upstream contract was changed,
and no receipt authentication, dependency, model call, or release authority was
added. Existing packages need a new bind and fresh evidence because the bound
tool and package metadata changed.

[Retained validation](r3-pdc-provenance-20260924/validation.json) identifies the
tested implementation commit/tree and tool hash; the same directory contains
the full RED/GREEN logs and synthetic re-execution record. Narrative docs retain
the previously published PR 65 wording plus the provenance clarification.

F-R3-07 is corrected by adding the recorded local-to-published mapping to the
historical review, preserving its original source identity and matching tree.
This does not reinterpret old test results as results for the R3 implementation.
