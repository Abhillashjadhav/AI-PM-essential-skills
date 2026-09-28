# Marketplace validation evidence

Combined code was checked at `9f78447` on 2026-09-28; subsequent documentation
clarifications leave that runtime and validator code unchanged. CI must also
pass on the final PR heads before merge.

| Check | Observed result |
|---|---|
| Verifier unit suite | 95 passed |
| Validator/PR gate unit suite | 24 passed |
| ContextPort unit suite | 107 passed |
| Repository integrity | PASS: 8 plugins, 3 standalone skills, 19 READMEs |
| Every tracked skill | 16/16 metadata checks passed |
| Complete PR required-check runner | PASS: diff, Python syntax, privacy, skill-impact detection and its unit suites |
| Graph contract and synthetic runner | PASS; AWAITING_HUMAN_APPROVAL, no external actions |
| Full-skill CLI negative control | Valid fixture passes; malformed internal Unicode-path skill fails |

New regressions cover stale counts in all three public entry points, omitted and
duplicated catalogue rows, missing plugin READMEs, manifest count changes,
non-object manifests, and internal/Unicode/newline skill paths. The workflow runs
all-skill lint and verifier tests on every PR, without a product path filter.

## Remaining limitations

The catalog reference replay still exits 1 (50/52 revision checks); see the
[reconciliation](2026-09-28-marketplace-reconciliation.md). Its D4/D2 repairs and
later grader PRs were not merged into this change. Passing marketplace checks
does not convert that reference into a validated grader.

Live plugin installation, product-specific behavior, state isolation beyond the
trusted adapter, authenticated approval and a real grader-contract exit test
remain unverified or outside the shipped runtime. The two bounded skill
exercises are samples, not a general quality claim.

Human review and merge approval remain required by `AGENTS.md` and `CLAUDE.md`.
