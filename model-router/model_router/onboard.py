"""One-command setup and a bounded live pilot.

``setup`` does everything that needs no human, and pauses only for the two
things that do: ChatGPT sign-in (Codex's own browser login, never a pasted
credential) and approving which discovered model serves each role.

``pilot`` runs a small, fixed set of real turns (normal answer, architecture
-> implementation handoff, human override, restart/resume) and refuses to
start unless the spend boundary is ALLOWED_INCLUDED_ONLY from a verified
mechanism. It never exhausts real usage on purpose; limit handling is covered
by the simulator tests.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from .adapters.base import AdapterError
from .adapters.codex_stdio import CodexConfig, CodexStdioAdapter, inspect_installation, pin_status, resolve_executable
from .contracts import JobState, Role, SpendStatus, utc_now
from .doctor import pin_installation
from .registry import CODING_TOOLS, mapping_hash_for
from .store import Store, atomic_write

FAMILIES: dict[Role, tuple[str, ...]] = {
    Role.HIGHEST: ("astra",),
    Role.MIDDLE: ("sol",),
    Role.LOWEST: ("luna", "terra"),
}
PILOT_TURN_BUDGET = 8


def _version_key(model_id: str) -> tuple:
    numbers = [int(n) for n in re.findall(r"\d+", model_id)]
    return tuple(numbers) or (0,)


def candidates_for(models: list[dict[str, Any]], role: Role) -> list[dict[str, Any]]:
    """Discovered, available models whose name matches the owner's family label
    for this role, newest version first (name match only; not quality evidence)."""
    families = FAMILIES[role]
    matches = [m for m in models if m["available"] and any(f in m["model_id"].lower() for f in families)]
    return sorted(matches, key=lambda m: _version_key(m["model_id"]), reverse=True)


class Setup:
    def __init__(
        self,
        data_dir: Path,
        *,
        codex_path: str | None = None,
        codex_home: Path | None = None,
        ask: Callable[[str], str] = input,
        say: Callable[[str], None] = print,
        run_login: Callable[[list[str], dict[str, str]], int] | None = None,
    ) -> None:
        self.data_dir = data_dir
        self.config = CodexConfig(data_dir=data_dir, executable=codex_path, codex_home=codex_home)
        self.ask = ask
        self.say = say
        self.run_login = run_login or (lambda argv, env: subprocess.call(argv, env=env))

    def confirm(self, question: str) -> bool:
        return self.ask(f"{question} [y/N] ").strip().lower() in {"y", "yes"}

    def run(self) -> dict[str, Any]:
        report: dict[str, Any] = {"started_at": utc_now(), "steps": []}

        def step(name: str, status: str, detail: str) -> None:
            report["steps"].append({"step": name, "status": status, "detail": detail})
            self.say(f"[{status}] {name}: {detail}")

        executable = resolve_executable(self.config.executable)
        if executable is None:
            npm = shutil.which("npm")
            step("codex cli", "BLOCKED", "Codex CLI not found" + ("; install with: npm install -g @openai/codex" if npm else ""))
            if npm and self.confirm("Install the Codex CLI now with npm (no sign-in, no spend)?"):
                code = subprocess.call([npm, "install", "-g", "@openai/codex"])
                executable = resolve_executable(self.config.executable)
                step("codex install", "VERIFIED" if code == 0 and executable else "FAILED", f"npm exited {code}")
            if executable is None:
                return self._finish(report, "Install the Codex CLI, then run setup again.")
        manifest, problems = inspect_installation(executable, self.config.home)
        if manifest is None:
            step("codex cli", "FAILED", "; ".join(problems))
            return self._finish(report, "The installed Codex CLI could not be inspected.")
        step("codex cli", "VERIFIED", f"{manifest.executable} ({manifest.version})")
        if manifest.compat_problems:
            step("protocol", "FAILED", "; ".join(manifest.compat_problems))
            return self._finish(report, "This Codex version's protocol is incompatible with the router adapter.")
        step("protocol", "VERIFIED", "installed App Server schema has every required method and field")

        from .adapters.codex_stdio import PinManifest

        state, _ = pin_status(PinManifest.load(self.config.pin_path), manifest)
        if state != "valid":
            self.say(f"Pin this exact Codex install? {manifest.executable} version {manifest.version} sha256 {manifest.sha256[:16]}…")
            if not self.confirm("Pin it (sends are blocked if it later changes)?"):
                step("adapter pin", "BLOCKED", "not pinned")
                return self._finish(report, "Pin the Codex install to continue.")
            pin_installation(self.data_dir, codex_path=str(executable), codex_home=self.config.codex_home,
                             approve_digest=manifest.digest, actor="owner")
        step("adapter pin", "VERIFIED", "pinned to this installation")

        adapter = CodexStdioAdapter(CodexConfig(data_dir=self.data_dir, executable=str(executable), codex_home=self.config.codex_home))
        try:
            adapter.initialise()
            account = adapter.read_account()
            if account.auth_mode != "chatgpt":
                step("sign-in", "BLOCKED", f"auth mode {account.auth_mode or 'none'}; ChatGPT sign-in needed")
                if not self.confirm("Open Codex's ChatGPT sign-in for the router's dedicated profile now?"):
                    return self._finish(report, "Sign in with ChatGPT to continue.")
                env = {k: v for k, v in os.environ.items() if k not in {"OPENAI_API_KEY", "CODEX_API_KEY"}}
                env["CODEX_HOME"] = str(self.config.home)
                self.run_login([str(executable), "login"], env)
                adapter.close()
                adapter = CodexStdioAdapter(CodexConfig(data_dir=self.data_dir, executable=str(executable), codex_home=self.config.codex_home))
                adapter.initialise()
                account = adapter.read_account()
                if account.auth_mode != "chatgpt":
                    step("sign-in", "FAILED", "still not signed in with ChatGPT")
                    return self._finish(report, "ChatGPT sign-in did not complete.")
            if not account.config_ok:
                step("profile", "FAILED", "; ".join(account.config_problems))
                return self._finish(report, "The router's Codex profile is not ChatGPT-only.")
            step("sign-in", "VERIFIED", f"ChatGPT account, plan {account.plan_type or 'not reported'} (email withheld)")
            step("profile", "VERIFIED", "dedicated CODEX_HOME with forced_login_method=chatgpt, no provider override")

            store = Store(self.data_dir)
            try:
                from .registry import Registry

                registry = Registry(store)
                catalogue = adapter.list_models()
                registry.record_discovery(account.account_scope, catalogue.models, provider=adapter.name)
                models = registry.models(account.account_scope)
                step("models", "VERIFIED", f"{len(models)} model(s) available to this account: " + ", ".join(m["model_id"] for m in models))
                report["mappings"] = self._approve_roles(registry, account.account_scope, models, step)
            finally:
                store.close()

            usage = adapter.read_usage()
            decision = adapter.check_spend_boundary(account, usage)
            report["spend"] = {"status": decision.status.value, "mechanism": decision.mechanism,
                               "reasons": decision.reasons, "missing": decision.missing}
            if decision.status is SpendStatus.ALLOWED_INCLUDED_ONLY:
                step("spend boundary", "VERIFIED", f"included-only enforced by {decision.mechanism}")
                return self._finish(report, "Ready. Run: python3 model-router/router.py pilot", ready=True)
            step("spend boundary", "BLOCKED", f"{decision.status.value}: " + "; ".join(decision.reasons + decision.missing))
            return self._finish(report, "Live sends stay blocked: this account has no enforceable included-only control.")
        except AdapterError as exc:
            step("app server", "FAILED", str(exc))
            return self._finish(report, "The Codex App Server could not be reached.")
        finally:
            adapter.close()

    def _approve_roles(self, registry, account_scope: str, models: list[dict[str, Any]], step) -> dict[str, Any]:
        active = registry.active_mappings(account_scope)
        approved: dict[str, Any] = {}
        for role in (Role.HIGHEST, Role.MIDDLE, Role.LOWEST):
            if role in active:
                approved[role.value] = active[role].model_id
                step(f"{role.value} role", "VERIFIED", f"already approved: {active[role].model_id} ({active[role].reasoning_effort})")
                continue
            options = candidates_for(models, role) or [m for m in models if m["available"]]
            self.say(f"\nWhich model should serve {role.value} reasoning? (family label: {'/'.join(FAMILIES[role])}; name match only)")
            for index, model in enumerate(options, 1):
                efforts = ",".join(model["info"].get("reasoning_efforts") or [])
                self.say(f"  {index}. {model['model_id']}  (default effort {model['info'].get('default_effort')}; efforts {efforts})")
            answer = self.ask("Number to approve (Enter = skip for now): ").strip()
            if not answer.isdigit() or not 1 <= int(answer) <= len(options):
                step(f"{role.value} role", "BLOCKED", "not approved yet; chats needing it route up or ask you")
                continue
            model = options[int(answer) - 1]
            efforts = model["info"].get("reasoning_efforts") or []
            effort = model["info"].get("default_effort")
            chosen = self.ask(f"Reasoning effort for {model['model_id']} (Enter = {effort}; options {','.join(efforts)}): ").strip()
            if chosen:
                effort = chosen
            confirm = mapping_hash_for(account_scope, role, model["model_id"], effort, tool_scope=list(CODING_TOOLS))
            registry.approve_mapping(account_scope, role, model["model_id"], effort, actor="owner", confirm_hash=confirm,
                                     tool_scope=list(CODING_TOOLS))
            approved[role.value] = model["model_id"]
            step(f"{role.value} role", "VERIFIED", f"approved {model['model_id']} ({effort}) for new chats")
        return approved

    def _finish(self, report: dict[str, Any], message: str, *, ready: bool = False) -> dict[str, Any]:
        report["ready"] = ready
        report["next"] = message
        report["finished_at"] = utc_now()
        path = self.data_dir / "setup" / f"setup-{int(time.time())}.json"
        atomic_write(path, json.dumps(report, indent=2))
        self.say(f"\n{message}")
        return report


# ------------------------------------------------------------------- pilot


def run_pilot(coordinator, *, project_dir: Path, allow_simulated: bool = False) -> dict[str, Any]:
    from .coordinator import Coordinator
    from .scheduler import AutoResumer

    store = coordinator.store
    report: dict[str, Any] = {"started_at": utc_now(), "live": coordinator.live, "scenarios": {}, "blocked": None}
    coordinator.start()
    try:
        account = coordinator.adapter.read_account()
        usage_before = coordinator.adapter.read_usage()
        decision = coordinator.adapter.check_spend_boundary(account, usage_before)
    except AdapterError as exc:
        report["blocked"] = f"provider unavailable: {exc}"
        return _save_pilot(store, report)
    report["spend"] = {"status": decision.status.value, "mechanism": decision.mechanism, "synthetic": decision.synthetic}
    if decision.status is not SpendStatus.ALLOWED_INCLUDED_ONLY or (decision.synthetic and not allow_simulated):
        report["blocked"] = "spend boundary is not ALLOWED_INCLUDED_ONLY from a verified mechanism: " + "; ".join(
            decision.reasons + decision.missing
        )
        return _save_pilot(store, report)
    mappings = coordinator.registry.active_mappings(coordinator.account_scope or "")
    missing_roles = [r.value for r in Role if r not in mappings]
    if missing_roles:
        report["blocked"] = f"approve models for roles {missing_roles} first (router.py setup)"
        return _save_pilot(store, report)

    project_dir.mkdir(parents=True, exist_ok=True)
    if not (project_dir / "hello.py").exists():
        (project_dir / "hello.py").write_text('def greet():\n    return "hi"\n')
        subprocess.run(["git", "init", "-q"], cwd=project_dir, check=False)
    if store.project_by_name("router-pilot") is None:
        coordinator.add_project("router-pilot", str(project_dir))

    def sends() -> int:
        return store.one("SELECT COUNT(*) AS n FROM dispatches WHERE phase IN ('SENT','ACKNOWLEDGED','TERMINAL','UNCERTAIN')")["n"]

    start_sends = sends()

    def budget_ok() -> bool:
        return sends() - start_sends < PILOT_TURN_BUDGET

    def dispatch_summary(job_id: str) -> dict[str, Any]:
        row = store.one("SELECT requested_model, observed_model, observed_model_note, turn_status FROM dispatches WHERE job_id=? ORDER BY created_at DESC LIMIT 1", (job_id,))
        return dict(row) if row else {}

    # A. Normal answer.
    normal = coordinator.submit("router-pilot", "Summarize in two bullets: the router picks a model per chat and keeps it fixed.")
    state = coordinator.run(normal.job_id)
    answer = store.one("SELECT length(content) AS n FROM messages WHERE thread_id=? AND role='assistant' ORDER BY created_at DESC LIMIT 1", (normal.thread_id,))
    report["scenarios"]["normal_answer"] = {
        "role": normal.role.value if normal.role else None, "model": normal.model_id, "state": state.value,
        "answer_chars": answer["n"] if answer else 0, "selection_ms": normal.timings_ms.get("submit_to_selection_ms"),
        **dispatch_summary(normal.job_id), "pass": state is JobState.SUCCEEDED and normal.role is Role.LOWEST,
    }

    # B. Architecture -> implementation handoff.
    if budget_ok():
        arch = coordinator.submit(
            "router-pilot",
            "Design a minimal architecture for adding a hello(name) function to hello.py in this project, with one unit test. "
            "Treat it as complete and include the architecture-record block.",
        )
        arch_state = coordinator.run(arch.job_id)
        accepted = coordinator.submit("router-pilot", "Approved, implement this.", thread_id=arch.thread_id)
        handoff = accepted.handoff
        impl_state = coordinator.run(handoff.job_id).value if handoff and handoff.job_id and handoff.status == "CREATED" else None
        report["scenarios"]["handoff"] = {
            "architecture_role": arch.role.value if arch.role else None, "architecture_model": arch.model_id,
            "architecture_state": arch_state.value, "handoff_status": handoff.status if handoff else None,
            "handoff_reasons": handoff.reasons if handoff else None,
            "implementation_role": handoff.role.value if handoff and handoff.role else None,
            "implementation_model": handoff.model_id if handoff else None, "implementation_state": impl_state,
            "source_pin_unchanged": store.thread(arch.thread_id)["pinned_model"] == arch.model_id,
            "pass": bool(handoff and handoff.status == "CREATED" and impl_state == "SUCCEEDED"),
        }

    # C. Human override on the normal-answer chat.
    if budget_ok():
        target = mappings[Role.MIDDLE].model_id
        coordinator.override_model(normal.thread_id, target, reason="preference")
        follow = coordinator.submit("router-pilot", "Now make it one bullet.", thread_id=normal.thread_id)
        follow_state = coordinator.run(follow.job_id)
        summary = dispatch_summary(follow.job_id)
        report["scenarios"]["override"] = {
            "new_model": target, "state": follow_state.value, **summary,
            "pass": follow_state is JobState.SUCCEEDED and summary.get("requested_model") == target,
        }

    # D. Pause, restart, automatic resume on the same pin.
    if budget_ok():
        queued = coordinator.submit("router-pilot", "Reformat as a numbered list: apples, pears, figs.")
        pinned = store.thread(queued.thread_id)["pinned_model"]
        restarted = Coordinator(store, coordinator.adapter, live=coordinator.live, ui=coordinator.ui)
        restarted.start()
        restarted.recover()
        tick = AutoResumer(restarted, min_interval=1, max_interval=5).tick()
        final = store.job(queued.job_id)["state"]
        report["scenarios"]["restart_resume"] = {
            "pinned_model": pinned, "resumed": tick.resumed, "state": final, **dispatch_summary(queued.job_id),
            "pass": final == "SUCCEEDED" and dispatch_summary(queued.job_id).get("requested_model") == pinned,
        }
        restarted.close()

    try:
        usage_after = coordinator.adapter.read_usage()
        report["usage"] = {
            "before": [b.to_dict() for b in usage_before.buckets], "after": [b.to_dict() for b in usage_after.buckets],
            "note": "percentages are rounded, delayed and shared with other sessions; not per-model cost",
        }
    except AdapterError as exc:
        report["usage"] = {"error": str(exc)}
    report["turns_sent"] = sends() - start_sends
    report["all_passed"] = all(s.get("pass") for s in report["scenarios"].values()) and len(report["scenarios"]) == 4
    return _save_pilot(store, report)


def _save_pilot(store: Store, report: dict[str, Any]) -> dict[str, Any]:
    report["finished_at"] = utc_now()
    path = store.data_dir / "pilot" / f"pilot-{int(time.time())}.json"
    atomic_write(path, json.dumps(report, indent=2, default=str))
    report["saved_to"] = str(path)
    return report
