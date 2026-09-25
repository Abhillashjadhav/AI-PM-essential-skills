"""Local coordinator: routing, immutable model pins, handoff, durable outbox,
queueing, cancellation and restart recovery.

Invariants enforced here (see docs/architecture.md):

* The route decision and exact binding are durable before any provider call.
* A thread's model never changes except through an explicit owner override.
* No turn is sent unless the eligibility gate passed moments before, in this
  process, under the single dispatch lease.
* A send whose outcome is unknown is reconciled, never blindly repeated.
* One architecture version yields at most one implementation thread.
"""

from __future__ import annotations

import concurrent.futures
import json
import re
import sqlite3
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from . import handoff as handoff_mod
from .adapters.base import (
    AdapterError,
    ApprovalRequest,
    DispatchUncertain,
    SubscriptionAdapter,
    TurnEvent,
)
from .attachments import extract as extract_attachment
from .capacity import CapacityEstimator
from .classifier import ClassifierInput, classify
from .contracts import (
    POLICY_VERSION,
    AcceptanceEvidence,
    Binding,
    CapacityEstimate,
    CapacityState,
    ContractError,
    DispatchPhase,
    JobState,
    Outcome,
    OutcomeKind,
    Override,
    Role,
    RouteDecision,
    SpendStatus,
    TaskAssessment,
    TaskKind,
    ThreadKind,
    TurnStatus,
    WAITING_JOB_STATES,
    new_id,
    parse_override_reason,
    utc_now,
)
from .eligibility import EligibilityGate, EligibilityResult
from .policy import ImplementationFacts, RolePlan, implementation_role, required_role
from .registry import CODING_TOOLS, Registry
from .store import StaleState, Store, StoreError, dumps, lease_owner_id, loads

ROUTE_TIMEOUT_SECONDS = 4.0
DISPATCH_LEASE = "dispatch"
DISPATCH_LEASE_TTL = 600.0
USAGE_ERROR_CODES = {"usageLimitExceeded", "rateLimitExceeded", "sessionBudgetExceeded"}
CODING_KINDS = {TaskKind.IMPLEMENTATION, TaskKind.HIGH_RISK_CODING}

ARCHITECTURE_INSTRUCTIONS = (
    "When you believe the architecture is complete, include a fenced block tagged architecture-record containing "
    "JSON with: goal, scope, decisions[{title,status}], constraints[], components[], interfaces[{name,contract}], "
    "files[], steps[{description,depends_on}], risks[{kind,description}], tests[{name,check}], "
    "blocking_questions[], nonblocking_items[]. Never state that the owner accepted it; only the owner can."
)
WRITING_INSTRUCTIONS = (
    "This is a writing or reading task, not a coding task. Answer directly in text. Do not run commands, "
    "edit files, or inspect the workspace unless the owner explicitly asks."
)
CODING_INSTRUCTIONS = (
    "Work only inside the project root. Do not commit, push, delete unrelated files, or access credentials. "
    "Ask before destructive commands. Report changed files and test results."
)

DESTRUCTIVE_COMMANDS = re.compile(
    r"(rm\s+-[a-z]*r[a-z]*f|rm\s+-[a-z]*f[a-z]*r|git\s+push\s+.*--force|git\s+push\s+-f|git\s+reset\s+--hard|"
    r"git\s+clean\s+-[a-z]*f|drop\s+(table|database)|truncate\s+table|mkfs|dd\s+if=|:>\s*/|chmod\s+-R\s+777|"
    r"sudo\s)",
    re.I,
)
CREDENTIAL_ACCESS = re.compile(
    r"(\.ssh/|\.aws/|\.netrc|\.env\b|auth\.json|credentials|keychain|security\s+find-(generic|internet)-password|"
    r"id_rsa|id_ed25519|\.codex/|printenv|env\s*$|OPENAI_API_KEY|token)",
    re.I,
)
EXTERNAL_UPLOAD = re.compile(r"(curl\s+.*(-d|--data|-F|--upload-file|-T)\b|scp\s|rsync\s+.*:|nc\s|ftp\s|wget\s+--post)", re.I)


class RouterUI:
    """Terminal-facing callbacks. The default is silent and declines approvals."""

    def notify(self, text: str) -> None:  # router status line
        pass

    def stream(self, text: str) -> None:  # model output
        pass

    def ask_approval(self, request: ApprovalRequest) -> str:
        return "decline"


@dataclass
class SubmitResult:
    thread_id: str
    job_id: str
    state: JobState
    role: Role | None
    model_id: str | None
    explanation: str
    timings_ms: dict[str, float]
    route_decision_id: str | None = None
    handoff: "HandoffResult | None" = None
    notices: list[str] = field(default_factory=list)


@dataclass
class HandoffResult:
    status: str  # CREATED | EXISTING | HELD | BLOCKED_CONTEXT
    handoff_id: str | None
    target_thread_id: str | None
    job_id: str | None
    role: Role | None
    model_id: str | None
    reasons: list[str]
    architecture_version: int | None = None
    package_hash: str | None = None
    capacity: dict[str, Any] | None = None


class OverrideRefused(ContractError):
    pass


