from __future__ import annotations

import unittest

from local_agents.engine import run_agent, run_log_analyzer_agent, run_slo_reporter_agent


class ObservabilityOpsTests(unittest.TestCase):
    def test_log_analyzer_elevated(self) -> None:
        out = run_log_analyzer_agent(
            {
                "log_entries": [
                    "2026-03-12T10:00:01Z INFO auth-service: login successful",
                    "2026-03-12T10:00:02Z ERROR auth-service: connection timeout to db-primary",
                    "2026-03-12T10:00:03Z ERROR auth-service: connection timeout to db-primary",
                    "2026-03-12T10:00:04Z WARN auth-service: retry exhausted",
                    "2026-03-12T10:00:05Z ERROR auth-service: authentication failed user=unknown",
                ],
            }
        )
        self.assertIn(out["severity"], {"normal", "elevated", "critical"})
        self.assertTrue(1 <= len(out["patterns"]) <= 5)
        self.assertTrue(len(out["anomalies"]) <= 5)

    def test_log_analyzer_normal(self) -> None:
        out = run_log_analyzer_agent(
            {
                "log_entries": [
                    "2026-03-12T10:00:01Z INFO app: started",
                    "2026-03-12T10:00:02Z INFO app: health check ok",
                ],
            }
        )
        self.assertEqual(out["severity"], "normal")
        self.assertEqual(len(out["anomalies"]), 0)

    def test_log_analyzer_critical(self) -> None:
        out = run_log_analyzer_agent(
            {
                "log_entries": [
                    "ERROR out of memory",
                    "ERROR disk full",
                    "ERROR process crashed",
                ],
            }
        )
        self.assertEqual(out["severity"], "critical")

    def test_slo_reporter_breached(self) -> None:
        out = run_slo_reporter_agent(
            {
                "service_name": "api-gateway",
                "metrics": {"availability": 99.8, "latency_p99_ms": 450, "error_rate_percent": 1.2},
                "slo_targets": {"availability": 99.9, "latency_p99_ms": 500, "error_rate_percent": 1.0},
            }
        )
        self.assertEqual(out["compliance_status"], "breached")
        self.assertTrue(1 <= len(out["findings"]) <= 4)
        self.assertTrue(1 <= len(out["recommended_actions"]) <= 3)

    def test_slo_reporter_met(self) -> None:
        out = run_slo_reporter_agent(
            {
                "service_name": "api-gateway",
                "metrics": {"availability": 99.99, "latency_p99_ms": 100, "error_rate_percent": 0.1},
                "slo_targets": {"availability": 99.9, "latency_p99_ms": 500, "error_rate_percent": 1.0},
            }
        )
        self.assertEqual(out["compliance_status"], "met")

    def test_slo_reporter_at_risk(self) -> None:
        out = run_slo_reporter_agent(
            {
                "service_name": "api-gateway",
                "metrics": {"availability": 99.91},
                "slo_targets": {"availability": 99.9},
            }
        )
        self.assertEqual(out["compliance_status"], "met")

    def test_run_agent_aliases(self) -> None:
        logs = run_agent(
            agent="observability-ops.log-analyzer-agent",
            payload={"log_entries": ["INFO app started"]},
        )
        slo = run_agent(
            agent="slo-reporter-agent",
            payload={
                "service_name": "test",
                "metrics": {"availability": 100},
                "slo_targets": {"availability": 99.9},
            },
        )
        self.assertIn("severity", logs)
        self.assertIn("compliance_status", slo)


if __name__ == "__main__":
    unittest.main()
