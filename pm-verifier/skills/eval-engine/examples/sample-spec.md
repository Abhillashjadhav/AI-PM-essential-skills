# Feature spec: AI ticket summarizer

## What it does

When a support agent opens a customer ticket, the feature generates a summary
of the full ticket thread so the agent can respond without reading every message.

## Requirements

- Output is a JSON object with two fields: `summary` (the thread summary) and
  `customer_request` (one sentence stating what the customer is actually asking for).
- The summary must be under 600 characters — it renders in a fixed sidebar panel.
- Every claim in the summary must come from the ticket thread. The model must not
  infer or invent order numbers, dates, refund amounts, or prior interactions that
  are not in the thread.
- The feature must never promise or imply a resolution ("you will receive a
  refund", "we guarantee") — commitments are the agent's call, not the model's.
- The summary should preserve the customer's sentiment (frustrated, neutral,
  satisfied) so agents can calibrate tone.
- Newest-message-first threads are common; the summary should reflect the
  chronological story, not the display order.

## Out of scope

- Suggested replies (separate feature).
- Tickets in languages other than English (v2).
