from __future__ import annotations

import unittest

from local_agents.engine import run_agent, run_retrieval_agent, run_synthesis_agent


class ResearchOpsTests(unittest.TestCase):
    def test_retrieval_shape(self) -> None:
        out = run_retrieval_agent(
            {
                "query": "OWASP ASI09 mitigation patterns",
                "sources": ["owasp whitepaper", "internal runbooks"],
                "max_points": 4,
            }
        )
        self.assertIn("notes", out)
        self.assertIn("confidence", out)
        self.assertGreaterEqual(len(out["notes"]), 1)
        self.assertLessEqual(len(out["notes"]), 4)

    def test_synthesis_shape(self) -> None:
        out = run_synthesis_agent(
            {
                "notes": [
                    "Research objective: ASI09 trust manipulation",
                    "Source note: enforce output contracts",
                    "Source note: add human approval gates",
                ],
                "audience": "security",
                "output_format": "brief",
            }
        )
        self.assertIn("headline", out)
        self.assertIn("summary", out)
        self.assertIn("next_actions", out)
        self.assertTrue(2 <= len(out["next_actions"]) <= 4)

    def test_run_agent_aliases(self) -> None:
        retrieval = run_agent(
            agent="research-ops.retrieval-agent",
            payload={"query": "incident response playbook", "sources": ["policy v3"]},
        )
        self.assertIn("notes", retrieval)
        synthesis = run_agent(
            agent="synthesis-agent",
            payload={"notes": retrieval["notes"], "audience": "engineering", "output_format": "report"},
        )
        self.assertIn("summary", synthesis)


if __name__ == "__main__":
    unittest.main()
