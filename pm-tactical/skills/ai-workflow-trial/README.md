# AI Workflow Trial Kit

Measure customer outcomes alongside the human work needed to produce them.
The local tool freezes a bounded plan, creates a ready-to-fill results sheet,
and checks that every assigned task remains in the accounting. It makes no
workflow-winner, causal, statistical, ROI or launch decision.

Python 3.11+; standard library only. No account, model calls, network or runtime
dependency installation. This is the sixth skill in pm-tactical. An installed
host can load [SKILL.md](SKILL.md); running the CLI does not verify host skill
installation or live trigger quality.

## Start here without code

Read the [completed collection-plan example](examples/collection-plan-completed.md)
first. It shows what to decide, who records the work, which tasks remain in the
trial and when follow-up closes. Then draft your own collection plan using those
headings: the change you want to compare, customer success rule, eligible tasks,
common horizon, recording responsibilities and measured/omitted human work.
Check the design with someone who can assess selection and spillover before
starting. There is no promised completion time.

You can collect the observations in a spreadsheet. Keep every frozen task ID,
log active person-minutes and customer outcomes, and compare success counts
beside the measured labor. The Python commands below are optional checks that
make missing records and immature follow-up explicit. The completed example is
fictional; it is a collection method to adapt, not evidence of an AI gain.

## Adapt this to your own workflow

1. **Choose the customer outcome and horizon before starting.** Examples: a
   support issue correctly resolved with no reopen by Friday, or a research
   handoff accepted without a required correction by the common cutoff. Define
   what counts as success, who records it, and how every task can get the full
   follow-up. Freeze eligibility and record all eligible IDs before assignment.
2. **Check whether this narrow design fits.** Use independent units and strata
   chosen before results, with an even count of at least two in each stratum.
   Shared customers, worker learning, shared drafts or carryover can create
   spillover. If it exists or is unknown, this tool blocks; seek external design
   review instead of changing the declaration to make the command run. Balanced
   assignments do not establish causal validity or a sufficient sample size.
3. **Name measured and omitted human work.** Copy [design.json](templates/design.json),
   [units.csv](templates/units.csv) and [effort-log.csv](templates/effort-log.csv)
   into a new local directory. Replace all placeholders. The design template is
   deliberately blocked until eligibility, spillover, dates and seed are resolved.
   Set a seed once before assignment; do not reroll it after seeing tasks or results.
4. **Freeze and keep the plan.** Run `plan`, then `results-template` below.
   Keep the original design, unit list and plan. The results template contains
   every original ID; blank observations must be filled from actual records.
5. **Log active person-minutes during work.** In the effort log, use stages
   `draft`, `review`, `rework`, `followup`; sum each task's observed minutes into
   the corresponding results fields. This optional log is a manual collection
   aid, not a validated importer. Record preparation/prompting, drafting, human
   review, corrections, recovery, coordination/handoffs and customer follow-up
   in the declared scope. Identify any omissions explicitly.
6. **Keep failures, unfinished tasks and deviations.** At the common horizon,
   mark observed status and success for every unit. Unresolved tasks are
   unsuccessful at that horizon; include all observed effort through it. Record
   the actual workflow even if it differs from assignment. Compare original
   assignment groups, never only completed tasks or only compliant tasks.
7. **Review outcomes and labor together.** Audit only after every task's full
   observation window is mature. Inspect N, successes, success rates, stage
   effort, total measured hours, deviations and outcomes/hour side by side.
   A higher ratio can coexist with fewer successful customer outcomes. Missing
   rows, effort or follow-up require fixing the records, not deleting tasks.

For one person using several agents at once, allocate each active minute once
across tasks and stages. Sum different people's labor: two people working for
five minutes contribute ten person-minutes. Passive model waiting is elapsed
time, not automatically active human work. If a shared team, onboarding or
infrastructure cost cannot be allocated, name it in `unmeasured_work`; the
reported ratio then covers the declared measured scope only. `[]` is a claim
of no omissions, not an independently verified fact.

## Local quickstart

From the repository root, enter this skill folder. Use a new output path for
each artifact; the tool refuses to overwrite existing files.

```bash
cd pm-tactical/skills/ai-workflow-trial
python3 trial_kit.py --version
python3 trial_kit.py plan --design examples/design.json --units examples/units.csv --out /tmp/trial-plan-new.json
python3 trial_kit.py results-template --plan /tmp/trial-plan-new.json --out /tmp/trial-results-blank-new.csv
python3 trial_kit.py audit --plan /tmp/trial-plan-new.json --results examples/results_fast_draft.csv --as-of 2026-09-08T00:00:00Z
python3 trial_kit.py audit --plan /tmp/trial-plan-new.json --results examples/results_favorable.csv --as-of 2026-09-08T00:00:00Z
python3 trial_kit.py audit --plan /tmp/trial-plan-new.json --results examples/results_ratio_tradeoff.csv --as-of 2026-09-08T00:00:00Z
python3 trial_kit.py audit --plan /tmp/trial-plan-new.json --results examples/results_gap.csv --as-of 2026-09-08T00:00:00Z
```

The last command intentionally exits **2 / BLOCKED**: one assigned unit is
missing. The preceding commands exit 0. Add `--format json` for unrounded
values, or `audit --out NEW_PATH` to save a JSON report. `--as-of` is the
declared observation cutoff, not an attestation from a trusted clock. In your
trial, replace example paths with your own filled files and actual mature
horizon; never relabel the fictional fixtures as observations.

