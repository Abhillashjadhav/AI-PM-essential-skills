---
name: mcp-migration-auditor
description: Use this skill when the user wants to audit my MCP setup, check MCP compatibility, asks will my MCP servers break, mentions MCP spec migration, wants an MCP 2026 spec check, or says scan mcp config — also on any readiness question about the MCP 2026-07-28 specification (stateless transport, removed Mcp-Session-Id, deprecated roots/sampling/logging, experimental Tasks migration, OAuth hardening). Locates MCP configs (.mcp.json, claude_desktop_config.json, mcp.json, settings files) or accepts a pasted one, checks each server against rules verified from the official MCP blog and spec changelog, and outputs a per-server BREAKS/DEGRADED/SAFE table naming the triggering rule and specific fix, plus a prioritized migration checklist against the 2026-07-28 final date. Stdio-only local setups get an honest all-clear. Do NOT use for context-window cost audits of MCP connectors (cli-over-mcp-auditor's job), for debugging a broken MCP connection, or for installing new servers.
---

# MCP Migration Auditor

Scan MCP server configs against the verified breaking changes in the MCP **2026-07-28** specification and report exactly which servers break, which degrade, and which are safe — with the rule and official source behind every verdict.

**The clock:** the release candidate locked May 21, 2026; the final specification ships **July 28, 2026**. Every rule below comes from the official announcement and spec changelog — full quotes and URLs in `references/spec-changes.md`. If a check isn't in that file, this skill doesn't make it.

## Step 1 — Locate configs

Search the project for MCP configs, in this order: `.mcp.json`, `mcp.json`, `claude_desktop_config.json`, `mcpServers` blocks inside `.claude/settings.json` / `.claude/settings.local.json` / other settings files. If none found, ask the user to paste one — never audit an imagined config.

## Step 2 — Classify transport per server

- `command`-based entries → **stdio/local**. Per the official announcement, stdio and local transports "operate independently of Streamable HTTP statelessness requirements and session infrastructure changes" — these start at SAFE.
- `url`-based entries (HTTP / Streamable HTTP / SSE) → remote. These get the full rule pass.

## Step 3 — Apply the verified rules

| Rule | Evidence to look for | Verdict | Source |
|---|---|---|---|
| **R1 — Protocol session dependency** | `Mcp-Session-Id` in headers, session-affinity/sticky-session settings, session-store references for an MCP endpoint | **BREAKS** — header and protocol-level session removed | SEP-2567 |
| **R2 — Handshake pinning** | custom client/server code pinned to `initialize`/`initialized`; version negotiation done once at connect | **BREAKS** — handshake removed; protocol version, client info, capabilities travel in `_meta` per request; `server/discover` replaces capability exchange | SEP-2575 |
| **R3 — Deprecated capabilities** | server uses **roots**, **sampling**, or **logging** (config flags, docs, or user confirmation) | **DEGRADED** — still works in this release and for ≥12 months under the lifecycle policy, but on the deprecation clock | SEP-2577, SEP-2596 |
| **R4 — Experimental Tasks** | server or client shipped against the 2025-11-25 experimental Tasks API | **BREAKS** — Tasks moved to an official extension with a new lifecycle; `tasks/list` removed | SEP-2663 |
| **R5 — OAuth patterns** | remote server using OAuth: no `iss` validation, credentials assumed portable across authorization servers, missing `application_type` in dynamic client registration | **DEGRADED** — action required for compliance: validate `iss` (RFC 9207), re-register credentials (issuer-bound), declare `application_type` | SEP-2468, SEP-2352, SEP-837 |
| **R6 — Plain stdio, none of the above** | `command`-based, no deprecated capabilities, no Tasks | **SAFE** — say so plainly | official announcement, "Unaffected Deployments" |

Fixes, stated per verdict:
- R1 → redesign around explicit state handles (the spec's recommended pattern: mint handles from tools, thread identifiers across calls) or upgrade to an SDK release implementing 2026-07-28 statelessness.
- R3 → roots → tool parameters / resource URIs / server config; sampling → direct LLM provider API integration; logging → `stderr` for stdio servers, OpenTelemetry for structured logging.
- R4 → migrate to the Tasks extension lifecycle (`tools/call` returns a task handle; client drives via `tasks/get` / `tasks/update` / `tasks/cancel`).
- Client-side note when relevant: code matching the MCP-custom error `-32002` must switch to JSON-RPC `-32602` (SEP-2164).

**Evidence honesty:** a config file shows transport, URLs, and headers — it usually cannot show whether a server uses sampling, roots, or the Tasks API. When a rule needs facts the config can't provide, ask the user (or check the server's docs if they're in the project) and mark the row `UNCONFIRMED — needs owner answer` until answered. Unknown is never silently SAFE and never silently BREAKS.

## Step 4 — Report

```
MCP MIGRATION AUDIT — spec final 2026-07-28 (<N> days away)
| Server | Transport | Status | Rule | Fix |
|--------|-----------|--------|------|-----|
```

Below the table, a prioritized checklist: BREAKS items first (deadline-framed — these stop working against 2026-07-28 implementations), then DEGRADED (12-month deprecation clock items and OAuth compliance actions), then a one-line all-clear for SAFE servers. If **every** server is stdio/local with no flagged capabilities, the entire report is one line: all servers are stdio/local and unaffected by the 2026-07-28 transport and session changes — no false alarms, no padding.

## Hard rules

- **No invented rules.** Every verdict cites a rule from the table above, and every rule traces to a quoted official source in `references/spec-changes.md`. If the user asks about a change not covered there, say it's unverified rather than improvising an answer.
- **No false alarms.** Stdio-only setups that trip no capability rule get the one-line all-clear. Alarm fatigue kills audit tools.
- **Unknown is not a verdict.** Capabilities invisible in config are asked about, not assumed either way.
- **Dates are fixed.** RC locked May 21, 2026; final spec July 28, 2026; deprecations hold for at least twelve months from deprecation per SEP-2596. Never dramatize the timeline beyond these facts.

## Limitations

- Config-level scanning sees transport and headers, not server internals; rules R3/R4 usually require the user's confirmation or server documentation, and the audit says so per row.
- Rules reflect the 2026-07-28 **release candidate** as officially announced; if the final specification changes between RC and release, `references/spec-changes.md` is the file to update.
- OAuth findings cover the documented SEP-level changes, not a full security review of the deployment.
- The audit reads configs; it does not probe live servers or verify that a declared transport matches runtime behavior.
