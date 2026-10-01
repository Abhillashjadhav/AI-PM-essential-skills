"""Read-only report exports (future dashboard contract) and diagnostics.

* Weekly cohort reports: JSON + Markdown (derived artifacts; the SQLite
  evidence remains the source of truth).
* Case drill-down, version history, latency and override/outcome trajectories.
* Diagnostic export is redacted by default: no message content, attachment
  text, e-mail addresses, paths under $HOME, or raw provider payloads.
  A private transcript export requires an explicit flag.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .contracts import REPORT_SCHEMA_VERSION, utc_now
from .evals.metrics import render_markdown, weekly_report
from .store import Store, atomic_write

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
SECRETISH = re.compile(r"(sk-[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9]{8,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})")


def scrub(text: str | None) -> str | None:
    if text is None:
        return None
    text = EMAIL.sub("[email]", text)
    text = SECRETISH.sub("[secret]", text)
    home = str(Path.home())
    return text.replace(home, "~")


def export_weekly(store: Store, week: str, out_dir: Path, *, include_synthetic: bool = False) -> dict[str, str]:
    report = weekly_report(store, week, include_synthetic=include_synthetic)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"weekly-{week}.json"
    md_path = out_dir / f"weekly-{week}.md"
    atomic_write(json_path, json.dumps(report, indent=2, sort_keys=True))
    atomic_write(md_path, render_markdown(report))
    return {"json": str(json_path), "markdown": str(md_path)}


def thread_drilldown(store: Store, thread_id: str, *, include_content: bool = False) -> dict[str, Any]:
    thread = dict(store.thread(thread_id))
    messages = [dict(m) for m in store.messages(thread_id)]
    if not include_content:
        for message in messages:
            message["content"] = f"[{len(message['content'] or '')} chars withheld]"
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "thread": thread,
        "pins": [dict(r) for r in store.all("SELECT * FROM pin_history WHERE thread_id=? ORDER BY at", (thread_id,))],
        "routes": [dict(r) for r in store.all("SELECT * FROM route_decisions WHERE thread_id=? ORDER BY created_at", (thread_id,))],
        "jobs": [dict(r) for r in store.all("SELECT * FROM jobs WHERE thread_id=? ORDER BY created_at", (thread_id,))],
        "dispatches": [dict(r) for r in store.all("SELECT * FROM dispatches WHERE thread_id=? ORDER BY created_at", (thread_id,))],
        "overrides": [dict(r) for r in store.all("SELECT * FROM overrides WHERE thread_id=? ORDER BY at", (thread_id,))],
        "outcomes": [dict(r) for r in store.all("SELECT * FROM outcomes WHERE thread_id=? ORDER BY recorded_at", (thread_id,))],
        "messages": messages,
        "events": store.events(thread_id=thread_id),
    }


def diagnostic_export(store: Store, *, private: bool = False) -> dict[str, Any]:
    """Redacted by default. ``private=True`` must be an explicit owner request."""

    def table(name: str, drop: tuple[str, ...] = ()) -> list[dict[str, Any]]:
        rows = []
        for row in store.all(f"SELECT * FROM {name}"):
            item = dict(row)
            for column in drop:
                if column in item and not private:
                    item[column] = "[withheld]"
            for key, value in list(item.items()):
                if isinstance(value, str) and not private:
                    item[key] = scrub(value)
            rows.append(item)
        return rows

    return {
        "schema_version": "diagnostic-export.1",
        "generated_at": utc_now(),
        "redacted": not private,
        "note": "private export: contains conversation content" if private else "message content, attachment text and raw provider payloads withheld",
        "schema": store.schema_version(),
        "integrity_problems": store.integrity_check(),
        "projects": table("projects", ("root", "worktree", "write_scope")),
        "threads": table("threads", ("title",)),
        "jobs": table("jobs", ("blocker",)),
        "dispatches": table("dispatches"),
        "route_decisions": table("route_decisions"),
        "overrides": table("overrides", ("reason_text",)),
        "outcomes": table("outcomes", ("note",)),
        "messages": table("messages", ("content",)),
        "attachments": table("attachments", ("source_path", "source_url")),
        "usage_snapshots": table("usage_snapshots", ("raw_redacted",)),
        "events": [
            {k: (v if private or k != "payload" else "[withheld]") for k, v in e.items()} for e in store.events()
        ],
    }
