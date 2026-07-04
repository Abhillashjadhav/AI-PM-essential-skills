# Gate 2 — Triggers
FIRE (explicit deep audit): "audit my MCPs" | "why is my context filling up so fast" | "should I use the GitHub CLI instead of the MCP" | "reduce my context overhead" | "my sessions compact too early"
FIRE (proactive first-prompt check, no user-pasted list): first substantial prompt of a session where the session has MCP servers connected that look irrelevant to the task just asked — e.g. session has GitHub + Slack + Weather MCPs connected and the user's first prompt is "fix this CSS bug" (no mention of MCPs, no pasted list, no explicit audit request)
NO-FIRE: "my Notion MCP won't connect" (debug) | "install the Slack MCP" (install) | "what is MCP?" (knowledge) | "audit my CLAUDE.md" (context-auditor's job) | "how many tokens did this session use" (token-cost-estimator's job) | second/third substantial prompt in the same session (first-prompt check already ran once) | first prompt where all connected MCPs are relevant to the task (nothing to flag, stays silent)

# Gate 3 — Functional known-answer

## 3a. Explicit deep audit
INPUT: user pastes `claude mcp list` showing GitHub MCP (26 tools, used weekly),
Postgres MCP (8 tools, used daily), Weather MCP (3 tools, never used)
EXPECTED: GitHub → REPLACE (gh CLI drop-in, weekly usage) with install command;
Postgres → KEEP (daily usage); Weather → REMOVE (never used);
all idle costs labeled ESTIMATE with ranges; total reclaimable stated as ~tokens + %

## 3b. Proactive first-prompt check
INPUT: session has 3 MCP servers connected (visible in the session's own tool list, nothing pasted by the user) — GitHub (used this task), Slack (unrelated to this task), Weather (unrelated to this task). User's first prompt: "fix this CSS bug".
EXPECTED: exactly one line, no user-provided list required: "3 MCPs loaded, 2 unused for this work — disable to free up to ~X% context?" — then the CSS task proceeds normally. No line at all if every connected MCP were relevant instead.
