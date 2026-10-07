# Research notes and design boundaries

Sources checked on 2026-10-06. These motivate local measurement; they are not
benchmarks or evidence that this kit measures a causal effect.

- [METR, July 10 2025](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/):
  a task-randomized study of 16 experienced contributors and 246 issues in
  familiar open-source repositories found slower completion with early-2025
  tools. It is a historical, narrow setting; it does not establish current
  effects across PM work, other users or today's models. Lesson: observed
  completion and perceived acceleration can disagree.
- [METR, February 24 2026](https://metr.org/blog/2026-02-24-uplift-update/):
  the researchers describe later data as unreliable for estimating the current
  effect because participant/task selection and concurrent-agent time reporting
  changed. Lesson: frozen eligible tasks alone do not remove worker selection;
  active person-time must not double-count parallel work or model elapsed time.
- [Workday, January 14 2026](https://investor.workday.com/news-and-events/press-releases/news-details/2026/New-Workday-Research-Companies-Are-Leaving-AI-Gains-on-the-Table/default.aspx):
  a survey of 3,200 active AI users at large employers reports rework alongside
  perceived time savings. These are self-reported survey results, not a randomized
  causal comparison. Lesson: include review, corrections and follow-up rather
  than treating a faster draft as an end-to-end gain.
- [Fang et al., retail field experiments, arXiv v6](https://arxiv.org/abs/2510.12049v6):
  the June 29 2026 preprint reports varying short-term sales effects across seven
  retail workflows, including no detectable impact in some. The abstract reports
  heterogeneous consumer effects and post-purchase measures. This is preprint
  evidence in a retail deployment, not a PM labor benchmark. Lesson: the outcome
  and workflow matter; a task-time ratio should not replace customer outcomes.

## What the tool does

This v1 records declarations, balances a fixed eligible list, and audits
descriptive assignment-group accounting. It makes no inferential or causal
assessment. Unknown/yes spillover and other trial designs are refused rather
than hidden behind a validity badge. Hashes are change-detection aids, not
signatures or proof of when/why a seed was chosen.
