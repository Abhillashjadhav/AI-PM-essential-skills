# Local installer

ContextPort's installer creates a new isolated Python environment from a wheel built from the current public checkout. It does not contact a package index or install dependencies.

Preview an installation without writing:

```sh
python3 context-port/install.py ~/.local/contextport
```

Perform the installation only after reviewing the plan:

```sh
python3 context-port/install.py ~/.local/contextport --install
```

The target must not exist. ContextPort atomically reserves it before creating the environment, so a target that appears after the dry-run check is rejected. ContextPort refuses to clear, overwrite, upgrade, or uninstall an existing directory. If installation fails after reserving the target, the structured `install_failed` report records `partial_target_retained: true`; cleanup is a separate human-controlled destructive action.

A successful report is `installed_verified` only after the installed `contextport --version` and `contextport capabilities` commands complete and confirm both `network_required: false` and `destination_writes_supported: false`. The report proves that local installation, not any assistant migration write, succeeded.

The installer implements POSIX (`bin/`) and Windows (`Scripts/`) executable layouts. Automated end-to-end installation currently runs on the repository's Linux CI; deterministic unit coverage verifies both path layouts.
