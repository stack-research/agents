from __future__ import annotations

import unittest

from local_agents.engine import (
    run_agent,
    run_claim_trace_agent,
    run_evidence_ranker_agent,
    run_memory_curator_agent,
    run_temporal_watch_agent,
)


class KnowledgeOpsTests(unittest.TestCase):
    def test_evidence_ranker_shape(self) -> None:
        out = run_evidence_ranker_agent(
            {
                "assertions": ["Dependency update caused CI instability"],
                "evidence_items": [
                    {
                        "content": "CI pass rate dropped from 94 to 61 after upgrade",
                        "source_kind": "measurement",
                        "corroboration_count": 3,
                        "age_days": 1,
                        "relevance_hint": 0.9,
                    },
                    {
                        "content": "Engineer note suspects flaky test cluster",
                        "source_kind": "note",
                        "corroboration_count": 0,
                        "age_days": 3,
                        "relevance_hint": 0.6,
                    },
                ],
                "max_evidence": 2,
            }
        )
        self.assertEqual(len(out["ranked_evidence"]), 2)
        self.assertGreaterEqual(out["ranked_evidence"][0]["score"], out["ranked_evidence"][1]["score"])

    def test_claim_trace_shape(self) -> None:
        out = run_claim_trace_agent(
            {
                "assertions": ["Rollback stabilized pass rate"],
                "evidence_bundle": [
                    {"evidence_id": "ev-1", "score": 0.82, "content": "Pass rate recovered after rollback"}
                ],
                "min_support_score": 0.6,
            }
        )
        self.assertEqual(len(out["assertion_map"]), 1)
        self.assertIn(out["assertion_map"][0]["status"], {"supported", "weak", "unsupported"})

    def test_memory_curator_shape(self) -> None:
        out = run_memory_curator_agent(
            {
                "run_id": "ci-run-1",
                "artifacts": ["Pass rate dropped after dependency update", "Rollback restored stability"],
                "memory_horizon_hours": 48,
            }
        )
        self.assertGreaterEqual(len(out["memory_updates"]), 1)
        self.assertEqual(out["expires_in_hours"], 48)

    def test_temporal_watch_shape(self) -> None:
        out = run_temporal_watch_agent(
            {
                "current_snapshot": {"pass_rate": 0.91, "flaky_tests": 2},
                "prior_snapshot": {"pass_rate": 0.84, "flaky_tests": 5},
                "window_label": "24h",
            }
        )
        self.assertIn(out["drift_level"], {"no_change", "minor_shift", "major_shift"})
        self.assertGreaterEqual(len(out["temporal_signals"]), 1)

    def test_run_agent_aliases(self) -> None:
        ranked = run_agent(
            "knowledge-ops.evidence-ranker-agent",
            {
                "assertions": ["Signal drift detected in deployment metrics"],
                "evidence_items": [{"content": "Pass rate dropped", "source_kind": "log"}],
            },
        )
        self.assertIn("ranked_evidence", ranked)
        watched = run_agent(
            "temporal-watch-agent",
            {"current_snapshot": {"a": 1}, "prior_snapshot": {"a": 1}},
        )
        self.assertIn("drift_level", watched)


if __name__ == "__main__":
    unittest.main()
