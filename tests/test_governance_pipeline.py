from __future__ import annotations

import unittest

from scripts.run_governance_pipeline import run_pipeline


class GovernancePipelineTests(unittest.TestCase):
    def test_pipeline_output_shape(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "gov-test-001",
                "action_description": "update user preferences",
                "permissions_requested": ["database-read", "audit-log-write"],
                "reversibility_plan": "rollback via config flag",
                "scope_boundary": "user prefs table only",
                "target_agent": "planner-executor.planner-agent",
                "target_payload": {
                    "goal": "Update user preference defaults",
                    "constraints": ["no downtime"],
                },
            },
            mode="deterministic",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )
        self.assertIn(out.get("pipeline_status"), {"ok", "degraded", "blocked"})
        self.assertIn("scope_validation", out)
        self.assertIn("target_output", out)
        self.assertIn("lineage", out)
        self.assertIn("checkpoint", out)

    def test_pipeline_blocks_on_fail_verdict(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "gov-test-002",
                "action_description": "delete all production logs",
                "permissions_requested": ["admin-write", "production-access", "pii-read"],
                "reversibility_plan": "",
                "scope_boundary": "",
                "target_agent": "planner-executor.planner-agent",
                "target_payload": {"goal": "Delete logs", "constraints": []},
            },
            mode="deterministic",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )
        self.assertEqual(out.get("pipeline_status"), "blocked")
        self.assertEqual(out["scope_validation"]["verdict"], "fail")
        self.assertEqual(out["target_output"]["status"], "blocked")

    def test_pipeline_degrades_on_missing_action(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "gov-test-003",
                "action_description": None,
                "permissions_requested": ["read"],
                "target_agent": "planner-executor.planner-agent",
                "target_payload": {"goal": "test", "constraints": []},
            },
            mode="deterministic",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )
        self.assertEqual(out.get("pipeline_status"), "degraded")
        self.assertEqual(out.get("failure_stage"), "scope-validator")

    def test_pipeline_degrades_on_missing_target(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "gov-test-004",
                "action_description": "read user data",
                "permissions_requested": ["database-read"],
                "scope_boundary": "read-only",
            },
            mode="deterministic",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )
        self.assertEqual(out.get("pipeline_status"), "degraded")
        self.assertEqual(out.get("failure_stage"), "target-resolution")

    def test_lineage_records_decision(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "gov-test-005",
                "action_description": "read metrics dashboard",
                "permissions_requested": ["metrics-read"],
                "reversibility_plan": "n/a read-only",
                "scope_boundary": "metrics namespace only",
                "target_agent": "planner-executor.planner-agent",
                "target_payload": {
                    "goal": "Read metrics dashboard data",
                    "constraints": ["read-only"],
                },
            },
            mode="deterministic",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )
        self.assertEqual(out.get("pipeline_status"), "ok")
        self.assertIn("lineage_id", out["lineage"])
        self.assertEqual(out["lineage"]["integrity_check"], "complete")


if __name__ == "__main__":
    unittest.main()
