# Release readiness

Run the deterministic audit after canonical session memory is fresh:

```sh
python3 context-port/contextport.py handoff --check
python3 context-port/contextport.py release-check
```

Add `--write` to regenerate `reports/RELEASE_READINESS.md` and `reports/RELEASE_READINESS.json`.

The audit verifies version alignment, fresh generated session memory, the complete test result, schema parsing, reproducible wheel/sdist builds, clean synthetic reconciliation, zero demo writes/network/browser activity, branch authorship, ContextPort-only scope, absence of tracked export/session archives, zero production dependencies, and no private runtime dependency.

It cannot select a public license, approve publication, establish package-index name availability, authorize real Claude ZIP access, or authorize browser/assistant writes. Those remain explicit human decisions. A `ready` synthetic MVP with `blocked_human_decisions` public release is the expected truthful result until those gates are resolved.

Line coverage remains `UNKNOWN` because no coverage instrumentation dependency is configured. Test count, individual behavioral gates, and independent review remain the current quality evidence; no percentage is invented.
