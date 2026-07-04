# pm-claude-skills

## What this repo is
Four Claude Code skills built for AI product managers. Each solves a real problem in the AI PM workflow — inference economics, eval design, context reliability, and output compression.

## PR rules (non-negotiable)
- Every change to a SKILL.md goes through a PR. No direct pushes to main.
- Every PR is reviewed using `/pr-review` before merge.
- One concern per PR. Schema changes, logic changes, and doc changes are separate PRs.
- PR description must state: what changed, why, and how to test the change.

## Skill quality bar
A skill ships when:
1. The SKILL.md has valid frontmatter (name, description, argument-hint)
2. The skill body has at least 3 explicit hard rules
3. A test input + expected output exists in the skill's README section
4. The PR review returns APPROVE

## What we do not ship
- Skills that duplicate official Anthropic surfaces
- Skills that produce unverifiable output (fabricated metrics, invented pricing)
- Skills without explicit failure guardrails

## Skill routing (fallback for not-yet-enabled sessions)
Plugin skills fire natively once `.claude/settings.json` (marketplace + `enabledPlugins`) is committed to the repo and the session trusts project settings. Sessions started before that commit, or where the plugin was installed mid-session rather than picked up from committed settings, won't have it in their invocable set yet. For those sessions, when a request matches one of the descriptions below, read that skill's SKILL.md from `pm-tactical/skills/` and follow it exactly, as if it had fired natively:

- Model choice / "which model should I use" / cost-per-task → `pm-tactical/skills/model-complexity-router/SKILL.md`
- Generate an artifact and validate it against a spec / self-QA → `pm-tactical/skills/builder-validator/SKILL.md`
- Improve or tune an existing prompt → `pm-tactical/skills/prompt-optimizer-loop/SKILL.md`
- Audit MCP connectors / context filling up too fast → `pm-tactical/skills/cli-over-mcp-auditor/SKILL.md`
- Set up project memory / remember stakeholders across sessions → `pm-tactical/skills/pm-context-system/SKILL.md`

## Session header protocol
On the first substantial prompt of a session, run whichever of model-complexity-router, cli-over-mcp-auditor, and pm-context-system have something to say *at that moment* and combine their lines into ONE compact header (max 4 lines) above the task response, instead of three separate interruptions. Each skill stays silent when it has nothing useful to say — an empty check contributes zero lines to the header, not a placeholder line.

This header is a formatting convenience for the first prompt only, not a firing-frequency limit. Each skill keeps following its own SKILL.md trigger rules afterward, independently of the header and of each other:
- model-complexity-router keeps firing its own compact line on every later distinct task handoff (not just the first).
- pm-context-system keeps proposing its one-line "Log to memory" entry whenever a later decision or fact worth keeping surfaces (not just the first).
- cli-over-mcp-auditor's proactive check is genuinely once per session — its Step 0 doesn't re-fire after the first prompt.

## Repo owner
Abhillash Jadhav — github.com/Abhillashjadhav
