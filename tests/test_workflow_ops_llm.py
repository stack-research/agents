from __future__ import annotations

import os
import unittest
import urllib.error
import urllib.request

from local_agents.engine import run_agent


class WorkflowOpsLLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mode = os.getenv("AGENT_MODE", "deterministic")
        cls.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        cls.model = os.getenv("LLM_MODEL", "llama3.2:3b")

    def setUp(self) -> None:
        if self.mode != "llm":
            self.skipTest("Set AGENT_MODE=llm to run workflow-ops LLM tests")
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

    def test_workflow_ops_llm_flow(self) -> None:
        routed = run_agent(
            agent="router-agent",
            payload={
                "task": "Customers cannot login after release; route for immediate triage",
                "available_agents": ["support-ops.triage-agent", "qa-ops.regression-triage-agent"],
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(routed.get("priority"), {"p1", "p2", "p3", "p4"})

        checkpoint = run_agent(
            agent="workflow-ops.checkpoint-agent",
            payload={
                "workflow_id": "release-42",
                "stage": "routing",
                "status": "completed",
                "notes": f"Routed to {routed['target_agent']}",
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertTrue(checkpoint.get("recorded"))
        self.assertIn("checkpoint_id", checkpoint)


if __name__ == "__main__":
    unittest.main()
