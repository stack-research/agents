from __future__ import annotations

import unittest

from local_agents.engine import run_agent, run_summary_agent


class SupportOpsTests(unittest.TestCase):
    def test_summary_agent_output_shape(self) -> None:
        out = run_summary_agent(
            {
                "period_start": "2026-02-09",
                "period_end": "2026-02-15",
                "tickets": [
                    {"id": "t1", "priority": "p1", "category": "access"},
                    {"id": "t2", "priority": "p2", "category": "access"},
                    {"id": "t3", "priority": "p3", "category": "billing"},
                ],
                "top_n_actions": 3,
            }
        )
        self.assertEqual(out["ticket_count"], 3)
        self.assertEqual(out["priority_breakdown"]["p1"], 1)
        self.assertIn("access:2", out["top_categories"])
        self.assertEqual(len(out["recommended_actions"]), 3)

    def test_summary_agent_empty_tickets(self) -> None:
        out = run_summary_agent(
            {
                "period_start": "2026-02-09",
                "period_end": "2026-02-15",
                "tickets": [],
                "top_n_actions": 2,
            }
        )
        self.assertEqual(out["ticket_count"], 0)
        self.assertEqual(out["top_categories"], [])
        self.assertEqual(len(out["recommended_actions"]), 2)

    def test_run_agent_aliases(self) -> None:
        out = run_agent(
            agent="support-ops.summary-agent",
            payload={
                "period_start": "2026-02-09",
                "period_end": "2026-02-15",
                "tickets": [{"priority": "p2", "category": "bug"}],
            },
        )
        self.assertIn("summary", out)
        self.assertIn("priority_breakdown", out)


if __name__ == "__main__":
    unittest.main()