## Synthetic test input and expected output

The six [example files](examples/) are transparent fictional records generated
by [generate_fixtures.py](examples/generate_fixtures.py). These are accounting
examples, not model runs or genuine workflow gains. To reproduce them in a
fresh directory, run `python3 examples/generate_fixtures.py --out NEW_DIRECTORY`.

All scenarios use the same frozen 32 tasks, four strata, seed 20261007 and
16 original assignments per arm. Each arm has one workflow deviation retained
under original assignment. Horizon: September 1–8, 2026, explicit UTC. Outcome:
correct resolution with no reopen by the horizon.

| Synthetic scenario / assignment | N | Customer successes | Success rate | Draft min | Review min | Rework min | Follow-up min | Measured min | Successes / measured hour |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Standard, all three examples | 16 | 14 | 87.5% | 192 | 64 | 32 | 32 | 320 | 2.625 |
| AI, fast draft | 16 | 10 | 62.5% | 64 | 112 | 160 | 64 | 400 | 1.500 |
| AI, favorable | 16 | 15 | 93.75% | 64 | 48 | 32 | 16 | 160 | 5.625 |
| AI, ratio tradeoff | 16 | 10 | 62.5% | 32 | 16 | 16 | 16 | 80 | 7.500 |

The fast-draft rows have **66.7% less drafting time**, calculated as
`(192 − 64) / 192`; total measured effort is 25% higher and customer successes
are lower. “66.7% faster” would be a different claim. The favorable rows
illustrate different submitted totals without establishing a winner. The
tradeoff rows show why the hourly ratio alone is insufficient: it rises while
successful customer outcomes fall from 14 to 10. None is evidence of a genuine
AI productivity improvement.

Standard: 14 completed, one failed, one unfinished. Fast-draft and ratio-tradeoff
AI: 10 completed, five failed, one unfinished. Favorable AI: 15 completed,
one unfinished. Mature unfinished work remains in both N and labor.

## Input contract

The design JSON has exactly the keys shown in [the design template](templates/design.json):
`schema_version=1`, ASCII `trial_id` (1–64 characters), `data_classification`
(`synthetic` or `observed`), `design=unit_randomized_parallel`, declared `outcome`,
UTC `window_start`/`window_end`, boolean `eligibility_frozen=true`, declared
`eligibility_rule`, `spillover=no`, declared `independence_basis`, declared
`human_effort_method`, `labor_scope` with exactly the four effort field names,
explicit `unmeasured_work` list, and integer `seed` from 0 to 2^63−1. Dates must
be real calendar timestamps in `YYYY-MM-DDTHH:MM:SSZ` form; end must follow start.

Units CSV has the exact header `unit_id,stratum`. IDs are unique ASCII letters,
digits, underscore, dot or hyphen, starting with a letter/digit (1–64 characters).
Strata are trimmed nonblank strings of at most 80 characters. Each stratum
needs an even count of at least two; assignment is 1:1 within it. The versioned
SHA-256 ranking is reproducible and invariant to input row order. It is not
cryptographic randomization, a validity test or a power calculation.

Results CSV has this exact header and one row per original unit:

```csv
unit_id,actual_arm,status,success,observed_through,draft_minutes,review_minutes,rework_minutes,followup_minutes
```

`actual_arm`: `standard_workflow`, `ai_workflow`, or `mixed`; `status`:
`completed`, `failed`, or `unfinished`; `success`: `yes`/`no` under the declared
outcome rule. A failed/unfinished unit cannot be successful. A completed unit
may be unsuccessful if it fails that rule. `observed_through` must equal the
frozen end for every row: capture effort/outcome through that horizon and exclude
later effort. The template's prefilled required date does not prove follow-up
actually occurred. Every effort field needs an observed finite nonnegative
number in minutes. Enter zero only for observed zero; never convert a blank or
missing task into zero. Zero total measured effort produces a null/undefined
hourly ratio, with success counts still visible.

The plan includes raw-file and canonical-content hashes, assignments, planning
version and a self-content hash. An audit rechecks embedded design/units,
assignments and hashes; it cannot compare original raw-file hashes without the
original files, authenticate the planning time, or prove that no one rerolled
the seed or rewrote a complete consistent plan. Preserve original files and
obtain separate design and measurement review.

## Validation and instructional demo

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/ai-workflow-trial -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 pm-tactical/skills/ai-workflow-trial/tools/run_uat.py
```

The UAT runs actual CLI subprocesses and independently checks complete coverage,
fixed-horizon blocking, zero-effort semantics and the synthetic accounting values.
It makes no model calls. The [scripted CLI walkthrough](demo/README.md) uses the
same synthetic inputs and computes its narration from actual CLI reports. No
accepted video is included. Its measurement method can be used manually in a
spreadsheet; the CLI makes missing records visible.

The submitted declarations cannot establish honest logging, independent tasks,
selection validity, interference, shared-worker learning, equal outcome
ascertainment or cause. No installed-plugin/live-model quality result is claimed.
See [research notes](references/source-notes.md) for bounded source context and
[the repository evidence table](../../../docs/VALIDATION.md) for product limits.
