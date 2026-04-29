"""Shared control-ops contracts, scoring, and formatting."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from typing import Any

from .core import ValidationError, sanitize_untrusted_text

LINEAGE_RECORD_KEYS = [
    "trigger",
    "knowledge",
    "rules_applied",
    "alternatives_considered",
    "action_taken",
]

SCOPE_VERDICTS = {"pass", "review", "fail"}
RISK_LEVELS = {"low", "medium", "high"}
MAX_DAMAGE_LEVELS = {"low", "medium", "high", "critical"}
LATENCY_LEVELS = {"fast", "moderate", "slow"}
READINESS_LEVELS = {"ready", "partial", "unprepared"}
GOVERNANCE_PIPELINE_STATUSES = {"ok", "needs_review", "blocked", "degraded"}
RESILIENCE_VERDICTS = {"adequate", "partial", "at-risk", "inadequate"}
KILL_PATH_LEVELS = ["throttle", "degrade", "isolate", "hard_stop"]
KILL_PATH_RECENCY_DAYS = 180

READ_ONLY_ACTION_TOKENS = {
    "audit",
    "check",
    "describe",
    "fetch",
    "inspect",
    "list",
    "observe",
    "query",
    "read",
    "review",
    "tail",
    "view",
}
MUTATING_ACTION_TOKENS = {
    "backfill",
    "configure",
    "create",
    "deploy",
    "modify",
    "optimize",
    "patch",
    "reindex",
    "restart",
    "restore",
    "rotate",
    "scale",
    "sync",
    "toggle",
    "update",
    "write",
}
DESTRUCTIVE_ACTION_TOKENS = {
    "delete",
    "destroy",
    "drop",
    "erase",
    "purge",
    "remove",
    "revoke",
    "truncate",
    "wipe",
}
REVERSIBILITY_HINT_TOKENS = {
    "auto-heal",
    "backup",
    "canary",
    "flag",
    "recover",
    "restore",
    "revert",
    "rollback",
    "snapshot",
    "soft-delete",
}
SCOPE_BROAD_TOKENS = {
    "all",
    "entire",
    "global",
    "production",
    "shared",
    "system-wide",
}
TRACEABILITY_TOKENS = {"audit", "log", "logging", "trace", "tracing"}
CRITICAL_PERMISSION_TOKENS = {"admin", "credential", "owner", "root", "sudo"}
DESTRUCTIVE_PERMISSION_TOKENS = {"delete", "destroy", "drop", "purge", "truncate", "wipe"}
SENSITIVE_PERMISSION_TOKENS = {
    "billing",
    "deploy",
    "external",
    "k8s",
    "payment",
    "pii",
    "prod",
    "production",
    "public",
    "restart",
    "secret",
    "token",
    "write",
}
EXTERNAL_EXPOSURE_TOKENS = {"api", "external", "internet", "public", "third-party"}
READ_PERMISSION_TOKENS = {"audit", "describe", "list", "log", "query", "read", "view"}


def _require_non_empty_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if key not in payload:
        raise ValidationError(f"missing required field: {key}")
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} must be a non-empty string")
    return sanitize_untrusted_text(value.strip())


def _optional_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError(f"{key} must be a string when provided")
    return sanitize_untrusted_text(value.strip())


def _require_non_empty_string_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if key not in payload:
        raise ValidationError(f"missing required field: {key}")
    if not isinstance(value, list) or not value:
        raise ValidationError(f"{key} must be a non-empty string array")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValidationError(f"{key} must be a non-empty string array")
    return [sanitize_untrusted_text(item.strip()) for item in value if item.strip()]


def _optional_string_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValidationError(f"{key} must be an array of strings")
    return [sanitize_untrusted_text(item.strip()) for item in value if item.strip()]


def _truncate_words(text: str, max_words: int) -> str:
    return " ".join(text.split()[:max_words])


def _truncate_list(items: list[str], *, max_items: int, max_words: int) -> list[str]:
    return [_truncate_words(item, max_words) for item in items[:max_items]]


def _slugify(text: str, max_len: int) -> str:
    collapsed = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not collapsed:
        return "item"
    return collapsed[:max_len].strip("-") or "item"


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:8]


def build_lineage_record(payload: dict[str, Any]) -> dict[str, Any]:
    trigger = _require_non_empty_string(payload, "trigger")
    knowledge = _require_non_empty_string(payload, "knowledge")
    rules_applied = _require_non_empty_string_list(payload, "rules_applied")
    alternatives_considered = _require_non_empty_string_list(payload, "alternatives_considered")
    action_taken = _require_non_empty_string(payload, "action_taken")

    record = {
        "trigger": _truncate_words(trigger, 20),
        "knowledge": _truncate_words(knowledge, 30),
        "rules_applied": _truncate_list(rules_applied, max_items=5, max_words=12),
        "alternatives_considered": _truncate_list(alternatives_considered, max_items=5, max_words=12),
        "action_taken": _truncate_words(action_taken, 20),
    }
    record_hash = _stable_hash(record)
    trigger_slug = _slugify(record["trigger"], 28)
    action_slug = _slugify(record["action_taken"], 28)
    lineage_id = f"{trigger_slug}--{action_slug}-{record_hash}"[:80]

    all_substantive = (
        bool(record["trigger"])
        and bool(record["knowledge"])
        and bool(record["rules_applied"])
        and bool(record["alternatives_considered"])
        and bool(record["action_taken"])
    )
    integrity_check = "complete" if all_substantive else "partial"
    return {"lineage_id": lineage_id, "record": record, "integrity_check": integrity_check}


def _contains_any(text: str, tokens: set[str]) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in tokens)


def _score_permission(permission: str) -> int:
    lowered = permission.lower()
    if any(token in lowered for token in TRACEABILITY_TOKENS) and not any(
        token in lowered
        for token in CRITICAL_PERMISSION_TOKENS | DESTRUCTIVE_PERMISSION_TOKENS | SENSITIVE_PERMISSION_TOKENS
    ):
        return 1
    if any(token in lowered for token in CRITICAL_PERMISSION_TOKENS):
        return 8
    if any(token in lowered for token in DESTRUCTIVE_PERMISSION_TOKENS):
        return 7
    if any(token in lowered for token in SENSITIVE_PERMISSION_TOKENS):
        return 4
    if any(token in lowered for token in READ_PERMISSION_TOKENS):
        return 1
    return 2


def assess_scope_validation(payload: dict[str, Any]) -> dict[str, Any]:
    action_description = _require_non_empty_string(payload, "action_description")
    permissions_requested = _require_non_empty_string_list(payload, "permissions_requested")
    reversibility_plan = _optional_string(payload, "reversibility_plan")
    scope_boundary = _optional_string(payload, "scope_boundary")

    lowered_action = action_description.lower()
    if _contains_any(lowered_action, DESTRUCTIVE_ACTION_TOKENS):
        action_class = "destructive"
        destructive_score = 3
    elif _contains_any(lowered_action, MUTATING_ACTION_TOKENS):
        action_class = "mutating"
        destructive_score = 1
    elif _contains_any(lowered_action, READ_ONLY_ACTION_TOKENS):
        action_class = "read-only"
        destructive_score = 0
    else:
        action_class = "unknown"
        destructive_score = 1

    if not scope_boundary:
        scope_penalty = 3
        scope_finding = "Scope boundary is missing; action remains unbounded"
    elif _contains_any(scope_boundary, SCOPE_BROAD_TOKENS):
        scope_penalty = 1
        scope_finding = f"Scope boundary is broad: {_truncate_words(scope_boundary, 12)}"
    else:
        scope_penalty = 0
        scope_finding = f"Scope boundary is explicit: {_truncate_words(scope_boundary, 12)}"

    if reversibility_plan:
        if _contains_any(reversibility_plan, REVERSIBILITY_HINT_TOKENS):
            reversibility_penalty = 0
            reversibility_finding = f"Reversibility plan is concrete: {_truncate_words(reversibility_plan, 12)}"
        else:
            reversibility_penalty = 1 if destructive_score >= 1 else 0
            reversibility_finding = f"Reversibility plan exists but needs more detail: {_truncate_words(reversibility_plan, 12)}"
    elif destructive_score >= 3:
        reversibility_penalty = 3
        reversibility_finding = "Reversibility plan is missing for a destructive action"
    elif destructive_score >= 1:
        reversibility_penalty = 1
        reversibility_finding = "Reversibility plan is missing for a mutating action"
    else:
        reversibility_penalty = 0
        reversibility_finding = "No reversibility plan needed for a read-only action"

    permission_points = [_score_permission(permission) for permission in permissions_requested]
    permission_penalty = min(6, sum(permission_points))
    sensitive_permissions = [
        permission
        for permission in permissions_requested
        if _score_permission(permission) >= 4
    ]
    if sensitive_permissions:
        permission_finding = (
            "Sensitive permissions requested: "
            + ", ".join(_truncate_list(sensitive_permissions, max_items=3, max_words=2))
        )
    else:
        permission_finding = (
            "Requested permissions appear low-sensitivity: "
            + ", ".join(_truncate_list(permissions_requested, max_items=3, max_words=2))
        )

    has_traceability = any(_contains_any(permission, TRACEABILITY_TOKENS) for permission in permissions_requested)
    if has_traceability:
        traceability_penalty = 0
        traceability_finding = "Traceability controls are requested alongside the action"
    elif destructive_score >= 1:
        traceability_penalty = 1
        traceability_finding = "No audit or log capability is requested for a mutating action"
    else:
        traceability_penalty = 0
        traceability_finding = "No extra traceability capability is needed for read-only work"

    total_risk = destructive_score + scope_penalty + reversibility_penalty + permission_penalty + traceability_penalty
    if (
        (destructive_score >= 3 and (scope_penalty >= 1 or reversibility_penalty >= 2))
        or (permission_penalty >= 6 and scope_penalty >= 1)
        or total_risk >= 9
    ):
        verdict = "fail"
    elif total_risk >= 3 or destructive_score >= 1 or permission_penalty >= 4:
        verdict = "review"
    else:
        verdict = "pass"

    if verdict == "fail" or total_risk >= 9:
        risk_level = "high"
    elif verdict == "review":
        risk_level = "medium"
    else:
        risk_level = "low"

    findings = [
        f"Action is classified as {action_class}",
        scope_finding,
        reversibility_finding,
        permission_finding,
        traceability_finding,
    ]
    return {
        "verdict": verdict,
        "findings": _truncate_list(findings, max_items=5, max_words=18),
        "risk_level": risk_level,
        "scores": {
            "action": destructive_score,
            "scope": scope_penalty,
            "reversibility": reversibility_penalty,
            "permissions": permission_penalty,
            "traceability": traceability_penalty,
            "total": total_risk,
        },
    }


def assess_blast_radius(payload: dict[str, Any]) -> dict[str, Any]:
    service_name = _require_non_empty_string(payload, "service_name")
    permissions = _require_non_empty_string_list(payload, "permissions")
    dependencies = _optional_string_list(payload, "dependencies")
    resource_limits = payload.get("resource_limits") or {}
    if not isinstance(resource_limits, dict):
        raise ValidationError("resource_limits must be an object when provided")

    permission_score = min(55, sum(_score_permission(permission) for permission in permissions))
    external_permissions = [permission for permission in permissions if _contains_any(permission, EXTERNAL_EXPOSURE_TOKENS)]
    critical_permissions = [permission for permission in permissions if _score_permission(permission) >= 6]
    sensitive_permissions = [permission for permission in permissions if _score_permission(permission) >= 4]

    external_dependencies = [dependency for dependency in dependencies if _contains_any(dependency, EXTERNAL_EXPOSURE_TOKENS)]
    dependency_score = min(30, len(dependencies) * 6 + len(external_dependencies) * 4)

    limit_keys = {str(key).lower() for key in resource_limits.keys()}
    limit_credit = 0
    for token_group in ({"rate", "rps", "throughput"}, {"budget", "cost"}, {"concurrency", "parallel"}, {"cpu", "memory"}, {"timeout"}):
        if any(any(token in key for token in token_group) for key in limit_keys):
            limit_credit += 5
    limit_credit = min(20, limit_credit)

    risk_score = max(0, min(100, permission_score + dependency_score - limit_credit))
    if risk_score >= 70:
        max_damage_potential = "critical"
    elif risk_score >= 50:
        max_damage_potential = "high"
    elif risk_score >= 25:
        max_damage_potential = "medium"
    else:
        max_damage_potential = "low"

    if external_permissions or external_dependencies:
        detection_latency = "slow"
    elif risk_score >= 35:
        detection_latency = "moderate"
    else:
        detection_latency = "fast"

    if len(dependencies) >= 4 or (risk_score >= 60 and not resource_limits):
        containment_time = "slow"
    elif len(dependencies) >= 2 or risk_score >= 30:
        containment_time = "moderate"
    else:
        containment_time = "fast"

    findings: list[str] = []
    if critical_permissions or sensitive_permissions:
        findings.append(
            "Sensitive permissions increase impact: "
            + ", ".join(_truncate_list((critical_permissions or sensitive_permissions), max_items=3, max_words=2))
        )
    if external_permissions or external_dependencies:
        findings.append("External exposure extends the blast radius beyond internal boundaries")
    if dependencies:
        findings.append(f"{len(dependencies)} dependencies expand cascading-failure surface")
    if resource_limits:
        findings.append("Resource limits are present and reduce runaway execution risk")
    else:
        findings.append("Resource limits are missing, leaving execution bounds undefined")
    if not findings:
        findings.append(f"{service_name} has a contained permission and dependency profile")

    if critical_permissions:
        control_one = f"Split critical permissions into least-privilege roles for {service_name}"
    else:
        control_one = f"Keep permissions tightly scoped to named resources for {service_name}"
    if external_permissions or external_dependencies:
        control_two = "Add egress allowlists, timeouts, and circuit breakers for external integrations"
    elif len(dependencies) >= 2:
        control_two = "Document dependency isolation points and rehearse containment steps"
    else:
        control_two = "Document dependency ownership and a fast containment path"
    if resource_limits:
        control_three = "Verify alerting and automatic throttles trigger before resource limits are exhausted"
    else:
        control_three = "Define explicit rate, concurrency, and budget limits with alerting"

    return {
        "risk_score": risk_score,
        "max_damage_potential": max_damage_potential,
        "detection_latency": detection_latency,
        "containment_time": containment_time,
        "findings": _truncate_list(findings, max_items=5, max_words=18),
        "recommended_controls": _truncate_list(
            [control_one, control_two, control_three],
            max_items=3,
            max_words=18,
        ),
        "factors": {
            "permissions": permission_score,
            "dependencies": dependency_score,
            "resource_limit_credit": limit_credit,
        },
    }


def assess_kill_path(payload: dict[str, Any], *, today: date | None = None) -> dict[str, Any]:
    system_name = _require_non_empty_string(payload, "system_name")
    if "capabilities" not in payload:
        raise ValidationError("missing required field: capabilities")
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, dict):
        raise ValidationError("capabilities must be an object")
    last_tested = _optional_string(payload, "last_tested")

    tested_date: date | None = None
    if last_tested:
        try:
            tested_date = date.fromisoformat(last_tested)
        except ValueError as exc:
            raise ValidationError("last_tested must be an ISO date when provided") from exc
        current_day = today or date.today()
        if tested_date > current_day:
            raise ValidationError("last_tested cannot be in the future")
    else:
        current_day = today or date.today()

    coverage_score = 0
    gaps: list[str] = []
    missing_levels: list[str] = []
    for level in KILL_PATH_LEVELS:
        description = capabilities.get(level, "")
        if isinstance(description, str) and description.strip():
            coverage_score += 1
        else:
            missing_levels.append(level)
            gaps.append(f"{level}: no {level.replace('_', ' ')} capability described")

    recency_state = "unknown"
    if tested_date is None:
        gaps.append("last_tested: no test date recorded")
    else:
        age_days = (current_day - tested_date).days
        if age_days > KILL_PATH_RECENCY_DAYS:
            recency_state = "stale"
            gaps.append(f"last_tested: older than {KILL_PATH_RECENCY_DAYS} days")
        else:
            recency_state = "recent"

    if coverage_score == 4 and recency_state == "recent":
        escalation_readiness = "ready"
    elif coverage_score >= 2:
        escalation_readiness = "partial"
    else:
        escalation_readiness = "unprepared"

    if missing_levels:
        first_action = f"Implement {missing_levels[0].replace('_', ' ')} capability for {system_name}"
    elif recency_state != "recent":
        first_action = f"Run and record a fresh kill path drill for {system_name}"
    else:
        first_action = f"Verify all four kill path levels function independently for {system_name}"

    return {
        "coverage_score": coverage_score,
        "gaps": _truncate_list(gaps, max_items=4, max_words=12),
        "escalation_readiness": escalation_readiness,
        "recommended_actions": _truncate_list(
            [
                first_action,
                "Schedule quarterly kill path drills covering throttle, degrade, isolate, and hard stop",
                "Verify hard_stop works independently of application cooperation",
            ],
            max_items=3,
            max_words=16,
        ),
        "recency_state": recency_state,
    }


def governance_pipeline_status(verdict: str) -> tuple[str, str, str]:
    if verdict == "pass":
        return ("ok", "executed", "completed")
    if verdict == "review":
        return ("needs_review", "needs_review", "failed")
    if verdict == "fail":
        return ("blocked", "blocked", "failed")
    raise ValidationError(f"unsupported governance verdict: {verdict}")


def assess_exception_policy(payload: dict[str, Any], *, today: date | None = None) -> dict[str, Any]:
    action_id = _require_non_empty_string(payload, "action_id")
    scope = _require_non_empty_string(payload, "scope")
    requested_by = _require_non_empty_string(payload, "requested_by")
    owner = _require_non_empty_string(payload, "owner")
    justification = _require_non_empty_string(payload, "justification")
    expires_at = _require_non_empty_string(payload, "expires_at")

    try:
        expiry_date = date.fromisoformat(expires_at)
    except ValueError as exc:
        raise ValidationError("expires_at must be an ISO date") from exc

    current_day = today or date.today()
    days_remaining = (expiry_date - current_day).days
    lowered_scope = scope.lower()
    lowered_justification = justification.lower()

    broad_scope = any(token in lowered_scope for token in {"all", "global", "entire", "production"})
    weak_justification = len(lowered_justification.split()) < 4
    emergency_hint = any(token in lowered_justification for token in {"incident", "outage", "saturation", "breach"})

    if days_remaining < 0:
        verdict = "denied"
        reason_code = "exception_expired"
    elif broad_scope and not emergency_hint:
        verdict = "denied"
        reason_code = "scope_violation"
    elif weak_justification or days_remaining > 90:
        verdict = "review"
        reason_code = "needs_review"
    else:
        verdict = "approved"
        reason_code = "policy_exception_approved"

    conditions = [
        f"Owner {owner} must review exception weekly",
        "Record all actions taken under this exception in lineage logs",
    ]
    if verdict != "approved":
        conditions.append("Require explicit human approval before execution")

    exception_id = f"exc-{_slugify(action_id, 28)}-{_stable_hash({'a': action_id, 'o': owner, 'e': expires_at})}"
    return {
        "exception_verdict": verdict,
        "exception_id": exception_id[:80],
        "owner": owner,
        "expires_at": expires_at,
        "conditions": _truncate_list(conditions, max_items=3, max_words=14),
        "reason_code": reason_code,
    }


def assess_approval_memory(payload: dict[str, Any], *, today: date | None = None) -> dict[str, Any]:
    approval_subject = _require_non_empty_string(payload, "approval_subject")
    approver = _require_non_empty_string(payload, "approver")
    approved_at = _require_non_empty_string(payload, "approved_at")
    expires_at = _require_non_empty_string(payload, "expires_at")
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValidationError("metadata must be an object when provided")

    try:
        approved_date = date.fromisoformat(approved_at)
    except ValueError as exc:
        raise ValidationError("approved_at must be an ISO date") from exc
    try:
        expiry_date = date.fromisoformat(expires_at)
    except ValueError as exc:
        raise ValidationError("expires_at must be an ISO date") from exc

    if expiry_date < approved_date:
        raise ValidationError("expires_at must be on or after approved_at")

    current_day = today or date.today()
    expired = expiry_date < current_day
    active = not expired

    record_seed = {
        "subject": approval_subject,
        "approver": approver,
        "approved_at": approved_at,
        "expires_at": expires_at,
        "metadata": metadata,
    }
    approval_record_id = f"apr-{_slugify(approval_subject, 24)}-{_stable_hash(record_seed)}"[:80]
    recall_hint = (
        "Approval expired; request renewal before privileged execution"
        if expired
        else "Re-check approval status before executing privileged action"
    )
    return {
        "approval_record_id": approval_record_id,
        "active": active,
        "expired": expired,
        "approver": approver,
        "expires_at": expires_at,
        "recall_hint": _truncate_words(recall_hint, 14),
    }


def resilience_verdict_from_scores(risk_score: int, coverage_score: int) -> str:
    if risk_score >= 50 and coverage_score <= 1:
        return "inadequate"
    if risk_score >= 60 and coverage_score <= 2:
        return "inadequate"
    if risk_score >= 40 and coverage_score <= 2:
        return "at-risk"
    if coverage_score == 4 and risk_score < 40:
        return "adequate"
    return "partial"
