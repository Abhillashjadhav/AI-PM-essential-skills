#!/usr/bin/env python3
"""Fail-closed, offline ContextPort installer."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

import contextport_build


INSTALLER_VERSION = "0.1"


class InstallError(RuntimeError):
    """Raised when installation cannot proceed without overwriting or network use."""

    def __init__(self, message: str, *, writes_performed: bool = False) -> None:
        super().__init__(message)
        self.writes_performed = writes_performed


def _executable(target: Path, name: str, platform: str | None = None) -> Path:
    platform = os.name if platform is None else platform
    directory = "Scripts" if platform == "nt" else "bin"
    suffix = ".exe" if platform == "nt" else ""
    return target / directory / f"{name}{suffix}"


def plan_install(target: Path) -> dict[str, object]:
    """Describe a new isolated installation without changing the filesystem."""
    target = target.expanduser().resolve()
    return {
        "installer_version": INSTALLER_VERSION,
        "status": "ready" if not target.exists() else "blocked_existing_target",
        "target": str(target),
        "package_version": contextport_build.VERSION,
        "source": "local_checkout",
        "network_allowed": False,
        "dependencies_allowed": False,
        "overwrite_allowed": False,
        "writes_performed": False,
    }


def install(target: Path) -> dict[str, object]:
    """Install the locally built wheel into a new isolated environment and verify it."""
    plan = plan_install(target)
    target = Path(str(plan["target"]))
    if plan["status"] != "ready":
        raise InstallError(f"target already exists; refusing to overwrite: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.mkdir(exist_ok=False)
    except FileExistsError as exc:
        raise InstallError(f"target appeared during installation; refusing to overwrite: {target}") from exc
    with tempfile.TemporaryDirectory(prefix="contextport-build-") as directory:
        wheel_directory = Path(directory)
        wheel = wheel_directory / contextport_build.build_wheel(wheel_directory)
        venv.EnvBuilder(with_pip=True, clear=False, symlinks=False).create(target)
        python = _executable(target, "python")
        environment = {**os.environ, "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
        subprocess.run(
            [str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
    command = _executable(target, "contextport")
    version = subprocess.run([str(command), "--version"], check=True, capture_output=True, text=True)
    capabilities = subprocess.run([str(command), "capabilities"], check=True, capture_output=True, text=True)
    capability_report = json.loads(capabilities.stdout)
    if version.stdout.strip() != f"ContextPort {contextport_build.VERSION}":
        raise InstallError("installed version verification failed", writes_performed=True)
    if capability_report.get("network_required") is not False:
        raise InstallError("installed capability verification failed", writes_performed=True)
    if capability_report.get("destination_writes_supported") is not False:
        raise InstallError("installed destination-write boundary verification failed", writes_performed=True)
    return {
        **plan,
        "status": "installed_verified",
        "command": str(command),
        "writes_performed": True,
        "verification": {
            "version": version.stdout.strip(),
            "capabilities_exit_code": capabilities.returncode,
            "network_required": capability_report["network_required"],
            "destination_writes_supported": capability_report["destination_writes_supported"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="contextport-install", description=__doc__)
    parser.add_argument("target", type=Path, help="new installation directory; must not already exist")
    parser.add_argument("--install", action="store_true", help="perform the planned local installation")
    arguments = parser.parse_args(argv)
    target = arguments.target.expanduser().resolve()
    try:
        report = install(target) if arguments.install else plan_install(target)
    except (InstallError, OSError, subprocess.SubprocessError, ValueError) as exc:
        partial = (
            exc.writes_performed
            if isinstance(exc, InstallError)
            else target.exists() and arguments.install
        )
        report = {
            "installer_version": INSTALLER_VERSION,
            "status": "install_failed",
            "target": str(target),
            "package_version": contextport_build.VERSION,
            "network_allowed": False,
            "dependencies_allowed": False,
            "overwrite_allowed": False,
            "writes_performed": partial,
            "partial_target_retained": partial,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] in {"ready", "installed_verified"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
