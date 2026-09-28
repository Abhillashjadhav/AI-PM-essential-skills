# Manual trigger and acceptance cases

No live model runs are recorded here.

FIRE: explicit requests to audit connector context cost or compare a CLI with an
MCP workflow. A proactive suggestion is appropriate only when irrelevant loaded
definitions are visible; deferred or unknown loading is insufficient.

NO-FIRE: connection debugging, installation, MCP migration, or a repeated
first-prompt check in the same session.

| Input | Expected behavior |
|---|---|
| Three connected servers; names visible, loading mode unknown | No asserted schema cost or savings; distinguish connection inventory from injected text. |
| Explicit audit, tool search enabled, schemas deferred | Count only observed loaded text; do not charge every advertised schema up front. |
| Explicit audit, full schemas visible, no tokenizer | Label supported estimates or mark cost unknown; visibility is not measurement. |
| Same task using a CLI | Include relevant help/output context, authorization and workflow coverage in the comparison. |
| First prompt with irrelevant full definitions visibly loaded | One short suggestion, then continue the task; no invented percentage and no disabling. |
