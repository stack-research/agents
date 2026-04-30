from __future__ import annotations

import os
import unittest
import urllib.error
import urllib.request

from local_agents.engine import run_agent


class ExperimentOpsLLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mode = os.getenv("AGENT_MODE", "deterministic")
        cls.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        cls.model = os.getenv("LLM_MODEL", "llama3.2:3b")

    def setUp(self) -> None:
        if self.mode != "llm":
            self.skipTest("Set AGENT_MODE=llm to run experiment-ops LLM tests")
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

    def test_experiment_ops_llm_flow(self) -> None:
        hyp = run_agent(
            agent="experiment-ops.hypothesis-registration-agent",
            payload={
                "hypothesis_statement": "Adding inline help tips increases form completion rate.",
                "experiment_domain": "ux-onboarding",
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(hyp.get("registration_status"), {"registered", "needs_clarification"})
        self.assertIsInstance(hyp.get("hypothesis_id"), str)

        plan = run_agent(
            agent="experiment-ops.experiment-plan-agent",
            payload={
                "hypothesis_statement": "Dark mode default reduces eye strain reports during night sessions.",
                "constraints": {"max_variants": 3},
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIsInstance(plan.get("variants"), list)
        self.assertGreaterEqual(len(plan.get("variants") or []), 2)

        adj = run_agent(
            agent="experiment-ops.result-adjudication-agent",
            payload={
                "hypothesis_statement": "Latency improves with the new cache layer.",
                "observed_metrics": {"p95_latency_ms": 120.0},
                "primary_metric": "p95_latency_ms",
                "success_criteria": "p95_latency_ms below 200",
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(adj.get("adjudication_verdict"), {"supports", "inconclusive", "refutes"})
        self.assertIn(adj.get("confidence"), {"low", "medium", "high"})


if __name__ == "__main__":
    unittest.main()
