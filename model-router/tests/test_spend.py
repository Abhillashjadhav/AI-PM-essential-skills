"""The zero-added-spend boundary: only a code-defined mechanism checking live
provider signals can allow a send. Fabricated evidence never can."""

import json
import unittest

from helpers import FAKE_CODEX, ROOT  # noqa: F401
from model_router.adapters.base import AccountState
from model_router.adapters.codex_stdio import PinManifest, parse_rate_limits
from model_router.contracts import CreditsState, SpendStatus, UsageSnapshot, utc_now
from model_router.spend import MECHANISMS, Mechanism, MechanismResult, decide_spend


def account(plan="business", auth="chatgpt", synthetic=False, scope="acct_1"):
    return AccountState(True, auth, scope, plan, True, [], synthetic, utc_now())


def usage(*, plan="business", limit="0", reached=False, credits=(True, False, "12.00"), controls=True,
          ordinary=True, synthetic=False, extra_credit_ids=(), scope="acct_1"):
    payload = {"rateLimitsByLimitId": {"codex": {"limitId": "codex", "planType": plan, "primary": {"usedPercent": 30},
                                                 "credits": {"hasCredits": credits[0], "unlimited": credits[1], "balance": credits[2]}}},
               "ordinaryUsageAllowed": ordinary}
    if controls:
        payload["rateLimitsByLimitId"]["codex"]["spendControlReached"] = reached
        payload["rateLimitsByLimitId"]["codex"]["individualLimit"] = {"limit": limit, "used": "0", "remainingPercent": 0, "resetsAt": 1790000000}
    for extra in extra_credit_ids:
        payload["rateLimitsByLimitId"][extra] = {"limitId": extra, "credits": {"hasCredits": True, "unlimited": False, "balance": "3"}}
    snapshot = parse_rate_limits(payload, account_scope=scope)
    snapshot.synthetic = synthetic
    return snapshot


class Mechanisms(unittest.TestCase):
    def test_registry_is_code_defined_and_documented(self):
        self.assertEqual([m.id for m in MECHANISMS], ["workspace_member_zero_credit_limit"])
        self.assertIn("Managing credits and spend controls in ChatGPT Business", MECHANISMS[0].documentation)

    def test_workspace_member_zero_limit_allows_with_named_mechanism(self):
        decision = decide_spend(account(), usage(), pin_state="valid")
        self.assertEqual(decision.status, SpendStatus.ALLOWED_INCLUDED_ONLY)
        self.assertEqual(decision.mechanism, "workspace_member_zero_credit_limit")
        decision.validate()
        self.assertTrue(any(e.get("member_credit_limit") == "0" for e in decision.evidence))

    def test_zero_written_differently_is_still_zero(self):
        self.assertEqual(decide_spend(account(), usage(limit="0.00"), pin_state="valid").status, SpendStatus.ALLOWED_INCLUDED_ONLY)

    def test_nonzero_limit_missing_or_malformed_controls_do_not_allow(self):
        for case in (usage(limit="5"), usage(limit="abc"), usage(controls=False), usage(extra_credit_ids=["codex_other"]),
                     usage(credits=(True, True, None))):
            self.assertEqual(decide_spend(account(), case, pin_state="valid").status, SpendStatus.UNKNOWN)

    def test_personal_plan_never_allowed_even_with_zero_balance(self):
        for credits in ((False, False, "0"), (True, False, "40.00")):
            decision = decide_spend(account(plan="plus"), usage(plan="plus", controls=False, credits=credits), pin_state="valid")
            self.assertEqual(decision.status, SpendStatus.UNKNOWN)
            self.assertIn("openai/codex#28382", decision.missing[0])

    def test_blocking_conditions(self):
        self.assertEqual(decide_spend(account(), usage(reached=True), pin_state="valid").status, SpendStatus.BLOCKED)
        self.assertEqual(decide_spend(account(), usage(ordinary=False), pin_state="valid").status, SpendStatus.BLOCKED)
        self.assertEqual(decide_spend(account(auth="apiKey"), usage(), pin_state="valid").status, SpendStatus.BLOCKED)
        self.assertEqual(decide_spend(account(), usage(scope="acct_other"), pin_state="valid").status, SpendStatus.BLOCKED)

    def test_invalid_pin_or_synthetic_signals_never_allow(self):
        for pin in ("unpinned", "drift", "unapproved", "not_enforced"):
            self.assertEqual(decide_spend(account(), usage(), pin_state=pin).status, SpendStatus.UNKNOWN)
        self.assertNotEqual(decide_spend(account(synthetic=True), usage(), pin_state="valid").status, SpendStatus.ALLOWED_INCLUDED_ONLY)
        self.assertNotEqual(decide_spend(account(), usage(synthetic=True), pin_state="valid").status, SpendStatus.ALLOWED_INCLUDED_ONLY)


