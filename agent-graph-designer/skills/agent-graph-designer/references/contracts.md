# Graph contract fields

## Node contract

Each node requires:

```text
id
type: LOOP | WORKER | VERIFIER | JOIN | HUMAN_GATE | TERMINAL
purpose
owner
inputs: names plus schemas
outputs: names plus schemas
reads_state
writes_state
allowed_tools
permissions: read/write/action allowlists
model_policy: capability requirement, not an unverified current model name
budget: time and token/cost ceiling
timeout_seconds
max_attempts
verifier: distinct role plus binary gates
on_exhaustion: BLOCKED | ESCALATE
```

## Edge contract

Each edge requires:

```text
id
source
target
type: SEQUENCE | FAN_OUT | FAN_IN | PASS | FAIL | RETRY | ESCALATE | APPROVE | REJECT
condition
evidence_required
state_mapping
priority when multiple edges could fire
```

Conditions must be mutually exclusive or carry explicit priority. An edge that says only "when appropriate" is invalid.

## State contract

```text
schema_version
fields: name, schema, writer nodes, reader nodes, sensitivity, freshness
idempotency_key
checkpoint_after
merge_policy
conflict_policy
retention_or_redaction
```

## Join contract

```text
node_id
required_branches
policy: ALL_REQUIRED | THRESHOLD | FIRST_VALID
threshold when used
artifact_schema
timeout_seconds
on_missing
on_failed
on_stale
on_conflict
```

## Graph-level contract

```text
name
version
outcome
start_node
terminal_nodes
node_cap
concurrency_cap
total_budget
max_repairs_per_node (maximum 2)
human_approval_actions
kill_switch
nodes
edges
state
joins
```

The machine-readable contract is the source of truth. Generate diagrams and runner scaffolding from it or cross-check them against it.