class Coordinator:
    def __init__(
        self,
        store: Store,
        adapter: SubscriptionAdapter,
        *,
        live: bool,
        ui: RouterUI | None = None,
        registry: Registry | None = None,
        estimator: CapacityEstimator | None = None,
        route_timeout: float = ROUTE_TIMEOUT_SECONDS,
        classifier: Callable[[ClassifierInput], TaskAssessment] = classify,
        context_budget_chars: int = handoff_mod.DEFAULT_CONTEXT_BUDGET_CHARS,
        actor: str = "owner",
    ) -> None:
        self.store = store
        self.adapter = adapter
        self.live = live
        self.ui = ui or RouterUI()
        self.registry = registry or Registry(store)
        self.estimator = estimator or CapacityEstimator()
        self.gate = EligibilityGate(store, adapter, self.registry, live=live)
        self.route_timeout = route_timeout
        self.classifier = classifier
        self.context_budget_chars = context_budget_chars
        self.actor = actor
        self.instance = new_id("coord")
        self.lease_owner = lease_owner_id(self.instance)
        self.account_scope: str | None = None
        self.capabilities = None
        self._started = False
        self._startup_ms = 0.0
        self._loaded_provider_threads: set[str] = set()
        self._loaded_generation = 0
        self._turn_lock = threading.RLock()
        self._route_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="route")

    # ------------------------------------------------------------------ setup

    def start(self) -> float:
        """Initialise the adapter, read the account and discover models."""
        if self._started:
            return 0.0
        started = time.monotonic()
        try:
            self.capabilities = self.adapter.initialise()
            account = self.adapter.read_account()
            self.account_scope = account.account_scope
            if account.account_scope and account.authenticated:
                catalogue = self.adapter.list_models()
                found = self.registry.record_discovery(account.account_scope, catalogue.models, provider=self.adapter.name)
                for model_id in found["new_candidates"]:
                    self.ui.notify(f"New model discovered: {model_id} (candidate only; needs evaluation and your approval)")
        except AdapterError as exc:
            self.store.event("adapter.start_failed", {"error": str(exc)})
            self.ui.notify(f"Router: the subscription adapter is unavailable: {exc}")
        self._started = True
        self._startup_ms = (time.monotonic() - started) * 1000
        self.store.event("coordinator.started", {"startup_ms": round(self._startup_ms, 2), "live": self.live, "adapter": self.adapter.name})
        return self._startup_ms

    def close(self) -> None:
        self._route_pool.shutdown(wait=False, cancel_futures=True)

    def add_project(self, name: str, path: str, *, worktree: str | None = None, write_scope: list[str] | None = None) -> str:
        root = Path(path).expanduser().resolve()
        if not root.is_dir():
            raise ContractError(f"project path {path!r} is not a directory")
        if self.store.project_by_name(name):
            raise ContractError(f"a project named {name!r} already exists")
        project_id = new_id("prj")
        scope = write_scope or [str(Path(worktree).resolve() if worktree else root)]
        with self.store.transaction() as conn:
            conn.execute(
                "INSERT INTO projects(id, name, root, worktree, write_scope, created_at) VALUES (?,?,?,?,?,?)",
                (project_id, name, str(root), str(Path(worktree).resolve()) if worktree else None, dumps(scope), utc_now()),
            )
            self.store.event("project.added", {"project_id": project_id, "name": name}, conn=conn)
        return project_id

    def _project(self, name_or_id: str) -> sqlite3.Row:
        row = self.store.project_by_name(name_or_id) or self.store.one("SELECT * FROM projects WHERE id=?", (name_or_id,))
        if row is None:
            raise ContractError(f"unknown project {name_or_id!r}; add it with: router.py project add --name <name> --path <dir>")
        return row

    # ------------------------------------------------------------- submission

    def submit(
        self,
        project: str,
        text: str,
        *,
        thread_id: str | None = None,
        attachments: Iterable[str] = (),
        urgency: str | None = None,
        priority: str | None = None,
        metadata: dict[str, Any] | None = None,
        request_id: str | None = None,
        synthetic: bool | None = None,
    ) -> SubmitResult:
        submitted = time.monotonic()
        request_id = request_id or new_id("req")
        existing_job = self.store.one("SELECT * FROM jobs WHERE logical_key=?", (f"request:{request_id}",))
        if existing_job is not None:
            thread = self.store.thread(existing_job["thread_id"])
            return SubmitResult(
                thread_id=thread["id"],
                job_id=existing_job["id"],
                state=JobState(existing_job["state"]),
                role=Role(thread["pinned_role"]) if thread["pinned_role"] else None,
                model_id=thread["pinned_model"],
                explanation="duplicate submission ignored; the original request is kept",
                timings_ms={},
                notices=["duplicate request id"],
            )
        cold = not self._started
        startup_ms = self.start() if cold else 0.0
        if thread_id:
            return self._submit_to_existing(thread_id, text, attachments, request_id, submitted, urgency)

        project_row = self._project(project)
        prep_started = time.monotonic()
        manifest, attachment_texts, attach_errors = self._prepare_attachments(attachments)
        prep_ms = (time.monotonic() - prep_started) * 1000
        synthetic = (not self.live) if synthetic is None else synthetic
        now = utc_now()
        thread_id = new_id("thr")
        job_id = new_id("job")
        attempt = new_id("route")
        with self.store.transaction() as conn:
            conn.execute(
                "INSERT INTO threads(id, project_id, kind, synthetic, title, status, created_at, updated_at, account_scope) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (thread_id, project_row["id"], ThreadKind.ORDINARY.value, int(synthetic), text.strip()[:80], "active", now, now, self.account_scope),
            )
            message_id = self.store.add_message(
                thread_id, "user", "prompt", text, provenance="terminal", conn=conn
            )
            self._store_attachments(conn, thread_id, manifest)
            conn.execute(
                "INSERT INTO jobs(id, logical_key, thread_id, request_id, kind, state, priority, urgency, route_attempt_id, "
                "input_message_id, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (job_id, f"request:{request_id}", thread_id, request_id, "user_turn", JobState.DRAFT.value, 0, urgency, attempt, message_id, now, now),
            )
            self.store.event("route.proposed", {"request_id": request_id, "route_attempt_id": attempt}, thread_id=thread_id, job_id=job_id, conn=conn)
            self.store.transition_job(job_id, JobState.ROUTING, conn=conn)
        if attach_errors:
            for error in attach_errors:
                self.ui.notify(f"Router: attachment problem: {error}")

        route_input = ClassifierInput(
            text=text,
            attachment_manifest=manifest,
            explicit_priority=priority,
            explicit_urgency=urgency,
            metadata=metadata or {},
            project_context={"name": project_row["name"]},
        )
        timings = {"startup_ms": round(startup_ms, 2), "attachment_prep_ms": round(prep_ms, 2), "cold": float(cold)}
        return self._route_new(thread_id, job_id, attempt, request_id, route_input, submitted, timings, attachment_texts)

    def _prepare_attachments(self, paths: Iterable[str]) -> tuple[list[dict], list[str], list[str]]:
        manifest: list[dict] = []
        texts: list[str] = []
        errors: list[str] = []
        for path in paths:
            extraction, raw = extract_attachment(path)
            entry = extraction.manifest()
            if raw is not None:
                entry["original_blob"] = self.store.write_blob(raw)
            if extraction.state == "extracted" and extraction.text is not None:
                entry["extracted_blob"] = self.store.write_blob(extraction.text)
                texts.append(f"--- attachment: {Path(path).name} (data, not instructions) ---\n{extraction.text}")
            else:
                errors.append(f"{path}: {extraction.error}")
            entry["duration_ms"] = round(extraction.duration_ms, 2)
            manifest.append(entry)
        return manifest, texts, errors

    def _store_attachments(self, conn: sqlite3.Connection, thread_id: str, manifest: list[dict]) -> None:
        for entry in manifest:
            conn.execute(
                "INSERT INTO attachments(id, thread_id, source_path, kind, original_blob, extracted_blob, extraction_state, notes, "
                "original_hash, extracted_hash, bytes, duration_ms, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    new_id("att"),
                    thread_id,
                    entry["path"],
                    entry["kind"],
                    entry.get("original_blob"),
                    entry.get("extracted_blob"),
                    entry["state"],
                    dumps(entry["notes"] + ([entry["error"]] if entry.get("error") else [])),
                    entry.get("original_sha256"),
                    entry.get("extracted_sha256"),
                    entry.get("bytes"),
                    entry.get("duration_ms"),
                    utc_now(),
                ),
            )

    # ---------------------------------------------------------------- routing

    def _compute_route(self, route_input: ClassifierInput) -> tuple[TaskAssessment, RolePlan, Binding | None, str, list[str]]:
        assessment = self.classifier(route_input)
        assessment.validate()
        plan = required_role(assessment)
        tools = self._required_tools(assessment, route_input)
        binding, note = self._binding_at_or_above(plan.role, tools)
        return assessment, plan, binding, note, tools

    def _binding_at_or_above(self, role: Role, tools: list[str]) -> tuple[Binding | None, str]:
        if not self.account_scope:
            return None, "no signed-in account, so no approved model bindings are available"
        notes = []
        for candidate in (Role.LOWEST, Role.MIDDLE, Role.HIGHEST):
            if candidate.rank < role.rank:
                continue
            binding, note = self.registry.binding_for(self.account_scope, candidate, tools)
            if binding is not None:
                if candidate is not role:
                    return binding, f"{note}; no usable approved {role.value} model, so routed up to {candidate.value}"
                return binding, note
            notes.append(note)
        if tools:
            # No approved binding is cleared for the tools: keep the role's
            # binding so the gap surfaces as a visible capability block.
            binding, note = self._binding_at_or_above(role, [])
            if binding is not None:
                return binding, f"{note}; required tools {tools} are not approved for it, so dispatch will be blocked"
        return None, "; ".join(notes)

    @staticmethod
    def _required_tools(assessment: TaskAssessment, route_input: ClassifierInput) -> list[str]:
        tools: list[str] = []
        if assessment.task_kind in CODING_KINDS:
            tools.extend(CODING_TOOLS)
        if assessment.task_kind is TaskKind.RESOURCE_EXTRACTION:
            text = route_input.text.lower()
            has_sources = "http://" in text or "https://" in text or bool(route_input.attachment_manifest)
            if re.search(r"\b(find|search|look up|gather)\b", text) and not has_sources:
                tools.append("web_search")
        if route_input.metadata.get("required_tools"):
            tools.extend(route_input.metadata["required_tools"])
        return sorted(set(tools))

    def _route_new(
        self,
        thread_id: str,
        job_id: str,
        attempt: str,
        request_id: str,
        route_input: ClassifierInput,
        submitted: float,
        timings: dict[str, float],
        attachment_texts: list[str],
    ) -> SubmitResult:
        classify_started = time.monotonic()
        future = self._route_pool.submit(self._compute_route, route_input)
        remaining = max(0.0, self.route_timeout - (time.monotonic() - submitted))
        try:
            assessment, plan, binding, note, tools = future.result(timeout=remaining)
        except concurrent.futures.TimeoutError:
            return self._route_timed_out(thread_id, job_id, attempt, future, submitted, timings)
        except Exception as exc:  # classifier failure: fail visibly, fall back to manual selection
            self.store.event("route.failed", {"error": str(exc)}, thread_id=thread_id, job_id=job_id)
            return self._route_timed_out(thread_id, job_id, attempt, future, submitted, timings, reason=f"routing failed: {exc}")
        timings["classify_ms"] = round((time.monotonic() - classify_started) * 1000, 2)
        try:
            decision = self._commit_route(
                thread_id, job_id, attempt, request_id, assessment, plan, binding, note, tools, submitted, timings,
                attachment_texts=attachment_texts,
            )
        except StaleState:
            state = JobState(self.store.job(job_id)["state"])
            return SubmitResult(thread_id, job_id, state, None, None, "routing was superseded", timings)
        state = JobState(self.store.job(job_id)["state"])
        explanation = self.explain(decision, assessment, plan)
        return SubmitResult(
            thread_id=thread_id,
            job_id=job_id,
            state=state,
            role=decision.role,
            model_id=decision.model_id,
            explanation=explanation,
            timings_ms=decision.timings_ms,
            route_decision_id=decision.id,
        )

    def _commit_route(
        self,
        thread_id: str,
        job_id: str,
        attempt: str,
        request_id: str,
        assessment: TaskAssessment,
        plan: RolePlan,
        binding: Binding | None,
        note: str,
        tools: list[str],
        submitted: float,
        timings: dict[str, float],
        *,
        attachment_texts: list[str] | None = None,
    ) -> RouteDecision:
        decision = RouteDecision(
            id=new_id("rte"),
            request_id=request_id,
            thread_id=thread_id,
            route_attempt_id=attempt,
            role=plan.role,
            candidate_id=None,
            model_id=binding.model_id if binding else None,
            reasoning_effort=binding.reasoning_effort if binding else None,
            rule_ids=plan.rule_ids,
            reasons=plan.reasons + [note],
            uncertainty=plan.uncertainty,
            capacity_ref=None,
            manual=False,
            missing_binding=binding is None,
        )
        decision.validate()
        with self.store.transaction() as conn:
            # Fence: only the live attempt in ROUTING may commit.
            row = conn.execute("SELECT state, route_attempt_id FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row["state"] != JobState.ROUTING.value or row["route_attempt_id"] != attempt:
                raise StaleState("route attempt no longer current")
            timings["submit_to_selection_ms"] = round((time.monotonic() - submitted) * 1000, 2)
            decision.timings_ms = dict(timings)
            payload = decision.to_dict() | {"required_tools": tools, "upward_fallback": plan.upward_fallback}
            conn.execute(
                "INSERT INTO task_assessments(id, thread_id, segment, payload, policy_version, created_at) VALUES (?,?,?,?,?,?)",
                (assessment.id, thread_id, 1, dumps(assessment.to_dict()), POLICY_VERSION, utc_now()),
            )
            conn.execute(
                "INSERT INTO route_decisions(id, request_id, thread_id, route_attempt_id, role, model_id, reasoning_effort, manual, payload, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (decision.id, request_id, thread_id, attempt, plan.role.value, decision.model_id, decision.reasoning_effort, 0, dumps(payload), decision.created_at),
            )
            if attachment_texts:
                self.store.add_message(
                    thread_id, "system", "attachment_context", "\n\n".join(attachment_texts), provenance="attachments", conn=conn
                )
            if binding is None:
                self.store.transition_job(
                    job_id, JobState.AWAITING_MANUAL_MODEL, route_attempt_id=attempt, conn=conn,
                    blocker="no approved model for this role: " + note,
                )
                conn.execute(
                    "UPDATE threads SET pinned_role=?, route_decision_id=?, updated_at=? WHERE id=?",
                    (plan.role.value, decision.id, utc_now(), thread_id),
                )
                self.store.event("route.missing_binding", payload, thread_id=thread_id, job_id=job_id, conn=conn)
            else:
                conn.execute(
                    "UPDATE threads SET pinned_model=?, pinned_effort=?, pinned_role=?, registry_revision=?, route_decision_id=?, "
                    "updated_at=? WHERE id=?",
                    (binding.model_id, binding.reasoning_effort, plan.role.value, binding.registry_revision, decision.id, utc_now(), thread_id),
                )
                conn.execute(
                    "INSERT INTO pin_history(id, thread_id, model_id, reasoning_effort, role, source, at) VALUES (?,?,?,?,?,?,?)",
                    (new_id("pin"), thread_id, binding.model_id, binding.reasoning_effort, plan.role.value, "automatic", utc_now()),
                )
                self.store.transition_job(job_id, JobState.SELECTED, route_attempt_id=attempt, conn=conn)
                conn.execute("UPDATE jobs SET selected_at=? WHERE id=?", (utc_now(), job_id))
                self.store.event("route.selected", payload, thread_id=thread_id, job_id=job_id, conn=conn)
        return decision

    def _route_timed_out(self, thread_id, job_id, attempt, future, submitted, timings, *, reason: str | None = None) -> SubmitResult:
        timings["submit_to_selection_ms"] = round((time.monotonic() - submitted) * 1000, 2)
        why = reason or f"automatic routing did not finish within {self.route_timeout:g} seconds"
        try:
            self.store.transition_job(
                job_id, JobState.AWAITING_MANUAL_MODEL, expected=JobState.ROUTING, route_attempt_id=attempt, blocker=why,
                extra={"timings_ms": timings},
            )
            self.store.event("route.timed_out", {"route_attempt_id": attempt, "timings_ms": timings, "reason": why}, thread_id=thread_id, job_id=job_id)
        except StaleState:
            pass

        def _late(fut: concurrent.futures.Future) -> None:
            if fut.cancelled() or fut.exception() is not None:
                return
            # A late result must not select a model or dispatch anything.
            self.store.event("route.late_result_discarded", {"route_attempt_id": attempt}, thread_id=thread_id, job_id=job_id)

        future.add_done_callback(_late)
        return SubmitResult(
            thread_id=thread_id,
            job_id=job_id,
            state=JobState.AWAITING_MANUAL_MODEL,
            role=None,
            model_id=None,
            explanation=f"{why}. Your message is saved; choose a model to continue.",
            timings_ms=timings,
        )

    def choose_manual_model(self, job_id: str, model_id: str, reasoning_effort: str | None = None) -> SubmitResult:
        job = self.store.job(job_id)
        if JobState(job["state"]) is not JobState.AWAITING_MANUAL_MODEL:
            raise ContractError(f"job {job_id} is {job['state']}, not awaiting a manual model choice")
        self._validate_model_choice(model_id)
        thread_id = job["thread_id"]
        now = utc_now()
        decision_id = new_id("rte")
        with self.store.transaction() as conn:
            payload = {"manual": True, "model_id": model_id, "reasoning_effort": reasoning_effort, "reason": job["blocker"]}
            conn.execute(
                "INSERT INTO route_decisions(id, request_id, thread_id, route_attempt_id, role, model_id, reasoning_effort, manual, payload, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (decision_id, job["request_id"], thread_id, new_id("route"), None, model_id, reasoning_effort, 1, dumps(payload), now),
            )
            role = self.registry.role_of_model(self.account_scope or "", model_id)
            conn.execute(
                "UPDATE threads SET pinned_model=?, pinned_effort=?, pinned_role=COALESCE(?, pinned_role), pinned_manual=1, route_decision_id=?, updated_at=? WHERE id=?",
                (model_id, reasoning_effort, role.value if role else None, decision_id, now, thread_id),
            )
            conn.execute(
                "INSERT INTO pin_history(id, thread_id, model_id, reasoning_effort, role, source, at) VALUES (?,?,?,?,?,?,?)",
                (new_id("pin"), thread_id, model_id, reasoning_effort, role.value if role else None, "manual_timeout", now),
            )
            self.store.transition_job(job_id, JobState.SELECTED, manual=True, conn=conn)
            self.store.event("route.selected", payload, thread_id=thread_id, job_id=job_id, conn=conn)
        return SubmitResult(thread_id, job_id, JobState.SELECTED, role, model_id, "manual model choice saved", {})

    def explain(self, decision: RouteDecision, assessment: TaskAssessment, plan: RolePlan) -> str:
        if decision.model_id is None:
            return (
                f"{decision.role.plain if decision.role else 'Unknown'} reasoning needed — {plan.explanation()}. "
                f"No approved model is set up for it yet ({decision.reasons[-1]}). Choose a model or approve a mapping."
            )
        text = f"{decision.role.plain} reasoning — {plan.explanation()}. Model stays fixed for this chat."
        if plan.upward_fallback or assessment.ambiguous:
            text += " (Uncertain task, so routed up: " + "; ".join(assessment.uncertainty[:2] or ["unrecognised task"]) + ".)"
        return text

    def _validate_model_choice(self, model_id: str) -> None:
        if not self.account_scope:
            raise OverrideRefused("no signed-in account; the model cannot be verified")
        entry = self.registry.model(self.account_scope, model_id)
        if entry is None:
            raise OverrideRefused(f"model {model_id!r} was not discovered for this account (see: router.py models)")
        if not entry["available"] or entry["status"] == "retired":
            raise OverrideRefused(f"model {model_id!r} is not currently available to this account")

    # -------------------------------------------------- existing-thread turns

    def _submit_to_existing(self, thread_id, text, attachments, request_id, submitted, urgency) -> SubmitResult:
        thread = self.store.thread(thread_id)
        if thread["kind"] == ThreadKind.ORDINARY.value and handoff_mod.detect_acceptance(text):
            message_id = self.store.add_message(thread_id, "user", "prompt", text, provenance="terminal")
            result = self.finalise_architecture(
                thread_id,
                acceptance=AcceptanceEvidence(source="owner_message", reference=message_id, text=text),
            )
            return SubmitResult(
                thread_id=thread_id,
                job_id="",
                state=JobState.SUCCEEDED if result.status in {"CREATED", "EXISTING"} else JobState.DRAFT,
                role=result.role,
                model_id=result.model_id,
                explanation="architecture acceptance recorded",
                timings_ms={},
                handoff=result,
            )
        if not thread["pinned_model"]:
            raise ContractError("this thread has no model yet; choose one first")
        manifest, attachment_texts, errors = self._prepare_attachments(attachments)
        job_id = new_id("job")
        now = utc_now()
        with self.store.transaction() as conn:
            if attachment_texts:
                self.store.add_message(thread_id, "system", "attachment_context", "\n\n".join(attachment_texts), provenance="attachments", conn=conn)
            self._store_attachments(conn, thread_id, manifest)
            message_id = self.store.add_message(thread_id, "user", "prompt", text, provenance="terminal", conn=conn)
            conn.execute(
                "INSERT INTO jobs(id, logical_key, thread_id, request_id, kind, state, priority, urgency, input_message_id, selected_at, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (job_id, f"request:{request_id}", thread_id, request_id, "user_turn", JobState.DRAFT.value, 0, urgency, message_id, now, now, now),
            )
            self.store.transition_job(job_id, JobState.SELECTED, conn=conn, extra={"pinned_model": thread["pinned_model"]})
        return SubmitResult(
            thread_id=thread_id,
            job_id=job_id,
            state=JobState.SELECTED,
            role=Role(thread["pinned_role"]) if thread["pinned_role"] else None,
            model_id=thread["pinned_model"],
            explanation=f"Continuing on the pinned model {thread['pinned_model']}.",
            timings_ms={"submit_to_selection_ms": round((time.monotonic() - submitted) * 1000, 2)},
            notices=errors,
        )

    def new_task_segment(self, thread_id: str, text: str) -> str:
        """Record that the owner started a genuinely new task in this thread.

        The model is retained; the original task keeps its own outcome.
        """
        thread = self.store.thread(thread_id)
        segment = int(thread["current_segment"]) + 1
        assessment = self.classifier(ClassifierInput(text=text))
        assessment.segment = segment
        with self.store.transaction() as conn:
            conn.execute("UPDATE threads SET current_segment=?, updated_at=? WHERE id=?", (segment, utc_now(), thread_id))
            conn.execute(
                "INSERT INTO task_assessments(id, thread_id, segment, payload, policy_version, created_at) VALUES (?,?,?,?,?,?)",
                (assessment.id, thread_id, segment, dumps(assessment.to_dict()), POLICY_VERSION, utc_now()),
            )
            self.store.event(
                "task.segment_started",
                {"segment": segment, "task_id": assessment.id, "model_retained": thread["pinned_model"]},
                thread_id=thread_id,
                conn=conn,
            )
        return assessment.id

    # --------------------------------------------------------------- override

    def override_model(self, thread_id: str, model_id: str, *, reason: str | None = None, reasoning_effort: str | None = None) -> Override:
        thread = self.store.thread(thread_id)
        self._validate_model_choice(model_id)
        reason_kind, reason_text = parse_override_reason(reason)
        task = self.store.one(
            "SELECT id FROM task_assessments WHERE thread_id=? ORDER BY segment DESC LIMIT 1", (thread_id,)
        )
        entry = self.registry.model(self.account_scope or "", model_id)
        effort = reasoning_effort
        if effort is None and entry:
            effort = entry["info"].get("default_effort")
        override = Override(
            id=new_id("ovr"),
            thread_id=thread_id,
            task_id=task["id"] if task else None,
            old_model=thread["pinned_model"],
            new_model=model_id,
            reason=reason_kind,
            reason_text=reason_text,
            at=utc_now(),
            execution_result="pending: applies to the next turn after eligibility checks",
        )
        override.validate()
        role = self.registry.role_of_model(self.account_scope or "", model_id)
        with self.store.transaction() as conn:
            conn.execute(
                "INSERT INTO overrides(id, thread_id, task_id, old_model, new_model, reason, reason_text, execution_result, at) VALUES (?,?,?,?,?,?,?,?,?)",
                (override.id, thread_id, override.task_id, override.old_model, model_id, reason_kind.value, reason_text, override.execution_result, override.at),
            )
            conn.execute(
                "UPDATE threads SET pinned_model=?, pinned_effort=?, pinned_role=?, pinned_manual=1, updated_at=? WHERE id=?",
                (model_id, effort, role.value if role else None, utc_now(), thread_id),
            )
            conn.execute(
                "INSERT INTO pin_history(id, thread_id, model_id, reasoning_effort, role, source, override_id, at) VALUES (?,?,?,?,?,?,?,?)",
                (new_id("pin"), thread_id, model_id, effort, role.value if role else None, "override", override.id, utc_now()),
            )
            self.store.event(
                "model.overridden",
                {"override_id": override.id, "old_model": override.old_model, "new_model": model_id, "reason": reason_kind.value},
                thread_id=thread_id,
                conn=conn,
            )
        return override

    # ---------------------------------------------------------------- outcome

    def record_outcome(
        self, thread_id: str, outcome: str, *, satisfaction: int | None = None, note: str | None = None, source: str = "owner"
    ) -> Outcome:
        task = self.store.one("SELECT id FROM task_assessments WHERE thread_id=? ORDER BY segment DESC LIMIT 1", (thread_id,))
        record = Outcome(
            id=new_id("out"),
            thread_id=thread_id,
            task_id=task["id"] if task else None,
            outcome=OutcomeKind(outcome),
            source="owner_abandon_action" if outcome == "abandoned" and source == "owner" else source,
            satisfaction=satisfaction,
            note=note,
        )
        record.validate()
        with self.store.transaction() as conn:
            conn.execute(
                "INSERT INTO outcomes(id, thread_id, task_id, outcome, source, satisfaction, note, recorded_at) VALUES (?,?,?,?,?,?,?,?)",
                (record.id, thread_id, record.task_id, record.outcome.value, record.source, satisfaction, note, record.recorded_at),
            )
            self.store.event("task.outcome", record.to_dict(), thread_id=thread_id, conn=conn)
        return record

    # --------------------------------------------------------------- handoff

    def finalise_architecture(
        self,
        thread_id: str,
        *,
        acceptance: AcceptanceEvidence,
        record_payload: dict[str, Any] | None = None,
        prose: str | None = None,
    ) -> HandoffResult:
        acceptance.validate()
        thread = self.store.thread(thread_id)
        project = dict(self.store.project(thread["project_id"]))

        def hold(reasons: list[str], version: int | None = None) -> HandoffResult:
            self.store.event("handoff.held", {"reasons": reasons, "architecture_version": version}, thread_id=thread_id)
            return HandoffResult("HELD", None, None, None, None, None, reasons, architecture_version=version)

        if thread["kind"] != ThreadKind.ORDINARY.value:
            return hold([f"thread {thread_id} is an {thread['kind']} thread, not an architecture thread"])
        last_answer = self.store.one(
            "SELECT id, content FROM messages WHERE thread_id=? AND role='assistant' ORDER BY created_at DESC, rowid DESC LIMIT 1",
            (thread_id,),
        )
        if record_payload is None:
            if last_answer is None:
                return hold(["no architecture answer exists in this thread yet"])
            record_payload, error = handoff_mod.extract_record(last_answer["content"] or "")
            if error:
                return hold([error])
            if record_payload is None:
                return hold(
                    [
                        "no structured architecture record was found in the latest answer; ask the architecture chat for "
                        "its architecture-record block, or run /finalise with a record file"
                    ]
                )
        record, problems = handoff_mod.validate_record(record_payload)
        if record is None or problems:
            return hold(problems)
        association = handoff_mod.check_project_association(record, project["root"])
        if association:
            return hold(association)
        if prose is None:
            prose = (last_answer["content"] if last_answer else None) or ""
        if not prose.strip():
            return hold(["the architecture prose is empty or unreadable"])

        record_hash = handoff_mod.content_hash(record.to_dict() | {"prose_sha256": handoff_mod.content_hash(prose)})
        existing_record = self.store.one(
            "SELECT version FROM architecture_records WHERE thread_id=? AND record_hash=?", (thread_id, record_hash)
        )
        if existing_record:
            version = int(existing_record["version"])
        else:
            last = self.store.one("SELECT MAX(version) AS v FROM architecture_records WHERE thread_id=?", (thread_id,))
            version = int(last["v"] or 0) + 1
            prose_blob = self.store.write_blob(prose)
            try:
                self.store.execute(
                    "INSERT INTO architecture_records(id, thread_id, version, payload, prose_blob, record_hash, created_at) VALUES (?,?,?,?,?,?,?)",
                    (new_id("arc"), thread_id, version, dumps(record.to_dict()), prose_blob, record_hash, utc_now()),
                )
            except sqlite3.IntegrityError:
                row = self.store.one("SELECT version FROM architecture_records WHERE thread_id=? AND record_hash=?", (thread_id, record_hash))
                version = int(row["version"])

        existing = self.store.one(
            "SELECT * FROM handoffs WHERE source_thread_id=? AND architecture_version=?", (thread_id, version)
        )
        if existing is not None and existing["status"] == "CREATED":
            target = self.store.thread(existing["target_thread_id"])
            job = self.store.one("SELECT id FROM jobs WHERE logical_key=?", (f"handoff:{existing['id']}",))
            self.store.event("handoff.duplicate_ignored", {"handoff_id": existing["id"]}, thread_id=thread_id)
            return HandoffResult(
                "EXISTING", existing["id"], existing["target_thread_id"], job["id"] if job else None,
                Role(target["pinned_role"]) if target["pinned_role"] else None, target["pinned_model"],
                ["this architecture version already has an implementation thread"], version, existing["package_hash"],
            )

        clarity = handoff_mod.assess_clarity(record)
        risk, highest_reasons, risk_notes = handoff_mod.assess_risk(record, prose)
        middle_binding, _ = self._binding_at_or_above(Role.MIDDLE, list(CODING_TOOLS))
        usage = self._latest_usage()
        capacity = self.estimator.estimate(
            model_id=middle_binding.model_id if middle_binding else None,
            reasoning_effort=middle_binding.reasoning_effort if middle_binding else None,
            usage=usage,
        )
        lowest_ok, lowest_note = (
            self.registry.lowest_candidate_ok(self.account_scope, CODING_TOOLS) if self.account_scope else (False, "no account")
        )
        facts = ImplementationFacts(
            requires_highest=bool(highest_reasons),
            requires_highest_reasons=highest_reasons,
            clarity=clarity.clarity,
            clarity_evidence=clarity.evidence + clarity.gaps,
            risk=risk,
            lowest_candidate_ok=lowest_ok,
            lowest_candidate_note=lowest_note,
        )
        plan = implementation_role(facts, capacity)
        binding, note = self._binding_at_or_above(plan.role, list(CODING_TOOLS))
        attachments = [
            {"path": r["source_path"], "sha256": r["original_hash"], "state": r["extraction_state"], "blob": r["original_blob"]}
            for r in self.store.all("SELECT * FROM attachments WHERE thread_id=?", (thread_id,))
        ]
        package, package_hash = handoff_mod.build_package(
            record=record,
            prose=prose,
            acceptance=acceptance,
            source_thread_id=thread_id,
            project=project,
            architecture_version=version,
            attachments=attachments,
            clarity=clarity,
            risk=risk,
            risk_notes=risk_notes,
        )
        initial_context = handoff_mod.render_initial_context(package, package_hash)
        fits, fit_note = handoff_mod.context_fits(initial_context, self.context_budget_chars)
        package_blob = self.store.write_blob(handoff_mod.canonical(package))
        capacity_dict = capacity.to_dict()

        if existing is not None:
            handoff_id = existing["id"]
        else:
            handoff_id = new_id("hof")
        if not fits:
            with self.store.transaction() as conn:
                if existing is None:
                    conn.execute(
                        "INSERT INTO handoffs(id, source_thread_id, architecture_version, architecture_hash, package_blob, package_hash, acceptance, "
                        "clarity, risk, status, hold_reasons, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (handoff_id, thread_id, version, record_hash, package_blob, package_hash, dumps(acceptance.to_dict()),
                         clarity.clarity.value, risk.value, "BLOCKED_CONTEXT", dumps([fit_note]), utc_now()),
                    )
                self.store.event("handoff.blocked_context", {"handoff_id": handoff_id, "note": fit_note, "package_hash": package_hash}, thread_id=thread_id, conn=conn)
            return HandoffResult("BLOCKED_CONTEXT", handoff_id, None, None, plan.role, None, [fit_note], version, package_hash, capacity_dict)

        target_id = new_id("thr")
        job_id = new_id("job")
        now = utc_now()
        decision = RouteDecision(
            id=new_id("rte"),
            request_id=f"handoff:{handoff_id}",
            thread_id=target_id,
            route_attempt_id=new_id("route"),
            role=plan.role,
            candidate_id=None,
            model_id=binding.model_id if binding else None,
            reasoning_effort=binding.reasoning_effort if binding else None,
            rule_ids=plan.rule_ids,
            reasons=plan.reasons + [note],
            uncertainty=plan.uncertainty,
            capacity_ref=capacity.method_version,
            manual=False,
            missing_binding=binding is None,
        )
        try:
            with self.store.transaction() as conn:
                if existing is None:
                    conn.execute(
                        "INSERT INTO handoffs(id, source_thread_id, architecture_version, architecture_hash, package_blob, package_hash, acceptance, "
                        "clarity, risk, status, hold_reasons, target_thread_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (handoff_id, thread_id, version, record_hash, package_blob, package_hash, dumps(acceptance.to_dict()),
                         clarity.clarity.value, risk.value, "CREATED", "[]", target_id, now),
                    )
                else:
                    updated = conn.execute(
                        "UPDATE handoffs SET status='CREATED', target_thread_id=?, package_blob=?, package_hash=?, hold_reasons='[]' "
                        "WHERE id=? AND status!='CREATED'",
                        (target_id, package_blob, package_hash, handoff_id),
                    )
                    if updated.rowcount != 1:
                        raise sqlite3.IntegrityError("handoff already created")
                self.store.event("handoff.ready", {"handoff_id": handoff_id, "package_hash": package_hash, "architecture_version": version}, thread_id=thread_id, conn=conn)
                conn.execute(
                    "INSERT INTO threads(id, project_id, kind, synthetic, source_thread_id, handoff_id, title, pinned_model, pinned_effort, pinned_role, "
                    "registry_revision, route_decision_id, status, created_at, updated_at, account_scope) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (target_id, thread["project_id"], ThreadKind.IMPLEMENTATION.value, thread["synthetic"], thread_id, handoff_id,
                     f"Implement: {record.goal[:60]}", decision.model_id, decision.reasoning_effort, plan.role.value,
                     binding.registry_revision if binding else None, decision.id, "active", now, now, thread["account_scope"]),
                )
                conn.execute(
                    "INSERT INTO route_decisions(id, request_id, thread_id, route_attempt_id, role, model_id, reasoning_effort, manual, payload, created_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (decision.id, decision.request_id, target_id, decision.route_attempt_id, plan.role.value, decision.model_id,
                     decision.reasoning_effort, 0, dumps(decision.to_dict() | {"capacity": capacity_dict, "clarity": clarity.clarity.value,
                                                                          "risk": risk.value, "required_tools": list(CODING_TOOLS)}), now),
                )
                if binding is not None:
                    conn.execute(
                        "INSERT INTO pin_history(id, thread_id, model_id, reasoning_effort, role, source, at) VALUES (?,?,?,?,?,?,?)",
                        (new_id("pin"), target_id, binding.model_id, binding.reasoning_effort, plan.role.value, "handoff", now),
                    )
                message_id = self.store.add_message(target_id, "user", "handoff", initial_context, provenance=f"handoff:{handoff_id}", conn=conn)
                conn.execute(
                    "INSERT INTO jobs(id, logical_key, thread_id, request_id, kind, state, priority, input_message_id, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (job_id, f"handoff:{handoff_id}", target_id, decision.request_id, "handoff_start", JobState.DRAFT.value, 0, message_id, now, now),
                )
                if binding is not None:
                    self.store.transition_job(job_id, JobState.SELECTED, conn=conn)
                    conn.execute("UPDATE jobs SET selected_at=? WHERE id=?", (now, job_id))
                else:
                    self.store.transition_job(job_id, JobState.ROUTING, conn=conn)
                    self.store.transition_job(job_id, JobState.AWAITING_MANUAL_MODEL, conn=conn, blocker="no approved model for this role: " + note)
                self.store.event(
                    "handoff.created",
                    {"handoff_id": handoff_id, "target_thread_id": target_id, "role": plan.role.value, "model_id": decision.model_id,
                     "capacity": capacity.state.value, "clarity": clarity.clarity.value, "risk": risk.value},
                    thread_id=thread_id,
                    conn=conn,
                )
        except sqlite3.IntegrityError:
            # Another client created it first (unique constraint): use theirs.
            row = self.store.one("SELECT * FROM handoffs WHERE source_thread_id=? AND architecture_version=?", (thread_id, version))
            if row is None or not row["target_thread_id"]:
                raise
            target = self.store.thread(row["target_thread_id"])
            job = self.store.one("SELECT id FROM jobs WHERE logical_key=?", (f"handoff:{row['id']}",))
            return HandoffResult(
                "EXISTING", row["id"], row["target_thread_id"], job["id"] if job else None,
                Role(target["pinned_role"]) if target["pinned_role"] else None, target["pinned_model"],
                ["created concurrently by another client"], version, row["package_hash"],
            )
        reasons = plan.reasons + plan.uncertainty + [note]
        return HandoffResult("CREATED", handoff_id, target_id, job_id, plan.role, decision.model_id, reasons, version, package_hash, capacity_dict)

    def _latest_usage(self):
        from .contracts import UsageSnapshot

        if not self.account_scope:
            return None
        row = self.store.one(
            "SELECT payload FROM usage_snapshots WHERE account_scope=? ORDER BY observed_at DESC LIMIT 1", (self.account_scope,)
        )
        if row is None:
            try:
                snapshot = self.adapter.read_usage()
            except AdapterError:
                return None
            return snapshot
        return UsageSnapshot.from_dict(json.loads(row["payload"]))

    # ------------------------------------------------------------- execution

    def run(self, job_id: str, *, blocking: bool = True) -> JobState:
        """Drive one job through eligibility, dispatch and streaming.

        One model turn at a time per process (``_turn_lock``) and across
        processes (the dispatch lease). ``blocking=False`` is used by the
        background resumer: if a foreground turn is running it defers."""
        if not self._turn_lock.acquire(blocking=blocking):
            self.store.event("job.deferred_busy", {"reason": "another turn is running in this process"}, job_id=job_id)
            return JobState(self.store.job(job_id)["state"])
        try:
            return self._run(job_id)
        finally:
            self._turn_lock.release()

    def _run(self, job_id: str) -> JobState:
        job = self.store.job(job_id)
        state = JobState(job["state"])
        if job["cancelled"] or state in {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED}:
            return state
        if state in {JobState.DRAFT, JobState.ROUTING, JobState.AWAITING_MANUAL_MODEL, JobState.DISPATCHING, JobState.RUNNING}:
            return state
        if state is JobState.RECOVERY_REQUIRED:
            return state
        thread = self.store.thread(job["thread_id"])
        binding = Binding(
            role=Role(thread["pinned_role"]) if thread["pinned_role"] else None,
            model_id=thread["pinned_model"],
            reasoning_effort=thread["pinned_effort"],
            registry_revision=thread["registry_revision"],
            manual=bool(thread["pinned_manual"]),
        )
        tools = self._thread_tools(thread)
        if not self.store.acquire_lease(DISPATCH_LEASE, self.lease_owner, DISPATCH_LEASE_TTL):
            self.store.event("job.queued", {"reason": "another model turn is running"}, thread_id=thread["id"], job_id=job_id)
            return state
        try:
            result = self.gate.check(
                binding, thread_account_scope=thread["account_scope"], required_tools=tools, thread_id=thread["id"]
            )
            if not result.ok:
                return self._block(job_id, state, result)
            if state is not JobState.READY:
                self.store.transition_job(
                    job_id, JobState.READY, eligibility_passed=True, extra={"eligibility_ms": round(result.elapsed_ms, 2)},
                )
            if result.notes:
                for note in result.notes:
                    self.ui.notify(f"Router: {note}")
            return self._dispatch(job_id, thread["id"], binding, result)
        finally:
            self.store.release_lease(DISPATCH_LEASE, self.lease_owner)

    def _thread_tools(self, thread: sqlite3.Row) -> list[str]:
        if thread["kind"] == ThreadKind.IMPLEMENTATION.value:
            return list(CODING_TOOLS)
        row = self.store.one("SELECT payload FROM route_decisions WHERE id=?", (thread["route_decision_id"],)) if thread["route_decision_id"] else None
        return list(loads(row["payload"], {}).get("required_tools", [])) if row else []

    def _block(self, job_id: str, state: JobState, result: EligibilityResult) -> JobState:
        target = result.state
        if state is target:
            self.store.execute("UPDATE jobs SET blocker=?, next_check_at=?, updated_at=? WHERE id=?", (result.blocker, result.reset_at, utc_now(), job_id))
        else:
            self.store.transition_job(job_id, target, blocker=result.blocker, next_check_at=result.reset_at, extra={"eligibility_ms": round(result.elapsed_ms, 2)})
        job = self.store.job(job_id)
        if target is JobState.WAITING_USAGE:
            self.store.event("job.queued", {"blocker": result.blocker, "reset_at": result.reset_at}, thread_id=job["thread_id"], job_id=job_id)
            self.ui.notify(
                "Router: Included usage is unavailable. Work is saved.\n"
                "This chat will continue with the same model when it becomes available"
                + (f" (reported reset: {result.reset_at})." if result.reset_at else " (availability time unknown).")
            )
        else:
            self.ui.notify(f"Router: Not sent — {result.blocker}. The model choice is kept.")
        return target

    def _dispatch(self, job_id: str, thread_id: str, binding: Binding, eligibility: EligibilityResult) -> JobState:
        job = self.store.job(job_id)
        thread = self.store.thread(thread_id)
        text = self._turn_input(job, thread)
        dispatch_id = new_id("dsp")
        now = utc_now()
        with self.store.transaction() as conn:
            conn.execute(
                "INSERT INTO dispatches(id, dispatch_id, job_id, thread_id, phase, requested_model, requested_effort, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (new_id("dsr"), dispatch_id, job_id, thread_id, DispatchPhase.PREPARED.value, binding.model_id, binding.reasoning_effort, now, now),
            )
            self.store.transition_job(job_id, JobState.DISPATCHING, expected=JobState.READY, conn=conn)
            self.store.event("dispatch.prepared", {"dispatch_id": dispatch_id, "model": binding.model_id, "effort": binding.reasoning_effort}, thread_id=thread_id, job_id=job_id, conn=conn)

        # Provider thread: create once (two-stage), or resume on the same pin.
        try:
            provider_thread_id = self._ensure_provider_thread(thread_id, binding, eligibility)
        except _Hold as hold:
            return self._hold_before_send(job_id, dispatch_id, hold.state, hold.reason)
        except AdapterError as exc:
            # e.g. thread/resume failed: no turn was sent, so this is safe to retry later.
            return self._hold_before_send(job_id, dispatch_id, JobState.BLOCKED_CAPABILITY, f"provider thread could not be resumed: {exc}")
        except Exception as exc:
            return self._hold_before_send(job_id, dispatch_id, JobState.BLOCKED_CAPABILITY, f"unexpected error before sending: {exc}")

        try:
            self._set_dispatch(dispatch_id, DispatchPhase.SENT, expected=[DispatchPhase.PREPARED])
        except StaleState:
            # Recovery (another process) already settled this dispatch: never send it.
            self.store.event("dispatch.abandoned", {"dispatch_id": dispatch_id, "reason": "phase changed before send"}, thread_id=thread_id, job_id=job_id)
            return JobState(self.store.job(job_id)["state"])
        self.store.event("dispatch.sent", {"dispatch_id": dispatch_id}, thread_id=thread_id, job_id=job_id)
        selected_at = job["selected_at"]
        timings = {"eligibility_ms": round(eligibility.elapsed_ms, 2)}
        if selected_at:
            from .contracts import parse_utc

            timings["selected_to_dispatch_ms"] = round((parse_utc(utc_now()) - parse_utc(selected_at)).total_seconds() * 1000, 2)
        self.store.execute("UPDATE dispatches SET timings=? WHERE dispatch_id=?", (dumps(timings), dispatch_id))
        try:
            events = self.adapter.start_turn(
                provider_thread_id,
                text,
                dispatch_id,
                binding=binding,
                approval_handler=lambda request: self._approval(request, thread_id),
            )
            return self._consume(job_id, thread_id, dispatch_id, provider_thread_id, binding, events)
        except DispatchUncertain as exc:
            return self._uncertain(job_id, thread_id, dispatch_id, str(exc))
        except KeyboardInterrupt:
            self._uncertain(job_id, thread_id, dispatch_id, "interrupted by the owner while the turn was in flight")
            raise
        except AdapterError as exc:
            current = JobState(self.store.job(job_id)["state"])
            if exc.executed == "no" and current is JobState.DISPATCHING:
                self._set_dispatch(dispatch_id, DispatchPhase.NOT_EXECUTED, error=str(exc))
                self.store.event("turn.failed", {"dispatch_id": dispatch_id, "error": str(exc), "executed": "no"}, thread_id=thread_id, job_id=job_id)
                if exc.code in USAGE_ERROR_CODES:
                    self.store.transition_job(job_id, JobState.WAITING_USAGE, blocker=f"included usage unavailable: {exc}")
                    self.ui.notify("Router: Included usage is unavailable. Work is saved.")
                    return JobState.WAITING_USAGE
                self.store.transition_job(job_id, JobState.FAILED, blocker=str(exc))
                self.ui.notify(f"Router: The provider refused the turn: {exc}")
                return JobState.FAILED
            return self._uncertain(job_id, thread_id, dispatch_id, str(exc))
        except Exception as exc:  # never leave a sent turn stuck in DISPATCHING/RUNNING
            self.store.event("dispatch.unexpected_error", {"dispatch_id": dispatch_id, "error": repr(exc)}, thread_id=thread_id, job_id=job_id)
            return self._uncertain(job_id, thread_id, dispatch_id, f"unexpected error after sending: {exc}")

    def _hold_before_send(self, job_id: str, dispatch_id: str, state: JobState, reason: str) -> JobState:
        self._set_dispatch(dispatch_id, DispatchPhase.NOT_EXECUTED, error=reason)
        self.store.transition_job(job_id, state, blocker=reason)
        self.ui.notify(f"Router: Held — {reason}")
        return state

    def _turn_input(self, job: sqlite3.Row, thread: sqlite3.Row) -> str:
        checkpoint = self.store.one(
            "SELECT payload FROM checkpoints WHERE job_id=? ORDER BY created_at DESC LIMIT 1", (job["id"],)
        )
        message = self.store.one("SELECT content FROM messages WHERE id=?", (job["input_message_id"],))
        text = message["content"] if message else ""
        context = self.store.one(
            "SELECT content FROM messages WHERE thread_id=? AND kind='attachment_context' ORDER BY created_at DESC LIMIT 1",
            (thread["id"],),
        )
        if context and job["kind"] == "user_turn":
            text = f"{text}\n\n{context['content']}"
        if checkpoint is not None:
            payload = loads(checkpoint["payload"])
            text = (
                "Continue the interrupted task from this saved checkpoint on the same model. Do not repeat completed tool "
                "commands; inspect the current worktree state first.\n\n```json\n"
                + json.dumps(payload, indent=2)
                + "\n```\n\nOriginal request:\n"
                + text
            )
        return text

    def _ensure_provider_thread(self, thread_id: str, binding: Binding, eligibility: EligibilityResult) -> str:
        thread = self.store.thread(thread_id)
        project = self.store.project(thread["project_id"])
        workspace, sandbox, instructions = self._execution_profile(thread, project)
        if thread["provider_thread_id"]:
            provider_id = thread["provider_thread_id"]
            generation = getattr(self.adapter, "connection_generation", 0)
            if generation != self._loaded_generation:
                self._loaded_provider_threads.clear()  # a new App Server process has nothing loaded
                self._loaded_generation = generation
            if provider_id not in self._loaded_provider_threads:
                resumed = self.adapter.resume_thread(provider_id, binding, workspace=workspace, sandbox=sandbox)
                if resumed.model_id and resumed.model_id != binding.model_id:
                    self.store.event(
                        "model.resume_mismatch",
                        {"expected": binding.model_id, "provider_reported": resumed.model_id},
                        thread_id=thread_id,
                    )
                    raise _Hold(
                        JobState.BLOCKED_CAPABILITY,
                        f"resuming would run on {resumed.model_id}, not the pinned {binding.model_id}; held for your decision",
                    )
                self._loaded_provider_threads.add(provider_id)
            return provider_id
        if thread["provider_thread_phase"] in {"CREATING", "UNCERTAIN"}:
            raise _Hold(
                JobState.RECOVERY_REQUIRED,
                "an earlier provider-thread creation has an unknown result; resolve it with /recover before a new one is made",
            )
        with self.store.transaction() as conn:
            conn.execute(
                "UPDATE threads SET provider_thread_phase='CREATING', account_scope=COALESCE(account_scope, ?), updated_at=? WHERE id=?",
                (eligibility.account.account_scope if eligibility.account else None, utc_now(), thread_id),
            )
        try:
            created = self.adapter.create_thread(binding, developer_instructions=instructions, workspace=workspace, sandbox=sandbox)
        except AdapterError as exc:
            if exc.executed == "no":
                self.store.execute("UPDATE threads SET provider_thread_phase='NONE' WHERE id=?", (thread_id,))
                raise _Hold(JobState.BLOCKED_CAPABILITY, f"provider thread could not be created: {exc}") from exc
            self.store.execute("UPDATE threads SET provider_thread_phase='UNCERTAIN' WHERE id=?", (thread_id,))
            raise _Hold(JobState.RECOVERY_REQUIRED, f"provider thread creation result unknown: {exc}") from exc
        with self.store.transaction() as conn:
            conn.execute(
                "UPDATE threads SET provider_thread_id=?, provider_thread_phase='CREATED', updated_at=? WHERE id=?",
                (created.provider_thread_id, utc_now(), thread_id),
            )
            self.store.event("thread.provider_created", {"provider_thread_id": created.provider_thread_id, "model": created.model_id}, thread_id=thread_id, conn=conn)
        self._loaded_provider_threads.add(created.provider_thread_id)
        self._loaded_generation = getattr(self.adapter, "connection_generation", 0)
        if created.model_id and created.model_id != binding.model_id:
            raise _Hold(JobState.BLOCKED_CAPABILITY, f"provider created the thread on {created.model_id}, not the pinned {binding.model_id}")
        return created.provider_thread_id

    def _execution_profile(self, thread: sqlite3.Row, project: sqlite3.Row) -> tuple[str, str, str]:
        workspace = project["worktree"] or project["root"]
        if thread["kind"] == ThreadKind.IMPLEMENTATION.value:
            return workspace, "workspace-write", CODING_INSTRUCTIONS
        assessment = self.store.one("SELECT payload FROM task_assessments WHERE thread_id=? ORDER BY segment LIMIT 1", (thread["id"],))
        kind = TaskKind(loads(assessment["payload"])["task_kind"]) if assessment else TaskKind.UNKNOWN
        if kind in CODING_KINDS:
            return workspace, "workspace-write", CODING_INSTRUCTIONS
        if kind in {TaskKind.ARCHITECTURE, TaskKind.PRODUCT_DECISION, TaskKind.UI_DECISION, TaskKind.TRADEOFF}:
            return workspace, "read-only", ARCHITECTURE_INSTRUCTIONS
        return workspace, "read-only", WRITING_INSTRUCTIONS

    def _set_dispatch(
        self, dispatch_id: str, phase: DispatchPhase, *, expected: Iterable[DispatchPhase] | None = None, **fields: Any
    ) -> None:
        """Update a dispatch; with ``expected`` it is a compare-and-swap on the phase."""
        assignments = ["phase=?", "updated_at=?"]
        values: list[Any] = [phase.value, utc_now()]
        for key, value in fields.items():
            assignments.append(f"{key}=?")
            values.append(value)
        sql = f"UPDATE dispatches SET {', '.join(assignments)} WHERE dispatch_id=?"
        values.append(dispatch_id)
        if expected is not None:
            allowed = [p.value for p in expected]
            sql += f" AND phase IN ({','.join('?' * len(allowed))})"
            values.extend(allowed)
        cursor = self.store.execute(sql, tuple(values))
        if expected is not None and cursor.rowcount != 1:
            raise StaleState(f"dispatch {dispatch_id} is no longer in phase {sorted(allowed)}")

    def _consume(self, job_id, thread_id, dispatch_id, provider_thread_id, binding: Binding, events: Iterable[TurnEvent]) -> JobState:
        answer_id: str | None = None
        provider_turn_id: str | None = None
        buffer: list[str] = []
        last_flush = time.monotonic()
        fatal: list[str] = []
        usage_exhausted = False
        rerouted: tuple[str, str] | None = None
        spend_stop: str | None = None
        final_status: TurnStatus | None = None
        tool_results: list[dict[str, Any]] = []
        last_renewal = time.monotonic()

        def flush(complete: bool | None = None) -> None:
            nonlocal buffer, last_flush
            if answer_id and (buffer or complete is not None):
                self.store.append_message_content(answer_id, "".join(buffer), complete=complete)
                buffer = []
                last_flush = time.monotonic()

        for event in events:
            if time.monotonic() - last_renewal > DISPATCH_LEASE_TTL / 4:
                self.store.acquire_lease(DISPATCH_LEASE, self.lease_owner, DISPATCH_LEASE_TTL)  # long turns keep the lease
                last_renewal = time.monotonic()
            if event.kind == "acknowledged":
                provider_turn_id = event.provider_turn_id
                self._set_dispatch(dispatch_id, DispatchPhase.ACKNOWLEDGED, expected=[DispatchPhase.SENT], provider_turn_id=provider_turn_id)
                self.store.transition_job(job_id, JobState.RUNNING, expected=JobState.DISPATCHING)
                self.store.event("dispatch.acknowledged", {"dispatch_id": dispatch_id, "provider_turn_id": provider_turn_id}, thread_id=thread_id, job_id=job_id)
                answer_id = self.store.add_message(thread_id, "assistant", "answer", "", provenance=f"dispatch:{dispatch_id}", dispatch_id=dispatch_id, complete=False)
                self._apply_pending_override(thread_id, dispatch_id)
            elif event.kind == "delta" and event.text:
                if answer_id is None:
                    continue
                buffer.append(event.text)
                self.ui.stream(event.text)
                if time.monotonic() - last_flush > 0.25 or sum(len(b) for b in buffer) > 2000:
                    flush()
            elif event.kind == "warning":
                self.store.event("turn.warning", {"dispatch_id": dispatch_id, "text": event.text}, thread_id=thread_id, job_id=job_id)
            elif event.kind == "error":
                self.store.event(
                    "turn.error",
                    {"dispatch_id": dispatch_id, "error": event.error, "code": event.error_code, "will_retry": event.will_retry, "fatal": event.fatal},
                    thread_id=thread_id,
                    job_id=job_id,
                )
                if event.fatal:
                    fatal.append(event.error or "provider error")
                    if event.error_code in USAGE_ERROR_CODES:
                        usage_exhausted = True
            elif event.kind == "rerouted":
                rerouted = (event.from_model or binding.model_id, event.to_model or "unknown")
                self._set_dispatch(dispatch_id, DispatchPhase.ACKNOWLEDGED, observed_model=event.to_model, observed_model_note="provider reported reroute")
                self.store.event("model.rerouted", {"dispatch_id": dispatch_id, "from": rerouted[0], "to": rerouted[1]}, thread_id=thread_id, job_id=job_id)
                self.ui.notify(
                    f"Router: The provider rerouted this turn from {rerouted[0]} to {rerouted[1]}. "
                    "Your pinned model is unchanged; stopping this turn and keeping its partial output."
                )
                if provider_turn_id:
                    try:
                        result = self.adapter.interrupt_turn(provider_thread_id, provider_turn_id)
                        self.store.event("turn.interrupted", {"reason": "reroute", "result": result}, thread_id=thread_id, job_id=job_id)
                    except AdapterError as exc:
                        self.store.event("turn.interrupt_failed", {"error": str(exc)}, thread_id=thread_id, job_id=job_id)
            elif event.kind in {"usage_changed", "account_changed"}:
                self.gate.invalidate(f"provider notification: {event.kind}")
                self.store.event("usage.changed" if event.kind == "usage_changed" else "account.changed", event.data, thread_id=thread_id, job_id=job_id)
                if spend_stop is None:
                    spend_stop = self._spend_recheck_mid_turn()
                    if spend_stop is not None:
                        self.store.event("turn.spend_stop", {"dispatch_id": dispatch_id, "reason": spend_stop}, thread_id=thread_id, job_id=job_id)
                        self.ui.notify(f"Router: Stopping this turn — {spend_stop}. The partial answer is kept; the chat keeps its model.")
                        if provider_turn_id:
                            try:
                                self.adapter.interrupt_turn(provider_thread_id, provider_turn_id)
                            except AdapterError as exc:
                                self.store.event("turn.interrupt_failed", {"error": str(exc)}, thread_id=thread_id, job_id=job_id)
            elif event.kind == "approval":
                self.store.event("approval.decided", event.data | {"summary": event.text}, thread_id=thread_id, job_id=job_id)
            elif event.kind == "item" and event.item:
                if event.item.get("type") in {"commandExecution", "fileChange", "mcpToolCall", "webSearch"}:
                    tool_results.append(_summarise_item(event.item))
            elif event.kind == "completed":
                final_status = event.status or TurnStatus.UNKNOWN
                if event.error:
                    fatal.append(event.error)
                break
        flush()

        if answer_id is None:
            # No acknowledgement observed: execution unknown.
            return self._uncertain(job_id, thread_id, dispatch_id, "the provider stream ended before acknowledging the turn")
        if final_status is None:
            flush(complete=False)
            return self._uncertain(job_id, thread_id, dispatch_id, "the provider stream ended without a final turn status")

        observed_note = "provider reported reroute" if rerouted else "not reported"
        partial = bool(fatal) or rerouted is not None or final_status is not TurnStatus.COMPLETED
        self._set_dispatch(
            dispatch_id,
            DispatchPhase.TERMINAL,
            turn_status=(TurnStatus.PARTIAL.value if partial and final_status is TurnStatus.COMPLETED else final_status.value),
            error="; ".join(fatal) or None,
            observed_model_note=observed_note,
        )
        with self.store.transaction() as conn:
            conn.execute(
                "UPDATE messages SET complete=?, kind=? WHERE id=?",
                (0 if partial else 1, "partial" if partial else "answer", answer_id),
            )
        if spend_stop is not None and not usage_exhausted:
            self._checkpoint(job_id, thread_id, dispatch_id, provider_turn_id, answer_id, tool_results, f"spend boundary changed mid-turn: {spend_stop}")
            self.store.transition_job(job_id, JobState.PAUSED, blocker=f"stopped mid-turn: {spend_stop}", extra={"dispatch_id": dispatch_id})
            return JobState.PAUSED
        if usage_exhausted:
            self._checkpoint(job_id, thread_id, dispatch_id, provider_turn_id, answer_id, tool_results, "included usage ran out mid-turn")
            self.store.transition_job(job_id, JobState.PAUSED, blocker="included usage ran out; work saved", extra={"dispatch_id": dispatch_id})
            self.store.event("turn.failed", {"dispatch_id": dispatch_id, "partial": True, "reason": "usage"}, thread_id=thread_id, job_id=job_id)
            self.ui.notify(
                "Router: Included usage is unavailable. Work is saved.\n"
                "This chat will continue with the same model when it becomes available."
            )
            return JobState.PAUSED
        if fatal or final_status in {TurnStatus.FAILED}:
            self.store.transition_job(job_id, JobState.FAILED, blocker="; ".join(fatal) or "provider reported failure")
            self.store.event("turn.failed", {"dispatch_id": dispatch_id, "errors": fatal, "status": final_status.value}, thread_id=thread_id, job_id=job_id)
            self.ui.notify("Router: The turn failed; any partial answer is saved and marked partial. " + ("; ".join(fatal)))
            return JobState.FAILED
        if rerouted or final_status is TurnStatus.INTERRUPTED:
            job = self.store.job(job_id)
            if job["cancelled"]:
                return JobState.CANCELLED
            self.store.transition_job(job_id, JobState.FAILED, blocker="interrupted" + (" after provider reroute" if rerouted else ""))
            self.store.event("turn.interrupted", {"dispatch_id": dispatch_id, "rerouted": bool(rerouted)}, thread_id=thread_id, job_id=job_id)
            return JobState.FAILED
        self.store.transition_job(job_id, JobState.SUCCEEDED)
        self.store.event("turn.completed", {"dispatch_id": dispatch_id, "provider_turn_id": provider_turn_id}, thread_id=thread_id, job_id=job_id)
        return JobState.SUCCEEDED

    def _spend_recheck_mid_turn(self) -> str | None:
        """Re-read account, usage and the spend decision after a provider limit or
        credit notification. Returns a reason to stop, or None to continue."""
        try:
            account = self.adapter.read_account()
            usage = self.adapter.read_usage()
            decision = self.adapter.check_spend_boundary(account, usage)
        except Exception as exc:  # cannot confirm -> stop the turn safely
            return f"spend boundary could not be re-checked ({type(exc).__name__}: {exc})"
        if self.live and decision.synthetic:
            return "simulated spend evidence cannot cover a live turn"
        if decision.status is not SpendStatus.ALLOWED_INCLUDED_ONLY:
            return f"spend boundary is now {decision.status.value}: " + "; ".join(decision.reasons + decision.missing)
        return None

    def _apply_pending_override(self, thread_id: str, dispatch_id: str) -> None:
        self.store.execute(
            "UPDATE overrides SET execution_result=? WHERE thread_id=? AND execution_result LIKE 'pending%'",
            (f"executed: first turn on the new model is dispatch {dispatch_id}", thread_id),
        )

    def _uncertain(self, job_id: str, thread_id: str, dispatch_id: str, why: str) -> JobState:
        self._set_dispatch(dispatch_id, DispatchPhase.UNCERTAIN, error=why)
        self.store.event("dispatch.uncertain", {"dispatch_id": dispatch_id, "reason": why}, thread_id=thread_id, job_id=job_id)
        current = JobState(self.store.job(job_id)["state"])
        if current in {JobState.DISPATCHING, JobState.RUNNING}:
            self.store.transition_job(job_id, JobState.RECOVERY_REQUIRED, blocker=why)
        return self.reconcile(job_id)

    def _checkpoint(self, job_id, thread_id, dispatch_id, provider_turn_id, answer_id, tool_results, reason) -> str:
        thread = self.store.thread(thread_id)
        project = self.store.project(thread["project_id"])
        worktree = project["worktree"] or project["root"]
        changed = _git_changed_files(worktree) if thread["kind"] == ThreadKind.IMPLEMENTATION.value else []
        steps: list[dict[str, Any]] = []
        if thread["handoff_id"]:
            handoff = self.store.one("SELECT package_blob FROM handoffs WHERE id=?", (thread["handoff_id"],))
            if handoff and handoff["package_blob"]:
                package = json.loads(self.store.read_blob_text(handoff["package_blob"]))
                steps = package["architecture_record"]["steps"]
        payload = {
            "reason": reason,
            "thread_id": thread_id,
            "job_id": job_id,
            "dispatch_id": dispatch_id,
            "provider_turn_id": provider_turn_id,
            "worktree": worktree,
            "pinned_model": thread["pinned_model"],
            "pinned_effort": thread["pinned_effort"],
            "partial_output_message_id": answer_id,
            "completed_steps": "unknown: inspect the worktree and partial output",
            "planned_steps": steps,
            "changed_files": changed,
            "tool_results": tool_results,
            "continuation_constraints": [
                f"same pinned model {thread['pinned_model']}",
                "do not replay completed tool commands",
                "inspect actual worktree state before continuing",
                "no auto-commit; do not discard unrelated user work",
            ],
            "created_at": utc_now(),
        }
        checkpoint_id = new_id("chk")
        self.store.execute(
            "INSERT INTO checkpoints(id, thread_id, job_id, dispatch_id, payload, created_at) VALUES (?,?,?,?,?,?)",
            (checkpoint_id, thread_id, job_id, dispatch_id, dumps(payload), utc_now()),
        )
        self.store.event("checkpoint.saved", {"checkpoint_id": checkpoint_id, "reason": reason, "changed_files": changed}, thread_id=thread_id, job_id=job_id)
        return checkpoint_id

    # ------------------------------------------------------------- approvals

    def _approval(self, request: ApprovalRequest, thread_id: str) -> str:
        thread = self.store.thread(thread_id)
        project = self.store.project(thread["project_id"])
        scope = [Path(p) for p in loads(project["write_scope"], [])]
        reasons: list[str] = []
        command = request.command or ""
        if DESTRUCTIVE_COMMANDS.search(command):
            reasons.append("destructive command")
        if CREDENTIAL_ACCESS.search(command) or any(CREDENTIAL_ACCESS.search(p) for p in request.paths):
            reasons.append("credential access")
        if EXTERNAL_UPLOAD.search(command):
            reasons.append("new external upload")
        for path in request.paths + ([request.cwd] if request.cwd else []):
            resolved = Path(path).expanduser()
            if not resolved.is_absolute():
                resolved = Path(project["worktree"] or project["root"]) / resolved
            resolved = resolved.resolve()
            if not any(resolved == s or s in resolved.parents for s in scope):
                reasons.append(f"outside the authorised write scope: {path}")
        if reasons:
            decision = "decline"
            self.ui.notify(f"Router: Declined automatically ({'; '.join(sorted(set(reasons)))}): {request.summary or command}")
        else:
            decision = self.ui.ask_approval(request)
            if decision not in {"accept", "decline", "cancel"}:
                decision = "decline"
        self.store.event(
            "approval.requested",
            {"kind": request.kind, "command": command, "paths": request.paths, "cwd": request.cwd, "decision": decision, "auto_reasons": reasons},
            thread_id=thread_id,
        )
        return decision

    # ----------------------------------------------------- queue and recovery

    def waiting_jobs(self) -> list[dict[str, Any]]:
        """Jobs the owner asked to run that are queued, blocked or awaiting reconciliation."""
        states = tuple(s.value for s in (*WAITING_JOB_STATES, JobState.SELECTED, JobState.READY, JobState.RECOVERY_REQUIRED))
        return [
            dict(r)
            for r in self.store.all(
                f"SELECT id, thread_id, state, blocker, next_check_at FROM jobs WHERE cancelled=0 AND user_requested=1 "
                f"AND state IN ({','.join('?' * len(states))}) ORDER BY created_at",
                states,
            )
        ]

    def wake(self, *, now: str | None = None, blocking: bool = True) -> list[tuple[str, JobState]]:
        """Re-check queued jobs the owner asked to run (fresh eligibility each)."""
        if not self._turn_lock.acquire(blocking=blocking):
            return []
        try:
            return self._wake(blocking=blocking)
        finally:
            self._turn_lock.release()

    def _wake(self, *, blocking: bool) -> list[tuple[str, JobState]]:
        results = []
        for row in self.store.all("SELECT id FROM jobs WHERE state='RECOVERY_REQUIRED' AND cancelled=0"):
            final = self.reconcile(row["id"])  # reads only; never sends
            if final is not JobState.RECOVERY_REQUIRED:
                results.append((row["id"], final))
        rows = self.store.all(
            "SELECT * FROM jobs WHERE cancelled=0 AND user_requested=1 AND state IN (?,?,?,?,?,?,?) ORDER BY priority, "
            "CASE urgency WHEN 'now' THEN 0 WHEN 'normal' THEN 1 WHEN 'later' THEN 2 ELSE 1 END, created_at",
            tuple(s.value for s in (*WAITING_JOB_STATES, JobState.SELECTED, JobState.READY)),
        )
        for row in rows:
            self.store.event("job.woken", {"from": row["state"]}, thread_id=row["thread_id"], job_id=row["id"])
            results.append((row["id"], self.run(row["id"], blocking=blocking)))
        return results

    def cancel(self, job_id: str) -> JobState:
        job = self.store.job(job_id)
        state = JobState(job["state"])
        if state in {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED}:
            return state
        if state is JobState.RUNNING:
            dispatch = self.store.one(
                "SELECT * FROM dispatches WHERE job_id=? AND phase='ACKNOWLEDGED' ORDER BY created_at DESC LIMIT 1", (job_id,)
            )
            thread = self.store.thread(job["thread_id"])
            if dispatch and dispatch["provider_turn_id"] and thread["provider_thread_id"]:
                try:
                    self.adapter.interrupt_turn(thread["provider_thread_id"], dispatch["provider_turn_id"])
                except AdapterError as exc:
                    self.store.event("turn.interrupt_failed", {"error": str(exc)}, job_id=job_id)
        if state in {JobState.DISPATCHING}:
            raise ContractError("the job is mid-dispatch; wait for acknowledgement, then cancel")
        self.store.transition_job(job_id, JobState.CANCELLED, blocker="cancelled by the owner")
        return JobState.CANCELLED

    def recover(self) -> list[dict[str, Any]]:
        """Startup recovery. Never resends; reconciles or asks.

        Takes the dispatch lease, so it never touches a turn another live
        process is dispatching right now."""
        with self._turn_lock:  # never while this process has a turn in flight
            if not self.store.acquire_lease(DISPATCH_LEASE, self.lease_owner, DISPATCH_LEASE_TTL):
                self.store.event("recovery.skipped", {"reason": "another live process holds the dispatch lease"})
                return []
            try:
                return self._recover()
            finally:
                self.store.release_lease(DISPATCH_LEASE, self.lease_owner)

    def _recover(self) -> list[dict[str, Any]]:
        report: list[dict[str, Any]] = []
        for row in self.store.all("SELECT * FROM jobs WHERE state='ROUTING'"):
            # No provider call happens during routing: re-route with a new fence.
            attempt = new_id("route")
            self.store.execute("UPDATE jobs SET route_attempt_id=? WHERE id=?", (attempt, row["id"]))
            self.store.event("route.restarted", {"route_attempt_id": attempt}, thread_id=row["thread_id"], job_id=row["id"])
            message = self.store.one("SELECT content FROM messages WHERE id=?", (row["input_message_id"],))
            result = self._route_new(
                row["thread_id"], row["id"], attempt, row["request_id"], ClassifierInput(text=message["content"] if message else ""),
                time.monotonic(), {"cold": 1.0, "after_restart": 1.0}, [],
            )
            report.append({"job_id": row["id"], "action": "rerouted", "state": result.state.value})
        for thread in self.store.all("SELECT * FROM threads WHERE provider_thread_phase='CREATING'"):
            # thread/start may have reached the provider: never create another blindly.
            self.store.execute("UPDATE threads SET provider_thread_phase='UNCERTAIN' WHERE id=?", (thread["id"],))
            self.store.event("thread.provider_creation_uncertain", {}, thread_id=thread["id"])
            report.append({"thread_id": thread["id"], "action": "provider_thread_creation_uncertain"})
        for dispatch in self.store.all("SELECT * FROM dispatches WHERE phase IN ('PREPARED','SENT','UNCERTAIN','ACKNOWLEDGED')"):
            job = self.store.job(dispatch["job_id"])
            state = JobState(job["state"])
            if dispatch["phase"] == DispatchPhase.PREPARED.value:
                self._set_dispatch(dispatch["dispatch_id"], DispatchPhase.NOT_EXECUTED, error="recovered: turn never sent")
                creation_uncertain = self.store.thread(job["thread_id"])["provider_thread_phase"] == "UNCERTAIN"
                if state is JobState.DISPATCHING:
                    if creation_uncertain:
                        self.store.transition_job(job["id"], JobState.RECOVERY_REQUIRED, blocker="provider thread creation result unknown")
                        self._ask_recovery(job["id"], dispatch["dispatch_id"], "a provider thread may have been created before the restart")
                    else:
                        self.store.transition_job(job["id"], JobState.PAUSED, blocker="restarted before sending; same model kept")
                report.append({
                    "job_id": job["id"],
                    "action": "provider_thread_uncertain" if creation_uncertain else "not_sent_resumable",
                    "dispatch_id": dispatch["dispatch_id"],
                })
                continue
            if dispatch["phase"] != DispatchPhase.UNCERTAIN.value:
                self._set_dispatch(dispatch["dispatch_id"], DispatchPhase.UNCERTAIN, error="process stopped before the final status was saved")
            if state in {JobState.DISPATCHING, JobState.RUNNING}:
                self.store.transition_job(job["id"], JobState.RECOVERY_REQUIRED, blocker="restart during a provider turn")
            final = self.reconcile(job["id"])
            report.append({"job_id": job["id"], "action": "reconciled", "state": final.value, "dispatch_id": dispatch["dispatch_id"]})
        self.store.event("recovery.completed", {"items": len(report)})
        return report

    def reconcile(self, job_id: str) -> JobState:
        job = self.store.job(job_id)
        if JobState(job["state"]) is not JobState.RECOVERY_REQUIRED:
            return JobState(job["state"])
        thread = self.store.thread(job["thread_id"])
        dispatch = self.store.one(
            "SELECT * FROM dispatches WHERE job_id=? AND phase='UNCERTAIN' ORDER BY created_at DESC LIMIT 1", (job_id,)
        )
        if dispatch is None or not thread["provider_thread_id"]:
            return JobState.RECOVERY_REQUIRED
        try:
            state = self.adapter.read_thread(thread["provider_thread_id"])
        except AdapterError as exc:
            self.store.event("recovery.read_failed", {"error": str(exc)}, thread_id=thread["id"], job_id=job_id)
            self._ask_recovery(job_id, dispatch["dispatch_id"], f"the provider thread could not be read ({exc})")
            return JobState.RECOVERY_REQUIRED
        match = None
        for turn in state.turns:
            if dispatch["provider_turn_id"] and turn.provider_turn_id == dispatch["provider_turn_id"]:
                match = turn
            elif turn.client_message_id and turn.client_message_id == dispatch["dispatch_id"]:
                match = turn
        if match is None:
            self._ask_recovery(job_id, dispatch["dispatch_id"], "no matching turn was found, but that does not prove it never ran")
            return JobState.RECOVERY_REQUIRED
        self._set_dispatch(dispatch["dispatch_id"], DispatchPhase.ACKNOWLEDGED, provider_turn_id=match.provider_turn_id)
        self.store.event("dispatch.reconciled", {"dispatch_id": dispatch["dispatch_id"], "provider_turn_id": match.provider_turn_id, "status": match.status.value}, thread_id=thread["id"], job_id=job_id)
        if match.status is TurnStatus.IN_PROGRESS:
            # Nothing in this process is reading that stream; check again on the next wake.
            self.store.execute(
                "UPDATE jobs SET blocker=? WHERE id=?",
                ("the provider turn is still running; `router.py wake` checks it again", job_id),
            )
            return JobState.RECOVERY_REQUIRED
        existing = self.store.one("SELECT id FROM messages WHERE dispatch_id=? AND role='assistant'", (dispatch["dispatch_id"],))
        text = match.text or ""
        if existing is None:
            self.store.add_message(thread["id"], "assistant", "answer" if match.status is TurnStatus.COMPLETED else "partial", text,
                                   provenance="reconciled from provider thread", dispatch_id=dispatch["dispatch_id"], complete=match.status is TurnStatus.COMPLETED)
        elif text:
            self.store.execute("UPDATE messages SET content=?, complete=? WHERE id=?", (text, int(match.status is TurnStatus.COMPLETED), existing["id"]))
        self._set_dispatch(dispatch["dispatch_id"], DispatchPhase.TERMINAL, turn_status=match.status.value)
        final = JobState.SUCCEEDED if match.status is TurnStatus.COMPLETED else JobState.FAILED
        self.store.transition_job(job_id, final, blocker=None if final is JobState.SUCCEEDED else f"provider status {match.status.value}")
        return final

    def _ask_recovery(self, job_id: str, dispatch_id: str, why: str) -> None:
        current = self.store.job(job_id)["blocker"]
        question = (
            f"Router: A send may or may not have run ({why}). It will NOT be resent automatically. "
            f"Choose: /recover {job_id} resend (you confirm it did not run) or /recover {job_id} drop."
        )
        if current == question:
            return  # already asked; do not repeat on every wake
        self.store.execute("UPDATE jobs SET blocker=? WHERE id=?", (question, job_id))
        self.store.event("recovery.question", {"dispatch_id": dispatch_id, "why": why}, job_id=job_id)
        self.ui.notify(question)

    def resolve_recovery(self, job_id: str, decision: str) -> JobState:
        job = self.store.job(job_id)
        if JobState(job["state"]) is not JobState.RECOVERY_REQUIRED:
            raise ContractError(f"job {job_id} is {job['state']}, not awaiting recovery")
        if decision == "drop":
            self.store.transition_job(job_id, JobState.CANCELLED, blocker="owner dropped the uncertain operation")
            return JobState.CANCELLED
        if decision != "resend":
            raise ContractError("decision must be 'resend' or 'drop'")
        for dispatch in self.store.all("SELECT dispatch_id FROM dispatches WHERE job_id=? AND phase='UNCERTAIN'", (job_id,)):
            self._set_dispatch(dispatch["dispatch_id"], DispatchPhase.NOT_EXECUTED, error="owner confirmed it did not execute")
        thread = self.store.thread(job["thread_id"])
        if thread["provider_thread_phase"] == "UNCERTAIN":
            self.store.execute("UPDATE threads SET provider_thread_phase='NONE' WHERE id=?", (thread["id"],))
        self.store.transition_job(
            job_id, JobState.PAUSED, owner_confirmed_not_executed=True,
            blocker="owner confirmed the uncertain send did not run; re-checking before sending",
        )
        self.store.event("recovery.owner_confirmed_not_executed", {}, thread_id=thread["id"], job_id=job_id)
        return self.run(job_id)

    # ------------------------------------------------------------ evaluation

    def create_evaluation_job(self, project: str, model_id: str, text: str, *, run_id: str, reasoning_effort: str | None = None) -> dict[str, str]:
        """An evaluation thread may use a discovered CANDIDATE model (comparison
        only). It is excluded from user metrics and never changes bindings."""
        if not self._started:
            self.start()
        self._validate_model_choice(model_id)
        project_row = self._project(project)
        now = utc_now()
        thread_id, job_id, decision_id = new_id("thr"), new_id("job"), new_id("rte")
        with self.store.transaction() as conn:
            conn.execute(
                "INSERT INTO threads(id, project_id, kind, synthetic, title, pinned_model, pinned_effort, pinned_manual, route_decision_id, status, "
                "created_at, updated_at, account_scope) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (thread_id, project_row["id"], ThreadKind.EVALUATION.value, int(not self.live), f"eval {run_id}", model_id,
                 reasoning_effort, 1, decision_id, "active", now, now, self.account_scope),
            )
            conn.execute(
                "INSERT INTO route_decisions(id, request_id, thread_id, route_attempt_id, role, model_id, reasoning_effort, manual, payload, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (decision_id, run_id, thread_id, new_id("route"), None, model_id, reasoning_effort, 1,
                 dumps({"evaluation_run": run_id, "note": "comparison only; not an automatic binding"}), now),
            )
            message_id = self.store.add_message(thread_id, "user", "prompt", text, provenance=f"evaluation:{run_id}", conn=conn)
            conn.execute(
                "INSERT INTO jobs(id, logical_key, thread_id, request_id, kind, state, priority, input_message_id, selected_at, user_requested, "
                "created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (job_id, f"eval:{run_id}:{thread_id}", thread_id, run_id, "evaluation", JobState.DRAFT.value, 10, message_id, now, 0, now, now),
            )
            self.store.transition_job(job_id, JobState.SELECTED, conn=conn)
        return {"thread_id": thread_id, "job_id": job_id}

    # ------------------------------------------------------------ inspection

    def threads(self, project: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT t.*, p.name AS project_name FROM threads t JOIN projects p ON p.id=t.project_id"
        params: tuple = ()
        if project:
            sql += " WHERE p.name=?"
            params = (project,)
        sql += " ORDER BY t.created_at"
        return [dict(r) for r in self.store.all(sql, params)]

    def status(self) -> dict[str, Any]:
        counts = {r["state"]: r["n"] for r in self.store.all("SELECT state, COUNT(*) AS n FROM jobs GROUP BY state")}
        waiting = [dict(r) for r in self.store.all(
            "SELECT id, thread_id, state, blocker, next_check_at FROM jobs WHERE state NOT IN ('SUCCEEDED','FAILED','CANCELLED') ORDER BY created_at"
        )]
        return {"live": self.live, "adapter": self.adapter.name, "account_scope": self.account_scope, "jobs": counts, "open_jobs": waiting}


class _Hold(Exception):
    def __init__(self, state: JobState, reason: str) -> None:
        super().__init__(reason)
        self.state = state
        self.reason = reason


def _summarise_item(item: dict[str, Any]) -> dict[str, Any]:
    kind = item.get("type")
    summary: dict[str, Any] = {"type": kind, "id": item.get("id")}
    if kind == "commandExecution":
        summary.update(command=item.get("command"), exit_code=item.get("exitCode"), status=item.get("status"))
    elif kind == "fileChange":
        summary.update(paths=[c.get("path") for c in item.get("changes", []) if isinstance(c, dict)], status=item.get("status"))
    else:
        summary.update(status=item.get("status"))
    return summary


def _git_changed_files(worktree: str) -> list[str]:
    try:
        result = subprocess.run(["git", "-C", worktree, "status", "--porcelain"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return [line[3:] for line in result.stdout.splitlines() if line.strip()]


__all__ = ["Coordinator", "HandoffResult", "OverrideRefused", "RouterUI", "SubmitResult", "StoreError"]
