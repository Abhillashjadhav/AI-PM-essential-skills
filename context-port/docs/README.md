# ContextPort documentation

## Start here

- [Project overview and quick start](../README.md)
- [Operator guide](OPERATOR_GUIDE.md)
- [Capability matrix](CAPABILITIES.md)
- [Privacy and safety](PRIVACY.md)
- [CLI contract](CLI.md)
- [Synthetic demonstration](DEMO.md)
- [Generated session memory](SESSION.md)
- [Release readiness](RELEASE_READINESS.md)
- [Packaging](PACKAGING.md) and [local installer](INSTALLER.md)

## Architecture and contracts

- [Architecture boundary](ARCHITECTURE.md)
- [Build specification and threat model](../BUILD_SPEC.md)
- [ContextPack 0.1](CONTEXTPACK.md)
- [Safe export inspection](EXPORT_INSPECTION.md)
- [Project segregation](PROJECT_SEGREGATION.md)
- [Human review](HUMAN_REVIEW.md)
- [Reconstruction planning](RECONSTRUCTION.md)
- [Independent reconciliation](RECONCILIATION.md)
- [Incremental sync planning](INCREMENTAL_SYNC.md)
- [ChatGPT adapter boundary](CHATGPT_ADAPTER.md)

## Development evidence

- [Contribution workflow](CONTRIBUTION_WORKFLOW.md)
- [Current state](../STATE.md)
- [Handoff](../HANDOFF.md)
- `../schemas/` — public versioned JSON contracts
- `../fixtures/` — synthetic committed inputs only
- `../tests/` — dependency-free verification
- `../evals/` — phase evaluation evidence
- `../prompts/` — public prompt contributions

Reliability labels have fixed meanings throughout these documents:

- `VERIFIED` — observable completed evidence supports the claim.
- `INFERRED` — identified evidence supports a reasoned conclusion.
- `UNKNOWN` — available evidence does not establish the claim.
- `UNSUPPORTED` — the current version intentionally refuses or cannot perform it.
