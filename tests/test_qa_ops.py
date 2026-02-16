from __future__ import annotations

import unittest

from local_agents.engine import run_agent, run_regression_triage_agent, run_test_case_generator_agent


class QaOpsTests(unittest.TestCase):
    def test_test_case_generator_shape(self) -> None:
        out = run_test_case_generator_agent(
            {
                "feature": "SSO login flow",
                "acceptance_criteria": ["Users can sign in with SAML", "Invalid assertion is rejected"],
            }
        )
        self.assertIn(out["risk_focus"], {"low", "medium", "high"})
        self.assertTrue(4 <= len(out["test_cases"]) <= 8)

    def test_regression_triage_shape(self) -> None:
        out = run_regression_triage_agent(
            {
                "failure_summary": "Production timeout after dependency version upgrade",
                "changed_components": ["auth-service", "sdk-client"],
            }
        )
        self.assertIn(out["probable_cause"], {"code", "config", "dependency", "infra", "test-data", "unknown"})
        self.assertIn(out["severity"], {"sev1", "sev2", "sev3", "sev4"})
        self.assertTrue(2 <= len(out["recommended_actions"]) <= 4)

    def test_run_agent_aliases(self) -> None:
        cases = run_agent(
            agent="qa-ops.test-case-generator-agent",
            payload={"feature": "Password reset", "acceptance_criteria": ["Reset token expires in 15 minutes"]},
        )
        triage = run_agent(
            agent="regression-triage-agent",
            payload={
                "failure_summary": "Config flag mismatch causes intermittent failures",
                "changed_components": ["config-service"],
            },
        )
        self.assertIn("test_cases", cases)
        self.assertIn("probable_cause", triage)


if __name__ == "__main__":
    unittest.main()
