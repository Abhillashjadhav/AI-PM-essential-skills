"""Eligibility, zero-added-spend and account gates (B01-B08), queueing and
cancellation (B05, S07), capability failures (I03)."""

from helpers import RouterTestCase
from model_router.contracts import JobState, SpendStatus


class AuthAndSpend(RouterTestCase):
    def assert_no_send(self, state, expected):
        self.assertEqual(state, expected)
        self.assertEqual(self.adapter.model_sends, 0)
        self.assertFalse(any(name == "create_thread" for name, _ in self.adapter.calls))

    def test_B01_api_key_auth_blocks(self):
        self.scenario.auth_mode = "apiKey"
        _, state = self.submit_and_run("Format my notes")
        self.assert_no_send(state, JobState.BLOCKED_AUTH)
        self.assertTrue(any("only ChatGPT sign-in" in n for n in self.ui.notices))

    def test_B01_unknown_auth_blocks(self):
        result = self.coordinator.submit("Portfolio", "Format my notes")
        self.scenario.auth_mode = None
        self.assert_no_send(self.coordinator.run(result.job_id), JobState.BLOCKED_AUTH)

    def test_B01_incompatible_config_blocks(self):
        self.scenario.config_ok = False
        self.scenario.config_problems = ["model_provider override 'azure' is not allowed"]
        _, state = self.submit_and_run("Format my notes")
        self.assert_no_send(state, JobState.BLOCKED_AUTH)

    def test_B02_unknown_spend_blocks_with_missing_evidence(self):
        self.scenario.spend_status = SpendStatus.UNKNOWN
        result, state = self.submit_and_run("Format my notes")
        self.assert_no_send(state, JobState.BLOCKED_SPEND)
        self.assertIn("UNKNOWN", self.store.job(result.job_id)["blocker"])

    def test_B08_synthetic_spend_cannot_authorise_live_dispatch(self):
        live = self.make_coordinator()
        live.live = True
        live.gate.live = True
        live.start()
        result = live.submit("Portfolio", "Format my notes", synthetic=False)
        state = live.run(result.job_id)
        self.assert_no_send(state, JobState.BLOCKED_SPEND)
        self.assertIn("simulated", self.store.job(result.job_id)["blocker"])
        live.close()

    def test_B08_other_accounts_thread_is_not_resumed(self):
        result, state = self.submit_and_run("Format my notes")
        self.assertEqual(state, JobState.SUCCEEDED)
        self.scenario.account_id = "someone-else"
        follow, state = self.submit_and_run("more", thread_id=result.thread_id)
        self.assertEqual(state, JobState.BLOCKED_AUTH)
        self.assertEqual(self.adapter.model_sends, 1)
        self.assertTrue(self.events("spend.evidence_invalidated"), "B03: account change invalidates evidence")

    def test_B03_change_after_startup_is_rechecked_before_send(self):
        result = self.coordinator.submit("Portfolio", "Format my notes")
        self.scenario.spend_status = SpendStatus.BLOCKED  # changed after the startup check
        self.assertEqual(self.coordinator.run(result.job_id), JobState.BLOCKED_SPEND)
        self.assertEqual(self.adapter.model_sends, 0)
        reads = [name for name, _ in self.adapter.calls if name in {"read_account", "read_usage", "check_spend_boundary"}]
        self.assertGreaterEqual(reads.count("check_spend_boundary"), 1)

    def test_B03_credit_transition_invalidates_evidence(self):
        self.submit_and_run("Format my notes")
        self.scenario.credits = {"has_credits": True, "unlimited": False, "balance": "5"}
        self.submit_and_run("Format more notes")
        self.assertTrue(any(e["payload"]["reason"] == "reported limit or credit transition" for e in self.events("spend.evidence_invalidated")))

    def test_B04_absent_credit_and_bucket_fields_are_unknown(self):
        self.scenario.credits = None
        self.scenario.buckets = []
        self.scenario.ordinary_usage_allowed = None
        usage = self.adapter.read_usage()
        self.assertFalse(usage.credits.reported)
        self.assertIsNone(usage.credits.has_credits)
        self.assertIsNone(usage.included_usage_available())
        _, state = self.submit_and_run("Format my notes")
        self.assertEqual(state, JobState.SUCCEEDED, "unknown capacity alone does not block (spend is simulated-allowed)")
        note = self.events("eligibility.checked")[-1]["payload"]["notes"]
        self.assertTrue(any("unknown, not unlimited" in n for n in note))

    def test_B06_reset_offer_is_never_redeemed(self):
        self.scenario.reset_offers = 2
        self.scenario.ordinary_usage_allowed = False
        _, state = self.submit_and_run("Format my notes")
        self.assertEqual(state, JobState.WAITING_USAGE)
        self.assertFalse(any("reset" in name.lower() or "consume" in name.lower() for name, _ in self.adapter.calls))


