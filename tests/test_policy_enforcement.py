from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.check_policy_pack import evaluate_runtime_policy


class PolicyEnforcementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[1]
        cls.policy = json.loads((root / "policy" / "asi-control-baselines.json").read_text(encoding="utf-8"))

    def test_dev_allows_llm(self) -> None:
        ok, _ = evaluate_runtime_policy(self.policy, "dev", "llm")
        self.assertTrue(ok)

    def test_prod_blocks_llm(self) -> None:
        ok, message = evaluate_runtime_policy(self.policy, "prod", "llm")
        self.assertFalse(ok)
        self.assertIn("not allowed", message)

    def test_unknown_env_rejected(self) -> None:
        ok, message = evaluate_runtime_policy(self.policy, "sandbox", "deterministic")
        self.assertFalse(ok)
        self.assertIn("unknown environment", message)


if __name__ == "__main__":
    unittest.main()
