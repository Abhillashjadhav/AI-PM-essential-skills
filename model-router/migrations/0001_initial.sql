-- Model router initial schema. All times are UTC ISO-8601 strings.
-- Local and external (provider) identifiers are stored in separate columns.

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    root TEXT NOT NULL,
    worktree TEXT,
    write_scope TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE threads (
    id TEXT PRIMARY KEY,
    provider_thread_id TEXT,
    provider_thread_phase TEXT NOT NULL DEFAULT 'NONE',  -- NONE | CREATING | CREATED | UNCERTAIN
    account_scope TEXT,
    project_id TEXT NOT NULL REFERENCES projects(id),
    kind TEXT NOT NULL,
    synthetic INTEGER NOT NULL DEFAULT 0,
    source_thread_id TEXT REFERENCES threads(id),
    handoff_id TEXT,
    title TEXT,
    pinned_model TEXT,
    pinned_effort TEXT,
    pinned_role TEXT,
    pinned_manual INTEGER NOT NULL DEFAULT 0,
    registry_revision INTEGER,
    route_decision_id TEXT,
    status TEXT NOT NULL,
    current_segment INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX threads_provider_id ON threads(provider_thread_id) WHERE provider_thread_id IS NOT NULL;

CREATE TABLE pin_history (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES threads(id),
    model_id TEXT NOT NULL,
    reasoning_effort TEXT,
    role TEXT,
    source TEXT NOT NULL,               -- automatic | manual_timeout | override | handoff
    override_id TEXT,
    at TEXT NOT NULL
);

CREATE TABLE task_assessments (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES threads(id),
    segment INTEGER NOT NULL,
    payload TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (thread_id, segment)
);

CREATE TABLE route_decisions (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    thread_id TEXT NOT NULL REFERENCES threads(id),
    route_attempt_id TEXT NOT NULL UNIQUE,
    role TEXT,
    model_id TEXT,
    reasoning_effort TEXT,
    manual INTEGER NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE registry_models (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    account_scope TEXT NOT NULL,
    model_id TEXT NOT NULL,
    display_name TEXT,
    payload TEXT NOT NULL,
    status TEXT NOT NULL,               -- candidate | approved | retired
    available INTEGER NOT NULL DEFAULT 1,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    UNIQUE (provider, account_scope, model_id)
);

CREATE TABLE registry_revisions (
    revision INTEGER PRIMARY KEY AUTOINCREMENT,
    account_scope TEXT NOT NULL,
    parent INTEGER,
    note TEXT,
    active INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    activated_at TEXT
);

CREATE TABLE role_mappings (
    id TEXT PRIMARY KEY,
    revision INTEGER NOT NULL REFERENCES registry_revisions(revision),
    role TEXT NOT NULL,
    payload TEXT NOT NULL,
    binding_hash TEXT NOT NULL,
    approval_id TEXT NOT NULL,
    effective_at TEXT NOT NULL,
    UNIQUE (revision, role)
);

CREATE TABLE approvals (
    id TEXT PRIMARY KEY,
    actor TEXT NOT NULL,
    item_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    item_hash TEXT NOT NULL,
    decision TEXT NOT NULL,
    at TEXT NOT NULL
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES threads(id),
    task_id TEXT,
    dispatch_id TEXT,
    role TEXT NOT NULL,                 -- user | assistant | router | system
    kind TEXT NOT NULL,                 -- prompt | answer | partial | handoff | continuation | notice
    content TEXT,
    blob_ref TEXT,
    provenance TEXT NOT NULL,
    content_hash TEXT,
    complete INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE attachments (
    id TEXT PRIMARY KEY,
    thread_id TEXT REFERENCES threads(id),
    source_path TEXT,
    source_url TEXT,
    kind TEXT NOT NULL,
    original_blob TEXT,
    extracted_blob TEXT,
    extraction_state TEXT NOT NULL,     -- extracted | failed | blocked
    notes TEXT NOT NULL DEFAULT '[]',
    original_hash TEXT,
    extracted_hash TEXT,
    bytes INTEGER,
    duration_ms REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE architecture_records (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES threads(id),
    version INTEGER NOT NULL,
    payload TEXT NOT NULL,
    prose_blob TEXT NOT NULL,
    record_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (thread_id, version),
    UNIQUE (thread_id, record_hash)
);

CREATE TABLE handoffs (
    id TEXT PRIMARY KEY,
    source_thread_id TEXT NOT NULL REFERENCES threads(id),
    architecture_version INTEGER NOT NULL,
    architecture_hash TEXT NOT NULL,
    package_blob TEXT,
    package_hash TEXT,
    acceptance TEXT NOT NULL,
    clarity TEXT,
    risk TEXT,
    status TEXT NOT NULL,               -- READY | CREATED | HELD | BLOCKED_CONTEXT
    hold_reasons TEXT NOT NULL DEFAULT '[]',
    target_thread_id TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (source_thread_id, architecture_version)
);

CREATE TABLE usage_snapshots (
    id TEXT PRIMARY KEY,
    account_scope TEXT,
    plan_type TEXT,
    payload TEXT NOT NULL,
    raw_redacted TEXT,
    observed_at TEXT NOT NULL,
    source TEXT NOT NULL,
    synthetic INTEGER NOT NULL
);

CREATE TABLE spend_evidence (
    id TEXT PRIMARY KEY,
    account_scope TEXT,
    payload TEXT NOT NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    expires_at TEXT,
    invalidated_at TEXT
);

CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    logical_key TEXT NOT NULL UNIQUE,
    thread_id TEXT NOT NULL REFERENCES threads(id),
    request_id TEXT NOT NULL,
    kind TEXT NOT NULL,                 -- user_turn | handoff_start | continuation | evaluation
    state TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    urgency TEXT,
    route_attempt_id TEXT,
    input_message_id TEXT,
    blocker TEXT,
    next_check_at TEXT,
    user_requested INTEGER NOT NULL DEFAULT 1,
    cancelled INTEGER NOT NULL DEFAULT 0,
    submitted_mono_ms REAL,
    selected_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE dispatches (
    id TEXT PRIMARY KEY,
    dispatch_id TEXT NOT NULL UNIQUE,
    job_id TEXT NOT NULL REFERENCES jobs(id),
    thread_id TEXT NOT NULL REFERENCES threads(id),
    phase TEXT NOT NULL,
    provider_turn_id TEXT,
    requested_model TEXT NOT NULL,
    requested_effort TEXT,
    observed_model TEXT,
    observed_model_note TEXT NOT NULL DEFAULT 'not reported',
    turn_status TEXT,
    error TEXT,
    retry_history TEXT NOT NULL DEFAULT '[]',
    timings TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX dispatch_one_open_per_job ON dispatches(job_id)
    WHERE phase IN ('PREPARED', 'SENT', 'ACKNOWLEDGED', 'UNCERTAIN');

CREATE TABLE checkpoints (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES threads(id),
    job_id TEXT,
    dispatch_id TEXT,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE eval_runs (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,                 -- offline | live
    plan TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE evaluations (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES eval_runs(id),
    case_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL,
    synthetic INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE outcomes (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES threads(id),
    task_id TEXT,
    outcome TEXT NOT NULL,
    source TEXT NOT NULL,
    satisfaction INTEGER,
    note TEXT,
    recorded_at TEXT NOT NULL
);

CREATE TABLE overrides (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES threads(id),
    task_id TEXT,
    old_model TEXT,
    new_model TEXT NOT NULL,
    reason TEXT NOT NULL,
    reason_text TEXT,
    execution_result TEXT NOT NULL,
    at TEXT NOT NULL
);

CREATE TABLE events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    schema_version TEXT NOT NULL,
    type TEXT NOT NULL,
    thread_id TEXT,
    job_id TEXT,
    payload TEXT NOT NULL,
    at TEXT NOT NULL
);
CREATE INDEX events_type ON events(type);
CREATE INDEX events_thread ON events(thread_id);

CREATE TABLE leases (
    name TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    expires_at_epoch REAL NOT NULL
);
