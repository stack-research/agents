from __future__ import annotations

import unittest

from local_agents.engine import (
    run_agent,
    run_blast_radius_assessor_agent,
    run_kill_path_auditor_agent,
    run_lineage_recorder_agent,
    run_scope_validator_agent,
)
from local_agents.core import ValidationError


class LineageRecorderTests(unittest.TestCase):
    def test_output_shape(self) -> None:
        out = run_lineage_recorder_agent(
            {
                "trigger": "payment-failed webhook",
                "knowledge": "3 prior failures; retry limit 5",
                "rules_applied": ["retry-if-under-limit"],
                "alternatives_considered": ["escalate-to-human"],
                "action_taken": "queued retry",
            }
        )
        self.assertIn("lineage_id", out)
        self.assertIn("record", out)
        self.assertIn("integrity_check", out)
        self.assertEqual(out["integrity_check"], "complete")
        self.assertIn("trigger", out["record"])
        self.assertIn("knowledge", out["record"])
        self.assertIn("rules_applied", out["record"])
        self.assertIn("alternatives_considered", out["record"])
        self.assertIn("action_taken", out["record"])

    def test_lineage_id_deterministic(self) -> None:
        payload = {
            "trigger": "deploy started",
            "knowledge": "staging env",
            "rules_applied": ["canary-first"],
            "alternatives_considered": ["full-rollout"],
            "action_taken": "canary deploy to 5%",
        }
        out1 = run_lineage_recorder_agent(payload)
        out2 = run_lineage_recorder_agent(payload)
        self.assertEqual(out1["lineage_id"], out2["lineage_id"])

    def test_missing_field_raises(self) -> None:
        with self.assertRaises(ValidationError):
            run_lineage_recorder_agent(
                {
                    "trigger": "x",
                    "knowledge": "y",
                    "rules_applied": ["r"],
                    "alternatives_considered": ["a"],
                }
            )

    def test_empty_rules_raises(self) -> None:
        with self.assertRaises(ValidationError):
            run_lineage_recorder_agent(
                {
                    "trigger": "x",
                    "knowledge": "y",
                    "rules_applied": [],
                    "alternatives_considered": ["a"],
                    "action_taken": "z",
                }
            )


class ScopeValidatorTests(unittest.TestCase):
    def test_pass_with_scope_and_reversibility(self) -> None:
        out = run_scope_validator_agent(
            {
                "action_description": "read user preferences",
                "permissions_requested": ["database-read", "audit-log-write"],
                "reversibility_plan": "rollback via config flag",
                "scope_boundary": "user preferences table only",
            }
        )
        self.assertEqual(out["verdict"], "pass")
        self.assertEqual(out["risk_level"], "low")
        self.assertTrue(1 <= len(out["findings"]) <= 5)

    def test_fail_destructive_no_reversibility_no_scope(self) -> None:
        out = run_scope_validator_agent(
            {
                "action_description": "delete all production logs",
                "permissions_requested": ["admin-write", "production-access", "pii-read"],
                "reversibility_plan": "",
                "scope_boundary": "",
            }
        )
        self.assertEqual(out["verdict"], "fail")
        self.assertEqual(out["risk_level"], "high")

    def test_review_destructive_with_reversibility(self) -> None:
        out = run_scope_validator_agent(
            {
                "action_description": "delete inactive accounts",
                "permissions_requested": ["database-write"],
                "reversibility_plan": "soft-delete with 30-day window",
                "scope_boundary": "us-east region",
            }
        )
        self.assertEqual(out["verdict"], "review")

    def test_missing_action_raises(self) -> None:
        with self.assertRaises(ValidationError):
            run_scope_validator_agent(
                {"permissions_requested": ["read"]}
            )


