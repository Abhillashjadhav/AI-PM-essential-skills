# Packaging ContextPort

ContextPort is a pure-Python project with no runtime or build dependencies. `pyproject.toml` uses the repository's small standard-library PEP 517 backend so an offline checkout can build a wheel or source distribution without downloading build tools.

The wheel exposes:

- the `contextport` console command;
- all runtime modules;
- versioned JSON schemas and public contract documentation under `contextport_data/`;
- standard wheel metadata and integrity records.

Wheel bytes are deterministic for an unchanged checkout. Build artifacts belong in a temporary or ignored `dist/` directory and are not release evidence until their hashes and installed behavior are independently verified.

No package has been uploaded or published. The availability of the `contextport` name on any package index is `UNKNOWN` until the release approval phase.

No package license is declared because this repository currently has no license file. Selecting a public software license remains a human legal decision before release.
