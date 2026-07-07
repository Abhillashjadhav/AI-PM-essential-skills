# pm-verifier

**Spec in, verification layer out.** One skill — `eval-engine` — that turns any feature spec, PRD, or task description into the three artifacts every AI feature needs before it ships: binary quality gates, a calibrated LLM-judge rubric, and a runnable eval harness.

Built for the AI PM who owns "define good" — companion plugin to [pm-tactical](../pm-tactical/), same marketplace.

---

## Install (30 seconds)

```bash
claude plugin marketplace add Abhillashjadhav/AI-PM-essential-skills
claude plugin install pm-verifier@ai-pm-skills
```

Or commit it to your repo's `.claude/settings.json` so every contributor gets it on trust — see this repo's own settings file for the pattern.

## Use (60 seconds)

Paste a spec and ask:

```
Here's the spec for our AI ticket summarizer: [paste spec]
Create an eval for this.
```

Also fires on: "write an eval", "build an eval rubric", "define good for this feature", "how do I test this AI feature", "generate a verification layer", "set up an LLM judge", "how do I grade outputs", "add quality gates", "how do I measure whether this works".

You get back, in one pass:

1. **Binary gates (3-6)** — the disqualifying checks: fabricated claims, missing required fields, safety violations. Each states WHY it's a gate ("partial credit is meaningless here") and whether it's mechanically checkable or needs a judge. Any gate failure = automatic fail, no matter how good the rest is.
2. **Calibrated LLM-judge rubric (4-7 criteria, 1-5 scale)** — each criterion with a concrete "what a 1 looks like", "what a 5 looks like", and a worked example, plus a paste-ready judge prompt that returns structured JSON.
3. **Runnable harness** — `prepare.py` / `run.py` / `report.py`, pure Python stdlib, no API keys. Gates run first in code; judge scoring routes through your own Claude session via generated prompt files. `report.py` renders a pass/fail table and per-criterion score distribution to markdown.

A complete worked example (spec → all three artifacts → harness run on real cases) ships in `skills/eval-engine/examples/`.

## Before / after

| Without | With |
|---|---|
| "The demo looked good" is the eval | 3-6 explicit unshippable-output checks, run in code |
| Quality debates re-litigated every review | A frozen rubric with anchors both humans and judges score against |
| Judge scores trusted blind, or distrusted blind | A calibration loop: human-vs-judge gaps ≥2 points rewrite the anchor, not the verdict |
| Eval tooling blocked on eng time and API keys | A harness a PM runs locally in three commands, LLM judgment via their own session |

## The design stance

**Gates are binary, disqualifying, and invisible when passing. Rubric criteria are gradual and tradeable.** Mixing the two — averaging gates into scores, or treating "well-written" as a gate — is the root failure of most eval setups, and the one thing this skill refuses to do. Human-vs-judge disagreement is treated as calibration signal, not failure. Full reasoning in `skills/eval-engine/references/gate-design.md` and `references/rubric-calibration.md`.

## Testing

Three-gate harness, same convention as pm-tactical (`tests/eval-engine/fixtures.md`):
- **Gate 1** — plugin + marketplace manifests lint clean; SKILL.md frontmatter passes `tests/lint_skill.py`.
- **Gate 2** — trigger accuracy against the fixture phrasings (fire + no-fire).
- **Gate 3** — end-to-end: the included sample spec produces all three artifacts, and the harness runs the 2 included sample cases through prepare → run → report without error, including the pending-judgment round-trip.

## License

MIT, same as the repo.

---

*Built by [Abhillash Jadhav](https://github.com/Abhillashjadhav) — GenAI PM. Evals, context engineering, agentic reliability.*
