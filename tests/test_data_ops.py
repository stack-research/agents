from __future__ import annotations

import unittest

from local_agents.engine import run_agent, run_data_validator_agent, run_schema_drift_detector_agent


class DataOpsTests(unittest.TestCase):
    def test_schema_drift_detector_shape(self) -> None:
        out = run_schema_drift_detector_agent(
            {
                "schema_before": {"user_id": "integer", "name": "string", "email": "string"},
                "schema_after": {"user_id": "integer", "name": "string", "email_address": "string", "updated_at": "timestamp"},
            }
        )
        self.assertIn(out["drift_severity"], {"none", "low", "medium", "high"})
        self.assertIsInstance(out["changes"], list)
        self.assertTrue(len(out["recommended_actions"]) >= 1)
        for change in out["changes"]:
            self.assertIn("field", change)
            self.assertIn("change_type", change)
            self.assertIn("detail", change)

    def test_schema_drift_detector_no_changes(self) -> None:
        out = run_schema_drift_detector_agent(
            {
                "schema_before": {"id": "integer", "name": "string"},
                "schema_after": {"id": "integer", "name": "string"},
            }
        )
        self.assertEqual(out["drift_severity"], "none")
        self.assertEqual(len(out["changes"]), 0)

    def test_schema_drift_detector_type_change(self) -> None:
        out = run_schema_drift_detector_agent(
            {
                "schema_before": {"id": "integer", "name": "string"},
                "schema_after": {"id": "string", "name": "string"},
            }
        )
        self.assertIn(out["drift_severity"], {"medium", "high"})
        type_changes = [c for c in out["changes"] if c["change_type"] == "type_changed"]
        self.assertTrue(len(type_changes) >= 1)

    def test_data_validator_shape(self) -> None:
        out = run_data_validator_agent(
            {
                "records": [
                    {"email": "alice@example.com", "age": 30},
                    {"email": "", "age": 25},
                    {"email": "bob@example.com", "age": -5},
                ],
                "rules": ["email must not be empty", "age must be non-negative"],
            }
        )
        self.assertIn(out["verdict"], {"pass", "warn", "fail"})
        self.assertIsInstance(out["valid_count"], int)
        self.assertIsInstance(out["invalid_count"], int)
        self.assertEqual(out["valid_count"] + out["invalid_count"], 3)
        self.assertTrue(len(out["violations"]) <= 10)

    def test_data_validator_all_valid(self) -> None:
        out = run_data_validator_agent(
            {
                "records": [
                    {"email": "alice@example.com", "age": 30},
                    {"email": "bob@example.com", "age": 25},
                ],
                "rules": ["email must not be empty", "age must be non-negative"],
            }
        )
        self.assertEqual(out["verdict"], "pass")
        self.assertEqual(out["invalid_count"], 0)

    def test_run_agent_aliases(self) -> None:
        drift = run_agent(
            agent="data-ops.schema-drift-detector-agent",
            payload={
                "schema_before": {"id": "integer"},
                "schema_after": {"id": "integer", "name": "string"},
            },
        )
        validator = run_agent(
            agent="data-validator-agent",
            payload={
                "records": [{"name": "Alice"}],
                "rules": ["name must not be empty"],
            },
        )
        self.assertIn("drift_severity", drift)
        self.assertIn("verdict", validator)


if __name__ == "__main__":
    unittest.main()
