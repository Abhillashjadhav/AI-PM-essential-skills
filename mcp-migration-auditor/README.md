# mcp-migration-auditor

**The MCP spec goes final on July 28, 2026. Will your servers break?**

One skill that scans your MCP configs against the *verified* breaking changes in the MCP 2026-07-28 specification — stateless transport, removed sessions, deprecated capabilities, Tasks migration, OAuth hardening — and tells you per server: **BREAKS**, **DEGRADED**, or **SAFE**, with the rule, the official source, and the specific fix.

Third plugin in the [ai-pm-skills](../) marketplace, alongside [pm-tactical](../pm-tactical/) and [pm-verifier](../pm-verifier/).

## The problem

The 2026-07-28 release candidate removes the `Mcp-Session-Id` header and the initialize handshake (SEP-2567, SEP-2575), deprecates Roots/Sampling/Logging (SEP-2577), moves Tasks to an extension with a new lifecycle (SEP-2663), and hardens OAuth (six SEPs). Teams running remote MCP servers built on sessions have until spec-final to migrate; teams on deprecated capabilities have a 12-month clock (SEP-2596). Most teams don't know which bucket they're in — and most "what's changing in MCP" content is speculation. This skill audits only against rules quoted from the official blog and spec changelog, with URLs, in `skills/mcp-migration-auditor/references/spec-changes.md`.

## Install (30 seconds)

```bash
claude plugin marketplace add Abhillashjadhav/AI-PM-essential-skills
claude plugin install mcp-migration-auditor@ai-pm-skills
```

## Use (60 seconds)

```
audit my MCP setup
```

Also fires on: "check MCP compatibility", "will my MCP servers break", "MCP spec migration", "MCP 2026 spec check", "scan mcp config". The skill finds your `.mcp.json` / `claude_desktop_config.json` / settings files (or takes a pasted config) and returns:

```
MCP MIGRATION AUDIT — spec final 2026-07-28 (21 days away)

| Server             | Transport   | Status   | Rule                     | Fix |
|--------------------|-------------|----------|--------------------------|-----|
| ticket-gateway     | HTTP remote | BREAKS   | R1 — sessions removed (SEP-2567) | explicit state handles; drop sticky routing |
| research-assistant | stdio local | DEGRADED | R3 — sampling deprecated (SEP-2577) | direct LLM provider API; 12-month clock |
| local-files        | stdio local | SAFE     | R6 — stdio unaffected    | none |
```

…plus a prioritized migration checklist: BREAKS items deadline-framed first, DEGRADED clock items second, and an honest one-line all-clear if everything you run is stdio/local. No false alarms — an unaffected setup is told it's unaffected.

## What it checks (all source-cited)

- **Session dependencies** — `Mcp-Session-Id`, sticky routing, session stores (SEP-2567: removed)
- **Handshake pinning** — `initialize`/`initialized` reliance (SEP-2575: removed; `_meta` + `server/discover` replace it)
- **Deprecated capabilities** — roots, sampling, logging (SEP-2577; ≥12-month lifecycle per SEP-2596)
- **Experimental Tasks** — 2025-11-25 API users must migrate to the extension (SEP-2663; `tasks/list` removed)
- **OAuth patterns** — `iss` validation, issuer-bound credentials, `application_type` in DCR (SEP-2468, SEP-2352, SEP-837)

What the config can't show (whether a server actually uses sampling or Tasks), the skill asks about — rows are marked `UNCONFIRMED — needs owner answer`, never silently guessed.

## Try it on the sample

A deliberately vulnerable config ships in `skills/mcp-migration-auditor/examples/sample-mcp-config.json` (one stateful HTTP server, one sampling user, one clean stdio server); the expected audit is next to it in `sample-audit-output.md`.

## Testing

Three-gate harness, same convention as the other plugins (`tests/mcp-migration-auditor/fixtures.md`): manifest lint, trigger fire/no-fire phrasings, and the known-answer end-to-end audit above.

## License

MIT, same as the repo.

---

*Built by [Abhillash Jadhav](https://github.com/Abhillashjadhav) — GenAI PM. Evals, context engineering, agentic reliability.*
