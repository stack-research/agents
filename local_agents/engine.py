"""Deterministic and LLM-backed local implementations for catalog agents."""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime
from typing import Any

from .artifact_ops import (
    build_artifact_inventory,
    build_bundle_manifest,
    seal_repro_bundle,
)
from .control_ops import (
    assess_approval_memory,
    assess_blast_radius,
    assess_exception_policy,
    assess_kill_path,
    assess_scope_validation,
    build_lineage_record,
)
from .core import (
    DEFAULT_LABELS,
    ValidationError,
    require,
    sanitize_untrusted_text,
    validate_llm_runtime_source,
)
from .security_scanner import scan_repository_controls


def run_heartbeat_agent(payload: dict[str, Any]) -> dict[str, Any]:
    service_name = require(payload, "service_name")
    age = require(payload, "heartbeat_age_seconds")
    error_rate = require(payload, "error_rate_percent")

    if not isinstance(service_name, str) or not service_name.strip():
        raise ValidationError("service_name must be a non-empty string")
    if not isinstance(age, (int, float)):
        raise ValidationError("heartbeat_age_seconds must be numeric")
    if not isinstance(error_rate, (int, float)):
        raise ValidationError("error_rate_percent must be numeric")

    clamped = False
    age_value = float(age)
    error_value = float(error_rate)

    if age_value < 0:
        age_value = 0.0
        clamped = True
    if error_value < 0:
        error_value = 0.0
        clamped = True

    if age_value > 90:
        status = "critical"
    elif age_value > 30:
        status = "warn"
    else:
        status = "ok"

    if error_value > 5:
        if status == "ok":
            status = "warn"
        elif status == "warn":
            status = "critical"

    report = (
        f"{service_name} heartbeat age {age_value:g}s, error rate {error_value:g}%; "
        f"status {status}."
    )
    if clamped:
        report = f"{report} Negative metrics were clamped to zero."

    return {"status": status, "report": report}


def _score_label(text: str, keywords: list[str]) -> int:
    score = 0
    for token in keywords:
        if token in text:
            score += 1
    return score


def run_classifier_agent(payload: dict[str, Any]) -> dict[str, Any]:
    text = require(payload, "text")
    labels = payload.get("labels") or DEFAULT_LABELS

    if not isinstance(text, str) or not text.strip():
        raise ValidationError("text must be a non-empty string")
    if not isinstance(labels, list) or not labels or not all(
        isinstance(item, str) and item for item in labels
    ):
        raise ValidationError("labels must be a non-empty string array")

    lowered = text.lower()

    keyword_map = {
        "billing": ["bill", "charged", "charge", "refund", "invoice", "payment", "subscription"],
        "bug-report": ["bug", "crash", "error", "broken", "fails", "failure", "exception", "issue"],
        "feature-request": ["feature", "add", "support", "request", "enhancement", "improvement"],
        "support": ["help", "how", "setup", "configure", "access", "login", "unable", "cannot"],
        "feedback": ["love", "like", "dislike", "hate", "feedback", "great", "bad", "confusing"],
    }

    scores: dict[str, int] = {}
    for label in labels:
        if label in keyword_map:
            scores[label] = _score_label(lowered, keyword_map[label])

    top_label = None
    top_score = 0
    tie = False
    for label, score in scores.items():
        if score > top_score:
            top_label = label
            top_score = score
            tie = False
        elif score == top_score and score > 0:
            tie = True

    unknown_available = "unknown" in labels
    if top_score == 0 or tie:
        if unknown_available:
            return {
                "label": "unknown",
                "confidence": 0.4,
                "rationale": "No clear dominant intent was detected from the text.",
            }
        fallback = labels[0]
        return {
            "label": fallback,
            "confidence": 0.35,
            "rationale": "Intent is ambiguous; selected the first available label as fallback.",
        }

    confidence = min(0.95, 0.55 + (0.1 * top_score))
    return {
        "label": top_label,
        "confidence": round(confidence, 2),
        "rationale": f"Text signals {top_label} based on strongest keyword overlap.",
    }


def _bump_priority(priority: str) -> str:
    order = ["p1", "p2", "p3", "p4"]
    idx = order.index(priority)
    return order[max(0, idx - 1)]


def run_triage_agent(payload: dict[str, Any]) -> dict[str, Any]:
    text = require(payload, "text")
    customer_tier = payload.get("customer_tier", "free")

    if not isinstance(text, str) or not text.strip():
        raise ValidationError("text must be a non-empty string")
    if not isinstance(customer_tier, str):
        customer_tier = "free"
    tier = customer_tier.lower()
    if tier not in {"free", "pro", "enterprise"}:
        tier = "free"

    lowered = text.lower()

    if any(token in lowered for token in ["outage", "down", "security", "breach", "data loss", "production"]):
        priority = "p1"
    elif any(token in lowered for token in ["cannot", "can't", "failed", "broken", "error", "crash"]):
        priority = "p2"
    elif any(token in lowered for token in ["refund", "invoice", "billing", "payment", "feature", "request"]):
        priority = "p3"
    else:
        priority = "p4"

    if "billing" in lowered or any(token in lowered for token in ["refund", "invoice", "charged", "payment"]):
        category = "billing"
    elif any(
        token in lowered
        for token in ["login", "log in", "auth", "permission", "access", "sign in", "sign-in", "sso"]
    ):
        category = "access"
    elif any(token in lowered for token in ["bug", "broken", "error", "crash", "fails", "failure"]):
        category = "bug"
    elif any(token in lowered for token in ["feature", "request", "add", "enhancement"]):
        category = "feature"
    elif any(token in lowered for token in ["how do i", "how to", "configure", "setup", "guide"]):
        category = "how-to"
    else:
        category = "other"

    if tier == "enterprise" and priority != "p1":
        priority = _bump_priority(priority)

    action_by_category = {
        "billing": "Route to billing queue and request invoice and charge identifiers.",
        "access": "Escalate to auth on-call and collect user and timestamp details.",
        "bug": "Open an incident ticket and include reproduction steps and logs.",
        "feature": "Log product request with business impact and customer context.",
        "how-to": "Send setup guide and offer a short assisted walkthrough.",
        "other": "Acknowledge request and ask one clarifying question.",
    }
    next_action = action_by_category[category]
    short_action = " ".join(next_action.split()[:20])

    return {
        "priority": priority,
        "category": category,
        "next_action": short_action,
    }


def run_reply_drafter_agent(payload: dict[str, Any]) -> dict[str, Any]:
    priority = require(payload, "priority")
    category = require(payload, "category")
    issue_summary = require(payload, "issue_summary")
    customer_name = payload.get("customer_name")

    if priority not in {"p1", "p2", "p3", "p4"}:
        raise ValidationError("priority must be one of p1,p2,p3,p4")
    if category not in {"billing", "bug", "access", "feature", "how-to", "other"}:
        raise ValidationError("category must be one of billing,bug,access,feature,how-to,other")
    if not isinstance(issue_summary, str) or not issue_summary.strip():
        raise ValidationError("issue_summary must be a non-empty string")
    if customer_name is not None and not isinstance(customer_name, str):
        raise ValidationError("customer_name must be a string when provided")

    subject_by_category = {
        "billing": "Update on your billing request",
        "bug": "Update on the reported issue",
        "access": "Update on your sign-in issue",
        "feature": "Update on your feature request",
        "how-to": "Guidance for your setup question",
        "other": "Update on your support request",
    }
    timeline_by_priority = {
        "p1": "within 30 minutes",
        "p2": "within 60 minutes",
        "p3": "within one business day",
        "p4": "within two business days",
    }
    next_step_by_category = {
        "billing": "We're reviewing the charge details with our billing team.",
        "bug": "We're reproducing the issue and collecting logs now.",
        "access": "We're checking authentication logs and account status now.",
        "feature": "We're logging this request with product and support context.",
        "how-to": "We're preparing step-by-step guidance for your setup.",
        "other": "We're reviewing this with the appropriate support queue.",
    }

    greeting = f"Hi {customer_name.strip()}," if isinstance(customer_name, str) and customer_name.strip() else "Hi,"
    subject = subject_by_category[category]
    timeline = timeline_by_priority[priority]
    next_step = next_step_by_category[category]
    issue = sanitize_untrusted_text(issue_summary.strip().rstrip("."))
    if not issue or issue == "[redacted]":
        issue = "the reported issue"
    reply = (
        f"{greeting} thanks for reporting this. We understand: {issue}. "
        f"{next_step} We will share another update {timeline}."
    )

    reply_words = reply.split()
    if len(reply_words) > 90:
        reply = " ".join(reply_words[:90])

    return {"subject": subject, "reply": reply}


