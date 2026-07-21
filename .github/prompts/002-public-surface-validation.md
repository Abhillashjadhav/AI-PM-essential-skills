# Public-surface validation task

## Scope

Make the public repository surface accurate and evidence-backed without modifying existing AI-PM skills or removing ContextPort.

## Required evidence

- The root README identifies exactly four standalone AI Product Manager Claude Code skills and ContextPort as a separate toolkit.
- Installation uses the canonical `Abhillashjadhav/AI-PM-essential-skills` clone path.
- Public claims distinguish automated tests, structural validation, manual fixtures, recorded behavioural model runs, and unverified behavior.
- A dependency-free integrity script validates declared public paths and README references.
- GitHub Actions runs the integrity script and ContextPort unit tests.

## Boundaries

`VERIFIED`: repository files and deterministic command output.

`UNKNOWN`: live Claude Code behavior, external skill-library coverage, current model information, and real-export compatibility without approval.

`UNSUPPORTED`: ContextPort destination writes and other capabilities documented as fail-closed.

## Privacy

Use committed synthetic fixtures only. Do not access real exports, credentials, browser automation, or external assistant accounts.
