from __future__ import annotations

import unittest
from unittest.mock import patch

from local_agents.core import ValidationError
from scripts.run_governance_pipeline import run_pipeline


_MODE = "deterministic"
_MODEL = "llama3.2:3b"
_BASE = "http://localhost:11434"


class GovernancePipelineTests(unittest.TestCase):
    def test_pipeline_output_shape(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "gov-test-001",
                "action_description": "update user preferences",
                "permissions_requested": ["database-read", "audit-log"],
                "reversibility_plan": "rollback via config flag",
                "scope_boundary": "user prefs table only",
                "target_agent": "planner-executor.planner-agent",
                "target_payload": {
                    "goal": "Update user preference defaults",
                    "constraints": ["no downtime"],
                },
            },
            mode=_MODE,
            model=_MODEL,
            base_url=_BASE,
        )
        self.assertIn(out.get("pipeline_status"), {"ok", "needs_review", "degraded", "blocked"})
        self.assertIn("scope_validation", out)
        self.assertIn("target_output", out)
        self.assertIn("lineage", out)
        self.assertIn("checkpoint", out)

    def test_pipeline_allows_pass_and_executes_target(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "gov-test-002",
                "action_description": "read metrics dashboard",
                "permissions_requested": ["metrics-read", "audit-log"],
                "reversibility_plan": "rollback via flag",
                "scope_boundary": "metrics namespace only",
                "target_agent": "planner-executor.planner-agent",
                "target_payload": {
                    "goal": "Read metrics dashboard data",
                    "constraints": ["read-only"],
                },
            },
            mode=_MODE,
            model=_MODEL,
            base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "ok")
        self.assertEqual(out["scope_validation"]["verdict"], "pass")
        self.assertIn("plan_steps", out["target_output"])
        self.assertEqual(out["checkpoint"]["recorded"], True)

    def test_pipeline_returns_needs_review_without_target_execution(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "gov-test-003",
                "action_description": "delete inactive accounts",
                "permissions_requested": ["database-write"],
                "reversibility_plan": "soft-delete with 30-day window",
                "scope_boundary": "us-east region",
                "target_agent": "planner-executor.planner-agent",
                "target_payload": {"goal": "Delete accounts", "constraints": []},
            },
            mode=_MODE,
            model=_MODEL,
            base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "needs_review")
        self.assertEqual(out["scope_validation"]["verdict"], "review")
        self.assertEqual(out["target_output"]["status"], "needs_review")
        self.assertNotIn("plan_steps", out["target_output"])

    def test_pipeline_blocks_on_fail_verdict(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "gov-test-004",
                "action_description": "delete all production logs",
                "permissions_requested": ["admin-write", "production-access", "pii-read"],
                "reversibility_plan": "",
                "scope_boundary": "",
                "target_agent": "planner-executor.planner-agent",
                "target_payload": {"goal": "Delete logs", "constraints": []},
            },
            mode=_MODE,
            model=_MODEL,
            base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "blocked")
        self.assertEqual(out["scope_validation"]["verdict"], "fail")
        self.assertEqual(out["target_output"]["status"], "blocked")

    def test_pipeline_degrades_on_missing_action(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "gov-test-005",
                "action_description": None,
                "permissions_requested": ["read"],
                "target_agent": "planner-executor.planner-agent",
                "target_payload": {"goal": "test", "constraints": []},
            },
            mode=_MODE,
            model=_MODEL,
            base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "degraded")
        self.assertEqual(out.get("failure_stage"), "scope-validator")

    def test_pipeline_degrades_on_missing_target(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "gov-test-006",
                "action_description": "read user data",
                "permissions_requested": ["database-read", "audit-log"],
                "reversibility_plan": "read-only",
                "scope_boundary": "read-only",
            },
            mode=_MODE,
            model=_MODEL,
            base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "degraded")
        self.assertEqual(out.get("failure_stage"), "target-resolution")

    def test_lineage_records_decision(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "gov-test-007",
                "action_description": "read metrics dashboard",
                "permissions_requested": ["metrics-read", "audit-log"],
                "reversibility_plan": "n/a read-only",
                "scope_boundary": "metrics namespace only",
                "target_agent": "planner-executor.planner-agent",
                "target_payload": {
                    "goal": "Read metrics dashboard data",
                    "constraints": ["read-only"],
                },
            },
            mode=_MODE,
            model=_MODEL,
            base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "ok")
        self.assertIn("lineage_id", out["lineage"])
        self.assertEqual(out["lineage"]["integrity_check"], "complete")

    def test_checkpoint_fallback_on_checkpoint_validation_error(self) -> None:
        original_run_agent = run_pipeline.__globals__["run_agent"]

        def fake_run_agent(*, agent: str, payload: dict[str, object], mode: str, model: str, base_url: str) -> dict[str, object]:
            if agent == "workflow-ops.checkpoint-agent":
                raise ValidationError("forced checkpoint failure")
            return original_run_agent(agent=agent, payload=payload, mode=mode, model=model, base_url=base_url)

        with patch("scripts.run_governance_pipeline.run_agent", side_effect=fake_run_agent):
            out = run_pipeline(
                {
                    "workflow_id": "gov-test-008",
                    "action_description": "read metrics dashboard",
                    "permissions_requested": ["metrics-read", "audit-log"],
                    "reversibility_plan": "read-only",
                    "scope_boundary": "metrics namespace only",
                    "target_agent": "planner-executor.planner-agent",
                    "target_payload": {"goal": "Inspect dashboard", "constraints": ["read-only"]},
                },
                mode=_MODE,
                model=_MODEL,
                base_url=_BASE,
            )
        self.assertTrue(out["checkpoint"]["recorded"])
        self.assertIn("Fallback checkpoint", out["checkpoint"]["summary"])


if __name__ == "__main__":
    unittest.main()
