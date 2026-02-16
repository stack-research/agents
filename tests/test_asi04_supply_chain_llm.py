from __future__ import annotations

import os
import unittest
import urllib.error
import urllib.request

from local_agents.core import ValidationError
from local_agents.engine import run_agent


class ASI04SupplyChainLLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mode = os.getenv("AGENT_MODE", "deterministic")
        cls.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        cls.model = os.getenv("LLM_MODEL", "llama3.2:3b")

    def setUp(self) -> None:
        if self.mode != "llm":
            self.skipTest("Set AGENT_MODE=llm to run LLM ASI04 tests")
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

    def test_approved_runtime_source_allows_execution(self) -> None:
        out = run_agent(
            agent="starter-kit.classifier-agent",
            payload={
                "text": "I was billed twice and need a refund.",
                "labels": ["billing", "feature-request", "unknown"],
            },
            mode="llm",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )
        self.assertIn(out["label"], {"billing", "feature-request", "unknown"})

    def test_unapproved_model_blocked_in_llm_mode(self) -> None:
        with self.assertRaises(ValidationError):
            run_agent(
                agent="starter-kit.classifier-agent",
                payload={"text": "Please add SSO support."},
                mode="llm",
                model="evilmodel:latest",
                base_url="http://localhost:11434",
            )

    def test_unapproved_host_blocked_in_llm_mode(self) -> None:
        with self.assertRaises(ValidationError):
            run_agent(
                agent="starter-kit.classifier-agent",
                payload={"text": "Please add SSO support."},
                mode="llm",
                model="llama3.2:3b",
                base_url="http://evil.example:11434",
            )


if __name__ == "__main__":
    unittest.main()
