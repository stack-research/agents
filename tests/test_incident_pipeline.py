from __future__ import annotations

import unittest

from scripts.run_incident_pipeline import run_pipeline


_MODE = "deterministic"
_MODEL = "llama3.2:3b"
_BASE = "http://localhost:11434"


class IncidentPipelineTests(unittest.TestCase):
    """Cross-domain incident pipeline: router -> triage -> qa -> synthesis -> governance -> checkpoint."""

    def test_pipeline_output_shape(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "incident-test-001",
                "incident_text": "Customers cannot login after the auth deploy",
                "customer_tier": "enterprise",
                "feature_area": "SSO authentication",
                "acceptance_criteria": ["Users can sign in with SAML"],
                "action_description": "Deploy hotfix to auth service",
                "permissions_requested": ["deploy:production"],
                "reversibility_plan": "Rollback via CI",
                "scope_boundary": "Auth service only",
            },
            mode=_MODE, model=_MODEL, base_url=_BASE,
        )
        self.assertIn(out.get("pipeline_status"), {"ok", "degraded", "blocked"})
        for key in ("route", "triage", "qa", "synthesis", "governance", "checkpoint"):
            self.assertIn(key, out, f"missing key: {key}")

    def test_pipeline_ok_path(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "incident-test-002",
                "incident_text": "Customers report slow page loads on dashboard",
                "customer_tier": "pro",
                "feature_area": "Dashboard rendering",
                "acceptance_criteria": ["Page loads under 2s"],
                "action_description": "Optimize dashboard queries",
                "permissions_requested": ["database-read"],
                "reversibility_plan": "Revert query changes",
                "scope_boundary": "Dashboard read replicas",
            },
            mode=_MODE, model=_MODEL, base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "ok")
        self.assertIn("target_agent", out["route"])
        self.assertIn("priority", out["triage"])
        self.assertIn("test_cases", out["qa"])
        self.assertIn("headline", out["synthesis"])
        self.assertIn("verdict", out["governance"])
        self.assertTrue(out["checkpoint"]["recorded"])

    def test_pipeline_blocked_by_governance(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "incident-test-003",
                "incident_text": "Need to delete all archived user records",
                "action_description": "Delete all archived user records from production",
                "permissions_requested": ["admin:write", "production:access", "pii:read"],
                "reversibility_plan": "",
                "scope_boundary": "",
            },
            mode=_MODE, model=_MODEL, base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "blocked")
        self.assertEqual(out["governance"]["verdict"], "fail")

    def test_pipeline_degrades_on_missing_incident_text(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "incident-test-004",
                "incident_text": None,
                "action_description": "Fix things",
                "permissions_requested": ["read"],
            },
            mode=_MODE, model=_MODEL, base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "degraded")
        self.assertEqual(out.get("failure_stage"), "router")

    def test_pipeline_degrades_on_empty_incident_text(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "incident-test-005",
                "incident_text": "",
            },
            mode=_MODE, model=_MODEL, base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "degraded")
        self.assertEqual(out.get("failure_stage"), "router")

    def test_pipeline_defaults_without_optional_fields(self) -> None:
        out = run_pipeline(
            {
                "incident_text": "Support ticket about billing confusion",
            },
            mode=_MODE, model=_MODEL, base_url=_BASE,
        )
        self.assertIn(out.get("pipeline_status"), {"ok", "degraded", "blocked"})
        self.assertIn("workflow_id", out)
        self.assertTrue(out["workflow_id"].startswith("incident-"))

    def test_triage_feeds_into_synthesis(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "incident-test-007",
                "incident_text": "Production outage affecting all users",
                "feature_area": "API gateway",
                "acceptance_criteria": ["Health check returns 200"],
                "action_description": "Restart API gateway pods",
                "permissions_requested": ["k8s:restart"],
                "reversibility_plan": "Pods auto-heal",
                "scope_boundary": "API gateway namespace",
            },
            mode=_MODE, model=_MODEL, base_url=_BASE,
        )
        if out.get("pipeline_status") in {"ok", "blocked"}:
            summary_text = out["synthesis"].get("summary", "")
            self.assertIn("Triage:", summary_text)
            self.assertIn("QA:", summary_text)

    def test_route_selects_support_triage(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "incident-test-008",
                "incident_text": "Customer cannot access their account after password reset",
                "action_description": "Check auth logs",
                "permissions_requested": ["logs:read"],
                "scope_boundary": "Auth logs only",
            },
            mode=_MODE, model=_MODEL, base_url=_BASE,
        )
        if out.get("pipeline_status") != "degraded":
            self.assertEqual(out["route"]["target_agent"], "support-ops.triage-agent")

    def test_qa_uses_feature_area(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "incident-test-009",
                "incident_text": "Payment failures reported",
                "feature_area": "Payment processing webhook",
                "acceptance_criteria": ["Webhooks retry on failure"],
                "action_description": "Review webhook handler",
                "permissions_requested": ["code:read"],
                "scope_boundary": "Payment service",
            },
            mode=_MODE, model=_MODEL, base_url=_BASE,
        )
        if out.get("pipeline_status") != "degraded":
            self.assertEqual(out["qa"]["risk_focus"], "high")

    def test_governance_blocks_destructive_unscoped(self) -> None:
        out = run_pipeline(
            {
                "workflow_id": "incident-test-010",
                "incident_text": "Database needs cleanup after incident",
                "action_description": "Purge all temporary records from production database",
                "permissions_requested": ["db:delete", "admin:root", "pii:access"],
                "reversibility_plan": "",
                "scope_boundary": "",
            },
            mode=_MODE, model=_MODEL, base_url=_BASE,
        )
        self.assertEqual(out.get("pipeline_status"), "blocked")
        self.assertEqual(out["governance"]["verdict"], "fail")
        self.assertEqual(out["governance"]["risk_level"], "high")


if __name__ == "__main__":
    unittest.main()
