---
name: eval-engine
description: Use this skill when the user pastes a feature spec, PRD, or task description and wants to create an eval, write an eval, build an eval rubric, define good, test this AI feature, generate a verification layer, set up an LLM judge, grade outputs, add quality gates, or asks "how do I measure" whether the feature works. Produces three artifacts from the spec — 3-6 binary disqualifying gates each marked with WHY it is a gate and not a score, a calibrated 4-7 criterion LLM-judge rubric on a 1-5 scale with anchors, worked examples, and a paste-ready judge prompt, and a runnable pure-Python-stdlib harness (prepare.py, run.py, report.py) that applies gates first so any gate failure is an automatic fail, then rubric scoring wired to the user's own Claude session with no API keys. Do NOT use for running or debugging an existing eval suite, for QA of non-AI features, or for one-off review of a single output with no spec attached.
---

# Eval Engine

Turn a feature spec into a complete verification layer: binary gates, a calibrated LLM-judge rubric, and a runnable harness. Spec in, eval out.

## The one distinction that matters

**Gates are binary, disqualifying, and invisible when passing.** A gate failure makes the output unshippable regardless of how good everything else is — fabricated claims, missing required fields, safety violations. Nobody celebrates a passed gate; a passed gate produces zero lines of output.

**Rubric criteria are gradual and tradeable.** A 3 on conciseness can be worth accepting for a 5 on accuracy. Rubric scores rank quality among outputs that already cleared every gate.

If a check can be "mostly passed," it is a rubric criterion. If partial credit is meaningless, it is a gate. Never average gates into a score — see `references/gate-design.md` for the full test.

**Human-vs-judge disagreement is calibration signal, not failure.** When the LLM judge scores a case 4 and the PM says 2, that gap is data about a vague anchor — tighten the anchor, re-run. See `references/rubric-calibration.md`.

## Step 1 — Extract the testable surface

Read the spec. List what the feature must never do (gate candidates) and what makes its output better or worse (rubric candidates). If the user gave no concrete spec, PRD, or task description, stop and ask for one — never generate an eval for a hypothetical feature. If the spec is silent on a domain fact a gate needs (a policy value, a required field list, a safety boundary), ask — never invent it.

## Step 2 — Binary gates (3-6)

Output this exact format per gate:

```
GATE G<n>: <name>
CHECK: <the binary yes/no test, mechanically checkable where possible>
WHY A GATE, NOT A SCORE: <one sentence — why partial credit is meaningless here>
TYPE: mechanical (regex/field/length) | judge (binary LLM verdict)
```

Rules:
- 3 to 6 gates. Fewer than 3 means the unshippable failure modes weren't found; more than 6 means scores are masquerading as gates.
- Every gate must state WHY it is a gate. If the WHY reads like "because quality matters," it is a rubric criterion — move it.
- Prefer mechanical gates (checkable in code) over judge gates wherever the spec allows.

## Step 3 — Calibrated LLM-judge rubric (4-7 criteria)

Per criterion:

```
C<n>: <criterion name> — <one-line definition>
  1 = <what a 1 concretely looks like for THIS feature>
  5 = <what a 5 concretely looks like for THIS feature>
  WORKED EXAMPLE: <a short sample output fragment + the score it earns + why>
```

Then emit a **judge prompt block** — a fenced, self-contained prompt the user can paste into any LLM. It must include: the role framing, the gates that need judge verdicts (binary PASS/FAIL each), all rubric criteria with anchors, the required JSON output shape (`{"gate_answers": {...}, "scores": {...}, "notes": "..."}`), and an instruction to score conservatively when uncertain.

Rules:
- Anchors must be feature-specific. "1 = bad, 5 = good" is a lint failure, not an anchor.
- Every criterion gets one worked example. No worked example, no criterion.
- 4 to 7 criteria. Cut overlapping criteria before adding new ones.

## Step 4 — Runnable harness

Scaffold this structure for the user (templates ship in this skill's `harness/` directory — copy them, then generate the three JSON/MD config files from Steps 2-3):

```
eval/
├── gates.json        ← generated from Step 2
├── rubric.json       ← generated from Step 3
├── judge_prompt.md   ← generated from Step 3
├── cases/            ← user adds test cases as {id, input, output} JSON
├── judgments/        ← judge verdicts land here (see flow below)
├── prepare.py        ← validates cases/, writes prepared_cases.json
├── run.py            ← gates first (any failure = automatic FAIL), then rubric
└── report.py         ← pass/fail table + score distribution → report.md
```

The flow, stated to the user exactly once: `prepare.py` validates test cases; `run.py` applies mechanical gates in code, and for judge gates + rubric scoring it writes one prompt file per case into `judgments/` — the user pastes each into their own Claude session (or has this session fill them) and saves the JSON reply next to it; re-running `run.py` picks up the verdicts and finalizes; `report.py` renders the markdown report. Pure Python stdlib, no API keys, no network.

## Step 5 — Calibrate before trusting

Tell the user to hand-score 3-5 cases themselves before trusting judge scores, then compare against the judge using the loop in `references/rubric-calibration.md`. Disagreement ≥2 points on any criterion → rewrite that anchor, not the judge.

## Hard rules

- **Never invent domain facts** to fill a gate or anchor — no made-up policy windows, field names, thresholds, or safety rules. Ask the user; a gate built on a fabricated fact is worse than no gate.
- **Never emit a gate without its WHY.** The WHY line is what stops gate/score drift over time.
- **Never present the rubric as objective measurement.** Judge scores are calibrated judgments; the skill must state this once in its output, and the harness report labels scores as judge-assigned.
- **Gates always run first.** The harness never rubric-scores a gate-failed case; a beautifully written fabrication is still a FAIL.
- **All three artifacts or none.** Gates without a harness don't get run; a rubric without gates lets unshippable output win on style. If the user wants only one artifact, produce it but say what risk the missing pieces leave open.

## Limitations

- Gate and rubric quality is bounded by spec quality: a vague spec yields judge-heavy gates and looser anchors — the skill flags which anchors are weakest rather than hiding it.
- The harness performs no LLM calls itself; scoring latency depends on the user's own session filling `judgments/`, and results are only as consistent as the judge model used.
- Rubric scores from a single judge run are noisy; the calibration loop reduces but never eliminates judge-human gaps.
- Mechanical gates cover only what regex/field/length checks can express; semantic failures (subtle fabrication, tone violations) require judge gates, which are slower and probabilistic.
