"""Importer for authorised conversation exports in a documented local format.

The router does not inherit ChatGPT memory or browser history. It only knows
what its own client saw or what the owner explicitly imports. Actual imports of
real exports remain subject to the repository's human-approval gate; the
public repository ships only synthetic examples.

Accepted format (``fixtures/import-example.json``)::

    {"format": "model-router-import.1",
     "source": "free text: where this came from",
     "authorised_by": "owner",
     "projects": [{"id": "...", "name": "...", "threads": [
         {"id": "...", "title": "...", "created_at": "...Z", "model": "...",
          "kind": "transcript" | "memory_summary",
          "messages": [{"id": "...", "role": "user|assistant", "created_at": "...Z", "content": "..."}]}]}]}

Memory summaries are imported as summaries, never represented as transcripts.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Any

from .contracts import ContractError, parse_utc, sha256_text, utc_now
from .store import Store

FORMAT = "model-router-import.1"


def import_file(store: Store, path: Path, *, project_root: str, since_days: int | None = None, now: str | None = None) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("format") != FORMAT:
        raise ContractError(f"unsupported import format {data.get('format')!r}; expected {FORMAT}")
    if not data.get("authorised_by"):
        raise ContractError("import file must state who authorised it (authorised_by)")
    cutoff = parse_utc(now or utc_now()) - timedelta(days=since_days) if since_days else None
    coverage: dict[str, dict[str, int]] = defaultdict(lambda: {"threads": 0, "messages": 0, "duplicates": 0, "summaries": 0, "skipped_old": 0})
    omissions: list[str] = []
    for project in data.get("projects", []):
        name = project.get("name") or project.get("id")
        if not name:
            omissions.append("project without id/name skipped")
            continue
        local_name = f"import:{name}"
        row = store.project_by_name(local_name)
        if row is None:
            project_id = f"prj_import_{sha256_text(local_name)[:16]}"
            store.execute(
                "INSERT INTO projects(id, name, root, worktree, write_scope, created_at) VALUES (?,?,?,?,?,?)",
                (project_id, local_name, project_root, None, "[]", utc_now()),
            )
        else:
            project_id = row["id"]
        for thread in project.get("threads", []):
            if not thread.get("id") or not thread.get("created_at"):
                omissions.append(f"{name}: thread without id/created_at skipped")
                continue
            if cutoff and parse_utc(thread["created_at"]) < cutoff:
                coverage[name]["skipped_old"] += 1
                continue
            local_id = f"thr_import_{sha256_text(name + '|' + thread['id'])[:20]}"
            is_summary = thread.get("kind") == "memory_summary"
            if store.one("SELECT id FROM threads WHERE id=?", (local_id,)) is None:
                store.execute(
                    "INSERT INTO threads(id, provider_thread_id, project_id, kind, synthetic, title, pinned_model, status, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (local_id, None, project_id, "imported", int(bool(data.get("synthetic"))), thread.get("title"),
                     thread.get("model"), "imported" if not is_summary else "imported_summary", thread["created_at"], thread["created_at"]),
                )
                coverage[name]["threads"] += 1
                if is_summary:
                    coverage[name]["summaries"] += 1
            for message in thread.get("messages", []):
                content = message.get("content")
                if content is None:
                    omissions.append(f"{name}/{thread['id']}: message {message.get('id')} has no content")
                    continue
                message_id = f"msg_import_{sha256_text(local_id + '|' + str(message.get('id')) + '|' + content)[:20]}"
                if store.one("SELECT id FROM messages WHERE id=?", (message_id,)):
                    coverage[name]["duplicates"] += 1
                    continue
                created = message.get("created_at") or thread["created_at"]
                store.execute(
                    "INSERT INTO messages(id, thread_id, role, kind, content, provenance, content_hash, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (message_id, local_id, message.get("role", "unknown"), "memory_summary" if is_summary else "imported",
                     content, f"import:{data.get('source', 'unspecified')}", sha256_text(content), created, created),
                )
                coverage[name]["messages"] += 1
    store.event("import.completed", {"file_sha256": sha256_text(Path(path).read_text(encoding="utf-8")), "coverage": dict(coverage), "omissions": len(omissions)})
    return {
        "coverage": dict(coverage),
        "omissions": omissions,
        "note": "memory summaries are marked as summaries, not transcripts; re-imports are deduplicated",
    }
