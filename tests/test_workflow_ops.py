from __future__ import annotations

import unittest

from local_agents.engine import run_agent, run_checkpoint_agent, run_router_agent


class WorkflowOpsTests(unittest.TestCase):
    def test_router_shape(self) -> None:
        out = run_router_agent(
            {
                "task": "Customers cannot log in after deploy",
                "available_agents": [
                    "support-ops.triage-agent",
                    "qa-ops.regression-triage-agent",
                ],
            }
        )
        self.assertIn("target_agent", out)
        self.assertIn(out["priority"], {"p1", "p2", "p3", "p4"})

    def test_checkpoint_shape(self) -> None:
        out = run_checkpoint_agent(
            {
                "workflow_id": "release-42",
                "stage": "qa-validation",
                "status": "in_progress",
                "notes": "Integration tests running",
            }
        )
        self.assertIn("checkpoint_id", out)
        self.assertTrue(out["recorded"])
        self.assertIsInstance(out["summary"], str)

    def test_run_agent_aliases(self) -> None:
        routed = run_agent(
            agent="workflow-ops.router-agent",
            payload={"task": "Generate QA test scenarios for checkout"},
        )
        checkpoint = run_agent(
            agent="checkpoint-agent",
            payload={
                "workflow_id": "wf-1",
                "stage": "routing",
                "status": "completed",
                "notes": f"Routed to {routed['target_agent']}",
            },
        )
        self.assertIn("target_agent", routed)
        self.assertIn("checkpoint_id", checkpoint)


if __name__ == "__main__":
    unittest.main()
