"""Deterministic generator for the summarization case study (500 traces).

An AI summarizer over five source types (meeting transcripts, email threads,
articles, research papers, Slack threads). We first synthesize 30 unique source
documents (500-5000 words), then create multiple summarization traces per source
with different attempts and failure modes.

Each trace embeds the full source in `retrieved_context` so the example is
self-contained and a faithfulness judge has the ground truth to check against.

Quality distribution (500 total):
    160 faithful concise summaries     (trimmed from a nominal 200)
    100 omissions (key fact missing)
     80 fabrications (asserts something not in source)
     50 wrong-emphasis (buries the key decision)
     40 over-long (no compression value)
     30 stylistic mismatches
     20 unattributed quotes (paraphrase shown as direct quote)
     20 hallucinated participants

Run: python examples/summarization/generate.py
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 20260522
random.seed(SEED)
OUT = Path(__file__).parent / "traces.jsonl"
SOURCES_OUT = Path(__file__).parent / "sources.jsonl"

SOURCE_TYPES = ["meeting_transcript", "email_thread", "article", "research_paper", "slack_thread"]
CHANNELS = ["chat", "email", "in-app"]
TIERS = ["free", "pro", "enterprise"]
MODELS = ["claude-3.5-sonnet", "gpt-4o", "claude-3-haiku"]

NAMES = [
    "Sarah", "Miguel", "Priya", "Tom", "Aisha", "Jonas", "Wei", "Lena",
    "Carlos", "Nadia", "Ben", "Yuki", "Omar", "Grace", "Felix", "Ravi",
]

TOPIC_NOUNS = [
    "the Q3 roadmap", "the pricing migration", "the onboarding redesign",
    "the data pipeline outage", "the mobile launch", "the hiring plan",
    "the security audit", "the partnership with Northwind", "the API v2 rollout",
    "the customer churn analysis",
]

BODY_SENTENCES = [
    "The team reviewed the current status and flagged the main risks.",
    "Adoption metrics were trending up week over week across all segments.",
    "Several customers had raised the same concern in recent calls.",
    "Engineering estimated the work at roughly three sprints.",
    "There was disagreement about whether to ship behind a feature flag.",
    "The budget impact was described as modest but non-trivial.",
    "Marketing wanted a coordinated announcement to amplify the launch.",
    "Support raised that documentation would need to be updated first.",
    "A dependency on the platform team could slip the timeline.",
    "Early experiments showed a measurable lift in activation.",
    "Legal asked for a review before any external commitments.",
    "The group agreed to revisit the open questions next week.",
    "Data showed the regression was isolated to one cohort.",
    "Two stakeholders volunteered to draft the follow-up proposal.",
    "The proposed change would simplify the existing workflow considerably.",
]


def make_source(idx: int) -> dict:
    """Build one synthetic source document with extractable ground-truth facts."""
    stype = SOURCE_TYPES[idx % len(SOURCE_TYPES)]
    n_people = random.randint(3, 5)
    participants = random.sample(NAMES, n_people)
    topic = random.choice(TOPIC_NOUNS)
    key_decision = (
        f"The group decided to proceed with {topic} and ship it next month."
    )
    key_facts = [
        f"{participants[0]} owns the next steps for {topic}.",
        f"The target date for {topic} is the end of next month.",
        f"The main risk for {topic} is the platform-team dependency.",
    ]
    real_quote = f"{participants[1]} said, \"We should not block the launch on perfect docs.\""

    target_words = random.randint(500, 5000)
    lines: list[str] = []
    if stype == "meeting_transcript":
        lines.append(f"Meeting: {topic} sync. Attendees: {', '.join(participants)}.")
    elif stype == "email_thread":
        lines.append(f"Subject: {topic} — next steps. Participants: {', '.join(participants)}.")
    elif stype == "slack_thread":
        lines.append(f"#project channel — thread on {topic}. In thread: {', '.join(participants)}.")
    elif stype == "article":
        lines.append(f"How teams are rethinking {topic}. By {participants[0]}.")
    else:
        lines.append(f"On {topic}: an empirical study. Authors: {', '.join(participants)}.")

    lines.append(key_decision)
    lines.extend(key_facts)
    lines.append(real_quote)

    # Pad the body to the target word count with attributed dialogue/sentences.
    while len(" ".join(lines).split()) < target_words:
        speaker = random.choice(participants)
        sent = random.choice(BODY_SENTENCES)
        if stype in ("meeting_transcript", "slack_thread"):
            lines.append(f"{speaker}: {sent}")
        else:
            lines.append(sent)

    body = "\n".join(lines)
    return {
        "source_id": f"src_{idx:02d}",
        "source_type": stype,
        "text": body,
        "participants": participants,
        "key_decision": key_decision,
        "key_facts": key_facts,
        "real_quote": real_quote,
        "length_words": len(body.split()),
    }


# ---- summary generators (return the summary text) -------------------------

def faithful(src: dict) -> str:
    return (
        f"{src['key_decision']} {src['key_facts'][0]} {src['key_facts'][1]} "
        f"Key risk: the platform-team dependency."
    )


def omission(src: dict) -> str:
    # Drops the key decision entirely.
    return f"{src['key_facts'][0]} {src['key_facts'][1]} The team discussed several topics."


def fabrication(src: dict) -> str:
    return (
        f"{src['key_decision']} The board has already approved a $2M budget and a new "
        f"hire to lead it. (No such budget or hire appears in the source.)"
    )


def wrong_emphasis(src: dict) -> str:
    return (
        "Mainly, documentation will need updating and there were scheduling logistics to sort. "
        f"In passing, {src['key_decision'].lower()}"
    )


def over_long(src: dict) -> str:
    # No compression value: restate most of the source.
    return " ".join(src["text"].split()[: max(300, int(src["length_words"] * 0.9))])


def stylistic_mismatch(src: dict) -> str:
    return (
        "Pursuant to the aforementioned deliberations, the assembled parties did resolve, "
        f"with all due solemnity, to advance {src['key_decision'].lower()}"
    )


def unattributed_quote(src: dict) -> str:
    # Turns a paraphrase into a fake direct quote.
    return (
        f"{src['key_decision']} A participant stated verbatim: \"This is the most important "
        f"initiative of the year and nothing else matters.\" (Paraphrase presented as a quote.)"
    )


def hallucinated_participant(src: dict) -> str:
    ghost = random.choice([n for n in NAMES if n not in src["participants"]])
    return (
        f"{src['key_decision']} {ghost}, who led the discussion, will own follow-ups. "
        f"({ghost} was not present in the source.)"
    )


GENERATORS = {
    "faithful": faithful,
    "omission": omission,
    "fabrication": fabrication,
    "wrong_emphasis": wrong_emphasis,
    "over_long": over_long,
    "stylistic_mismatch": stylistic_mismatch,
    "unattributed_quote": unattributed_quote,
    "hallucinated_participant": hallucinated_participant,
}

COUNTS = {
    "faithful": 160,
    "omission": 100,
    "fabrication": 80,
    "wrong_emphasis": 50,
    "over_long": 40,
    "stylistic_mismatch": 30,
    "unattributed_quote": 20,
    "hallucinated_participant": 20,
}
assert sum(COUNTS.values()) == 500


def build() -> tuple[list[dict], list[dict]]:
    sources = [make_source(i) for i in range(30)]
    cats: list[str] = []
    for c, n in COUNTS.items():
        cats += [c] * n
    random.shuffle(cats)

    base_time = datetime(2026, 3, 1, 9, 0, 0)
    traces: list[dict] = []
    for i in range(500):
        cat = cats[i]
        src = sources[i % len(sources)]
        summary = GENERATORS[cat](src)
        summary_words = len(summary.split())
        ratio = round(summary_words / src["length_words"], 4)

        ts = base_time + timedelta(minutes=i * 5)
        trace = {
            "trace_id": f"sm_{i + 1:03d}",
            "conversation_id": f"single_{i:03d}",
            "turn_index": 0,
            "user_message": f"Summarize this {src['source_type'].replace('_', ' ')} concisely.",
            "agent_response": summary,
            "retrieved_context": [src["text"]],
            "source_id": src["source_id"],
            "source_type": src["source_type"],
            "source_length_words": src["length_words"],
            "summary_length_words": summary_words,
            "compression_ratio": ratio,
            "timestamp": ts.isoformat() + "Z",
            "metadata": {
                "channel": random.choice(CHANNELS),
                "user_tier": random.choice(TIERS),
                "response_latency_ms": random.randint(400, 8000),
                "model": random.choice(MODELS),
                "quality_label": cat,
                "source_id": src["source_id"],
            },
        }
        traces.append(trace)
    return traces, sources


def main() -> None:
    traces, sources = build()
    with SOURCES_OUT.open("w", encoding="utf-8") as fh:
        for s in sources:
            fh.write(json.dumps(s) + "\n")
    with OUT.open("w", encoding="utf-8") as fh:
        for t in traces:
            fh.write(json.dumps(t) + "\n")
    print(f"Wrote {len(traces)} traces to {OUT} and {len(sources)} sources to {SOURCES_OUT}")


if __name__ == "__main__":
    main()
