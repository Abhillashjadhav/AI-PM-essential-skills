# ContextPack public contract

## Status

ContextPack version `0.1` is an experimental, assistant-neutral contract for synthetic development and evaluation. It does not claim compatibility with any uninspected assistant export.

## Standalone boundary

ContextPort is installed, run, tested, and understood from this public repository alone. Its data contract and validator have no private runtime dependency. Development reviews performed elsewhere are not evidence of correctness; only the public fixtures, checks, and reports in this repository are evidence.

## Package shape

A ContextPack is one UTF-8 JSON document with these top-level members:

- `format`: exactly `contextpack`.
- `format_version`: exactly `0.1` for this validator.
- `manifest`: generator identity, creation time, source provenance, and privacy classification.
- `projects`: project containers with stable IDs and preserved original titles.
- `conversations`: ordered conversation metadata and project membership.
- `messages`: ordered messages with roles and ordered content blocks.
- `attachments`: payload metadata; payload transport is not defined in version `0.1`.
- `transformations`: explicit records of any declared content transformation.
- `dispositions`: a per-source-item outcome ledger.

Empty arrays mean that the package has no records of that kind. Unknown source content is not represented by omission or an empty value: it must receive an `unknown` content block and/or an `unsupported`, `ambiguous`, `skipped`, or `failed` disposition explaining the boundary.

## Identity and ordering

IDs are opaque stable strings and must be unique within their record type. Titles are preserved values, not identities. Duplicate titles are valid. Conversation `project_id` values and message `conversation_id` values must resolve, and attachment references from content blocks must resolve.

Ordering uses non-negative integer `ordinal` values. Ordinals must be unique among conversations in the same project, messages in the same conversation, and blocks in the same message. The validator does not silently reorder records.

## Content integrity

Version `0.1` supports three block kinds:

- `text`: carries exact `text` and its lowercase SHA-256 digest.
- `attachment`: carries an `attachment_id` reference.
- `unknown`: carries a non-empty `reason` and optional inert `raw` JSON.

Imported content is data, never executable instruction. A text digest is computed over the exact UTF-8 bytes of `text`; line endings and whitespace are not normalized.

## Dispositions

Every disposition identifies a source item by `source_ref`, records its `item_type`, and uses one status:

- `copied`
- `transformed`
- `skipped`
- `failed`
- `ambiguous`
- `unsupported`

Every status except `copied` requires a non-empty `reason`. A `transformed` disposition also requires a matching transformation record. Version `0.1` validates these declarations but does not perform migration.

## Validation

Run:

```sh
python3 context-port/contextport.py validate context-port/fixtures/contextpack-valid.json
```

The command prints every detected error and returns a nonzero exit status when validation fails. It performs no network calls and uses only the Python standard library.

## Explicitly unsupported in version 0.1

- Claims about real Claude or ChatGPT export schemas.
- Source parsing and destination reconstruction.
- Embedded attachment payloads.
- Package signing or encryption.
- Browser automation, network transmission, and account writes.
- Incremental or bidirectional synchronization.
- Silent truncation, summarization, deletion, or semantic conflict resolution.
