from __future__ import annotations

import os
import unittest
import urllib.error
import urllib.request

from local_agents.engine import run_agent


class KnowledgeOpsLLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mode = os.getenv("AGENT_MODE", "deterministic")
        cls.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        cls.model = os.getenv("LLM_MODEL", "llama3.2:3b")

    def setUp(self) -> None:
        if self.mode != "llm":
            self.skipTest("Set AGENT_MODE=llm to run knowledge-ops LLM tests")
        if not self._ollama_reachable(self.base_url):
            self.skipTest(f"LLM endpoint not reachable: {self.base_url}")

    @staticmethod
    def _ollama_reachable(base_url: str) -> bool:
        url = f"{base_url.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=3):
                return True
        except urllib.error.URLError:
            return False

    def test_knowledge_ops_chain_llm(self) -> None:
        ranked = run_agent(
            "knowledge-ops.evidence-ranker-agent",
            {
                "assertions": ["Rollback stabilized CI pass rate"],
                "evidence_items": [
                    {
                        "content": "Pass rate recovered to 91 percent within one run after rollback",
                        "source_kind": "measurement",
                    }
                ],
                "max_evidence": 2,
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertGreaterEqual(len(ranked.get("ranked_evidence", [])), 1)

        traced = run_agent(
            "claim-trace-agent",
            {
                "assertions": ["Rollback stabilized CI pass rate"],
                "evidence_bundle": ranked["ranked_evidence"],
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertEqual(len(traced.get("assertion_map", [])), 1)

        watched = run_agent(
            "temporal-watch-agent",
            {
                "current_snapshot": {"pass_rate": 0.91, "flaky_tests": 2},
                "prior_snapshot": {"pass_rate": 0.84, "flaky_tests": 5},
                "window_label": "24h",
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(watched.get("drift_level"), {"no_change", "minor_shift", "major_shift"})


if __name__ == "__main__":
    unittest.main()