class QueueAndResume(RouterTestCase):
    def test_B05_exhausted_then_restored_resumes_same_model(self):
        self.scenario.ordinary_usage_allowed = False
        self.scenario.buckets[0]["resets_at"] = "2026-09-26T00:00:00Z"
        result, state = self.submit_and_run("Implement the CSV import per the agreed architecture")
        self.assertEqual(state, JobState.WAITING_USAGE)
        self.assertEqual(self.store.job(result.job_id)["next_check_at"], "2026-09-26T00:00:00Z")
        self.assertTrue(any("Work is saved" in n for n in self.ui.notices))
        self.assertEqual(self.coordinator.wake(), [(result.job_id, JobState.WAITING_USAGE)], "a due time alone proves nothing")
        self.assertEqual(self.adapter.model_sends, 0)
        self.scenario.ordinary_usage_allowed = True
        self.assertEqual(self.coordinator.wake(), [(result.job_id, JobState.SUCCEEDED)])
        self.assertEqual(self.adapter.sent_turns[-1]["model"], "sim-sol-1")

    def test_B05_mid_turn_exhaustion_checkpoints_then_continues(self):
        script = [
            {"kind": "delta", "text": "Step 1 done. "},
            {"kind": "error", "text": "usage limit reached", "code": "usageLimitExceeded"},
            {"kind": "completed", "status": "failed"},
        ]
        result, state = self.submit_and_run("Implement the CSV import per the agreed architecture", script=script)
        self.assertEqual(state, JobState.PAUSED)
        checkpoint = self.store.one("SELECT payload FROM checkpoints WHERE job_id=?", (result.job_id,))
        self.assertIsNotNone(checkpoint)
        partial = self.store.one("SELECT kind, complete, content FROM messages WHERE thread_id=? AND role='assistant'", (result.thread_id,))
        self.assertEqual((partial["kind"], partial["complete"]), ("partial", 0))
        self.assertEqual(partial["content"], "Step 1 done. ")
        self.assertEqual([(result.job_id, JobState.SUCCEEDED)], self.coordinator.wake())
        continuation = self.adapter.sent_turns[-1]
        self.assertIn("Continue the interrupted task from this saved checkpoint", continuation["text"])
        self.assertEqual(continuation["model"], "sim-sol-1")
        dispatches = self.store.all("SELECT dispatch_id FROM dispatches WHERE job_id=?", (result.job_id,))
        self.assertEqual(len({d["dispatch_id"] for d in dispatches}), 2, "continuation is a separately identified turn")

    def test_S07_cancelled_queue_never_resumes(self):
        self.scenario.ordinary_usage_allowed = False
        result, _ = self.submit_and_run("Format my notes")
        self.assertEqual(self.coordinator.cancel(result.job_id), JobState.CANCELLED)
        self.scenario.ordinary_usage_allowed = True
        self.assertEqual(self.coordinator.wake(), [])
        self.assertEqual(self.coordinator.run(result.job_id), JobState.CANCELLED)
        self.assertEqual(self.adapter.model_sends, 0)

    def test_foreground_before_evaluation(self):
        self.scenario.ordinary_usage_allowed = False
        evaluation = self.coordinator.create_evaluation_job("Portfolio", "sim-sol-1", "eval prompt", run_id="evr_x")
        self.coordinator.run(evaluation["job_id"])
        user, _ = self.submit_and_run("Format my notes")
        self.scenario.ordinary_usage_allowed = True
        order = [job for job, _ in self.coordinator.wake()]
        self.assertEqual(order, [user.job_id, evaluation["job_id"]])


class Capabilities(RouterTestCase):
    def test_B07_unavailable_model_keeps_pin_and_blocks(self):
        result, _ = self.submit_and_run("Format my notes")
        self.scenario.models = [m for m in self.scenario.models if m.model_id != "sim-luna-1"]
        _, state = self.submit_and_run("again", thread_id=result.thread_id)
        self.assertEqual(state, JobState.BLOCKED_CAPABILITY)
        self.assertEqual(self.store.thread(result.thread_id)["pinned_model"], "sim-luna-1")
        self.assertEqual(self.adapter.model_sends, 1)
        self.assertTrue(self.events("model.unavailable"))

    def test_B07_provider_reroute_is_reported_not_hidden(self):
        script = [
            {"kind": "delta", "text": "partial "},
            {"kind": "rerouted", "to_model": "sim-other"},
            {"kind": "completed", "status": "interrupted"},
        ]
        result, state = self.submit_and_run("Format my notes", script=script)
        self.assertEqual(state, JobState.FAILED)
        dispatch = self.store.one("SELECT * FROM dispatches WHERE job_id=?", (result.job_id,))
        self.assertEqual((dispatch["requested_model"], dispatch["observed_model"]), ("sim-luna-1", "sim-other"))
        self.assertEqual(self.store.thread(result.thread_id)["pinned_model"], "sim-luna-1")
        self.assertTrue(any(name == "interrupt_turn" for name, _ in self.adapter.calls))
        self.assertTrue(any("rerouted" in n for n in self.ui.notices))
        message = self.store.one("SELECT kind, content FROM messages WHERE thread_id=? AND role='assistant'", (result.thread_id,))
        self.assertEqual((message["kind"], message["content"]), ("partial", "partial "))

    def test_I03_missing_search_tool_is_visible(self):
        result, state = self.submit_and_run("Find me papers on retrieval evaluation")
        self.assertEqual(state, JobState.BLOCKED_CAPABILITY)
        self.assertIn("web_search", self.store.job(result.job_id)["blocker"])
        self.assertEqual(self.adapter.model_sends, 0)

    def test_I03_missing_edit_tool_blocks_coding(self):
        self.scenario.tools = {"edit": "unsupported", "shell": "supported", "web_search": "unsupported"}
        fresh = self.make_coordinator()
        fresh.start()
        result = fresh.submit("Portfolio", "Implement the export per the agreed architecture")
        self.assertEqual(fresh.run(result.job_id), JobState.BLOCKED_CAPABILITY)
        fresh.close()
