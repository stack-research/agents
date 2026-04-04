from __future__ import annotations

import unittest
from datetime import date, timedelta

from scripts.run_resilience_pipeline import run_pipeline


_MODE = "deterministic"
_MODEL = "llama3.2:3b"
_BASE = "http://localhost:11434"


class ResiliencePipelineTests(unittest.TestCase):
    def test_pipeline_output_shape(self) -> None:
        out = run_pipeline(
            {
                "service_name": "test-service",
                "permissions": ["database-read"],
                "dependencies": ["auth"],
                "resource_limits": {"rate_limit": "50 req/s"},
                "capabilities": {
                    "throttle": "rate limit",
                    "degrade": "read-only",
                    "isolate": "network seg",
                    "hard_stop": "kill container",
                },
                "last_tested": (date.today() - timedelta(days=7)).isoformat(),
            },
            mode=_MODE,
            model=_MODEL,
            base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "ok")
        self.assertIn("blast_radius", out)
        self.assertIn("kill_path", out)
        self.assertIn("resilience_verdict", out)
        self.assertIn(out["resilience_verdict"], {"adequate", "partial", "at-risk", "inadequate"})

    def test_high_risk_low_coverage_is_inadequate(self) -> None:
        out = run_pipeline(
            {
                "service_name": "risky-service",
                "permissions": ["admin-write", "pii-read", "delete-all", "external-api-call"],
                "dependencies": ["db", "cache", "queue", "external"],
                "capabilities": {
                    "throttle": "rate limit",
                    "degrade": "",
                    "isolate": "",
                    "hard_stop": "",
                },
                "last_tested": "",
            },
            mode=_MODE,
            model=_MODEL,
            base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "ok")
        self.assertEqual(out["resilience_verdict"], "inadequate")

    def test_elevated_risk_low_coverage_is_at_risk(self) -> None:
        out = run_pipeline(
            {
                "service_name": "webhook-relay",
                "permissions": ["admin-write", "pii-read", "external-api-call"],
                "dependencies": ["message-queue", "public-webhook", "external-sink"],
                "capabilities": {
                    "throttle": "limit ingress",
                    "degrade": "",
                    "isolate": "",
                    "hard_stop": "kill process",
                },
                "last_tested": (date.today() - timedelta(days=30)).isoformat(),
            },
            mode=_MODE,
            model=_MODEL,
            base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "ok")
        self.assertEqual(out["resilience_verdict"], "at-risk")

    def test_full_coverage_low_risk_is_adequate(self) -> None:
        out = run_pipeline(
            {
                "service_name": "safe-service",
                "permissions": ["read-only"],
                "dependencies": [],
                "resource_limits": {"rate_limit": "10 req/s", "budget": "$1/day"},
                "capabilities": {
                    "throttle": "rate limit to 1%",
                    "degrade": "disable all writes",
                    "isolate": "network block",
                    "hard_stop": "container kill",
                },
                "last_tested": (date.today() - timedelta(days=15)).isoformat(),
            },
            mode=_MODE,
            model=_MODEL,
            base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "ok")
        self.assertEqual(out["resilience_verdict"], "adequate")

    def test_partial_is_default_for_other_combinations(self) -> None:
        out = run_pipeline(
            {
                "service_name": "internal-job-runner",
                "permissions": ["queue-write", "database-read"],
                "dependencies": ["scheduler", "queue"],
                "resource_limits": {"concurrency": 5},
                "capabilities": {
                    "throttle": "limit jobs",
                    "degrade": "pause optional queues",
                    "isolate": "disable downstream jobs",
                    "hard_stop": "",
                },
                "last_tested": (date.today() - timedelta(days=20)).isoformat(),
            },
            mode=_MODE,
            model=_MODEL,
            base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "ok")
        self.assertEqual(out["resilience_verdict"], "partial")

    def test_pipeline_degrades_on_invalid_service(self) -> None:
        out = run_pipeline(
            {
                "service_name": "",
                "permissions": ["read"],
                "capabilities": {"throttle": "yes"},
            },
            mode=_MODE,
            model=_MODEL,
            base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "degraded")
        self.assertEqual(out.get("failure_stage"), "blast-radius-assessor")

    def test_pipeline_degrades_on_missing_permissions(self) -> None:
        out = run_pipeline(
            {
                "service_name": "svc",
                "permissions": None,
                "capabilities": {"throttle": "yes"},
            },
            mode=_MODE,
            model=_MODEL,
            base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "degraded")


if __name__ == "__main__":
    unittest.main()
