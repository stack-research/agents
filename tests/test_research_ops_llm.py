from __future__ import annotations

import os
import unittest
import urllib.error
import urllib.request

from local_agents.engine import run_agent


class ResearchOpsLLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mode = os.getenv("AGENT_MODE", "deterministic")
        cls.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        cls.model = os.getenv("LLM_MODEL", "llama3.2:3b")

    def setUp(self) -> None:
        if self.mode != "llm":
            self.skipTest("Set AGENT_MODE=llm to run research-ops LLM tests")
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

    def test_retrieval_and_synthesis_llm(self) -> None:
        retrieval = run_agent(
            agent="retrieval-agent",
            payload={
                "query": "Summarize security testing guidance for agentic systems",
                "sources": ["owasp top 10", "internal testing SOP"],
                "max_points": 4,
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertGreaterEqual(len(retrieval.get("notes", [])), 1)
        self.assertLessEqual(len(retrieval.get("notes", [])), 4)

        synthesis = run_agent(
            agent="research-ops.synthesis-agent",
            payload={
                "notes": retrieval["notes"],
                "audience": "engineering",
                "output_format": "brief",
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn("headline", synthesis)
        self.assertIn("summary", synthesis)
        self.assertTrue(2 <= len(synthesis.get("next_actions", [])) <= 4)


if __name__ == "__main__":
    unittest.main()
