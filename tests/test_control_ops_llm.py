from __future__ import annotations

import os
import unittest

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
        self.assertIn(out["integrity_check"], {"complete", "partial"})


@unittest.skipUnless(OLLAMA_OK, SKIP_REASON)
class ScopeValidatorLLMTests(unittest.TestCase):
    def test_output_shape(self) -> None:
        out = run_agent(
            agent="control-ops.scope-validator-agent",
            payload={
                "action_description": "update user preferences",
                "permissions_requested": ["database-read"],
                "reversibility_plan": "rollback via flag",
                "scope_boundary": "user prefs table",
            },
            mode="llm",
        )
        self.assertIn(out["verdict"], {"pass", "fail", "review"})
        self.assertIn(out["risk_level"], {"low", "medium", "high"})
        self.assertTrue(1 <= len(out["findings"]) <= 5)


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


if __name__ == "__main__":
    unittest.main()
