#!/usr/bin/env python3
"""A fake `codex` CLI for offline protocol tests. Synthetic only.

Modes:
  fake_codex.py --version
  fake_codex.py app-server generate-json-schema --out DIR
  fake_codex.py app-server            (JSONL JSON-RPC over stdio)

Behaviour comes from $CODEX_HOME/fake-scenario.json (the router passes only a
minimal environment, so CODEX_HOME is the channel). Every message received is
appended to $CODEX_HOME/fake-log.jsonl so tests can assert what was, and was
not, sent. The environment variable *names* seen at startup are logged too.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA_FIXTURE = HERE.parents[1] / "fixtures" / "codex-schema-min"


HOME = Path(os.environ["CODEX_HOME"]) if os.environ.get("CODEX_HOME") else None


def load_scenario() -> dict:
    path = HOME / "fake-scenario.json" if HOME else None
    if path and path.is_file():
        return json.loads(path.read_text())
    return {}


SCENARIO = load_scenario()
LOG = str(HOME / "fake-log.jsonl") if HOME else None
STATE = {"threads": {}, "turn": 0}


def log(message: dict) -> None:
    if LOG:
        with open(LOG, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(message) + "\n")


def send(message: dict) -> None:
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def send_raw(text: str) -> None:
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def read_message() -> dict | None:
    line = sys.stdin.readline()
    if not line:
        return None
    message = json.loads(line)
    log(message)
    return message


def result(request_id, value) -> None:
    send({"id": request_id, "result": value})


def error(request_id, message, code=-32000, info=None) -> None:
    payload = {"code": code, "message": message}
    if info:
        payload["data"] = {"codexErrorInfo": info}
    send({"id": request_id, "error": payload})


def handle(message: dict) -> bool:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}
    if method == "initialized":
        return True
    if method == "initialize":
        result(request_id, {"userAgent": "fake-codex/0.0-test", "platformFamily": "unix", "platformOs": "linux", "codexHome": None})
    elif method == "account/read":
        account = SCENARIO.get("account", {"type": "chatgpt", "email": "owner@example.invalid", "planType": "plus"})
        result(request_id, {"account": account, "requiresOpenaiAuth": True})
    elif method == "config/read":
        result(request_id, {"config": SCENARIO.get("config", {"forced_login_method": "chatgpt"}), "origins": {}})
    elif method == "model/list":
        result(request_id, {"data": SCENARIO.get("models", [
            {"id": "fake-astra", "model": "fake-astra", "displayName": "Fake Astra", "description": "", "hidden": False,
             "isDefault": True, "defaultReasoningEffort": "high",
             "supportedReasoningEfforts": [{"reasoningEffort": "high", "description": ""}, {"reasoningEffort": "medium", "description": ""}]},
            {"id": "fake-sol", "model": "fake-sol", "displayName": "Fake Sol", "description": "", "hidden": False,
             "isDefault": False, "defaultReasoningEffort": "medium",
             "supportedReasoningEfforts": [{"reasoningEffort": "medium", "description": ""}]},
        ]), "nextCursor": None})
    elif method == "account/rateLimits/read":
        result(request_id, SCENARIO.get("rate_limits", {
            "rateLimits": {"limitId": "codex", "primary": {"usedPercent": 12, "windowDurationMins": 300, "resetsAt": 1790000000},
                            "credits": {"hasCredits": False, "unlimited": False, "balance": "0"}, "planType": "plus"},
            "ordinaryUsageAllowed": True,
        }))
    elif method == "thread/start":
        STATE["turn"] += 1
        thread_id = f"fake-thread-{STATE['turn']}"
        model = SCENARIO.get("thread_model_override") or params.get("model")
        STATE["threads"][thread_id] = {"model": model, "turns": []}
        result(request_id, {"thread": {"id": thread_id, "model": model, "turns": []}, "model": model, "reasoningEffort": None,
                            "cwd": params.get("cwd"), "approvalPolicy": params.get("approvalPolicy"), "sandbox": {"type": "readOnly"}, "modelProvider": "openai"})
    elif method == "thread/resume":
        thread = STATE["threads"].setdefault(params["threadId"], {"model": params.get("model"), "turns": []})
        result(request_id, {"thread": {"id": params["threadId"]}, "model": SCENARIO.get("resume_model") or thread["model"]})
    elif method == "thread/read":
        thread = STATE["threads"].get(params["threadId"], {"model": None, "turns": []})
        result(request_id, {"thread": {"id": params["threadId"], "model": thread["model"], "status": {"type": "idle"}, "turns": thread["turns"]}})
    elif method == "turn/start":
        return run_turn(request_id, params)
    elif method == "turn/interrupt":
        result(request_id, {})
        send({"method": "turn/completed", "params": {"threadId": params["threadId"], "turn": {"id": params["turnId"], "status": "interrupted", "items": []}}})
    elif request_id is not None:
        error(request_id, f"method not found: {method}", code=-32601)
    return True


def run_turn(request_id, params) -> bool:
    script = SCENARIO.get("turn", [{"kind": "delta", "text": "Hello "}, {"kind": "delta", "text": "from fake codex."}, {"kind": "completed", "status": "completed"}])
    if SCENARIO.get("turn_start_error"):
        error(request_id, SCENARIO["turn_start_error"], info=SCENARIO.get("turn_start_error_info"))
        return True
    STATE["turn"] += 1
    turn_id = f"fake-turn-{STATE['turn']}"
    thread = STATE["threads"].setdefault(params["threadId"], {"model": params.get("model"), "turns": []})
    record = {"id": turn_id, "status": "inProgress", "items": [
        {"type": "userMessage", "id": "u1", "clientId": params.get("clientUserMessageId"), "content": params.get("input")}]}
    thread["turns"].append(record)
    if SCENARIO.get("exit_after_turn_start_request"):
        record["status"] = "completed"
        record["items"].append({"type": "agentMessage", "id": "a1", "text": "ran before the crash"})
        sys.exit(3)
    result(request_id, {"turn": {"id": turn_id, "status": "inProgress", "items": []}})
    tid = params["threadId"]
    send({"method": "turn/started", "params": {"threadId": tid, "turn": {"id": turn_id, "status": "inProgress", "items": []}}})
    text = ""
    for step in script:
        kind = step["kind"]
        if kind == "delta":
            text += step["text"]
            send({"method": "item/agentMessage/delta", "params": {"threadId": tid, "turnId": turn_id, "itemId": "a1", "delta": step["text"]}})
        elif kind == "malformed":
            send_raw("{this is not json")
        elif kind == "other_thread_delta":
            send({"method": "item/agentMessage/delta", "params": {"threadId": "someone-else", "turnId": "x", "itemId": "z", "delta": "LEAK"}})
        elif kind == "error":
            send({"method": "error", "params": {"threadId": tid, "turnId": turn_id, "willRetry": step.get("will_retry", False),
                                                "error": {"message": step.get("text", "boom"), "codexErrorInfo": step.get("code")}}})
        elif kind == "warning":
            send({"method": "warning", "params": {"threadId": tid, "message": step.get("text", "careful")}})
        elif kind == "rerouted":
            send({"method": "model/rerouted", "params": {"threadId": tid, "turnId": turn_id, "fromModel": params.get("model"),
                                                         "toModel": step["to_model"], "reason": "highRiskCyberActivity"}})
        elif kind == "approval":
            send({"id": "srv-1", "method": step.get("method", "item/commandExecution/requestApproval"),
                  "params": {"threadId": tid, "turnId": turn_id, "itemId": "c1", "startedAtMs": 0,
                             "command": step.get("command"), "cwd": step.get("cwd"), "reason": step.get("reason")}})
            reply = read_message()
            decision = (reply or {}).get("result", {}) or {}
            send({"method": "item/completed", "params": {"threadId": tid, "turnId": turn_id, "completedAtMs": 0,
                                                         "item": {"type": "commandExecution", "id": "c1", "command": step.get("command"),
                                                                  "status": "declined" if decision.get("decision") != "accept" else "completed"}}})
        elif kind == "usage_update":
            send({"method": "account/rateLimits/updated", "params": {"rateLimits": {"limitId": "codex", "primary": {"usedPercent": 99}}}})
        elif kind == "exit":
            sys.exit(4)
        elif kind == "completed":
            record["status"] = step.get("status", "completed")
            record["items"].append({"type": "agentMessage", "id": "a1", "text": text})
            turn = {"id": turn_id, "status": record["status"], "items": []}
            if step.get("error"):
                turn["error"] = {"message": step["error"]}
            send({"method": "turn/completed", "params": {"threadId": tid, "turn": turn}})
    return True


def main(argv: list[str]) -> int:
    if argv[:1] == ["--version"]:
        print(SCENARIO.get("version", "codex-cli 0.0.0-fake"))
        return 0
    if argv[:2] == ["app-server", "generate-json-schema"]:
        out = Path(argv[argv.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SCHEMA_FIXTURE, out, dirs_exist_ok=True)
        if SCENARIO.get("schema_drop_method"):
            path = out / "ClientRequest.json"
            data = json.loads(path.read_text())
            data["oneOf"] = [v for v in data["oneOf"] if v["properties"]["method"]["enum"][0] != SCENARIO["schema_drop_method"]]
            path.write_text(json.dumps(data))
        return 0
    if argv[:1] == ["app-server"]:
        log({"startup_env_names": sorted(os.environ)})
        while True:
            message = read_message()
            if message is None:
                return 0
            handle(message)
    print(f"unsupported fake invocation: {argv}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
