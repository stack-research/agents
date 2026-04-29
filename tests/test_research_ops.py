from __future__ import annotations

import unittest

from local_agents.engine import (
    run_agent,
    run_gap_detector_agent,
    run_retrieval_agent,
    run_source_planner_agent,
    run_synthesis_agent,
)


class ResearchOpsTests(unittest.TestCase):
    def test_source_planner_shape(self) -> None:
        out = run_source_planner_agent(
            {
                "query": "Assess CI instability root cause after dependency upgrade",
                "current_evidence": [{"content": "Pass rate dropped", "source_kind": "measurement", "score": 0.8}],
                "budget_limit": 4,
            }
        )
        self.assertIn("fetch_plan", out)
        self.assertIn("priority_sources", out)
        self.assertIn("coverage_target", out)
        self.assertGreaterEqual(len(out["fetch_plan"]), 1)
        self.assertLessEqual(len(out["fetch_plan"]), 4)

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

    def test_gap_detector_shape(self) -> None:
        out = run_gap_detector_agent(
            {
                "assertions": ["Dependency update caused flaky tests"],
                "evidence_bundle": [{"content": "Anecdotal flaky report", "source_kind": "note", "score": 0.4}],
                "required_confidence": 0.7,
            }
        )
        self.assertIn("gaps", out)
        self.assertIn("risk_level", out)
        self.assertIn("next_collection_actions", out)
        self.assertIn(out["risk_level"], {"low", "medium", "high"})

    def test_run_agent_aliases(self) -> None:
        planner = run_agent(
            agent="research-ops.source-planner-agent",
            payload={"query": "incident response playbook evidence collection"},
        )
        self.assertIn("fetch_plan", planner)
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
        gaps = run_agent(
            agent="gap-detector-agent",
            payload={
                "assertions": ["rollback fixed stability"],
                "evidence_bundle": [{"content": "pass rate recovered", "source_kind": "measurement", "score": 0.84}],
            },
        )
        self.assertIn("risk_level", gaps)


if __name__ == "__main__":
    unittest.main()
