from __future__ import annotations

import os
import unittest
import urllib.error
import urllib.request

from local_agents import run_agent


class LLMIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mode = os.getenv("AGENT_MODE", "deterministic")
        cls.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        cls.model = os.getenv("LLM_MODEL", "llama3.2:3b")

    def setUp(self) -> None:
        if self.mode != "llm":
            self.skipTest("Set AGENT_MODE=llm to run integration tests")
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

    def test_classifier_output_shape(self) -> None:
        out = run_agent(
            agent="starter-kit.classifier-agent",
            payload={
                "text": "Please add SSO support for our workspace.",
                "labels": [
                    "bug-report",
                    "billing",
                    "feature-request",
                    "support",
                    "feedback",
                    "unknown",
                ],
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(out["label"], {"bug-report", "billing", "feature-request", "support", "feedback", "unknown"})
        self.assertGreaterEqual(float(out["confidence"]), 0)
        self.assertLessEqual(float(out["confidence"]), 1)
        self.assertIsInstance(out["rationale"], str)

    def test_heartbeat_output_shape(self) -> None:
        out = run_agent(
            agent="starter-kit.heartbeat-agent",
            payload={
                "service_name": "billing-api",
                "heartbeat_age_seconds": 55,
                "error_rate_percent": 7.2,
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(out["status"], {"ok", "warn", "critical"})
        self.assertIsInstance(out["report"], str)

    def test_triage_output_shape(self) -> None:
        out = run_agent(
            agent="support-ops.triage-agent",
            payload={
                "text": "Customers cannot log in to production after deploy.",
                "customer_tier": "pro",
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(out["priority"], {"p1", "p2", "p3", "p4"})
        self.assertIn(out["category"], {"billing", "bug", "access", "feature", "how-to", "other"})
        self.assertIsInstance(out["next_action"], str)

    def test_reply_drafter_output_shape(self) -> None:
        out = run_agent(
            agent="support-ops.reply-drafter-agent",
            payload={
                "customer_name": "Alex",
                "priority": "p2",
                "category": "access",
                "issue_summary": "Users cannot sign in after reset.",
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIsInstance(out["subject"], str)
        self.assertIsInstance(out["reply"], str)


if __name__ == "__main__":
    unittest.main()
