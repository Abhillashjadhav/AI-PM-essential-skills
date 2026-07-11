# ContextPort architecture boundary

ContextPort is the only product implementation in scope under `context-port/`. It is a public, standalone, local-first tool for representing and reconciling conversational context.

ContextPort does not define or implement a broader software-delivery operating system. Product planning systems, private review environments, and any future engineering automation are outside its product architecture.

## Public completeness rule

A public checkout must contain everything required to install, run, test, evaluate, and understand ContextPort. No private repository, agent, prompt, reviewer, service, or orchestration layer may be a runtime dependency or a prerequisite for interpreting public evidence.

External review may inform development. A resulting public artifact is acceptable only when it is generic, redacted, non-proprietary, and independently understandable from this repository.

## Component boundary

- `schemas/` defines public versioned interchange contracts.
- `contextport.py` provides the local command-line interface.
- `fixtures/` contains synthetic inputs only.
- `tests/` and `evals/` provide public verification evidence.
- Future source adapters, normalization, reconstruction, and reconciliation remain separate components connected through explicit versioned contracts.

Imported content is always inert data. Inspection observes structure; it does not interpret content, infer project mappings, normalize text, or authorize migration.
