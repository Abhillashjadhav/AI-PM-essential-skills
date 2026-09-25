"""Codex App Server adapter over stdio (JSON-RPC, one JSON message per line).

Evidence basis (see docs/capability-evidence.md): method and field names come
from the upstream generated JSON Schema at openai/codex commit
bd3d4d1436bb41b94fd38ba9bdd34d74524e7a9f. They are documented-but-unverified
against the owner's *installed* binary until ``doctor`` validates the pinned
installation's own generated schema.

Safety properties:

* Live sends require a valid pin (absolute executable path, version, sha256,
  schema digest) that matches the running installation. Drift blocks sends.
* The subprocess gets a minimal environment; API-key variables are never
  passed, and are never printed.
* A dedicated CODEX_HOME holds this router's profile with
  ``forced_login_method = "chatgpt"``; the effective config is validated.
* The spend decision is UNKNOWN unless a live-verified enforcement record for
  this exact pin and account is present and its per-dispatch conditions hold.
* Methods that could spend or change billing are never called.
"""

from __future__ import annotations

import hashlib
import json
import os
import queue
import random
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from ..contracts import (
    Binding,
    CreditsState,
    ModelInfo,
    SpendDecision,
    SpendStatus,
    TurnStatus,
    UsageBucket,
    UsageSnapshot,
    new_id,
    parse_utc,
    utc_now,
)
from ..store import atomic_write
from .base import (
    AccountState,
    AdapterCapabilities,
    AdapterError,
    ApprovalHandler,
    ApprovalRequest,
    DispatchUncertain,
    ModelCatalogue,
    ProviderThread,
    ProviderThreadState,
    ProviderTurnRecord,
    SubscriptionAdapter,
    TurnEvent,
    UnsupportedOperation,
)

ADAPTER_VERSION = "codex-stdio-1"
REFERENCE_SCHEMA_COMMIT = "bd3d4d1436bb41b94fd38ba9bdd34d74524e7a9f"
CLIENT_INFO = {"name": "ai_pm_model_router", "title": "AI PM Model Router", "version": "1.0.0"}

# Never called by this adapter: purchases, reset redemption, billing nudges,
# login/logout flows and config writes are the owner's business.
FORBIDDEN_METHODS = frozenset(
    {
        "account/rateLimitResetCredit/consume",
        "account/sendAddCreditsNudgeEmail",
        "account/login/start",
        "account/logout",
        "config/value/write",
        "config/batchWrite",
        "feedback/upload",
    }
)
REQUIRED_CLIENT_METHODS = (
    "initialize",
    "thread/start",
    "thread/resume",
    "thread/read",
    "turn/start",
    "turn/interrupt",
    "model/list",
    "account/read",
    "account/rateLimits/read",
    "config/read",
)
REQUIRED_NOTIFICATIONS = ("turn/started", "turn/completed", "item/agentMessage/delta", "item/completed", "error")
MONITORED_NOTIFICATIONS = ("model/rerouted", "account/rateLimits/updated", "account/updated", "warning")
REQUIRED_SERVER_REQUESTS = ("item/commandExecution/requestApproval", "item/fileChange/requestApproval")
SAFE_ENV_KEYS = ("PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "TERM", "USER", "LOGNAME", "SHELL")
SECRET_ENV_KEYS = ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL", "AZURE_OPENAI_API_KEY", "OPENAI_ORG_ID")
USAGE_CODES = {"usageLimitExceeded", "rateLimitExceeded", "sessionBudgetExceeded"}
READ_METHODS = {"account/read", "model/list", "account/rateLimits/read", "thread/read", "config/read"}


# --------------------------------------------------------------------- pinning


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def schema_digest(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(directory)).encode("utf-8") + b"\0")
        digest.update(sha256_file(path).encode("ascii") + b"\n")
    return digest.hexdigest()


def resolve_executable(explicit: str | None = None) -> Path | None:
    candidate = explicit or shutil.which("codex")
    if not candidate:
        return None
    path = Path(candidate).expanduser()
    if not path.is_absolute():
        found = shutil.which(str(path))
        if not found:
            return None
        path = Path(found)
    return path.resolve()


def launcher_details(executable: Path) -> dict[str, Any]:
    """Record interpreter/launcher details for script launchers (e.g. npm)."""
    details: dict[str, Any] = {}
    try:
        with executable.open("rb") as handle:
            head = handle.read(256)
    except OSError:
        return details
    if head.startswith(b"#!"):
        line = head.splitlines()[0][2:].decode("utf-8", "replace").strip()
        details["shebang"] = line
        interpreter = line.split()[-1] if line.split() and line.split()[0].endswith("env") else line.split()[0]
        resolved = shutil.which(interpreter) if not interpreter.startswith("/") else interpreter
        if resolved:
            details["interpreter"] = str(Path(resolved).resolve())
            try:
                details["interpreter_sha256"] = sha256_file(Path(resolved).resolve())
            except OSError:
                pass
        details["note"] = "script launcher: the underlying native binary may be selected at runtime; pin the package directory too"
    return details


def minimal_env(codex_home: Path) -> tuple[dict[str, str], list[str]]:
    env = {k: os.environ[k] for k in SAFE_ENV_KEYS if k in os.environ}
    env["CODEX_HOME"] = str(codex_home)
    dropped = sorted(k for k in SECRET_ENV_KEYS if k in os.environ)
    return env, dropped


