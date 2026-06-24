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

## Repo owner
Abhillash Jadhav — github.com/Abhillashjadhav
