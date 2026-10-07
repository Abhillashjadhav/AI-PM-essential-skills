# Implementation decisions

2026-10-06: Added AI Workflow Trial Kit to the existing pm-tactical plugin because workflow-effort accounting is separate from pm-verifier's model-quality and release gates.

2026-10-06: Supported only frozen, balanced parallel units with resolved spillover declarations; unsupported designs need external design review. Declarations and hashes do not certify validity.

2026-10-06: Retained every original assignment through a common horizon, showed customer successes beside measured active person-time, and kept omitted work visible. No causal, statistical, ROI or launch decision is produced.

2026-10-06: Used standard-library Python for the runtime. The optional demo recorder uses existing Pillow and ffmpeg to render real cloud Linux PTY output; no model or account is involved.

2026-10-06: Kept work on a local branch with local commits and Library deliverables under explicit user instruction. Push, PR creation, merge and external publication are out of scope.
