from __future__ import annotations

import os
import unittest
import urllib.error
import urllib.request

from scripts.run_workflow_pipeline import run_pipeline


class WorkflowPipelineLLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mode = os.getenv("AGENT_MODE", "deterministic")
        cls.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        cls.model = os.getenv("LLM_MODEL", "llama3.2:3b")

    def setUp(self) -> None:
        if self.mode != "llm":
            self.skipTest("Set AGENT_MODE=llm to run workflow pipeline LLM tests")
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

    def test_workflow_pipeline_llm_output_shape(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "wf-incident-2026-02-16",
                "task": "Customers cannot login after deploy; triage and prioritize this issue",
                "available_agents": [
                    "support-ops.triage-agent",
                    "qa-ops.regression-triage-agent",
                ],
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(out.get("pipeline_status"), {"ok", "degraded"})
        self.assertIn("route", out)
        self.assertIn("target_output", out)
        self.assertIn("checkpoint", out)


if __name__ == "__main__":
    unittest.main()
