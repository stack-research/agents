"""Ollama-backed implementations for catalog agents."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .control_ops import (
    assess_approval_memory,
    assess_blast_radius,
    assess_exception_policy,
    assess_kill_path,
    assess_scope_validation,
    build_lineage_record,
)
from .core import DEFAULT_LABELS, ValidationError, require, sanitize_untrusted_text


def _post_ollama(model: str, base_url: str, prompt: str) -> str:
    url = f"{base_url.rstrip('/')}/api/generate"
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    last_error: Exception | None = None
    for _ in range(2):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except TimeoutError as exc:
            last_error = exc
            continue
        except urllib.error.URLError as exc:
            raise ValidationError(f"unable to reach LLM endpoint at {url}: {exc}") from exc
    else:
        raise ValidationError(f"LLM request timed out at {url}: {last_error}")

    text = payload.get("response")
    if not isinstance(text, str) or not text.strip():
        raise ValidationError("LLM returned empty response")
    return text


def _extract_json(raw: str) -> dict[str, Any]:
    candidate = raw.strip()
    if candidate.startswith("```"):
        lines = [line for line in candidate.splitlines() if not line.strip().startswith("```")]
        candidate = "\n".join(lines).strip()

    def _extract_first_object(text: str) -> str:
        start = text.find("{")
        if start < 0:
            return text

        depth = 0
        in_string = False
        escaping = False
        for idx in range(start, len(text)):
            char = text[idx]
            if escaping:
                escaping = False
                continue
            if char == "\\" and in_string:
                escaping = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]
        return text

    candidate = _extract_first_object(candidate)

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"LLM output is not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValidationError("LLM output must be a JSON object")
    return parsed


def run_heartbeat_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    service_name = require(payload, "service_name")
    age = require(payload, "heartbeat_age_seconds")
    error_rate = require(payload, "error_rate_percent")

    if not isinstance(service_name, str) or not service_name.strip():
        raise ValidationError("service_name must be a non-empty string")
    if not isinstance(age, (int, float)):
        raise ValidationError("heartbeat_age_seconds must be numeric")
    if not isinstance(error_rate, (int, float)):
        raise ValidationError("error_rate_percent must be numeric")

    prompt = f"""
