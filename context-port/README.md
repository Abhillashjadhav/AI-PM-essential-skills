# ContextPort

ContextPort is a public, standalone, local-first toolkit for representing, reviewing, planning, and reconciling conversational context. It preserves exact synthetic source content, project boundaries, provenance, and explicit dispositions without requiring a private operating system, paid API, account credential, or production dependency.

## Current status

The synthetic migration MVP is `VERIFIED`. ContextPort can validate ContextPack `0.1`, segregate projects, generate a privacy-safe human review package, create an approved reconstruction dry run, reconcile it independently, plan incremental changes, build/install locally, and run a revision-bound synthetic demonstration.

Real Claude export compatibility is `UNKNOWN` until a human approves local inspection of a real ZIP. Consumer ChatGPT reconstruction writes are `UNSUPPORTED` because a public write interface has not been verified. ContextPort performs no browser automation or assistant write.

See the [capability matrix](docs/CAPABILITIES.md) for the precise boundary.

## Quick start

Requirements: Python 3.11 or newer and a public checkout. No production dependencies are required.

```sh
python3 context-port/contextport.py --version
python3 context-port/contextport.py capabilities
python3 context-port/contextport.py validate context-port/fixtures/contextpack-valid.json
python3 context-port/demo.py
python3 -m unittest discover -s context-port/tests -v
```

The demo uses committed synthetic fixtures, reconciles with zero differences, reports every destination operation as unsupported/not copied, and performs no network call, browser automation, or migration write.

## Install locally

Preview a new isolated installation without writing:

```sh
python3 context-port/install.py ~/.local/contextport
```

After reviewing the plan, explicitly install:

```sh
python3 context-port/install.py ~/.local/contextport --install
```

The target must not exist. The installer never clears, overwrites, upgrades, or uninstalls content. No package has been published.

## Safe workflow

1. Inspect only synthetic input, unless fresh approval authorizes a real export.
2. Validate ContextPack structure and exact text digests.
3. Build a deterministic project segregation plan.
4. Review metadata and record an explicit decision artifact.
5. Build an assistant-neutral reconstruction dry run.
6. Reconcile the plan independently.
7. Assess destination support; currently ChatGPT writes fail closed as `UNSUPPORTED`.

Start with the [operator guide](docs/OPERATOR_GUIDE.md). The [CLI contract](docs/CLI.md) documents every exit status and output channel.

## Human approval gates

Fresh approval is required before:

- accessing, listing, hashing, extracting, or inspecting a real Claude or ChatGPT export;
- resolving an ambiguous project mapping;
- truncating or summarizing any conversation;
- launching browser automation;
- writing to ChatGPT or Claude;
- sending private data over a network;
- deleting or overwriting content;
- adding a production dependency;
- publishing a release.

See [privacy and safety](docs/PRIVACY.md) before handling any non-synthetic artifact.

## Documentation

The complete public documentation map is in [docs/README.md](docs/README.md). Architecture, contracts, schemas, fixtures, tests, evaluation evidence, saved prompts, state, and handoff records all live inside `context-port/`.

Canonical cross-session working memory is generated in [SESSION.md](SESSION.md) and [SESSION.json](SESSION.json) with `contextport handoff`; these files are never maintained manually.

ContextPort has no runtime dependency on any private repository or internal reviewer. Private development systems are not named, exposed, copied, or required by the public product.
