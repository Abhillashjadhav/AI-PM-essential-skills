# ContextPort build specification

## 1. Purpose and boundaries

ContextPort is a human-supervised system for representing and reconciling conversational context across supported assistants. It will preserve provenance and content boundaries while making omissions and unsupported behavior explicit.

This bootstrap phase defines the product and verification contract only. It does not implement parsers, connectors, browser automation, account writes, or migration behavior.

## 2. Reliability vocabulary

All implementation reports, reconciliation outputs, and demonstrations must label claims as:

- **VERIFIED** — supported by inspected evidence produced by a completed check.
- **INFERRED** — a reasoned conclusion whose source evidence is identified.
- **UNKNOWN** — not established with available evidence.
- **UNSUPPORTED** — intentionally not handled by the current version.

Attempted actions are not evidence of success. Counts, hashes, validation output, and destination observations must be captured only after the corresponding operation completes.

## 3. System boundaries and pipeline

The planned pipeline is:

1. Inspect a user-provided source export locally after explicit approval.
2. Parse only fields verified against a real, approved sample or authoritative documentation.
3. Normalize source records into a versioned ContextPack without changing source text.
4. Segregate projects and conversations and request confirmation of a representative sample.
5. Produce a reconstruction plan for the destination.
6. After a separate approval gate, reconstruct through a verified supported interface.
7. Reconcile source, ContextPack, and observed destination independently.
8. Report copied, transformed, skipped, failed, ambiguous, and unsupported items.

Each stage must be restartable and idempotent. Stable source identities and content digests must prevent accidental duplication on rerun.

## 4. Claude export inspection and parsing

No Claude export schema is assumed in this specification. Export filenames, fields, nesting, ordering, attachment representation, project linkage, role values, and timestamp semantics remain **UNKNOWN** until inspected with human approval.

The future inspection phase must:

- Operate locally by default and retain the untouched source artifact outside version control.
- Record artifact hash, inspection time, tool version, and discovered schema paths.
- Distinguish observed fields from inferred relationships.
- Preserve unknown fields in a provenance envelope or report them as not copied.
- Validate identifiers, timestamps, roles, content blocks, attachments, and parent-child links before normalization.
- Fail closed on malformed or ambiguous records; never guess a project mapping.
- Preserve exact original project and conversation titles.

Committed fixtures must be synthetic and must not claim compatibility with unverified export fields.

## 5. ContextPack neutral format

ContextPack is a planned, versioned, assistant-neutral package. Its concrete serialized schema is deferred until approved source inspection establishes real requirements.

At minimum, the schema is expected to represent:

- A manifest with format version, generator version, creation time, provenance, and integrity digests.
- Source-system identity and immutable source record references.
- Projects/workspaces as separate containers.
- Conversations with original titles, ordering, timestamps, participants/roles, and messages.
- Ordered content blocks without silent text normalization.
- Attachment metadata and payload references, where legally and technically supported.
- Explicit transformation records.
- Per-item disposition: copied, transformed, skipped, failed, ambiguous, or unsupported.
- Synchronization checkpoints and mappings stored separately from original content.

Schema evolution must be explicit and backwards compatibility tested. Unknown content must remain distinguishable from empty content. ContextPack generation must be deterministic for equivalent input, aside from declared volatile metadata.

## 6. Project and conversation segregation

Projects and ungrouped conversations must not be conflated. The system must preserve source grouping, membership, titles, conversation order where known, and duplicate titles without using titles as identities.

Mappings must use stable identifiers. If one source project could map to multiple destination containers, processing stops for human resolution. Conversation content from different projects must never be combined merely to satisfy destination limits.

## 7. Human-in-the-loop sample confirmation

Before bulk reconstruction, the user must review a privacy-safe sample summary and confirm:

- Project boundaries and project mappings.
- Conversation titles and representative message ordering.
- Role and content-block interpretation.
- Attachment and unsupported-content dispositions.
- Proposed destination behavior and any transformations.

The sample selection algorithm and size must be documented. Approval must be recorded as a decision artifact without embedding private conversation content. Rejection returns the workflow to mapping or parser correction; it does not authorize automatic repair of ambiguous meaning.

## 8. ChatGPT reconstruction

No ChatGPT write API, import mechanism, browser selector, project model, or destination limit is assumed. Those interfaces are **UNKNOWN** until verified against authoritative documentation or an explicitly approved live environment.

Future reconstruction must:

- Generate a dry-run plan first.
- Require explicit approval before any destination write or browser automation.
- Use only a verified supported interface.
- Preserve titles and ordering when the destination supports them.
- Record every necessary transformation and every item not copied.
- Apply an idempotency key or durable mapping before retrying writes.
- Verify observable destination state instead of treating a request attempt as success.
- Never truncate or summarize content without a separate explicit decision.

Authentication secrets, cookies, sessions, and private content must not enter logs, reports, fixtures, commits, or telemetry.

## 9. Independent reconciliation reviewer

