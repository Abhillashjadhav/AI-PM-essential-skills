# Eval contract: AI ticket summarizer

## Release question

Can the candidate summarize a support thread without inventing facts, losing
the escalation reason, using incorrect tool parameters, or silently skipping
a required workflow stage?

## Product response

The user-visible response is one JSON object with exactly:

- `summary` — a chronological summary under 600 characters;
- `customer_request` — one sentence stating what the customer wants.

The evidence adapter separately exposes sentiment, escalation reason, supported
claims, chronology, and operational metrics for grading.

## Enabled surfaces

- Outcome: required response, supported claims, sentiment, escalation reason,
  length, safety, and privacy.
- Tool trajectory: ordering, summarization, claim validation, and delivery use
  the correct ticket identity, message count, supported-claim count, and
  chronological order.
- System: intake, ordering, summarization, validation, and delivery all pass in
  the required order while preserving ticket identity and thread state.

Memory is not enabled because this feature does not promise persistent state.

## Automatic failure conditions

- A required response field is missing or incorrect.
- The summary exceeds 600 characters.
- A claim is not supported by the source thread.
- The escalation reason or sentiment is lost.
- The model processes the displayed newest-first thread as chronological.
- A tool receives the wrong ticket, message count, or supported-claim count.
- A required system checkpoint is absent, failed, or out of order.
- Ticket identity or thread state changes between workflow checkpoints.
- The workflow does not complete or reach delivery.
- The output promises a resolution or exposes an email address.

## Dataset

Three deterministic product use cases cover a blocked invoice export, an SSO
compatibility question, and account access blocked after MFA plus a password
reset.

Each case runs twice in a fresh adapter process. All trials must pass because
this is a regression suite.

## Operational guardrails

- Maximum latency: 1,000 ms per trial.
- Maximum total tokens: 500 per trial.
- Maximum retries: 0.
- Safety failures: 0.
- Privacy failures: 0.

## Adaptation rule

Replace every expected value and threshold with an approved product fact. If a
fact is unknown, record it as unresolved; do not invent it to complete the suite.
