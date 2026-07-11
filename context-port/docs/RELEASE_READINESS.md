# Release readiness

Run the deterministic audit after canonical session memory is fresh:

```sh
python3 context-port/contextport.py handoff --check
python3 context-port/contextport.py release-check
```

Add `--write` to regenerate `reports/RELEASE_READINESS.md` and `reports/RELEASE_READINESS.json`.

The audit verifies version alignment, fresh generated session memory, the complete test result, schema parsing, reproducible wheel/sdist builds, clean synthetic reconciliation, zero demo writes/network/browser activity, branch authorship, approved public scope, absence of tracked export/session archives, zero production dependencies, and no private runtime dependency. Phase 15 permits only two non-`context-port/` infrastructure paths: the deterministic PR checker and its regression test, required to narrowly recognize canonical public `context-port/SESSION.json`; similarly named session files remain blocked.

`audited_revision` is the newest commit that changes non-generated ContextPort content. Commits that change only `SESSION.md`, `SESSION.json`, or canonical release reports are excluded from that field, preventing generated evidence from trying to reference the commit that contains itself. Every other repository change still invalidates freshness or advances the audited revision.

It cannot select a public license, approve publication, establish package-index name availability, authorize real Claude ZIP access, or authorize browser/assistant writes. Those remain explicit human decisions. A `ready` synthetic MVP with `blocked_human_decisions` public release is the expected truthful result until those gates are resolved.

Line coverage remains `UNKNOWN` because no coverage instrumentation dependency is configured. Test count, individual behavioral gates, and independent review remain the current quality evidence; no percentage is invented.
