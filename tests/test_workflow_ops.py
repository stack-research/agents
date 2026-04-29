from __future__ import annotations

import unittest

from local_agents.engine import (
    run_agent,
    run_checkpoint_agent,
    run_dependency_router_agent,
    run_retry_policy_agent,
    run_router_agent,
)


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

    def test_dependency_router_shape(self) -> None:
        out = run_dependency_router_agent(
            {
                "task": "Route incident triage for login outage",
                "available_agents": ["support-ops.triage-agent"],
                "prerequisites": ["incident_ticket_created", "oncall_notified"],
                "completed_prerequisites": ["incident_ticket_created"],
            }
        )
        self.assertIn("target_agent", out)
        self.assertIn("ready", out)
        self.assertIn("missing_prerequisites", out)
        self.assertFalse(out["ready"])

    def test_retry_policy_shape(self) -> None:
        out = run_retry_policy_agent(
            {
                "stage_name": "target",
                "failure_signal": "timeout calling downstream agent",
                "attempt_count": 1,
                "max_attempts": 3,
                "latency_ms": 3000,
            }
        )
        self.assertIn(out["decision"], {"retry", "backoff", "escalate", "stop"})
        self.assertIsInstance(out["backoff_ms"], int)
        self.assertIn("reason_code", out)

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
        dep_routed = run_agent(
            agent="dependency-router-agent",
            payload={
                "task": "Route incident triage",
                "available_agents": ["support-ops.triage-agent"],
                "prerequisites": ["incident_ticket_created"],
                "completed_prerequisites": ["incident_ticket_created"],
            },
        )
        self.assertTrue(dep_routed["ready"])
        retry = run_agent(
            agent="workflow-ops.retry-policy-agent",
            payload={
                "stage_name": "target",
                "failure_signal": "timeout",
                "attempt_count": 1,
                "max_attempts": 3,
            },
        )
        self.assertIn(retry["decision"], {"retry", "backoff", "escalate", "stop"})


if __name__ == "__main__":
    unittest.main()
