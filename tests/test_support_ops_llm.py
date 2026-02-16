from __future__ import annotations

import os
import unittest
import urllib.error
import urllib.request

from local_agents.engine import run_agent


class SupportOpsLLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mode = os.getenv("AGENT_MODE", "deterministic")
        cls.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        cls.model = os.getenv("LLM_MODEL", "llama3.2:3b")

    def setUp(self) -> None:
        if self.mode != "llm":
            self.skipTest("Set AGENT_MODE=llm to run support-ops LLM tests")
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

    def test_summary_agent_llm_output_shape(self) -> None:
        out = run_agent(
            agent="summary-agent",
            payload={
                "period_start": "2026-02-09",
                "period_end": "2026-02-15",
                "tickets": [
                    {"id": "t1", "priority": "p2", "category": "access"},
                    {"id": "t2", "priority": "p3", "category": "bug"},
                    {"id": "t3", "priority": "p3", "category": "access"},
                ],
                "top_n_actions": 3,
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIsInstance(out.get("ticket_count"), int)
        breakdown = out.get("priority_breakdown", {})
        self.assertTrue(all(key in breakdown for key in ["p1", "p2", "p3", "p4"]))
        self.assertTrue(0 <= len(out.get("top_categories", [])) <= 3)
        self.assertEqual(len(out.get("recommended_actions", [])), 3)

    def test_handoff_agent_llm_output_shape(self) -> None:
        out = run_agent(
            agent="support-ops.handoff-agent",
            payload={
                "shift_label": "night-shift-2026-02-16",
                "incidents": [
                    {"id": "inc-1", "severity": "sev1", "status": "mitigating", "owner": "oncall-a"},
                    {"id": "inc-2", "severity": "sev2", "status": "investigating", "owner": "oncall-b"},
                    {"id": "inc-3", "severity": "sev3", "status": "resolved", "owner": "oncall-c"},
                ],
                "handoff_window": "next 8 hours",
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIsInstance(out.get("active_count"), int)
        self.assertTrue(0 <= len(out.get("critical_items", [])) <= 3)
        self.assertIsInstance(out.get("handoff_brief"), str)
        self.assertEqual(len(out.get("recommended_checks", [])), 3)


if __name__ == "__main__":
    unittest.main()
