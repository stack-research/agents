from __future__ import annotations

import unittest

from local_agents.engine import (
    run_agent,
    run_classifier_agent,
    run_heartbeat_agent,
    run_reply_drafter_agent,
    run_triage_agent,
)


class HeartbeatAgentTests(unittest.TestCase):
    def test_warn_when_stale(self) -> None:
        output = run_heartbeat_agent(
            {
                "service_name": "billing-api",
                "heartbeat_age_seconds": 40,
                "error_rate_percent": 1.0,
            }
        )
        self.assertEqual(output["status"], "warn")

    def test_escalates_on_error_rate(self) -> None:
        output = run_heartbeat_agent(
            {
                "service_name": "billing-api",
                "heartbeat_age_seconds": 20,
                "error_rate_percent": 7.0,
            }
        )
        self.assertEqual(output["status"], "warn")


class ClassifierAgentTests(unittest.TestCase):
    def test_feature_request_label(self) -> None:
        output = run_classifier_agent(
            {
                "text": "Please add SSO support for our workspace.",
                "labels": [
                    "bug-report",
                    "billing",
                    "feature-request",
                    "support",
                    "feedback",
                    "unknown",
                ],
            }
        )
        self.assertEqual(output["label"], "feature-request")
        self.assertGreaterEqual(output["confidence"], 0.55)

    def test_unknown_for_ambiguous_text(self) -> None:
        output = run_classifier_agent(
            {
                "text": "Hello team.",
                "labels": ["billing", "feature-request", "unknown"],
            }
        )
        self.assertEqual(output["label"], "unknown")

    def test_run_agent_defaults_to_deterministic(self) -> None:
        output = run_agent(
            agent="starter-kit.classifier-agent",
            payload={"text": "Please add dark mode."},
        )
        self.assertIn(output["label"], {"feature-request", "unknown", "support"})


class TriageAgentTests(unittest.TestCase):
    def test_access_issue(self) -> None:
        output = run_triage_agent(
            {
                "text": "Users cannot login after release.",
                "customer_tier": "pro",
            }
        )
        self.assertEqual(output["category"], "access")
        self.assertIn(output["priority"], {"p1", "p2", "p3", "p4"})

    def test_enterprise_escalation(self) -> None:
        output = run_triage_agent(
            {
                "text": "Need refund for duplicate invoice",
                "customer_tier": "enterprise",
            }
        )
        self.assertEqual(output["category"], "billing")
        self.assertIn(output["priority"], {"p1", "p2", "p3"})


class ReplyDrafterAgentTests(unittest.TestCase):
    def test_reply_shape(self) -> None:
        output = run_reply_drafter_agent(
            {
                "customer_name": "Alex",
                "priority": "p2",
                "category": "access",
                "issue_summary": "Users cannot sign in after password reset.",
            }
        )
        self.assertIsInstance(output["subject"], str)
        self.assertIsInstance(output["reply"], str)
        self.assertGreater(len(output["subject"].strip()), 0)
        self.assertGreater(len(output["reply"].strip()), 0)

    def test_run_agent_alias(self) -> None:
        output = run_agent(
            agent="reply-drafter-agent",
            payload={
                "priority": "p3",
                "category": "billing",
                "issue_summary": "Duplicate charge on invoice",
            },
        )
        self.assertIn("subject", output)
        self.assertIn("reply", output)


if __name__ == "__main__":
    unittest.main()
