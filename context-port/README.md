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

See [the ContextPack contract](docs/CONTEXTPACK.md) for the data model and current limitations, and [the build specification](BUILD_SPEC.md) for the planned system.

## Current boundary

The current implementation validates synthetic ContextPack documents only. It does not read real assistant exports, reconstruct destination conversations, perform browser automation, access accounts, send data over a network, or synchronize content.
