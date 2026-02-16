from __future__ import annotations

import os
import unittest
import urllib.error
import urllib.request

from local_agents.engine import run_agent


class QaOpsLLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mode = os.getenv("AGENT_MODE", "deterministic")
        cls.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        cls.model = os.getenv("LLM_MODEL", "llama3.2:3b")

    def setUp(self) -> None:
        if self.mode != "llm":
            self.skipTest("Set AGENT_MODE=llm to run qa-ops LLM tests")
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

    def test_qa_ops_llm_flow(self) -> None:
        cases = run_agent(
            agent="test-case-generator-agent",
            payload={
                "feature": "checkout payment authorization",
                "acceptance_criteria": ["declined card returns clear error", "success path stores receipt"],
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertTrue(4 <= len(cases.get("test_cases", [])) <= 8)

        triage = run_agent(
            agent="qa-ops.regression-triage-agent",
            payload={
                "failure_summary": "Production timeout after dependency update",
                "changed_components": ["payment-gateway-sdk"],
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(triage.get("probable_cause"), {"code", "config", "dependency", "infra", "test-data", "unknown"})
        self.assertIn(triage.get("severity"), {"sev1", "sev2", "sev3", "sev4"})


if __name__ == "__main__":
    unittest.main()
