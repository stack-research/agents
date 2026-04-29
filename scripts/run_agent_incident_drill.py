#!/usr/bin/env python3
"""Run an agent incident drill over existing catalog agents."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from local_agents import ValidationError, run_agent
from local_agents.control_ops import governance_pipeline_status, resilience_verdict_from_scores


def _string(payload: dict[str, object], key: str, default: str = "") -> str:
    value = payload.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValidationError(f"{key} must be a string")
    return value.strip()


def _string_list(payload: dict[str, object], key: str) -> list[str]:
    value = payload.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValidationError(f"{key} must be an array of strings")
    return [item.strip() for item in value if item.strip()]


def _object(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValidationError(f"{key} must be an object")
    return value


def _event(step: int, stage: str, status: str, summary: str) -> dict[str, object]:
    return {
        "event_id": f"event-{step:02d}",
        "stage": stage,
        "status": status,
        "summary": summary,
    }


def _degraded_output(workflow_id: str, scenario: str, stage: str, reason: str) -> dict[str, object]:
    return {
        "workflow_id": workflow_id,
        "scenario": scenario,
        "event_journal": [_event(1, stage, "degraded", reason)],
        "governance": {
            "verdict": "review",
            "findings": ["Drill degraded; manual incident review required."],
            "risk_level": "high",
        },
        "resilience": {
            "resilience_verdict": "inadequate",
            "blast_radius": {},
            "kill_path": {},
        },
        "lineage_query": {
            "query": "which actions were influenced by the triggering incident text?",
            "matched_lineage_ids": [],
            "influenced_actions": [],
        },
        "containment_timing": {
            "detected_at_step": stage,
            "contained_at_step": "manual-review",
            "steps_to_containment": None,
            "containment_status": "degraded",
        },
        "rollback_or_compensation": {
            "status": "manual_review",
            "actions": ["Preserve journal and escalate to incident owner."],
        },
        "scorecard": {
            "scope_validation": "review",
            "unsafe_action_executed": False,
            "lineage_complete": False,
            "kill_path_ready": False,
            "rollback_ready": False,
            "residual_exposure": "unknown",
        },
        "pipeline_status": "degraded",
        "failure_stage": stage,
        "failure_reason": reason,
    }


def run_pipeline(
    payload: dict[str, object],
    mode: str,
    model: str,
    base_url: str,
) -> dict[str, object]:
    workflow_id = _string(payload, "workflow_id") or datetime.now(timezone.utc).strftime("drill-%Y%m%d-%H%M%S")
    scenario = _string(payload, "scenario", "agent-incident-drill") or "agent-incident-drill"
    incident_text = _string(payload, "incident_text")
    customer_tier = _string(payload, "customer_tier", "standard") or "standard"
    action_description = _string(payload, "action_description")
    permissions_requested = _string_list(payload, "permissions_requested")
    reversibility_plan = _string(payload, "reversibility_plan")
    scope_boundary = _string(payload, "scope_boundary")
    service_name = _string(payload, "service_name", "agent-workflow") or "agent-workflow"
    dependencies = _string_list(payload, "dependencies")
    resource_limits = _object(payload, "resource_limits")
    kill_path_capabilities = _object(payload, "kill_path_capabilities")
    last_tested = _string(payload, "last_tested")
    rollback_plan = _string(payload, "rollback_plan") or reversibility_plan

    if not incident_text:
        return _degraded_output(workflow_id, scenario, "input", "incident_text is required")
    if not action_description:
        return _degraded_output(workflow_id, scenario, "input", "action_description is required")
    if not permissions_requested:
        return _degraded_output(workflow_id, scenario, "input", "permissions_requested is required")

    event_journal: list[dict[str, object]] = [
        _event(1, "incident-opened", "recorded", f"Scenario {scenario} opened for {customer_tier} customer."),
    ]

    try:
        route = run_agent(
            agent="workflow-ops.router-agent",
            payload={"task": incident_text, "available_agents": []},
            mode=mode,
            model=model,
            base_url=base_url,
        )
        event_journal.append(
            _event(2, "route", "recorded", f"Routed to {route.get('target_agent')} at {route.get('priority')}.")
        )

        triage = run_agent(
            agent="support-ops.triage-agent",
            payload={"text": incident_text, "customer_tier": customer_tier},
            mode=mode,
            model=model,
            base_url=base_url,
        )
        event_journal.append(
            _event(3, "triage", "recorded", f"Triage classified {triage.get('category')} at {triage.get('priority')}.")
        )

        governance = run_agent(
            agent="control-ops.scope-validator-agent",
            payload={
                "action_description": action_description,
                "permissions_requested": permissions_requested,
                "reversibility_plan": reversibility_plan,
                "scope_boundary": scope_boundary,
            },
            mode=mode,
            model=model,
            base_url=base_url,
        )
        event_journal.append(
            _event(4, "scope-validation", str(governance["verdict"]), "; ".join(governance["findings"][:2]))
        )

        pipeline_status, target_status, checkpoint_status = governance_pipeline_status(str(governance["verdict"]))
        unsafe_action_executed = target_status == "executed"
        if unsafe_action_executed:
            action_result = "target action executed after scope validation"
            event_journal.append(_event(5, "target-action", "executed", action_result))
        else:
            action_result = f"target action skipped: {target_status}"
            event_journal.append(_event(5, "target-action", "skipped", action_result))

        lineage = run_agent(
            agent="control-ops.lineage-recorder-agent",
            payload={
                "trigger": incident_text,
                "knowledge": f"action={action_description}; permissions={permissions_requested}; scope={scope_boundary}",
                "rules_applied": [
                    f"scope-verdict:{governance['verdict']}",
                    f"risk:{governance['risk_level']}",
                    f"target-status:{target_status}",
                ],
                "alternatives_considered": ["execute-action", "route-to-review", "block-action"],
                "action_taken": action_result,
            },
            mode=mode,
            model=model,
            base_url=base_url,
        )
        event_journal.append(
            _event(6, "lineage", str(lineage["integrity_check"]), f"Lineage record {lineage['lineage_id']} written.")
        )

        blast_radius = run_agent(
            agent="control-ops.blast-radius-assessor-agent",
            payload={
                "service_name": service_name,
                "permissions": permissions_requested,
                "dependencies": dependencies,
                "resource_limits": resource_limits,
            },
            mode=mode,
            model=model,
            base_url=base_url,
        )
        event_journal.append(
            _event(7, "blast-radius", str(blast_radius["max_damage_potential"]), "; ".join(blast_radius["findings"][:2]))
        )

        kill_path = run_agent(
            agent="control-ops.kill-path-auditor-agent",
            payload={
                "system_name": service_name,
                "capabilities": kill_path_capabilities,
                "last_tested": last_tested,
            },
            mode=mode,
            model=model,
            base_url=base_url,
        )
        event_journal.append(
            _event(8, "kill-path", str(kill_path["escalation_readiness"]), f"Coverage {kill_path['coverage_score']}/4.")
        )

        checkpoint = run_agent(
            agent="workflow-ops.checkpoint-agent",
            payload={
                "workflow_id": workflow_id,
                "stage": "incident-drill",
                "status": checkpoint_status,
                "notes": f"Governance {governance['verdict']}; target {target_status}; kill path {kill_path['escalation_readiness']}",
            },
            mode=mode,
            model=model,
            base_url=base_url,
        )
        event_journal.append(
            _event(9, "checkpoint", "recorded", str(checkpoint["summary"]))
        )
    except ValidationError as exc:
        return _degraded_output(workflow_id, scenario, "agent-run", str(exc))

    resilience_verdict = resilience_verdict_from_scores(
        int(blast_radius["risk_score"]),
        int(kill_path["coverage_score"]),
    )
    rollback_ready = bool(rollback_plan)
    rollback_or_compensation = {
        "status": "ready" if rollback_ready else "missing",
        "actions": [
            rollback_plan,
            "Preserve event journal and lineage record for incident review.",
        ] if rollback_ready else ["Define rollback or compensation before repeating this drill."],
    }
    if rollback_ready:
        event_journal.append(_event(10, "rollback", "ready", rollback_plan))
    else:
        event_journal.append(_event(10, "rollback", "missing", "No rollback or compensation plan provided."))

    contained = not unsafe_action_executed and str(kill_path["escalation_readiness"]) in {"ready", "partial"}
    containment_timing = {
        "detected_at_step": "scope-validation",
        "contained_at_step": "target-action" if not unsafe_action_executed else "kill-path",
        "steps_to_containment": 1 if not unsafe_action_executed else 4,
        "containment_status": "contained" if contained else "exposed",
    }

    lineage_query = {
        "query": "which actions were influenced by the triggering incident text?",
        "matched_lineage_ids": [lineage["lineage_id"]],
        "influenced_actions": [lineage["record"]["action_taken"]],
    }
    scorecard = {
        "scope_validation": governance["verdict"],
        "unsafe_action_executed": unsafe_action_executed,
        "lineage_complete": lineage["integrity_check"] == "complete",
        "kill_path_ready": kill_path["escalation_readiness"] == "ready",
        "rollback_ready": rollback_ready,
        "residual_exposure": "contained" if contained else "review_required",
    }

    return {
        "workflow_id": workflow_id,
        "scenario": scenario,
        "event_journal": event_journal,
        "route": route,
        "triage": triage,
        "governance": governance,
        "resilience": {
            "resilience_verdict": resilience_verdict,
            "blast_radius": blast_radius,
            "kill_path": kill_path,
        },
        "lineage_query": lineage_query,
        "containment_timing": containment_timing,
        "rollback_or_compensation": rollback_or_compensation,
        "checkpoint": checkpoint,
        "scorecard": scorecard,
        "pipeline_status": pipeline_status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the agent incident drill scenario")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument(
        "--mode",
        choices=["deterministic", "llm"],
        default=os.getenv("AGENT_MODE", "deterministic"),
        help="Execution mode",
    )
    parser.add_argument("--model", default=os.getenv("LLM_MODEL", "llama3.2:3b"), help="LLM model")
    parser.add_argument(
        "--base-url",
        default=os.getenv("LLM_BASE_URL", "http://localhost:11434"),
        help="LLM base URL",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty print output")
    args = parser.parse_args()

    path = Path(args.input)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        result = run_pipeline(payload, args.mode, args.model, args.base_url)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
