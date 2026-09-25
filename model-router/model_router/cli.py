"""Terminal entry point. Plain-language help for every command.

By default commands use the real Codex App Server adapter (live mode, with all
gates). ``--simulate`` uses the synthetic simulator in a separate
``simulator/`` data directory so synthetic threads never mix with real ones.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

from .adapters.base import ApprovalRequest
from .adapters.codex_stdio import CodexConfig, CodexStdioAdapter
from .adapters.fake import FakeAdapter
from .contracts import AcceptanceEvidence, ContractError, JobState, Role, utc_now
from .coordinator import Coordinator, OverrideRefused, RouterUI
from .registry import mapping_hash_for
from .store import Store, default_data_dir

HELP_CHAT = """Inside chat, type a message, or one of:
  /attach <path>            attach a local TXT/MD/DOCX/PDF to your next message
  /fetch <url>              fetch a public page you named and attach it as data
  /history                  show this chat's messages
  /cancel                   cancel this chat's queued or running work
  /model <model-id> [why]   change this chat's model (why: quality, task, preference, or blank)
  /done <resolved|partial|failed|abandoned> [1-5]   record whether your task got done
  /feedback <text>          save a note about the answer
  /newtask <text>           mark that you are starting a genuinely new task in this chat
  /finalise [record.json]   accept the architecture in this chat and open implementation
  /choose <model-id>        pick a model when automatic routing timed out
  /wake                     re-check queued work now
  /recover <job> resend|drop   answer a recovery question
  /threads  /status  /help  /quit"""


class TerminalUI(RouterUI):
    def __init__(self, interactive: bool = True) -> None:
        self.interactive = interactive
        self._streaming = False

    def _end(self) -> None:
        if self._streaming:
            print()
            self._streaming = False

    def notify(self, text: str) -> None:
        self._end()
        print(text if text.startswith("Router:") else f"Router: {text}")

    def stream(self, text: str) -> None:
        self._streaming = True
        sys.stdout.write(text)
        sys.stdout.flush()

    def ask_approval(self, request: ApprovalRequest) -> str:
        self._end()
        print(f"Router: The model asks to run a {request.kind.replace('_', ' ')}:")
        if request.command:
            print(f"  command: {request.command}")
        if request.cwd:
            print(f"  in: {request.cwd}")
        if request.paths:
            print(f"  paths: {', '.join(request.paths)}")
        if request.summary:
            print(f"  reason: {request.summary}")
        if not self.interactive:
            print("Router: declined (non-interactive session)")
            return "decline"
        answer = input("Allow this once? [y/N] ").strip().lower()
        return "accept" if answer in {"y", "yes"} else "decline"


def build(args: argparse.Namespace, *, ui: RouterUI | None = None) -> tuple[Coordinator, Store]:
    data_dir = Path(args.data_dir).expanduser() if args.data_dir else default_data_dir()
    if getattr(args, "simulate", False):
        sim_dir = data_dir / "simulator"
        store = Store(sim_dir)
        adapter = FakeAdapter(state_path=str(sim_dir / "simulator-provider-state.json"))
        coordinator = Coordinator(store, adapter, live=False, ui=ui or TerminalUI())
    else:
        store = Store(data_dir)
        adapter = CodexStdioAdapter(
            CodexConfig(data_dir=data_dir, executable=getattr(args, "codex_path", None),
                        codex_home=Path(args.codex_home) if getattr(args, "codex_home", None) else None)
        )
        coordinator = Coordinator(store, adapter, live=True, ui=ui or TerminalUI())
    return coordinator, store


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


# ------------------------------------------------------------------ commands


def cmd_doctor(args: argparse.Namespace) -> int:
    from .doctor import format_gates, run_doctor

    data_dir = Path(args.data_dir).expanduser() if args.data_dir else default_data_dir()
    gates = run_doctor(
        data_dir, codex_path=args.codex_path, codex_home=Path(args.codex_home) if args.codex_home else None, connect=not args.no_connect
    )
    if args.json:
        _print_json([g.to_dict() for g in gates])
    else:
        print("Model router doctor (read-only: no model turn, no credentials shown)\n")
        print(format_gates(gates))
        blocked = [g.name for g in gates if g.status.value in {"BLOCKED", "FAILED"}]
        print()
        if any(g.name == "spend boundary" and g.status.value != "VERIFIED" for g in gates):
            print("Live model sends stay blocked: zero added spend cannot be verified yet.")
        if blocked:
            print("Not ready: " + ", ".join(blocked))
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    from .demo import run_demo

    summary = run_demo(Path(args.data_dir) if args.keep_data and args.data_dir else None)
    if args.json:
        _print_json(summary)
    return 0


def cmd_project_add(args: argparse.Namespace) -> int:
    coordinator, store = build(args)
    try:
        project_id = coordinator.add_project(args.name, args.path, worktree=args.worktree)
    except ContractError as exc:
        print(f"Router: {exc}")
        return 1
    print(f"Router: project {args.name!r} added ({project_id}) at {Path(args.path).resolve()}")
    return 0


def cmd_threads(args: argparse.Namespace) -> int:
    coordinator, _ = build(args)
    rows = coordinator.threads(args.project)
    if not rows:
        print("No threads yet.")
    for row in rows:
        print(f"{row['id']}  {row['project_name']:<14} {row['kind']:<14} {row['pinned_model'] or '(no model)':<18} "
              f"{row['pinned_role'] or '-':<8} {row['title'] or ''}")
    return 0


def cmd_models(args: argparse.Namespace) -> int:
    coordinator, _ = build(args)
    coordinator.start()
    account = coordinator.account_scope
    if not account:
        print("Router: no signed-in account; run `router.py doctor` for the exact blocker.")
        return 1
    action = args.action or "list"
    if action == "list":
        mappings = coordinator.registry.active_mappings(account)
        print(f"Registry revision: {coordinator.registry.active_revision(account)}")
        for role in Role:
            mapping = mappings.get(role)
            print(f"  {role.value:<8} → {mapping.model_id + ' (' + str(mapping.reasoning_effort) + ')' if mapping else 'not set up'}")
        print("Discovered models:")
        for model in coordinator.registry.models(account):
            efforts = ",".join(model["info"].get("reasoning_efforts") or [])
            print(f"  {model['model_id']:<24} {model['status']:<9} {'available' if model['available'] else 'UNAVAILABLE':<11} efforts: {efforts}")
        return 0
    if action == "propose":
        for proposal in coordinator.registry.propose(account):
            print(f"  {proposal.role.value}: {proposal.model_id} ({proposal.reasoning_effort}) — {proposal.rationale}")
            print(f"    approve with: router.py models approve --role {proposal.role.value} --model {proposal.model_id} "
                  f"--effort {proposal.reasoning_effort} --confirm {proposal.mapping_hash}")
        return 0
    if action == "approve":
        if not (args.role and args.model):
            print("Router: --role and --model are required")
            return 2
        expected = mapping_hash_for(account, Role(args.role), args.model, args.effort, evaluation_ids=args.evaluation or [])
        if not args.confirm:
            print(f"Router: you are approving {args.role} → {args.model} ({args.effort}) for new chats only.")
            print(f"Router: evaluation evidence attached: {args.evaluation or 'none — consider running comparisons first'}")
            print(f"Router: to approve exactly this mapping, re-run with --confirm {expected}")
            return 0
        try:
            result = coordinator.registry.approve_mapping(
                account, Role(args.role), args.model, args.effort, actor=args.actor, confirm_hash=args.confirm, evaluation_ids=args.evaluation or []
            )
        except ContractError as exc:
            print(f"Router: {exc}")
            return 1
        print(f"Router: approved. Registry revision {result['revision']} is active for new chats; existing chats keep their models.")
        return 0
    return 2


def cmd_model_set(args: argparse.Namespace) -> int:
    coordinator, _ = build(args)
    coordinator.start()
    thread = coordinator.store.thread(args.thread_id)
    try:
        override = coordinator.override_model(args.thread_id, args.model_id, reason=args.reason)
    except (OverrideRefused, ContractError) as exc:
        print(f"Router: cannot change the model: {exc}")
        return 1
    print(f"Router: this chat moves from {thread['pinned_model']} to {args.model_id} (reason: {override.reason.value}).")
    print("Router: the change applies from the next turn, after the usual sign-in and spend checks.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    coordinator, _ = build(args)
    status = coordinator.status()
    from .doctor import peak_rss_mib

    status["process_peak_rss_mib"] = peak_rss_mib()
    _print_json(status)
    return 0


def cmd_wake(args: argparse.Namespace) -> int:
    coordinator, _ = build(args)
    coordinator.start()
    coordinator.recover()
    for job_id, state in coordinator.wake():
        print(f"Router: {job_id} → {state.value}")
    return 0


def cmd_recover(args: argparse.Namespace) -> int:
    coordinator, _ = build(args)
    coordinator.start()
    try:
        state = coordinator.resolve_recovery(args.job_id, args.decision)
    except ContractError as exc:
        print(f"Router: {exc}")
        return 1
    print(f"Router: {args.job_id} → {state.value}")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    from .evals.runner import run_offline
    from .reporting import export_weekly

    data_dir = Path(args.data_dir).expanduser() if args.data_dir else default_data_dir()
    store = Store(data_dir / "simulator" if args.simulate else data_dir)
    if args.eval_action == "run":
        if not args.offline:
            print("Router: live comparisons need an authorised finite plan and passing spend gates; use --offline now.")
            return 2
        result = run_offline(store)
        if args.json:
            _print_json(result)
        else:
            print(f"Offline evaluation {result['status']}: {result['passed']} passed, {len(result['failed'])} failed "
                  f"(model calls: {result['plan']['model_calls']}). Judge self-check usable: {result['judge_self_check']['usable']}")
            for failure in result["failed"]:
                print(f"  FAIL {failure['case_id']}: {failure['checks']}")
            print(result["note"])
        return 0 if result["status"] == "PASSED" else 1
    if args.eval_action == "report":
        week = args.week or __import__("model_router.evals.metrics", fromlist=["iso_week"]).iso_week(utc_now())
        out_dir = Path(args.out).expanduser() if args.out else store.data_dir / "reports"
        paths = export_weekly(store, week, out_dir, include_synthetic=args.include_synthetic or args.simulate)
        print(Path(paths["markdown"]).read_text(encoding="utf-8"))
        print(f"Saved: {paths['json']} and {paths['markdown']}")
        return 0
    return 2


def cmd_import(args: argparse.Namespace) -> int:
    from .importer import import_file

    data_dir = Path(args.data_dir).expanduser() if args.data_dir else default_data_dir()
    store = Store(data_dir / "simulator" if args.simulate else data_dir)
    print("Router: importing only the file you named; nothing is fetched from ChatGPT and nothing leaves this machine.")
    _print_json(import_file(store, Path(args.file), project_root=str(Path(args.file).resolve().parent), since_days=args.since_days))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    from .reporting import diagnostic_export

    data_dir = Path(args.data_dir).expanduser() if args.data_dir else default_data_dir()
    store = Store(data_dir / "simulator" if args.simulate else data_dir)
    if args.private:
        print("Router: PRIVATE export requested: it contains your conversation content. Keep it off public repositories.", file=sys.stderr)
    _print_json(diagnostic_export(store, private=args.private))
    return 0


def cmd_adapter_pin(args: argparse.Namespace) -> int:
    from .doctor import pin_installation

    data_dir = Path(args.data_dir).expanduser() if args.data_dir else default_data_dir()
    _print_json(pin_installation(data_dir, codex_path=args.codex_path, codex_home=Path(args.codex_home) if args.codex_home else None,
                                 approve_digest=args.approve, actor=args.actor))
    return 0


def cmd_outcome(args: argparse.Namespace) -> int:
    coordinator, _ = build(args)
    record = coordinator.record_outcome(args.thread_id, args.outcome, satisfaction=args.satisfaction, note=args.note)
    print(f"Router: recorded {record.outcome.value} for {args.thread_id}")
    return 0


# ---------------------------------------------------------------------- chat


def cmd_chat(args: argparse.Namespace, *, thread_id: str | None = None) -> int:
    coordinator, store = build(args)
    coordinator.start()
    coordinator.recover()
    if thread_id:
        thread = store.thread(thread_id)
        project = store.project(thread["project_id"])["name"]
    else:
        project = args.project
        if store.project_by_name(project) is None:
            print(f"Router: unknown project {project!r}. Add it: router.py project add --name {project} --path <dir>")
            return 1
    ui = coordinator.ui
    print(f"Project: {project}" + ("  [SIMULATED]" if args.simulate else ""))
    if thread_id:
        print(f"Router: continuing chat {thread_id} on {store.thread(thread_id)['pinned_model']}.")
        for job in store.all("SELECT id FROM jobs WHERE thread_id=? AND state NOT IN ('SUCCEEDED','FAILED','CANCELLED')", (thread_id,)):
            _drive(coordinator, job["id"], ui)
    pending_attachments: list[str] = []
    while True:
        try:
            line = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        text = line.strip()
        if not text:
            continue
        if text.startswith("/"):
            thread_id, stop = _chat_command(coordinator, text, thread_id, pending_attachments, args)
            if stop:
                return 0
            continue
        try:
            result = coordinator.submit(project, text, thread_id=thread_id, attachments=list(pending_attachments))
        except ContractError as exc:
            ui.notify(f"Router: {exc}")
            continue
        pending_attachments.clear()
        if result.handoff is not None:
            _report_handoff(coordinator, result.handoff, ui)
            continue
        if thread_id is None:
            thread_id = result.thread_id
            ui.notify(f"Router: {result.explanation}")
            timing = result.timings_ms.get("submit_to_selection_ms")
            if timing is not None:
                ui.notify(f"Router: (routing took {timing:.0f} ms{' incl. startup' if result.timings_ms.get('cold') else ''})")
        for notice in result.notices:
            ui.notify(f"Router: {notice}")
        if result.state is JobState.AWAITING_MANUAL_MODEL:
            ui.notify("Router: choose a model with /choose <model-id> (see: router.py models)")
            continue
        _drive(coordinator, result.job_id, ui)


def _drive(coordinator: Coordinator, job_id: str, ui: RouterUI) -> None:
    try:
        state = coordinator.run(job_id)
    except KeyboardInterrupt:
        ui.notify("Router: interrupted; cancelling this turn.")
        coordinator.cancel(job_id)
        return
    if isinstance(ui, TerminalUI):
        ui._end()
    if state in {JobState.SELECTED, JobState.READY}:
        ui.notify("Router: queued behind another running turn.")


def _report_handoff(coordinator: Coordinator, handoff, ui: RouterUI) -> None:
    if handoff.status in {"CREATED", "EXISTING"}:
        ui.notify("Router: Architecture saved. Opening implementation in this project.")
        if handoff.role is Role.LOWEST:
            ui.notify("Router: Using the approved lower model for this new coding chat:\nthe steps are clear, the work is low risk, and included usage looks tight.")
        elif handoff.role:
            ui.notify(f"Router: {handoff.role.plain} reasoning — implementation from the agreed architecture.")
        ui.notify(f"Router: implementation chat {handoff.target_thread_id} (model {handoff.model_id}); "
                  f"continue it later with: router.py resume {handoff.target_thread_id}")
        if handoff.status == "CREATED" and handoff.job_id:
            _drive(coordinator, handoff.job_id, ui)
    else:
        ui.notify(f"Router: Architecture not handed off ({handoff.status}): " + "; ".join(handoff.reasons))


def _chat_command(coordinator: Coordinator, text: str, thread_id: str | None, pending: list[str], args) -> tuple[str | None, bool]:
    ui = coordinator.ui
    parts = shlex.split(text)
    command, rest = parts[0].lower(), parts[1:]
    store = coordinator.store
    if command in {"/quit", "/exit"}:
        return thread_id, True
    if command == "/help":
        print(HELP_CHAT)
    elif command == "/attach" and rest:
        pending.append(rest[0])
        ui.notify(f"Router: will attach {rest[0]} to your next message")
    elif command == "/fetch" and rest:
        from .store import atomic_write
        from .webfetch import fetch_public

        result = fetch_public(rest[0])
        if not result.ok:
            ui.notify(f"Router: fetch failed: {result.error}")
        else:
            path = store.data_dir / "fetched" / f"{abs(hash(rest[0]))}.md"
            atomic_write(path, f"{result.attribution}\n\n{result.text}")
            pending.append(str(path))
            ui.notify(f"Router: fetched {rest[0]} ({len(result.text or '')} chars) — attached as data to your next message")
    elif command == "/history" and thread_id:
        for message in store.messages(thread_id):
            print(f"[{message['role']}/{message['kind']}] {(message['content'] or '')[:400]}")
    elif command == "/cancel" and thread_id:
        for job in store.all("SELECT id FROM jobs WHERE thread_id=? AND state NOT IN ('SUCCEEDED','FAILED','CANCELLED')", (thread_id,)):
            ui.notify(f"Router: {job['id']} → {coordinator.cancel(job['id']).value}")
    elif command == "/model" and rest and thread_id:
        reason = " ".join(rest[1:]) or (input("Why? (quality / task / preference / blank = unknown) ") if sys.stdin.isatty() else "")
        try:
            override = coordinator.override_model(thread_id, rest[0], reason=reason)
            ui.notify(f"Router: this chat moves from {override.old_model} to {override.new_model} (reason: {override.reason.value}).")
        except (OverrideRefused, ContractError) as exc:
            ui.notify(f"Router: cannot change the model: {exc}")
    elif command == "/choose" and rest and thread_id:
        job = store.one("SELECT id FROM jobs WHERE thread_id=? AND state='AWAITING_MANUAL_MODEL'", (thread_id,))
        if job is None:
            ui.notify("Router: nothing is waiting for a model choice")
        else:
            try:
                coordinator.choose_manual_model(job["id"], rest[0])
                _drive(coordinator, job["id"], ui)
            except ContractError as exc:
                ui.notify(f"Router: {exc}")
    elif command == "/done" and rest and thread_id:
        satisfaction = int(rest[1]) if len(rest) > 1 else None
        coordinator.record_outcome(thread_id, rest[0], satisfaction=satisfaction)
        ui.notify(f"Router: recorded {rest[0]}")
    elif command == "/feedback" and rest and thread_id:
        coordinator.record_outcome(thread_id, "unknown", note=" ".join(rest))
        ui.notify("Router: feedback saved")
    elif command == "/newtask" and thread_id:
        coordinator.new_task_segment(thread_id, " ".join(rest))
        ui.notify("Router: new task noted; this chat keeps its model. Start a new chat if you want a fresh choice.")
    elif command == "/finalise" and thread_id:
        record = json.loads(Path(rest[0]).read_text(encoding="utf-8")) if rest else None
        handoff = coordinator.finalise_architecture(
            thread_id, acceptance=AcceptanceEvidence(source="finalise_command", reference=f"cli:{utc_now()}", text=text), record_payload=record
        )
        _report_handoff(coordinator, handoff, ui)
    elif command == "/threads":
        for row in coordinator.threads():
            print(f"{row['id']}  {row['kind']:<14} {row['pinned_model'] or '-':<18} {row['title'] or ''}")
    elif command == "/status":
        _print_json(coordinator.status())
    elif command == "/wake":
        for job_id, state in coordinator.wake():
            ui.notify(f"Router: {job_id} → {state.value}")
    elif command == "/recover" and len(rest) == 2:
        try:
            ui.notify(f"Router: {rest[0]} → {coordinator.resolve_recovery(rest[0], rest[1]).value}")
        except ContractError as exc:
            ui.notify(f"Router: {exc}")
    else:
        ui.notify("Router: unknown or incomplete command; /help lists them" + ("" if thread_id else " (start a chat with a message first)"))
    return thread_id, False


# -------------------------------------------------------------------- parser


def parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data-dir", help="where local records live (default: platform user data directory)")
    common.add_argument("--simulate", action="store_true", help="use the synthetic simulator (no account, no model)")
    common.add_argument("--codex-path", help="absolute path of the Codex CLI to use")
    common.add_argument("--codex-home", help="dedicated Codex profile directory (default: <data-dir>/codex-home)")

    root = argparse.ArgumentParser(
        prog="router.py",
        description="Local model router: picks a model per chat, keeps it fixed, hands architecture to implementation, never adds spend.",
    )
    sub = root.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", parents=[common], help="check this machine, sign-in, models, usage and the spend boundary (read-only)")
    p.add_argument("--no-connect", action="store_true", help="do not start the App Server")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("demo", parents=[common], help="run the synthetic end-to-end demo (no account needed)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--keep-data", action="store_true", help="keep demo data in --data-dir instead of a temp dir")
    p.set_defaults(func=cmd_demo)

    project = sub.add_parser("project", help="manage projects").add_subparsers(dest="project_command", required=True)
    p = project.add_parser("add", parents=[common], help="link a project name to a working directory")
    p.add_argument("--name", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--worktree")
    p.set_defaults(func=cmd_project_add)

    p = sub.add_parser("chat", parents=[common], help="start chatting in a project")
    p.add_argument("--project", required=True)
    p.set_defaults(func=cmd_chat)

    p = sub.add_parser("threads", parents=[common], help="list chats and their fixed models")
    p.add_argument("--project")
    p.set_defaults(func=cmd_threads)

    p = sub.add_parser("resume", parents=[common], help="continue a chat (and any queued work) on its same model")
    p.add_argument("thread_id")
    p.set_defaults(func=lambda a: cmd_chat(a, thread_id=a.thread_id))

    model = sub.add_parser("model", help="change a chat's model").add_subparsers(dest="model_command", required=True)
    p = model.add_parser("set", parents=[common], help="deliberately change one chat's model")
    p.add_argument("thread_id")
    p.add_argument("model_id")
    p.add_argument("--reason", help="quality, task, preference, or leave blank (unknown)")
    p.set_defaults(func=cmd_model_set)

    p = sub.add_parser("models", parents=[common], help="list discovered models and approved roles; propose or approve mappings")
    p.add_argument("action", nargs="?", choices=["list", "propose", "approve"])
    p.add_argument("--role", choices=[r.value for r in Role])
    p.add_argument("--model")
    p.add_argument("--effort")
    p.add_argument("--evaluation", action="append")
    p.add_argument("--confirm", help="the exact mapping hash you are approving")
    p.add_argument("--actor", default="owner")
    p.set_defaults(func=cmd_models)

    p = sub.add_parser("status", parents=[common], help="show queued/blocked work and memory use")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("wake", parents=[common], help="recover after restart and re-check queued work")
    p.set_defaults(func=cmd_wake)

    p = sub.add_parser("recover", parents=[common], help="answer a recovery question for an uncertain send")
    p.add_argument("job_id")
    p.add_argument("decision", choices=["resend", "drop"])
    p.set_defaults(func=cmd_recover)

    evals = sub.add_parser("eval", help="evaluation runs and weekly reports").add_subparsers(dest="eval_action", required=True)
    p = evals.add_parser("run", parents=[common], help="run evaluations (offline needs no account)")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_eval)
    p = evals.add_parser("report", parents=[common], help="weekly JSON + Markdown report")
    p.add_argument("--week", help="ISO week like 2026-W39 (default: this week)")
    p.add_argument("--out")
    p.add_argument("--include-synthetic", action="store_true")
    p.set_defaults(func=cmd_eval)

    p = sub.add_parser("import", parents=[common], help="import an authorised conversation export in the documented format")
    p.add_argument("--file", required=True)
    p.add_argument("--since-days", type=int)
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("export", parents=[common], help="diagnostic export (redacted unless --private)")
    p.add_argument("--private", action="store_true", help="include conversation content (explicit request)")
    p.set_defaults(func=cmd_export)

    adapter = sub.add_parser("adapter", help="pin the installed Codex CLI").add_subparsers(dest="adapter_command", required=True)
    p = adapter.add_parser("pin", parents=[common], help="measure and (with --approve) pin the installed Codex CLI")
    p.add_argument("--approve", help="the exact installation digest shown by a review run")
    p.add_argument("--actor", default="owner")
    p.set_defaults(func=cmd_adapter_pin)

    p = sub.add_parser("outcome", parents=[common], help="record whether a chat's task got done")
    p.add_argument("thread_id")
    p.add_argument("outcome", choices=["resolved", "partial", "failed", "abandoned", "unknown"])
    p.add_argument("--satisfaction", type=int, choices=range(1, 6))
    p.add_argument("--note")
    p.set_defaults(func=cmd_outcome)
    return root


def main(argv: list[str] | None = None) -> int:
    import signal

    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # `router.py models | head` exits quietly
    args = parser().parse_args(argv)
    return int(args.func(args) or 0)
