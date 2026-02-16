from __future__ import annotations

import unittest

from local_agents.engine import run_agent, run_executor_agent, run_planner_agent


class PlannerExecutorAgentTests(unittest.TestCase):
    def test_planner_shape(self) -> None:
        out = run_planner_agent(
            {
                "goal": "Prepare a safe rollout plan for billing migration",
                "constraints": ["No downtime", "Keep rollback under 10 minutes"],
            }
        )
        self.assertIn(out["risk_level"], {"low", "medium", "high"})
        self.assertTrue(3 <= len(out["plan_steps"]) <= 6)

    def test_executor_shape(self) -> None:
        out = run_executor_agent(
            {
                "plan_steps": [
                    "Clarify objective and success criteria",
                    "Prepare checklist and rollback path",
                    "Execute staged rollout and validate",
                ],
                "context": "Migration completed with one non-blocking issue.",
            }
        )
        self.assertIn(out["status"], {"done", "partial"})
        self.assertGreaterEqual(out["completed_steps"], 0)
        self.assertGreaterEqual(out["blocked_steps"], 0)
        self.assertIsInstance(out["summary"], str)

    def test_run_agent_aliases(self) -> None:
        plan = run_agent(
            agent="planner-agent",
            payload={"goal": "Draft rollout steps for feature flag launch"},
        )
        self.assertIn("plan_steps", plan)
        execute = run_agent(
            agent="planner-executor.executor-agent",
            payload={"plan_steps": plan["plan_steps"], "context": "Two steps done, one pending"},
        )
        self.assertIn("summary", execute)


if __name__ == "__main__":
    unittest.main()
