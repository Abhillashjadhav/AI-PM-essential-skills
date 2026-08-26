#!/usr/bin/env python3
"""Backward-compatible wrapper for `python -m pm_verifier report`."""
from pm_verifier.cli import main


raise SystemExit(main(["report"]))
