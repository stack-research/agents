from __future__ import annotations

import os
import unittest
import urllib.error
import urllib.request

from local_agents.engine import run_agent


class ArtifactOpsLLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mode = os.getenv("AGENT_MODE", "deterministic")
        cls.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        cls.model = os.getenv("LLM_MODEL", "llama3.2:3b")

    def setUp(self) -> None:
        if self.mode != "llm":
            self.skipTest("Set AGENT_MODE=llm to run artifact-ops LLM tests")
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

    def test_artifact_ops_llm_flow(self) -> None:
        inv = run_agent(
            agent="artifact-ops.artifact-inventory-agent",
            payload={
                "run_id": "llm-run-1",
                "artifacts": [
                    {"logical_path": "cfg.json", "role": "input", "inline_text": '{"k":1}'},
                ],
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(inv.get("inventory_status"), {"complete", "partial"})
        self.assertIsInstance(inv.get("artifacts"), list)

        man = run_agent(
            agent="artifact-ops.bundle-manifest-agent",
            payload={"run_id": "llm-run-1", "inventory": inv},
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIsInstance(man.get("bundle_root_sha256"), str)
        self.assertEqual(len(man.get("bundle_root_sha256") or ""), 64)

        seal = run_agent(
            agent="artifact-ops.bundle-seal-agent",
            payload={
                "run_id": "llm-run-1",
                "bundle_root_sha256": man["bundle_root_sha256"],
                "lineage_records": [{"lineage_id": "llm-lineage-1"}],
            },
            mode="llm",
            model=self.model,
            base_url=self.base_url,
        )
        self.assertIn(seal.get("seal_status"), {"sealed", "sealed_with_gaps"})
        self.assertIsInstance(seal.get("bundle_id"), str)


if __name__ == "__main__":
    unittest.main()
