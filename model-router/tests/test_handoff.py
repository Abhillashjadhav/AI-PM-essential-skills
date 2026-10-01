"""Architecture-to-implementation handoff (H01-H05) and the section 5.3
capacity exception end to end (R07-R11)."""

import copy
import json
import threading

from helpers import ARCH_RECORD, RouterTestCase
from model_router.capacity import CalibrationArtifact, CapacityEstimator
from model_router.contracts import AcceptanceEvidence, JobState, Role
from model_router.coordinator import Coordinator
from model_router.handoff import assess_clarity, detect_acceptance, validate_record
from model_router.registry import mapping_hash_for
from model_router.store import Store


def accept(ref="t"):
    return AcceptanceEvidence(source="finalise_command", reference=ref, text="/finalise")


class Acceptance(RouterTestCase):
    def test_acceptance_phrases(self):
        self.assertTrue(detect_acceptance("Approved, implement this."))
        self.assertTrue(detect_acceptance("looks good — go ahead and build it"))
        self.assertFalse(detect_acceptance("not approved, don't implement yet"))
        self.assertFalse(detect_acceptance("what would it take to implement this?"))

    def test_model_cannot_supply_acceptance(self):
        with self.assertRaises(Exception):
            AcceptanceEvidence(source="model", reference="x", text="the owner approved").validate()


