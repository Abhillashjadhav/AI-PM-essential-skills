"""Local Jev setup and a classifier-only pilot; these never start Codex."""
from __future__ import annotations

import getpass
import json
import os
import sys
import time
from pathlib import Path

from .classifier import ClassifierInput, classify
from .jev import JevClient, JevUnavailable
from .plugin_classifier import combined_classifier
from .policy import required_role
from .store import default_data_dir

# Public synthetic prompts only. Live private exports are not part of this pilot.
CASES = (
    ("architecture", "Review the architecture for my reporting application.", "highest"),
    ("ordinary code", "Implement the CSV export per the agreed architecture.", "middle"),
    ("routine notes", "Format my private meeting notes into bullet points.", "lowest"),
    ("resume", "Score my resume against the product manager job description.", "highest"),
    ("risky code", "Implement a bank transfer endpoint, keeping payment amounts consistent.", "highest"),
    ("literal extraction", "Extract the dates and employers from this resume.", "lowest"),
)


def _print(value):
    print(json.dumps(value, indent=2, sort_keys=True))


def command(args) -> int:
    data_dir = Path(args.data_dir).expanduser() if args.data_dir else default_data_dir()
    pilot = JevClient(data_dir)
    try:
        if args.jev_action == "status":
            _print(pilot.status())
            return 0
        if args.jev_action == "disable":
            pilot.disable()
            print("Jev disabled. Existing routing rules and pinned GPT chats are unchanged.")
            return 0
        if args.jev_action == "setup":
            return setup(pilot)
        if args.jev_action == "pilot":
            return run_pilot(pilot)
    except (JevUnavailable, OSError, ValueError, EOFError, KeyboardInterrupt) as exc:
        reason = str(exc) if isinstance(exc, JevUnavailable) else "setup interrupted or invalid input"
        print(f"Jev: {reason}. No automatic retry; routing uses the local rules.", file=sys.stderr)
        return 1
    return 2


def setup(pilot: JevClient) -> int:
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        print("Run `router.py jev setup` in your own interactive terminal. Never paste a key into chat.")
        return 2
    print("This enables TypeSafe Jev for first-prompt classification; GPT still does the work.")
    print("Jev receives the new task text. It does not receive files, chat history or Codex credentials.")
    print("In the TypeSafe billing page, confirm that you have ONLY free promotional/monthly credits,")
    print("auto-recharge is OFF, and NO payment method is saved. Nothing here changes those settings.")
    answer = input("Are all three statements true right now? Type yes to continue: ").strip().lower()
    if answer != "yes":
        pilot.disable()
        print("Jev remains off; local rules are available.")
        return 1
    key = os.environ.get("TYPESAFE_API_KEY")
    if key is None:
        try:
            key = pilot._key()
            print("Reusing the private key already saved on this computer.")
        except JevUnavailable:
            key = getpass.getpass("TypeSafe API key (hidden; saved locally with owner-only permissions): ").strip()
    pilot.configure(key=key, free_only=True, auto_recharge_off=True, no_payment_method=True)
    print("Enabled. TypeSafe enforces the free-credit limit; there is no local spending cap.")
    print("Credit/billing errors stop Jev calls; local routing rules take over. No automatic retries.")
    print("This cannot observe billing changes or other clients. Re-enable after a stop with `jev setup`.")
    print("Next: python3 model-router/router.py jev pilot   (six public example prompts; no GPT calls)")
    _print(pilot.status())
    return 0


def run_pilot(pilot: JevClient) -> int:
    """Six bounded classifications; no GPT, scheduler, real conversations or retries."""
    status = pilot.status()
    if not status.get("enabled"):
        _print({"sent": 0, "blocked": status.get("reason"), "next": "router.py jev setup"})
        return 1
    rows = []
    for case_id, prompt, expected in CASES:
        started = time.monotonic()
        try:
            answer = pilot(prompt)
        except JevUnavailable as exc:
            _print({"completed": len(rows), "stopped": str(exc), "cases": rows,
                    "gpt_calls": 0, "note": "The failed attempt may have consumed credit. No retry was made."})
            return 1
        # The network result is reused; combined_classifier must NOT send again.
        routed = combined_classifier(lambda _: answer)(ClassifierInput(text=prompt))
        role = required_role(routed).role.value
        rows.append({"case": case_id, "expected": expected,
                     "rules_only": required_role(classify(ClassifierInput(text=prompt))).role.value,
                     "jev_kind": answer["task_kind"], "combined_role": role,
                     "passed": role == expected,
                     "seconds": round(time.monotonic() - started, 4)})
    _print({"completed": len(rows), "passed": sum(r["passed"] for r in rows), "cases": rows,
            "gpt_calls": 0, "status": pilot.status(),
            "note": "Connectivity/safety smoke test, not proof of 95% real-task accuracy. No model mappings promoted."})
    return 0 if all(r["passed"] for r in rows) else 1
