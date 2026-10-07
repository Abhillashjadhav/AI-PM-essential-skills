# Local Beacon integration

The shared adapter is an optional, commit-pinned Python package. It records run
identity, lifecycle and exit status. It never receives CLI arguments, conversation
exports, prompts, judgments, output bodies or credentials from these integrations.

## Setup

Install the local collector with the LinkedIn OS `tools/beacon/install-macos.sh`
helper. Then use the **same virtualenv Python as each workflow**:

```sh
python scripts/install_beacon_adapter.py
```

For a new environment, first run `python3 -m venv .venv` and use
`.venv/bin/python scripts/install_beacon_adapter.py`. Installing into the separate
collector helper environment does not install into a workflow's Python environment.
Python 3.11 or newer is required for the optional adapter; existing tools remain
usable without it. No TypeScript or paid API is added.

## Automatic coverage

| Entry point | Capture |
| --- | --- |
| ContextPort `contextport.main`, console script and direct script | Start, end and existing return code |
| PM Verifier `pm_verifier.cli.main`, console script and module | Start, end and existing gate return code |
| Additional executable skill commands | Use `python scripts/beacon_run.py -- COMMAND ARGS...` |
| Prose-only skills invoked by an external agent | Not intrinsically captured by this repository; register that agent's runner |

Coverage does not imply unregistered commands are observed. The adapter uses the
current working directory as project scope for installed CLIs; run from the target
project. It reuses an inherited bridge run ID for child work. Existing schemas,
evaluation gates, explicit approvals, content handling and export policy remain
authoritative. This change does not inspect real user exports.

Delivery waits for the Mac installer's local-only verification receipt. Until then,
events queue privately. A missing package, collector outage or recording failure
must not turn a passing task into a failure. Reports are explicit commands only:
`python -m workflow_beacon status`. Task success and capture evidence are separate.

Rollback: uninstall `workflow-beacon` from that runtime or revert the integration
commit. Preserve private history. Mac capture and installed console-script behavior
still require the local handoff; cloud checks use only synthetic data.