def generate_schema(executable: Path, out_dir: Path, env: dict[str, str], timeout: float = 60) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [str(executable), "app-server", "generate-json-schema", "--out", str(out_dir)],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"schema generation failed to run: {exc}"
    if result.returncode != 0:
        return False, f"schema generation exited {result.returncode}: {result.stderr.strip()[:300]}"
    return True, "generated"


def read_version(executable: Path, env: dict[str, str]) -> str | None:
    try:
        result = subprocess.run([str(executable), "--version"], capture_output=True, text=True, timeout=20, env=env)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _methods(schema: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for variant in schema.get("oneOf", []) + schema.get("anyOf", []):
        enum = variant.get("properties", {}).get("method", {}).get("enum")
        if enum:
            found.update(enum)
    return found


def check_schema_compat(schema_dir: Path) -> tuple[list[str], list[str]]:
    """Return (problems, notes). Problems block live use; additive fields are fine."""
    problems: list[str] = []
    notes: list[str] = []

    def load(name: str) -> dict[str, Any] | None:
        for candidate in (schema_dir / name, schema_dir / "v2" / name, schema_dir / "v1" / name):
            if candidate.is_file():
                try:
                    return json.loads(candidate.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    problems.append(f"{name}: invalid JSON ({exc})")
                    return None
        return None

    client = load("ClientRequest.json")
    notifications = load("ServerNotification.json")
    server_requests = load("ServerRequest.json")
    if client is None or notifications is None or server_requests is None:
        problems.append("schema bundle lacks ClientRequest/ServerNotification/ServerRequest")
        return problems, notes
    client_methods = _methods(client)
    for method in REQUIRED_CLIENT_METHODS:
        if method not in client_methods:
            problems.append(f"required client method missing: {method}")
    note_methods = _methods(notifications)
    for method in REQUIRED_NOTIFICATIONS:
        if method not in note_methods:
            problems.append(f"required notification missing: {method}")
    for method in MONITORED_NOTIFICATIONS:
        if method not in note_methods:
            notes.append(f"optional notification absent: {method} (feature degrades; reported)")
    request_methods = _methods(server_requests)
    for method in REQUIRED_SERVER_REQUESTS:
        if method not in request_methods:
            problems.append(f"approval request missing: {method}")
    unknown_requests = sorted(request_methods - set(REQUIRED_SERVER_REQUESTS))
    if unknown_requests:
        notes.append(f"other server requests are declined or answered with an error: {unknown_requests}")

    turn_start = load("TurnStartParams.json")
    if turn_start is None:
        problems.append("TurnStartParams schema missing")
    else:
        props = turn_start.get("properties", {})
        for name in ("threadId", "input", "model"):
            if name not in props:
                problems.append(f"TurnStartParams.{name} missing")
        if "clientUserMessageId" not in props:
            notes.append("TurnStartParams.clientUserMessageId absent: crash reconciliation limited to turn ids")
    thread_start = load("ThreadStartParams.json")
    if thread_start is None or not {"model", "cwd", "sandbox"} <= set(thread_start.get("properties", {})):
        problems.append("ThreadStartParams lacks model/cwd/sandbox")
    completed = load("TurnCompletedNotification.json")
    if completed is not None:
        status = completed.get("definitions", {}).get("TurnStatus", {}).get("enum", [])
        if not {"completed", "failed", "interrupted"} <= set(status):
            problems.append(f"TurnStatus enum lacks required values: {status}")
    else:
        problems.append("TurnCompletedNotification schema missing")
    account = load("GetAccountResponse.json")
    if account is None or "chatgpt" not in json.dumps(account):
        problems.append("GetAccountResponse lacks the chatgpt account type")
    limits = load("GetAccountRateLimitsResponse.json")
    if limits is None or "rateLimits" not in limits.get("properties", {}):
        problems.append("GetAccountRateLimitsResponse lacks rateLimits")
    else:
        for optional in ("ordinaryUsageAllowed", "rateLimitsByLimitId"):
            if optional not in limits.get("properties", {}):
                notes.append(f"rate-limit field absent: {optional}")
    return problems, notes


@dataclass
class PinManifest:
    executable: str
    version: str | None
    sha256: str
    schema_digest: str
    launcher: dict[str, Any]
    compat_problems: list[str]
    compat_notes: list[str]
    approved_by: str | None
    approved_at: str | None
    adapter_version: str = ADAPTER_VERSION
    enforcement: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def load(cls, path: Path) -> "PinManifest | None":
        if not path.is_file():
            return None
        return cls(**json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        atomic_write(path, json.dumps(self.to_dict(), indent=2, sort_keys=True))

    @property
    def digest(self) -> str:
        return hashlib.sha256(f"{self.executable}|{self.version}|{self.sha256}|{self.schema_digest}".encode()).hexdigest()


def inspect_installation(executable: Path, codex_home: Path) -> tuple[PinManifest | None, list[str]]:
    """Measure the installed CLI: version, checksum, launcher, schema digest."""
    problems: list[str] = []
    env, _ = minimal_env(codex_home)
    version = read_version(executable, env)
    if version is None:
        problems.append("could not read `codex --version`")
    with tempfile.TemporaryDirectory(prefix="router-schema-") as tmp:
        ok, message = generate_schema(executable, Path(tmp), env)
        if not ok:
            problems.append(message)
            return None, problems
        compat_problems, compat_notes = check_schema_compat(Path(tmp))
        digest = schema_digest(Path(tmp))
    manifest = PinManifest(
        executable=str(executable),
        version=version,
        sha256=sha256_file(executable),
        schema_digest=digest,
        launcher=launcher_details(executable),
        compat_problems=compat_problems,
        compat_notes=compat_notes,
        approved_by=None,
        approved_at=None,
    )
    return manifest, problems


def pin_status(saved: PinManifest | None, current: PinManifest | None) -> tuple[str, list[str]]:
    if saved is None:
        return "unpinned", ["no approved adapter pin; run `router.py adapter pin` after reviewing doctor output"]
    if current is None:
        return "unverifiable", ["the installed CLI could not be inspected"]
    drift = []
    for name in ("executable", "version", "sha256", "schema_digest"):
        if getattr(saved, name) != getattr(current, name):
            drift.append(f"{name} changed")
    if drift:
        return "drift", drift + ["new sends are blocked until the adapter is re-validated and re-pinned"]
    if saved.compat_problems:
        return "incompatible", saved.compat_problems
    if not saved.approved_by:
        return "unapproved", ["pin exists but was not approved by the owner"]
    return "valid", []


# -------------------------------------------------------------------- client


class JsonRpcProcess:
    """Line-delimited JSON-RPC peer over a subprocess's stdio."""

    def __init__(self, argv: list[str], env: dict[str, str], stderr_path: Path, *, max_queue: int = 10_000) -> None:
        self._stderr = stderr_path.open("ab")
        os.chmod(stderr_path, 0o600)
        try:
            self.proc = subprocess.Popen(
                argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr, env=env, bufsize=0
            )
        except OSError as exc:
            self._stderr.close()
            raise AdapterError(f"could not start the App Server: {exc}", executed="no") from exc
        self._next_id = 0
        self._pending: dict[Any, queue.Queue] = {}
        self._lock = threading.Lock()
        self.inbox: "queue.Queue[dict[str, Any]]" = queue.Queue(maxsize=max_queue)  # bounded: backpressure
        self.malformed: list[str] = []
        self.closed = threading.Event()
        self._reader = threading.Thread(target=self._read, name="codex-reader", daemon=True)
        self._reader.start()

    def _read(self) -> None:
        assert self.proc.stdout is not None
        for raw in iter(self.proc.stdout.readline, b""):
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                self.malformed.append(line[:200])
                continue
            if not isinstance(message, dict):
                self.malformed.append(line[:200])
                continue
            if "id" in message and "method" not in message:
                with self._lock:
                    waiter = self._pending.pop(message["id"], None)
                if waiter is not None:
                    waiter.put(message)
                else:
                    self.malformed.append(f"response for unknown id {message.get('id')!r}")
            else:
                self.inbox.put(message)
        self.closed.set()
        self.inbox.put({"method": "__closed__"})

    def send(self, message: dict[str, Any]) -> None:
        if self.closed.is_set() or self.proc.stdin is None:
            raise AdapterError("App Server connection is closed", executed="no")
        data = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
        try:
            self.proc.stdin.write(data)
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise DispatchUncertain(f"write to the App Server failed: {exc}") from exc

    def request(self, method: str, params: dict[str, Any] | None, timeout: float, *, before_send: Callable[[], None] | None = None) -> Any:
        if method in FORBIDDEN_METHODS:
            raise UnsupportedOperation(f"{method} is never called by the router")
        with self._lock:
            self._next_id += 1
            request_id = self._next_id
            waiter: queue.Queue = queue.Queue(maxsize=1)
            self._pending[request_id] = waiter
        message = {"id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        if before_send:
            before_send()
        try:
            self.send(message)
        except AdapterError:
            with self._lock:
                self._pending.pop(request_id, None)
            raise
        try:
            response = waiter.get(timeout=timeout)
        except queue.Empty as exc:
            with self._lock:
                self._pending.pop(request_id, None)
            raise DispatchUncertain(f"no response to {method} within {timeout:g}s") from exc
        if "error" in response:
            error = response["error"] or {}
            raise AdapterError(
                f"{method} failed: {error.get('message', 'unknown error')}",
                executed="no",
                code=_error_code(error),
            )
        return response.get("result")

    def respond(self, request_id: Any, result: Any = None, error: dict[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"id": request_id}
        if error is not None:
            message["error"] = error
        else:
            message["result"] = result
        self.send(message)

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"method": method}
        if params is not None:
            message["params"] = params
        self.send(message)

    def close(self, timeout: float = 5.0) -> int | None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except OSError:
            pass
        try:
            code = self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            try:
                code = self.proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                code = self.proc.wait()
        if self.proc.stdout:
            self.proc.stdout.close()
        self._reader.join(timeout=timeout)
        self._stderr.close()
        return code


def _error_code(error: dict[str, Any]) -> str | None:
    data = error.get("data")
    if isinstance(data, dict):
        info = data.get("codexErrorInfo")
        if isinstance(info, str):
            return info
        if isinstance(info, dict) and info:
            return next(iter(info))
    return None


def _epoch_to_iso(value: Any) -> str | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number > 1e12:  # INFERRED: milliseconds if implausibly large for seconds
        number /= 1000.0
    return datetime.fromtimestamp(number, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def account_fingerprint(auth_type: str | None, email: str | None, account_id: str | None) -> str | None:
    if auth_type is None:
        return None
    basis = f"{auth_type}|{account_id or ''}|{(email or '').strip().lower()}"
    return "acct_" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]


def redact(value: Any) -> Any:
    """Remove e-mail addresses and anything token-like from raw payloads."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            lowered = key.lower()
            if lowered in {"email", "token", "accesstoken", "refreshtoken", "idtoken", "apikey", "authorization"}:
                out[key] = "[redacted]"
            else:
                out[key] = redact(item)
        return out
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


# ------------------------------------------------------------------- adapter


@dataclass
class CodexConfig:
    data_dir: Path
    executable: str | None = None
    codex_home: Path | None = None
    request_timeout: float = 30.0
    turn_idle_timeout: float = 900.0
    enforce_pin: bool = True
    argv_override: list[str] | None = None  # tests: a fake App Server script

    @property
    def home(self) -> Path:
        return self.codex_home or (self.data_dir / "codex-home")

    @property
    def pin_path(self) -> Path:
        return self.data_dir / "adapter-pin.json"


class CodexStdioAdapter(SubscriptionAdapter):
    name = "codex-app-server"

    def __init__(self, config: CodexConfig) -> None:
        self.config = config
        self.rpc: JsonRpcProcess | None = None
        self.pin_state = "unchecked"
        self.pin_problems: list[str] = []
        self.dropped_env: list[str] = []
        self._account: AccountState | None = None
        self._thread_listeners: dict[str, "queue.Queue[dict[str, Any]]"] = {}
        self._pending_notifications: list[dict[str, Any]] = []
        self._last_usage_raw: dict[str, Any] | None = None
        self.connection_generation = 0
        self.send_client_message_id = True
        self.capabilities: AdapterCapabilities | None = None

    # -- process ---------------------------------------------------------------

    def _ensure_profile(self) -> None:
        home = self.config.home
        home.mkdir(parents=True, exist_ok=True)
        os.chmod(home, 0o700)
        config_path = home / "config.toml"
        if not config_path.exists():
            atomic_write(
                config_path,
                "# Dedicated profile for AI PM Model Router. Created by the router; safe to inspect.\n"
                'forced_login_method = "chatgpt"\n',
            )

    def _argv(self) -> list[str]:
        if self.config.argv_override:
            return list(self.config.argv_override)
        executable = resolve_executable(self.config.executable)
        if executable is None:
            raise AdapterError("Codex CLI not found; install it or pass --codex-path", executed="no", code="not_installed")
        return [str(executable), "app-server"]

    def _check_pin(self) -> None:
        if not self.config.enforce_pin:
            self.pin_state, self.pin_problems = "not_enforced", ["pin enforcement disabled (test harness only)"]
            return
        executable = resolve_executable(self.config.executable)
        saved = PinManifest.load(self.config.pin_path)
        current = None
        if executable is not None:
            current, problems = inspect_installation(executable, self.config.home)
            self.pin_problems = problems
        self.pin_state, reasons = pin_status(saved, current)
        self.pin_problems = self.pin_problems + reasons

    def _connect(self) -> JsonRpcProcess:
        if self.rpc is not None and not self.rpc.closed.is_set():
            return self.rpc
        self._reset()  # reap an exited App Server before starting a new one
        self._verify_binary_unchanged()
        self._ensure_profile()
        env, dropped = minimal_env(self.config.home)
        self.dropped_env = dropped
        stderr_path = self.config.data_dir / "logs" / "app-server.stderr.log"
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(stderr_path.parent, 0o700)
        self.rpc = JsonRpcProcess(self._argv(), env, stderr_path)
        self.connection_generation += 1
        result = self.rpc.request("initialize", {"clientInfo": CLIENT_INFO}, self.config.request_timeout)
        self.rpc.notify("initialized")
        self._init_result = redact(result or {})
        return self.rpc

    def _verify_binary_unchanged(self) -> None:
        """Every (re)spawn re-checks the executable against the approved pin, so a
        binary replaced after startup can never inherit a valid pin state."""
        if not self.config.enforce_pin or self.pin_state != "valid":
            return
        saved = PinManifest.load(self.config.pin_path)
        executable = resolve_executable(self.config.executable)
        if saved is None or executable is None or str(executable) != saved.executable or sha256_file(executable) != saved.sha256:
            self.pin_state = "drift"
            self.pin_problems = ["the Codex executable changed since it was pinned; new sends are blocked until re-validated"]

    def _read_request(self, method: str, params: dict[str, Any] | None) -> Any:
        """Idempotent reads: bounded exponential backoff with jitter."""
        delay = 0.2
        last: Exception | None = None
        for attempt in range(3):
            try:
                return self._connect().request(method, params, self.config.request_timeout)
            except DispatchUncertain as exc:  # transport trouble on a read is safe to retry
                last = exc
                self._reset()
            except AdapterError as exc:
                if exc.code == "not_installed":
                    raise
                last = exc
                if attempt == 2:
                    break
            time.sleep(delay + random.uniform(0, delay))
            delay *= 2
        assert last is not None
        raise AdapterError(f"{method} failed after retries: {last}", executed="no")

    def _reset(self) -> None:
        if self.rpc is not None:
            try:
                self.rpc.close(timeout=1)
            except Exception:
                pass
        self.rpc = None

    # -- interface ---------------------------------------------------------------

    def initialise(self) -> AdapterCapabilities:
        self._check_pin()
        saved = PinManifest.load(self.config.pin_path)
        if saved is not None and any("clientUserMessageId absent" in note for note in saved.compat_notes):
            self.send_client_message_id = False  # never send a field the pinned schema lacks
        operations = {
            "read_account": "unverified",
            "list_models": "unverified",
            "read_usage": "unverified",
            "create_thread": "unverified",
            "read_thread": "unverified",
            "resume_thread": "unverified",
            "start_turn": "unverified" if self.pin_state in {"valid", "not_enforced"} else "blocked:" + self.pin_state,
            "interrupt_turn": "unverified",
        }
        self.capabilities = AdapterCapabilities(
            adapter=self.name,
            adapter_version=ADAPTER_VERSION,
            protocol=f"codex app-server stdio JSONL (reference schema {REFERENCE_SCHEMA_COMMIT[:12]})",
            synthetic=False,
            operations=operations,
            tools={"edit": "unverified", "shell": "unverified", "web_search": "unverified"},
            pin={"state": self.pin_state, "problems": self.pin_problems},
            notes=[f"API-key variables present in the environment and NOT passed: {self.dropped_env}"] if self.dropped_env else [],
        )
        return self.capabilities

    def read_account(self) -> AccountState:
        observed = utc_now()
        problems: list[str] = []
        try:
            result = self._read_request("account/read", {"refreshToken": False}) or {}
        except AdapterError as exc:
            return AccountState(False, None, None, None, False, [str(exc)], False, observed)
        account = result.get("account")
        auth_type = account.get("type") if isinstance(account, dict) else None
        plan = account.get("planType") if isinstance(account, dict) else None
        email = account.get("email") if isinstance(account, dict) else None
        try:
            config = (self._read_request("config/read", {"includeLayers": False}) or {}).get("config", {})
        except AdapterError as exc:
            config = {}
            problems.append(f"effective config could not be read: {exc}")
        forced = config.get("forced_login_method")
        if forced != "chatgpt":
            problems.append(f"forced_login_method is {forced!r}, expected 'chatgpt'")
        provider = config.get("model_provider")
        if provider not in (None, "openai"):
            problems.append(f"model_provider override {provider!r} is not allowed")
        scope = account_fingerprint(auth_type, email, None)
        self._account = AccountState(
            authenticated=auth_type is not None,
            auth_mode=auth_type,
            account_scope=scope,
            plan_type=plan,
            config_ok=not problems,
            config_problems=problems,
            synthetic=False,
            observed_at=observed,
            raw_redacted=redact(result),
        )
        return self._account

    def list_models(self) -> ModelCatalogue:
        models: list[ModelInfo] = []
        cursor = None
        complete = True
        for _ in range(20):
            params: dict[str, Any] = {"includeHidden": False}
            if cursor:
                params["cursor"] = cursor
            result = self._read_request("model/list", params) or {}
            for raw in result.get("data", []):
                efforts = [
                    e.get("reasoningEffort") for e in raw.get("supportedReasoningEfforts", []) if isinstance(e, dict) and e.get("reasoningEffort")
                ]
                default = raw.get("defaultReasoningEffort")
                models.append(
                    ModelInfo(
                        model_id=raw.get("model") or raw.get("id"),
                        display_name=raw.get("displayName") or raw.get("model") or raw.get("id"),
                        provider=self.name,
                        reasoning_efforts=efforts,
                        default_effort=default if (not efforts or default in efforts) else None,
                        input_modalities=list(raw.get("inputModalities") or []),
                        hidden=bool(raw.get("hidden")),
                        is_default=bool(raw.get("isDefault")),
                        upgrade=raw.get("upgrade"),
                        raw_ref=raw.get("id"),
                    )
                )
            cursor = result.get("nextCursor")
            if not cursor:
                break
        else:
            complete = False
        return ModelCatalogue(models=models, observed_at=utc_now(), synthetic=False, complete=complete)

    def read_usage(self) -> UsageSnapshot:
        result = self._read_request("account/rateLimits/read", None) or {}
        self._last_usage_raw = redact(result)
        return parse_rate_limits(result, account_scope=self._account.account_scope if self._account else None)

    def check_spend_boundary(self, account: AccountState, usage: UsageSnapshot) -> SpendDecision:
        return decide_spend(account, usage, pin_state=self.pin_state, manifest=PinManifest.load(self.config.pin_path))

    def create_thread(self, binding: Binding, *, developer_instructions: str | None, workspace: str | None, sandbox: str) -> ProviderThread:
        self._require_sendable()
        if sandbox not in {"read-only", "workspace-write"}:
            raise AdapterError(f"sandbox {sandbox!r} is not permitted", executed="no")
        params = {
            "model": binding.model_id,
            "cwd": workspace,
            "sandbox": sandbox,
            "approvalPolicy": "on-request",
            "developerInstructions": developer_instructions,
            "ephemeral": False,
        }
        result = self._connect().request("thread/start", params, self.config.request_timeout) or {}
        thread = result.get("thread") or {}
        if not thread.get("id"):
            raise DispatchUncertain("thread/start response had no thread id")
        return ProviderThread(
            provider_thread_id=thread["id"],
            model_id=result.get("model") or thread.get("model"),
            reasoning_effort=result.get("reasoningEffort"),
            raw_redacted=redact({k: v for k, v in result.items() if k != "thread"}),
        )

    def read_thread(self, provider_thread_id: str) -> ProviderThreadState:
        result = self._read_request("thread/read", {"threadId": provider_thread_id, "includeTurns": True}) or {}
        thread = result.get("thread") or {}
        turns = []
        for turn in thread.get("turns") or []:
            client_id = None
            text_parts: list[str] = []
            for item in turn.get("items") or []:
                if item.get("type") == "userMessage" and item.get("clientId"):
                    client_id = item.get("clientId")
                if item.get("type") == "agentMessage" and item.get("text"):
                    text_parts.append(item["text"])
            try:
                status = TurnStatus(turn.get("status"))
            except ValueError:
                status = TurnStatus.UNKNOWN
            error = turn.get("error")
            turns.append(
                ProviderTurnRecord(
                    provider_turn_id=turn.get("id"),
                    status=status,
                    client_message_id=client_id,
                    text="\n".join(text_parts) or None,
                    error=error.get("message") if isinstance(error, dict) else None,
                )
            )
        status = thread.get("status")
        return ProviderThreadState(
            provider_thread_id=provider_thread_id,
            model_id=thread.get("model"),
            status=status.get("type") if isinstance(status, dict) else str(status),
            turns=turns,
        )

    def resume_thread(self, provider_thread_id: str, expected: Binding, *, workspace: str | None, sandbox: str) -> ProviderThread:
        self._require_sendable()
        params = {
            "threadId": provider_thread_id,
            "model": expected.model_id,
            "cwd": workspace,
            "sandbox": sandbox,
            "approvalPolicy": "on-request",
            "excludeTurns": True,
        }
        result = self._connect().request("thread/resume", params, self.config.request_timeout) or {}
        return ProviderThread(
            provider_thread_id=provider_thread_id,
            model_id=result.get("model") or (result.get("thread") or {}).get("model"),
            reasoning_effort=result.get("reasoningEffort"),
        )

    def _require_sendable(self) -> None:
        if self.pin_state not in {"valid", "not_enforced"}:
            raise AdapterError(
                f"adapter pin is {self.pin_state}: " + "; ".join(self.pin_problems or ["not validated"]),
                executed="no",
                code="pin",
            )

    def start_turn(
        self,
        provider_thread_id: str,
        text: str,
        dispatch_id: str,
        *,
        binding: Binding,
        approval_handler: ApprovalHandler,
        on_sent: Callable[[], None] | None = None,
    ) -> Iterator[TurnEvent]:
        self._require_sendable()
        rpc = self._connect()
        self._drain_stale(rpc)
        params: dict[str, Any] = {
            "threadId": provider_thread_id,
            "input": [{"type": "text", "text": text}],
            "model": binding.model_id,
        }
        if self.send_client_message_id:
            params["clientUserMessageId"] = dispatch_id
        if binding.reasoning_effort:
            params["effort"] = binding.reasoning_effort
        result = rpc.request("turn/start", params, self.config.request_timeout, before_send=on_sent) or {}
        turn = result.get("turn") or {}
        turn_id = turn.get("id")
        if not turn_id:
            raise DispatchUncertain("turn/start returned no turn id")
        return self._events(rpc, provider_thread_id, turn_id, approval_handler)

    def _drain_stale(self, rpc: JsonRpcProcess) -> int:
        """Drop notifications left over from earlier or abandoned turns so the
        bounded inbox never fills; refuse any stale provider request."""
        dropped = 0
        while True:
            try:
                message = rpc.inbox.get_nowait()
            except queue.Empty:
                return dropped
            if message.get("method") == "__closed__":
                rpc.inbox.put(message)
                return dropped
            if "id" in message:
                rpc.respond(message["id"], error={"code": -32000, "message": "request belongs to a finished turn"})
            dropped += 1

    def _events(self, rpc: JsonRpcProcess, thread_id: str, turn_id: str, approval_handler: ApprovalHandler) -> Iterator[TurnEvent]:
        yield TurnEvent(kind="acknowledged", provider_turn_id=turn_id)
        deadline = time.monotonic() + self.config.turn_idle_timeout
        while True:
            try:
                message = rpc.inbox.get(timeout=max(0.1, deadline - time.monotonic()))
            except queue.Empty:
                raise DispatchUncertain(f"no provider events for {self.config.turn_idle_timeout:g}s")
            deadline = time.monotonic() + self.config.turn_idle_timeout
            method = message.get("method")
            params = message.get("params") or {}
            if method == "__closed__":
                raise DispatchUncertain("the App Server exited during the turn")
            if "id" in message:
                yield from self._server_request(rpc, message, approval_handler)
                continue
            if params.get("threadId") not in (None, thread_id):
                continue
            if params.get("turnId") not in (None, turn_id) and method not in {"turn/completed"}:
                continue
            event = translate_notification(method, params, turn_id)
            if event is None:
                continue
            yield event
            if event.kind == "completed":
                return

    def _server_request(self, rpc: JsonRpcProcess, message: dict[str, Any], approval_handler: ApprovalHandler) -> Iterator[TurnEvent]:
        method = message.get("method")
        params = message.get("params") or {}
        request_id = message["id"]
        if method == "item/commandExecution/requestApproval":
            request = ApprovalRequest(
                kind="command",
                summary=params.get("reason") or "command approval",
                command=params.get("command"),
                cwd=params.get("cwd"),
                paths=[],
                raw_method=method,
            )
        elif method == "item/fileChange/requestApproval":
            request = ApprovalRequest(
                kind="file_change",
                summary=params.get("reason") or "file change approval",
                command=None,
                cwd=None,
                paths=[params["grantRoot"]] if params.get("grantRoot") else [],
                raw_method=method,
            )
        else:
            # Unsupported provider-initiated requests are refused visibly.
            rpc.respond(request_id, error={"code": -32601, "message": f"{method} is not supported by this client"})
            yield TurnEvent(kind="warning", text=f"declined unsupported provider request {method}", fatal=False)
            return
        decision = approval_handler(request)
        if decision not in {"accept", "decline", "cancel"}:
            decision = "decline"
        rpc.respond(request_id, {"decision": decision})
        yield TurnEvent(kind="approval", text=request.summary, data={"decision": decision, "command": request.command, "paths": request.paths, "method": method})

    def interrupt_turn(self, provider_thread_id: str, provider_turn_id: str) -> dict[str, Any]:
        try:
            self._connect().request("turn/interrupt", {"threadId": provider_thread_id, "turnId": provider_turn_id}, self.config.request_timeout)
        except AdapterError as exc:
            return {"interrupted": False, "error": str(exc)}
        return {"interrupted": True, "note": "interrupt requested; final status arrives as turn/completed"}

    def close(self) -> dict[str, Any]:
        if self.rpc is None:
            return {"closed": True, "exit_code": None}
        code = self.rpc.close()
        self.rpc = None
        return {"closed": True, "exit_code": code}


# ------------------------------------------------------------ translation


def translate_notification(method: str | None, params: dict[str, Any], turn_id: str) -> TurnEvent | None:
    if method == "item/agentMessage/delta":
        return TurnEvent(kind="delta", text=params.get("delta", ""), provider_turn_id=turn_id)
    if method == "error":
        error = params.get("error") or {}
        info = error.get("codexErrorInfo")
        code = info if isinstance(info, str) else (next(iter(info)) if isinstance(info, dict) and info else None)
        will_retry = bool(params.get("willRetry"))
        return TurnEvent(
            kind="error",
            error=error.get("message", "provider error"),
            error_code=code,
            will_retry=will_retry,
            fatal=not will_retry,
            provider_turn_id=turn_id,
        )
    if method in {"warning", "configWarning", "deprecationNotice", "guardianWarning"}:
        return TurnEvent(kind="warning", text=params.get("message") or method, fatal=False)
    if method == "model/rerouted":
        return TurnEvent(kind="rerouted", from_model=params.get("fromModel"), to_model=params.get("toModel"), provider_turn_id=turn_id, data={"reason": params.get("reason")})
    if method == "account/rateLimits/updated":
        return TurnEvent(kind="usage_changed", data={"rateLimits": redact(params.get("rateLimits"))})
    if method == "account/updated":
        return TurnEvent(kind="account_changed", data=redact(params))
    if method == "item/completed":
        return TurnEvent(kind="item", item=params.get("item"), provider_turn_id=turn_id)
    if method == "turn/completed":
        turn = params.get("turn") or {}
        if turn.get("id") not in (None, turn_id):
            return None
        try:
            status = TurnStatus(turn.get("status"))
        except ValueError:
            status = TurnStatus.UNKNOWN
        error = turn.get("error")
        return TurnEvent(
            kind="completed",
            status=status,
            provider_turn_id=turn_id,
            error=error.get("message") if isinstance(error, dict) else None,
        )
    return None


def parse_rate_limits(result: dict[str, Any], *, account_scope: str | None) -> UsageSnapshot:
    snapshots: dict[str, dict[str, Any]] = {}
    by_id = result.get("rateLimitsByLimitId")
    if isinstance(by_id, dict) and by_id:
        snapshots.update({str(k): v for k, v in by_id.items() if isinstance(v, dict)})
    elif isinstance(result.get("rateLimits"), dict):
        single = result["rateLimits"]
        snapshots[str(single.get("limitId") or "default")] = single
    buckets: list[UsageBucket] = []
    plan = None
    credits_raw = None
    spend_control = None
    for limit_id, snapshot in snapshots.items():
        plan = plan or snapshot.get("planType")
        credits_raw = credits_raw or snapshot.get("credits")
        if snapshot.get("spendControlReached") is not None:
            spend_control = bool(spend_control) or bool(snapshot.get("spendControlReached"))
        for window_name in ("primary", "secondary"):
            window = snapshot.get(window_name)
            if not isinstance(window, dict):
                continue
            buckets.append(
                UsageBucket(
                    limit_id=f"{limit_id}:{window_name}",
                    label=snapshot.get("limitName"),
                    used_percent=float(window["usedPercent"]) if window.get("usedPercent") is not None else None,
                    window_minutes=window.get("windowDurationMins"),
                    resets_at=_epoch_to_iso(window.get("resetsAt")),
                    applicable_models=[snapshot["normalModelSlug"]] if snapshot.get("normalModelSlug") else None,
                    reached_type=snapshot.get("rateLimitReachedType"),
                )
            )
    if isinstance(credits_raw, dict):
        credits = CreditsState(
            has_credits=credits_raw.get("hasCredits"),
            unlimited=credits_raw.get("unlimited"),
            balance=credits_raw.get("balance"),
            reported=True,
        )
    else:
        credits = CreditsState(has_credits=None, unlimited=None, balance=None, reported=False)
    resets = result.get("rateLimitResetCredits")
    return UsageSnapshot(
        id=new_id("use"),
        account_scope=account_scope,
        plan_type=plan,
        schema_version=f"app-server-v2@{REFERENCE_SCHEMA_COMMIT[:12]}",
        buckets=buckets,
        credits=credits,
        ordinary_usage_allowed=result.get("ordinaryUsageAllowed"),
        spend_control_reached=spend_control,
        reset_offer_available=resets.get("availableCount") if isinstance(resets, dict) else None,
        observed_at=utc_now(),
        source="account/rateLimits/read",
        synthetic=False,
    )


MISSING_ENFORCEMENT = (
    "no documented provider control that prevents purchased-credit use on the Codex App Server path "
    "has been verified for this pinned installation and account"
)


def decide_spend(account: AccountState, usage: UsageSnapshot, *, pin_state: str, manifest: PinManifest | None) -> SpendDecision:
    """ALLOWED_INCLUDED_ONLY only with live, pin-bound, account-bound enforcement
    evidence whose per-dispatch conditions hold right now. Otherwise UNKNOWN or
    BLOCKED, with the supporting observations listed."""
    now = utc_now()
    supporting = [
        {"source": "live", "field": "ordinaryUsageAllowed", "value": usage.ordinary_usage_allowed, "status": "supporting"},
        {"source": "live", "field": "credits", "value": usage.credits.describe(), "status": "supporting"},
        {"source": "live", "field": "spendControlReached", "value": usage.spend_control_reached, "status": "supporting"},
    ]
    if account.auth_mode != "chatgpt":
        return SpendDecision(SpendStatus.BLOCKED, ["not a ChatGPT-authenticated account"], supporting, account.account_scope, now, False)
    if usage.spend_control_reached:
        return SpendDecision(SpendStatus.BLOCKED, ["provider reports a spend control has been reached"], supporting, account.account_scope, now, False)
    if usage.ordinary_usage_allowed is False:
        return SpendDecision(SpendStatus.BLOCKED, ["included usage is not allowed right now; a send could draw on purchased credits"], supporting, account.account_scope, now, False)
    if pin_state not in {"valid"}:
        return SpendDecision(
            SpendStatus.UNKNOWN, [f"adapter pin is {pin_state}"], supporting, account.account_scope, now, False,
            missing=[MISSING_ENFORCEMENT],
        )
    if manifest is None or not manifest.enforcement:
        return SpendDecision(SpendStatus.UNKNOWN, ["spend boundary not enforced by any verified control"], supporting, account.account_scope, now, False, missing=[MISSING_ENFORCEMENT])
    rejected: list[str] = []
    for record in manifest.enforcement:
        why = _enforcement_rejection(record, account, usage, manifest)
        if why is None:
            evidence = supporting + [{"source": "live", "control": record.get("control_type"), "status": "enforced", "documentation": record.get("documentation")}]
            return SpendDecision(SpendStatus.ALLOWED_INCLUDED_ONLY, [], evidence, account.account_scope, now, False)
        rejected.append(why)
    return SpendDecision(SpendStatus.UNKNOWN, ["enforcement evidence rejected: " + "; ".join(rejected)], supporting, account.account_scope, now, False, missing=[MISSING_ENFORCEMENT])


def _enforcement_rejection(record: dict[str, Any], account: AccountState, usage: UsageSnapshot, manifest: PinManifest) -> str | None:
    if record.get("source") != "live":
        return f"evidence source {record.get('source')!r} is not live observation"
    if record.get("status") != "enforced":
        return "evidence is supporting only"
    if not record.get("documentation"):
        return "no current documentation reference"
    if record.get("pin_digest") != manifest.digest:
        return "evidence was recorded for a different adapter pin"
    if record.get("account_scope") != account.account_scope:
        return "evidence belongs to another account"
    expires = record.get("expires_at")
    if not expires or parse_utc(expires) <= parse_utc(utc_now()):
        return "evidence expired or has no expiry"
    for field_name, expected in (record.get("requires") or {}).items():
        actual = _usage_field(usage, field_name)
        if actual != expected:
            return f"condition {field_name}={expected!r} not met (observed {actual!r})"
    if not record.get("requires"):
        return "evidence states no per-dispatch observable condition"
    return None


def _usage_field(usage: UsageSnapshot, name: str) -> Any:
    mapping = {
        "ordinaryUsageAllowed": usage.ordinary_usage_allowed,
        "credits.hasCredits": usage.credits.has_credits,
        "credits.unlimited": usage.credits.unlimited,
        "credits.balance": usage.credits.balance,
        "spendControlReached": usage.spend_control_reached,
    }
    return mapping.get(name, "__unknown_field__")
