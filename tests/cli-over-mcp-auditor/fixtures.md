# Gate 2 — Triggers
FIRE: "audit my MCPs" | "why is my context filling up so fast" | "should I use the GitHub CLI instead of the MCP" | "reduce my context overhead" | "my sessions compact too early"
NO-FIRE: "my Notion MCP won't connect" (debug) | "install the Slack MCP" (install) | "what is MCP?" (knowledge) | "audit my CLAUDE.md" (context-auditor's job) | "how many tokens did this session use" (token-cost-estimator's job)

# Gate 3 — Functional known-answer
INPUT: user pastes `claude mcp list` showing GitHub MCP (26 tools, used weekly),
Postgres MCP (8 tools, used daily), Weather MCP (3 tools, never used)
EXPECTED: GitHub → REPLACE (gh CLI drop-in, weekly usage) with install command;
Postgres → KEEP (daily usage); Weather → REMOVE (never used);
all idle costs labeled ESTIMATE with ranges; total reclaimable stated as ~tokens + %
