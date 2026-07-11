# Capability matrix

This matrix describes ContextPort `0.1.0`. Command availability is not permission to cross a human approval gate.

| Capability | Status | Evidence or boundary |
|---|---|---|
| ContextPack `0.1` validation | `VERIFIED` | Public schema, valid/invalid fixtures, deterministic validator tests |
| Metadata-only JSON structure inspection | `VERIFIED` for synthetic input | Values are not emitted; real artifacts require fresh approval |
| Real Claude export schema compatibility | `UNKNOWN` | No real ZIP has been accessed or interpreted |
| Project segregation | `VERIFIED` for validated ContextPack | Stable IDs, duplicate-title preservation, explicit ambiguous-mapping stop |
| Human review package and offline HTML | `VERIFIED` | Metadata-only package, escaped HTML, digest-bound decision artifact |
| Assistant-neutral reconstruction planning | `VERIFIED` | Approved dry run with dependencies, exact content, and idempotency keys |
| Independent plan reconciliation | `VERIFIED` | Detects omissions, extras, duplicates, content/order changes, and tampering |
| Incremental change planning | `VERIFIED` | Add/edit/rename/move/reorder/delete detection, tombstones, conflicts |
| Consumer ChatGPT reconstruction writes | `UNSUPPORTED` | A bounded public-doc review did not verify the required write interface |
| Destination inventory observation | `UNSUPPORTED` | Requires separately approved account or browser access |
| Synthetic end-to-end migration demo | `VERIFIED` | Revision-bound report, zero reconciliation differences, every operation accounted for |
| Local wheel/sdist build | `VERIFIED` | Dependency-free reproducible artifacts and metadata tests |
| Local isolated installation | `VERIFIED` on Linux CI | Dry-run first, absent target, offline wheel, post-install verification |
| Windows installation | `INFERRED` | Path layout has unit coverage; end-to-end Windows CI is not yet evidence |
| Package-index publication | `UNSUPPORTED` | No package is published; name availability is `UNKNOWN` |
| Browser automation | `UNSUPPORTED` without approval | No selectors or browser workflow are implemented |
| Claude or ChatGPT writes | `UNSUPPORTED` without approval | No credential, session, or write path is implemented |
| Truncation or summarization | `UNSUPPORTED` without approval | Content reduction is never silent and requires a material human decision |
| Destructive delete/overwrite | `UNSUPPORTED` | Tombstones and fail-closed behavior replace destructive automation |

Run the machine-readable local inventory:

```sh
python3 context-port/contextport.py capabilities
```
