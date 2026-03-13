#!/usr/bin/env python3
"""Generate eval fixture files for all catalog agents.

Curated inputs are defined here. Expected outputs are captured by running each
input through the deterministic engine.  Output is written to
  catalog/projects/<project>/agents/<agent>/evals/cases.json

Usage:
    python3 scripts/generate_eval_fixtures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from local_agents.engine import run_agent  # noqa: E402

# ---------------------------------------------------------------------------
# Curated inputs per agent.
# Each entry: (case_id, tags, input_payload, extra_assertions)
# ---------------------------------------------------------------------------

CASES: dict[str, list[tuple[str, list[str], dict, list[dict]]]] = {
    # ── starter-kit ────────────────────────────────────────────────
    "starter-kit.heartbeat-agent": [
        ("healthy-service", ["happy-path"], {
            "service_name": "api-gateway",
            "heartbeat_age_seconds": 10,
            "error_rate_percent": 1.5,
        }, [
            {"field": "status", "op": "eq", "value": "ok"},
            {"field": "report", "op": "contains", "value": "api-gateway"},
            {"field": "report", "op": "max_words", "value": 45},
        ]),
        ("warn-age", ["happy-path"], {
            "service_name": "auth-service",
            "heartbeat_age_seconds": 45,
            "error_rate_percent": 2.0,
        }, [
            {"field": "status", "op": "eq", "value": "warn"},
        ]),
        ("critical-age", ["happy-path"], {
            "service_name": "db-proxy",
            "heartbeat_age_seconds": 120,
            "error_rate_percent": 0.5,
        }, [
            {"field": "status", "op": "eq", "value": "critical"},
        ]),
        ("error-escalation", ["edge-case"], {
            "service_name": "payment-svc",
            "heartbeat_age_seconds": 50,
            "error_rate_percent": 8.0,
        }, [
            {"field": "status", "op": "eq", "value": "critical"},
        ]),
        ("negative-clamped", ["boundary"], {
            "service_name": "worker",
            "heartbeat_age_seconds": -5,
            "error_rate_percent": -1,
        }, [
            {"field": "status", "op": "eq", "value": "ok"},
            {"field": "report", "op": "contains", "value": "clamped"},
        ]),
        ("zero-boundary", ["boundary"], {
            "service_name": "cache",
            "heartbeat_age_seconds": 0,
            "error_rate_percent": 0,
        }, [
            {"field": "status", "op": "eq", "value": "ok"},
        ]),
        ("exact-threshold-30", ["boundary"], {
            "service_name": "cdn",
            "heartbeat_age_seconds": 30,
            "error_rate_percent": 5,
        }, [
            {"field": "status", "op": "eq", "value": "ok"},
        ]),
        ("exact-threshold-31", ["boundary"], {
            "service_name": "cdn",
            "heartbeat_age_seconds": 31,
            "error_rate_percent": 5,
        }, [
            {"field": "status", "op": "eq", "value": "warn"},
        ]),
    ],
    "starter-kit.classifier-agent": [
        ("billing-clear", ["happy-path"], {
            "text": "I was charged twice on my invoice for the subscription",
        }, [
            {"field": "label", "op": "eq", "value": "billing"},
            {"field": "confidence", "op": "range", "value": [0.55, 0.95]},
        ]),
        ("bug-clear", ["happy-path"], {
            "text": "The app crashes with an error every time I open it",
        }, [
            {"field": "label", "op": "eq", "value": "bug-report"},
        ]),
        ("feature-request", ["happy-path"], {
            "text": "Please add support for dark mode enhancement",
        }, [
            {"field": "label", "op": "eq", "value": "feature-request"},
        ]),
        ("ambiguous-text", ["edge-case"], {
            "text": "Hello, I have a question about your product.",
        }, [
            {"field": "confidence", "op": "range", "value": [0.3, 0.5]},
        ]),
        ("empty-labels-unknown", ["edge-case"], {
            "text": "nothing matches here",
            "labels": ["billing", "bug-report", "unknown"],
        }, [
            {"field": "label", "op": "eq", "value": "unknown"},
        ]),
    ],
    # ── support-ops ────────────────────────────────────────────────
    "support-ops.triage-agent": [
        ("outage-p1", ["happy-path"], {
            "text": "Production is down, complete outage for all users",
            "customer_tier": "free",
        }, [
            {"field": "priority", "op": "eq", "value": "p1"},
            {"field": "category", "op": "in", "value": ["bug", "other"]},
        ]),
        ("billing-free", ["happy-path"], {
            "text": "I need a refund for my last invoice payment",
            "customer_tier": "free",
        }, [
            {"field": "priority", "op": "eq", "value": "p3"},
            {"field": "category", "op": "eq", "value": "billing"},
        ]),
        ("access-enterprise", ["happy-path"], {
            "text": "Users cannot login to SSO since the update",
            "customer_tier": "enterprise",
        }, [
            {"field": "category", "op": "eq", "value": "access"},
        ]),
        ("enterprise-bump", ["edge-case"], {
            "text": "How do I configure the API integration?",
            "customer_tier": "enterprise",
        }, [
            {"field": "category", "op": "eq", "value": "how-to"},
        ]),
        ("default-tier", ["boundary"], {
            "text": "General question about your service",
        }, [
            {"field": "priority", "op": "in", "value": ["p3", "p4"]},
        ]),
    ],
    "support-ops.reply-drafter-agent": [
        ("billing-p2", ["happy-path"], {
            "priority": "p2",
            "category": "billing",
            "issue_summary": "Double charge on monthly subscription",
            "customer_name": "Alice",
        }, [
            {"field": "subject", "op": "eq", "value": "Update on your billing request"},
            {"field": "reply", "op": "contains", "value": "Hi Alice,"},
            {"field": "reply", "op": "contains", "value": "within 60 minutes"},
        ]),
        ("access-no-name", ["edge-case"], {
            "priority": "p1",
            "category": "access",
            "issue_summary": "All users locked out of the portal",
        }, [
            {"field": "reply", "op": "contains", "value": "Hi,"},
            {"field": "reply", "op": "contains", "value": "within 30 minutes"},
        ]),
        ("how-to-p4", ["happy-path"], {
            "priority": "p4",
            "category": "how-to",
            "issue_summary": "Need help setting up API keys",
            "customer_name": "Bob",
        }, [
            {"field": "subject", "op": "eq", "value": "Guidance for your setup question"},
            {"field": "reply", "op": "contains", "value": "within two business days"},
        ]),
    ],
    "support-ops.summary-agent": [
        ("mixed-tickets", ["happy-path"], {
            "period_start": "2026-03-01",
            "period_end": "2026-03-07",
            "tickets": [
                {"priority": "p1", "category": "access"},
                {"priority": "p2", "category": "access"},
                {"priority": "p3", "category": "billing"},
                {"priority": "p4", "category": "bug"},
                {"priority": "p2", "category": "access"},
            ],
            "top_n_actions": 3,
        }, [
            {"field": "ticket_count", "op": "eq", "value": 5},
            {"field": "priority_breakdown", "op": "has_keys", "value": ["p1", "p2", "p3", "p4"]},
            {"field": "top_categories", "op": "min_length", "value": 1},
            {"field": "recommended_actions", "op": "length", "value": 3},
        ]),
        ("empty-tickets", ["edge-case"], {
            "period_start": "2026-03-01",
            "period_end": "2026-03-07",
            "tickets": [],
            "top_n_actions": 3,
        }, [
            {"field": "ticket_count", "op": "eq", "value": 0},
            {"field": "top_categories", "op": "length", "value": 0},
        ]),
        ("p1-special-action", ["edge-case"], {
            "period_start": "2026-03-01",
            "period_end": "2026-03-07",
            "tickets": [
                {"priority": "p1", "category": "bug"},
            ],
            "top_n_actions": 2,
        }, [
            {"field": "recommended_actions.0", "op": "contains", "value": "p1"},
            {"field": "recommended_actions", "op": "length", "value": 2},
        ]),
        ("top-n-four", ["boundary"], {
            "period_start": "2026-01-01",
            "period_end": "2026-01-07",
            "tickets": [
                {"priority": "p3", "category": "feature"},
                {"priority": "p4", "category": "how-to"},
            ],
            "top_n_actions": 4,
        }, [
            {"field": "recommended_actions", "op": "length", "value": 4},
        ]),
    ],
    "support-ops.handoff-agent": [
        ("active-incidents", ["happy-path"], {
            "shift_label": "APAC Night Shift",
            "incidents": [
                {"id": "INC-101", "severity": "sev1", "status": "investigating", "owner": "oncall-a", "next_step": "check logs"},
                {"id": "INC-102", "severity": "sev3", "status": "monitoring", "owner": "oncall-b", "next_step": "watch metrics"},
            ],
        }, [
            {"field": "active_count", "op": "eq", "value": 2},
            {"field": "critical_items", "op": "min_length", "value": 1},
            {"field": "handoff_brief", "op": "contains", "value": "APAC Night Shift"},
        ]),
        ("all-resolved", ["edge-case"], {
            "shift_label": "EU Day Shift",
            "incidents": [
                {"id": "INC-200", "severity": "sev2", "status": "resolved", "owner": "oncall-c", "next_step": ""},
            ],
        }, [
            {"field": "active_count", "op": "eq", "value": 0},
        ]),
        ("unowned-incident", ["edge-case"], {
            "shift_label": "US West Shift",
            "incidents": [
                {"id": "INC-300", "severity": "sev2", "status": "investigating", "owner": "", "next_step": "triage"},
            ],
        }, [
            {"field": "active_count", "op": "eq", "value": 1},
            {"field": "recommended_checks.0", "op": "contains", "value": "unowned"},
        ]),
    ],
    # ── planner-executor ───────────────────────────────────────────
    "planner-executor.planner-agent": [
        ("security-goal", ["happy-path"], {
            "goal": "Investigate a potential security breach in the auth service",
            "constraints": ["Must complete within 2 hours", "No production changes without approval"],
        }, [
            {"field": "risk_level", "op": "eq", "value": "high"},
            {"field": "plan_steps", "op": "min_length", "value": 5},
        ]),
        ("low-risk-goal", ["happy-path"], {
            "goal": "Update the README with new contributor guidelines",
        }, [
            {"field": "risk_level", "op": "eq", "value": "low"},
            {"field": "plan_steps", "op": "min_length", "value": 5},
        ]),
        ("migration-medium", ["edge-case"], {
            "goal": "Migrate user data to the new database schema",
            "constraints": [],
        }, [
            {"field": "risk_level", "op": "eq", "value": "medium"},
        ]),
    ],
    "planner-executor.executor-agent": [
        ("short-plan", ["happy-path"], {
            "plan_steps": ["Step A", "Step B", "Step C"],
            "context": "Routine maintenance window",
        }, [
            {"field": "status", "op": "in", "value": ["done", "partial"]},
            {"field": "completed_steps", "op": "range", "value": [1, 3]},
            {"field": "summary", "op": "type", "value": "string"},
        ]),
        ("no-context", ["edge-case"], {
            "plan_steps": ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],
        }, [
            {"field": "status", "op": "eq", "value": "partial"},
            {"field": "completed_steps", "op": "eq", "value": 3},
            {"field": "blocked_steps", "op": "eq", "value": 2},
        ]),
        ("single-step", ["boundary"], {
            "plan_steps": ["Do the thing"],
            "context": "urgent fix",
        }, [
            {"field": "completed_steps", "op": "range", "value": [1, 1]},
            {"field": "status", "op": "eq", "value": "done"},
        ]),
    ],
    # ── research-ops ───────────────────────────────────────────────
    "research-ops.retrieval-agent": [
        ("with-sources", ["happy-path"], {
            "query": "What are the best practices for API rate limiting?",
            "sources": ["Use token buckets", "Set per-client quotas"],
            "max_points": 4,
        }, [
            {"field": "notes", "op": "min_length", "value": 3},
            {"field": "confidence", "op": "eq", "value": 0.65},
        ]),
        ("no-sources", ["edge-case"], {
            "query": "Explain container orchestration patterns",
            "sources": [],
            "max_points": 3,
        }, [
            {"field": "confidence", "op": "eq", "value": 0.45},
            {"field": "notes", "op": "min_length", "value": 1},
        ]),
        ("max-points-one", ["boundary"], {
            "query": "Single point query",
            "sources": ["Source A", "Source B"],
            "max_points": 1,
        }, [
            {"field": "notes", "op": "length", "value": 1},
        ]),
    ],
    "research-ops.synthesis-agent": [
        ("brief-engineering", ["happy-path"], {
            "notes": ["Token bucket is standard", "Per-client quotas improve fairness"],
            "audience": "engineering",
            "output_format": "brief",
        }, [
            {"field": "headline", "op": "eq", "value": "Engineering Brief Summary"},
            {"field": "summary", "op": "contains", "value": "Key findings"},
            {"field": "next_actions", "op": "length", "value": 3},
        ]),
        ("report-leadership", ["happy-path"], {
            "notes": ["Q1 revenue grew 15%", "Churn down 2%", "NPS at 72"],
            "audience": "leadership",
            "output_format": "report",
        }, [
            {"field": "headline", "op": "eq", "value": "Leadership Report Summary"},
            {"field": "summary", "op": "contains", "value": "Research report summary"},
        ]),
    ],
    # ── qa-ops ─────────────────────────────────────────────────────
    "qa-ops.test-case-generator-agent": [
        ("auth-feature", ["happy-path"], {
            "feature": "SSO authentication flow",
            "acceptance_criteria": ["Users can sign in with SAML", "Session persists for 24h"],
        }, [
            {"field": "test_cases", "op": "length", "value": 5},
            {"field": "risk_focus", "op": "eq", "value": "high"},
        ]),
        ("simple-feature", ["happy-path"], {
            "feature": "Dark mode toggle",
            "acceptance_criteria": ["Theme switches instantly"],
        }, [
            {"field": "risk_focus", "op": "eq", "value": "medium"},
            {"field": "test_cases", "op": "min_length", "value": 4},
        ]),
        ("no-criteria", ["edge-case"], {
            "feature": "Export CSV report",
        }, [
            {"field": "test_cases", "op": "min_length", "value": 4},
        ]),
        ("payment-high-risk", ["edge-case"], {
            "feature": "Payment processing webhook",
            "acceptance_criteria": ["Handles retries"],
        }, [
            {"field": "risk_focus", "op": "eq", "value": "high"},
        ]),
    ],
    "qa-ops.regression-triage-agent": [
        ("dependency-failure", ["happy-path"], {
            "failure_summary": "Failure after dependency version update in SDK package",
            "changed_components": ["auth-service", "sdk-client"],
        }, [
            {"field": "probable_cause", "op": "eq", "value": "dependency"},
            {"field": "severity", "op": "eq", "value": "sev3"},
            {"field": "recommended_actions", "op": "length", "value": 3},
        ]),
        ("config-issue", ["happy-path"], {
            "failure_summary": "Application fails after config flag change in staging env",
            "changed_components": ["config-service"],
        }, [
            {"field": "probable_cause", "op": "eq", "value": "config"},
        ]),
        ("data-loss-sev1", ["edge-case"], {
            "failure_summary": "Data loss detected in backup restoration process",
            "changed_components": ["backup-svc"],
        }, [
            {"field": "severity", "op": "eq", "value": "sev1"},
        ]),
        ("minor-cosmetic", ["boundary"], {
            "failure_summary": "Minor cosmetic alignment issue in dashboard header",
            "changed_components": [],
        }, [
            {"field": "severity", "op": "eq", "value": "sev4"},
            {"field": "probable_cause", "op": "eq", "value": "unknown"},
        ]),
    ],
    # ── workflow-ops ───────────────────────────────────────────────
    "workflow-ops.router-agent": [
        ("support-route", ["happy-path"], {
            "task": "A customer reported they cannot login to their account",
            "available_agents": [],
        }, [
            {"field": "target_agent", "op": "eq", "value": "support-ops.triage-agent"},
            {"field": "priority", "op": "in", "value": ["p1", "p2", "p3", "p4"]},
        ]),
        ("qa-route", ["happy-path"], {
            "task": "Generate acceptance test scenarios for the new API",
            "available_agents": [],
        }, [
            {"field": "target_agent", "op": "eq", "value": "qa-ops.test-case-generator-agent"},
        ]),
        ("critical-priority", ["edge-case"], {
            "task": "Critical production outage affecting all customers",
            "available_agents": [],
        }, [
            {"field": "priority", "op": "eq", "value": "p1"},
        ]),
        ("fallback-unavailable", ["edge-case"], {
            "task": "Investigate a customer support ticket",
            "available_agents": ["planner-executor.planner-agent"],
        }, [
            {"field": "target_agent", "op": "eq", "value": "planner-executor.planner-agent"},
            {"field": "rationale", "op": "contains", "value": "unavailable"},
        ]),
        ("default-planner", ["boundary"], {
            "task": "Build a new onboarding flow for the mobile app",
            "available_agents": [],
        }, [
            {"field": "target_agent", "op": "eq", "value": "planner-executor.planner-agent"},
        ]),
    ],
    "workflow-ops.checkpoint-agent": [
        ("in-progress", ["happy-path"], {
            "workflow_id": "release-2026-03-10",
            "stage": "qa-validation",
            "status": "in_progress",
            "notes": "Integration tests running on staging.",
        }, [
            {"field": "recorded", "op": "eq", "value": True},
            {"field": "checkpoint_id", "op": "contains", "value": "release-2026-03-10"},
            {"field": "summary", "op": "contains", "value": "qa-validation"},
        ]),
        ("completed-no-notes", ["edge-case"], {
            "workflow_id": "deploy-v2",
            "stage": "rollout",
            "status": "completed",
        }, [
            {"field": "recorded", "op": "eq", "value": True},
            {"field": "summary", "op": "contains", "value": "No notes"},
        ]),
        ("failed-checkpoint", ["edge-case"], {
            "workflow_id": "migration-job",
            "stage": "schema-apply",
            "status": "failed",
            "notes": "Column type mismatch on users table.",
        }, [
            {"field": "checkpoint_id", "op": "contains", "value": "failed"},
        ]),
    ],
    # ── control-ops ────────────────────────────────────────────────
    "control-ops.lineage-recorder-agent": [
        ("complete-record", ["happy-path"], {
            "trigger": "Customer escalation from support queue",
            "knowledge": "Tier mapping policy requires enterprise escalation",
            "rules_applied": ["Enterprise SLA clause 4.2", "Priority override policy"],
            "alternatives_considered": ["Standard queue routing", "Self-service portal redirect"],
            "action_taken": "Escalated to dedicated enterprise support team",
        }, [
            {"field": "integrity_check", "op": "eq", "value": "complete"},
            {"field": "lineage_id", "op": "type", "value": "string"},
            {"field": "record", "op": "has_keys", "value": ["trigger", "knowledge", "rules_applied", "alternatives_considered", "action_taken"]},
        ]),
    ],
    "control-ops.scope-validator-agent": [
        ("safe-read-action", ["happy-path"], {
            "action_description": "Read user preferences from the settings API",
            "permissions_requested": ["settings:read"],
            "reversibility_plan": "Read-only, no changes needed",
            "scope_boundary": "User settings service only",
        }, [
            {"field": "verdict", "op": "eq", "value": "pass"},
            {"field": "risk_level", "op": "eq", "value": "low"},
        ]),
        ("destructive-no-plan", ["edge-case"], {
            "action_description": "Delete all archived user records from production",
            "permissions_requested": ["db:delete", "admin:write", "pii:access"],
            "reversibility_plan": "",
            "scope_boundary": "",
        }, [
            {"field": "verdict", "op": "eq", "value": "fail"},
            {"field": "risk_level", "op": "eq", "value": "high"},
        ]),
        ("destructive-with-plan", ["edge-case"], {
            "action_description": "Remove stale cache entries from Redis cluster",
            "permissions_requested": ["cache:delete"],
            "reversibility_plan": "Cache auto-repopulates within 5 minutes",
            "scope_boundary": "Redis staging cluster only",
        }, [
            {"field": "verdict", "op": "eq", "value": "review"},
            {"field": "risk_level", "op": "in", "value": ["medium", "high"]},
        ]),
        ("update-medium-risk", ["boundary"], {
            "action_description": "Update feature flag for dark mode rollout",
            "permissions_requested": ["flags:write"],
            "scope_boundary": "Feature flag service",
        }, [
            {"field": "risk_level", "op": "eq", "value": "medium"},
        ]),
    ],
    "control-ops.blast-radius-assessor-agent": [
        ("low-risk-service", ["happy-path"], {
            "service_name": "static-asset-cdn",
            "permissions": ["cdn:read"],
            "dependencies": [],
            "resource_limits": {"max_rps": 1000},
        }, [
            {"field": "risk_score", "op": "range", "value": [0, 25]},
            {"field": "max_damage_potential", "op": "eq", "value": "low"},
            {"field": "containment_time", "op": "eq", "value": "fast"},
        ]),
        ("high-risk-service", ["happy-path"], {
            "service_name": "payment-processor",
            "permissions": ["pii:read", "db:write", "billing:admin"],
            "dependencies": ["auth-service", "ledger-db", "stripe-api"],
            "resource_limits": {},
        }, [
            {"field": "risk_score", "op": "range", "value": [50, 100]},
            {"field": "max_damage_potential", "op": "in", "value": ["high", "critical"]},
            {"field": "findings", "op": "min_length", "value": 2},
            {"field": "recommended_controls", "op": "length", "value": 3},
        ]),
        ("external-dependency", ["edge-case"], {
            "service_name": "webhook-relay",
            "permissions": ["external:api-call", "queue:write"],
            "dependencies": ["message-queue"],
        }, [
            {"field": "detection_latency", "op": "eq", "value": "slow"},
        ]),
    ],
    "control-ops.kill-path-auditor-agent": [
        ("full-coverage", ["happy-path"], {
            "system_name": "order-processor",
            "capabilities": {
                "throttle": "Rate limit to 10 rps via API gateway",
                "degrade": "Disable non-critical enrichment steps",
                "isolate": "Network policy blocks all egress",
                "hard_stop": "Kill switch via infrastructure controller",
            },
            "last_tested": "2026-02-01",
        }, [
            {"field": "coverage_score", "op": "eq", "value": 4},
            {"field": "escalation_readiness", "op": "eq", "value": "ready"},
            {"field": "gaps", "op": "length", "value": 0},
        ]),
        ("missing-two-levels", ["edge-case"], {
            "system_name": "analytics-pipeline",
            "capabilities": {
                "throttle": "Rate limit via ingestion queue",
                "degrade": "",
                "isolate": "",
                "hard_stop": "Container kill via orchestrator",
            },
            "last_tested": "2026-01-15",
        }, [
            {"field": "coverage_score", "op": "eq", "value": 2},
            {"field": "escalation_readiness", "op": "eq", "value": "partial"},
            {"field": "gaps", "op": "min_length", "value": 2},
        ]),
        ("no-test-date", ["boundary"], {
            "system_name": "notification-svc",
            "capabilities": {
                "throttle": "Limit via queue",
                "degrade": "Drop low-priority",
                "isolate": "Firewall rule",
                "hard_stop": "Process kill",
            },
        }, [
            {"field": "coverage_score", "op": "eq", "value": 4},
            {"field": "escalation_readiness", "op": "eq", "value": "partial"},
            {"field": "gaps", "op": "min_length", "value": 1},
        ]),
    ],
    # ── data-ops ───────────────────────────────────────────────────
    "data-ops.schema-drift-detector-agent": [
        ("breaking-changes", ["happy-path"], {
            "schema_before": {"id": "integer", "name": "string", "email": "string"},
            "schema_after": {"id": "string", "name": "string", "phone": "string"},
        }, [
            {"field": "drift_severity", "op": "in", "value": ["medium", "high"]},
            {"field": "changes", "op": "min_length", "value": 2},
        ]),
        ("no-drift", ["edge-case"], {
            "schema_before": {"id": "integer", "name": "string"},
            "schema_after": {"id": "integer", "name": "string"},
        }, [
            {"field": "drift_severity", "op": "eq", "value": "none"},
            {"field": "changes", "op": "length", "value": 0},
        ]),
        ("additive-only", ["happy-path"], {
            "schema_before": {"id": "integer"},
            "schema_after": {"id": "integer", "created_at": "timestamp"},
        }, [
            {"field": "drift_severity", "op": "eq", "value": "low"},
            {"field": "changes", "op": "length", "value": 1},
        ]),
    ],
    "data-ops.data-validator-agent": [
        ("all-valid", ["happy-path"], {
            "records": [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ],
            "rules": ["name must not be empty", "age must be non-negative"],
        }, [
            {"field": "verdict", "op": "eq", "value": "pass"},
            {"field": "valid_count", "op": "eq", "value": 2},
            {"field": "invalid_count", "op": "eq", "value": 0},
        ]),
        ("some-invalid", ["happy-path"], {
            "records": [
                {"name": "Alice", "age": 30},
                {"name": "", "age": -5},
                {"name": "Charlie", "age": 20},
            ],
            "rules": ["name must not be empty", "age must be non-negative"],
        }, [
            {"field": "verdict", "op": "in", "value": ["warn", "fail"]},
            {"field": "violations", "op": "min_length", "value": 1},
        ]),
        ("all-invalid", ["edge-case"], {
            "records": [
                {"name": "", "age": -1},
                {"name": "", "age": -2},
            ],
            "rules": ["name must not be empty", "age must be non-negative"],
        }, [
            {"field": "verdict", "op": "eq", "value": "fail"},
            {"field": "invalid_count", "op": "eq", "value": 2},
        ]),
    ],
    # ── code-ops ───────────────────────────────────────────────────
    "code-ops.code-reviewer-agent": [
        ("security-issues", ["happy-path"], {
            "diff": "password = 'hunter2'\nselect * from users where id = $input",
            "context": "Auth module update",
        }, [
            {"field": "severity", "op": "eq", "value": "critical"},
            {"field": "findings", "op": "min_length", "value": 2},
        ]),
        ("clean-diff", ["happy-path"], {
            "diff": "def add(a, b):\n    return a + b",
            "context": "Math utility",
        }, [
            {"field": "severity", "op": "eq", "value": "clean"},
            {"field": "findings", "op": "length", "value": 0},
        ]),
        ("eval-usage", ["edge-case"], {
            "diff": "result = eval(user_input)",
        }, [
            {"field": "severity", "op": "eq", "value": "critical"},
            {"field": "findings", "op": "contains", "value": "Unsafe eval usage on user input"},
        ]),
        ("broad-exception", ["edge-case"], {
            "diff": "try:\n    do_work()\nexcept Exception:\n    pass",
        }, [
            {"field": "severity", "op": "eq", "value": "major"},
        ]),
    ],
    "code-ops.pr-summary-agent": [
        ("small-safe-pr", ["happy-path"], {
            "title": "Fix typo in README",
            "changed_files": ["README.md"],
            "diff_summary": "Corrected spelling in installation section",
        }, [
            {"field": "review_focus", "op": "eq", "value": "low"},
            {"field": "summary", "op": "contains", "value": "Fix typo in README"},
        ]),
        ("sensitive-files", ["edge-case"], {
            "title": "Update auth middleware",
            "changed_files": ["src/auth/middleware.py", "src/auth/tokens.py", "config/security.yaml"],
        }, [
            {"field": "review_focus", "op": "eq", "value": "high"},
            {"field": "risk_areas", "op": "min_length", "value": 2},
        ]),
        ("many-files", ["boundary"], {
            "title": "Refactor utils",
            "changed_files": [f"src/util_{i}.py" for i in range(12)],
        }, [
            {"field": "review_focus", "op": "eq", "value": "high"},
            {"field": "summary", "op": "contains", "value": "12 file(s)"},
        ]),
    ],
    # ── observability-ops ──────────────────────────────────────────
    "observability-ops.log-analyzer-agent": [
        ("error-spike", ["happy-path"], {
            "log_entries": [
                "2026-03-10 ERROR: connection timeout to db-primary",
                "2026-03-10 ERROR: connection timeout to db-primary",
                "2026-03-10 ERROR: connection refused on port 5432",
                "2026-03-10 WARN: slow query detected",
                "2026-03-10 INFO: health check passed",
            ],
            "time_range": "2026-03-10 00:00 to 06:00",
        }, [
            {"field": "severity", "op": "eq", "value": "critical"},
            {"field": "patterns", "op": "min_length", "value": 2},
            {"field": "anomalies", "op": "min_length", "value": 1},
        ]),
        ("clean-logs", ["happy-path"], {
            "log_entries": [
                "2026-03-10 INFO: request completed in 45ms",
                "2026-03-10 INFO: health check passed",
            ],
        }, [
            {"field": "severity", "op": "eq", "value": "normal"},
            {"field": "anomalies", "op": "length", "value": 0},
        ]),
        ("auth-failures", ["edge-case"], {
            "log_entries": [
                "2026-03-10 ERROR: authentication failed for user unknown",
                "2026-03-10 ERROR: authentication failed for user admin",
                "2026-03-10 ERROR: unauthorized access attempt",
            ],
        }, [
            {"field": "severity", "op": "eq", "value": "critical"},
            {"field": "anomalies", "op": "min_length", "value": 1},
        ]),
        ("oom-critical", ["edge-case"], {
            "log_entries": [
                "2026-03-10 ERROR: out of memory on worker-3",
                "2026-03-10 INFO: restarting worker-3",
            ],
        }, [
            {"field": "severity", "op": "eq", "value": "critical"},
        ]),
    ],
    "observability-ops.slo-reporter-agent": [
        ("all-met", ["happy-path"], {
            "service_name": "api-gateway",
            "metrics": {"availability": 99.99, "latency_p99": 180},
            "slo_targets": {"availability": 99.9, "latency_p99": 200},
        }, [
            {"field": "compliance_status", "op": "eq", "value": "met"},
            {"field": "findings", "op": "min_length", "value": 2},
        ]),
        ("breached", ["happy-path"], {
            "service_name": "payment-api",
            "metrics": {"availability": 98.0, "latency_p99": 500},
            "slo_targets": {"availability": 99.9, "latency_p99": 200},
        }, [
            {"field": "compliance_status", "op": "eq", "value": "breached"},
            {"field": "recommended_actions", "op": "min_length", "value": 1},
        ]),
        ("at-risk", ["edge-case"], {
            "service_name": "search-api",
            "metrics": {"availability": 99.85, "latency_p99": 195},
            "slo_targets": {"availability": 99.9, "latency_p99": 200},
        }, [
            {"field": "compliance_status", "op": "eq", "value": "at_risk"},
        ]),
    ],
}


def generate() -> None:
    total_cases = 0
    total_agents = 0

    for agent_id, case_defs in sorted(CASES.items()):
        project, agent_name = agent_id.split(".", 1)
        evals_dir = ROOT / "catalog" / "projects" / project / "agents" / agent_name / "evals"
        evals_dir.mkdir(parents=True, exist_ok=True)

        fixture: dict[str, Any] = {"agent_id": agent_id, "cases": []}

        for case_id, tags, input_payload, assertions in case_defs:
            output = run_agent(agent_id, input_payload)

            case: dict[str, Any] = {
                "id": case_id,
                "tags": tags,
                "input": input_payload,
                "expected_output": output,
            }
            if assertions:
                case["assertions"] = assertions

            fixture["cases"].append(case)
            total_cases += 1

        out_path = evals_dir / "cases.json"
        out_path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n")
        total_agents += 1
        print(f"  {out_path.relative_to(ROOT)}: {len(fixture['cases'])} cases")

    print(f"\nGenerated {total_cases} eval cases across {total_agents} agents.")


if __name__ == "__main__":
    generate()
