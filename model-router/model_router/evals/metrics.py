"""Weekly metrics: the owner's guardrail plus a reasoned diagnostic view.

Guardrail (owner definition, unchanged): distinct eligible chat threads with any
human model override / distinct eligible chat threads, grouped by thread-start
ISO week. A thread counts once however many overrides it has.

Eligible thread: an automatically routed, non-synthetic, non-evaluation thread
whose selected model produced some answer to a real user task.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any

from ..capacity import wilson_interval
from ..contracts import CLASSIFIER_VERSION, POLICY_VERSION, REPORT_SCHEMA_VERSION, parse_utc, utc_now
from ..store import Store
from .graders import GRADER_VERSION

TARGET_OVERRIDE_RATE = 0.05
SMALL_SAMPLE = 20  # below this, the report refuses to judge the 5% target


def iso_week(ts: str) -> str:
    year, week, _ = parse_utc(ts).isocalendar()
    return f"{year}-W{week:02d}"


def week_bounds(week: str) -> tuple[datetime, datetime]:
    year, number = week.split("-W")
    start = datetime.combine(date.fromisocalendar(int(year), int(number), 1), datetime.min.time(), tzinfo=timezone.utc)
    return start, start + timedelta(days=7)


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(pct / 100 * (len(ordered) - 1))))
    return round(ordered[index], 2)


def weekly_report(store: Store, week: str, *, include_synthetic: bool = False, now: str | None = None) -> dict[str, Any]:
    start, end = week_bounds(week)
    now_dt = parse_utc(now or utc_now())
    threads = [
        dict(r)
        for r in store.all("SELECT * FROM threads WHERE kind IN ('ordinary','implementation')")
        if start <= parse_utc(r["created_at"]) < end and (include_synthetic or not r["synthetic"])
    ]
    ids = [t["id"] for t in threads]

    def rows(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        return [dict(r) for r in store.all(sql, params)]

    first_routes: dict[str, dict[str, Any]] = {}
    for route in rows("SELECT * FROM route_decisions ORDER BY created_at"):
        if route["thread_id"] in ids and route["thread_id"] not in first_routes:
            first_routes[route["thread_id"]] = route | {"payload": json.loads(route["payload"])}
    answered = {
        r["thread_id"]
        for r in rows("SELECT thread_id FROM messages WHERE role='assistant' AND content IS NOT NULL AND length(content) > 0")
    }
    overrides = [o for o in rows("SELECT * FROM overrides ORDER BY at") if o["thread_id"] in ids]
    outcomes_all = rows("SELECT * FROM outcomes ORDER BY recorded_at")
    outcomes = [o for o in outcomes_all if o["thread_id"] in ids]
    latest_outcome: dict[str, dict[str, Any]] = {}
    for outcome in outcomes:
        latest_outcome[outcome["thread_id"]] = outcome

    eligible, blocked, timeout_manual, manual_other = [], [], [], []
    for thread in threads:
        route = first_routes.get(thread["id"])
        if route is None:
            blocked.append(thread["id"])
            continue
        if route["manual"]:
            (timeout_manual if "timed out" in json.dumps(route["payload"]) or "within" in json.dumps(route["payload"]) else manual_other).append(thread["id"])
            continue
        if thread["id"] in answered and route["model_id"]:
            eligible.append(thread["id"])
        else:
            blocked.append(thread["id"])

    override_threads = sorted({o["thread_id"] for o in overrides if o["thread_id"] in eligible})
    rate = len(override_threads) / len(eligible) if eligible else None
    interval = wilson_interval(len(override_threads), len(eligible))
    if not eligible:
        verdict = "no eligible threads this week; nothing to judge"
    elif len(eligible) < SMALL_SAMPLE:
        verdict = f"sample too small ({len(eligible)} eligible threads) to judge the 5% target; raw counts only"
    elif interval and interval[1] <= TARGET_OVERRIDE_RATE:
        verdict = "within the 5% target (upper 95% bound at or below 5%)"
    elif interval and interval[0] > TARGET_OVERRIDE_RATE:
        verdict = "above the 5% target (lower 95% bound above 5%)"
    else:
        verdict = "inconclusive against the 5% target (interval spans 5%)"

    reasons = Counter(o["reason"] for o in overrides)
    different_task_only = {
        t for t in override_threads if all(o["reason"] == "different_task" for o in overrides if o["thread_id"] == t)
    }
    adjusted = len(override_threads) - len(different_task_only)
    failures_without_switch = [
        t for t, o in latest_outcome.items() if o["outcome"] in {"failed", "partial"} and t not in {x["thread_id"] for x in overrides}
    ]
    outcome_counts = Counter(o["outcome"] for o in latest_outcome.values())
    unknown_outcome = [t for t in eligible if t not in latest_outcome]
    late_feedback = [o["id"] for o in outcomes if parse_utc(o["recorded_at"]) >= end]

    role_mix = Counter((first_routes[t]["role"] or "manual") for t in first_routes)
    model_mix = Counter((first_routes[t]["model_id"] or "none") for t in first_routes)
    upward = [
        t for t, r in first_routes.items()
        if r["payload"].get("upward_fallback") or any(rule in ("RF-UPWARD", "RF-UNKNOWN") for rule in r["payload"].get("rule_ids", []))
    ]
    latencies = [(r["payload"].get("timings_ms") or {}) for r in first_routes.values()]
    cold = [t["submit_to_selection_ms"] for t in latencies if t.get("cold") and "submit_to_selection_ms" in t]
    warm = [t["submit_to_selection_ms"] for t in latencies if not t.get("cold") and "submit_to_selection_ms" in t]
    all_lat = cold + warm
    dispatch_timings = [json.loads(r["timings"]) for r in rows("SELECT thread_id, timings FROM dispatches") if r["thread_id"] in ids]
    elig = [d["eligibility_ms"] for d in dispatch_timings if "eligibility_ms" in d]
    sel_to_disp = [d["selected_to_dispatch_ms"] for d in dispatch_timings if "selected_to_dispatch_ms" in d]

    usage = [
        dict(r) for r in store.all("SELECT observed_at, synthetic, plan_type FROM usage_snapshots")
        if start <= parse_utc(r["observed_at"]) < end and (include_synthetic or not r["synthetic"])
    ]
    week_override_events = [
        e for e in store.events(event_type="model.overridden") if start <= parse_utc(e["at"]) < end
    ]
    registry_changes = [e["payload"] for e in store.events(event_type="model.approval") if start <= parse_utc(e["at"]) < end]
    policies = sorted({r["payload"].get("policy_version", POLICY_VERSION) for r in first_routes.values()})

    failed_jobs = rows("SELECT id, thread_id, blocker FROM jobs WHERE state='FAILED'")
    review_failures = [j for j in failed_jobs if j["thread_id"] in ids][:5]
    quality_overrides = [o for o in overrides if o["reason"] == "answer_quality"][:5]
    candidates = rows("SELECT model_id, account_scope FROM registry_models WHERE status='candidate' AND available=1")
    eval_runs = rows("SELECT id, kind, status, created_at FROM eval_runs ORDER BY created_at DESC LIMIT 5")

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "week": week,
        "generated_at": utc_now(),
        "synthetic_included": include_synthetic,
        "cohort_complete": now_dt >= end,
        "guardrail": {
            "definition": "distinct eligible threads with any human override / distinct eligible threads (thread-start cohort)",
            "eligible_threads": len(eligible),
            "threads_with_override": len(override_threads),
            "rate": None if rate is None else round(rate, 4),
            "wilson_95": None if interval is None else [round(interval[0], 4), round(interval[1], 4)],
            "target": TARGET_OVERRIDE_RATE,
            "verdict": verdict,
        },
        "proposed_adjusted_view": {
            "status": "PROPOSED — awaiting owner acceptance; the guardrail above is unchanged",
            "excludes": "threads whose only overrides were for a genuinely different task",
            "threads_with_override": adjusted,
            "rate": None if not eligible else round(adjusted / len(eligible), 4),
        },
        "diagnostic": {
            "override_reasons": dict(reasons),
            "override_events_in_cohort": len(overrides),
            "different_task_only_threads": len(different_task_only),
            "unknown_reason_overrides": reasons.get("unknown", 0),
            "explicit_failures_without_switch": failures_without_switch,
            "outcomes": dict(outcome_counts),
            "confirmed_resolutions": outcome_counts.get("resolved", 0),
            "unknown_outcomes": len(unknown_outcome),
            "late_feedback_outcomes": late_feedback,
            "note": "no override does not mean resolved; inactivity is not abandonment",
        },
        "system": {
            "threads_started": len(threads),
            "blocked_or_no_answer_threads": len(blocked),
            "manual_after_routing_timeout": len(timeout_manual),
            "manual_other": len(manual_other),
            "upward_fallbacks": len(upward),
            "role_mix": dict(role_mix),
            "model_mix": dict(model_mix),
            "classification_uncertainty_rate": None if not first_routes else round(len(upward) / len(first_routes), 4),
        },
        "latency_ms": {
            "measured": "submit to durable model selection (excludes output generation)",
            "count": len(all_lat),
            "cold": {"count": len(cold), "p50": percentile(cold, 50), "p90": percentile(cold, 90), "max": max(cold) if cold else None},
            "warm": {"count": len(warm), "p50": percentile(warm, 50), "p90": percentile(warm, 90), "max": max(warm) if warm else None},
            "over_1s": sum(1 for v in all_lat if v > 1000),
            "over_2s": sum(1 for v in all_lat if v > 2000),
            "over_4s": sum(1 for v in all_lat if v > 4000),
            "eligibility_wait": {"count": len(elig), "p50": percentile(elig, 50), "max": max(elig) if elig else None},
            "selected_to_dispatch": {"count": len(sel_to_disp), "p50": percentile(sel_to_disp, 50), "max": max(sel_to_disp) if sel_to_disp else None},
        },
        "usage_observations": {
            "snapshots": len(usage),
            "note": "percent-used snapshots are rounded, delayed and shared with other sessions; not a remaining balance",
        },
        "versions": {
            "policy": policies or [POLICY_VERSION],
            "classifier": CLASSIFIER_VERSION,
            "grader": GRADER_VERSION,
            "registry_changes": registry_changes,
        },
        "this_week_override_events": [e["payload"] | {"at": e["at"], "thread_id": e["thread_id"]} for e in week_override_events],
        "review_pack": {
            "budget": "fits a 30-minute weekly review: at most 5 items per list",
            "prioritised_failures": review_failures,
            "quality_overrides": [{"thread_id": o["thread_id"], "old": o["old_model"], "new": o["new_model"]} for o in quality_overrides],
            "representative_threads": [{"thread_id": t["id"], "title": t["title"]} for t in threads[:5]],
            "candidate_comparisons": eval_runs,
            "approval_queue": candidates[:5],
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    g = report["guardrail"]
    d = report["diagnostic"]
    s = report["system"]
    lat = report["latency_ms"]
    lines = [
        f"# Model router weekly report — {report['week']}",
        "",
        f"Generated {report['generated_at']} · schema {report['schema_version']}"
        + (" · **includes SYNTHETIC data**" if report["synthetic_included"] else "")
        + ("" if report["cohort_complete"] else " · cohort still open (incomplete)"),
        "",
        "## Owner guardrail (≤ 5% of threads changed)",
        "",
        f"- Eligible threads: **{g['eligible_threads']}**; threads with any override: **{g['threads_with_override']}**",
        f"- Rate: {g['rate'] if g['rate'] is not None else 'n/a'} (Wilson 95%: {g['wilson_95'] or 'n/a'})",
        f"- Verdict: {g['verdict']}",
        "",
        "## Proposed adjusted view (not adopted)",
        "",
        f"- {report['proposed_adjusted_view']['status']}",
        f"- Excluding different-task-only threads: {report['proposed_adjusted_view']['threads_with_override']} threads",
        "",
        "## Diagnostic view",
        "",
        f"- Override reasons: {d['override_reasons'] or 'none'}",
        f"- Explicit failures without a model switch: {len(d['explicit_failures_without_switch'])}",
        f"- Outcomes: {d['outcomes'] or 'none recorded'}; unknown outcomes: {d['unknown_outcomes']}; late feedback: {len(d['late_feedback_outcomes'])}",
        f"- {d['note']}",
        "",
        "## System",
        "",
        f"- Threads started: {s['threads_started']}; blocked/no-answer: {s['blocked_or_no_answer_threads']}; manual after routing timeout: {s['manual_after_routing_timeout']}",
        f"- Upward fallbacks: {s['upward_fallbacks']}; role mix: {s['role_mix']}; model mix: {s['model_mix']}",
        "",
        "## Routing latency (submit → durable selection)",
        "",
        f"- Cold: n={lat['cold']['count']} p50={lat['cold']['p50']} p90={lat['cold']['p90']} max={lat['cold']['max']}",
        f"- Warm: n={lat['warm']['count']} p50={lat['warm']['p50']} p90={lat['warm']['p90']} max={lat['warm']['max']}",
        f"- Over 1 s: {lat['over_1s']}; over 2 s: {lat['over_2s']}; over 4 s: {lat['over_4s']}",
        f"- Eligibility wait (separate): n={lat['eligibility_wait']['count']} p50={lat['eligibility_wait']['p50']} max={lat['eligibility_wait']['max']}",
        "",
        "## Usage observations",
        "",
        f"- {report['usage_observations']['snapshots']} snapshots. {report['usage_observations']['note']}",
        "",
        "## Versions",
        "",
        f"- Policy {report['versions']['policy']}; classifier {report['versions']['classifier']}; grader {report['versions']['grader']}",
        f"- Registry changes this week: {len(report['versions']['registry_changes'])}",
        "",
        "## Review pack (≤ 30 minutes)",
        "",
    ]
    pack = report["review_pack"]
    for title, key in (("Prioritised failures", "prioritised_failures"), ("Quality overrides", "quality_overrides"),
                       ("Representative threads", "representative_threads"), ("Candidate comparisons", "candidate_comparisons"),
                       ("Approval queue", "approval_queue")):
        items = pack[key]
        lines.append(f"- {title}: " + ("none" if not items else "; ".join(json.dumps(i, sort_keys=True) for i in items)))
    return "\n".join(lines) + "\n"
