# pm-claude-skills

**4 Claude Code skills built specifically for AI Product Managers.**  
Not in Anthropic's official library. Not in the cookbook. Shipped and tested.

Each skill solves a problem that costs AI PMs real time and real money — before, during, and after they ship.

---

## Skills

| Skill | What it does | Install link |
|---|---|---|
| [token-cost-estimator](./token-cost-estimator/) | Pre-flight cost + latency comparison across model choices | [↗](#token-cost-estimator) |
| [eval-rubric-generator](./eval-rubric-generator/) | Turns a feature spec into a binary pass/fail eval checklist | [↗](#eval-rubric-generator) |
| [context-auditor](./context-auditor/) | Scans any context file and flags the 4 known failure modes | [↗](#context-auditor) |
| [concise-rewriter](./concise-rewriter/) | Compresses verbose output and reports a real token delta | [↗](#concise-rewriter) |

---

## Install all four (2 minutes)

```bash
# Clone the repo
git clone https://github.com/Abhillashjadhav/pm-claude-skills
cd pm-claude-skills

# Install to your personal Claude Code skills directory
mkdir -p ~/.claude/skills
cp -r token-cost-estimator ~/.claude/skills/
cp -r eval-rubric-generator ~/.claude/skills/
cp -r context-auditor ~/.claude/skills/
cp -r concise-rewriter ~/.claude/skills/
```

Skills hot-reload — no restart needed. Invoke any skill via its slash command.

---

## token-cost-estimator

**Invoke:** `/token-cost-estimator`

Most teams pick a model and discover the bill later. This skill flips that.

Paste a prompt + your candidate models → get a projected cost and latency comparison before a single token runs in production. Built for the AI PM who owns inference economics, not just feature specs.

**What it does:**
- Estimates input + output token count for your prompt
- Projects cost across multiple Claude models side by side
- Surfaces latency tradeoff (speed vs. quality vs. cost)
- Flags if a smaller model is likely sufficient for the task

**Test input:**
```
/token-cost-estimator

Prompt: [paste your system prompt here]
Models to compare: claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5
Expected output length: ~500 tokens
```

**Expected output:** A side-by-side cost + latency table with a recommendation.

---

## eval-rubric-generator

**Invoke:** `/eval-rubric-generator`

The most important thing an AI PM can do before shipping is define what "good" looks like. Most skip it. This skill forces the discipline.

Paste a feature spec or product requirement → get a binary yes/no rubric back. Every dimension is pass/fail — no partial credit, no vibes. Plug the output directly into your eval harness or LLM-as-judge setup.

**What it does:**
- Reads your spec and extracts the core output requirements
- Generates 5–10 binary (yes/no) evaluation criteria
- Labels each criterion as a hard gate (ship-blocker) or soft check
- Outputs in a format ready to drop into Braintrust, DeepEval, or a manual review sheet

**Test input:**
```
/eval-rubric-generator

Feature spec: A customer support agent that answers billing questions.
It should be accurate, cite the correct policy, avoid hallucinating charges,
and escalate when it cannot answer with confidence.
```

**Expected output:** A numbered pass/fail rubric with gate labels.

---

## context-auditor

**Invoke:** `/context-auditor`

Context poisoning is the #1 silent killer of agent reliability. Most teams find out in production.

This skill scans your CLAUDE.md, system prompt, or any assembled context file and flags the four known context failure modes before your agent sees them. Based on Drew Breunig's failure taxonomy — the framework Anthropic references but doesn't ship a diagnostic for.

**The four failure modes it checks:**
1. **Context Poisoning** — a hallucination or stale fact has made it into the context and will be repeated downstream
2. **Context Distraction** — the context is so long the model over-indexes on history instead of the current task
3. **Context Confusion** — superfluous information is present that degrades response quality
4. **Context Clash** — conflicting instructions or facts exist in the same context window

**Test input:**
```
/context-auditor

[paste your CLAUDE.md or system prompt here]
```

**Expected output:** A flag-by-flag audit with line-level citations and a severity rating (Critical / Warning / Clean).

---

## concise-rewriter

**Invoke:** `/concise-rewriter`

Verbose model output costs money twice — once in output tokens, once in the time it takes someone to read it. This skill fixes both.

Paste any LLM output → get a compressed version back, plus a real before/after token count and percentage reduction. Not a summary. A rewrite that preserves every piece of meaning while stripping everything the model added for padding.

**What it does:**
- Rewrites the output at the same information density, shorter
- Reports exact before token count, after token count, and % reduction
- Flags specific patterns that caused bloat (hedges, restated context, filler transitions)
- Works on any output: agent responses, PRD drafts, model-generated summaries

**Test input:**
```
/concise-rewriter

[paste verbose model output here]
```

**Expected output:** Rewritten text + token delta table + bloat pattern breakdown.

---

## How to test each skill

Each skill has a `test/` folder with:
- `input.md` — a real example input
- `expected-output.md` — what a good output looks like
- `eval-notes.md` — what to check for and what counts as a failure

Run a skill → compare your output against `expected-output.md` → if it diverges, check `eval-notes.md` to understand why.

---

## Why these four

These skills exist at the intersection of three disciplines every serious AI PM has to own:

- **Evals** — defining and measuring what "good" looks like before you ship
- **Context engineering** — what the model sees is the product; it has to be clean
- **Inference economics** — cost and latency are product decisions, not engineering afterthoughts

Nothing in Anthropic's official skill library covers this PM-specific surface. These do.

---

## Known constraints

- `pm-tactical` installs and enables correctly in Claude Code web, but web sessions do not load plugin skills into the invocable set (verified 2026-07-04). Native auto-fire works on CLI/desktop. On web, the supported path is the CLAUDE.md "Skill routing (Claude Code web fallback)" section, which tells Claude to read and follow the matching SKILL.md manually.

---

## Contributing

PRs welcome. Every PR is reviewed by the repo's PR agent before merge.

Open an issue if a skill produces output that fails its own eval criteria — that's the highest-quality signal for improvement.

---

## License

MIT. Use freely, fork freely, ship freely.

---

*Built by [Abhillash Jadhav](https://github.com/Abhillashjadhav) — GenAI PM. Evals, context engineering, agentic reliability.*
