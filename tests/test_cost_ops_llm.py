from __future__ import annotations

import os
import unittest
import urllib.error
import urllib.request

from local_agents.engine import run_agent


class CostOpsLLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mode = os.getenv("AGENT_MODE", "deterministic")
        cls.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        cls.model = os.getenv("LLM_MODEL", "llama3.2:3b")

    def setUp(self) -> None:
        if self.mode != "llm":
            self.skipTest("Set AGENT_MODE=llm to run cost-ops LLM tests")
        if not self._ollama_reachable(self.base_url):
            self.skipTest(f"LLM endpoint not reachable: {self.base_url}")

    @staticmethod
    def _ollama_reachable(base_url: str) -> bool:
        try:
            with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=3):
                return True
        except urllib.error.URLError:
            return False

    def test_cost_ops_llm_flow(self) -> None:
        attr = run_agent(
            agent="cost-ops.cost-attribution-agent",
            payload={"run_id": "r1", "stages": [{"stage_name": "a", "tokens_in": 100, "tokens_out": 50, "runtime_ms": 2000}]},
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        guard = run_agent(
            agent="cost-ops.budget-guardrail-agent",
            payload={"run_id": "r1", "attribution": attr, "budget_limits": {"run_limit_usd": 1, "warning_ratio": 0.8, "stage_limit_usd": 1}},
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        opt = run_agent(
            agent="cost-ops.pipeline-optimizer-agent",
            payload={"run_id": "r1", "attribution": attr, "guardrails": guard},
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIsInstance(opt.get("optimization_suggestions"), list)


if __name__ == "__main__":
    unittest.main()
