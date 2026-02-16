"""Deterministic and LLM-backed local implementations for catalog agents."""

from __future__ import annotations

import os
from typing import Any

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


def run_agentic_security_scanner_agent(payload: dict[str, Any]) -> dict[str, Any]:
    target_path = payload.get("target_path", ".")
    if not isinstance(target_path, str) or not target_path.strip():
        raise ValidationError("target_path must be a non-empty string")
    return scan_repository_controls(target_path.strip())


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
            run_classifier_agent_llm,
            run_executor_agent_llm,
            run_heartbeat_agent_llm,
            run_planner_agent_llm,
            run_retrieval_agent_llm,
            run_reply_drafter_agent_llm,
            run_synthesis_agent_llm,
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

    if canonical in {"synthesis-agent", "research-ops.synthesis-agent"}:
        if selected_mode == "deterministic":
            return run_synthesis_agent(payload)
        if selected_mode == "llm":
            return run_synthesis_agent_llm(payload, selected_model, selected_base_url)
        raise ValidationError(f"unsupported mode: {selected_mode}")

    raise ValidationError(f"unsupported agent: {agent}")
