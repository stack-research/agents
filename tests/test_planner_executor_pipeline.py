from __future__ import annotations

import unittest

from scripts.run_planner_executor_pipeline import run_pipeline


class PlannerExecutorPipelineTests(unittest.TestCase):
    def test_pipeline_output_shape(self) -> None:
        out = run_pipeline(
            {
                "goal": "Prepare a safe release checklist for new authentication flow",
                "constraints": ["No downtime"],
                "context": "Staging checks passed",
            },
            mode="deterministic",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )
        self.assertIn("plan", out)
        self.assertIn("execution", out)
        self.assertIn(out.get("pipeline_status"), {"ok", "degraded"})
        self.assertIn("plan_steps", out["plan"])
        self.assertIn("risk_level", out["plan"])
        self.assertIn("status", out["execution"])
        self.assertIn("summary", out["execution"])

    def test_pipeline_degrades_on_invalid_goal(self) -> None:
        out = run_pipeline(
            {
                "goal": None,
                "constraints": ["No downtime"],
                "context": "Staging checks passed",
            },
            mode="deterministic",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )
        self.assertEqual(out.get("pipeline_status"), "degraded")
        self.assertEqual(out.get("failure_stage"), "planner")


if __name__ == "__main__":
    unittest.main()
