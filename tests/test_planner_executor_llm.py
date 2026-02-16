from __future__ import annotations

import os
import unittest
import urllib.error
import urllib.request

from local_agents.engine import run_agent


class PlannerExecutorLLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mode = os.getenv("AGENT_MODE", "deterministic")
        cls.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        cls.model = os.getenv("LLM_MODEL", "llama3.2:3b")

    def setUp(self) -> None:
        if self.mode != "llm":
            self.skipTest("Set AGENT_MODE=llm to run planner/executor LLM tests")
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

    def test_planner_and_executor_llm(self) -> None:
        plan = run_agent(
            agent="planner-executor.planner-agent",
            payload={
                "goal": "Plan a secure release checklist for a new API endpoint",
                "constraints": ["No production downtime", "Approval required for schema changes"],
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(plan.get("risk_level"), {"low", "medium", "high"})
        self.assertTrue(3 <= len(plan.get("plan_steps", [])) <= 6)

        execution = run_agent(
            agent="planner-executor.executor-agent",
            payload={"plan_steps": plan["plan_steps"], "context": "Staging checks passed."},
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(execution.get("status"), {"done", "partial"})
        self.assertIsInstance(execution.get("summary"), str)


if __name__ == "__main__":
    unittest.main()
