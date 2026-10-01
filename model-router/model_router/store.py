"""SQLite persistence: migrations, transactions, blobs, events, leases.

Private data (conversations, résumés, usage responses, transcripts) lives in the
user data directory, never in the repository. Files are created with 0600 and
directories with 0700; no encryption at rest is claimed beyond host protections.
"""

from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Iterator

from .contracts import (
    EVENT_SCHEMA_VERSION,
    ContractError,
    JobState,
    check_transition,
    new_id,
    sha256_text,
    utc_now,
)

APP_DIR_NAME = "AI-PM-Model-Router"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
DB_NAME = "router.sqlite3"


class StoreError(RuntimeError):
    pass


class StaleState(StoreError):
    """A compare-and-swap update found a different current state."""


def default_data_dir() -> Path:
    override = os.environ.get("MODEL_ROUTER_DATA_DIR")
    if override:
        return Path(override).expanduser()
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / APP_DIR_NAME
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg).expanduser() if xdg else home / ".local" / "share"
    return base / APP_DIR_NAME


def ensure_private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def atomic_write(path: Path, data: bytes | str, mode: int = 0o600) -> None:
    """Write via temp file + fsync + rename so readers never see a partial file."""
    payload = data.encode("utf-8") if isinstance(data, str) else data
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def migration_files() -> list[tuple[int, Path]]:
    found = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        number = int(path.name.split("_", 1)[0])
        found.append((number, path))
    return found


