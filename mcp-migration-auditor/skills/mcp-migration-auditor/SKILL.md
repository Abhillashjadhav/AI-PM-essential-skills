---
name: mcp-migration-auditor
description: Use this skill when the user wants to audit my MCP setup, check MCP compatibility, asks will my MCP servers break, mentions MCP spec migration, wants an MCP 2026 spec check, or says scan mcp config — also on any readiness question about the MCP 2026-07-28 specification (stateless transport, removed Mcp-Session-Id, deprecated roots/sampling/logging, experimental Tasks migration, OAuth hardening). Locates MCP configs (.mcp.json, claude_desktop_config.json, mcp.json, settings files) or accepts a pasted one, checks each server against rules verified from the official MCP blog and spec changelog, and outputs a per-server BREAKS/DEGRADED/SAFE table naming the triggering rule and specific fix, plus a scoped migration checklist for the deployed protocol version. Stdio findings distinguish transport from capability evidence. Do NOT use for context-window cost audits of MCP connectors (cli-over-mcp-auditor's job), for debugging a broken MCP connection, or for installing new servers.
---

# MCP Migration Auditor

Review MCP configs for the selected **2026-07-28** migration risks below. For each finding, name the target version, observed evidence, source and remaining unknowns. A scoped clearance is not a full compatibility certificate.

**Source status:** rules rechecked on 2026-09-28 against the versioned
specification; see `references/spec-changes.md`. July 28 is a past revision date.
Record the deployed protocol/client/SDK versions before applying a migration
verdict. These selected checks are not full protocol conformance.

## Step 1 — Locate configs

Search the project for MCP configs, in this order: `.mcp.json`, `mcp.json`, `claude_desktop_config.json`, `mcpServers` blocks inside `.claude/settings.json` / `.claude/settings.local.json` / other settings files. If none found, ask the user to paste one — never audit an imagined config.

## Step 2 — Classify transport per server

- `command`-based entries → **stdio/local**. HTTP session changes alone do not establish a transport failure; inspect shared protocol/capability rules before any broader verdict.
- `url`-based entries (HTTP / Streamable HTTP / SSE) → remote. These get the full rule pass.

## Step 3 — Apply the verified rules

| Rule | Evidence to look for | Verdict | Source |
|---|---|---|---|
| **R1 — Protocol session dependency** | `Mcp-Session-Id` in headers, session-affinity/sticky-session settings, session-store references for an MCP endpoint | **BREAKS** — header and protocol-level session removed | SEP-2567 |
| **R2 — Handshake pinning** | custom client/server code pinned to `initialize`/`initialized`; version negotiation done once at connect | **BREAKS** — handshake removed; protocol version and capabilities travel in `_meta` per request; client identity is recommended; `server/discover` replaces capability exchange | SEP-2575 |
| **R3 — Deprecated capabilities** | server uses **roots**, **sampling**, or **logging** (config flags, docs, or user confirmation) | **DEGRADED** — deprecated feature; inspect specific method removals and the current lifecycle registry | SEP-2577, SEP-2596 |
| **R4 — Experimental Tasks** | server or client shipped against the 2025-11-25 experimental Tasks API | **BREAKS** — Tasks moved to an official extension with a new lifecycle; `tasks/list` removed | SEP-2663 |
| **R5 — OAuth patterns** | remote server using OAuth: no validation of a present `iss`, credentials assumed portable across authorization servers, missing `application_type` in dynamic client registration | **DEGRADED** — action required for compliance: validate `iss` (RFC 9207), re-register credentials (issuer-bound), declare `application_type` | SEP-2468, SEP-2352, SEP-837 |
| **R6 — Stdio transport scope** | `command`-based; other applicable checks explicitly resolved | **SAFE for checked scope** — list unconfirmed rules separately | official announcement, "Unaffected Deployments" |

Fixes, stated per verdict:
- R1 → redesign around explicit state handles (the spec's recommended pattern: mint handles from tools, thread identifiers across calls) or upgrade to an SDK release implementing 2026-07-28 statelessness.
- R3 → roots → tool parameters / resource URIs / server config; sampling → direct LLM provider API integration; logging → `stderr` for stdio servers, OpenTelemetry for structured logging.
- R4 → migrate to the Tasks extension lifecycle (`tools/call` returns a task handle; client drives via `tasks/get` / `tasks/update` / `tasks/cancel`).
- Client-side note when relevant: code matching the MCP-custom error `-32002` must switch to JSON-RPC `-32602` (SEP-2164).

**Evidence honesty:** a config file shows transport, URLs, and headers — it usually cannot show whether a server uses sampling, roots, or the Tasks API. When a rule needs facts the config can't provide, ask the user (or check the server's docs if they're in the project) and mark the row `UNCONFIRMED — needs owner answer` until answered. Unknown is never silently SAFE and never silently BREAKS.

## Step 4 — Report

```
MCP MIGRATION AUDIT — target 2026-07-28; reviewed <date>; deployed version <version/unknown>
| Server | Transport | Status | Rule | Fix |
|--------|-----------|--------|------|-----|
```

Below the table, list observed incompatibilities first, migration work second,
and unresolved evidence last. Explain which implementation/version each finding
applies to. A stdio-only config can clear the HTTP session check; it cannot by
itself establish that hidden capabilities or client code are compatible.

## Hard rules

- **No invented rules.** Every verdict cites a rule from the table above, and every rule traces to an official source in `references/spec-changes.md`. If the user asks about a change not covered there, say it's unverified rather than improvising an answer.
- **No false alarms.** Report only evidenced incompatibilities. Missing capability evidence is unconfirmed, not SAFE or BREAKS.
- **Unknown is not a verdict.** Capabilities invisible in config are asked about, not assumed either way.
- **No countdown from stale dates.** State the target revision, source-check date and deployed version. Check the current lifecycle registry before asserting a removal deadline.

## Limitations

- Config-level scanning sees transport and headers, not server internals; rules R3/R4 usually require the user's confirmation or server documentation, and the audit says so per row.
- R1–R6 cover selected migration risks, not every 2026-07-28 requirement. The source ledger names additional areas requiring implementation evidence.
- OAuth findings cover the documented SEP-level changes, not a full security review of the deployment.
- The audit reads configs; it does not probe live servers or verify that a declared transport matches runtime behavior.
