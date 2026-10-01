"""Shipped JSON Schemas match the fixtures and the artifacts the code emits."""

import json
import unittest

from helpers import RouterTestCase
from model_router.contracts import AcceptanceEvidence, utc_now
from model_router.evals.metrics import iso_week, weekly_report
from model_router.jsonschema_lite import load_schema, validate


class EmittedArtifacts(RouterTestCase):
    def test_handoff_package_and_weekly_report_validate(self):
        source = self.architecture_thread()
        result = self.coordinator.finalise_architecture(source, acceptance=AcceptanceEvidence(source="finalise_command", reference="t", text="/finalise"))
        row = self.store.one("SELECT package_blob FROM handoffs WHERE id=?", (result.handoff_id,))
        package = json.loads(self.store.read_blob_text(row["package_blob"]))
        self.assertEqual(validate(package, load_schema("handoff-package.schema.json")), [])
        report = weekly_report(self.store, iso_week(utc_now()), include_synthetic=True)
        self.assertEqual(validate(report, load_schema("weekly-report.schema.json")), [])


if __name__ == "__main__":
    unittest.main()
