from __future__ import annotations

import os
import unittest
import urllib.error
import urllib.request

from local_agents.engine import run_agent


class EvalOpsLLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mode = os.getenv("AGENT_MODE", "deterministic")
        cls.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        cls.model = os.getenv("LLM_MODEL", "llama3.2:3b")

    def setUp(self) -> None:
        if self.mode != "llm":
            self.skipTest("Set AGENT_MODE=llm to run eval-ops LLM tests")
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

    def test_eval_ops_llm_flow(self) -> None:
        bench = run_agent(
            agent="eval-ops.benchmark-curator-agent",
            payload={
                "benchmark_name": "reasoning-v2",
                "candidate_cases": [
                    {"case_id": "r1", "title": "Multi-step math"},
                    {"case_id": "r2", "title": "Contradiction detection"},
                ],
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(bench.get("curation_verdict"), {"ready", "needs_expansion", "sparse"})
        self.assertIsInstance(bench.get("included_cases"), list)

        score = run_agent(
            agent="eval-ops.regression-score-agent",
            payload={
                "baseline_scores": {"f1": 0.82},
                "current_scores": {"f1": 0.79},
                "regression_threshold_percent": 2.0,
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(score.get("verdict"), {"pass", "warn", "fail"})
        self.assertIn("regression_flag", score)

        drift = run_agent(
            agent="eval-ops.quality-drift-reporter-agent",
            payload={
                "metric_name": "f1_score",
                "windows": [
                    {"window_label": "m1", "score": 0.81},
                    {"window_label": "m2", "score": 0.80},
                    {"window_label": "m3", "score": 0.78},
                ],
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(drift.get("trend"), {"improving", "stable", "degrading", "volatile"})
        self.assertIn(drift.get("drift_severity"), {"none", "low", "medium", "high"})


if __name__ == "__main__":
    unittest.main()
