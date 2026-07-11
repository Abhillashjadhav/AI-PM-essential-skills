# ContextPort

ContextPort is a standalone, human-supervised system for representing and reconciling conversational context across supported assistants. It is under development and currently provides an experimental assistant-neutral ContextPack `0.1` contract and local validator.

## Try the public validator

Requirements: Python 3 and a checkout of this repository. There are no production dependencies.

Discover the stable CLI surface:

```sh
python3 context-port/contextport.py --version
python3 context-port/contextport.py capabilities
```

Standard Python wheel and source-distribution metadata is available in `context-port/pyproject.toml`; see [packaging](docs/PACKAGING.md). No package has been published.

Preview a new isolated local installation without writing:

```sh
python3 context-port/install.py ~/.local/contextport
```

Add `--install` only after reviewing the plan. The installer refuses existing targets; see [installer safety](docs/INSTALLER.md).

Run the truthful end-to-end synthetic migration demonstration:

```sh
python3 context-port/demo.py
```

The demo ends with a clean independent reconciliation and an explicit unsupported ChatGPT write boundary. See [demo evidence](docs/DEMO.md).

```sh
python3 context-port/contextport.py validate context-port/fixtures/contextpack-valid.json
```

Run the tests offline:

```sh
python3 -m unittest discover -s context-port/tests -v
```

Inspect the structure of the synthetic source fixture without printing content values:

```sh
python3 context-port/contextport.py inspect context-port/fixtures/synthetic-claude-export-shape.json --classification synthetic
```

Real export inspection requires separate human approval. Supplying `approved-private` records an approval classification in the local report; it does not grant approval by itself.

Build a deterministic segregation plan from the synthetic ContextPack:

```sh
python3 context-port/contextport.py segregate \
  context-port/fixtures/segregation-contextpack.json \
  --mappings context-port/fixtures/project-mappings-valid.json
```

The plan preserves stable project and conversation boundaries without emitting message content. Ambiguous mappings return `decision_required` and a distinct nonzero exit status.

Build a metadata-only review package and render its offline HTML form:

```sh
python3 context-port/contextport.py review-package \
  context-port/fixtures/segregation-contextpack.json \
  --mappings context-port/fixtures/project-mappings-valid.json

python3 context-port/contextport.py review-html \
  context-port/fixtures/review-package-synthetic.json
```

Both commands write to stdout. ContextPort does not launch a browser or overwrite a file.

Build an approved assistant-neutral dry-run reconstruction plan:

```sh
python3 context-port/contextport.py reconstruct-plan \
  context-port/fixtures/segregation-contextpack.json \
  --mappings context-port/fixtures/project-mappings-valid.json \
  --review-package context-port/fixtures/review-package-synthetic.json \
  --decision context-port/fixtures/review-decision-approved.json
```

The command performs no destination write. It fails if the review package, approval, segregation plan, or source digest does not match.

Independently reconcile a saved reconstruction plan:

```sh
python3 context-port/contextport.py reconcile-plan SOURCE.json PLAN.json
```

A clean report requires zero source-versus-plan differences and never trusts writer success flags.

Detect incremental changes without applying them:

```sh
python3 context-port/contextport.py sync-plan PREVIOUS.json CURRENT.json
```

The result includes checkpoints, tombstones, a replay key, and human-required conflicts. It never deletes or writes content.

Assess an approved reconstruction plan against verified public ChatGPT capabilities:

```sh
python3 context-port/contextport.py chatgpt-adapt \
  context-port/fixtures/reconstruction-plan-synthetic.json
```

The offline adapter currently returns `blocked_unsupported` because no public API for reconstructing consumer ChatGPT Projects and chats has been verified. It does not use an API key, call a network service, automate a browser, or write to ChatGPT.

See [the CLI contract](docs/CLI.md), [ContextPack contract](docs/CONTEXTPACK.md), [project segregation contract](docs/PROJECT_SEGREGATION.md), [human review contract](docs/HUMAN_REVIEW.md), [reconstruction contract](docs/RECONSTRUCTION.md), [reconciliation contract](docs/RECONCILIATION.md), [incremental sync contract](docs/INCREMENTAL_SYNC.md), [ChatGPT adapter contract](docs/CHATGPT_ADAPTER.md), and [build specification](BUILD_SPEC.md).

## Current boundary

The current implementation validates synthetic ContextPack documents only. It does not read real assistant exports, reconstruct destination conversations, perform browser automation, access accounts, send data over a network, or synchronize content.
