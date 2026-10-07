---
name: ai-workflow-comparison
description: Use this skill when an AI PM asks to compare an AI-assisted workflow with the standard workflow, plan a bounded workflow comparison, freeze eligible tasks before assignment, measure human effort including review and rework, or audit customer outcomes per measured human hour without dropping failed or unfinished work. Guides manual collection and produces a local frozen plan, results template and descriptive accounting from supplied CSVs. Do NOT use for statistical inference, causal certification, ROI, a ship or kill recommendation, live provider calls, or model-output grading and release gates.
argument-hint: <declared workflow outcome and window, frozen units CSV, then results CSV>
---

# AI Workflow Comparison

Help the PM define a comparison, collect observations and read customer
outcomes beside measured human work. Use the [bundled tool](trial_kit.py) to
freeze assignments, create a results template and audit supplied records.
See [README](README.md) for the input contracts and synthetic examples.

In Claude Code, the explicit command is `/pm-tactical:ai-workflow-comparison`.
An example request is: “Compare AI-assisted support replies with our standard
workflow. Help me define customer success and collect all human effort.”
The first useful result is a collection plan with unresolved facts named;
once the inputs are complete, create frozen assignments and a blank results
sheet in the user's local workspace. No separate UI is required.

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

1. **Define collection before assignment.** Obtain the declared binary outcome,
   common UTC window, eligibility rule, complete units/strata, seed chosen before
   assignment, spillover/independence rationale, human-time method and measured/
   omitted work. Name who freezes the list, logs effort and checks outcomes and
   complete follow-up. Use the [completed collection plan](examples/collection-plan-completed.md)
   for its structure; its fictional facts are not the user's observations.
   Preserve unresolved questions rather than supplying optimistic assumptions.
2. **Prepare local files.** Read the bundled [templates](templates/). Use the
   user's chosen local directory or a new directory in the current project.
   Prepare `design.json` and `units.csv` from supplied facts, retaining the
   compatible `trial_id` field. Require complete design inputs before `plan`.
   Copy the optional `effort-log.csv` for manual logging; there is no automatic
   importer, model runner or customer observation collector.
3. **Freeze and preserve.** Run `plan` with design/units and a new output path.
   Explain the seed, balance and hash manifest. These are reproducibility
   records, not authenticated pre-registration or proof of design validity.
   Preserve original inputs and the plan; never edit or overwrite an existing
   plan to accommodate later results.
4. **Create and fill the results sheet.** Run `results-template` with the plan
   and a new CSV path. Keep every original ID. The PM records actual workflow,
   status, yes/no customer success and all four observed effort totals for
   every task. Sum manually logged person-stage minutes into these fields.
   Reconcile each per-task stage total against the effort logs; the CLI checks
   submitted totals, not whether that manual transfer was accurate.
   Prefilled horizon dates are required cutoffs, not completed follow-up.
   A zero must be observed zero; never fill blanks with plausible values.
5. **Audit at the mature common cutoff.** Run `audit` against the original plan
   and all assigned results. Every row declares exactly the frozen
   `observed_through` horizon. Report BLOCKED data gaps before comparing arms;
   help the PM resolve the missing records without removing assigned tasks.
6. **Present joint evidence.** Show N, customer success counts/rates, all effort
   stages, total measured hours, deviations, strata and outcomes/hour together.
   Keep measured scope and omissions visible. Ask the PM to review selection,
   interference, measurement and customer-outcome tradeoffs; the tool does not
   make the resulting product decision.

## Bundled runtime from the user's project

Use the quoted absolute script path below. Claude Code substitutes
`${CLAUDE_SKILL_DIR}` in this skill's Markdown with the installed skill
directory; it is not a shell environment variable to assume is set. Replace
`/absolute/path/to/comparison` with the actual local directory from step 2.
Inputs and new outputs belong there, not inside the installed plugin cache.

```bash
python3 "${CLAUDE_SKILL_DIR}/trial_kit.py" plan --design "/absolute/path/to/comparison/design.json" --units "/absolute/path/to/comparison/units.csv" --out "/absolute/path/to/comparison/plan.json"
python3 "${CLAUDE_SKILL_DIR}/trial_kit.py" results-template --plan "/absolute/path/to/comparison/plan.json" --out "/absolute/path/to/comparison/results.csv"
python3 "${CLAUDE_SKILL_DIR}/trial_kit.py" audit --plan "/absolute/path/to/comparison/plan.json" --results "/absolute/path/to/comparison/results.csv" --as-of YYYY-MM-DDTHH:MM:SSZ
```

Replace the audit cutoff with the actual mature horizon and fill results from
observations before auditing. The bundled tool needs Python 3.11+ and its
standard library only. It makes no model calls or network requests. Claude
Code host access and ordinary tool permissions still apply. If Python or file
access is unavailable, provide the collection checklist and template fields,
and state exactly which files or commands were not created or executed.

## Limitations

The tool checks submitted data, not whether declarations or observations are
true. It cannot detect dishonest eligibility, post-assignment task selection,
shared-worker carryover, leakage, other concurrent changes or overlapping
person-time. It supports no adaptive, cluster or crossover trial design. Actual
workflow crossovers are recorded as deviations under original assignment.
Offline copied-plugin checks, CSV audits and synthetic UAT do not establish
native-host installation, trigger quality or live productivity gains.
Read [source notes](references/source-notes.md) before using
external studies as motivation; their settings and evidence types differ.
