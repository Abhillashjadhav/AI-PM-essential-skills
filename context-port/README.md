# ContextPort

ContextPort is a standalone, human-supervised system for representing and reconciling conversational context across supported assistants. It is under development and currently provides an experimental assistant-neutral ContextPack `0.1` contract and local validator.

## Try the public validator

Requirements: Python 3 and a checkout of this repository. There are no production dependencies.

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

See [the ContextPack contract](docs/CONTEXTPACK.md), [project segregation contract](docs/PROJECT_SEGREGATION.md), [human review contract](docs/HUMAN_REVIEW.md), [reconstruction contract](docs/RECONSTRUCTION.md), and [build specification](BUILD_SPEC.md).

## Current boundary

The current implementation validates synthetic ContextPack documents only. It does not read real assistant exports, reconstruct destination conversations, perform browser automation, access accounts, send data over a network, or synchronize content.
