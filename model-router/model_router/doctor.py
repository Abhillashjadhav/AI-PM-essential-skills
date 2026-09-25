"""Read-only diagnostics. No model turn, no credential output, no browser.

Each gate reports VERIFIED, FAILED, BLOCKED, or NOT_RUN with evidence.
"""

from __future__ import annotations

import platform
import resource
import shutil
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .adapters.codex_stdio import (
    CodexConfig,
    CodexStdioAdapter,
    PinManifest,
    inspect_installation,
    pin_status,
    resolve_executable,
)
from .contracts import GateStatus, SpendStatus, utc_now
from .store import Store


@dataclass
class Gate:
    name: str
    status: GateStatus
    evidence: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "status": self.status.value, "evidence": self.evidence, "detail": self.detail}


def _mode(path: Path) -> str:
    return oct(stat.S_IMODE(path.stat().st_mode))


def peak_rss_mib() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports bytes, Linux kibibytes.
    return round(usage / (1024 * 1024) if sys.platform == "darwin" else usage / 1024, 1)


def run_doctor(data_dir: Path, *, codex_path: str | None = None, codex_home: Path | None = None, connect: bool = True) -> list[Gate]:
    gates: list[Gate] = []
    version_ok = sys.version_info >= (3, 11)
    gates.append(Gate("python", GateStatus.VERIFIED if version_ok else GateStatus.FAILED, f"Python {platform.python_version()}"))

    store = Store(data_dir)
    try:
        problems = store.integrity_check()
        gates.append(
            Gate(
                "local store",
                GateStatus.VERIFIED if not problems else GateStatus.FAILED,
                f"{store.db_path} schema v{store.schema_version()}; dir mode {_mode(store.data_dir)}; db mode {_mode(store.db_path)}",
                {"problems": problems},
            )
        )
    finally:
        store.close()

    config = CodexConfig(data_dir=data_dir, executable=codex_path, codex_home=codex_home)
    executable = resolve_executable(codex_path)
    if executable is None:
        gates.append(Gate("codex cli", GateStatus.BLOCKED, "Codex CLI not found on PATH (or --codex-path). Live routing is unavailable; the simulator still works."))
        for name in ("adapter pin", "app server", "chatgpt sign-in", "effective config", "model discovery", "usage signals", "spend boundary"):
            gates.append(Gate(name, GateStatus.BLOCKED, "requires the Codex CLI on this machine"))
    else:
        current, problems = inspect_installation(executable, config.home)
        if current is None:
            gates.append(Gate("codex cli", GateStatus.FAILED, f"{executable}: " + "; ".join(problems)))
        else:
            gates.append(
                Gate(
                    "codex cli",
                    GateStatus.VERIFIED,
                    f"{current.executable} version {current.version!r} sha256 {current.sha256[:16]}…",
                    {"launcher": current.launcher, "schema_digest": current.schema_digest},
                )
            )
            gates.append(
                Gate(
                    "protocol compatibility",
                    GateStatus.VERIFIED if not current.compat_problems else GateStatus.FAILED,
                    "installed schema has every required method/field" if not current.compat_problems else "; ".join(current.compat_problems),
                    {"notes": current.compat_notes},
                )
            )
        saved = PinManifest.load(config.pin_path)
        state, reasons = pin_status(saved, current)
        gates.append(Gate("adapter pin", GateStatus.VERIFIED if state == "valid" else GateStatus.BLOCKED, f"pin state: {state}", {"reasons": reasons}))
        if connect:
            gates.extend(_live_read_only(config))
        else:
            gates.append(Gate("app server", GateStatus.NOT_RUN, "--no-connect given"))

    pdf = shutil.which("pdftotext")
    gates.append(
        Gate(
            "pdf extraction",
            GateStatus.VERIFIED if pdf else GateStatus.BLOCKED,
            f"pdftotext at {pdf}" if pdf else "pdftotext (poppler-utils) not installed; text PDFs are BLOCKED, TXT/MD/DOCX work",
        )
    )
    gates.append(Gate("process memory", GateStatus.VERIFIED, f"peak RSS {peak_rss_mib()} MiB for this doctor run (not a pilot measurement)"))
    gates.append(Gate("browser / desktop integration", GateStatus.BLOCKED, "no supported ChatGPT-web or Codex-desktop integration; routing works in this terminal client only"))
    return gates


