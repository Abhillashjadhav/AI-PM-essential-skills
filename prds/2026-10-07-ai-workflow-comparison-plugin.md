# AI Workflow Comparison: installed plugin contract

## Outcome

A PM can ask the installed `pm-tactical` plugin to compare an AI-assisted
workflow with a standard workflow, freeze eligible task assignments, obtain
a local results template, and audit supplied observations at the common
cutoff. The skill guides collection before calculation. A separate UI is not
required.

The public name is AI Workflow Comparison and the invocable skill name is
`ai-workflow-comparison`. Existing folder paths, CLI filename and JSON schema
remain compatible. This contract extends the earlier implementation and
publication specifications without changing their accounting design.

## Acceptance

1. Marketplace and plugin descriptions, public entry points and runtime labels
   use comparison branding. Existing research and other products retain their
   own methodological terminology.
2. Frontmatter discovery and `/pm-tactical:ai-workflow-comparison` match the
   official host naming contract. The skill references bundled files with
   `${CLAUDE_SKILL_DIR}` and never requires the repository checkout as cwd.
3. The first interaction collects the binary outcome, eligibility, strata,
   window, seed, independence rationale and human-time scope. Missing facts
   stay unresolved; examples never become observations.
4. The assistant writes outputs only to new paths in the user's chosen local
   workspace. Records are supplied or manually collected; the tool does not
   run models, observe customers or import the optional effort log.
5. An offline copied-plugin test covers discovery metadata and bundled files,
   an unrelated cwd with spaces, freeze/template/audit, missing observations
   and coverage, mature cutoff and overwrite refusal. It verifies descriptive
   counts and measured effort, without claiming native-host execution.
6. Existing 27 core tests, nine CLI UAT checks, 24 repository gate tests,
   integrity and skill lint remain successful. Save exact commands, outputs,
   source diff, commit metadata and preservation evidence.

## Evidence limits and dependencies

Python 3.11+ and its standard library run the bundled accounting tool. Claude
Code host access has separate eligibility and permissions; the tool's lack
of model calls does not make host usage free. Publication of a revision that
contains this skill is required before a public installation can expose it.
No native-host installation or live trigger quality is claimed by offline
checks. Issue #94 tracks the plugin; issues #95 and #96 are optional UI/video
follow-ups.
