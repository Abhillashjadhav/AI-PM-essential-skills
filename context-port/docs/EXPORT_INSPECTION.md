# Safe export inspection

## Purpose

The inspection layer records the observable structure of a candidate JSON export before any source-specific parser is designed. It does not assume that filenames, fields, nesting, roles, timestamps, project links, or attachment structures match any assistant schema.

## Approval boundary

Only synthetic fixtures may be inspected during committed development and automated tests. Accessing a real Claude or ChatGPT export requires separate human approval under the repository rules.

The CLI requires an explicit classification:

```sh
python3 context-port/contextport.py inspect INPUT.json --classification synthetic
python3 context-port/contextport.py inspect INPUT.json --classification approved-private
```

`approved-private` is an audit label supplied after approval; it does not grant or prove approval by itself.

## Observed output

The JSON report contains:

- Report version and declared input classification.
- Artifact basename, byte count, and SHA-256 digest.
- Inspection timestamp and top-level JSON type.
- Sorted JSON paths, observed types, and occurrence counts. Object-key segments use JSON Pointer escaping (`~0` and `~1`), and `*` represents any array element.
- `values_emitted: false`.
- `schema_interpretation: UNKNOWN`.

Scalar values are never included. The tool does not infer relationships, rename fields, map projects, normalize text, or generate a ContextPack.

## Privacy limits

Artifact filenames and JSON field names are metadata and may still disclose private information. Private inspection reports must remain local unless separately reviewed and explicitly approved for disclosure. Report output should not be committed merely because scalar values are absent.

The inspector reads the file locally, performs no network access, caps input at 50 MiB, and caps traversal at 1,000,000 JSON nodes. Imported strings and field names are treated as inert data, not instructions.

## Failure behavior

Malformed UTF-8, malformed JSON, duplicate object keys, inaccessible files, oversized artifacts, and excessive node counts fail closed with a nonzero exit status. No partial report is presented as successful inspection.
