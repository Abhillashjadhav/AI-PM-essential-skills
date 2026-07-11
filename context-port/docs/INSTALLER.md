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

The target must not exist. ContextPort refuses to clear, overwrite, upgrade, or uninstall an existing directory. If installation fails after creating the target, the partial target is retained and reported; cleanup is a separate human-controlled destructive action.

A successful report is `installed_verified` only after the installed `contextport --version` and `contextport capabilities` commands complete and match the expected offline boundary. The report proves that local installation, not any assistant migration write, succeeded.
