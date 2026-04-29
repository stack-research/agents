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
class ObservabilityOpsLLMTests(unittest.TestCase):
    def test_change_correlation_output_shape(self) -> None:
        out = run_agent(
            agent="observability-ops.change-correlation-agent",
            payload={
                "incident_signals": [
                    {
                        "timestamp": "2026-04-02T14:05:00Z",
                        "service": "checkout-api",
                        "metric": "error_rate_percent",
                        "baseline": 0.4,
                        "observed": 2.7,
                        "severity": "critical",
                    }
                ],
                "deploy_events": [
                    {
                        "timestamp": "2026-04-02T13:58:00Z",
                        "service": "checkout-api",
                        "event": "deploy",
                    }
                ],
            },
            mode="llm",
        )
        self.assertIn("correlated_events", out)
        self.assertIn("incident_signals", out)
        self.assertTrue(0 <= out["confidence"] <= 1)
        self.assertTrue(isinstance(out["summary"], str) and out["summary"])

    def test_alert_tuner_output_shape(self) -> None:
        out = run_agent(
            agent="alert-tuner-agent",
            payload={
                "alert_history": [
                    {
                        "metric": "latency_p99_ms",
                        "threshold": 400,
                        "trigger_count": 42,
                        "actionable_count": 8,
                        "window": "7d",
                    }
                ],
                "target_precision": 0.6,
            },
            mode="llm",
        )
        self.assertIn("tuning_recommendations", out)
        self.assertIn("incident_signals", out)
        self.assertTrue(0 <= out["noise_score"] <= 1)
        self.assertTrue(isinstance(out["rationale"], str) and out["rationale"])


if __name__ == "__main__":
    unittest.main()
