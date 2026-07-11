# ContextPort command-line contract

The public CLI is dependency-free, local-first, and invoked from a checkout with Python 3:

```sh
python3 context-port/contextport.py --help
python3 context-port/contextport.py --version
python3 context-port/contextport.py capabilities
```

## Output contract

- Successful data-producing commands print JSON or HTML to standard output.
- A well-formed ContextPack that fails semantic validation returns status `1` and prints the complete human-readable validation report to stdout. This is an expected validation result, not a CLI usage failure.
- Malformed input, I/O failures, and CLI usage errors return status `2` and print diagnostics to standard error.
- ContextPort never overwrites an output file; callers may redirect stdout to a new protected local file.
- Outputs derived from real conversations are private even when they contain only metadata.
- `capabilities` is deterministic and does not probe accounts, files, environment secrets, or networks.

## Exit statuses

| Code | Meaning |
|---:|---|
| 0 | Success |
| 1 | ContextPack validation failed |
| 2 | Invalid input, malformed JSON, I/O failure, or CLI usage error |
| 3 | Ambiguous mapping requires a human decision |
| 4 | Human review rejected the operation |
| 5 | Reconciliation found differences |
| 6 | Incremental sync found a human-required conflict |
| 7 | Destination capability assessment completed but the write interface is unsupported |

Nonzero statuses are expected control-flow outcomes where documented. They never prove that a write was attempted.

## Capability discovery

`capabilities` returns the CLI and ContextPack versions, command inventory, exit-code map, production dependency inventory, network requirement, and destination-write support. Scripts should inspect this output instead of inferring support from command names.
