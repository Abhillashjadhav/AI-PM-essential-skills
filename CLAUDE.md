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

## Skill routing (Claude Code web fallback)
Native plugin auto-fire works in CLI/desktop; Claude Code web sessions do not load plugin skills into the invocable set. When a request in a web session matches one of the descriptions below, read that skill's SKILL.md from `pm-tactical/skills/` and follow it exactly, as if it had fired natively:

- Model choice / "which model should I use" / cost-per-task → `pm-tactical/skills/model-complexity-router/SKILL.md`
- Generate an artifact and validate it against a spec / self-QA → `pm-tactical/skills/builder-validator/SKILL.md`
- Improve or tune an existing prompt → `pm-tactical/skills/prompt-optimizer-loop/SKILL.md`
- Audit MCP connectors / context filling up too fast → `pm-tactical/skills/cli-over-mcp-auditor/SKILL.md`
- Set up project memory / remember stakeholders across sessions → `pm-tactical/skills/pm-context-system/SKILL.md`

## Repo owner
Abhillash Jadhav — github.com/Abhillashjadhav
