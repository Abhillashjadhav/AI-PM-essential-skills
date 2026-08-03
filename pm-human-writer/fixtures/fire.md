# Fire fixture

User request:

```text
Please rewrite this LinkedIn post so it sounds less AI-generated while keeping my product judgment and facts.

Audience: AI product managers and engineering leaders on LinkedIn.
Reader outcome: understand why the measured result remained marginal.

Draft:
What most people miss is that an LLM judge can look accurate and still be unsafe to trust.

The best part: I measured 76.5% agreement with human graders. This robust result changes everything.

I could lower the threshold and call it a pass. I marked it MARGINAL instead.
```

Expected behaviour: trigger `human-product-writer`, preserve `76.5%`, `human graders`, the threshold decision, and `MARGINAL`; remove the named machine-writing patterns; add no new test dimensions or evidence; and return the edited draft plus `What changed`.
