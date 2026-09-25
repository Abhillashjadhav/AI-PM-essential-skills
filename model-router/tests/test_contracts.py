"""Contract validation and state-machine guards."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from model_router.contracts import (  # noqa: E402
    Approval,
    CapacityEstimate,
    ContractError,
    CreditsState,
    InvalidTransition,
    JobState,
    OverrideReason,
    RouteDecision,
    SpendDecision,
    SpendEvidence,
    check_transition,
    parse_override_reason,
    utc_now,
)
from model_router.jsonschema_lite import load_schema, validate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RECORD = {
    "goal": "g", "scope": "s", "decisions": [{"title": "d", "status": "decided"}], "constraints": [], "components": [],
    "interfaces": [{"name": "f", "contract": "a -> b"}], "files": ["x.py"], "steps": [{"description": "do"}],
    "risks": [], "tests": [{"name": "t", "check": "f() == 1"}], "blocking_questions": [],
}


class TransitionGuards(unittest.TestCase):
    def test_only_manual_choice_leaves_awaiting_manual(self):
        with self.assertRaises(InvalidTransition):
            check_transition(JobState.AWAITING_MANUAL_MODEL, JobState.SELECTED)
        check_transition(JobState.AWAITING_MANUAL_MODEL, JobState.SELECTED, manual=True)

    def test_ready_requires_eligibility(self):
        for source in (JobState.SELECTED, JobState.PAUSED, JobState.WAITING_USAGE, JobState.BLOCKED_SPEND):
            with self.assertRaises(InvalidTransition):
                check_transition(source, JobState.READY)
            check_transition(source, JobState.READY, eligibility_passed=True)

    def test_only_ready_enters_dispatching(self):
        for state in JobState:
            if state is JobState.READY:
                check_transition(state, JobState.DISPATCHING)
            else:
                with self.assertRaises(InvalidTransition, msg=state):
                    check_transition(state, JobState.DISPATCHING)

    def test_uncertain_dispatch_goes_to_recovery_not_ready(self):
        with self.assertRaises(InvalidTransition):
            check_transition(JobState.DISPATCHING, JobState.READY, eligibility_passed=True)
        check_transition(JobState.DISPATCHING, JobState.RECOVERY_REQUIRED)
        with self.assertRaises(InvalidTransition):
            check_transition(JobState.RECOVERY_REQUIRED, JobState.READY, eligibility_passed=True)
        check_transition(JobState.RECOVERY_REQUIRED, JobState.READY, eligibility_passed=True, owner_confirmed_not_executed=True)
        with self.assertRaises(InvalidTransition):
            check_transition(JobState.RECOVERY_REQUIRED, JobState.PAUSED)
        check_transition(JobState.RECOVERY_REQUIRED, JobState.PAUSED, owner_confirmed_not_executed=True)

    def test_terminal_states_never_dispatch_again(self):
        for terminal in (JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED):
            for target in JobState:
                with self.assertRaises(InvalidTransition):
                    check_transition(terminal, target, manual=True, eligibility_passed=True, owner_confirmed_not_executed=True)


class RecordValidation(unittest.TestCase):
    def test_override_reason_never_invented(self):
        self.assertEqual(parse_override_reason(""), (OverrideReason.UNKNOWN, None))
        self.assertEqual(parse_override_reason(None), (OverrideReason.UNKNOWN, None))
        self.assertEqual(parse_override_reason("quality")[0], OverrideReason.ANSWER_QUALITY)
        self.assertEqual(parse_override_reason("new task")[0], OverrideReason.DIFFERENT_TASK)
        reason, text = parse_override_reason("it felt off somehow")
        self.assertEqual(reason, OverrideReason.UNKNOWN)
        self.assertEqual(text, "it felt off somehow")

    def test_spend_allowed_needs_evidence(self):
        with self.assertRaises(ContractError):
            SpendDecision("ALLOWED_INCLUDED_ONLY", [], [], "a", utc_now(), False).validate()
        with self.assertRaises(ContractError):
            SpendDecision("UNKNOWN", [], [], "a", utc_now(), False).validate()

    def test_screenshot_is_never_enforcement(self):
        with self.assertRaises(ContractError):
            SpendEvidence("e", "auto_reload_off", "acct", "screenshot", "enforced", utc_now(), None, "screenshot").validate()
        SpendEvidence("e", "auto_reload_off", "acct", "screenshot", "supporting", utc_now(), None, "screenshot").validate()

    def test_unreported_credits_carry_no_values(self):
        with self.assertRaises(ContractError):
            CreditsState(has_credits=False, unlimited=None, balance=None, reported=False).validate()
        self.assertIn("unknown", CreditsState(None, None, None, False).describe())

    def test_capacity_always_estimated_and_explained(self):
        with self.assertRaises(ContractError):
            CapacityEstimate("UNKNOWN", [], None, None, None, None, None, "m", "v", [], []).validate()
        with self.assertRaises(ContractError):
            CapacityEstimate("TIGHT", [], None, None, None, None, None, "m", "v", [], ["x"]).validate()
        with self.assertRaises(ContractError):
            CapacityEstimate("UNKNOWN", [], None, None, None, None, None, "m", "v", [], ["x"], label="guaranteed").validate()

    def test_route_decision_requires_rules_or_missing_binding(self):
        base = dict(id="r", request_id="q", thread_id="t", route_attempt_id="a", role="highest", candidate_id=None,
                    reasoning_effort=None, reasons=[], uncertainty=[], capacity_ref=None, manual=False)
        with self.assertRaises(ContractError):
            RouteDecision.from_dict(base | {"model_id": None, "rule_ids": ["RF"], "missing_binding": False})
        with self.assertRaises(ContractError):
            RouteDecision.from_dict(base | {"model_id": "m", "rule_ids": [], "missing_binding": False})
        RouteDecision.from_dict(base | {"model_id": None, "rule_ids": ["RF"], "missing_binding": True})

    def test_approval_binds_hash_and_human(self):
        with self.assertRaises(ContractError):
            Approval("a", "owner", "role_mapping", "x", "short", "approved", utc_now()).validate()
        with self.assertRaises(ContractError):
            Approval("a", "model", "role_mapping", "x", "0" * 64, "approved", utc_now()).validate()


class SchemaFiles(unittest.TestCase):
    def test_fixtures_validate(self):
        import json

        fixtures = ROOT / "fixtures"
        self.assertEqual(validate(json.loads((fixtures / "routing-cases.json").read_text()), load_schema("routing-cases.schema.json")), [])
        self.assertEqual(validate(json.loads((fixtures / "import-example.json").read_text()), load_schema("import.schema.json")), [])
        self.assertEqual(validate(RECORD, load_schema("architecture-record.schema.json")), [])

    def test_schema_rejects_invalid(self):
        broken = {k: v for k, v in RECORD.items() if k != "steps"} | {"goal": ""}
        errors = validate(broken, load_schema("architecture-record.schema.json"))
        self.assertTrue(any("steps" in e for e in errors))
        self.assertTrue(any("shorter" in e for e in errors))

    def test_architecture_record_contract_matches_schema(self):
        from model_router.contracts import ARCHITECTURE_REQUIRED_FIELDS

        self.assertEqual(set(load_schema("architecture-record.schema.json")["required"]), set(ARCHITECTURE_REQUIRED_FIELDS))


if __name__ == "__main__":
    unittest.main()
