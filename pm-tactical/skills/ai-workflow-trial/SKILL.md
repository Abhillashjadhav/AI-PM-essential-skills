---
name: ai-workflow-trial
description: Use this skill when an AI PM wants to plan a bounded AI workflow productivity trial, freeze eligible tasks before assignment, measure human effort including review and rework, or audit outcomes per human hour without dropping failed or unfinished work. Produces a local frozen plan and descriptive accounting from supplied CSVs. Do NOT use for statistical inference, causal certification, ROI, a ship or kill recommendation, live provider calls, or model-output grading and release gates; those belong to separate evaluation workflows.
argument-hint: <declared workflow outcome and window, frozen units CSV, then results CSV>
---

# AI Workflow Trial Kit

Use the [local stdlib tool](trial_kit.py) to freeze a small workflow trial and
account for human effort. This is a measurement aid, not a design validator.
See [README](README.md) for exact input contracts and runnable examples.

## Hard rules

1. Freeze outcome, common UTC window, eligible unit IDs, strata and seed before
   assignment. Do not select an easier subset after results or reroll the seed.
   Only parallel unit randomization with even-sized strata is supported. If
   interference/spillover is yes or unknown, stop and request external design
   review. A no-spillover declaration does not prove independence.
2. Name the measured scope of all four effort fields and explicitly list omitted
   work. Cover preparation/prompting, drafting, review, rework, coordination and
   handoffs, customer follow-up and failure recovery where relevant. Never claim
   all human effort when any relevant category is unmeasured. Allocate each
   person's active minute once across overlapping tasks/stages; sum different
   people's minutes, and do not substitute concurrent agent wall time or passive
   model waiting for active human labor.
3. Keep every assigned unit, including failed, unfinished and crossover work,
   under its original assignment. Record observed effort through the common
   horizon. A mature unresolved unit is unsuccessful there, not proof it will
   never succeed. Missing rows or blank effort are data gaps, never zero labor.
4. Show raw denominators, success counts/rates, measured effort totals and
   successful outcomes per measured human hour together. A larger hourly ratio
   can coexist with fewer successful customer outcomes. Name no workflow winner
   from that ratio; produce no significance test, p-value, causal-validity badge,
   ROI or ship/kill verdict. Zero effort yields an undefined hourly ratio.
5. Label synthetic examples visibly. Never invent observations, model runs,
   measurement validity or owner approval. Keep real records local and avoid
   private data in public fixtures, source archives or demo footage.

## Workflow

- Obtain the declared binary outcome, common horizon, eligibility rule, frozen
  units/strata, spillover/independence rationale and human-time method. Preserve
  unresolved questions; do not fill them with an optimistic assumption.
- Locate this loaded skill's directory; invoke its `trial_kit.py` by that path.
  It needs Python 3.11+ only. No model, account or additional installation is used.
- Run `plan` with design/units and a new output path. Explain the seed, balance
  and hash manifest. These are reproducibility records, not authenticated
  pre-registration or proof of randomization validity.
- Run `results-template` with that plan and a new output CSV. Keep every original
  ID and fill observations from the ready-to-fill [templates](templates/).
  Prefilled horizon dates are required cutoffs, not proof of completed follow-up.
- At the mature declared cutoff, run `audit` against the original plan and every
  assigned result. Rows declare exactly the same `observed_through` horizon.
  Report BLOCKED data gaps before comparing arms. Do not overwrite the plan.
- Present descriptive totals, status/deviation counts and strata. Ask the PM to
  review selection, interference, measurement and customer-outcome tradeoffs;
  the tool does not make the resulting product decision.

## Limitations

The tool checks submitted data, not whether declarations or observations are
true. It cannot detect dishonest eligibility, post-assignment task selection,
shared-worker carryover, leakage, other concurrent changes or overlapping
person-time. It supports no adaptive, cluster or crossover trial design. Actual
workflow crossovers are recorded as deviations under original assignment.
CSV audits and synthetic UAT do not establish installed skill quality or live
productivity gains. Read [source notes](references/source-notes.md) before using
external studies as motivation; their settings and evidence types differ.