class Store:
    def __init__(self, data_dir: Path | str | None = None, *, clock=time.time) -> None:
        self.data_dir = ensure_private_dir(Path(data_dir) if data_dir else default_data_dir())
        self.blob_dir = ensure_private_dir(self.data_dir / "blobs")
        self.backup_dir = ensure_private_dir(self.data_dir / "backups")
        self.db_path = self.data_dir / DB_NAME
        self._clock = clock
        self._lock = threading.RLock()
        new_file = not self.db_path.exists()
        self.conn = sqlite3.connect(str(self.db_path), isolation_level=None, check_same_thread=False, timeout=10)
        if new_file:
            os.chmod(self.db_path, 0o600)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA busy_timeout = 10000")
        self.migrate()

    # -- lifecycle -----------------------------------------------------------

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    def schema_version(self) -> int:
        exists = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='meta'"
        ).fetchone()
        if not exists:
            return 0
        row = self.conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        return int(row["value"]) if row else 0

    def migrate(self) -> list[int]:
        applied: list[int] = []
        current = self.schema_version()
        pending = [(n, p) for n, p in migration_files() if n > current]
        if not pending:
            return applied
        if current > 0:
            self.backup(f"pre-migration-{current}-to-{pending[-1][0]}")
        for number, path in pending:
            sql = path.read_text(encoding="utf-8")
            try:
                self.conn.execute("BEGIN IMMEDIATE")
                for statement in _split_sql(sql):
                    self.conn.execute(statement)
                self.conn.execute(
                    "INSERT INTO meta(key, value) VALUES('schema_version', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (str(number),),
                )
                self.conn.execute("COMMIT")
            except Exception as exc:
                self.conn.execute("ROLLBACK")
                raise StoreError(
                    f"migration {path.name} failed; previous data retained (backup in {self.backup_dir})"
                ) from exc
            applied.append(number)
        return applied

    def backup(self, label: str) -> Path:
        target = self.backup_dir / f"{label}-{int(self._clock())}.sqlite3"
        dest = sqlite3.connect(str(target))
        try:
            self.conn.backup(dest)
        finally:
            dest.close()
        os.chmod(target, 0o600)
        return target

    def integrity_check(self) -> list[str]:
        problems = [row[0] for row in self.conn.execute("PRAGMA integrity_check") if row[0] != "ok"]
        for row in self.conn.execute(
            "SELECT id, blob_ref, content_hash FROM messages WHERE blob_ref IS NOT NULL"
        ):
            try:
                self.read_blob(row["blob_ref"])
            except StoreError as exc:
                problems.append(f"message {row['id']}: {exc}")
        return problems

    @contextlib.contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                yield self.conn
            except BaseException:
                self.conn.execute("ROLLBACK")
                raise
            else:
                self.conn.execute("COMMIT")

    # -- generic helpers -----------------------------------------------------

    def one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        with self._lock:
            return self.conn.execute(sql, params).fetchone()

    def all(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return list(self.conn.execute(sql, params).fetchall())

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            return self.conn.execute(sql, params)

    # -- blobs ---------------------------------------------------------------

    def write_blob(self, data: bytes | str) -> str:
        payload = data.encode("utf-8") if isinstance(data, str) else data
        import hashlib

        digest = hashlib.sha256(payload).hexdigest()
        path = self.blob_dir / digest[:2] / digest
        if not path.exists():
            ensure_private_dir(path.parent)
            atomic_write(path, payload)
        return digest

    def read_blob(self, ref: str) -> bytes:
        import hashlib

        path = self.blob_dir / ref[:2] / ref
        if not path.exists():
            raise StoreError(f"missing blob {ref}")
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != ref:
            raise StoreError(f"blob {ref} failed its integrity check")
        return payload

    def read_blob_text(self, ref: str) -> str:
        return self.read_blob(ref).decode("utf-8")

    # -- events --------------------------------------------------------------

    def event(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        thread_id: str | None = None,
        job_id: str | None = None,
        conn: sqlite3.Connection | None = None,
    ) -> int:
        target = conn or self.conn
        with self._lock:
            cursor = target.execute(
                "INSERT INTO events(schema_version, type, thread_id, job_id, payload, at) VALUES (?,?,?,?,?,?)",
                (EVENT_SCHEMA_VERSION, event_type, thread_id, job_id, json.dumps(payload or {}, sort_keys=True), utc_now()),
            )
            return int(cursor.lastrowid)

    def events(self, *, event_type: str | None = None, thread_id: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM events WHERE 1=1"
        params: list[Any] = []
        if event_type:
            sql += " AND type=?"
            params.append(event_type)
        if thread_id:
            sql += " AND thread_id=?"
            params.append(thread_id)
        sql += " ORDER BY seq"
        return [
            {**dict(row), "payload": json.loads(row["payload"])} for row in self.all(sql, tuple(params))
        ]

    # -- leases --------------------------------------------------------------

    def acquire_lease(self, name: str, owner: str, ttl_seconds: float) -> bool:
        now = self._clock()
        with self.transaction() as conn:
            row = conn.execute("SELECT owner, expires_at_epoch FROM leases WHERE name=?", (name,)).fetchone()
            if row and row["owner"] != owner and row["expires_at_epoch"] > now and _owner_alive(row["owner"]):
                return False
            conn.execute(
                "INSERT INTO leases(name, owner, expires_at_epoch) VALUES (?,?,?) "
                "ON CONFLICT(name) DO UPDATE SET owner=excluded.owner, expires_at_epoch=excluded.expires_at_epoch",
                (name, owner, now + ttl_seconds),
            )
            return True

    def release_lease(self, name: str, owner: str) -> None:
        with self.transaction() as conn:
            conn.execute("DELETE FROM leases WHERE name=? AND owner=?", (name, owner))

    # -- jobs ----------------------------------------------------------------

    def job(self, job_id: str) -> sqlite3.Row:
        row = self.one("SELECT * FROM jobs WHERE id=?", (job_id,))
        if row is None:
            raise StoreError(f"unknown job {job_id}")
        return row

    def transition_job(
        self,
        job_id: str,
        target: JobState,
        *,
        expected: JobState | None = None,
        manual: bool = False,
        eligibility_passed: bool = False,
        owner_confirmed_not_executed: bool = False,
        blocker: str | None = None,
        next_check_at: str | None = None,
        route_attempt_id: str | None = None,
        conn: sqlite3.Connection | None = None,
        extra: dict[str, Any] | None = None,
    ) -> JobState:
        """Guarded compare-and-swap state change; records a job event."""

        def _apply(c: sqlite3.Connection) -> JobState:
            row = c.execute("SELECT state, route_attempt_id, cancelled FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise StoreError(f"unknown job {job_id}")
            current = JobState(row["state"])
            if expected is not None and current is not expected:
                raise StaleState(f"job {job_id} is {current.value}, expected {expected.value}")
            if route_attempt_id is not None and row["route_attempt_id"] != route_attempt_id:
                raise StaleState(f"job {job_id} route attempt fenced (late callback)")
            if row["cancelled"] and target is not JobState.CANCELLED:
                raise StaleState(f"job {job_id} was cancelled")
            check_transition(
                current,
                target,
                manual=manual,
                eligibility_passed=eligibility_passed,
                owner_confirmed_not_executed=owner_confirmed_not_executed,
            )
            c.execute(
                "UPDATE jobs SET state=?, blocker=?, next_check_at=?, updated_at=?, "
                "cancelled=CASE WHEN ?='CANCELLED' THEN 1 ELSE cancelled END WHERE id=? AND state=?",
                (target.value, blocker, next_check_at, utc_now(), target.value, job_id, current.value),
            )
            thread_id = c.execute("SELECT thread_id FROM jobs WHERE id=?", (job_id,)).fetchone()["thread_id"]
            self.event(
                "job.state",
                {"from": current.value, "to": target.value, "blocker": blocker, **(extra or {})},
                thread_id=thread_id,
                job_id=job_id,
                conn=c,
            )
            return target

        if conn is not None:
            return _apply(conn)
        with self.transaction() as c:
            return _apply(c)

    # -- threads / projects --------------------------------------------------

    def thread(self, thread_id: str) -> sqlite3.Row:
        row = self.one("SELECT * FROM threads WHERE id=?", (thread_id,))
        if row is None:
            raise StoreError(f"unknown thread {thread_id}")
        return row

    def project_by_name(self, name: str) -> sqlite3.Row | None:
        return self.one("SELECT * FROM projects WHERE name=?", (name,))

    def project(self, project_id: str) -> sqlite3.Row:
        row = self.one("SELECT * FROM projects WHERE id=?", (project_id,))
        if row is None:
            raise StoreError(f"unknown project {project_id}")
        return row

    # -- messages ------------------------------------------------------------

    def add_message(
        self,
        thread_id: str,
        role: str,
        kind: str,
        content: str,
        *,
        provenance: str,
        task_id: str | None = None,
        dispatch_id: str | None = None,
        complete: bool = True,
        conn: sqlite3.Connection | None = None,
        message_id: str | None = None,
    ) -> str:
        message_id = message_id or new_id("msg")
        now = utc_now()
        target = conn or self.conn
        with self._lock:
            target.execute(
                "INSERT INTO messages(id, thread_id, task_id, dispatch_id, role, kind, content, provenance, content_hash, "
                "complete, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    message_id,
                    thread_id,
                    task_id,
                    dispatch_id,
                    role,
                    kind,
                    content,
                    provenance,
                    sha256_text(content),
                    int(complete),
                    now,
                    now,
                ),
            )
        return message_id

    def append_message_content(self, message_id: str, delta: str, *, complete: bool | None = None) -> None:
        with self.transaction() as conn:
            row = conn.execute("SELECT content FROM messages WHERE id=?", (message_id,)).fetchone()
            if row is None:
                raise StoreError(f"unknown message {message_id}")
            content = (row["content"] or "") + delta
            conn.execute(
                "UPDATE messages SET content=?, content_hash=?, updated_at=?, complete=COALESCE(?, complete) WHERE id=?",
                (content, sha256_text(content), utc_now(), None if complete is None else int(complete), message_id),
            )

    def messages(self, thread_id: str) -> list[sqlite3.Row]:
        return self.all("SELECT * FROM messages WHERE thread_id=? ORDER BY created_at, rowid", (thread_id,))


def lease_owner_id(instance: str) -> str:
    return f"pid{os.getpid()}:{instance}"


def _owner_alive(owner: str) -> bool:
    """A lease held by a process that no longer exists is stale."""
    if not owner.startswith("pid"):
        return True
    try:
        pid = int(owner[3:].split(":", 1)[0])
    except ValueError:
        return True
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _split_sql(sql: str) -> list[str]:
    statements = []
    buffer: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buffer).strip().rstrip(";")
            if statement:
                statements.append(statement)
            buffer = []
    if buffer:
        raise ContractError("unterminated SQL statement in migration")
    return statements


def dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def loads(value: str | None, default: Any = None) -> Any:
    if value is None:
        return default
    return json.loads(value)