def run_summary_agent(payload: dict[str, Any]) -> dict[str, Any]:
    period_start = require(payload, "period_start")
    period_end = require(payload, "period_end")
    tickets = require(payload, "tickets")
    top_n_actions = payload.get("top_n_actions", 3)

    if not isinstance(period_start, str) or not period_start.strip():
        raise ValidationError("period_start must be a non-empty string")
    if not isinstance(period_end, str) or not period_end.strip():
        raise ValidationError("period_end must be a non-empty string")
    if not isinstance(tickets, list):
        raise ValidationError("tickets must be an array")
    if not isinstance(top_n_actions, int) or top_n_actions < 2 or top_n_actions > 4:
        raise ValidationError("top_n_actions must be an integer between 2 and 4")

    allowed_priorities = {"p1", "p2", "p3", "p4"}
    allowed_categories = {"billing", "bug", "access", "feature", "how-to", "other"}
    priority_counts = {"p1": 0, "p2": 0, "p3": 0, "p4": 0}
    category_counts = {key: 0 for key in sorted(allowed_categories)}

    for item in tickets:
        if not isinstance(item, dict):
            raise ValidationError("each ticket must be an object")
        priority = item.get("priority")
        category = item.get("category")
        if priority not in allowed_priorities:
            raise ValidationError("ticket priority must be one of p1,p2,p3,p4")
        if category not in allowed_categories:
            raise ValidationError("ticket category must be one of billing,bug,access,feature,how-to,other")
        priority_counts[priority] += 1
        category_counts[category] += 1

    ticket_count = len(tickets)
    if ticket_count == 0:
        top_categories: list[str] = []
    else:
        ordered = sorted(category_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        top_categories = [f"{name}:{count}" for name, count in ordered if count > 0][:3]

    safe_period_start = sanitize_untrusted_text(period_start.strip())
    safe_period_end = sanitize_untrusted_text(period_end.strip())
    leading_category = top_categories[0].split(":")[0] if top_categories else "none"
    summary = (
        f"Support volume from {safe_period_start} to {safe_period_end}: {ticket_count} tickets. "
        f"Top category: {leading_category}. Priority mix p1={priority_counts['p1']}, "
        f"p2={priority_counts['p2']}, p3={priority_counts['p3']}, p4={priority_counts['p4']}."
    )
    summary = " ".join(summary.split()[:80])

    recommended_actions = [
        "Review top category queue and confirm owner coverage for next week",
        "Publish one trend note with priority shifts and customer impact",
        "Select one recurring issue and define mitigation experiment",
        "Audit aged tickets and close stale items with explicit resolution notes",
    ]
    if priority_counts["p1"] > 0:
        recommended_actions[0] = "Run a brief incident review for p1 themes and preventive controls"

    return {
        "ticket_count": ticket_count,
        "priority_breakdown": priority_counts,
        "top_categories": top_categories,
        "summary": summary,
        "recommended_actions": recommended_actions[:top_n_actions],
    }


def run_handoff_agent(payload: dict[str, Any]) -> dict[str, Any]:
    shift_label = require(payload, "shift_label")
    incidents = require(payload, "incidents")
    handoff_window = payload.get("handoff_window", "next 8 hours")

    if not isinstance(shift_label, str) or not shift_label.strip():
        raise ValidationError("shift_label must be a non-empty string")
    if not isinstance(incidents, list):
        raise ValidationError("incidents must be an array")
    if not isinstance(handoff_window, str) or not handoff_window.strip():
        raise ValidationError("handoff_window must be a non-empty string")

    allowed_severity = {"sev1", "sev2", "sev3", "sev4"}
    allowed_status = {"investigating", "mitigating", "monitoring", "open", "resolved"}
    active_count = 0
    critical_items: list[str] = []
    unowned_count = 0

    for item in incidents:
        if not isinstance(item, dict):
            raise ValidationError("each incident must be an object")
        incident_id = item.get("id")
        severity = item.get("severity")
        status = item.get("status")
        owner = item.get("owner", "")
        next_step = item.get("next_step", "")
        if not isinstance(incident_id, str) or not incident_id.strip():
            raise ValidationError("incident id must be a non-empty string")
        if severity not in allowed_severity:
            raise ValidationError("incident severity must be one of sev1,sev2,sev3,sev4")
        if status not in allowed_status:
            raise ValidationError("incident status must be one of investigating,mitigating,monitoring,open,resolved")
        if owner is not None and not isinstance(owner, str):
            raise ValidationError("incident owner must be a string when provided")
        if next_step is not None and not isinstance(next_step, str):
            raise ValidationError("incident next_step must be a string when provided")

        if status != "resolved":
            active_count += 1
        if severity in {"sev1", "sev2"} and status != "resolved":
            safe_item = sanitize_untrusted_text(f"{incident_id}:{severity}:{status}")
            critical_items.append(" ".join(safe_item.split()[:4]))
        if not owner or not owner.strip():
            unowned_count += 1

    safe_shift = sanitize_untrusted_text(shift_label.strip())
    safe_window = sanitize_untrusted_text(handoff_window.strip())
    top_critical = ", ".join(critical_items[:3]) if critical_items else "none"
    handoff_brief = (
        f"Handoff for {safe_shift}: {active_count} active incidents for {safe_window}. "
        f"Critical items: {top_critical}. Keep updates in the incident channel and checkpoint owner handoff."
    )
    handoff_brief = " ".join(handoff_brief.split()[:90])

    recommended_checks = [
        "Confirm incident owners acknowledge handoff and next-step deadlines",
        "Post one timeline update for each active sev1/sev2 incident",
        "Re-check mitigation status before end of current shift window",
    ]
    if unowned_count > 0:
        recommended_checks[0] = "Assign owner for unowned incidents and confirm acknowledgement"
    if active_count == 0:
        recommended_checks = [
            "Verify no hidden blockers remain in pending queues",
            "Record clean handoff note and monitoring posture",
            "Keep alert channel watch active for the next shift window",
        ]

    return {
        "active_count": active_count,
        "critical_items": critical_items[:3],
        "handoff_brief": handoff_brief,
        "recommended_checks": recommended_checks,
    }


def run_agentic_security_scanner_agent(payload: dict[str, Any]) -> dict[str, Any]:
    target_path = payload.get("target_path", ".")
    rules_path = payload.get("rules_path")
    if not isinstance(target_path, str) or not target_path.strip():
        raise ValidationError("target_path must be a non-empty string")
    if rules_path is not None and (not isinstance(rules_path, str) or not rules_path.strip()):
        raise ValidationError("rules_path must be a non-empty string when provided")
    return scan_repository_controls(target_path.strip(), rules_path=rules_path)


def run_planner_agent(payload: dict[str, Any]) -> dict[str, Any]:
    goal = require(payload, "goal")
    constraints = payload.get("constraints", [])

    if not isinstance(goal, str) or not goal.strip():
        raise ValidationError("goal must be a non-empty string")
    if constraints is None:
        constraints = []
    if not isinstance(constraints, list) or not all(isinstance(item, str) for item in constraints):
        raise ValidationError("constraints must be an array of strings")

    lowered = goal.lower()
    if any(token in lowered for token in {"security", "breach", "incident", "outage", "data loss"}):
        risk_level = "high"
    elif any(token in lowered for token in {"migrate", "delete", "billing", "auth", "production"}):
        risk_level = "medium"
    else:
        risk_level = "low"

    safe_goal = sanitize_untrusted_text(goal.strip())
    first = f"Clarify objective and success criteria for: {safe_goal}"
    second = "List dependencies, owners, and required access upfront"
    third = "Create implementation checklist with rollback and validation"
    fourth = "Execute checklist in small stages and capture evidence"
    fifth = "Summarize outcome, risks, and next follow-up actions"
    plan_steps = [first, second, third, fourth, fifth]

    sanitized_constraints = [
        sanitize_untrusted_text(item.strip()) for item in constraints if isinstance(item, str) and item.strip()
    ]
    if sanitized_constraints:
        plan_steps.append(f"Respect constraints: {', '.join(sanitized_constraints[:3])}")

    clipped_steps = [" ".join(step.split()[:18]) for step in plan_steps[:6]]
    return {"plan_steps": clipped_steps, "risk_level": risk_level}


def run_executor_agent(payload: dict[str, Any]) -> dict[str, Any]:
    plan_steps = require(payload, "plan_steps")
    context = payload.get("context", "")

    if not isinstance(plan_steps, list) or not plan_steps or not all(isinstance(item, str) for item in plan_steps):
        raise ValidationError("plan_steps must be a non-empty string array")
    if context is None:
        context = ""
    if not isinstance(context, str):
        raise ValidationError("context must be a string when provided")

    safe_context = sanitize_untrusted_text(context.strip())
    total = min(len(plan_steps), 8)
    completed_steps = max(1, min(total, 3 + (1 if safe_context else 0)))
    blocked_steps = max(0, total - completed_steps)
    status = "done" if blocked_steps == 0 else "partial"

    summary = (
        f"Executed {completed_steps} of {total} planned steps. "
        f"Status: {status}. "
        f"{'Context considered: ' + safe_context if safe_context else 'No additional context provided.'}"
    )
    summary = " ".join(summary.split()[:60])
    return {
        "status": status,
        "completed_steps": completed_steps,
        "blocked_steps": blocked_steps,
        "summary": summary,
    }


def run_retrieval_agent(payload: dict[str, Any]) -> dict[str, Any]:
    query = require(payload, "query")
    sources = payload.get("sources", [])
    max_points = payload.get("max_points", 5)

    if not isinstance(query, str) or not query.strip():
        raise ValidationError("query must be a non-empty string")
    if sources is None:
        sources = []
    if not isinstance(sources, list) or not all(isinstance(item, str) for item in sources):
        raise ValidationError("sources must be an array of strings")
    if not isinstance(max_points, int) or max_points < 1 or max_points > 8:
        raise ValidationError("max_points must be an integer between 1 and 8")

    safe_query = sanitize_untrusted_text(query.strip())
    cleaned_sources = [
        sanitize_untrusted_text(item.strip()) for item in sources if isinstance(item, str) and item.strip()
    ]

    notes = [f"Research objective: {safe_query}"]
    for item in cleaned_sources[: max(0, max_points - 1)]:
        notes.append(f"Source note: {item}")

    if len(notes) < max_points:
        notes.append("Gap: additional primary sources may be required for verification.")
    clipped = [" ".join(note.split()[:20]) for note in notes[:max_points]]
    confidence = 0.65 if cleaned_sources else 0.45
    return {"notes": clipped, "confidence": round(confidence, 2)}


def _normalize_evidence_contract(evidence_items: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(evidence_items, start=1):
        if isinstance(item, dict):
            content = sanitize_untrusted_text(str(item.get("content", "")).strip())
            if not content:
                continue
            source_kind = sanitize_untrusted_text(str(item.get("source_kind", "note")).lower())
            score_value = item.get("score", item.get("confidence", 0.5))
            if not isinstance(score_value, (int, float)):
                score_value = 0.5
            normalized.append(
                {
                    "evidence_id": sanitize_untrusted_text(str(item.get("evidence_id", f"ev-{idx}"))),
                    "source_kind": source_kind,
                    "content": " ".join(content.split()[:24]),
                    "score": round(max(0.0, min(1.0, float(score_value))), 2),
                }
            )
        elif isinstance(item, str) and item.strip():
            normalized.append(
                {
                    "evidence_id": f"ev-{idx}",
                    "source_kind": "note",
                    "content": " ".join(sanitize_untrusted_text(item.strip()).split()[:24]),
                    "score": 0.5,
                }
            )
    return normalized


def run_source_planner_agent(payload: dict[str, Any]) -> dict[str, Any]:
    query = require(payload, "query")
    current_evidence = payload.get("current_evidence", [])
    budget_limit = payload.get("budget_limit", 4)

    if not isinstance(query, str) or not query.strip():
        raise ValidationError("query must be a non-empty string")
    if current_evidence is None:
        current_evidence = []
    if not isinstance(current_evidence, list):
        raise ValidationError("current_evidence must be an array when provided")
    if not isinstance(budget_limit, int) or not (1 <= budget_limit <= 12):
        raise ValidationError("budget_limit must be an integer between 1 and 12")

    normalized = _normalize_evidence_contract(current_evidence)
    source_kinds = {item["source_kind"] for item in normalized}
    missing_primary = "measurement" not in source_kinds and "log" not in source_kinds
    missing_corroboration = len(normalized) < 2

    safe_query = " ".join(sanitize_untrusted_text(query.strip()).split()[:20])
    steps = [f"Clarify evidence goal for query: {safe_query}"]
    if missing_primary:
        steps.append("Collect primary telemetry or logs for the target window")
    if missing_corroboration:
        steps.append("Gather independent corroborating source for key assertion")
    steps.extend(
        [
            "Extract structured evidence objects with confidence scores",
            "Validate evidence consistency across source types",
            "Escalate unresolved gaps to targeted follow-up collection",
        ]
    )
    plan = [" ".join(step.split()[:16]) for step in steps[:budget_limit]]

    priorities = ["measurement", "log", "code", "policy", "report"]
    priority_sources = [item for item in priorities if item not in source_kinds][:3]
    if not priority_sources:
        priority_sources = ["measurement", "log"]

    coverage_target = 0.8 if missing_primary or missing_corroboration else 0.9
    return {
        "fetch_plan": plan,
        "priority_sources": priority_sources,
        "coverage_target": round(coverage_target, 2),
    }


def run_gap_detector_agent(payload: dict[str, Any]) -> dict[str, Any]:
    assertions = require(payload, "assertions")
    evidence_bundle = require(payload, "evidence_bundle")
    required_confidence = payload.get("required_confidence", 0.7)

    if not isinstance(assertions, list) or not assertions or not all(isinstance(item, str) for item in assertions):
        raise ValidationError("assertions must be a non-empty string array")
    if not isinstance(evidence_bundle, list) or not evidence_bundle:
        raise ValidationError("evidence_bundle must be a non-empty array")
    if not isinstance(required_confidence, (int, float)) or not (0 <= float(required_confidence) <= 1):
        raise ValidationError("required_confidence must be numeric in [0,1]")

    normalized = _normalize_evidence_contract(evidence_bundle)
    if not normalized:
        raise ValidationError("evidence_bundle did not contain valid evidence items")
    top_score = max(item["score"] for item in normalized)

    gaps = []
    for assertion in assertions:
        safe_assertion = " ".join(sanitize_untrusted_text(assertion).split()[:20])
        if top_score < float(required_confidence):
            gaps.append(
                {
                    "assertion": safe_assertion,
                    "support_status": "gap",
                    "confidence": round(top_score, 2),
                    "missing_evidence": "Need stronger corroborated evidence for this assertion",
                }
            )

    gap_ratio = len(gaps) / len(assertions)
    if gap_ratio == 0:
        risk_level = "low"
    elif gap_ratio < 0.5:
        risk_level = "medium"
    else:
        risk_level = "high"

    actions = []
    if gaps:
        actions = [
            "Collect primary telemetry tied to the weakest assertions",
            "Add at least one independent corroborating source per gap",
            "Re-score evidence bundle after data collection",
        ]
    return {
        "gaps": gaps,
        "risk_level": risk_level,
        "next_collection_actions": actions,
    }


def run_synthesis_agent(payload: dict[str, Any]) -> dict[str, Any]:
    notes = require(payload, "notes")
    audience = payload.get("audience", "engineering")
    output_format = payload.get("output_format", "brief")

    if not isinstance(notes, list) or not notes or not all(isinstance(item, str) for item in notes):
        raise ValidationError("notes must be a non-empty string array")
    if not isinstance(audience, str) or not audience.strip():
        raise ValidationError("audience must be a non-empty string")
    if output_format not in {"brief", "report"}:
        raise ValidationError("output_format must be one of brief,report")

    safe_notes = [sanitize_untrusted_text(item.strip()) for item in notes if item.strip()]
    headline = f"{audience.strip().title()} {output_format.title()} Summary"
    body_prefix = "Key findings: " if output_format == "brief" else "Research report summary: "
    summary = body_prefix + "; ".join(safe_notes[:3])
    summary = " ".join(summary.split()[:80])
    next_actions = [
        "Validate highest-impact claim with one primary source",
        "Document assumptions and unresolved risks",
        "Share summary with stakeholders for review",
    ]
    return {"headline": headline, "summary": summary, "next_actions": next_actions}


def run_evidence_ranker_agent(payload: dict[str, Any]) -> dict[str, Any]:
    assertions = require(payload, "assertions")
    evidence_items = require(payload, "evidence_items")
    max_evidence = payload.get("max_evidence", 5)

    if not isinstance(assertions, list) or not assertions or not all(isinstance(item, str) for item in assertions):
        raise ValidationError("assertions must be a non-empty string array")
    if not isinstance(evidence_items, list) or not evidence_items:
        raise ValidationError("evidence_items must be a non-empty array")
    if not isinstance(max_evidence, int) or max_evidence < 1 or max_evidence > 10:
        raise ValidationError("max_evidence must be an integer between 1 and 10")

    ranked: list[dict[str, Any]] = []
    for idx, item in enumerate(evidence_items, start=1):
        if not isinstance(item, dict):
            raise ValidationError("each evidence item must be an object")
        content = item.get("content", "")
        source_kind = str(item.get("source_kind", "note")).lower()
        corroboration_count = item.get("corroboration_count", 0)
        age_days = item.get("age_days", 14)
        relevance_hint = float(item.get("relevance_hint", 0.6))
        if not isinstance(content, str) or not content.strip():
            raise ValidationError("evidence item content must be a non-empty string")
        if not isinstance(corroboration_count, int) or corroboration_count < 0:
            raise ValidationError("evidence item corroboration_count must be a non-negative integer")
        if not isinstance(age_days, (int, float)) or age_days < 0:
            raise ValidationError("evidence item age_days must be a non-negative number")
        if not isinstance(relevance_hint, (int, float)):
            raise ValidationError("evidence item relevance_hint must be numeric")

        source_score_map = {
            "measurement": 0.95,
            "log": 0.85,
            "policy": 0.8,
            "code": 0.8,
            "report": 0.75,
            "note": 0.65,
        }
        source_score = source_score_map.get(source_kind, 0.6)
        freshness_score = max(0.2, 1.0 - (float(age_days) / 120.0))
        corroboration_score = min(1.0, 0.45 + (0.12 * corroboration_count))
        relevance_score = max(0.1, min(1.0, float(relevance_hint)))
        score = round(
            (source_score * 0.35) + (freshness_score * 0.2) + (corroboration_score * 0.25) + (relevance_score * 0.2),
            2,
        )
        ranked.append(
            {
                "evidence_id": f"ev-{idx}",
                "score": score,
                "source_kind": source_kind,
                "content": " ".join(sanitize_untrusted_text(content).split()[:24]),
                "corroboration_count": corroboration_count,
                "age_days": float(age_days),
            }
        )

    ranked.sort(key=lambda item: (-item["score"], item["evidence_id"]))
    selected = ranked[:max_evidence]
    avg = sum(float(item["score"]) for item in selected) / len(selected)
    return {"ranked_evidence": selected, "overall_confidence": round(avg, 2)}


def run_claim_trace_agent(payload: dict[str, Any]) -> dict[str, Any]:
    assertions = require(payload, "assertions")
    evidence_bundle = require(payload, "evidence_bundle")
    min_support_score = payload.get("min_support_score", 0.55)

    if not isinstance(assertions, list) or not assertions or not all(isinstance(item, str) for item in assertions):
        raise ValidationError("assertions must be a non-empty string array")
    if not isinstance(evidence_bundle, list) or not evidence_bundle:
        raise ValidationError("evidence_bundle must be a non-empty array")
    if not isinstance(min_support_score, (int, float)) or not (0 <= float(min_support_score) <= 1):
        raise ValidationError("min_support_score must be numeric in [0,1]")

    valid_evidence = [item for item in evidence_bundle if isinstance(item, dict) and isinstance(item.get("score"), (int, float))]
    if not valid_evidence:
        raise ValidationError("evidence_bundle must include scored evidence objects")

    sorted_evidence = sorted(valid_evidence, key=lambda item: float(item["score"]), reverse=True)
    trace: list[dict[str, Any]] = []
    supported = 0
    for assertion in assertions:
        safe_assertion = " ".join(sanitize_untrusted_text(assertion).split()[:24])
        refs = [str(item.get("evidence_id", "unknown")) for item in sorted_evidence[:2]]
        top_score = float(sorted_evidence[0]["score"])
        if top_score >= float(min_support_score) + 0.15:
            status = "supported"
            supported += 1
        elif top_score >= float(min_support_score):
            status = "weak"
        else:
            status = "unsupported"
        trace.append({"assertion": safe_assertion, "status": status, "evidence_refs": refs})

    coverage_score = round(supported / len(assertions), 2)
    return {"assertion_map": trace, "coverage_score": coverage_score}


def run_memory_curator_agent(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = require(payload, "run_id")
    artifacts = require(payload, "artifacts")
    memory_horizon_hours = payload.get("memory_horizon_hours", 24)

    if not isinstance(run_id, str) or not run_id.strip():
        raise ValidationError("run_id must be a non-empty string")
    if not isinstance(artifacts, list) or not artifacts or not all(isinstance(item, str) for item in artifacts):
        raise ValidationError("artifacts must be a non-empty string array")
    if not isinstance(memory_horizon_hours, int) or memory_horizon_hours < 1 or memory_horizon_hours > 720:
        raise ValidationError("memory_horizon_hours must be an integer between 1 and 720")

    updates = []
    for idx, artifact in enumerate(artifacts[:6], start=1):
        cleaned = sanitize_untrusted_text(artifact.strip())
        if not cleaned:
            continue
        updates.append(
            {
                "memory_key": f"{sanitize_untrusted_text(run_id.strip()).replace(' ', '-').lower()}:fact:{idx}",
                "fact": " ".join(cleaned.split()[:20]),
                "confidence": round(max(0.4, 0.8 - (0.05 * (idx - 1))), 2),
            }
        )

    return {"memory_updates": updates, "expires_in_hours": memory_horizon_hours}


def run_temporal_watch_agent(payload: dict[str, Any]) -> dict[str, Any]:
    current_snapshot = require(payload, "current_snapshot")
    prior_snapshot = require(payload, "prior_snapshot")
    window_label = payload.get("window_label", "24h")

    if not isinstance(current_snapshot, dict) or not current_snapshot:
        raise ValidationError("current_snapshot must be a non-empty object")
    if not isinstance(prior_snapshot, dict) or not prior_snapshot:
        raise ValidationError("prior_snapshot must be a non-empty object")
    if not isinstance(window_label, str) or not window_label.strip():
        raise ValidationError("window_label must be a non-empty string")

    current_keys = set(current_snapshot.keys())
    prior_keys = set(prior_snapshot.keys())
    added = sorted(current_keys - prior_keys)
    removed = sorted(prior_keys - current_keys)
    changed = sorted(key for key in (current_keys & prior_keys) if str(current_snapshot[key]) != str(prior_snapshot[key]))

    total_delta = len(added) + len(removed) + len(changed)
    if total_delta == 0:
        drift_level = "no_change"
    elif total_delta <= 2:
        drift_level = "minor_shift"
    else:
        drift_level = "major_shift"

    signals = []
    if added:
        signals.append(f"Added keys: {', '.join(added[:3])}")
    if removed:
        signals.append(f"Removed keys: {', '.join(removed[:3])}")
    if changed:
        signals.append(f"Changed keys: {', '.join(changed[:3])}")
    if not signals:
        signals.append("No temporal drift detected in compared snapshots")

    actions = [
        f"Revalidate assertions for window {sanitize_untrusted_text(window_label.strip())}",
        "Record drift decision and checkpoint downstream workflows",
    ]
    if drift_level == "major_shift":
        actions.insert(0, "Escalate major drift for manual review before automation")
    return {
        "temporal_signals": signals[:4],
        "drift_level": drift_level,
        "recommended_actions": actions[:3],
    }


def run_test_case_generator_agent(payload: dict[str, Any]) -> dict[str, Any]:
    feature = require(payload, "feature")
    acceptance_criteria = payload.get("acceptance_criteria", [])

    if not isinstance(feature, str) or not feature.strip():
        raise ValidationError("feature must be a non-empty string")
    if acceptance_criteria is None:
        acceptance_criteria = []
    if not isinstance(acceptance_criteria, list) or not all(isinstance(item, str) for item in acceptance_criteria):
        raise ValidationError("acceptance_criteria must be an array of strings")

    safe_feature = sanitize_untrusted_text(feature.strip())
    criteria = [sanitize_untrusted_text(item.strip()) for item in acceptance_criteria if item.strip()]
    criteria_snippet = criteria[:2] if criteria else ["basic flow"]

    cases = [
        f"Happy path: validate {safe_feature} with {criteria_snippet[0]}",
        f"Validation edge: reject invalid input for {safe_feature}",
        f"Boundary check: enforce limits and defaults for {safe_feature}",
        f"Failure path: verify clear error handling for {safe_feature}",
        f"Security check: block unauthorized access during {safe_feature}",
    ]
    risk_focus = "high" if any(token in safe_feature.lower() for token in ["auth", "payment", "billing", "admin"]) else "medium"
    return {"test_cases": [" ".join(case.split()[:18]) for case in cases], "risk_focus": risk_focus}


def run_regression_triage_agent(payload: dict[str, Any]) -> dict[str, Any]:
    failure_summary = require(payload, "failure_summary")
    changed_components = payload.get("changed_components", [])

    if not isinstance(failure_summary, str) or not failure_summary.strip():
        raise ValidationError("failure_summary must be a non-empty string")
    if changed_components is None:
        changed_components = []
    if not isinstance(changed_components, list) or not all(isinstance(item, str) for item in changed_components):
        raise ValidationError("changed_components must be an array of strings")

    lowered = failure_summary.lower()
    if any(token in lowered for token in ["timeout", "latency", "unreachable", "dns", "network"]):
        probable_cause = "infra"
    elif any(token in lowered for token in ["version", "package", "dependency", "sdk"]):
        probable_cause = "dependency"
    elif any(token in lowered for token in ["config", "flag", "env", "setting"]):
        probable_cause = "config"
    elif any(token in lowered for token in ["fixture", "seed", "test data", "dataset"]):
        probable_cause = "test-data"
    elif any(token in lowered for token in ["exception", "null", "panic", "traceback", "assert"]):
        probable_cause = "code"
    else:
        probable_cause = "unknown"

    severity = "sev2" if any(token in lowered for token in ["production", "outage", "critical"]) else "sev3"
    if any(token in lowered for token in ["minor", "cosmetic", "non-blocking"]):
        severity = "sev4"
    if "data loss" in lowered or "security breach" in lowered:
        severity = "sev1"

    safe_failure = sanitize_untrusted_text(failure_summary.strip())
    changed = ", ".join(
        sanitize_untrusted_text(item.strip()) for item in changed_components if isinstance(item, str) and item.strip()
    )
    actions = [
        f"Reproduce failure with focused logs for: {safe_failure}",
        "Compare failure window with most recent merged changes",
        f"Review changed components: {changed}" if changed else "Review changed components linked to the failing area",
    ]
    return {
        "probable_cause": probable_cause,
        "severity": severity,
        "recommended_actions": [" ".join(action.split()[:18]) for action in actions],
    }


def run_benchmark_curator_agent(payload: dict[str, Any]) -> dict[str, Any]:
    benchmark_name = require(payload, "benchmark_name")
    target_capability = payload.get("target_capability", "")
    candidate_cases = payload.get("candidate_cases")

    if not isinstance(benchmark_name, str) or not benchmark_name.strip():
        raise ValidationError("benchmark_name must be a non-empty string")
    if target_capability is not None and not isinstance(target_capability, str):
        raise ValidationError("target_capability must be a string when provided")
    if not isinstance(candidate_cases, list) or not candidate_cases:
        raise ValidationError("candidate_cases must be a non-empty array")

    safe_name = sanitize_untrusted_text(benchmark_name.strip())
    _ = target_capability  # reserved for future weighting; deterministic path ignores

    seen_ids: set[str] = set()
    excluded_duplicates: list[str] = []
    included: list[tuple[str, str]] = []

    for idx, item in enumerate(candidate_cases):
        if not isinstance(item, dict):
            raise ValidationError("each candidate_cases item must be an object")
        case_id = item.get("case_id")
        title = item.get("title")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValidationError(f"candidate_cases[{idx}].case_id must be a non-empty string")
        if not isinstance(title, str) or not title.strip():
            raise ValidationError(f"candidate_cases[{idx}].title must be a non-empty string")
        raw_id = sanitize_untrusted_text(case_id.strip())
        norm_id = raw_id.lower()
        safe_title = sanitize_untrusted_text(title.strip())
        if norm_id in seen_ids:
            excluded_duplicates.append(raw_id)
            continue
        seen_ids.add(norm_id)
        included.append((raw_id, safe_title))

    unique_count = len(included)
    if unique_count < 3:
        verdict: str = "sparse"
    elif unique_count < 5:
        verdict = "needs_expansion"
    else:
        verdict = "ready"

    combined_titles = " ".join(t.lower() for _, t in included)
    coverage_gaps: list[str] = []
    if not any(
        token in combined_titles
        for token in ("adversarial", "safety", "negative", "denial", "attack", "jailbreak")
    ):
        coverage_gaps.append("Add adversarial or safety-heavy eval scenarios")
    if unique_count < 5:
        coverage_gaps.append("Grow suite to at least five distinct case ids for stable coverage")
    if not coverage_gaps:
        coverage_gaps.append("Schedule periodic review against live incident taxonomy")
    if len(coverage_gaps) < 2 and unique_count >= 5:
        coverage_gaps.append("Add negative-path cases for permission denial if not already covered")
    coverage_gaps = [" ".join(g.split()[:24]) for g in coverage_gaps[:4]]

    sorted_ids = sorted(seen_ids)
    digest = hashlib.sha256(f"{safe_name}|{','.join(sorted_ids)}".encode("utf-8")).hexdigest()[:10]
    slug = "".join(ch if ch.isalnum() else "-" for ch in safe_name.lower()).strip("-")[:24] or "bench"
    curated_suite_id = f"{slug}-{digest}"

    included_cases = [
        " ".join((f"{cid}: {tit}").split()[:18]) for cid, tit in included[:12]
    ]

    return {
        "curated_suite_id": curated_suite_id,
        "included_cases": included_cases,
        "excluded_duplicates": excluded_duplicates[:12],
        "coverage_gaps": coverage_gaps,
        "curation_verdict": verdict,
    }


def _metric_lower_is_better(metric: str) -> bool:
    lowered = metric.lower()
    return any(
        token in lowered for token in ("latency", "p95", "p99", "error", "errors", "duration", "ttfb", "_ms")
    )


def run_regression_score_agent(payload: dict[str, Any]) -> dict[str, Any]:
    baseline_scores = require(payload, "baseline_scores")
    current_scores = require(payload, "current_scores")
    threshold = payload.get("regression_threshold_percent", 5.0)

    if not isinstance(baseline_scores, dict) or not baseline_scores:
        raise ValidationError("baseline_scores must be a non-empty object")
    if not isinstance(current_scores, dict) or not current_scores:
        raise ValidationError("current_scores must be a non-empty object")
    if not isinstance(threshold, (int, float)) or threshold <= 0:
        raise ValidationError("regression_threshold_percent must be a positive number when provided")

    shared_keys = sorted(set(baseline_scores) & set(current_scores))
    if not shared_keys:
        raise ValidationError("baseline_scores and current_scores must share at least one metric key")

    metric_deltas: list[str] = []
    worst_pct = 0.0
    regressed_metrics: list[str] = []

    for key in shared_keys:
        b_raw = baseline_scores[key]
        c_raw = current_scores[key]
        if not isinstance(b_raw, (int, float)) or not isinstance(c_raw, (int, float)):
            continue
        b_val = float(b_raw)
        c_val = float(c_raw)
        lower_better = _metric_lower_is_better(str(key))
        if lower_better:
            if b_val == 0:
                pct = 100.0 if c_val > 0 else 0.0
            else:
                pct = (c_val - b_val) / abs(b_val) * 100.0
            regressed = pct > float(threshold)
        else:
            if b_val == 0:
                pct = -100.0 if c_val < 0 else 0.0
            else:
                pct = (c_val - b_val) / abs(b_val) * 100.0
            regressed = pct < -float(threshold)

        metric_deltas.append(
            sanitize_untrusted_text(f"{key}: {b_val} -> {c_val} ({pct:+.1f}%)")
        )
        if regressed:
            regressed_metrics.append(str(key))
            worst_pct = max(worst_pct, abs(pct))

    if not metric_deltas:
        raise ValidationError("no comparable numeric metrics found across baseline and current")

    regression_flag = bool(regressed_metrics)
    if regression_flag:
        verdict = "fail" if worst_pct >= float(threshold) else "warn"
    else:
        verdict = "pass"

    findings: list[str] = [
        "No metric exceeded the configured regression threshold"
        if not regression_flag
        else f"Regression beyond threshold on: {', '.join(regressed_metrics[:4])}"
    ]
    findings.append(
        "Tighten change review or roll back if these metrics gate release"
        if verdict == "fail"
        else "Monitor the next eval run to confirm whether drift persists"
    )
    if len(findings) < 3:
        findings.append(
            "Compare prompts, tools, and data slices between baseline and current eval harnesses"
        )
    findings = [" ".join(f.split()[:24]) for f in findings[:4]]

    return {
        "regression_flag": regression_flag,
        "verdict": verdict,
        "metric_deltas": metric_deltas[:12],
        "findings": findings[:4],
    }


def run_quality_drift_reporter_agent(payload: dict[str, Any]) -> dict[str, Any]:
    metric_name = require(payload, "metric_name")
    windows = payload.get("windows")

    if not isinstance(metric_name, str) or not metric_name.strip():
        raise ValidationError("metric_name must be a non-empty string")
    if not isinstance(windows, list) or len(windows) < 2:
        raise ValidationError("windows must be an array with at least 2 entries")

    parsed: list[tuple[str, float]] = []
    for idx, win in enumerate(windows):
        if not isinstance(win, dict):
            raise ValidationError(f"windows[{idx}] must be an object")
        label = win.get("window_label")
        score = win.get("score")
        if not isinstance(label, str) or not label.strip():
            raise ValidationError(f"windows[{idx}].window_label must be a non-empty string")
        if not isinstance(score, (int, float)):
            raise ValidationError(f"windows[{idx}].score must be numeric")
        parsed.append((sanitize_untrusted_text(label.strip()), float(score)))

    lower_better = _metric_lower_is_better(metric_name)
    scores = [s for _, s in parsed]

    def _mean(vals: list[float]) -> float:
        return sum(vals) / len(vals) if vals else 0.0

    mean_s = _mean(scores)
    var = sum((x - mean_s) ** 2 for x in scores) / len(scores) if scores else 0.0
    std = var**0.5

    deltas = [scores[i] - scores[i - 1] for i in range(1, len(scores))]
    max_step = max(abs(d) for d in deltas) if deltas else 0.0
    volatile = len(scores) >= 4 and std > 0.04 and max_step > 0.05

    first, last = scores[0], scores[-1]
    epsilon = 1e-6
    if volatile:
        trend = "volatile"
    elif lower_better:
        if last < first - epsilon:
            trend = "improving"
        elif last > first + epsilon:
            trend = "degrading"
        else:
            trend = "stable"
    else:
        if last > first + epsilon:
            trend = "improving"
        elif last < first - epsilon:
            trend = "degrading"
        else:
            trend = "stable"

    span = abs(last - first)
    if volatile:
        drift_severity = "high" if max_step > 0.12 else "medium"
    elif span < 0.02:
        drift_severity = "none"
    elif span < 0.05:
        drift_severity = "low"
    elif span < 0.12:
        drift_severity = "medium"
    else:
        drift_severity = "high"

    windows_flagged: list[str] = []
    for i in range(1, len(parsed)):
        prev_s, cur_s = scores[i - 1], scores[i]
        if lower_better:
            step_bad = cur_s - prev_s > 0.04
        else:
            step_bad = prev_s - cur_s > 0.04
        if step_bad:
            windows_flagged.append(parsed[i][0])
    windows_flagged = windows_flagged[:4]

    safe_metric = sanitize_untrusted_text(metric_name.strip())
    report_summary = (
        f"{safe_metric} across {len(parsed)} windows shows {trend} trend with {drift_severity} drift; "
        f"first={first:.3f} last={last:.3f}."
    )
    report_summary = " ".join(report_summary.split()[:48])

    return {
        "drift_severity": drift_severity,
        "trend": trend,
        "windows_flagged": windows_flagged,
        "report_summary": report_summary,
    }


def run_hypothesis_registration_agent(payload: dict[str, Any]) -> dict[str, Any]:
    hypothesis_statement = require(payload, "hypothesis_statement")
    experiment_domain = payload.get("experiment_domain", "")

    if not isinstance(hypothesis_statement, str) or not hypothesis_statement.strip():
        raise ValidationError("hypothesis_statement must be a non-empty string")
    if experiment_domain is not None and not isinstance(experiment_domain, str):
        raise ValidationError("experiment_domain must be a string when provided")

    raw_stmt = hypothesis_statement.strip()
    safe_stmt = sanitize_untrusted_text(raw_stmt)
    normalized_statement = " ".join(safe_stmt.split()[:64])[:400]
    lowered = normalized_statement.lower()
    domain_raw = (experiment_domain or "").strip()
    safe_domain = sanitize_untrusted_text(domain_raw)[:48] if domain_raw else ""

    hedges = (
        "maybe ",
        "might ",
        "perhaps ",
        " could ",
        " i think",
        "probably ",
        "unclear",
        "uncertain",
        " not sure",
    )
    hedged = any(h in lowered for h in hedges) or "?" in normalized_statement
    measurable_tokens = (
        "rate",
        "latency",
        "accuracy",
        "conversion",
        "success",
        "metric",
        "p95",
        "p99",
        " p99",
        "throughput",
        "revenue",
        "error",
        "ctr",
        "f1",
        "precision",
        "recall",
    )
    has_digit = any(ch.isdigit() for ch in normalized_statement)
    measurable = has_digit or any(tok in lowered for tok in measurable_tokens)

    ambiguities: list[str] = []
    if hedged:
        ambiguities.append("Hedged language reduces falsifiability tighten wording")
    if len(normalized_statement) < 28:
        ambiguities.append("Statement is short add population metric and direction")
    if not measurable:
        ambiguities.append("Add explicit measurable outcome and unit or threshold")
    ambiguities = [" ".join(a.split()[:14]) for a in ambiguities[:4]]

    registration_status = "needs_clarification" if (hedged or len(normalized_statement) < 28 or not measurable) else "registered"

    digest = hashlib.sha256(f"{safe_domain}|{normalized_statement}".encode("utf-8")).hexdigest()[:12]
    slug = "".join(ch if ch.isalnum() else "-" for ch in (safe_domain or "hyp").lower()).strip("-")[:20] or "hyp"
    hypothesis_id = f"{slug}-{digest}"

    if registration_status == "registered":
        registration_notes = " ".join(
            (
                "Hypothesis registered with measurable cues suitable for experiment-plan-agent.",
                f"Domain hint: {safe_domain}" if safe_domain else "No experiment_domain provided.",
            )
        ).split()[:32]
    else:
        registration_notes = " ".join(
            (
                "Clarify ambiguities before locking allocation or success criteria.",
                "Re-run after edits to hypothesis_statement.",
            )
        ).split()[:32]
    registration_notes = " ".join(registration_notes)

    return {
        "hypothesis_id": hypothesis_id,
        "normalized_statement": normalized_statement,
        "registration_status": registration_status,
        "ambiguities": ambiguities,
        "registration_notes": registration_notes,
    }


def run_experiment_plan_agent(payload: dict[str, Any]) -> dict[str, Any]:
    hypothesis_statement = require(payload, "hypothesis_statement")
    constraints = payload.get("constraints") or {}

    if not isinstance(hypothesis_statement, str) or not hypothesis_statement.strip():
        raise ValidationError("hypothesis_statement must be a non-empty string")
    if not isinstance(constraints, dict):
        raise ValidationError("constraints must be an object when provided")

    raw_max = constraints.get("max_variants", 2)
    if isinstance(raw_max, bool) or not isinstance(raw_max, (int, float)):
        max_variants = 2
    else:
        max_variants = int(raw_max)
    max_variants = max(2, min(6, max_variants))

    risk_tol = constraints.get("risk_tolerance", "medium")
    risk_s = str(risk_tol).strip().lower() if risk_tol is not None else "medium"
    if risk_s not in {"low", "medium", "high"}:
        risk_s = "medium"

    safe_hyp = sanitize_untrusted_text(" ".join(hypothesis_statement.strip().split()[:48]))
    digest = hashlib.sha256(safe_hyp.encode("utf-8")).hexdigest()[:10]
    slug = "".join(ch if ch.isalnum() else "-" for ch in safe_hyp.lower())[:18].strip("-") or "plan"
    experiment_design_id = f"{slug}-{digest}"

    variants: list[str] = [
        "control: hold current experience without the proposed intervention",
        "treatment: apply the intervention described in the hypothesis to eligible subjects only",
    ]
    if max_variants >= 3:
        variants.append(
            "treatment_b: stronger intervention or alternate UX copy if hypothesis allows multiple levers"
        )
    if max_variants >= 4:
        variants.append("treatment_c: staged rollout variant for high-risk segments if applicable")
    if max_variants >= 5:
        variants.append("treatment_d: optional pricing or incentive arm if hypothesis mentions offers")
    if max_variants >= 6:
        variants.append("treatment_e: exploratory arm capped at small traffic fraction")
    variants = [" ".join(v.split()[:22]) for v in variants[:max_variants]]

    success_metrics = [
        "primary outcome aligned to hypothesis wording",
        "guardrail metrics such as errors latency and revenue per session",
    ]
    lowered = safe_hyp.lower()
    if "conversion" in lowered or "checkout" in lowered:
        success_metrics.insert(0, "checkout_conversion_rate")
    if "latency" in lowered or "p95" in lowered or "p99" in lowered:
        success_metrics.insert(0, "p95_latency_ms")
    if "click" in lowered or "ctr" in lowered:
        success_metrics.insert(0, "click_through_rate")
    success_metrics = [" ".join(m.split()[:12]) for m in success_metrics[:5]]

    guardrails = [
        "Start with low traffic allocation when risk_tolerance is low",
        "Predefine stop rules for regressions on safety or revenue metrics",
        "Log assignment and exposures for reproducibility",
    ]
    if risk_s == "low":
        guardrails.insert(0, "Cap initial exposure to a small fraction until stability checks pass")
    guardrails = [" ".join(g.split()[:18]) for g in guardrails[:4]]

    execution_risks = [
        "Selection bias if cohorts differ outside the intended manipulation",
        "Instrumentation drift if logging or metrics definitions change mid-flight",
    ]
    if "model" in lowered or "ranking" in lowered:
        execution_risks.append("Model freshness or data skew can confound short measurement windows")
    execution_risks = [" ".join(r.split()[:18]) for r in execution_risks[:4]]

    next_steps = [
        "Confirm primary metric minimum detectable effect and duration with analytics",
        "Wire feature flags and monitoring before enabling treatment traffic",
        "Schedule interim readouts with precommitted decision rules",
    ]
    next_steps = [" ".join(n.split()[:18]) for n in next_steps[:4]]

    return {
        "experiment_design_id": experiment_design_id,
        "variants": variants,
        "success_metrics": success_metrics,
        "guardrails": guardrails,
        "execution_risks": execution_risks,
        "next_steps": next_steps,
    }


def _parse_success_criteria(criteria: str) -> tuple[str | None, str | None, float | None]:
    """Return (metric, direction, threshold) where direction is 'above' or 'below'."""
    s = criteria.strip()
    if not s:
        return None, None, None
    m = re.search(
        r"^\s*([A-Za-z_][\w]*)\s+(above|below|at least|at most)\s+([-+]?\d*\.?\d+(?:e[-+]?\d+)?)\s*$",
        s,
        re.IGNORECASE,
    )
    if m:
        metric = m.group(1)
        dir_raw = m.group(2).lower()
        thr = float(m.group(3))
        direction = "above" if dir_raw in ("above", "at least") else "below"
        return metric, direction, thr
    m2 = re.search(r"^\s*([A-Za-z_][\w]*)\s*>\s*([-+]?\d*\.?\d+(?:e[-+]?\d+)?)\s*$", s)
    if m2:
        return m2.group(1), "above", float(m2.group(2))
    m3 = re.search(r"^\s*([A-Za-z_][\w]*)\s*<\s*([-+]?\d*\.?\d+(?:e[-+]?\d+)?)\s*$", s)
    if m3:
        return m3.group(1), "below", float(m3.group(2))
    return None, None, None


def run_result_adjudication_agent(payload: dict[str, Any]) -> dict[str, Any]:
    hypothesis_statement = require(payload, "hypothesis_statement")
    observed_metrics = require(payload, "observed_metrics")
    primary_metric = payload.get("primary_metric")
    success_criteria = payload.get("success_criteria", "")

    if not isinstance(hypothesis_statement, str) or not hypothesis_statement.strip():
        raise ValidationError("hypothesis_statement must be a non-empty string")
    if not isinstance(observed_metrics, dict) or not observed_metrics:
        raise ValidationError("observed_metrics must be a non-empty object")
    if primary_metric is not None and not isinstance(primary_metric, str):
        raise ValidationError("primary_metric must be a string when provided")
    if success_criteria is not None and not isinstance(success_criteria, str):
        raise ValidationError("success_criteria must be a string when provided")

    safe_hyp = sanitize_untrusted_text(" ".join(hypothesis_statement.strip().split()[:32]))

    keys_sorted = sorted(str(k) for k in observed_metrics.keys())
    metric_key: str | None = None
    if isinstance(primary_metric, str) and primary_metric.strip():
        pm = primary_metric.strip()
        if pm in observed_metrics:
            metric_key = pm
        else:
            for k in keys_sorted:
                if k.lower() == pm.lower():
                    metric_key = k
                    break
    if metric_key is None and keys_sorted:
        metric_key = keys_sorted[0]
    if metric_key is None:
        raise ValidationError("observed_metrics must contain at least one key")

    raw_val = observed_metrics[metric_key]
    if not isinstance(raw_val, (int, float)):
        raise ValidationError(f"observed_metrics[{metric_key!r}] must be numeric")
    value = float(raw_val)

    crit = success_criteria.strip() if isinstance(success_criteria, str) else ""
    parsed_metric, direction, threshold = _parse_success_criteria(crit)

    caveats: list[str] = []
    followups: list[str] = []

    if not crit or parsed_metric is None or direction is None or threshold is None:
        adjudication_verdict = "inconclusive"
        confidence = "low"
        caveats.append("No parseable numeric success_criteria provide explicit bound such as metric above 0.1")
        followups.append("Add success_criteria with metric threshold before final launch decision")
    else:
        pm = parsed_metric
        if pm not in observed_metrics:
            for k in keys_sorted:
                if k.lower() == pm.lower():
                    pm = k
                    break
        if pm not in observed_metrics:
            raise ValidationError("success_criteria metric must exist in observed_metrics")
        raw_val = observed_metrics[pm]
        if not isinstance(raw_val, (int, float)):
            raise ValidationError(f"observed_metrics[{pm!r}] must be numeric")
        value = float(raw_val)
        metric_key = pm

        margin = 1e-9
        if direction == "above":
            if value > threshold + margin:
                adjudication_verdict = "supports"
            elif value < threshold - margin:
                adjudication_verdict = "refutes"
            else:
                adjudication_verdict = "inconclusive"
        else:
            if value < threshold - margin:
                adjudication_verdict = "supports"
            elif value > threshold + margin:
                adjudication_verdict = "refutes"
            else:
                adjudication_verdict = "inconclusive"

        gap = abs(value - threshold)
        if adjudication_verdict == "inconclusive":
            confidence = "low"
        elif gap >= 0.05 * max(abs(threshold), 1e-6) or gap >= 0.02:
            confidence = "high"
        else:
            confidence = "medium"

        caveats.append("Single measurement window confirm stability across an additional cohort")
        followups.append("Document segment filters and rerun with precommitted decision thresholds")

    if adjudication_verdict != "inconclusive" or len(caveats) < 2:
        caveats.append("Compare against pre-registered baseline and variance estimates where available")
    if len(followups) < 2:
        followups.append("Archive inputs outputs and lineage for audit replay")

    caveats = [" ".join(c.split()[:18]) for c in caveats[:4]]
    followups = [" ".join(f.split()[:18]) for f in followups[:4]]

    return {
        "adjudication_verdict": adjudication_verdict,
        "confidence": confidence,
        "caveats": caveats,
        "recommended_followups": followups,
    }


def run_artifact_inventory_agent(payload: dict[str, Any]) -> dict[str, Any]:
    return build_artifact_inventory(payload)


def run_bundle_manifest_agent(payload: dict[str, Any]) -> dict[str, Any]:
    return build_bundle_manifest(payload)


def run_bundle_seal_agent(payload: dict[str, Any]) -> dict[str, Any]:
    return seal_repro_bundle(payload)


def run_router_agent(payload: dict[str, Any]) -> dict[str, Any]:
    task = require(payload, "task")
    available_agents = payload.get("available_agents", [])

    if not isinstance(task, str) or not task.strip():
        raise ValidationError("task must be a non-empty string")
    if available_agents is None:
        available_agents = []
    if not isinstance(available_agents, list) or not all(isinstance(item, str) for item in available_agents):
        raise ValidationError("available_agents must be an array of strings")

    safe_task = sanitize_untrusted_text(task.strip())
    lowered = safe_task.lower()

    target_agent = "planner-executor.planner-agent"
    rationale = "General planning intent detected; route to planner."
    if any(token in lowered for token in ["ticket", "incident", "cannot", "login", "support", "customer"]):
        target_agent = "support-ops.triage-agent"
        rationale = "Support issue intent detected; route to triage."
    elif any(token in lowered for token in ["handoff", "shift transition", "on-call handover", "incident handover"]):
        target_agent = "support-ops.handoff-agent"
        rationale = "Handoff intent detected; route to handoff agent."
    elif any(
        token in lowered
        for token in [
            "register hypothesis",
            "hypothesis registration",
            "log a hypothesis",
            "record a hypothesis",
        ]
    ):
        target_agent = "experiment-ops.hypothesis-registration-agent"
        rationale = "Hypothesis registration intent detected; route to hypothesis registration agent."
    elif any(
        token in lowered
        for token in [
            "experiment design",
            "experiment plan",
            "ab test plan",
            "a/b plan",
            "design an experiment",
        ]
    ):
        target_agent = "experiment-ops.experiment-plan-agent"
        rationale = "Experiment planning intent detected; route to experiment plan agent."
    elif any(
        token in lowered
        for token in [
            "adjudicate results",
            "adjudicate experiment",
            "supports or refutes",
            "experiment adjudication",
            "hypothesis supported",
        ]
    ):
        target_agent = "experiment-ops.result-adjudication-agent"
        rationale = "Result adjudication intent detected; route to result adjudication agent."
    elif any(token in lowered for token in ["test", "qa", "acceptance", "scenario"]):
        target_agent = "qa-ops.test-case-generator-agent"
        rationale = "QA/test intent detected; route to test-case generator."
    elif any(token in lowered for token in ["benchmark suite", "eval suite", "curate benchmark", "benchmark curation"]):
        target_agent = "eval-ops.benchmark-curator-agent"
        rationale = "Benchmark curation intent detected; route to benchmark curator."
    elif any(token in lowered for token in ["regression score", "score regression", "eval regression", "metric regression"]):
        target_agent = "eval-ops.regression-score-agent"
        rationale = "Eval regression scoring intent detected; route to regression score agent."
    elif any(token in lowered for token in ["metric drift", "quality drift", "eval drift", "drift report"]):
        target_agent = "eval-ops.quality-drift-reporter-agent"
        rationale = "Quality drift reporting intent detected; route to drift reporter."
    elif any(token in lowered for token in ["regression", "failure", "flaky", "timeout"]):
        target_agent = "qa-ops.regression-triage-agent"
        rationale = "Regression/failure intent detected; route to regression triage."
    elif any(token in lowered for token in ["research", "summarize", "findings", "source"]):
        target_agent = "research-ops.retrieval-agent"
        rationale = "Research intent detected; route to retrieval."
    elif any(token in lowered for token in ["source plan", "plan sources", "collection plan"]):
        target_agent = "research-ops.source-planner-agent"
        rationale = "Research source planning intent detected; route to source planner."
    elif any(token in lowered for token in ["evidence gap", "missing proof", "support gap"]):
        target_agent = "research-ops.gap-detector-agent"
        rationale = "Evidence gap intent detected; route to gap detector."
    elif any(token in lowered for token in ["evidence rank", "evidence quality", "source quality"]):
        target_agent = "knowledge-ops.evidence-ranker-agent"
        rationale = "Evidence ranking intent detected; route to evidence ranker."
    elif any(token in lowered for token in ["trace claim", "claim support", "assertion map"]):
        target_agent = "knowledge-ops.claim-trace-agent"
        rationale = "Assertion traceability intent detected; route to claim trace."
    elif any(token in lowered for token in ["curate memory", "memory update", "knowledge memory"]):
        target_agent = "knowledge-ops.memory-curator-agent"
        rationale = "Memory curation intent detected; route to memory curator."
    elif any(token in lowered for token in ["temporal drift", "snapshot drift", "time-window drift"]):
        target_agent = "knowledge-ops.temporal-watch-agent"
        rationale = "Temporal drift intent detected; route to temporal watch."
    elif any(token in lowered for token in ["security scan", "owasp", "scan repo", "controls"]):
        target_agent = "security-ops.agentic-security-scanner-agent"
        rationale = "Security scanning intent detected; route to scanner."
    elif any(token in lowered for token in ["seal run artifacts", "seal bundle", "bundle seal"]):
        target_agent = "artifact-ops.bundle-seal-agent"
        rationale = "Bundle seal intent detected; route to bundle seal agent."
    elif any(token in lowered for token in ["manifest checksum", "bundle manifest", "repro bundle manifest"]):
        target_agent = "artifact-ops.bundle-manifest-agent"
        rationale = "Manifest checksum intent detected; route to bundle manifest agent."
    elif any(
        token in lowered
        for token in [
            "artifact bundle",
            "repro bundle",
            "package run artifacts",
            "reproducible bundle",
            "artifact inventory",
        ]
    ):
        target_agent = "artifact-ops.artifact-inventory-agent"
        rationale = "Reproducible artifact packaging intent detected; route to artifact inventory agent."
    elif any(token in lowered for token in ["lineage", "decision record", "audit trail", "decision log"]):
        target_agent = "control-ops.lineage-recorder-agent"
        rationale = "Lineage/audit intent detected; route to lineage recorder."
    elif any(token in lowered for token in ["scope", "governance", "permission check", "validate action"]):
        target_agent = "control-ops.scope-validator-agent"
        rationale = "Governance/scope intent detected; route to scope validator."
    elif any(token in lowered for token in ["blast radius", "failure impact", "damage assessment"]):
        target_agent = "control-ops.blast-radius-assessor-agent"
        rationale = "Blast radius intent detected; route to assessor."
    elif any(token in lowered for token in ["kill path", "shutdown", "kill switch", "emergency stop"]):
        target_agent = "control-ops.kill-path-auditor-agent"
        rationale = "Kill path intent detected; route to auditor."
    elif any(token in lowered for token in ["schema drift", "schema change", "migration", "data validation", "validate data"]):
        target_agent = "data-ops.schema-drift-detector-agent"
        rationale = "Data/schema intent detected; route to data-ops."
    elif any(token in lowered for token in ["code review", "review diff", "review code", "pr review"]):
        target_agent = "code-ops.code-reviewer-agent"
        rationale = "Code review intent detected; route to code reviewer."
    elif any(token in lowered for token in ["pr summary", "pull request summary", "summarize pr"]):
        target_agent = "code-ops.pr-summary-agent"
        rationale = "PR summary intent detected; route to PR summarizer."
    elif any(token in lowered for token in ["log analysis", "analyze logs", "log entries", "anomaly detection"]):
        target_agent = "observability-ops.log-analyzer-agent"
        rationale = "Log analysis intent detected; route to log analyzer."
    elif any(token in lowered for token in ["change correlation", "correlate deploy", "config drift cause", "incident correlation"]):
        target_agent = "observability-ops.change-correlation-agent"
        rationale = "Change correlation intent detected; route to change correlation."
    elif any(token in lowered for token in ["alert tuning", "tune alert", "threshold tuning", "alert fatigue"]):
        target_agent = "observability-ops.alert-tuner-agent"
        rationale = "Alert tuning intent detected; route to alert tuner."
    elif any(token in lowered for token in ["slo", "sla", "compliance", "uptime report", "availability report"]):
        target_agent = "observability-ops.slo-reporter-agent"
        rationale = "SLO/compliance intent detected; route to SLO reporter."

    if available_agents and target_agent not in available_agents:
        target_agent = available_agents[0]
        rationale = "Preferred route unavailable; selected first available agent."

    priority = "p4"
    if any(token in lowered for token in ["critical", "outage", "breach", "production down"]):
        priority = "p1"
    elif any(token in lowered for token in ["urgent", "blocking", "cannot"]):
        priority = "p2"
    elif any(token in lowered for token in ["soon", "next sprint", "follow up"]):
        priority = "p3"

    return {
        "target_agent": target_agent,
        "priority": priority,
        "rationale": " ".join(rationale.split()[:24]),
    }


def run_dependency_router_agent(payload: dict[str, Any]) -> dict[str, Any]:
    task = require(payload, "task")
    available_agents = payload.get("available_agents", [])
    prerequisites = payload.get("prerequisites", [])
    completed_prerequisites = payload.get("completed_prerequisites", [])

    if not isinstance(task, str) or not task.strip():
        raise ValidationError("task must be a non-empty string")
    if available_agents is None:
        available_agents = []
    if prerequisites is None:
        prerequisites = []
    if completed_prerequisites is None:
        completed_prerequisites = []
    if not isinstance(available_agents, list) or not all(isinstance(item, str) for item in available_agents):
        raise ValidationError("available_agents must be an array of strings")
    if not isinstance(prerequisites, list) or not all(isinstance(item, str) for item in prerequisites):
        raise ValidationError("prerequisites must be an array of strings")
    if not isinstance(completed_prerequisites, list) or not all(isinstance(item, str) for item in completed_prerequisites):
        raise ValidationError("completed_prerequisites must be an array of strings")

    required = [sanitize_untrusted_text(item.strip()) for item in prerequisites if item.strip()]
    completed = {sanitize_untrusted_text(item.strip()) for item in completed_prerequisites if item.strip()}
    missing = [item for item in required if item not in completed]
    route = run_router_agent({"task": task, "available_agents": available_agents})

    if missing:
        return {
            "target_agent": "workflow-ops.checkpoint-agent",
            "ready": False,
            "missing_prerequisites": missing[:6],
            "priority": route["priority"],
            "rationale": "Missing prerequisites block target routing until dependencies are complete",
        }

    return {
        "target_agent": route["target_agent"],
        "ready": True,
        "missing_prerequisites": [],
        "priority": route["priority"],
        "rationale": route["rationale"],
    }


def run_retry_policy_agent(payload: dict[str, Any]) -> dict[str, Any]:
    stage_name = require(payload, "stage_name")
    failure_signal = require(payload, "failure_signal")
    attempt_count = require(payload, "attempt_count")
    max_attempts = require(payload, "max_attempts")
    latency_ms = payload.get("latency_ms", 0)

    if not isinstance(stage_name, str) or not stage_name.strip():
        raise ValidationError("stage_name must be a non-empty string")
    if not isinstance(failure_signal, str) or not failure_signal.strip():
        raise ValidationError("failure_signal must be a non-empty string")
    if not isinstance(attempt_count, int) or attempt_count < 1:
        raise ValidationError("attempt_count must be a positive integer")
    if not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValidationError("max_attempts must be a positive integer")
    if not isinstance(latency_ms, (int, float)) or latency_ms < 0:
        raise ValidationError("latency_ms must be a non-negative number when provided")

    safe_signal = sanitize_untrusted_text(failure_signal.strip()).lower()
    timeout_like = any(token in safe_signal for token in ["timeout", "latency", "temporarily unavailable"])
    blocked_like = any(token in safe_signal for token in ["unauthorized", "forbidden", "policy", "invalid"])
    attempts_exhausted = attempt_count >= max_attempts

    decision = "retry"
    reason_code = "retryable_failure"
    backoff_ms = 0
    next_step = "Retry stage and capture fresh telemetry"

    if blocked_like:
        decision = "stop"
        reason_code = "non_retryable_failure"
        next_step = "Stop automated retries and request manual intervention"
    elif attempts_exhausted:
        decision = "escalate"
        reason_code = "attempts_exhausted"
        next_step = "Escalate to on-call owner with failure context"
    elif timeout_like or float(latency_ms) > 2000:
        decision = "backoff"
        reason_code = "retryable_timeout"
        backoff_ms = min(15000, 1000 * (2 ** max(0, attempt_count - 1)))
        next_step = "Retry after backoff and monitor latency trend"

    return {
        "decision": decision,
        "backoff_ms": int(backoff_ms),
        "reason_code": reason_code,
        "next_step": " ".join(next_step.split()[:18]),
    }


def run_checkpoint_agent(payload: dict[str, Any]) -> dict[str, Any]:
    workflow_id = require(payload, "workflow_id")
    stage = require(payload, "stage")
    status = require(payload, "status")
    notes = payload.get("notes", "")

    if not isinstance(workflow_id, str) or not workflow_id.strip():
        raise ValidationError("workflow_id must be a non-empty string")
    if not isinstance(stage, str) or not stage.strip():
        raise ValidationError("stage must be a non-empty string")
    if status not in {"pending", "in_progress", "completed", "failed"}:
        raise ValidationError("status must be one of pending,in_progress,completed,failed")
    if notes is None:
        notes = ""
    if not isinstance(notes, str):
        raise ValidationError("notes must be a string when provided")

    safe_workflow = sanitize_untrusted_text(workflow_id.strip()).replace(" ", "-")
    safe_stage = sanitize_untrusted_text(stage.strip()).replace(" ", "-")
    safe_notes = sanitize_untrusted_text(notes.strip())
    checkpoint_id = f"{safe_workflow}:{safe_stage}:{status}".lower()
    summary = (
        f"Checkpoint recorded for workflow {safe_workflow} at stage {safe_stage} with status {status}. "
        f"{'Notes: ' + safe_notes if safe_notes else 'No notes provided.'}"
    )
    return {
        "checkpoint_id": checkpoint_id[:80],
        "recorded": True,
        "summary": " ".join(summary.split()[:50]),
    }


def run_lineage_recorder_agent(payload: dict[str, Any]) -> dict[str, Any]:
    return build_lineage_record(payload)


def run_scope_validator_agent(payload: dict[str, Any]) -> dict[str, Any]:
    assessment = assess_scope_validation(payload)
    return {
        "verdict": assessment["verdict"],
        "findings": assessment["findings"],
        "risk_level": assessment["risk_level"],
    }


def run_exception_policy_agent(payload: dict[str, Any]) -> dict[str, Any]:
    assessment = assess_exception_policy(payload)
    return {
        "exception_verdict": assessment["exception_verdict"],
        "exception_id": assessment["exception_id"],
        "owner": assessment["owner"],
        "expires_at": assessment["expires_at"],
        "conditions": assessment["conditions"],
        "reason_code": assessment["reason_code"],
    }


def run_approval_memory_agent(payload: dict[str, Any]) -> dict[str, Any]:
    assessment = assess_approval_memory(payload)
    return {
        "approval_record_id": assessment["approval_record_id"],
        "active": assessment["active"],
        "expired": assessment["expired"],
        "approver": assessment["approver"],
        "expires_at": assessment["expires_at"],
        "recall_hint": assessment["recall_hint"],
    }


def run_blast_radius_assessor_agent(payload: dict[str, Any]) -> dict[str, Any]:
    assessment = assess_blast_radius(payload)
    return {
        "risk_score": assessment["risk_score"],
        "max_damage_potential": assessment["max_damage_potential"],
        "detection_latency": assessment["detection_latency"],
        "containment_time": assessment["containment_time"],
        "findings": assessment["findings"],
        "recommended_controls": assessment["recommended_controls"],
    }


def run_kill_path_auditor_agent(payload: dict[str, Any]) -> dict[str, Any]:
    assessment = assess_kill_path(payload)
    return {
        "coverage_score": assessment["coverage_score"],
        "gaps": assessment["gaps"],
        "escalation_readiness": assessment["escalation_readiness"],
        "recommended_actions": assessment["recommended_actions"],
    }


def run_schema_drift_detector_agent(payload: dict[str, Any]) -> dict[str, Any]:
    schema_before = require(payload, "schema_before")
    schema_after = require(payload, "schema_after")

    if not isinstance(schema_before, dict) or not schema_before:
        raise ValidationError("schema_before must be a non-empty object")
    if not isinstance(schema_after, dict) or not schema_after:
        raise ValidationError("schema_after must be a non-empty object")

    changes: list[dict[str, str]] = []
    before_keys = set(schema_before.keys())
    after_keys = set(schema_after.keys())

    for key in sorted(before_keys - after_keys):
        changes.append({"field": key, "change_type": "removed", "detail": "field removed from schema"})
    for key in sorted(after_keys - before_keys):
        changes.append({"field": key, "change_type": "added", "detail": "new field added to schema"})
    for key in sorted(before_keys & after_keys):
        if str(schema_before[key]) != str(schema_after[key]):
            changes.append({
                "field": key,
                "change_type": "type_changed",
                "detail": f"type changed from {sanitize_untrusted_text(str(schema_before[key]))} to {sanitize_untrusted_text(str(schema_after[key]))}",
            })

    breaking = sum(1 for c in changes if c["change_type"] in {"removed", "type_changed"})
    if not changes:
        drift_severity = "none"
    elif breaking >= 2:
        drift_severity = "high"
    elif breaking == 1:
        drift_severity = "medium"
    else:
        drift_severity = "low"

    actions: list[str] = []
    removed = [c["field"] for c in changes if c["change_type"] == "removed"]
    added = [c["field"] for c in changes if c["change_type"] == "added"]
    type_changed = [c["field"] for c in changes if c["change_type"] == "type_changed"]

    if removed:
        actions.append(f"Verify removal of {', '.join(removed[:3])} is intentional and migrate dependent consumers")
    if added:
        actions.append(f"Update downstream pipelines to handle new field(s): {', '.join(added[:3])}")
    if type_changed:
        actions.append(f"Update consumers for type change in: {', '.join(type_changed[:3])}")
    if not actions:
        actions.append("No schema drift detected; no action required")

    return {
        "changes": changes[:10],
        "drift_severity": drift_severity,
        "recommended_actions": [" ".join(a.split()[:18]) for a in actions[:4]],
    }


def run_data_validator_agent(payload: dict[str, Any]) -> dict[str, Any]:
    records = require(payload, "records")
    rules = require(payload, "rules")

    if not isinstance(records, list) or not records:
        raise ValidationError("records must be a non-empty array")
    if not all(isinstance(r, dict) for r in records):
        raise ValidationError("each record must be an object")
    if not isinstance(rules, list) or not rules:
        raise ValidationError("rules must be a non-empty array of strings")
    if not all(isinstance(r, str) for r in rules):
        raise ValidationError("each rule must be a string")

    safe_rules = [sanitize_untrusted_text(r.strip()) for r in rules if r.strip()]
    violations: list[str] = []
    invalid_indices: set[int] = set()

    for idx, record in enumerate(records, start=1):
        for rule in safe_rules:
            lowered = rule.lower()
            for field_name, value in record.items():
                if field_name.lower() in lowered:
                    if "not be empty" in lowered or "non-empty" in lowered:
                        if value is None or (isinstance(value, str) and not value.strip()):
                            violations.append(f"Record {idx}: {rule} (value is empty)")
                            invalid_indices.add(idx)
                    if "non-negative" in lowered or "must be positive" in lowered:
                        if isinstance(value, (int, float)) and value < 0:
                            violations.append(f"Record {idx}: {rule} (value: {value})")
                            invalid_indices.add(idx)
                    if "required" in lowered:
                        if value is None:
                            violations.append(f"Record {idx}: {rule} (field is null)")
                            invalid_indices.add(idx)

    violations = violations[:10]
    invalid_count = len(invalid_indices)
    valid_count = len(records) - invalid_count

    if invalid_count == 0:
        verdict = "pass"
    elif invalid_count < len(records) / 2:
        verdict = "warn"
    else:
        verdict = "fail"

    return {
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "violations": [" ".join(v.split()[:18]) for v in violations],
        "verdict": verdict,
    }


def run_code_reviewer_agent(payload: dict[str, Any]) -> dict[str, Any]:
    diff = require(payload, "diff")
    context = payload.get("context", "")

    if not isinstance(diff, str) or not diff.strip():
        raise ValidationError("diff must be a non-empty string")
    if context is None:
        context = ""
    if not isinstance(context, str):
        raise ValidationError("context must be a string when provided")

    safe_diff = sanitize_untrusted_text(diff.strip())
    lowered = diff.lower()

    findings: list[str] = []

    security_patterns = {
        "hardcoded credential detected in diff": ["password =", "secret =", "api_key =", "token =", "hardcoded"],
        "Potential SQL injection via string interpolation": ["select *", "select ", "f'select", 'f"select', "where id ="],
        "Unsafe eval usage on user input": ["eval(", "exec("],
        "Potential command injection": ["os.system(", "subprocess.call(", "shell=true"],
    }
    correctness_patterns = {
        "Missing null or None check before access": ["nonetype", ".get("] if "if " not in lowered and "is none" not in lowered else [],
        "Broad exception catch may hide errors": ["except exception", "except:", "bare except"],
    }

    for finding, patterns in security_patterns.items():
        if any(p in lowered for p in patterns):
            findings.append(finding)
    for finding, patterns in correctness_patterns.items():
        if any(p in lowered for p in patterns):
            findings.append(finding)

    findings = findings[:6]

    if any("injection" in f.lower() or "eval" in f.lower() or "credential" in f.lower() or "command injection" in f.lower() for f in findings):
        severity = "critical"
    elif any("exception" in f.lower() or "null" in f.lower() for f in findings):
        severity = "major"
    elif findings:
        severity = "minor"
    else:
        severity = "clean"

    actions: list[str] = []
    if any("credential" in f.lower() for f in findings):
        actions.append("Move credentials to environment variables or secret manager")
    if any("injection" in f.lower() for f in findings):
        actions.append("Use parameterized queries instead of string interpolation")
    if any("eval" in f.lower() for f in findings):
        actions.append("Replace eval with safe parsing or allowlisted operations")
    if any("exception" in f.lower() for f in findings):
        actions.append("Narrow exception handling to specific error types")
    if any("command injection" in f.lower() for f in findings):
        actions.append("Use subprocess with argument lists instead of shell strings")
    if not actions:
        actions.append("No issues detected; approve for merge")

    return {
        "findings": findings,
        "severity": severity,
        "suggested_actions": [" ".join(a.split()[:18]) for a in actions[:4]],
    }


def run_pr_summary_agent(payload: dict[str, Any]) -> dict[str, Any]:
    title = require(payload, "title")
    changed_files = require(payload, "changed_files")
    diff_summary = payload.get("diff_summary", "")

    if not isinstance(title, str) or not title.strip():
        raise ValidationError("title must be a non-empty string")
    if not isinstance(changed_files, list) or not changed_files:
        raise ValidationError("changed_files must be a non-empty array of strings")
    if not all(isinstance(f, str) for f in changed_files):
        raise ValidationError("each changed_file must be a string")
    if diff_summary is None:
        diff_summary = ""
    if not isinstance(diff_summary, str):
        raise ValidationError("diff_summary must be a string when provided")

    safe_title = sanitize_untrusted_text(title.strip())
    safe_files = [sanitize_untrusted_text(f.strip()) for f in changed_files if f.strip()]
    safe_diff = sanitize_untrusted_text(diff_summary.strip()) if diff_summary else ""

    file_scope = f"{len(safe_files)} file(s)" if len(safe_files) > 3 else ", ".join(safe_files)
    summary = f"{safe_title}. Changes span {file_scope}."
    if safe_diff:
        summary += f" {safe_diff}"
    summary = " ".join(summary.split()[:40])

    sensitive_dirs = {"auth", "security", "credential", "secret", "payment", "billing", "admin"}
    infra_dirs = {"config", "infra", "deploy", "ci", "migration", "terraform", "k8s", "docker"}
    risk_areas: list[str] = []

    for f in safe_files:
        lowered = f.lower()
        for s in sensitive_dirs:
            if s in lowered:
                risk_areas.append(f"Sensitive area touched: {f}")
                break
        for s in infra_dirs:
            if s in lowered:
                risk_areas.append(f"Infrastructure change: {f}")
                break

    if not risk_areas:
        risk_areas.append("No high-risk file paths detected")

    risk_areas = list(dict.fromkeys(risk_areas))[:4]

    has_sensitive = any("sensitive" in r.lower() for r in risk_areas)
    if has_sensitive or len(safe_files) > 10:
        review_focus = "high"
    elif len(safe_files) > 4 or any("infrastructure" in r.lower() for r in risk_areas):
        review_focus = "medium"
    else:
        review_focus = "low"

    return {
        "summary": summary,
        "risk_areas": [" ".join(r.split()[:18]) for r in risk_areas],
        "review_focus": review_focus,
    }


def run_log_analyzer_agent(payload: dict[str, Any]) -> dict[str, Any]:
    log_entries = require(payload, "log_entries")
    time_range = payload.get("time_range", "")

    if not isinstance(log_entries, list) or not log_entries:
        raise ValidationError("log_entries must be a non-empty array of strings")
    if not all(isinstance(e, str) for e in log_entries):
        raise ValidationError("each log entry must be a string")
    if time_range is not None and not isinstance(time_range, str):
        raise ValidationError("time_range must be a string when provided")

    safe_entries = [sanitize_untrusted_text(e.strip()) for e in log_entries if e.strip()]
    total = len(safe_entries)

    error_count = sum(1 for e in safe_entries if "error" in e.lower())
    warn_count = sum(1 for e in safe_entries if "warn" in e.lower())
    info_count = sum(1 for e in safe_entries if "info" in e.lower())

    patterns: list[str] = []
    if error_count:
        patterns.append(f"{error_count} ERROR entries detected across {total} log lines")
    if warn_count:
        patterns.append(f"{warn_count} WARN entries detected across {total} log lines")
    if info_count:
        patterns.append(f"{info_count} INFO entries detected across {total} log lines")

    repeated: dict[str, int] = {}
    for entry in safe_entries:
        lowered = entry.lower()
        for keyword in ["timeout", "connection refused", "connection timeout", "out of memory", "disk full"]:
            if keyword in lowered:
                repeated[keyword] = repeated.get(keyword, 0) + 1
    for keyword, count in sorted(repeated.items(), key=lambda x: -x[1]):
        if count >= 2:
            patterns.append(f"Repeated {keyword}: {count} occurrences")

    if not patterns:
        patterns.append(f"{total} log entries with no notable patterns")
    patterns = patterns[:5]

    anomalies: list[str] = []
    if error_count >= 2:
        anomalies.append(f"Error spike: {error_count} errors in window")
    for keyword, count in repeated.items():
        if count >= 2:
            anomalies.append(f"{keyword.title()} spike: {count} occurrences in short window")

    auth_failures = sum(1 for e in safe_entries if "authentication failed" in e.lower() or "auth failure" in e.lower() or "unauthorized" in e.lower())
    if auth_failures:
        anomalies.append(f"Authentication failure from {'multiple sources' if auth_failures > 1 else 'unknown user'}")

    anomalies = list(dict.fromkeys(anomalies))[:5]

    if any("out of memory" in e.lower() or "disk full" in e.lower() or "data loss" in e.lower() for e in safe_entries):
        severity = "critical"
    elif error_count >= 3 or auth_failures >= 2:
        severity = "critical"
    elif anomalies:
        severity = "elevated"
    else:
        severity = "normal"

    return {
        "patterns": patterns,
        "anomalies": anomalies,
        "severity": severity,
    }


def run_slo_reporter_agent(payload: dict[str, Any]) -> dict[str, Any]:
    service_name = require(payload, "service_name")
    metrics = require(payload, "metrics")
    slo_targets = require(payload, "slo_targets")

    if not isinstance(service_name, str) or not service_name.strip():
        raise ValidationError("service_name must be a non-empty string")
    if not isinstance(metrics, dict) or not metrics:
        raise ValidationError("metrics must be a non-empty object")
    if not isinstance(slo_targets, dict) or not slo_targets:
        raise ValidationError("slo_targets must be a non-empty object")

    safe_name = sanitize_untrusted_text(service_name.strip())

    findings: list[str] = []
    breached_keys: list[str] = []
    at_risk_keys: list[str] = []

    for key in sorted(slo_targets.keys()):
        target = slo_targets[key]
        actual = metrics.get(key)
        if actual is None or not isinstance(actual, (int, float)) or not isinstance(target, (int, float)):
            findings.append(f"{key}: metric or target not numeric, skipped")
            continue

        is_higher_better = key.lower() in {"availability", "uptime", "throughput", "success_rate"}

        if is_higher_better:
            if actual >= target:
                findings.append(f"{key}: {actual} meets target {target} (met)")
            elif actual >= target * 0.95:
                findings.append(f"{key}: {actual} within 5% of target {target} (at risk)")
                at_risk_keys.append(key)
            else:
                findings.append(f"{key}: {actual} below target {target} (breached)")
                breached_keys.append(key)
        else:
            if actual <= target:
                findings.append(f"{key}: {actual} within target {target} (met)")
            elif actual <= target * 1.05:
                findings.append(f"{key}: {actual} within 5% of target {target} (at risk)")
                at_risk_keys.append(key)
            else:
                findings.append(f"{key}: {actual} above target {target} (breached)")
                breached_keys.append(key)

    if breached_keys:
        compliance_status = "breached"
    elif at_risk_keys:
        compliance_status = "at_risk"
    else:
        compliance_status = "met"

    actions: list[str] = []
    if breached_keys:
        actions.append(f"Investigate {', '.join(breached_keys[:2])} breach and review recent deployments for {safe_name}")
    if at_risk_keys:
        actions.append(f"Monitor {', '.join(at_risk_keys[:2])} closely to prevent SLO breach")
    if not actions:
        actions.append(f"All SLO targets met for {safe_name}; continue monitoring")

    return {
        "compliance_status": compliance_status,
        "findings": [" ".join(f.split()[:18]) for f in findings[:4]],
        "recommended_actions": [" ".join(a.split()[:18]) for a in actions[:3]],
    }


def _parse_rfc3339(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _signal_level(value: str) -> int:
    mapping = {"normal": 1, "elevated": 2, "critical": 3}
    return mapping.get(str(value).lower(), 1)


def run_change_correlation_agent(payload: dict[str, Any]) -> dict[str, Any]:
    incident_signals = require(payload, "incident_signals")
    deploy_events = payload.get("deploy_events", [])
    config_events = payload.get("config_events", [])
    window_minutes = payload.get("window_minutes", 90)

    if not isinstance(incident_signals, list) or not incident_signals or not all(isinstance(item, dict) for item in incident_signals):
        raise ValidationError("incident_signals must be a non-empty array of objects")
    if deploy_events is None:
        deploy_events = []
    if config_events is None:
        config_events = []
    if not isinstance(deploy_events, list) or not all(isinstance(item, dict) for item in deploy_events):
        raise ValidationError("deploy_events must be an array of objects")
    if not isinstance(config_events, list) or not all(isinstance(item, dict) for item in config_events):
        raise ValidationError("config_events must be an array of objects")
    if not isinstance(window_minutes, int) or not (5 <= window_minutes <= 720):
        raise ValidationError("window_minutes must be an integer between 5 and 720")

    candidates: list[dict[str, Any]] = []
    critical_count = 0
    for signal in incident_signals:
        signal_ts = _parse_rfc3339(str(signal.get("timestamp", "")))
        if signal_ts is None:
            continue
        service = str(signal.get("service", "")).strip().lower()
        severity = str(signal.get("severity", "normal")).lower()
        if _signal_level(severity) >= 3:
            critical_count += 1
        metric = sanitize_untrusted_text(str(signal.get("metric", "metric")))
        for event in deploy_events + config_events:
            event_ts = _parse_rfc3339(str(event.get("timestamp", "")))
            if event_ts is None:
                continue
            event_service = str(event.get("service", "")).strip().lower()
            if service and event_service and service != event_service:
                continue
            distance = int(abs((signal_ts - event_ts).total_seconds()) / 60)
            if distance > window_minutes:
                continue
            event_type = str(event.get("event", "change")).strip().lower() or "change"
            impact_hint = "high" if distance <= 15 or _signal_level(severity) >= 3 else "medium"
            candidates.append(
                {
                    "event_type": event_type,
                    "service": sanitize_untrusted_text(str(event.get("service", signal.get("service", "unknown-service")))),
                    "timestamp": sanitize_untrusted_text(str(event.get("timestamp", ""))),
                    "distance_minutes": distance,
                    "impact_hint": impact_hint,
                    "evidence": f"{metric} shifted near {event_type} event ({distance}m distance)",
                }
            )

    candidates.sort(key=lambda item: (item["distance_minutes"], 0 if item["impact_hint"] == "high" else 1))
    correlated_events = []
    seen: set[tuple[str, str, str]] = set()
    for item in candidates:
        key = (item["event_type"], item["service"], item["timestamp"])
        if key in seen:
            continue
        seen.add(key)
        correlated_events.append(item)
        if len(correlated_events) >= 5:
            break

    normalized_signals = []
    for signal in incident_signals[:5]:
        baseline = signal.get("baseline")
        observed = signal.get("observed")
        delta_percent = None
        if isinstance(baseline, (int, float)) and isinstance(observed, (int, float)) and float(baseline) != 0:
            delta_percent = round(((float(observed) - float(baseline)) / float(baseline)) * 100, 2)
        metric = sanitize_untrusted_text(str(signal.get("metric", "unknown_metric")))
        service = sanitize_untrusted_text(str(signal.get("service", "unknown-service")))
        timestamp = sanitize_untrusted_text(str(signal.get("timestamp", ""))) or "1970-01-01T00:00:00Z"
        severity = str(signal.get("severity", "elevated")).lower()
        if severity not in {"normal", "elevated", "critical"}:
            severity = "elevated"
        normalized_signals.append(
            {
                "signal_id": f"sig-{service.replace(' ', '-').lower()}-{metric.replace(' ', '-').lower()}",
                "timestamp": timestamp,
                "service": service,
                "signal_type": "metric_shift",
                "metric": metric,
                "baseline": float(baseline) if isinstance(baseline, (int, float)) else None,
                "observed": float(observed) if isinstance(observed, (int, float)) else None,
                "delta_percent": delta_percent,
                "severity": severity,
                "summary": "Incident signal aligned to nearby deploy/config events",
                "source_refs": [f"{item['event_type']}:{item['timestamp']}" for item in correlated_events[:3]],
            }
        )

    confidence = 0.35 + (0.12 * len(correlated_events)) + (0.08 * critical_count)
    confidence = round(max(0.0, min(0.95, confidence)), 2)
    summary = "No strong change correlation found in selected window."
    if correlated_events:
        summary = (
            f"Found {len(correlated_events)} likely correlated change events across "
            f"{len(normalized_signals)} incident signals."
        )
    return {
        "correlated_events": correlated_events,
        "incident_signals": normalized_signals,
        "confidence": confidence,
        "summary": " ".join(summary.split()[:18]),
    }


def run_alert_tuner_agent(payload: dict[str, Any]) -> dict[str, Any]:
    alert_history = require(payload, "alert_history")
    incident_labels = payload.get("incident_labels", [])
    target_precision = payload.get("target_precision", 0.6)

    if not isinstance(alert_history, list) or not alert_history or not all(isinstance(item, dict) for item in alert_history):
        raise ValidationError("alert_history must be a non-empty array of objects")
    if incident_labels is None:
        incident_labels = []
    if not isinstance(incident_labels, list) or not all(isinstance(item, dict) for item in incident_labels):
        raise ValidationError("incident_labels must be an array of objects")
    if not isinstance(target_precision, (int, float)) or not (0 <= float(target_precision) <= 1):
        raise ValidationError("target_precision must be numeric in [0,1]")

    missed_by_metric: dict[str, int] = {}
    for label in incident_labels:
        metric = str(label.get("metric", "")).strip()
        missed = label.get("missed_incidents", 0)
        if metric and isinstance(missed, int) and missed > 0:
            missed_by_metric[metric] = missed

    recommendations: list[dict[str, Any]] = []
    noise_values: list[float] = []
    for row in alert_history:
        metric = sanitize_untrusted_text(str(row.get("metric", "")))
        threshold = row.get("threshold")
        trigger_count = row.get("trigger_count", 0)
        actionable_count = row.get("actionable_count", 0)
        if not metric or not isinstance(threshold, (int, float)):
            continue
        if not isinstance(trigger_count, int) or trigger_count <= 0:
            continue
        if not isinstance(actionable_count, int) or actionable_count < 0:
            actionable_count = 0

        actionable_ratio = min(1.0, max(0.0, actionable_count / trigger_count))
        noise_ratio = round(1.0 - actionable_ratio, 2)
        noise_values.append(noise_ratio)

        change_type = None
        proposed_threshold = float(threshold)
        effect = ""
        if noise_ratio > (1.0 - float(target_precision)):
            change_type = "raise"
            proposed_threshold = round(float(threshold) * (1.0 + min(0.3, noise_ratio / 2)), 2)
            effect = "reduce noise with slight recall risk"
        elif missed_by_metric.get(metric, 0) > 0:
            change_type = "lower"
            proposed_threshold = round(float(threshold) * 0.9, 2)
            effect = "improve recall at acceptable noise increase"

        if change_type:
            recommendations.append(
                {
                    "metric": metric,
                    "current_threshold": float(threshold),
                    "proposed_threshold": proposed_threshold,
                    "change_type": change_type,
                    "expected_effect": effect,
                }
            )
        if len(recommendations) >= 5:
            break

    noise_score = round(sum(noise_values) / len(noise_values), 2) if noise_values else 0.0
    incident_signals = []
    for rec in recommendations[:5]:
        incident_signals.append(
            {
                "signal_id": f"sig-alert-{rec['metric'].replace(' ', '-').lower()}",
                "timestamp": "1970-01-01T00:00:00Z",
                "service": "observability-control-plane",
                "signal_type": "alert_tuning",
                "metric": rec["metric"],
                "baseline": rec["current_threshold"],
                "observed": rec["proposed_threshold"],
                "delta_percent": round(
                    ((rec["proposed_threshold"] - rec["current_threshold"]) / rec["current_threshold"]) * 100,
                    2,
                )
                if rec["current_threshold"]
                else None,
                "severity": "elevated" if noise_score >= 0.5 else "normal",
                "summary": f"Alert threshold {rec['change_type']} recommendation for {rec['metric']}",
                "source_refs": ["alert_history", f"target_precision:{float(target_precision):.2f}"],
            }
        )

    rationale = "Alert thresholds are stable; no immediate tuning required."
    if recommendations:
        rationale = (
            f"Generated {len(recommendations)} tuning recommendations from historical noise score {noise_score}."
        )
    return {
        "tuning_recommendations": recommendations,
        "incident_signals": incident_signals,
        "noise_score": noise_score,
        "rationale": " ".join(rationale.split()[:18]),
    }


def run_agent(
    agent: str,
    payload: dict[str, Any],
    mode: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    selected_mode = (mode or os.getenv("AGENT_MODE", "deterministic")).strip().lower()
    selected_model = model or os.getenv("LLM_MODEL", "llama3.2:3b")
    selected_base_url = base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434")
    canonical = agent.strip().lower()
    if selected_mode == "llm":
        validate_llm_runtime_source(selected_model, selected_base_url)
        from .llm import (
            run_artifact_inventory_agent_llm,
            run_blast_radius_assessor_agent_llm,
            run_benchmark_curator_agent_llm,
            run_approval_memory_agent_llm,
            run_bundle_manifest_agent_llm,
            run_bundle_seal_agent_llm,
            run_checkpoint_agent_llm,
            run_classifier_agent_llm,
            run_code_reviewer_agent_llm,
            run_data_validator_agent_llm,
            run_executor_agent_llm,
            run_experiment_plan_agent_llm,
            run_heartbeat_agent_llm,
            run_hypothesis_registration_agent_llm,
            run_kill_path_auditor_agent_llm,
            run_lineage_recorder_agent_llm,
            run_log_analyzer_agent_llm,
            run_change_correlation_agent_llm,
            run_alert_tuner_agent_llm,
            run_planner_agent_llm,
            run_pr_summary_agent_llm,
            run_quality_drift_reporter_agent_llm,
            run_regression_score_agent_llm,
            run_regression_triage_agent_llm,
            run_result_adjudication_agent_llm,
            run_retrieval_agent_llm,
            run_reply_drafter_agent_llm,
            run_router_agent_llm,
            run_dependency_router_agent_llm,
            run_claim_trace_agent_llm,
            run_evidence_ranker_agent_llm,
            run_handoff_agent_llm,
            run_gap_detector_agent_llm,
            run_memory_curator_agent_llm,
            run_exception_policy_agent_llm,
            run_retry_policy_agent_llm,
            run_source_planner_agent_llm,
            run_schema_drift_detector_agent_llm,
            run_scope_validator_agent_llm,
            run_slo_reporter_agent_llm,
            run_summary_agent_llm,
            run_synthesis_agent_llm,
            run_test_case_generator_agent_llm,
            run_temporal_watch_agent_llm,
            run_triage_agent_llm,
        )

    if canonical in {"heartbeat-agent", "starter-kit.heartbeat-agent"}:
        if selected_mode == "deterministic":
            return run_heartbeat_agent(payload)
        if selected_mode == "llm":
            return run_heartbeat_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"classifier-agent", "starter-kit.classifier-agent"}:
        if selected_mode == "deterministic":
            return run_classifier_agent(payload)
        if selected_mode == "llm":
            return run_classifier_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"triage-agent", "support-ops.triage-agent"}:
        if selected_mode == "deterministic":
            return run_triage_agent(payload)
        if selected_mode == "llm":
            return run_triage_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"reply-drafter-agent", "support-ops.reply-drafter-agent"}:
        if selected_mode == "deterministic":
            return run_reply_drafter_agent(payload)
        if selected_mode == "llm":
            return run_reply_drafter_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"summary-agent", "support-ops.summary-agent"}:
        if selected_mode == "deterministic":
            return run_summary_agent(payload)
        if selected_mode == "llm":
            return run_summary_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"handoff-agent", "support-ops.handoff-agent"}:
        if selected_mode == "deterministic":
            return run_handoff_agent(payload)
        if selected_mode == "llm":
            return run_handoff_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"agentic-security-scanner-agent", "security-ops.agentic-security-scanner-agent"}:
        if selected_mode == "deterministic":
            return run_agentic_security_scanner_agent(payload)
        raise ValidationError("security scanner currently supports deterministic mode only")

    if canonical in {"planner-agent", "planner-executor.planner-agent"}:
        if selected_mode == "deterministic":
            return run_planner_agent(payload)
        if selected_mode == "llm":
            return run_planner_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"executor-agent", "planner-executor.executor-agent"}:
        if selected_mode == "deterministic":
            return run_executor_agent(payload)
        if selected_mode == "llm":
            return run_executor_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"retrieval-agent", "research-ops.retrieval-agent"}:
        if selected_mode == "deterministic":
            return run_retrieval_agent(payload)
        if selected_mode == "llm":
            return run_retrieval_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"source-planner-agent", "research-ops.source-planner-agent"}:
        if selected_mode == "deterministic":
            return run_source_planner_agent(payload)
        if selected_mode == "llm":
            return run_source_planner_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"gap-detector-agent", "research-ops.gap-detector-agent"}:
        if selected_mode == "deterministic":
            return run_gap_detector_agent(payload)
        if selected_mode == "llm":
            return run_gap_detector_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"synthesis-agent", "research-ops.synthesis-agent"}:
        if selected_mode == "deterministic":
            return run_synthesis_agent(payload)
        if selected_mode == "llm":
            return run_synthesis_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"evidence-ranker-agent", "knowledge-ops.evidence-ranker-agent"}:
        if selected_mode == "deterministic":
            return run_evidence_ranker_agent(payload)
        if selected_mode == "llm":
            return run_evidence_ranker_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"claim-trace-agent", "knowledge-ops.claim-trace-agent"}:
        if selected_mode == "deterministic":
            return run_claim_trace_agent(payload)
        if selected_mode == "llm":
            return run_claim_trace_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"memory-curator-agent", "knowledge-ops.memory-curator-agent"}:
        if selected_mode == "deterministic":
            return run_memory_curator_agent(payload)
        if selected_mode == "llm":
            return run_memory_curator_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"temporal-watch-agent", "knowledge-ops.temporal-watch-agent"}:
        if selected_mode == "deterministic":
            return run_temporal_watch_agent(payload)
        if selected_mode == "llm":
            return run_temporal_watch_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"test-case-generator-agent", "qa-ops.test-case-generator-agent"}:
        if selected_mode == "deterministic":
            return run_test_case_generator_agent(payload)
        if selected_mode == "llm":
            return run_test_case_generator_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"regression-triage-agent", "qa-ops.regression-triage-agent"}:
        if selected_mode == "deterministic":
            return run_regression_triage_agent(payload)
        if selected_mode == "llm":
            return run_regression_triage_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"benchmark-curator-agent", "eval-ops.benchmark-curator-agent"}:
        if selected_mode == "deterministic":
            return run_benchmark_curator_agent(payload)
        if selected_mode == "llm":
            return run_benchmark_curator_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"regression-score-agent", "eval-ops.regression-score-agent"}:
        if selected_mode == "deterministic":
            return run_regression_score_agent(payload)
        if selected_mode == "llm":
            return run_regression_score_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"quality-drift-reporter-agent", "eval-ops.quality-drift-reporter-agent"}:
        if selected_mode == "deterministic":
            return run_quality_drift_reporter_agent(payload)
        if selected_mode == "llm":
            return run_quality_drift_reporter_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"hypothesis-registration-agent", "experiment-ops.hypothesis-registration-agent"}:
        if selected_mode == "deterministic":
            return run_hypothesis_registration_agent(payload)
        if selected_mode == "llm":
            return run_hypothesis_registration_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"experiment-plan-agent", "experiment-ops.experiment-plan-agent"}:
        if selected_mode == "deterministic":
            return run_experiment_plan_agent(payload)
        if selected_mode == "llm":
            return run_experiment_plan_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"result-adjudication-agent", "experiment-ops.result-adjudication-agent"}:
        if selected_mode == "deterministic":
            return run_result_adjudication_agent(payload)
        if selected_mode == "llm":
            return run_result_adjudication_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"artifact-inventory-agent", "artifact-ops.artifact-inventory-agent"}:
        if selected_mode == "deterministic":
            return run_artifact_inventory_agent(payload)
        if selected_mode == "llm":
            return run_artifact_inventory_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"bundle-manifest-agent", "artifact-ops.bundle-manifest-agent"}:
        if selected_mode == "deterministic":
            return run_bundle_manifest_agent(payload)
        if selected_mode == "llm":
            return run_bundle_manifest_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"bundle-seal-agent", "artifact-ops.bundle-seal-agent"}:
        if selected_mode == "deterministic":
            return run_bundle_seal_agent(payload)
        if selected_mode == "llm":
            return run_bundle_seal_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"router-agent", "workflow-ops.router-agent"}:
        if selected_mode == "deterministic":
            return run_router_agent(payload)
        if selected_mode == "llm":
            return run_router_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"dependency-router-agent", "workflow-ops.dependency-router-agent"}:
        if selected_mode == "deterministic":
            return run_dependency_router_agent(payload)
        if selected_mode == "llm":
            return run_dependency_router_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"retry-policy-agent", "workflow-ops.retry-policy-agent"}:
        if selected_mode == "deterministic":
            return run_retry_policy_agent(payload)
        if selected_mode == "llm":
            return run_retry_policy_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"checkpoint-agent", "workflow-ops.checkpoint-agent"}:
        if selected_mode == "deterministic":
            return run_checkpoint_agent(payload)
        if selected_mode == "llm":
            return run_checkpoint_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"lineage-recorder-agent", "control-ops.lineage-recorder-agent"}:
        if selected_mode == "deterministic":
            return run_lineage_recorder_agent(payload)
        if selected_mode == "llm":
            return run_lineage_recorder_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"scope-validator-agent", "control-ops.scope-validator-agent"}:
        if selected_mode == "deterministic":
            return run_scope_validator_agent(payload)
        if selected_mode == "llm":
            return run_scope_validator_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"exception-policy-agent", "control-ops.exception-policy-agent"}:
        if selected_mode == "deterministic":
            return run_exception_policy_agent(payload)
        if selected_mode == "llm":
            return run_exception_policy_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"approval-memory-agent", "control-ops.approval-memory-agent"}:
        if selected_mode == "deterministic":
            return run_approval_memory_agent(payload)
        if selected_mode == "llm":
            return run_approval_memory_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"blast-radius-assessor-agent", "control-ops.blast-radius-assessor-agent"}:
        if selected_mode == "deterministic":
            return run_blast_radius_assessor_agent(payload)
        if selected_mode == "llm":
            return run_blast_radius_assessor_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"kill-path-auditor-agent", "control-ops.kill-path-auditor-agent"}:
        if selected_mode == "deterministic":
            return run_kill_path_auditor_agent(payload)
        if selected_mode == "llm":
            return run_kill_path_auditor_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"schema-drift-detector-agent", "data-ops.schema-drift-detector-agent"}:
        if selected_mode == "deterministic":
            return run_schema_drift_detector_agent(payload)
        if selected_mode == "llm":
            return run_schema_drift_detector_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"data-validator-agent", "data-ops.data-validator-agent"}:
        if selected_mode == "deterministic":
            return run_data_validator_agent(payload)
        if selected_mode == "llm":
            return run_data_validator_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"code-reviewer-agent", "code-ops.code-reviewer-agent"}:
        if selected_mode == "deterministic":
            return run_code_reviewer_agent(payload)
        if selected_mode == "llm":
            return run_code_reviewer_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"pr-summary-agent", "code-ops.pr-summary-agent"}:
        if selected_mode == "deterministic":
            return run_pr_summary_agent(payload)
        if selected_mode == "llm":
            return run_pr_summary_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"log-analyzer-agent", "observability-ops.log-analyzer-agent"}:
        if selected_mode == "deterministic":
            return run_log_analyzer_agent(payload)
        if selected_mode == "llm":
            return run_log_analyzer_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"change-correlation-agent", "observability-ops.change-correlation-agent"}:
        if selected_mode == "deterministic":
            return run_change_correlation_agent(payload)
        if selected_mode == "llm":
            return run_change_correlation_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"alert-tuner-agent", "observability-ops.alert-tuner-agent"}:
        if selected_mode == "deterministic":
            return run_alert_tuner_agent(payload)
        if selected_mode == "llm":
            return run_alert_tuner_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    if canonical in {"slo-reporter-agent", "observability-ops.slo-reporter-agent"}:
        if selected_mode == "deterministic":
            return run_slo_reporter_agent(payload)
        if selected_mode == "llm":
            return run_slo_reporter_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    raise ValidationError(f"unsupported agent: {agent}")