class BlastRadiusAssessorTests(unittest.TestCase):
    def test_output_shape(self) -> None:
        out = run_blast_radius_assessor_agent(
            {
                "service_name": "test-service",
                "permissions": ["database-read"],
                "dependencies": ["auth"],
                "resource_limits": {"rate_limit": "50 req/s"},
            }
        )
        self.assertIn("risk_score", out)
        self.assertIn("max_damage_potential", out)
        self.assertIn("detection_latency", out)
        self.assertIn("containment_time", out)
        self.assertIn("findings", out)
        self.assertIn("recommended_controls", out)
        self.assertTrue(0 <= out["risk_score"] <= 100)
        self.assertIn(out["max_damage_potential"], {"low", "medium", "high", "critical"})
        self.assertIn(out["detection_latency"], {"fast", "moderate", "slow"})
        self.assertIn(out["containment_time"], {"fast", "moderate", "slow"})
        self.assertEqual(len(out["recommended_controls"]), 3)

    def test_high_risk_permissions(self) -> None:
        out = run_blast_radius_assessor_agent(
            {
                "service_name": "admin-service",
                "permissions": ["admin-write", "pii-read", "delete-all", "external-api-call"],
                "dependencies": ["db", "cache", "queue", "external-svc"],
            }
        )
        self.assertGreaterEqual(out["risk_score"], 50)
        self.assertIn(out["max_damage_potential"], {"high", "critical"})

    def test_low_risk_service(self) -> None:
        out = run_blast_radius_assessor_agent(
            {
                "service_name": "static-page-server",
                "permissions": ["read-only"],
                "dependencies": [],
                "resource_limits": {"rate_limit": "10 req/s", "budget": "$1/day"},
            }
        )
        self.assertLessEqual(out["risk_score"], 25)

    def test_missing_permissions_raises(self) -> None:
        with self.assertRaises(ValidationError):
            run_blast_radius_assessor_agent(
                {"service_name": "svc", "permissions": []}
            )


class KillPathAuditorTests(unittest.TestCase):
    def test_full_coverage(self) -> None:
        out = run_kill_path_auditor_agent(
            {
                "system_name": "test-system",
                "capabilities": {
                    "throttle": "rate limit to 10%",
                    "degrade": "read-only mode",
                    "isolate": "network segmentation",
                    "hard_stop": "container kill",
                },
                "last_tested": "2026-03-01",
            }
        )
        self.assertEqual(out["coverage_score"], 4)
        self.assertEqual(out["escalation_readiness"], "ready")
        self.assertEqual(len(out["recommended_actions"]), 3)

    def test_partial_coverage(self) -> None:
        out = run_kill_path_auditor_agent(
            {
                "system_name": "partial-system",
                "capabilities": {
                    "throttle": "rate limit",
                    "degrade": "",
                    "isolate": "",
                    "hard_stop": "kill process",
                },
                "last_tested": "2026-01-15",
            }
        )
        self.assertEqual(out["coverage_score"], 2)
        self.assertEqual(out["escalation_readiness"], "partial")
        self.assertTrue(len(out["gaps"]) >= 2)

    def test_no_coverage(self) -> None:
        out = run_kill_path_auditor_agent(
            {
                "system_name": "new-system",
                "capabilities": {},
            }
        )
        self.assertEqual(out["coverage_score"], 0)
        self.assertEqual(out["escalation_readiness"], "unprepared")
        self.assertTrue(len(out["gaps"]) >= 4)

    def test_missing_system_name_raises(self) -> None:
        with self.assertRaises(ValidationError):
            run_kill_path_auditor_agent(
                {"capabilities": {"throttle": "x"}}
            )


class RunAgentAliasTests(unittest.TestCase):
    def test_short_names(self) -> None:
        out = run_agent(
            agent="lineage-recorder-agent",
            payload={
                "trigger": "event",
                "knowledge": "context",
                "rules_applied": ["rule-a"],
                "alternatives_considered": ["alt-a"],
                "action_taken": "action",
            },
        )
        self.assertIn("lineage_id", out)

    def test_qualified_names(self) -> None:
        out = run_agent(
            agent="control-ops.kill-path-auditor-agent",
            payload={
                "system_name": "svc",
                "capabilities": {"throttle": "yes"},
            },
        )
        self.assertIn("coverage_score", out)


if __name__ == "__main__":
    unittest.main()
