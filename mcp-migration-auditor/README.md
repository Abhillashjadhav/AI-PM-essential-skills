# mcp-migration-auditor

**Check MCP configuration evidence against selected migration rules.**

One skill that scans your MCP configs against the source-cited changes in the MCP 2026-07-28 specification — stateless transport, removed sessions, deprecated capabilities, Tasks migration, OAuth hardening — and tells you per server: **BREAKS**, **DEGRADED**, or **SAFE**, with the rule, the official source, and the specific fix.

Installable plugin in the [ai-pm-skills](../) marketplace.

## The problem

A config can expose a protocol dependency, but it cannot reveal every server
capability or prove runtime compatibility. This skill records what each finding
rests on and asks for missing evidence. Rules were rechecked on 2026-09-28;
July 28 is a past revision date. See the [source ledger](skills/mcp-migration-auditor/references/spec-changes.md) for sources and scope limits.

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
MCP MIGRATION AUDIT — target 2026-07-28; deployed version supplied by owner

| Server             | Transport   | Status   | Rule                     | Fix |
|--------------------|-------------|----------|--------------------------|-----|
| ticket-gateway     | HTTP remote | BREAKS   | R1 — sessions removed (SEP-2567) | explicit state handles; drop sticky routing |
| research-assistant | stdio local | DEGRADED | R3 — sampling deprecated (SEP-2577) | direct LLM provider API; 12-month clock |
| local-files        | stdio local | SAFE     | R6 — stdio unaffected    | none |
```

The checklist prioritizes evidenced incompatibilities and keeps unresolved rules
visible. `SAFE` applies only to the stated checks, not to full protocol conformance.

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

Manual review cases in `tests/mcp-migration-auditor/fixtures.md` cover triggers and expected audit output. Manifest and metadata checks are automated. No test invokes the live skill or probes a real server.

## License

MIT, same as the repo.

---

*Built by [Abhillash Jadhav](https://github.com/Abhillashjadhav) — GenAI PM. Evals, context engineering, agentic reliability.*