You are heartbeat-agent.
Return only JSON with keys status and report.
Rules:
- Base status from heartbeat_age_seconds: >90 critical, >30 warn, else ok.
- If error_rate_percent > 5, escalate one level (ok->warn, warn->critical).
- Report under 45 words including age and error rate.
Input:
{{"service_name":"{service_name}","heartbeat_age_seconds":{float(age)},"error_rate_percent":{float(error_rate)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)

    status = out.get("status")
    report = out.get("report")
    if status not in {"ok", "warn", "critical"}:
        raise ValidationError("LLM output status must be one of ok, warn, critical")
    if not isinstance(report, str) or not report.strip():
        raise ValidationError("LLM output report must be a non-empty string")

    return {"status": status, "report": report.strip()}


def run_classifier_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    text = require(payload, "text")
    labels = payload.get("labels") or DEFAULT_LABELS

    if not isinstance(text, str) or not text.strip():
        raise ValidationError("text must be a non-empty string")
    if not isinstance(labels, list) or not labels or not all(
        isinstance(item, str) and item for item in labels
    ):
        raise ValidationError("labels must be a non-empty string array")

    labels_json = json.dumps(labels)
    prompt = f"""
You are classifier-agent.
Return only JSON with keys label, confidence, rationale.
Rules:
- Choose exactly one label from labels.
- If ambiguous, choose unknown when present.
- confidence must be a number in [0,1].
- rationale under 30 words.
Input:
{{"text":{json.dumps(text)},"labels":{labels_json}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    try:
        out = _extract_json(raw)
    except ValidationError:
        repair_prompt = f"""
You are a strict JSON repair assistant.
Return only a valid JSON object with keys label, confidence, rationale.
- label: one of the provided labels.
- confidence: number in [0,1].
- rationale: non-empty short string.
Repair this malformed model output:
{json.dumps(raw)}
""".strip()
        repaired = _post_ollama(model, base_url, repair_prompt)
        out = _extract_json(repaired)

    label = out.get("label")
    confidence = out.get("confidence")
    rationale = out.get("rationale")

    if label not in labels:
        raise ValidationError("LLM output label must be one of input labels")
    if not isinstance(confidence, (int, float)) or not (0 <= float(confidence) <= 1):
        raise ValidationError("LLM output confidence must be numeric in [0,1]")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValidationError("LLM output rationale must be a non-empty string")

    return {
        "label": label,
        "confidence": round(float(confidence), 2),
        "rationale": rationale.strip(),
    }


def run_triage_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    text = require(payload, "text")
    customer_tier = payload.get("customer_tier", "free")

    if not isinstance(text, str) or not text.strip():
        raise ValidationError("text must be a non-empty string")
    if not isinstance(customer_tier, str):
        customer_tier = "free"
    tier = customer_tier.lower()
    if tier not in {"free", "pro", "enterprise"}:
        tier = "free"

    prompt = f"""
You are triage-agent.
Return only JSON with keys priority, category, next_action.
Rules:
- priority must be one of p1,p2,p3,p4.
- category must be one of billing,bug,access,feature,how-to,other.
- Use p1 for outage, data-loss, security, or production-down.
- next_action must be imperative and under 20 words.
Input:
{{"text":{json.dumps(text)},"customer_tier":{json.dumps(tier)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)

    priority = out.get("priority")
    category = out.get("category")
    next_action = out.get("next_action")

    if priority not in {"p1", "p2", "p3", "p4"}:
        raise ValidationError("LLM output priority must be one of p1,p2,p3,p4")
    if category not in {"billing", "bug", "access", "feature", "how-to", "other"}:
        raise ValidationError("LLM output category must be one of triage categories")
    if not isinstance(next_action, str) or not next_action.strip():
        raise ValidationError("LLM output next_action must be a non-empty string")

    return {
        "priority": priority,
        "category": category,
        "next_action": " ".join(next_action.strip().split()[:20]),
    }


def run_reply_drafter_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    priority = require(payload, "priority")
    category = require(payload, "category")
    issue_summary = require(payload, "issue_summary")
    customer_name = payload.get("customer_name", "")

    if priority not in {"p1", "p2", "p3", "p4"}:
        raise ValidationError("priority must be one of p1,p2,p3,p4")
    if category not in {"billing", "bug", "access", "feature", "how-to", "other"}:
        raise ValidationError("category must be one of billing,bug,access,feature,how-to,other")
    if not isinstance(issue_summary, str) or not issue_summary.strip():
        raise ValidationError("issue_summary must be a non-empty string")
    if not isinstance(customer_name, str):
        raise ValidationError("customer_name must be a string when provided")

    safe_issue_summary = sanitize_untrusted_text(issue_summary)
    prompt = f"""
You are reply-drafter-agent.
Return only JSON with keys subject and reply.
Rules:
- Subject under 12 words.
- Reply under 90 words.
- Professional tone.
- Include one concrete next step and a rough timeline.
Input:
{{"customer_name":{json.dumps(customer_name)},"priority":{json.dumps(priority)},"category":{json.dumps(category)},"issue_summary":{json.dumps(safe_issue_summary)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)

    subject = out.get("subject")
    reply = out.get("reply")

    if not isinstance(subject, str) or not subject.strip():
        raise ValidationError("LLM output subject must be a non-empty string")
    if not isinstance(reply, str) or not reply.strip():
        raise ValidationError("LLM output reply must be a non-empty string")

    safe_subject = sanitize_untrusted_text(" ".join(subject.strip().split()[:12]))
    safe_reply = sanitize_untrusted_text(" ".join(reply.strip().split()[:90]))
    return {"subject": safe_subject, "reply": safe_reply}


def run_summary_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
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

    prompt = f"""
You are summary-agent.
Return only JSON with keys ticket_count, priority_breakdown, top_categories, summary, recommended_actions.
Rules:
- ticket_count must be a non-negative integer.
- priority_breakdown must contain keys p1,p2,p3,p4 with non-negative integer counts.
- top_categories must be an array of up to 3 strings formatted as category:count.
- summary must be non-empty and under 80 words.
- recommended_actions must be an array with exactly top_n_actions concise strings.
Input:
{{"period_start":{json.dumps(period_start)},"period_end":{json.dumps(period_end)},"tickets":{json.dumps(tickets)},"top_n_actions":{top_n_actions}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)

    ticket_count = out.get("ticket_count")
    priority_breakdown = out.get("priority_breakdown")
    top_categories = out.get("top_categories")
    summary = out.get("summary")
    recommended_actions = out.get("recommended_actions")

    if not isinstance(ticket_count, int) or ticket_count < 0:
        raise ValidationError("LLM output ticket_count must be a non-negative integer")
    if not isinstance(priority_breakdown, dict):
        raise ValidationError("LLM output priority_breakdown must be an object")
    for key in ["p1", "p2", "p3", "p4"]:
        value = priority_breakdown.get(key)
        if not isinstance(value, int) or value < 0:
            raise ValidationError("LLM output priority_breakdown values must be non-negative integers")
    if not isinstance(top_categories, list) or len(top_categories) > 3:
        raise ValidationError("LLM output top_categories must be an array with at most 3 items")
    if not all(isinstance(item, str) and item.strip() for item in top_categories):
        raise ValidationError("LLM output top_categories items must be non-empty strings")
    if not isinstance(summary, str) or not summary.strip():
        raise ValidationError("LLM output summary must be a non-empty string")
    if not isinstance(recommended_actions, list) or len(recommended_actions) != top_n_actions:
        raise ValidationError("LLM output recommended_actions must match top_n_actions")
    if not all(isinstance(item, str) and item.strip() for item in recommended_actions):
        raise ValidationError("LLM output recommended_actions items must be non-empty strings")

    safe_categories = [sanitize_untrusted_text(" ".join(item.strip().split()[:4])) for item in top_categories]
    safe_summary = sanitize_untrusted_text(" ".join(summary.strip().split()[:80]))
    safe_actions = [sanitize_untrusted_text(" ".join(item.strip().split()[:16])) for item in recommended_actions]
    return {
        "ticket_count": ticket_count,
        "priority_breakdown": {
            "p1": int(priority_breakdown["p1"]),
            "p2": int(priority_breakdown["p2"]),
            "p3": int(priority_breakdown["p3"]),
            "p4": int(priority_breakdown["p4"]),
        },
        "top_categories": safe_categories,
        "summary": safe_summary,
        "recommended_actions": safe_actions,
    }


def run_handoff_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    shift_label = require(payload, "shift_label")
    incidents = require(payload, "incidents")
    handoff_window = payload.get("handoff_window", "next 8 hours")

    if not isinstance(shift_label, str) or not shift_label.strip():
        raise ValidationError("shift_label must be a non-empty string")
    if not isinstance(incidents, list):
        raise ValidationError("incidents must be an array")
    if not isinstance(handoff_window, str) or not handoff_window.strip():
        raise ValidationError("handoff_window must be a non-empty string")

    prompt = f"""
You are handoff-agent.
Return only JSON with keys active_count, critical_items, handoff_brief, recommended_checks.
Rules:
- active_count must be a non-negative integer.
- critical_items must be an array of up to 3 concise strings.
- handoff_brief must be non-empty and under 90 words.
- recommended_checks must contain exactly 3 concise imperative strings.
Input:
{{"shift_label":{json.dumps(shift_label)},"incidents":{json.dumps(incidents)},"handoff_window":{json.dumps(handoff_window)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    active_count = out.get("active_count")
    critical_items = out.get("critical_items")
    handoff_brief = out.get("handoff_brief")
    recommended_checks = out.get("recommended_checks")

    if not isinstance(active_count, int) or active_count < 0:
        raise ValidationError("LLM output active_count must be a non-negative integer")
    if not isinstance(critical_items, list) or len(critical_items) > 3:
        raise ValidationError("LLM output critical_items must have at most 3 items")
    if not all(isinstance(item, str) and item.strip() for item in critical_items):
        raise ValidationError("LLM output critical_items items must be non-empty strings")
    if not isinstance(handoff_brief, str) or not handoff_brief.strip():
        raise ValidationError("LLM output handoff_brief must be a non-empty string")
    if not isinstance(recommended_checks, list) or len(recommended_checks) != 3:
        raise ValidationError("LLM output recommended_checks must contain exactly 3 items")
    if not all(isinstance(item, str) and item.strip() for item in recommended_checks):
        raise ValidationError("LLM output recommended_checks items must be non-empty strings")

    safe_critical = [sanitize_untrusted_text(" ".join(item.strip().split()[:4])) for item in critical_items]
    safe_brief = sanitize_untrusted_text(" ".join(handoff_brief.strip().split()[:90]))
    safe_checks = [sanitize_untrusted_text(" ".join(item.strip().split()[:16])) for item in recommended_checks]
    return {
        "active_count": active_count,
        "critical_items": safe_critical,
        "handoff_brief": safe_brief,
        "recommended_checks": safe_checks,
    }


def run_planner_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    goal = require(payload, "goal")
    constraints = payload.get("constraints", [])

    if not isinstance(goal, str) or not goal.strip():
        raise ValidationError("goal must be a non-empty string")
    if constraints is None:
        constraints = []
    if not isinstance(constraints, list) or not all(isinstance(item, str) for item in constraints):
        raise ValidationError("constraints must be an array of strings")

    prompt = f"""
You are planner-agent.
Return only JSON with keys plan_steps and risk_level.
Rules:
- plan_steps must be 3 to 6 short imperative strings.
- each plan step under 18 words.
- risk_level must be one of low, medium, high.
Input:
{{"goal":{json.dumps(goal)},"constraints":{json.dumps(constraints)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    plan_steps = out.get("plan_steps")
    risk_level = out.get("risk_level")

    if not isinstance(plan_steps, list) or not (3 <= len(plan_steps) <= 6):
        raise ValidationError("LLM output plan_steps must be an array with 3 to 6 items")
    if not all(isinstance(item, str) and item.strip() for item in plan_steps):
        raise ValidationError("LLM output plan_steps items must be non-empty strings")
    if risk_level not in {"low", "medium", "high"}:
        raise ValidationError("LLM output risk_level must be one of low,medium,high")

    safe_steps = [sanitize_untrusted_text(" ".join(step.strip().split()[:18])) for step in plan_steps]
    return {"plan_steps": safe_steps, "risk_level": risk_level}


def run_executor_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    plan_steps = require(payload, "plan_steps")
    context = payload.get("context", "")

    if not isinstance(plan_steps, list) or not plan_steps or not all(isinstance(item, str) for item in plan_steps):
        raise ValidationError("plan_steps must be a non-empty string array")
    if context is None:
        context = ""
    if not isinstance(context, str):
        raise ValidationError("context must be a string when provided")

    prompt = f"""
You are executor-agent.
Return only JSON with keys status, completed_steps, blocked_steps, summary.
Rules:
- status must be done or partial.
- completed_steps and blocked_steps must be non-negative integers.
- summary under 60 words.
- completed_steps + blocked_steps must be <= number of input plan_steps.
Input:
{{"plan_steps":{json.dumps(plan_steps)},"context":{json.dumps(context)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    status = out.get("status")
    completed_steps = out.get("completed_steps")
    blocked_steps = out.get("blocked_steps")
    summary = out.get("summary")

    if status not in {"done", "partial"}:
        raise ValidationError("LLM output status must be done or partial")
    if not isinstance(completed_steps, int) or completed_steps < 0:
        raise ValidationError("LLM output completed_steps must be a non-negative integer")
    if not isinstance(blocked_steps, int) or blocked_steps < 0:
        raise ValidationError("LLM output blocked_steps must be a non-negative integer")
    if completed_steps + blocked_steps > len(plan_steps):
        raise ValidationError("LLM output step counts exceed input plan size")
    if not isinstance(summary, str) or not summary.strip():
        raise ValidationError("LLM output summary must be a non-empty string")

    safe_summary = sanitize_untrusted_text(" ".join(summary.strip().split()[:60]))
    return {
        "status": status,
        "completed_steps": completed_steps,
        "blocked_steps": blocked_steps,
        "summary": safe_summary,
    }


def run_retrieval_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
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

    prompt = f"""
You are retrieval-agent.
Return only JSON with keys notes and confidence.
Rules:
- notes must be an array of 1 to max_points short strings.
- each note under 20 words.
- confidence must be numeric in [0,1].
Input:
{{"query":{json.dumps(query)},"sources":{json.dumps(sources)},"max_points":{max_points}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    notes = out.get("notes")
    confidence = out.get("confidence")

    if not isinstance(notes, list) or not (1 <= len(notes) <= max_points):
        raise ValidationError("LLM output notes must be an array sized 1..max_points")
    if not all(isinstance(item, str) and item.strip() for item in notes):
        raise ValidationError("LLM output notes items must be non-empty strings")
    if not isinstance(confidence, (int, float)) or not (0 <= float(confidence) <= 1):
        raise ValidationError("LLM output confidence must be numeric in [0,1]")

    safe_notes = [sanitize_untrusted_text(" ".join(note.strip().split()[:20])) for note in notes]
    return {"notes": safe_notes, "confidence": round(float(confidence), 2)}


def _normalize_evidence_contract_llm(evidence_items: list[Any]) -> list[dict[str, Any]]:
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


def run_source_planner_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
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

    normalized_evidence = _normalize_evidence_contract_llm(current_evidence)
    prompt = f"""
You are source-planner-agent.
Return only JSON with keys fetch_plan, priority_sources, coverage_target.
Rules:
- fetch_plan must be 1..budget_limit concise strings.
- priority_sources must be 1..3 concise strings.
- coverage_target must be numeric in [0,1].
Input:
{{"query":{json.dumps(query)},"current_evidence":{json.dumps(normalized_evidence)},"budget_limit":{budget_limit}}}
""".strip()
    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    fetch_plan = out.get("fetch_plan")
    priority_sources = out.get("priority_sources")
    coverage_target = out.get("coverage_target")
    if not isinstance(fetch_plan, list) or not (1 <= len(fetch_plan) <= budget_limit):
        raise ValidationError("LLM output fetch_plan must contain 1..budget_limit items")
    if not isinstance(priority_sources, list) or not (1 <= len(priority_sources) <= 3):
        raise ValidationError("LLM output priority_sources must contain 1..3 items")
    if not isinstance(coverage_target, (int, float)) or not (0 <= float(coverage_target) <= 1):
        raise ValidationError("LLM output coverage_target must be numeric in [0,1]")
    safe_plan = [sanitize_untrusted_text(" ".join(str(item).split()[:16])) for item in fetch_plan]
    safe_sources = [sanitize_untrusted_text(" ".join(str(item).split()[:4])) for item in priority_sources]
    return {"fetch_plan": safe_plan, "priority_sources": safe_sources, "coverage_target": round(float(coverage_target), 2)}


def run_gap_detector_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    assertions = require(payload, "assertions")
    evidence_bundle = require(payload, "evidence_bundle")
    required_confidence = payload.get("required_confidence", 0.7)

    if not isinstance(assertions, list) or not assertions or not all(isinstance(item, str) for item in assertions):
        raise ValidationError("assertions must be a non-empty string array")
    if not isinstance(evidence_bundle, list) or not evidence_bundle:
        raise ValidationError("evidence_bundle must be a non-empty array")
    if not isinstance(required_confidence, (int, float)) or not (0 <= float(required_confidence) <= 1):
        raise ValidationError("required_confidence must be numeric in [0,1]")

    normalized_evidence = _normalize_evidence_contract_llm(evidence_bundle)
    prompt = f"""
You are gap-detector-agent.
Return only JSON with keys gaps, risk_level, next_collection_actions.
Rules:
- gaps must be an array of objects with assertion, support_status, confidence, missing_evidence.
- risk_level must be one of low, medium, high.
- next_collection_actions must be an array of 0..3 concise strings.
Input:
{{"assertions":{json.dumps(assertions)},"evidence_bundle":{json.dumps(normalized_evidence)},"required_confidence":{float(required_confidence)}}}
""".strip()
    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    gaps = out.get("gaps")
    risk_level = out.get("risk_level")
    actions = out.get("next_collection_actions")
    if not isinstance(gaps, list):
        raise ValidationError("LLM output gaps must be an array")
    if risk_level not in {"low", "medium", "high"}:
        raise ValidationError("LLM output risk_level must be low|medium|high")
    if not isinstance(actions, list) or len(actions) > 3:
        raise ValidationError("LLM output next_collection_actions must contain 0..3 items")
    safe_gaps = []
    for item in gaps[:10]:
        if not isinstance(item, dict):
            continue
        confidence = item.get("confidence", 0.0)
        if not isinstance(confidence, (int, float)):
            confidence = 0.0
        safe_gaps.append(
            {
                "assertion": sanitize_untrusted_text(" ".join(str(item.get("assertion", "")).split()[:20])),
                "support_status": sanitize_untrusted_text(str(item.get("support_status", "gap"))),
                "confidence": round(max(0.0, min(1.0, float(confidence))), 2),
                "missing_evidence": sanitize_untrusted_text(" ".join(str(item.get("missing_evidence", "")).split()[:16])),
            }
        )
    safe_actions = [sanitize_untrusted_text(" ".join(str(item).split()[:16])) for item in actions]
    return {"gaps": safe_gaps, "risk_level": risk_level, "next_collection_actions": safe_actions}


def run_synthesis_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    notes = require(payload, "notes")
    audience = payload.get("audience", "engineering")
    output_format = payload.get("output_format", "brief")

    if not isinstance(notes, list) or not notes or not all(isinstance(item, str) for item in notes):
        raise ValidationError("notes must be a non-empty string array")
    if not isinstance(audience, str) or not audience.strip():
        raise ValidationError("audience must be a non-empty string")
    if output_format not in {"brief", "report"}:
        raise ValidationError("output_format must be one of brief,report")

    prompt = f"""
You are synthesis-agent.
Return only JSON with keys headline, summary, next_actions.
Rules:
- headline must be a non-empty string under 12 words.
- summary must be a non-empty string under 80 words.
- next_actions must be 2 to 4 concise strings.
Input:
{{"notes":{json.dumps(notes)},"audience":{json.dumps(audience)},"output_format":{json.dumps(output_format)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    headline = out.get("headline")
    summary = out.get("summary")
    next_actions = out.get("next_actions")

    if not isinstance(headline, str) or not headline.strip():
        raise ValidationError("LLM output headline must be a non-empty string")
    if not isinstance(summary, str) or not summary.strip():
        raise ValidationError("LLM output summary must be a non-empty string")
    if not isinstance(next_actions, list) or not (2 <= len(next_actions) <= 4):
        raise ValidationError("LLM output next_actions must be 2 to 4 items")
    if not all(isinstance(item, str) and item.strip() for item in next_actions):
        raise ValidationError("LLM output next_actions items must be non-empty strings")

    safe_headline = sanitize_untrusted_text(" ".join(headline.strip().split()[:12]))
    safe_summary = sanitize_untrusted_text(" ".join(summary.strip().split()[:80]))
    safe_actions = [sanitize_untrusted_text(" ".join(item.strip().split()[:16])) for item in next_actions]
    return {"headline": safe_headline, "summary": safe_summary, "next_actions": safe_actions}


def run_evidence_ranker_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    assertions = require(payload, "assertions")
    evidence_items = require(payload, "evidence_items")
    max_evidence = payload.get("max_evidence", 5)

    if not isinstance(assertions, list) or not assertions or not all(isinstance(item, str) for item in assertions):
        raise ValidationError("assertions must be a non-empty string array")
    if not isinstance(evidence_items, list) or not evidence_items:
        raise ValidationError("evidence_items must be a non-empty array")
    if not isinstance(max_evidence, int) or max_evidence < 1 or max_evidence > 10:
        raise ValidationError("max_evidence must be an integer between 1 and 10")

    prompt = f"""
You are evidence-ranker-agent.
Return only JSON with keys ranked_evidence and overall_confidence.
Rules:
- ranked_evidence must be an array of 1..max_evidence objects.
- each object must include evidence_id, score, source_kind, content.
- score must be numeric in [0,1].
- overall_confidence must be numeric in [0,1].
Input:
{{"assertions":{json.dumps(assertions)},"evidence_items":{json.dumps(evidence_items)},"max_evidence":{max_evidence}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    ranked_evidence = out.get("ranked_evidence")
    overall_confidence = out.get("overall_confidence")
    if not isinstance(ranked_evidence, list) or not (1 <= len(ranked_evidence) <= max_evidence):
        raise ValidationError("LLM output ranked_evidence must be sized 1..max_evidence")
    if not isinstance(overall_confidence, (int, float)) or not (0 <= float(overall_confidence) <= 1):
        raise ValidationError("LLM output overall_confidence must be numeric in [0,1]")
    cleaned = []
    for idx, item in enumerate(ranked_evidence, start=1):
        if not isinstance(item, dict):
            continue
        score = item.get("score")
        if not isinstance(score, (int, float)):
            continue
        cleaned.append(
            {
                "evidence_id": str(item.get("evidence_id", f"ev-{idx}")),
                "score": round(float(score), 2),
                "source_kind": sanitize_untrusted_text(str(item.get("source_kind", "note"))),
                "content": sanitize_untrusted_text(" ".join(str(item.get("content", "")).split()[:24])),
            }
        )
    if not cleaned:
        raise ValidationError("LLM output ranked_evidence must contain object entries with numeric scores")
    return {"ranked_evidence": cleaned[:max_evidence], "overall_confidence": round(float(overall_confidence), 2)}


def run_claim_trace_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    assertions = require(payload, "assertions")
    evidence_bundle = require(payload, "evidence_bundle")
    min_support_score = payload.get("min_support_score", 0.55)

    if not isinstance(assertions, list) or not assertions or not all(isinstance(item, str) for item in assertions):
        raise ValidationError("assertions must be a non-empty string array")
    if not isinstance(evidence_bundle, list) or not evidence_bundle:
        raise ValidationError("evidence_bundle must be a non-empty array")
    if not isinstance(min_support_score, (int, float)) or not (0 <= float(min_support_score) <= 1):
        raise ValidationError("min_support_score must be numeric in [0,1]")

    prompt = f"""
You are claim-trace-agent.
Return only JSON with keys assertion_map and coverage_score.
Rules:
- assertion_map must be an array matching assertion count.
- each item must include assertion, status (supported|weak|unsupported), evidence_refs.
- coverage_score must be numeric in [0,1].
Input:
{{"assertions":{json.dumps(assertions)},"evidence_bundle":{json.dumps(evidence_bundle)},"min_support_score":{float(min_support_score)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    assertion_map = out.get("assertion_map")
    coverage_score = out.get("coverage_score")
    if not isinstance(assertion_map, list) or len(assertion_map) != len(assertions):
        raise ValidationError("LLM output assertion_map must match assertion count")
    if not isinstance(coverage_score, (int, float)) or not (0 <= float(coverage_score) <= 1):
        raise ValidationError("LLM output coverage_score must be numeric in [0,1]")
    normalized = []
    for idx, item in enumerate(assertion_map):
        if not isinstance(item, dict):
            raise ValidationError("LLM output assertion_map items must be objects")
        status = item.get("status")
        if status not in {"supported", "weak", "unsupported"}:
            raise ValidationError("LLM output status must be supported|weak|unsupported")
        refs = item.get("evidence_refs")
        if not isinstance(refs, list):
            refs = []
        normalized.append(
            {
                "assertion": sanitize_untrusted_text(" ".join(str(item.get("assertion", assertions[idx])).split()[:24])),
                "status": status,
                "evidence_refs": [sanitize_untrusted_text(str(ref)) for ref in refs[:3]],
            }
        )
    return {"assertion_map": normalized, "coverage_score": round(float(coverage_score), 2)}


def run_memory_curator_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    run_id = require(payload, "run_id")
    artifacts = require(payload, "artifacts")
    memory_horizon_hours = payload.get("memory_horizon_hours", 24)

    if not isinstance(run_id, str) or not run_id.strip():
        raise ValidationError("run_id must be a non-empty string")
    if not isinstance(artifacts, list) or not artifacts or not all(isinstance(item, str) for item in artifacts):
        raise ValidationError("artifacts must be a non-empty string array")
    if not isinstance(memory_horizon_hours, int) or memory_horizon_hours < 1 or memory_horizon_hours > 720:
        raise ValidationError("memory_horizon_hours must be an integer between 1 and 720")

    prompt = f"""
You are memory-curator-agent.
Return only JSON with keys memory_updates and expires_in_hours.
Rules:
- memory_updates must be 1..6 objects with memory_key, fact, confidence.
- confidence must be numeric in [0,1].
- expires_in_hours must be integer.
Input:
{{"run_id":{json.dumps(run_id)},"artifacts":{json.dumps(artifacts)},"memory_horizon_hours":{memory_horizon_hours}}}
""".strip()
    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    updates = out.get("memory_updates")
    expires_in_hours = out.get("expires_in_hours")
    if not isinstance(updates, list) or not (1 <= len(updates) <= 6):
        raise ValidationError("LLM output memory_updates must contain 1..6 items")
    if not isinstance(expires_in_hours, int):
        raise ValidationError("LLM output expires_in_hours must be an integer")
    normalized_updates = []
    for idx, item in enumerate(updates, start=1):
        if not isinstance(item, dict):
            continue
        confidence = item.get("confidence", 0.6)
        if not isinstance(confidence, (int, float)):
            confidence = 0.6
        normalized_updates.append(
            {
                "memory_key": sanitize_untrusted_text(str(item.get("memory_key", f"{run_id}:fact:{idx}"))),
                "fact": sanitize_untrusted_text(" ".join(str(item.get("fact", "")).split()[:20])),
                "confidence": round(max(0.0, min(1.0, float(confidence))), 2),
            }
        )
    if not normalized_updates:
        raise ValidationError("LLM output memory_updates must contain object items")
    return {"memory_updates": normalized_updates, "expires_in_hours": expires_in_hours}


def run_temporal_watch_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    current_snapshot = require(payload, "current_snapshot")
    prior_snapshot = require(payload, "prior_snapshot")
    window_label = payload.get("window_label", "24h")

    if not isinstance(current_snapshot, dict) or not current_snapshot:
        raise ValidationError("current_snapshot must be a non-empty object")
    if not isinstance(prior_snapshot, dict) or not prior_snapshot:
        raise ValidationError("prior_snapshot must be a non-empty object")
    if not isinstance(window_label, str) or not window_label.strip():
        raise ValidationError("window_label must be a non-empty string")

    prompt = f"""
You are temporal-watch-agent.
Return only JSON with keys temporal_signals, drift_level, recommended_actions.
Rules:
- temporal_signals must be 1..4 concise strings.
- drift_level must be one of no_change, minor_shift, major_shift.
- recommended_actions must be 1..3 concise strings.
Input:
{{"current_snapshot":{json.dumps(current_snapshot)},"prior_snapshot":{json.dumps(prior_snapshot)},"window_label":{json.dumps(window_label)}}}
""".strip()
    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    temporal_signals = out.get("temporal_signals")
    drift_level = out.get("drift_level")
    recommended_actions = out.get("recommended_actions")
    if not isinstance(temporal_signals, list) or not (1 <= len(temporal_signals) <= 4):
        raise ValidationError("LLM output temporal_signals must contain 1..4 items")
    if drift_level not in {"no_change", "minor_shift", "major_shift"}:
        raise ValidationError("LLM output drift_level must be no_change|minor_shift|major_shift")
    if not isinstance(recommended_actions, list) or not (1 <= len(recommended_actions) <= 3):
        raise ValidationError("LLM output recommended_actions must contain 1..3 items")
    safe_signals = [sanitize_untrusted_text(" ".join(str(item).split()[:16])) for item in temporal_signals]
    safe_actions = [sanitize_untrusted_text(" ".join(str(item).split()[:16])) for item in recommended_actions]
    return {"temporal_signals": safe_signals, "drift_level": drift_level, "recommended_actions": safe_actions}


def run_test_case_generator_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    feature = require(payload, "feature")
    acceptance_criteria = payload.get("acceptance_criteria", [])

    if not isinstance(feature, str) or not feature.strip():
        raise ValidationError("feature must be a non-empty string")
    if acceptance_criteria is None:
        acceptance_criteria = []
    if not isinstance(acceptance_criteria, list) or not all(isinstance(item, str) for item in acceptance_criteria):
        raise ValidationError("acceptance_criteria must be an array of strings")

    prompt = f"""
You are test-case-generator-agent.
Return only JSON with keys test_cases and risk_focus.
Rules:
- test_cases must be an array of 4 to 8 concise test descriptions.
- each test case under 18 words.
- risk_focus must be one of low, medium, high.
Input:
{{"feature":{json.dumps(feature)},"acceptance_criteria":{json.dumps(acceptance_criteria)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    test_cases = out.get("test_cases")
    risk_focus = out.get("risk_focus")

    if not isinstance(test_cases, list):
        raise ValidationError("LLM output test_cases must be an array")
    normalized_cases: list[str] = []
    for item in test_cases:
        if isinstance(item, str) and item.strip():
            normalized_cases.append(item.strip())
        elif item is not None:
            coerced = str(item).strip()
            if coerced:
                normalized_cases.append(coerced)
    normalized_focus = risk_focus if risk_focus in {"low", "medium", "high"} else "medium"
    safe_cases = [sanitize_untrusted_text(" ".join(item.split()[:18])) for item in normalized_cases[:8]]

    defaults = [
        f"Happy path: validate {sanitize_untrusted_text(feature)}",
        f"Validation edge: reject invalid input for {sanitize_untrusted_text(feature)}",
        f"Boundary check: enforce limits for {sanitize_untrusted_text(feature)}",
        f"Failure path: verify clear error handling for {sanitize_untrusted_text(feature)}",
    ]
    for default_case in defaults:
        if len(safe_cases) >= 4:
            break
        safe_cases.append(" ".join(default_case.split()[:18]))

    return {"test_cases": safe_cases[:8], "risk_focus": normalized_focus}


def run_regression_triage_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    failure_summary = require(payload, "failure_summary")
    changed_components = payload.get("changed_components", [])

    if not isinstance(failure_summary, str) or not failure_summary.strip():
        raise ValidationError("failure_summary must be a non-empty string")
    if changed_components is None:
        changed_components = []
    if not isinstance(changed_components, list) or not all(isinstance(item, str) for item in changed_components):
        raise ValidationError("changed_components must be an array of strings")

    prompt = f"""
You are regression-triage-agent.
Return only JSON with keys probable_cause, severity, recommended_actions.
Rules:
- probable_cause must be one of code, config, dependency, infra, test-data, unknown.
- severity must be one of sev1, sev2, sev3, sev4.
- recommended_actions must contain 2 to 4 concise strings.
Input:
{{"failure_summary":{json.dumps(failure_summary)},"changed_components":{json.dumps(changed_components)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    probable_cause = out.get("probable_cause")
    severity = out.get("severity")
    recommended_actions = out.get("recommended_actions")

    if probable_cause not in {"code", "config", "dependency", "infra", "test-data", "unknown"}:
        raise ValidationError("LLM output probable_cause must be in allowed enum")
    if severity not in {"sev1", "sev2", "sev3", "sev4"}:
        raise ValidationError("LLM output severity must be one of sev1,sev2,sev3,sev4")
    if not isinstance(recommended_actions, list) or not (2 <= len(recommended_actions) <= 4):
        raise ValidationError("LLM output recommended_actions must contain 2 to 4 items")
    if not all(isinstance(item, str) and item.strip() for item in recommended_actions):
        raise ValidationError("LLM output recommended_actions items must be non-empty strings")

    safe_actions = [sanitize_untrusted_text(" ".join(item.strip().split()[:18])) for item in recommended_actions]
    return {
        "probable_cause": probable_cause,
        "severity": severity,
        "recommended_actions": safe_actions,
    }


def run_router_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    task = require(payload, "task")
    available_agents = payload.get("available_agents", [])

    if not isinstance(task, str) or not task.strip():
        raise ValidationError("task must be a non-empty string")
    if available_agents is None:
        available_agents = []
    if not isinstance(available_agents, list) or not all(isinstance(item, str) for item in available_agents):
        raise ValidationError("available_agents must be an array of strings")

    prompt = f"""
You are router-agent.
Return only JSON with keys target_agent, priority, rationale.
Rules:
- target_agent must be a non-empty string.
- priority must be one of p1, p2, p3, p4.
- rationale must be a concise string under 24 words.
Input:
{{"task":{json.dumps(task)},"available_agents":{json.dumps(available_agents)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    target_agent = out.get("target_agent")
    priority = out.get("priority")
    rationale = out.get("rationale")

    if not isinstance(target_agent, str) or not target_agent.strip():
        raise ValidationError("LLM output target_agent must be a non-empty string")
    if priority not in {"p1", "p2", "p3", "p4"}:
        raise ValidationError("LLM output priority must be one of p1,p2,p3,p4")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValidationError("LLM output rationale must be a non-empty string")

    safe_target = sanitize_untrusted_text(" ".join(target_agent.strip().split()[:6]))
    safe_rationale = sanitize_untrusted_text(" ".join(rationale.strip().split()[:24]))
    if available_agents and safe_target not in available_agents:
        safe_target = available_agents[0]
        safe_rationale = "Preferred route unavailable; selected first available agent."
    return {"target_agent": safe_target, "priority": priority, "rationale": safe_rationale}


def run_dependency_router_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
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

    prompt = f"""
You are dependency-router-agent.
Return only JSON with keys target_agent, ready, missing_prerequisites, priority, rationale.
Rules:
- ready must be boolean.
- missing_prerequisites must be string array.
- priority must be one of p1,p2,p3,p4.
- rationale under 24 words.
Input:
{{"task":{json.dumps(task)},"available_agents":{json.dumps(available_agents)},"prerequisites":{json.dumps(prerequisites)},"completed_prerequisites":{json.dumps(completed_prerequisites)}}}
""".strip()
    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    target_agent = out.get("target_agent")
    ready = out.get("ready")
    missing = out.get("missing_prerequisites")
    priority = out.get("priority")
    rationale = out.get("rationale")

    if not isinstance(target_agent, str) or not target_agent.strip():
        raise ValidationError("LLM output target_agent must be a non-empty string")
    if not isinstance(ready, bool):
        raise ValidationError("LLM output ready must be a boolean")
    if not isinstance(missing, list) or not all(isinstance(item, str) for item in missing):
        raise ValidationError("LLM output missing_prerequisites must be an array of strings")
    if priority not in {"p1", "p2", "p3", "p4"}:
        raise ValidationError("LLM output priority must be one of p1,p2,p3,p4")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValidationError("LLM output rationale must be a non-empty string")

    safe_target = sanitize_untrusted_text(" ".join(target_agent.strip().split()[:6]))
    safe_rationale = sanitize_untrusted_text(" ".join(rationale.strip().split()[:24]))
    safe_missing = [sanitize_untrusted_text(" ".join(item.strip().split()[:4])) for item in missing if item.strip()]
    if available_agents and ready and safe_target not in available_agents:
        safe_target = available_agents[0]
        safe_rationale = "Preferred route unavailable; selected first available agent."
    if not ready:
        safe_target = "workflow-ops.checkpoint-agent"
    return {
        "target_agent": safe_target,
        "ready": ready,
        "missing_prerequisites": safe_missing[:6],
        "priority": priority,
        "rationale": safe_rationale,
    }


def run_retry_policy_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
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

    prompt = f"""
You are retry-policy-agent.
Return only JSON with keys decision, backoff_ms, reason_code, next_step.
Rules:
- decision must be one of retry,backoff,escalate,stop.
- backoff_ms must be non-negative integer.
- reason_code must be short snake_case string.
- next_step under 18 words.
Input:
{{"stage_name":{json.dumps(stage_name)},"failure_signal":{json.dumps(failure_signal)},"attempt_count":{attempt_count},"max_attempts":{max_attempts},"latency_ms":{int(latency_ms)}}}
""".strip()
    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    decision = out.get("decision")
    backoff_ms = out.get("backoff_ms")
    reason_code = out.get("reason_code")
    next_step = out.get("next_step")
    if decision not in {"retry", "backoff", "escalate", "stop"}:
        raise ValidationError("LLM output decision must be retry|backoff|escalate|stop")
    if not isinstance(backoff_ms, int) or backoff_ms < 0:
        raise ValidationError("LLM output backoff_ms must be a non-negative integer")
    if not isinstance(reason_code, str) or not reason_code.strip():
        raise ValidationError("LLM output reason_code must be a non-empty string")
    if not isinstance(next_step, str) or not next_step.strip():
        raise ValidationError("LLM output next_step must be a non-empty string")
    return {
        "decision": decision,
        "backoff_ms": backoff_ms,
        "reason_code": sanitize_untrusted_text(" ".join(reason_code.strip().split()[:4])),
        "next_step": sanitize_untrusted_text(" ".join(next_step.strip().split()[:18])),
    }


def run_lineage_recorder_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    return build_lineage_record(payload)


def run_scope_validator_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    assessment = assess_scope_validation(payload)
    return {
        "verdict": assessment["verdict"],
        "findings": assessment["findings"],
        "risk_level": assessment["risk_level"],
    }


def run_exception_policy_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    assessment = assess_exception_policy(payload)
    return {
        "exception_verdict": assessment["exception_verdict"],
        "exception_id": assessment["exception_id"],
        "owner": assessment["owner"],
        "expires_at": assessment["expires_at"],
        "conditions": assessment["conditions"],
        "reason_code": assessment["reason_code"],
    }


def run_approval_memory_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    assessment = assess_approval_memory(payload)
    return {
        "approval_record_id": assessment["approval_record_id"],
        "active": assessment["active"],
        "expired": assessment["expired"],
        "approver": assessment["approver"],
        "expires_at": assessment["expires_at"],
        "recall_hint": assessment["recall_hint"],
    }


def run_blast_radius_assessor_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    assessment = assess_blast_radius(payload)
    return {
        "risk_score": assessment["risk_score"],
        "max_damage_potential": assessment["max_damage_potential"],
        "detection_latency": assessment["detection_latency"],
        "containment_time": assessment["containment_time"],
        "findings": assessment["findings"],
        "recommended_controls": assessment["recommended_controls"],
    }


def run_kill_path_auditor_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    assessment = assess_kill_path(payload)
    return {
        "coverage_score": assessment["coverage_score"],
        "gaps": assessment["gaps"],
        "escalation_readiness": assessment["escalation_readiness"],
        "recommended_actions": assessment["recommended_actions"],
    }


def run_checkpoint_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
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

    prompt = f"""
You are checkpoint-agent.
Return only JSON with keys checkpoint_id, recorded, summary.
Rules:
- checkpoint_id must be a non-empty string.
- recorded must be true.
- summary must be under 50 words.
Input:
{{"workflow_id":{json.dumps(workflow_id)},"stage":{json.dumps(stage)},"status":{json.dumps(status)},"notes":{json.dumps(notes)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    checkpoint_id = out.get("checkpoint_id")
    recorded = out.get("recorded")
    summary = out.get("summary")

    if not isinstance(checkpoint_id, str) or not checkpoint_id.strip():
        raise ValidationError("LLM output checkpoint_id must be a non-empty string")
    if recorded is not True:
        raise ValidationError("LLM output recorded must be true")
    if not isinstance(summary, str) or not summary.strip():
        raise ValidationError("LLM output summary must be a non-empty string")

    safe_id = sanitize_untrusted_text(checkpoint_id.strip())[:80]
    safe_summary = sanitize_untrusted_text(" ".join(summary.strip().split()[:50]))
    return {"checkpoint_id": safe_id, "recorded": True, "summary": safe_summary}


def run_schema_drift_detector_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    schema_before = require(payload, "schema_before")
    schema_after = require(payload, "schema_after")

    if not isinstance(schema_before, dict) or not schema_before:
        raise ValidationError("schema_before must be a non-empty object")
    if not isinstance(schema_after, dict) or not schema_after:
        raise ValidationError("schema_after must be a non-empty object")

    prompt = f"""
You are schema-drift-detector-agent.
Return only JSON with keys changes, drift_severity, recommended_actions.
Rules:
- changes must be an array of objects with field, change_type (added|removed|type_changed), detail.
- drift_severity must be one of none, low, medium, high.
- recommended_actions must be 1-4 concise strings.
Input:
{{"schema_before":{json.dumps(schema_before)},"schema_after":{json.dumps(schema_after)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    changes = out.get("changes")
    drift_severity = out.get("drift_severity")
    recommended_actions = out.get("recommended_actions")

    if not isinstance(changes, list):
        raise ValidationError("LLM output changes must be an array")
    if drift_severity not in {"none", "low", "medium", "high"}:
        raise ValidationError("LLM output drift_severity must be one of none, low, medium, high")
    if not isinstance(recommended_actions, list) or not (1 <= len(recommended_actions) <= 4):
        raise ValidationError("LLM output recommended_actions must contain 1-4 items")
    if not all(isinstance(a, str) and a.strip() for a in recommended_actions):
        raise ValidationError("LLM output recommended_actions items must be non-empty strings")

    safe_changes = []
    for c in changes[:10]:
        if isinstance(c, dict) and isinstance(c.get("field"), str):
            safe_changes.append({
                "field": sanitize_untrusted_text(c["field"]),
                "change_type": c.get("change_type", "unknown"),
                "detail": sanitize_untrusted_text(str(c.get("detail", ""))),
            })
    safe_actions = [sanitize_untrusted_text(" ".join(a.strip().split()[:18])) for a in recommended_actions]
    return {"changes": safe_changes, "drift_severity": drift_severity, "recommended_actions": safe_actions}


def run_data_validator_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    records = require(payload, "records")
    rules = require(payload, "rules")

    if not isinstance(records, list) or not records:
        raise ValidationError("records must be a non-empty array")
    if not isinstance(rules, list) or not rules:
        raise ValidationError("rules must be a non-empty array of strings")

    prompt = f"""
You are data-validator-agent.
Return only JSON with keys valid_count, invalid_count, violations, verdict.
Rules:
- valid_count and invalid_count must be non-negative integers summing to the total record count.
- violations must be an array of up to 10 concise strings.
- verdict must be one of pass, warn, fail.
- pass if no violations, warn if <50% invalid, fail if >=50% invalid.
Input:
{{"records":{json.dumps(records)},"rules":{json.dumps(rules)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    valid_count = out.get("valid_count")
    invalid_count = out.get("invalid_count")
    violations = out.get("violations")
    verdict = out.get("verdict")

    if not isinstance(valid_count, int) or valid_count < 0:
        raise ValidationError("LLM output valid_count must be a non-negative integer")
    if not isinstance(invalid_count, int) or invalid_count < 0:
        raise ValidationError("LLM output invalid_count must be a non-negative integer")
    if not isinstance(violations, list):
        raise ValidationError("LLM output violations must be an array")
    if verdict not in {"pass", "warn", "fail"}:
        raise ValidationError("LLM output verdict must be one of pass, warn, fail")

    safe_violations = [sanitize_untrusted_text(" ".join(v.strip().split()[:18])) for v in violations[:10] if isinstance(v, str)]
    return {"valid_count": valid_count, "invalid_count": invalid_count, "violations": safe_violations, "verdict": verdict}


def run_code_reviewer_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    diff = require(payload, "diff")
    context = payload.get("context", "")

    if not isinstance(diff, str) or not diff.strip():
        raise ValidationError("diff must be a non-empty string")
    if context is None:
        context = ""

    safe_diff = sanitize_untrusted_text(diff.strip())
    safe_context = sanitize_untrusted_text(context.strip()) if context else ""

    prompt = f"""
You are code-reviewer-agent.
Return only JSON with keys findings, severity, suggested_actions.
Rules:
- findings must be an array of 0-6 concise strings describing issues.
- severity must be one of clean, minor, major, critical.
- suggested_actions must be an array of 1-4 concise strings.
Input:
{{"diff":{json.dumps(safe_diff)},"context":{json.dumps(safe_context)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    findings = out.get("findings")
    severity = out.get("severity")
    suggested_actions = out.get("suggested_actions")

    if not isinstance(findings, list):
        raise ValidationError("LLM output findings must be an array")
    if severity not in {"clean", "minor", "major", "critical"}:
        raise ValidationError("LLM output severity must be one of clean, minor, major, critical")
    if not isinstance(suggested_actions, list) or not (1 <= len(suggested_actions) <= 4):
        raise ValidationError("LLM output suggested_actions must contain 1-4 items")

    safe_findings = [sanitize_untrusted_text(" ".join(f.strip().split()[:18])) for f in findings[:6] if isinstance(f, str)]
    safe_actions = [sanitize_untrusted_text(" ".join(a.strip().split()[:18])) for a in suggested_actions]
    return {"findings": safe_findings, "severity": severity, "suggested_actions": safe_actions}


def run_pr_summary_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    title = require(payload, "title")
    changed_files = require(payload, "changed_files")
    diff_summary = payload.get("diff_summary", "")

    if not isinstance(title, str) or not title.strip():
        raise ValidationError("title must be a non-empty string")
    if not isinstance(changed_files, list) or not changed_files:
        raise ValidationError("changed_files must be a non-empty array of strings")
    if diff_summary is None:
        diff_summary = ""

    safe_title = sanitize_untrusted_text(title.strip())
    safe_files = [sanitize_untrusted_text(f.strip()) for f in changed_files if isinstance(f, str) and f.strip()]

    prompt = f"""
You are pr-summary-agent.
Return only JSON with keys summary, risk_areas, review_focus.
Rules:
- summary must be under 80 words.
- risk_areas must be an array of 1-4 concise strings.
- review_focus must be one of low, medium, high.
Input:
{{"title":{json.dumps(safe_title)},"changed_files":{json.dumps(safe_files)},"diff_summary":{json.dumps(diff_summary)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    summary = out.get("summary")
    risk_areas = out.get("risk_areas")
    review_focus = out.get("review_focus")

    if not isinstance(summary, str) or not summary.strip():
        raise ValidationError("LLM output summary must be a non-empty string")
    if not isinstance(risk_areas, list) or not (1 <= len(risk_areas) <= 4):
        raise ValidationError("LLM output risk_areas must contain 1-4 items")
    if review_focus not in {"low", "medium", "high"}:
        raise ValidationError("LLM output review_focus must be one of low, medium, high")

    safe_summary = sanitize_untrusted_text(" ".join(summary.strip().split()[:40]))
    safe_risks = [sanitize_untrusted_text(" ".join(r.strip().split()[:18])) for r in risk_areas if isinstance(r, str)]
    return {"summary": safe_summary, "risk_areas": safe_risks, "review_focus": review_focus}


def run_log_analyzer_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    log_entries = require(payload, "log_entries")
    time_range = payload.get("time_range", "")

    if not isinstance(log_entries, list) or not log_entries:
        raise ValidationError("log_entries must be a non-empty array of strings")
    if not all(isinstance(e, str) for e in log_entries):
        raise ValidationError("each log entry must be a string")

    safe_entries = [sanitize_untrusted_text(e.strip()) for e in log_entries if e.strip()]

    prompt = f"""
You are log-analyzer-agent.
Return only JSON with keys patterns, anomalies, severity.
Rules:
- patterns must be an array of 1-5 concise strings describing recurring patterns.
- anomalies must be an array of 0-5 concise strings describing anomalies.
- severity must be one of normal, elevated, critical.
Input:
{{"log_entries":{json.dumps(safe_entries)},"time_range":{json.dumps(time_range or "")}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    patterns = out.get("patterns")
    anomalies = out.get("anomalies")
    severity = out.get("severity")

    if not isinstance(patterns, list) or not (1 <= len(patterns) <= 5):
        raise ValidationError("LLM output patterns must contain 1-5 items")
    if not isinstance(anomalies, list) or len(anomalies) > 5:
        raise ValidationError("LLM output anomalies must contain 0-5 items")
    if severity not in {"normal", "elevated", "critical"}:
        raise ValidationError("LLM output severity must be one of normal, elevated, critical")

    safe_patterns = [sanitize_untrusted_text(" ".join(p.strip().split()[:18])) for p in patterns if isinstance(p, str)]
    safe_anomalies = [sanitize_untrusted_text(" ".join(a.strip().split()[:18])) for a in anomalies if isinstance(a, str)]
    return {"patterns": safe_patterns, "anomalies": safe_anomalies, "severity": severity}


def run_slo_reporter_agent_llm(payload: dict[str, Any], model: str, base_url: str) -> dict[str, Any]:
    service_name = require(payload, "service_name")
    metrics = require(payload, "metrics")
    slo_targets = require(payload, "slo_targets")

    if not isinstance(service_name, str) or not service_name.strip():
        raise ValidationError("service_name must be a non-empty string")
    if not isinstance(metrics, dict) or not metrics:
        raise ValidationError("metrics must be a non-empty object")
    if not isinstance(slo_targets, dict) or not slo_targets:
        raise ValidationError("slo_targets must be a non-empty object")

    prompt = f"""
You are slo-reporter-agent.
Return only JSON with keys compliance_status, findings, recommended_actions.
Rules:
- compliance_status must be one of met, at_risk, breached.
- findings must be an array of 1-4 concise strings.
- recommended_actions must be an array of 1-3 concise strings.
- Compare each metric against its SLO target numerically.
Input:
{{"service_name":{json.dumps(service_name)},"metrics":{json.dumps(metrics)},"slo_targets":{json.dumps(slo_targets)}}}
""".strip()

    raw = _post_ollama(model, base_url, prompt)
    out = _extract_json(raw)
    compliance_status = out.get("compliance_status")
    findings = out.get("findings")
    recommended_actions = out.get("recommended_actions")

    if compliance_status not in {"met", "at_risk", "breached"}:
        raise ValidationError("LLM output compliance_status must be one of met, at_risk, breached")
    if not isinstance(findings, list) or not (1 <= len(findings) <= 4):
        raise ValidationError("LLM output findings must contain 1-4 items")
    if not isinstance(recommended_actions, list) or not (1 <= len(recommended_actions) <= 3):
        raise ValidationError("LLM output recommended_actions must contain 1-3 items")

    safe_findings = [sanitize_untrusted_text(" ".join(f.strip().split()[:18])) for f in findings if isinstance(f, str)]
    safe_actions = [sanitize_untrusted_text(" ".join(a.strip().split()[:18])) for a in recommended_actions]
    return {"compliance_status": compliance_status, "findings": safe_findings, "recommended_actions": safe_actions}
