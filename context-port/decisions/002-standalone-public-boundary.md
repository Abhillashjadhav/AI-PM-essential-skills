# Decision 002: standalone public boundary

## Status

Accepted on 2026-07-11.

## Decision

ContextPort is a fully standalone public component located entirely under `context-port/` in this repository. Installation, execution, validation, testing, and documentation must work without access to any private development environment or repository.

Private tools may assist development reviews, evaluation design, and regression analysis, but they are not part of the product architecture. Their internal names, prompts, agents, orchestration, implementation, and other proprietary details must not appear in public ContextPort artifacts.

Any privately assisted output committed publicly must be generic, redacted, non-proprietary, and understandable and reproducible from the public repository alone.

## Consequences

- Runtime and packaging code may depend only on components declared in this public repository.
- Public tests and evaluation evidence must be runnable without private resources.
- Product verification relies on observable public checks, not claims about private reviews.
- Integrations with private development tooling remain outside ContextPort's public interface and documentation.
