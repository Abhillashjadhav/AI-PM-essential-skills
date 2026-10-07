# Completed collection-plan example

**Classification: SYNTHETIC.** This is a filled plan for the bundled fictional
support comparison, not a real experiment, observed customer record or verified
productivity gain. Names below are roles, not people who ran a comparison.

| Decision | Completed example |
|---|---|
| Workflow change | Compare the existing support-resolution workflow with one that permits AI drafting. Human review and follow-up remain part of both workflows. |
| Customer success | A task is correctly resolved and has no reopen by the fixed September 8 cutoff. A draft alone is not success. The outcome recorder checks correctness and reopen status under the same rule in both groups. |
| Eligible population | All 32 fictional support tasks in `units.csv`, frozen before assignment. No task is removed because it is difficult, failed, unfinished or used the other workflow. |
| Unit and strata | One task per unit; eight each in account, billing, complex and simple. These categories are fixed before results. Each stratum has four original assignments per workflow. |
| Window | September 1, 2026 at 00:00:00 UTC through September 8 at 00:00:00 UTC. Effort and outcomes are recorded through this same end for every task; the collection owner verifies full follow-up before audit. |
| Assignment | Seed 20261007 chosen before assignment. Keep the original design, eligible list and generated plan; do not reroll the seed or select tasks after seeing the groups. |
| Independence premise | In this fictional example, tasks have no shared customer or worker carryover. In a real team, review learning, shared workers/drafts and interference first. If spillover is present or unknown, this v1 tool blocks and a design specialist must choose an appropriate design. A declaration does not prove independence. |
| Collection owner | A support operations coordinator freezes the list, stores the plan and checks that every assigned ID has a result row. |
| Effort recorders | Each person working on a task logs their own active minutes, task ID, stage, activity and recording timestamp during work. The coordinator totals these per task; they do not infer minutes from elapsed model wait. |
| Outcome recorder | A reviewer records actual workflow, completed/failed/unfinished status, yes/no success and verified observation-through date at the common horizon. Completed work can still be unsuccessful under the rule. |
| Review responsibility | A separate reviewer checks full coverage, recording scope, deviations, follow-up and the joint customer-outcome/labor tradeoff. The tool does not make the product decision. |

## What gets logged

| Results field | Included work | Collection rule |
|---|---|---|
| `draft_minutes` | Preparation, prompting and drafting | Record active time for all contributors, including setting up the prompt. |
| `review_minutes` | Human review | Record checking correctness and usability, even when a draft looks good. |
| `rework_minutes` | Corrections and failure recovery | Include repair attempts and effort on work that remains unresolved. |
| `followup_minutes` | Coordination, handoff and customer follow-up | Record active work through the common horizon, including checking for reopens. |

Allocate each person's active minute once across tasks and stages. Two people
working for five minutes contribute ten person-minutes; one person supervising
two agents for five minutes contributes five active person-minutes allocated
across the work. Passive waiting is not automatically labor. The blank effort
log is a manual collection aid; the tool does not verify overlapping time.

**Omitted work:** this fictional dataset declares none outside these four
fields. That is not independently verified. Before a real comparison, either allocate
relevant onboarding, training, shared coordination, tooling setup and recovery
to the measured scope or explicitly list them as omitted. Then describe the
ratio as successes per measured human hour; do not claim all human effort.

## Close the records without dropping tasks

At the common horizon, retain every original ID. For failed or unfinished tasks,
record the effort already observed and `success=no`; that means unsuccessful at
the horizon, not that the task will never succeed. Record workflow crossovers
or `mixed` as actual behavior, while preserving the original assignment for
comparison. A blank effort field or missing result row is a data gap, not zero.
If follow-up is incomplete for any task, the comparative audit is blocked.

The coordinator copies per-task labor totals and outcomes into the complete-ID
results sheet. Keep a spreadsheet if useful, or run the documented local CLI
checks. Review original N, success counts/rates, every effort stage, total
measured hours and outcomes/hour together. More outcomes per hour can coexist
with fewer successful customer outcomes; name no winner from that ratio.

**Evidence limit:** this plan and the bundled arithmetic are synthetic teaching
material. Scripted CLI acceptance and independent clean-package UAT verify
software behavior; neither establishes that a real PM can use the method well,
that the design fits a real team or that AI improves that workflow.
