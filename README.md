# AI PM Skills Marketplace

**Install focused Claude Code plugins for the product decisions that make AI systems expensive, unreliable, or difficult to ship.**

This repository is the distribution hub for four installable plugins. Each plugin solves a distinct job, ships examples and validation fixtures, and is designed to produce a useful artifact within one working session.

## Install your first plugin

```bash
claude plugin marketplace add Abhillashjadhav/AI-PM-essential-skills
claude plugin install pm-verifier@ai-pm-skills
```

Then paste a feature spec and ask:

```text
Create an eval for this feature.
```

`pm-verifier` returns binary release gates, a calibrated judge rubric, and a runnable local evaluation harness.

## Choose the job you need done

| Plugin | Use it when you need to… | Ask Claude Code | First useful result |
|---|---|---|---|
| **[pm-verifier](pm-verifier/)** | Turn a PRD or feature spec into a verification layer | `Create an eval for this feature` | Quality gates, judge rubric, judge prompt, and runnable harness |
| **[pm-tactical](pm-tactical/)** | Make daily PM work cheaper, faster, and self-checking | `Check whether this task needs a stronger model` | Model routing, frozen-spec validation, prompt optimization, context audit, or project-memory update |
| **[loop-designer](loop-designer/)** | Convert a recurring task into a bounded autonomous workflow | `Turn this recurring task into a guarded loop` | Loop specification, five guardrails, and Routine plus cron runners |
| **[mcp-migration-auditor](mcp-migration-auditor/)** | Check MCP configurations against the 2026 specification changes | `Audit my MCP setup` | Per-server `BREAKS`, `DEGRADED`, or `SAFE` verdicts with cited fixes |

Install any plugin with the same two-step pattern:

```bash
claude plugin marketplace add Abhillashjadhav/AI-PM-essential-skills
claude plugin install <plugin-name>@ai-pm-skills
```

## See the outputs before installing

### Spec → verification system

`pm-verifier` separates binary, disqualifying failures from gradual quality criteria:

```text
FEATURE: AI support-ticket summarizer

RELEASE GATES
1. No fabricated customer facts — automatic failure
2. Required escalation reason present — automatic failure
3. No restricted personal data in output — automatic failure

JUDGE RUBRIC
- factual completeness: anchored 1–5
- actionability: anchored 1–5
- concise communication: anchored 1–5

HARNESS
prepare.py → run.py → report.py
```

See the complete workflow in [`pm-verifier`](pm-verifier/).

### Recurring task → guarded loop

`loop-designer` makes the safety structure explicit before generating a scheduler:

```text
Discover → Plan and deduplicate → Execute → Independent Verify → Stop or Repeat

Required guardrails:
- iteration cap
- cost ceiling
- cross-run seen log
- destructive-action allowlist
- completion and failure notification
```

See the worked example in [`loop-designer`](loop-designer/).

### MCP config → migration decision

`mcp-migration-auditor` converts configuration evidence into a prioritized action table:

```text
| Server | Status   | Reason                | Required action |
|--------|----------|-----------------------|-----------------|
| api    | BREAKS   | session dependency    | migrate state   |
| local  | SAFE     | stdio unaffected      | none            |
```

See the sample audit in [`mcp-migration-auditor`](mcp-migration-auditor/).

## Product principles

- **One plugin, one decision job.** Installation should not require learning an operating system.
- **Outputs over prompt collections.** Each plugin produces a concrete artifact a PM or team can inspect and use.
- **Verification before confidence.** Claims are bounded by tests, fixtures, official sources, or explicit limitations.
- **Human judgment remains accountable.** The plugins structure decisions; they do not own product responsibility.
- **No silent success.** Missing evidence, incompatible inputs, and unverifiable outcomes must remain visible.

## Marketplace structure

| Path | Purpose |
|---|---|
| [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) | Installable marketplace catalogue |
| [`pm-verifier/`](pm-verifier/) | Spec-to-evaluation plugin |
| [`pm-tactical/`](pm-tactical/) | Daily AI PM workflow plugin |
| [`loop-designer/`](loop-designer/) | Guarded-loop design plugin |
| [`mcp-migration-auditor/`](mcp-migration-auditor/) | MCP compatibility and migration plugin |
| [`tests/`](tests/) | Manifest, trigger, policy, and known-answer fixtures |

## Additional tools in this repository

These remain available but are not the four marketplace products above:

- [`token-cost-estimator/`](token-cost-estimator/) — compare projected model cost and latency; verify current prices from official sources.
- [`eval-rubric-generator/`](eval-rubric-generator/) — an earlier rubric-focused skill; `pm-verifier` is the broader verification product.
- [`context-auditor/`](context-auditor/) — identify poisoning, distraction, and conflicting supplied context.
- [`concise-rewriter/`](concise-rewriter/) — reduce supplied text and report token change.
- [`context-port/`](context-port/) — separate local-first context-package validation and migration toolkit.

Keeping these boundaries explicit prevents older utilities from competing with the marketplace’s current products.

## Verify the repository

```bash
python3 scripts/check_repository_integrity.py
python3 -m unittest discover -s context-port/tests -q
```

The public-smoke workflow verifies the marketplace manifest, plugin layout, repository links, additional standalone skills, and ContextPort’s deterministic quickstart from a clean checkout.

What this does **not** certify:

- behavioural quality across every live model and environment;
- current provider pricing or model availability;
- compatibility with every Claude Code or MCP release;
- product outcomes without human review of the generated artifacts.

## Contributing

Keep each contribution inside one product boundary. New marketplace plugins must solve a distinct decision job, declare their input/output contract, include fire and no-fire fixtures, provide a known-answer example, and state evidence limitations. Avoid adding generic prompt collections that duplicate an existing plugin.

## License

MIT.
