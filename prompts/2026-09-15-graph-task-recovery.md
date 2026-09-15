# Graph task recovery correction

Clarify and demonstrate coordination of distinct atomic tasks, each with bounded
attempts and independent checks. Establish what happens when the worker responsible
for one required task fails. Preserve valid completed sibling tasks.

The graph contract at upstream 7afd999 declares retries, timeouts and checkpoints,
but its sample returns fixed PASS artifacts without those recovery mechanisms.
Correct the synthetic sample using its existing product, quality and safety tasks.

Acceptance: register tasks and inputs before dispatch; recover worker failures
within task and graph budgets; preserve verified results; require every task at
the join; fail visibly on missing registration, changed inputs or exhausted
recovery; never reset budgets on resume or claim a release was approved.

Use synthetic inputs and Python's standard library only. This remains a reference
for the committed topology, not a production runtime or a Loop Engineering rewrite.
Prepare a draft PR with execution evidence for human review.
