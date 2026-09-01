# Eval contract: AI ticket summarizer

## Release question

Can the candidate summarize a support thread without inventing facts, losing
the escalation reason, or reading newest-first messages in the wrong order?

## Product response

The user-visible response is one JSON object with exactly:

- `summary` — a chronological summary under 600 characters;
- `customer_request` — one sentence stating what the customer wants.

The evidence adapter separately exposes sentiment, escalation reason, supported
claims, chronology, and operational metrics for grading.

## Enabled surfaces

- Outcome: required response, supported claims, sentiment, escalation reason,
  length, safety, and privacy.
- Trajectory: the ticket messages were processed in chronological order.

System and memory are not enabled because this feature does not promise an
end-to-end workflow or persistent state.

## Automatic failure conditions

- A required response field is missing or incorrect.
- The summary exceeds 600 characters.
- A claim is not supported by the source thread.
- The escalation reason or sentiment is lost.
- The model processes the displayed newest-first thread as chronological.
- The output promises a resolution or exposes an email address.

## Dataset

Three synthetic workflows cover a blocked invoice export, an SSO compatibility
question, and account access blocked after MFA plus a password reset.

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
