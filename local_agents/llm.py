"""Ollama-backed implementations for catalog agents."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

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
