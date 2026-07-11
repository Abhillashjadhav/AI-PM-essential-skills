# ContextPack 0.1 validation evaluation

## Revision

Branch: `context-port/002-contextpack-schema`

Exact commit: **UNKNOWN** until the phase commits are created.

## Inputs

- `fixtures/contextpack-valid.json`: **VERIFIED synthetic** fixture containing fictional content only.
- `fixtures/contextpack-invalid.json`: **VERIFIED synthetic** planted-failure fixture.
- No real exports, credentials, account identifiers, private conversations, or network services were accessed.

## Gates

1. A valid synthetic package passes the public CLI.
2. The invalid fixture reports every planted failure in one run.
3. Exact text integrity is checked with SHA-256 without whitespace normalization.
4. Unknown blocks require an explicit reason.
5. Empty text remains valid and distinct from unknown content.
6. Duplicate titles remain valid while duplicate identities fail.
7. Every represented project, conversation, message, content block, and attachment requires a disposition.
8. The implementation uses the Python standard library only.

## Completed evidence

`python3 -m unittest discover -s context-port/tests -v`

- Result: **VERIFIED PASS**
- Tests completed: 7
- Failures: 0
- Errors: 0

`python3 context-port/contextport.py validate context-port/fixtures/contextpack-valid.json`

- Result: **VERIFIED PASS**
- Observable output: `ContextPack 0.1 is valid`

`git diff --check`

- Result: **VERIFIED PASS**
- Observable output: none; exit status 0.

## Repair history

1. Initial evaluation correctly rejected an incorrect digest in the valid fixture. The fixture digest was recomputed from its exact synthetic text.
2. Adding disposition-coverage enforcement exposed stale test expectations. The expectations were updated to require the newly reported omissions.
3. The full gate passed after repair attempt 2. No further repair was performed.

## Limitations

- **UNSUPPORTED:** compatibility with real assistant exports.
- **UNSUPPORTED:** parsing, reconstruction, attachment payload transfer, synchronization, signing, and encryption.
- **UNKNOWN:** supported Python-version range beyond the locally completed run.
- **INFERRED:** standard-library-only validation reduces installation and supply-chain complexity; it does not by itself establish portability across all platforms.
- The validator is the executable authority for ContextPack `0.1`; no claim is made that it implements an external assistant schema.
