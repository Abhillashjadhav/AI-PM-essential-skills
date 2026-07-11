# Real Claude-export converter policy

Status: Implementing

Migration fidelity takes priority over automatic categorization. Preserve a verified project reference exactly. Put every conversation without a verified project reference into one generated project named `Unmapped Conversations`. Do not infer, classify, score confidence, or use LLM reasoning. Preserve UUIDs, titles, timestamps, message order, attachments, memories, design chats, and project instructions. Never silently discard unsupported data. Produce deterministic `contextpack.json`, `manifest.json`, `reconciliation-report.json`, and `loss-report.json`; require exact source/output counts and zero losses. Do not attempt destination import.
