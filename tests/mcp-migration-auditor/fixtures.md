# Gate 2 — Trigger accuracy

SHOULD FIRE:
T1. "Audit my MCP setup before the new spec lands"
T2. "Check MCP compatibility for our servers"
T3. "Will my MCP servers break on the 2026 spec?"
T4. "We need an MCP spec migration plan — what's affected?"
T5. "Run an MCP 2026 spec check on this config" / "scan mcp config"

SHOULD NOT FIRE:
N1. "Why is my context filling up so fast?"          (cli-over-mcp-auditor's job — context cost, not compatibility)
N2. "My Notion MCP won't connect"                    (debugging a broken connection)
N3. "Install the Slack MCP server"                   (installation)
N4. "What is MCP?"                                   (knowledge question)
N5. "Write an MCP server for our ticket system"      (building, not auditing)

# Gate 3 — Functional known-answer (end-to-end)

INPUT: mcp-migration-auditor/skills/mcp-migration-auditor/examples/sample-mcp-config.json
(three servers: ticket-gateway = stateful HTTP with Mcp-Session-Id header and
session-store note; research-assistant = stdio with --use-sampling flag and
sampling note; local-files = plain stdio)

EXPECTED (reference output in examples/sample-audit-output.md):
- ticket-gateway → BREAKS, rule R1, citing SEP-2567 (Mcp-Session-Id removed),
  fix = explicit state handles / 2026-07-28 SDK, drop sticky routing
- research-assistant → DEGRADED, rule R3, citing SEP-2577 (sampling deprecated)
  with the SEP-2596 12-month lifecycle note; fix = direct LLM provider API.
  Must NOT be marked BREAKS: stdio transport is safe, only the sampling
  capability degrades it
- local-files → SAFE, rule R6, stated plainly with no invented caveats
- Output includes the table (server → status → rule → fix) and a prioritized
  checklist with BREAKS first and deadline framing against 2026-07-28
- Every verdict cites a SEP that appears in references/spec-changes.md with a
  source URL — no rule outside that file may be asserted
- R4 (Tasks) must NOT be asserted for any server (no Tasks evidence in the
  config) — absence of evidence produces a question in live audits, never a
  verdict

ALL-CLEAR CASE:
INPUT: a config containing only local-files (plain stdio, no capability flags)
EXPECTED: one-line all-clear — all servers stdio/local and unaffected by the
2026-07-28 transport/session changes; no table of non-findings, no false alarms
