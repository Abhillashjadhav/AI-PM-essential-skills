# Decision 003: ContextPort-only product scope

## Status

Accepted on 2026-07-11.

## Decision

This project will not build or design a Product Engineering OS. ContextPort is the current product priority and the only product implementation in scope under `context-port/`.

ContextPort remains public, standalone, free to use from a public checkout, and independent of private development tooling at runtime. Private review or evaluation systems may inform development but are outside the public product architecture.

## Consequences

- No software-delivery agent architecture, orchestration, deployment operation, or generalized engineering-OS abstraction will be added to ContextPort.
- ContextPort interfaces are designed only around inspection, neutral representation, reconstruction planning, approved adapters, and independent reconciliation.
- Public artifacts must remain understandable and verifiable without private context.
