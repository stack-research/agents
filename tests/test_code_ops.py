from __future__ import annotations

import unittest

from local_agents.engine import run_agent, run_code_reviewer_agent, run_pr_summary_agent


class CodeOpsTests(unittest.TestCase):
    def test_code_reviewer_security_findings(self) -> None:
        out = run_code_reviewer_agent(
            {
                "diff": "+    password = 'hardcoded123'\n+    query = f'SELECT * FROM users WHERE id = {user_id}'",
                "context": "Auth module update",
            }
        )
        self.assertEqual(out["severity"], "critical")
        self.assertTrue(len(out["findings"]) >= 1)
        self.assertTrue(1 <= len(out["suggested_actions"]) <= 4)

    def test_code_reviewer_clean_diff(self) -> None:
        out = run_code_reviewer_agent(
            {
                "diff": "+    return x + y\n+    # simple addition",
            }
        )
        self.assertEqual(out["severity"], "clean")
        self.assertEqual(len(out["findings"]), 0)

    def test_code_reviewer_severity_enum(self) -> None:
        out = run_code_reviewer_agent({"diff": "+    except Exception:\n+        pass"})
        self.assertIn(out["severity"], {"clean", "minor", "major", "critical"})

    def test_pr_summary_shape(self) -> None:
        out = run_pr_summary_agent(
            {
                "title": "Add rate limiting to auth endpoints",
                "changed_files": [
                    "src/auth/middleware.py",
                    "src/auth/rate_limiter.py",
                    "tests/auth/test_rate_limiter.py",
                    "config/auth.yaml",
                ],
                "diff_summary": "Adds token bucket rate limiter.",
            }
        )
        self.assertIn(out["review_focus"], {"low", "medium", "high"})
        self.assertIsInstance(out["summary"], str)
        self.assertTrue(1 <= len(out["risk_areas"]) <= 4)

    def test_pr_summary_low_risk(self) -> None:
        out = run_pr_summary_agent(
            {
                "title": "Fix typo in readme",
                "changed_files": ["README.md"],
            }
        )
        self.assertEqual(out["review_focus"], "low")

    def test_pr_summary_high_risk(self) -> None:
        out = run_pr_summary_agent(
            {
                "title": "Update auth flow",
                "changed_files": ["src/auth/login.py", "src/security/tokens.py"],
            }
        )
        self.assertEqual(out["review_focus"], "high")

    def test_run_agent_aliases(self) -> None:
        review = run_agent(
            agent="code-ops.code-reviewer-agent",
            payload={"diff": "+    x = 1"},
        )
        summary = run_agent(
            agent="pr-summary-agent",
            payload={"title": "Update docs", "changed_files": ["docs/readme.md"]},
        )
        self.assertIn("severity", review)
        self.assertIn("review_focus", summary)


if __name__ == "__main__":
    unittest.main()
