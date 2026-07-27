---
name: ai-feature-kill-criteria
description: Define falsifiable assumptions, explicit kill thresholds, an evidence plan, and a decision date before an AI feature is built. Use when a team is excited by a demo, proposing an AI feature, debating whether to prototype, or continuing investment without clear stopping conditions. Do not use for post-launch evaluation or ordinary roadmap prioritization.
---

# AI Feature Kill Criteria

Prevent attractive AI demos from turning into open-ended investments.

## Required input

Ask for only what is missing:

1. The user problem and target user.
2. The proposed AI behavior.
3. The business or customer outcome expected.
4. Known constraints such as latency, cost, privacy, safety, or workflow fit.
5. The maximum evidence budget: time, users, data, or engineering effort.

Do not accept "we will know when we see it" as a success definition.

## Workflow

### 1. Separate the demo from the product claim

Write the product claim in this form:

> For [user], [AI behavior] will improve [observable outcome] because [mechanism].

Flag any part that is an aspiration rather than evidence.

### 2. Extract the assumptions

Create 3-7 assumptions across these categories:

- problem: the pain is frequent and important;
- behavior: users will trust, understand, and act on the output;
- capability: the system can perform on realistic inputs;
- workflow: the feature fits the real sequence of work;
- economics: latency and cost are viable at expected volume;
- risk: privacy, safety, compliance, and misuse remain inside acceptable bounds;
- adoption: the target user can discover and repeatedly use it.

Each assumption must be falsifiable. Replace vague wording such as "users will like it" with a measurable observation.

### 3. Define a kill threshold for every critical assumption

Use this format:

| Assumption | Evidence to collect | Continue threshold | Kill threshold | Decision owner |
|---|---|---|---|---|

A kill threshold must be observable and time-bounded. Examples:

- fewer than 4 of 10 target users complete the task without expert help;
- factual accuracy remains below 95% on the original failure set after two model or prompt iterations;
- p95 latency exceeds 3 seconds under expected concurrency;
- cost per completed task exceeds the current human-assisted path;
- more than 2% of high-risk outputs require correction;
- the workflow saves less than five minutes per task after two weeks of use.

Never invent thresholds. Propose clearly labelled defaults and require the user to approve or replace them.

### 4. Choose the cheapest decisive test

For each critical assumption, select the lowest-cost evidence that can change the decision:

- interview or observed workflow;
- concierge test;
- Wizard-of-Oz test;
- offline evaluation on a frozen failure set;
- shadow mode;
- limited pilot;
- production experiment.

Do not recommend building a full prototype when a cheaper test can falsify the assumption.

### 5. Lock the decision date

Specify:

- evidence collection window;
- maximum iteration count;
- decision date;
- named decision owner;
- allowed outcomes: `PROCEED`, `NARROW`, `PAUSE`, or `KILL`.

A missing decision date is a failed output.

### 6. Produce the decision contract

Return exactly these sections:

1. **Product claim**
2. **Critical assumptions**
3. **Kill-criteria table**
4. **Cheapest evidence plan**
5. **Decision date and owner**
6. **Current verdict**: `NOT READY TO BUILD`, `READY FOR BOUNDED TEST`, or `READY TO BUILD`
7. **What would change the verdict**

## Decision rules

- `NOT READY TO BUILD`: the problem, outcome, or critical assumptions are not measurable.
- `READY FOR BOUNDED TEST`: assumptions and thresholds exist, but decisive evidence is missing.
- `READY TO BUILD`: the highest-risk assumptions have passed their approved thresholds and remaining risks are explicitly accepted.

Do not convert missing evidence into confidence. Do not soften a kill threshold after seeing poor results unless the original threshold was demonstrably invalid; record that as a new decision contract.

## Limits

This skill structures a decision. It does not prove market demand, validate model performance, set thresholds without accountable human approval, or own the final investment decision.
