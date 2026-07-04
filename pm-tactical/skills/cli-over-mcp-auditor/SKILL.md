---
name: cli-over-mcp-auditor
description: Use this skill proactively on the first substantial prompt of a session — silently inspect the session's own available tools/MCP servers (never ask the user to paste anything for this check) and, if any connectors look irrelevant to the task at hand, surface one compact line offering to free up context. Use this skill when the user makes explicit requests too — to audit MCP connectors, reduce context window usage, or explain why sessions run out of context fast — phrasings like "audit my MCPs", "why is my context filling up", "should I use CLI instead of MCP", "reduce my context overhead", "my sessions compact too early" — which get the full deep-audit flow instead of the one-liner. Do NOT use for debugging a broken MCP connection, for installing new connectors, or for general questions about what MCP is.
---

# CLI-over-MCP Auditor

Every connected MCP server loads its tool definitions into the context window at session start — a standing tax paid whether or not the tools are used. CLI tools cost zero context until invoked. This skill finds the tax and recommends where to stop paying it.

## Step 0 — First-prompt check (proactive, silent)

On the first substantial prompt of a session, before doing anything else, silently inspect the session's own already-available tools/MCP servers — do not ask the user to run or paste `claude mcp list` for this check; that's only for the explicit deep-audit flow (Step 1). Count connected MCP servers and their tools directly from what's visible in the session.

Judge relevance against the task the user is actually asking for right now — not against hypothetical future use. If one or more connectors look irrelevant to this task, emit exactly one line, then continue straight into the task:

```
N MCPs loaded, M unused for this work — disable to free up to ~X% context?
```

If nothing looks unused or irrelevant, say nothing — stay silent. This check runs once per session, not on every prompt.

## Step 1 — Inventory (explicit deep audit)

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
- The first-prompt relevance check is a judgment call based on the current task alone; it can miss connectors that matter later in the session, and never disables anything on its own — it only offers.
