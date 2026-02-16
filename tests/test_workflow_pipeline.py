from __future__ import annotations

import unittest

from scripts.run_workflow_pipeline import run_pipeline


class WorkflowPipelineTests(unittest.TestCase):
    def test_pipeline_output_shape(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "wf-incident-2026-02-16",
                "task": "Customers cannot login after deploy; triage and prioritize this issue",
                "available_agents": [
                    "support-ops.triage-agent",
                    "qa-ops.regression-triage-agent",
                ],
            },
            mode="deterministic",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )
        self.assertIn(out.get("pipeline_status"), {"ok", "degraded"})
        self.assertIn("route", out)
        self.assertIn("target_output", out)
        self.assertIn("checkpoint", out)

    def test_pipeline_degrades_on_invalid_task(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "wf-incident-2026-02-16",
                "task": None,
                "available_agents": ["support-ops.triage-agent"],
            },
            mode="deterministic",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )
        self.assertEqual(out.get("pipeline_status"), "degraded")
        self.assertEqual(out.get("failure_stage"), "router")


if __name__ == "__main__":
    unittest.main()