def _live_read_only(config: CodexConfig) -> list[Gate]:
    gates: list[Gate] = []
    adapter = CodexStdioAdapter(config)
    try:
        capabilities = adapter.initialise()
        if adapter.dropped_env:
            gates.append(Gate("environment", GateStatus.VERIFIED, f"API-key variables present and withheld from Codex: {len(adapter.dropped_env)} (names only in JSON)", {"withheld": adapter.dropped_env}))
        account = adapter.read_account()
        if not account.authenticated and account.config_problems:
            gates.append(Gate("app server", GateStatus.FAILED, "; ".join(account.config_problems)))
            return gates
        gates.append(Gate("app server", GateStatus.VERIFIED, "initialize/account/read answered over stdio", {"pin": capabilities.pin}))
        if account.auth_mode == "chatgpt":
            gates.append(Gate("chatgpt sign-in", GateStatus.VERIFIED, f"ChatGPT account, plan {account.plan_type or 'not reported'} (email withheld)"))
        else:
            gates.append(
                Gate(
                    "chatgpt sign-in",
                    GateStatus.BLOCKED,
                    f"auth mode {account.auth_mode or 'none'}; sign in with: CODEX_HOME={config.home} codex login",
                )
            )
        gates.append(
            Gate(
                "effective config",
                GateStatus.VERIFIED if account.config_ok else GateStatus.FAILED,
                "forced_login_method=chatgpt; no provider override" if account.config_ok else "; ".join(account.config_problems),
            )
        )
        if account.auth_mode != "chatgpt":
            try:
                catalogue = adapter.list_models()
                gates.append(Gate("model catalogue", GateStatus.VERIFIED if catalogue.models else GateStatus.BLOCKED,
                                  f"{len(catalogue.models)} model(s) in the CLI catalogue (not yet confirmed for your account)",
                                  {"models": [m.model_id for m in catalogue.models]}))
            except Exception as exc:  # report, do not crash
                gates.append(Gate("model catalogue", GateStatus.BLOCKED, f"model/list unavailable before sign-in: {exc}"))
            gates.append(Gate("spend boundary", GateStatus.BLOCKED,
                              "needs ChatGPT sign-in; then decided per request from live provider signals (spend.py)"))
            return gates
        catalogue = adapter.list_models()
        gates.append(
            Gate(
                "model discovery",
                GateStatus.VERIFIED if catalogue.models else GateStatus.FAILED,
                f"{len(catalogue.models)} account-visible model(s)",
                {"models": [{"id": m.model_id, "efforts": m.reasoning_efforts} for m in catalogue.models]},
            )
        )
        usage = adapter.read_usage()
        gates.append(
            Gate(
                "usage signals",
                GateStatus.VERIFIED if usage.buckets else GateStatus.BLOCKED,
                f"{len(usage.buckets)} bucket(s); ordinaryUsageAllowed={usage.ordinary_usage_allowed}; {usage.credits.describe()}",
                {"buckets": [b.to_dict() for b in usage.buckets], "plan": usage.plan_type, "reset_offers": usage.reset_offer_available},
            )
        )
        spend = adapter.check_spend_boundary(account, usage)
        gates.append(
            Gate(
                "spend boundary",
                GateStatus.VERIFIED if spend.status is SpendStatus.ALLOWED_INCLUDED_ONLY else GateStatus.BLOCKED,
                f"{spend.status.value}: " + "; ".join(spend.reasons + spend.missing),
                {"evidence": spend.evidence},
            )
        )
    except Exception as exc:  # doctor must report, not crash
        gates.append(Gate("app server", GateStatus.FAILED, f"{type(exc).__name__}: {exc}"))
    finally:
        adapter.close()
    return gates


def pin_installation(data_dir: Path, *, codex_path: str | None, codex_home: Path | None, approve_digest: str | None, actor: str) -> dict[str, Any]:
    config = CodexConfig(data_dir=data_dir, executable=codex_path, codex_home=codex_home)
    executable = resolve_executable(codex_path)
    if executable is None:
        return {"status": "BLOCKED", "reason": "Codex CLI not found"}
    manifest, problems = inspect_installation(executable, config.home)
    if manifest is None:
        return {"status": "FAILED", "reason": "; ".join(problems)}
    if manifest.compat_problems:
        return {"status": "FAILED", "reason": "installed protocol is incompatible", "problems": manifest.compat_problems}
    if approve_digest is None:
        return {"status": "REVIEW", "manifest": manifest.to_dict(), "digest": manifest.digest,
                "next": f"re-run with --approve {manifest.digest} to pin exactly this installation"}
    if approve_digest != manifest.digest:
        return {"status": "FAILED", "reason": "digest does not match the installation measured now"}
    manifest.approved_by = actor
    manifest.approved_at = utc_now()
    manifest.save(config.pin_path)
    return {"status": "PINNED", "digest": manifest.digest, "path": str(config.pin_path)}


def format_gates(gates: list[Gate]) -> str:
    width = max(len(g.name) for g in gates)
    return "\n".join(f"{g.status.value:9} {g.name.ljust(width)}  {g.evidence}" for g in gates)


__all__ = ["Gate", "format_gates", "peak_rss_mib", "pin_installation", "run_doctor"]
