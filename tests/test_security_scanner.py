from __future__ import annotations

import unittest

from local_agents.engine import run_agent, run_agentic_security_scanner_agent


class SecurityScannerTests(unittest.TestCase):
    def test_scanner_output_shape(self) -> None:
        out = run_agentic_security_scanner_agent({"target_path": "."})
        self.assertIn("summary", out)
        self.assertIn("risk_score", out)
        self.assertIn("findings", out)
        self.assertIsInstance(out["findings"], list)
        self.assertGreaterEqual(int(out["risk_score"]), 0)
        self.assertLessEqual(int(out["risk_score"]), 100)

    def test_scanner_alias_via_run_agent(self) -> None:
        out = run_agent(
            agent="security-ops.agentic-security-scanner-agent",
            payload={"target_path": "."},
        )
        self.assertIn("summary", out)


if __name__ == "__main__":
    unittest.main()
