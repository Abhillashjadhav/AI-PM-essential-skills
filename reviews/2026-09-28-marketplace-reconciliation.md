# Review reconciliation and implemented scope

> Status update (2026-09-30): The 50/52 catalog replay and unresolved D4/D2
> statements below describe this historical run. Merged PR #79 superseded
> them on main `316f02050650a3da60342a600b26ae1b99adf412`. Fresh local
> catalog replay exits 0 with 55/55 revision and 31/31 metadata checks;
> [catalog follow-through](2026-09-28-catalog-followthrough.md) records the
> integrated repair. Later grader drafts and live accuracy remain unverified.

Baseline: `60b61efb1294c10045f6af11ff07ce5aea5bb03b`.
The owner authorized implementation after an independent review.

| Finding | Resolution in this repair |
|---|---|
| F01: boolean/number membership | Integrate #57; add float and full-release controls. |
| F02: validation false passes | Integrate #59; retain malformed-metadata, duplicate-name and quoted-path regressions. |
| F03: state isolation | Document fresh processes versus trusted adapter state reset. No new isolation promise. |
| F04: graph contract versus runner | Separate static declarations from synthetic runtime behavior and reviewer independence. |
| F05: catalogue drift | List all eight plugins, add pm-tactical README, update contributor context and retired routes. |
| F06: evidence claims | Add per-product evidence table, manual kill-criteria cases and honest test descriptions. Broader CI coverage follows in a separate phase. |
| F07: stale/unsupported guidance | Reuse #58/#62; remove universal context cutoffs, account for deferred tools, recheck MCP sources and remove the expired countdown. |
| F08: loop state/publication | Rescan open issues by ID; preserve overflow, pause on pending PRs, verify before publication and define host prerequisites. This is a template, not an implemented scheduler. |
| F09: grader status | Reconcile shipped-code, probe, version and exit-test claims against current main. Preserve D4/D2 as unresolved implementation defects. |
| F10: PMOS authority | Document declared approval and re-binding limits. The existing tamper test checks PMOS edits without re-binding. |
| F11: attribution/writing | Restore Drew Breunig credit and remove unsupported universal claims. No claim of universal originality. |

## Corrections to the independent review

- #48's merge-base diff has four changed files, 583 insertions and 52 deletions.
  The claimed 37,949 deletions came from comparing whole branch tips; it is not
  the change that a normal merge would apply. The older branch still needs review.
- #57 is already an ancestor of #64. Preserving ancestry does not duplicate
  that change on merge. This repair retains the original commits.
- #55 is an ancestor of #56, and #60 and #61 extend #56 separately. The
  current #54 head is not an ancestor of #55. Status corrections can describe
  current main without choosing or combining those later implementation heads.
- The quoted-path bug skips syntax checks and skill-impact detection. The old
  PR gate did not invoke skill lint through `impacted_skills()` in the first place.
- Removal of a credit is observable; the commit alone does not establish intent.
- Reading public PR metadata or CI results does not inherently require push access.

## Observed checks

- Repository integrity PASS; 8 plugins, 3 standalone skills, 18 README files.
- All 16 skills pass the real PyYAML metadata linter.
- Graph contract checker PASS; sample returns AWAITING_HUMAN_APPROVAL and no
  external actions. Runtime scope remains as documented.
- Catalog replay: 3/3 approved, 12/12 fault, 50/52 revision and 25/25 metadata
  expectations match; 30/30 saved candidates accepted. The command exits 1.
  Failures: `optional-description-conflict-withholds-field` and
  `unapproved-authority-withholds-not-blocks`, both consistent with D4.
- Catalog coverage extraction: 45 inputs, 43 issue codes; mapping remains
  author judgment, not independent proof of contract completeness.

No live marketplace installation, external-service trial, grader exit interview,
independent human adjudication, deployment, merge or release was performed.

Technical sources were rechecked on 2026-09-28 and are linked in the relevant
skills: Claude Code MCP documentation, versioned MCP 2026-07-28 changelog and
transport documentation, MCP feature lifecycle, and Breunig's original taxonomy.
