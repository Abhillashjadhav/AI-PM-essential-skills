# Expected audit output for examples/sample-mcp-config.json

This is the known-answer output the skill produces for the sample config,
audited 2026-07-07 (21 days before the final spec). Used as the Gate 3
end-to-end fixture in `tests/mcp-migration-auditor/fixtures.md`.

---

```
MCP MIGRATION AUDIT — spec final 2026-07-28 (21 days away)

| Server             | Transport   | Status   | Rule                          | Fix |
|--------------------|-------------|----------|-------------------------------|-----|
| ticket-gateway     | HTTP remote | BREAKS   | R1 — session dependency (SEP-2567): Mcp-Session-Id header in config, session-affinity gateway + Redis session store noted | Redesign around explicit state handles (mint handles from tools, thread IDs across calls) or upgrade to a 2026-07-28 SDK; remove sticky routing — any request may land on any instance |
| research-assistant | stdio local | DEGRADED | R3 — deprecated capability (SEP-2577): --use-sampling flag, config note confirms MCP sampling | Replace MCP sampling with direct LLM provider API integration; works ≥12 months from deprecation under SEP-2596, but the clock is running |
| local-files        | stdio local | SAFE     | R6 — stdio/local transport, no flagged capabilities | None — stdio transports are unaffected by the 2026-07-28 session and transport changes |
```

## Prioritized migration checklist

1. **[BREAKS — before 2026-07-28] ticket-gateway**: remove the `Mcp-Session-Id`
   dependency (header is removed by SEP-2567 — requests carrying protocol
   sessions stop working against 2026-07-28 implementations). Move state into
   explicit handles returned by tools; then delete the session-affinity gateway
   rule and the Redis session store — the protocol no longer needs either.
2. **[DEGRADED — 12-month clock] research-assistant**: migrate off MCP sampling
   to a direct LLM provider API call inside the server. No hard deadline at
   spec-final, but sampling is deprecated (SEP-2577) and removable in any spec
   version published ≥12 months after deprecation (SEP-2596).
3. **[SAFE] local-files**: no action.

Sources for every rule cited: `references/spec-changes.md`.

## Notes on the verdicts (evidence honesty)

- ticket-gateway's BREAKS rests on config-visible evidence (the header + the
  session-store note). Without those markers, an HTTP server would be
  `UNCONFIRMED — needs owner answer` for R1, not silently BREAKS.
- research-assistant is stdio, which starts SAFE for transport — the DEGRADED
  verdict comes solely from the confirmed sampling capability (R3). Transport
  safety does not exempt a server from capability deprecations.
- Neither non-safe server was checked for R4 (experimental Tasks): the config
  shows no Tasks evidence, so R4 is not asserted — it would be asked about in
  a live audit, not assumed.
