"""Deterministic builders for cost-ops agents."""

from __future__ import annotations

from typing import Any

from .core import ValidationError, require, sanitize_untrusted_text


def run_cost_attribution(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = require(payload, "run_id")
    stages = require(payload, "stages")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValidationError("run_id must be a non-empty string")
    if not isinstance(stages, list) or not stages:
        raise ValidationError("stages must be a non-empty array")
    table = payload.get("price_table") or {}
    if not isinstance(table, dict):
        raise ValidationError("price_table must be an object when provided")
    pin = float(table.get("token_in_per_1k_usd", 0.001))
    pout = float(table.get("token_out_per_1k_usd", 0.002))
    prun = float(table.get("runtime_per_second_usd", 0.0005))

    stage_costs = []
    total = 0.0
    for row in stages[:32]:
        if not isinstance(row, dict):
            raise ValidationError("each stage must be an object")
        name = row.get("stage_name")
        tin = row.get("tokens_in", 0)
        tout = row.get("tokens_out", 0)
        rt = row.get("runtime_ms", 0)
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("stage_name must be a non-empty string")
        if not isinstance(tin, (int, float)) or not isinstance(tout, (int, float)) or not isinstance(rt, (int, float)):
            raise ValidationError("tokens and runtime must be numeric")
        if tin < 0 or tout < 0 or rt < 0:
            raise ValidationError("tokens and runtime must be non-negative")
        cost = (float(tin) / 1000.0) * pin + (float(tout) / 1000.0) * pout + (float(rt) / 1000.0) * prun
        cost = round(cost, 6)
        total += cost
        stage_costs.append({"stage_name": sanitize_untrusted_text(name.strip())[:80], "cost_usd": cost})
    stage_costs.sort(key=lambda x: x["cost_usd"], reverse=True)
    drivers = [f"{x['stage_name']} cost" for x in stage_costs[:2]]
    return {
        "run_id": sanitize_untrusted_text(run_id.strip())[:120],
        "stage_costs": stage_costs,
        "total_cost_usd": round(total, 6),
        "dominant_cost_drivers": drivers,
        "attribution_notes": "Computed token and runtime cost using observed metrics with fallback pricing.",
    }


def run_budget_guardrail(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = require(payload, "run_id")
    attribution = require(payload, "attribution")
    limits = require(payload, "budget_limits")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValidationError("run_id must be a non-empty string")
    if not isinstance(attribution, dict) or not isinstance(limits, dict):
        raise ValidationError("attribution and budget_limits must be objects")
    total = attribution.get("total_cost_usd")
    stages = attribution.get("stage_costs", [])
    if not isinstance(total, (int, float)):
        raise ValidationError("attribution.total_cost_usd must be numeric")
    if not isinstance(stages, list):
        raise ValidationError("attribution.stage_costs must be an array")
    run_limit = limits.get("run_limit_usd")
    warn_ratio = float(limits.get("warning_ratio", 0.8))
    stage_limit = limits.get("stage_limit_usd")
    if not isinstance(run_limit, (int, float)) or run_limit <= 0:
        raise ValidationError("budget_limits.run_limit_usd must be positive numeric")
    if not isinstance(stage_limit, (int, float)) or stage_limit <= 0:
        raise ValidationError("budget_limits.stage_limit_usd must be positive numeric")
    triggered = []
    status = "within"
    if float(total) >= float(run_limit):
        status = "breach"
        triggered.append("run_limit_exceeded")
    elif float(total) >= float(run_limit) * warn_ratio:
        status = "warning"
        triggered.append("run_limit_warning")
    for s in stages[:32]:
        if isinstance(s, dict) and isinstance(s.get("cost_usd"), (int, float)) and float(s["cost_usd"]) > float(stage_limit):
            triggered.append(f"stage_limit_exceeded:{sanitize_untrusted_text(str(s.get('stage_name','unknown')))[:40]}")
            status = "breach"
    mitigations = ["Reduce max output tokens on highest-cost stages.", "Apply stop condition when budget breaches."]
    if status == "within":
        mitigations = ["No mitigation required."]
    return {
        "run_id": sanitize_untrusted_text(run_id.strip())[:120],
        "budget_status": status,
        "triggered_guardrails": triggered[:8],
        "recommended_mitigations": mitigations[:6],
        "guardrail_notes": "Budget evaluation completed using run and stage limits.",
    }


def run_pipeline_optimizer(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = require(payload, "run_id")
    attribution = require(payload, "attribution")
    guardrails = require(payload, "guardrails")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValidationError("run_id must be a non-empty string")
    if not isinstance(attribution, dict) or not isinstance(guardrails, dict):
        raise ValidationError("attribution and guardrails must be objects")
    stages = attribution.get("stage_costs", [])
    if not isinstance(stages, list):
        raise ValidationError("attribution.stage_costs must be an array")
    top = sorted([x for x in stages if isinstance(x, dict)], key=lambda x: float(x.get("cost_usd", 0)), reverse=True)[:2]
    suggestions = []
    for idx, s in enumerate(top, start=1):
        name = sanitize_untrusted_text(str(s.get("stage_name", "stage")).strip())[:40]
        cost = float(s.get("cost_usd", 0))
        suggestions.append(
            {
                "suggestion": f"Reduce token ceiling on {name}.",
                "estimated_savings_usd": round(cost * 0.2, 6),
                "risk_tier": "low" if idx == 1 else "medium",
            }
        )
    if guardrails.get("budget_status") == "breach":
        suggestions.append(
            {
                "suggestion": "Route non-critical traffic to lower-cost model tier.",
                "estimated_savings_usd": 0.001,
                "risk_tier": "medium",
            }
        )
    return {
        "run_id": sanitize_untrusted_text(run_id.strip())[:120],
        "optimization_suggestions": suggestions[:5],
        "optimizer_notes": "Suggestions ranked by stage spend and guardrail pressure.",
    }