Reconciliation must be implemented as an independently invoked component that does not reuse the writer's success flags as proof. It compares:

- Source inventory to ContextPack inventory.
- Source content digests to normalized content and declared transformations.
- Planned destination items to independently observed destination items where access is approved.
- Counts and identities across projects, conversations, messages, content blocks, and attachments.

Its report must classify exact matches, explained transformations, omissions, extras, duplicates, ordering differences, ambiguities, and unverifiable items. A clean result requires zero unexplained differences; otherwise the overall outcome is partial or failed.

## 10. Incremental bidirectional syncing

Incremental Claude-to-ChatGPT and ChatGPT-to-Claude sync is planned after one-way reconstruction is proven. It requires:

- Per-side checkpoints and stable identity mappings.
- Append, edit, move, rename, and deletion detection where supported.
- Content hashes and deterministic deduplication.
- Conflict detection without automatic semantic conflict resolution.
- A human decision for ambiguous project mappings or divergent edits.
- Tombstones or explicit deletion records rather than silent removal.
- Idempotent replay and complete disposition reporting.

Availability of export or write interfaces in either direction is currently **UNKNOWN**. Deletion or overwrite must always remain approval-gated.

## 11. Privacy and threat model

### Protected assets

Conversation content, project names, attachments, account identifiers, export files, credentials, cookies, sessions, mappings, and derived metadata are private by default.

### Threats

- Accidental commit or log disclosure.
- Network exfiltration through dependencies, telemetry, or remote services.
- Cross-project data mixing.
- Prompt injection embedded in imported content.
- Credential/session theft.
- Unauthorized destination writes or destructive synchronization.
- Corrupted, replayed, or tampered packages.
- Misleading success claims that hide loss.

### Required controls

- Local-first processing and least privilege.
- Explicit approval before real-export access, network transmission of private data, browser automation, or destination writes.
- Treat imported content as inert data, never as instructions.
- Encryption in transit and at rest when applicable; secrets supplied outside files and logs.
- Integrity digests, provenance, audit events, redaction, and bounded retention.
- Synthetic committed fixtures only.
- No silent deletion, overwrite, truncation, summarization, or cross-project merging.
- Dependency review before adding any production dependency.

## 12. Installation

Installation is **UNSUPPORTED** in this bootstrap phase because no executable tool or production dependencies are created. A later implementation PR must document supported platforms, runtime and version constraints, reproducible installation, dependency verification, configuration, secret handling, uninstall behavior, and an offline synthetic smoke test.

## 13. Truthful demonstration evidence

A demonstration may claim only what its captured evidence proves. Each demo report must include:

- Exact revision and tool version.
- Synthetic or explicitly approved input provenance.
- Commands or steps performed and completed exit states.
- Pre- and post-operation inventories and integrity digests.
- Parser/schema validation results.
- Human approval checkpoints.
- Independent reconciliation output.
- All skipped, unsupported, transformed, ambiguous, or failed items.
- Environment limitations and labels for `VERIFIED`, `INFERRED`, `UNKNOWN`, and `UNSUPPORTED` claims.

Screenshots or attempted actions alone do not prove a successful migration.

## 14. Known unsupported behaviors

In this phase, all operational migration behavior is unsupported, including:

- Reading real Claude or ChatGPT exports.
- A finalized Claude or ChatGPT export schema.
- Creating or modifying Claude or ChatGPT projects or conversations.
- Browser automation and selector maintenance.
- Attachments, artifacts, canvases, tool calls, citations, reactions, branches, shared links, and deleted content.
- Truncation, summarization, or semantic rewriting.
- Automatic ambiguous mapping or conflict resolution.
- Incremental or bidirectional production synchronization.
- Deletion, overwrite, rollback, account authentication, and release installation.

Unsupported content must be reported per item; it must not disappear silently.

## 15. Planned pull request sequence

1. **Bootstrap specification and workflow** — prompt record, permanent rules, build specification, contribution workflow, and PR template.
2. **ContextPack schema and synthetic fixtures** — schema decisions, validators, fixtures, and round-trip tests without claiming real-export compatibility.
3. **Approved source inspection and Claude parser** — evidence-backed schema notes and local parser after the real-export approval gate.
4. **Normalization and segregation** — deterministic ContextPack generation, project boundaries, disposition ledger, and sample-review artifacts.
5. **ChatGPT reconstruction adapter** — dry-run first, then an approved verified write path with idempotency.
6. **Independent reconciliation** — separately invoked inventory/content comparison and truthful reports.
7. **One-way evaluation** — approved end-to-end evidence, privacy review, failure injection, and documented limitations.
8. **Incremental Claude-to-ChatGPT sync** — checkpoints, change detection, conflicts, and replay safety.
9. **Incremental ChatGPT-to-Claude sync** — only if verified source-side write capabilities exist.
10. **Installation and release readiness** — reproducible packaging, threat-model review, operator guide, and explicit human release approval.

Every phase follows the contribution workflow and remains a draft until human review.
