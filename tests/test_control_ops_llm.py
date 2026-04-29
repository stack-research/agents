from __future__ import annotations

import os
import unittest
from datetime import date, timedelta

from local_agents.engine import run_agent

LLM_MODE = os.getenv("AGENT_MODE", "deterministic") == "llm"


def _ollama_reachable() -> bool:
    if not LLM_MODE:
        return False
    try:
        import urllib.request

        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        return True
    except Exception:
        return False


OLLAMA_OK = _ollama_reachable()
SKIP_REASON = "AGENT_MODE!=llm or Ollama unavailable"


@unittest.skipUnless(OLLAMA_OK, SKIP_REASON)
class LineageRecorderLLMTests(unittest.TestCase):
    def test_output_shape(self) -> None:
        out = run_agent(
            agent="control-ops.lineage-recorder-agent",
            payload={
                "trigger": "payment-failed webhook",
                "knowledge": "3 prior failures; retry limit 5",
                "rules_applied": ["retry-if-under-limit"],
                "alternatives_considered": ["escalate-to-human"],
                "action_taken": "queued retry",
            },
            mode="llm",
        )
        self.assertIn("lineage_id", out)
        self.assertIn("record", out)
        self.assertIn("integrity_check", out)
        self.assertRegex(out["lineage_id"], r"^[a-z0-9-]+--[a-z0-9-]+-[0-9a-f]{8}$")


@unittest.skipUnless(OLLAMA_OK, SKIP_REASON)
class ScopeValidatorLLMTests(unittest.TestCase):
    def test_pass_path(self) -> None:
        out = run_agent(
            agent="control-ops.scope-validator-agent",
            payload={
                "action_description": "read user preferences",
                "permissions_requested": ["database-read", "audit-log"],
                "reversibility_plan": "rollback via flag",
                "scope_boundary": "user prefs table only",
            },
            mode="llm",
        )
        self.assertEqual(out["verdict"], "pass")
        self.assertEqual(out["risk_level"], "low")

    def test_review_path(self) -> None:
        out = run_agent(
            agent="control-ops.scope-validator-agent",
            payload={
                "action_description": "delete inactive accounts",
                "permissions_requested": ["database-write"],
                "reversibility_plan": "soft-delete with 30-day window",
                "scope_boundary": "us-east region",
            },
            mode="llm",
        )
        self.assertEqual(out["verdict"], "review")
        self.assertEqual(out["risk_level"], "medium")


@unittest.skipUnless(OLLAMA_OK, SKIP_REASON)
class ExceptionPolicyLLMTests(unittest.TestCase):
    def test_exception_policy_output_shape(self) -> None:
        out = run_agent(
            agent="control-ops.exception-policy-agent",
            payload={
                "action_id": "prod-maint-window",
                "scope": "prod logs region one",
                "requested_by": "ops",
                "owner": "security",
                "justification": "incident mitigation for saturation risk",
                "expires_at": (date.today() + timedelta(days=7)).isoformat(),
            },
            mode="llm",
        )
        self.assertIn(out["exception_verdict"], {"approved", "review", "denied"})
        self.assertIn("exception_id", out)


@unittest.skipUnless(OLLAMA_OK, SKIP_REASON)
class ApprovalMemoryLLMTests(unittest.TestCase):
    def test_approval_memory_output_shape(self) -> None:
        out = run_agent(
            agent="approval-memory-agent",
            payload={
                "approval_subject": "prod-maint-window",
                "approver": "security-owner",
                "approved_at": date.today().isoformat(),
                "expires_at": (date.today() + timedelta(days=7)).isoformat(),
                "metadata": {"ticket": "GOV-501"},
            },
            mode="llm",
        )
        self.assertIn("approval_record_id", out)
        self.assertIn("active", out)
        self.assertIn("expired", out)


@unittest.skipUnless(OLLAMA_OK, SKIP_REASON)
class BlastRadiusAssessorLLMTests(unittest.TestCase):
    def test_output_shape(self) -> None:
        out = run_agent(
            agent="control-ops.blast-radius-assessor-agent",
            payload={
                "service_name": "test-svc",
                "permissions": ["database-read"],
                "dependencies": ["auth"],
            },
            mode="llm",
        )
        self.assertTrue(0 <= out["risk_score"] <= 100)
        self.assertIn(out["max_damage_potential"], {"low", "medium", "high", "critical"})
        self.assertEqual(len(out["recommended_controls"]), 3)

    def test_high_risk_path(self) -> None:
        out = run_agent(
            agent="control-ops.blast-radius-assessor-agent",
            payload={
                "service_name": "admin-svc",
                "permissions": ["admin-write", "pii-read", "delete-all", "external-api-call"],
                "dependencies": ["db", "queue", "external"],
            },
            mode="llm",
        )
        self.assertGreaterEqual(out["risk_score"], 40)
        self.assertEqual(out["detection_latency"], "slow")


@unittest.skipUnless(OLLAMA_OK, SKIP_REASON)
class KillPathAuditorLLMTests(unittest.TestCase):
    def test_output_shape(self) -> None:
        out = run_agent(
            agent="control-ops.kill-path-auditor-agent",
            payload={
                "system_name": "test-system",
                "capabilities": {
                    "throttle": "rate limit",
                    "degrade": "",
                    "isolate": "network seg",
                    "hard_stop": "kill container",
                },
            },
            mode="llm",
        )
        self.assertTrue(0 <= out["coverage_score"] <= 4)
        self.assertIn(out["escalation_readiness"], {"ready", "partial", "unprepared"})
        self.assertEqual(len(out["recommended_actions"]), 3)

    def test_recent_full_coverage_is_ready(self) -> None:
        out = run_agent(
            agent="control-ops.kill-path-auditor-agent",
            payload={
                "system_name": "ready-system",
                "capabilities": {
                    "throttle": "rate limit",
                    "degrade": "read-only",
                    "isolate": "network seg",
                    "hard_stop": "kill container",
                },
                "last_tested": (date.today() - timedelta(days=5)).isoformat(),
            },
            mode="llm",
        )
        self.assertEqual(out["coverage_score"], 4)
        self.assertEqual(out["escalation_readiness"], "ready")


if __name__ == "__main__":
    unittest.main()