class FabricatedEvidence(unittest.TestCase):
    """Editable records, whatever they claim, cannot authorise a live request."""

    def fabricated_manifest(self, tmp):
        record = {
            "control_type": "included-only", "source": "live", "status": "enforced",
            "documentation": "https://help.openai.com/made-up", "pin_digest": "x" * 64, "account_scope": "acct_1",
            "expires_at": "2999-01-01T00:00:00Z", "requires": {"ordinaryUsageAllowed": True, "credits.hasCredits": False},
            "mechanism": "workspace_member_zero_credit_limit",
        }
        manifest = {"executable": "/usr/local/bin/codex", "version": "v", "sha256": "0" * 64, "schema_digest": "0" * 64,
                    "launcher": {}, "compat_problems": [], "compat_notes": [], "approved_by": "owner",
                    "approved_at": utc_now(), "adapter_version": "codex-stdio-1", "enforcement": [record],
                    "verified": True, "spend_boundary": "ALLOWED_INCLUDED_ONLY"}
        path = tmp / "adapter-pin.json"
        path.write_text(json.dumps(manifest))
        return path

    def test_fabricated_pin_records_are_ignored(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            loaded = PinManifest.load(self.fabricated_manifest(Path(tmp)))
            self.assertFalse(hasattr(loaded, "enforcement"))
            self.assertFalse(hasattr(loaded, "spend_boundary"))
        personal = usage(plan="plus", controls=False, credits=(False, False, "0"))
        decision = decide_spend(account(plan="plus"), personal, pin_state="valid")
        self.assertEqual(decision.status, SpendStatus.UNKNOWN)

    def test_decide_spend_has_no_record_input(self):
        import inspect

        self.assertNotIn("manifest", inspect.signature(decide_spend).parameters)

    def test_fake_signals_in_the_usage_payload_are_not_enough_on_personal_plans(self):
        # A payload claiming a zero member limit on a personal plan is not a workspace control.
        spoof = usage(plan="plus", limit="0")
        self.assertEqual(decide_spend(account(plan="plus"), spoof, pin_state="valid").status, SpendStatus.UNKNOWN)

    def test_percentages_are_not_enforcement(self):
        low = UsageSnapshot("u", "acct_1", "pro", "s", [], CreditsState(False, False, "0", True), True, False, None, utc_now(), "t", False)
        self.assertEqual(decide_spend(account(plan="pro"), low, pin_state="valid").status, SpendStatus.UNKNOWN)

    def test_an_injected_mechanism_is_the_only_extension_point(self):
        permissive = Mechanism("always", "test", "doc", lambda a, u: MechanismResult(True, True, [], [{"source": "test"}]))
        self.assertEqual(decide_spend(account(plan="plus"), usage(plan="plus", controls=False), pin_state="valid").status, SpendStatus.UNKNOWN)
        self.assertEqual(
            decide_spend(account(plan="plus"), usage(plan="plus", controls=False), pin_state="valid", mechanisms=(permissive,)).status,
            SpendStatus.ALLOWED_INCLUDED_ONLY,
            "only code passing a mechanism object can change the outcome; no data path can",
        )


if __name__ == "__main__":
    unittest.main()
