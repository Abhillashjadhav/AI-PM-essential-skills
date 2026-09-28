# Bounded skill exercises

Two fresh agent contexts read the revised local skill files. These are
author-orchestrated spot checks, not independent adjudication, a trigger-accuracy
study, or proof of Claude Code plugin installation. No external tools, paid API
calls or repository mutations were part of either task. Only excerpts are
retained below; these are not full transcripts.

## Connector cost

Supplied facts: GitHub has 26 connected tools, Weather has 3; definitions are
deferred, names visible, no tokenizer and unknown window size. GitHub is used
weekly; Weather was unused today. Asked whether to switch/remove and what
percentage would be saved.

Observed response excerpt:

> The percentage you would save is unknown.

It separated deferred tools from injected schemas, did not manufacture a token
estimate, and asked for workflow/permission evidence before recommending CLI
replacement. This single case matched the revised guidance.

## Daily issue triage

Supplied task: fictional repository, daily 07:00 triage, at most 25 issues per
PR, 26 old unprocessed issues, manual merges delayed by days, local cron, no
configured locking or budget enforcement.

Observed response excerpt:

> Issue 26 remains eligible regardless of its age.

The proposed workflow paused on a pending PR, deduplicated by issue identity,
verified before publication and flagged host controls as prerequisites. It
labelled the same-model semantic check self-review. It also proposed a timezone,
a $2 budget and a hypothetical budget-controller interface; those are not
owner-approved settings or shipped tools. The proposed runner was not executed
or added to this repository. Those configuration choices still need owner input
before any real deployment.

The useful result is narrower than “the skill works”: these two prompts exposed
no regression in the corrected deferred-tool and overflow/pending-PR behaviors.