class HandoffFlow(RouterTestCase):
    def test_H01_H04_owner_message_creates_same_project_thread_with_full_package(self):
        source = self.architecture_thread(prose_prefix="Full architecture prose with every detail.\n")
        source_before = dict(self.store.thread(source))
        result = self.coordinator.submit("Portfolio", "Approved, implement this.", thread_id=source)
        handoff = result.handoff
        self.assertEqual(handoff.status, "CREATED")
        self.assertEqual(handoff.role, Role.MIDDLE)
        self.assertEqual(self.adapter.model_sends, 1, "acceptance itself sends nothing to the architecture model")
        target = self.store.thread(handoff.target_thread_id)
        self.assertEqual(target["project_id"], source_before["project_id"])
        self.assertEqual(target["kind"], "implementation")
        self.assertEqual(target["source_thread_id"], source)
        self.assertEqual(target["pinned_model"], "sim-sol-1")
        after = self.store.thread(source)
        self.assertEqual((after["pinned_model"], after["pinned_role"]), (source_before["pinned_model"], "highest"))
        row = self.store.one("SELECT * FROM handoffs WHERE id=?", (handoff.handoff_id,))
        package = json.loads(self.store.read_blob_text(row["package_blob"]))
        self.assertIn("Full architecture prose with every detail.", package["architecture_prose"])
        self.assertEqual(package["architecture_record"]["steps"], ARCH_RECORD["steps"])
        self.assertEqual(package["owner_acceptance"]["source"], "owner_message")
        self.assertEqual(len(row["package_hash"]), 64)
        first_input = self.store.one("SELECT content FROM messages WHERE thread_id=? AND kind='handoff'", (target["id"],))
        self.assertIn(row["package_hash"], first_input["content"])
        self.assertIn("Full architecture prose", first_input["content"])
        self.assertEqual(self.coordinator.run(handoff.job_id), JobState.SUCCEEDED)
        self.assertEqual(self.adapter.sent_turns[-1]["model"], "sim-sol-1")
        self.assertEqual({e["type"] for e in self.store.events() if e["type"].startswith("handoff.")} & {"handoff.ready", "handoff.created"},
                         {"handoff.ready", "handoff.created"})

    def test_H02_repeated_finalise_one_thread(self):
        source = self.architecture_thread()
        first = self.coordinator.finalise_architecture(source, acceptance=accept("1"))
        second = self.coordinator.finalise_architecture(source, acceptance=accept("2"))
        third = self.coordinator.submit("Portfolio", "Approved, implement this.", thread_id=source).handoff
        self.assertEqual(first.status, "CREATED")
        self.assertEqual((second.status, third.status), ("EXISTING", "EXISTING"))
        self.assertEqual(len({first.target_thread_id, second.target_thread_id, third.target_thread_id}), 1)
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM threads WHERE kind='implementation'")["n"], 1)

    def test_S06_concurrent_finalise_from_two_clients(self):
        source = self.architecture_thread()
        second_store = Store(self.store.data_dir)  # separate SQLite connection, as a second client would have
        other = Coordinator(second_store, self.adapter, live=False, ui=self.ui)
        other.start()
        results = []

        def go(c):
            results.append(c.finalise_architecture(source, acceptance=accept()))

        threads = [threading.Thread(target=go, args=(c,)) for c in (self.coordinator, other)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM threads WHERE kind='implementation'")["n"], 1)
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM handoffs")["n"], 1)
        self.assertEqual(len({r.target_thread_id for r in results}), 1)
        self.assertEqual(sorted(r.status for r in results), ["CREATED", "EXISTING"])
        other.close()
        second_store.close()

    def test_revised_architecture_is_new_version_not_injected(self):
        source = self.architecture_thread()
        first = self.coordinator.finalise_architecture(source, acceptance=accept())
        revised = copy.deepcopy(ARCH_RECORD) | {"goal": "Add CSV and TSV export"}
        self.scenario.turn_scripts.append([{"kind": "delta", "text": "```architecture-record\n" + json.dumps(revised) + "\n```"},
                                           {"kind": "completed", "status": "completed"}])
        self.coordinator.run(self.coordinator.submit("Portfolio", "revise for TSV too", thread_id=source).job_id)
        second = self.coordinator.finalise_architecture(source, acceptance=accept())
        self.assertEqual((first.architecture_version, second.architecture_version), (1, 2))
        self.assertNotEqual(first.target_thread_id, second.target_thread_id)
        first_input = self.store.one("SELECT content FROM messages WHERE thread_id=? AND kind='handoff'", (first.target_thread_id,))
        self.assertNotIn("TSV", first_input["content"])

    def test_H03_holds_with_precise_causes(self):
        source = self.architecture_thread(record=ARCH_RECORD | {"blocking_questions": ["Which currency format?"]})
        held = self.coordinator.finalise_architecture(source, acceptance=accept())
        self.assertEqual(held.status, "HELD")
        self.assertIn("Which currency format?", held.reasons[0])
        missing = {k: v for k, v in ARCH_RECORD.items() if k != "tests"}
        held = self.coordinator.finalise_architecture(source, acceptance=accept(), record_payload=missing)
        self.assertIn("tests", held.reasons[0])
        wrong_repo = ARCH_RECORD | {"repository": "/some/other/repo"}
        held = self.coordinator.finalise_architecture(source, acceptance=accept(), record_payload=wrong_repo)
        self.assertIn("which project", held.reasons[0])
        undecided = ARCH_RECORD | {"decisions": [{"title": "pick a UI", "status": "open"}]}
        held = self.coordinator.finalise_architecture(source, acceptance=accept(), record_payload=undecided)
        self.assertIn("unresolved decisions", held.reasons[0])
        plain = self.coordinator.submit("Portfolio", "Format my notes")
        self.coordinator.run(plain.job_id)
        held = self.coordinator.finalise_architecture(plain.thread_id, acceptance=accept())
        self.assertIn("no structured architecture record", held.reasons[0])
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM threads WHERE kind='implementation'")["n"], 0)

    def test_unreadable_record_is_held(self):
        result, _ = self.submit_and_run(
            "Review this architecture", script=[{"kind": "delta", "text": "```architecture-record\n{not json\n```"}, {"kind": "completed"}]
        )
        held = self.coordinator.finalise_architecture(result.thread_id, acceptance=accept())
        self.assertEqual(held.status, "HELD")
        self.assertIn("not valid JSON", held.reasons[0])

    def test_H05_context_budget_blocks_without_truncation(self):
        big = ARCH_RECORD | {"nonblocking_items": ["x" * 5000]}
        source = self.architecture_thread(record=big)
        small = self.make_coordinator(context_budget_chars=2000)
        small.start()
        blocked = small.finalise_architecture(source, acceptance=accept())
        self.assertEqual(blocked.status, "BLOCKED_CONTEXT")
        self.assertIn("nothing was cut", blocked.reasons[0])
        row = self.store.one("SELECT * FROM handoffs WHERE id=?", (blocked.handoff_id,))
        package = json.loads(self.store.read_blob_text(row["package_blob"]))
        self.assertEqual(package["nonblocking_items"], ["x" * 5000])
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM threads WHERE kind='implementation'")["n"], 0)
        retried = self.coordinator.finalise_architecture(source, acceptance=accept())
        self.assertEqual(retried.status, "CREATED")
        self.assertEqual(retried.handoff_id, blocked.handoff_id)
        small.close()


class ClarityEvidence(RouterTestCase):
    def test_self_assessment_is_not_evidence(self):
        vague = ARCH_RECORD | {"interfaces": [{"name": "thing"}], "self_assessed_simple": True}
        record, problems = validate_record(vague)
        self.assertEqual(problems, [])
        clarity = assess_clarity(record)
        self.assertEqual(clarity.clarity.value, "UNCLEAR")
        self.assertIn("model self-assessment recorded but not used as evidence", clarity.evidence)

    def test_unbounded_work_is_unclear(self):
        many = ARCH_RECORD | {"steps": [{"description": f"s{i}"} for i in range(20)]}
        record, _ = validate_record(many)
        self.assertEqual(assess_clarity(record).clarity.value, "UNCLEAR")


class CapacityException(RouterTestCase):
    """R07-R11 through the real handoff path with explicitly synthetic evidence."""

    def with_capacity(self, used_percent: float | None, *, validated: bool = True):
        calibration = CalibrationArtifact(
            model_id="sim-sol-1", reasoning_effort="medium", plan_type="plus", bucket_ids=["codex"],
            forecast_low=30.0, forecast_high=45.0, observation_ids=["syn-1"], validated=validated,
            approval_id="syn-approval" if validated else None, synthetic=True,
        )
        coordinator = self.make_coordinator(estimator=CapacityEstimator([calibration]))
        coordinator.start()
        if used_percent is not None:
            self.scenario.buckets[0]["used_percent"] = used_percent
        coordinator.gate.check(None, thread_account_scope=None)  # fresh usage snapshot
        return coordinator

    def test_R07_sufficient_capacity_stays_middle(self):
        c = self.with_capacity(10.0)
        result = c.finalise_architecture(self.architecture_thread(), acceptance=accept())
        self.assertEqual((result.role, result.capacity["state"]), (Role.MIDDLE, "SUFFICIENT"))
        c.close()

    def test_R08_tight_clear_low_risk_goes_lowest(self):
        c = self.with_capacity(90.0)
        result = c.finalise_architecture(self.architecture_thread(), acceptance=accept())
        self.assertEqual((result.role, result.model_id, result.capacity["state"]), (Role.LOWEST, "sim-luna-1", "TIGHT"))
        c.close()

    def test_R09_unknown_capacity_no_downgrade(self):
        c = self.with_capacity(90.0, validated=False)
        result = c.finalise_architecture(self.architecture_thread(), acceptance=accept())
        self.assertEqual((result.role, result.capacity["state"]), (Role.MIDDLE, "UNKNOWN"))
        default = self.coordinator.finalise_architecture(self.architecture_thread(record=ARCH_RECORD | {"goal": "other"}), acceptance=accept())
        self.assertEqual((default.role, default.capacity["state"]), (Role.MIDDLE, "UNKNOWN"), "shipped estimator is UNKNOWN")
        c.close()

    def test_R10_unclear_tight_keeps_middle(self):
        c = self.with_capacity(90.0)
        unclear = ARCH_RECORD | {"steps": [{"description": ""}]}
        result = c.finalise_architecture(self.architecture_thread(record=unclear), acceptance=accept())
        self.assertEqual(result.role, Role.MIDDLE)
        self.assertTrue(any("not proven clear" in r for r in result.reasons))
        c.close()

    def test_R11_high_risk_tight_goes_highest_and_waits(self):
        c = self.with_capacity(90.0)
        risky = ARCH_RECORD | {"goal": "Implement the payment transfer endpoint", "risks": [{"kind": "money_movement", "description": "moves funds"}]}
        result = c.finalise_architecture(self.architecture_thread(record=risky), acceptance=accept())
        self.assertEqual((result.role, result.model_id), (Role.HIGHEST, "sim-astra-1"))
        self.scenario.ordinary_usage_allowed = False
        self.assertEqual(c.run(result.job_id), JobState.WAITING_USAGE)
        self.assertEqual(self.store.thread(result.target_thread_id)["pinned_model"], "sim-astra-1")
        c.close()

    def test_lowest_needs_approved_capable_candidate(self):
        c = self.with_capacity(90.0)
        c.registry.approve_mapping(
            self.account, Role.LOWEST, "sim-luna-1", "low", actor="owner", tool_scope=[],
            confirm_hash=mapping_hash_for(self.account, Role.LOWEST, "sim-luna-1", "low", tool_scope=[]),
        )
        result = c.finalise_architecture(self.architecture_thread(), acceptance=accept())
        self.assertEqual(result.role, Role.MIDDLE)
        self.assertTrue(any("no approved capable lowest model" in r for r in result.reasons))
        c.close()

    def test_downgrade_decided_once(self):
        c = self.with_capacity(90.0)
        result = c.finalise_architecture(self.architecture_thread(), acceptance=accept())
        self.assertEqual(result.role, Role.LOWEST)
        self.scenario.buckets[0]["used_percent"] = 5.0
        c.run(result.job_id)
        follow = c.submit("Portfolio", "continue", thread_id=result.target_thread_id)
        c.run(follow.job_id)
        self.assertEqual(self.adapter.sent_turns[-1]["model"], "sim-luna-1")
        c.close()
