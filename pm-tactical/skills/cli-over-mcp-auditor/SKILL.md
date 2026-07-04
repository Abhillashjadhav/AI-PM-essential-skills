---
name: cli-over-mcp-auditor
description: Use this skill when the user wants to audit their MCP connectors, reduce context window usage, or asks why their Claude Code sessions run out of context fast — phrasings like "audit my MCPs", "why is my context filling up", "should I use CLI instead of MCP", "reduce my context overhead", "my sessions compact too early". Inventories connected MCP servers, estimates the idle context cost of each, checks whether a CLI or script equivalent exists, and outputs a keep/replace/remove verdict per connector. Do NOT use for debugging a broken MCP connection, for installing new connectors, or for general questions about what MCP is.
---

# CLI-over-MCP Auditor

Every connected MCP server loads its tool definitions into the context window at session start — a standing tax paid whether or not the tools are used. CLI tools cost zero context until invoked. This skill finds the tax and recommends where to stop paying it.

## Step 1 — Inventory

List every connected MCP server. In Claude Code, ask the user to run `claude mcp list` and paste the output, or read `.mcp.json` / settings files if accessible. For each server, list its tools and count them.

## Step 2 — Estimate idle cost

For each MCP server, estimate context cost as the token size of its injected tool definitions (tool names + descriptions + parameter schemas). Method, in order of preference:
1. If the raw tool definitions are visible, count them directly (state the count as measured).
2. Otherwise estimate: typical tool definition ≈ 150-600 tokens depending on schema complexity; multiply by tool count and label the result ESTIMATE with the range.

Never present an estimate as a measurement. Show per-server and total overhead as a percentage of a 200K context window.

## Step 3 — Check usage vs cost

For each server ask: how often were its tools actually used in recent sessions (user's recollection is acceptable input)? Classify: DAILY / WEEKLY / RARELY / NEVER.

## Step 4 — Find the CLI alternative

For each server, check whether a mature CLI covers the same jobs (e.g., GitHub → `gh`, Vercel → `vercel`, cloud providers → their CLIs, databases → native clients, file/web jobs → curl or scripts). Rate replacement difficulty: DROP-IN (CLI covers everything) / PARTIAL (covers main jobs) / NONE (no equivalent — MCP earns its seat).

## Step 5 — Verdict table

```
MCP AUDIT — <date>
| Server | Tools | Idle cost (est/meas) | Usage | CLI alt | Verdict |
|--------|-------|----------------------|-------|---------|---------|
KEEP     — used daily or no CLI alternative
REPLACE  — CLI is drop-in or partial and usage is weekly or less
REMOVE   — never used, regardless of alternative
TOTAL RECLAIMABLE: ~X tokens (~Y% of a 200K window)
```

For every REPLACE, give the exact CLI install command and one example invocation covering the most common job.

## Limitations

- Idle-cost figures are estimates unless tool definitions were directly countable; ranges are stated, not hidden.
- Context overhead varies by client and version; percentages assume a 200K window.
- Some MCPs provide auth or stateful sessions a CLI can't replicate — flagged as NONE, never force-fit.
- Usage data relies on the user's recollection unless session logs are provided.
