# Trimmed App Server schema fixture

A small subset, trimmed down to method names and property names, of the JSON Schema that `codex app-server generate-json-schema` emits. It was taken from the openai/codex repository (Apache-2.0) at commit `bd3d4d1436bb41b94fd38ba9bdd34d74524e7a9f`, path `codex-rs/app-server-protocol/schema/json/`.

It exists so the offline tests can exercise `check_schema_compat` and the fake App Server's `generate-json-schema` mode. It isn't evidence about the owner's installed Codex version. The reserved method `account/rateLimitResetCredit/consume` is included on purpose, so tests can assert that the router never calls it.
