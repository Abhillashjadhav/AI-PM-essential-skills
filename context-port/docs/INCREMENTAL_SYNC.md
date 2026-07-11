# Incremental sync planning

Phase 8 compares two validated ContextPacks and emits deterministic changes, checkpoints, tombstones, and conflicts. It performs no write.

Detected changes include additions, message appends, edits, title renames, parent moves, ordinal reordering, and deletions. Deletions become tombstones; source content is not removed by the planner.

Optional peer-state digests identify divergent same-item changes. Conflicts are labeled `human_required` and are never semantically resolved automatically.

Destination adapters, checkpoint persistence, and approved effect application remain later phases.
