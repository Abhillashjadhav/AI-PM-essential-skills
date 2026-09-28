---
name: cli-over-mcp-auditor
description: Use this skill when the user asks to audit MCP connector context cost, compare CLI and MCP workflows, or investigate context overhead. On the first substantial prompt, offer a brief suggestion only if irrelevant full tool definitions are visibly loaded; do not infer loaded schema cost from connected servers or deferred tool names. Distinguishes measured, estimated and unknown costs, checks workflow coverage and permissions, and leaves configuration changes to the owner. Do NOT use for connection debugging, installation, generic MCP questions or specification migration audits.
---

# CLI-over-MCP Auditor

Tool context depends on the client, model and loading mode. Audit what is
actually injected before recommending a change. A connected server is not proof
that all its tool definitions occupy the current context.

## Step 0 — First-prompt check

Inspect only information already visible in the session. Distinguish connected
servers, available tool names and full definitions actually loaded. Do not load
more tools merely to inflate this inventory. If irrelevant loaded definitions
are visible, offer one short audit suggestion and continue the requested task.
If loading mode or relevance is unclear, stay silent. Never claim a percentage
saving without a measurement or an explicitly labelled estimate.

## Step 1 — Inventory for an explicit audit

Record client/version, model, loading mode and configured window size when known.
Use supplied configuration or a permitted local read; do not disclose secrets.
`claude mcp list` describes connections, not prompt-token usage. Separate each
server's loaded definitions from deferred names and server instructions.

Claude Code documentation checked 2026-09-28 describes tool search as enabled by
default, with definitions deferred. Some provider/model/configuration combinations
load tools up front; `alwaysLoad` can exempt a server. Check the actual session.
Source: [Claude Code MCP tool search](https://code.claude.com/docs/en/mcp#scale-with-mcp-tool-search).

## Step 2 — Measure or mark unknown

Count the injected text only with a matching tokenizer or runtime measurement;
record tool, scope and method. Visibility alone is not a token measurement.
If only an estimate is possible, state its basis and uncertainty. If only tool
counts are known, report token cost as unknown rather than multiplying by an
unsourced per-tool average. Do not count deferred schemas as already loaded.
Use the actual context-window size for percentages; omit them if it is unknown.

## Step 3 — Compare workflow costs

Ask how often the tools are used. Compare CLI coverage, authentication, permissions,
output size and operational effort. CLI help, invocation text and results also
consume context when supplied to the model. A CLI alternative is not automatically
cheaper or equivalent. Check its official documentation before giving commands.

## Step 4 — Report

| Server | Loading mode | Observed context cost | Usage | CLI coverage | Recommendation |
|---|---|---|---|---|---|
| supplied server | loaded / deferred / unknown | measured / estimated / unknown | supplied evidence | verified / partial / unknown | reason and tradeoff |

Recommend retaining, changing or investigating the integration using the observed
workflow. Quantify reclaimable context only when the relevant text is measured
or the estimate is supported. Do not disable connectors or change permissions
without authorization.

## Hard rules

- Do not equate connection count with injected schema cost.
- Do not call an estimate a measurement or assume a 200K window.
- Do not recommend removal solely because a tool was unused in one task.
- Do not claim CLI parity without checking required operations and permissions.

## Limitations

This skill does not inspect hidden prompts, meter billed usage or alter runtime
loading. A first-prompt check can see only the current session. Provider support
and defaults can change; use the linked official documentation when auditing.
