#!/usr/bin/env python3
"""Run cross-domain incident pipeline:
   router -> triage -> test-case-generator -> synthesis -> scope-validator -> checkpoint
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from local_agents import ValidationError, run_agent
from local_agents.control_ops import governance_pipeline_status
from local_agents.state import connect as connect_state, save_stage, save_result


def _degraded_output(stage: str, reason: str, workflow_id: str, **prior: object) -> dict[str, object]:
    result: dict[str, object] = {
        "workflow_id": workflow_id,
        "route": prior.get("route", {}),
        "triage": prior.get("triage", {}),
        "qa": prior.get("qa", {}),
        "synthesis": prior.get("synthesis", {}),
        "governance": prior.get("governance", {
            "verdict": "review",
            "findings": ["Pipeline degraded; manual governance review required."],
            "risk_level": "high",
        }),
        "checkpoint": {
            "checkpoint_id": f"{workflow_id}:incident:failed",
            "recorded": True,
            "summary": f"Incident pipeline degraded at stage {stage}: {reason}",
        },
        "pipeline_status": "degraded",
        "failure_stage": stage,
        "failure_reason": reason,
    }
    return result


def run_pipeline(
    payload: dict[str, object],
    mode: str,
    model: str,
    base_url: str,
    run_id: str = "",
    store: object | None = None,
) -> dict[str, object]:
    incident_text = payload.get("incident_text")
    customer_tier = payload.get("customer_tier", "free")
    feature_area = payload.get("feature_area", "")
    acceptance_criteria = payload.get("acceptance_criteria", [])
    action_description = payload.get("action_description", "")
    permissions_requested = payload.get("permissions_requested", [])
    reversibility_plan = payload.get("reversibility_plan", "")
    scope_boundary = payload.get("scope_boundary", "")
    workflow_id = payload.get("workflow_id")

    if not isinstance(workflow_id, str) or not workflow_id.strip():
        workflow_id = datetime.now(timezone.utc).strftime("incident-%Y%m%d-%H%M%S")
    if not isinstance(acceptance_criteria, list):
        acceptance_criteria = []
    if not isinstance(permissions_requested, list):
        permissions_requested = []

    # ── Stage 1: Route ─────────────────────────────────────────────
    try:
        route = run_agent(
            agent="workflow-ops.router-agent",
            payload={
                "task": incident_text,
                "available_agents": [],
            },
            mode=mode, model=model, base_url=base_url,
        )
    except ValidationError as exc:
        return _degraded_output("router", str(exc), workflow_id)

    if store and run_id:
        save_stage(store, run_id, "router", route)

    # ── Stage 2: Triage ────────────────────────────────────────────
    try:
        triage = run_agent(
            agent="support-ops.triage-agent",
            payload={
                "text": incident_text,
                "customer_tier": customer_tier,
            },
            mode=mode, model=model, base_url=base_url,
        )
    except ValidationError as exc:
        return _degraded_output("triage", str(exc), workflow_id, route=route)

    if store and run_id:
        save_stage(store, run_id, "triage", triage)

    # ── Stage 3: QA ───────────────────────────────────────────────
    qa_feature = feature_area if isinstance(feature_area, str) and feature_area.strip() else str(incident_text or "incident area")
    try:
        qa = run_agent(
            agent="qa-ops.test-case-generator-agent",
            payload={
                "feature": qa_feature,
                "acceptance_criteria": acceptance_criteria,
            },
            mode=mode, model=model, base_url=base_url,
        )
    except ValidationError as exc:
        return _degraded_output("qa", str(exc), workflow_id, route=route, triage=triage)

    if store and run_id:
        save_stage(store, run_id, "qa", qa)

    # ── Stage 4: Synthesis ─────────────────────────────────────────
    notes = [
        f"Route: {route.get('target_agent', 'unknown')} at {route.get('priority', 'p4')}",
        f"Triage: {triage.get('category', 'other')} / {triage.get('priority', 'p4')} — {triage.get('next_action', '')}",
        f"QA: {len(qa.get('test_cases', []))} test cases generated, risk focus {qa.get('risk_focus', 'medium')}",
    ]
    try:
        synthesis = run_agent(
            agent="research-ops.synthesis-agent",
            payload={
                "notes": notes,
                "audience": "engineering",
                "output_format": "brief",
            },
            mode=mode, model=model, base_url=base_url,
        )
    except ValidationError as exc:
        return _degraded_output("synthesis", str(exc), workflow_id, route=route, triage=triage, qa=qa)

    if store and run_id:
        save_stage(store, run_id, "synthesis", synthesis)

    # ── Stage 5: Governance ────────────────────────────────────────
    gov_action = action_description if isinstance(action_description, str) and action_description.strip() else f"incident response for {triage.get('category', 'unknown')}"
    gov_perms = permissions_requested if permissions_requested else ["incident-response"]
    try:
        governance = run_agent(
            agent="control-ops.scope-validator-agent",
            payload={
                "action_description": gov_action,
                "permissions_requested": gov_perms,
                "reversibility_plan": reversibility_plan,
                "scope_boundary": scope_boundary,
            },
            mode=mode, model=model, base_url=base_url,
        )
    except ValidationError as exc:
        return _degraded_output("governance", str(exc), workflow_id, route=route, triage=triage, qa=qa, synthesis=synthesis)

    if store and run_id:
        save_stage(store, run_id, "governance", governance)

    # ── Stage 6: Checkpoint ────────────────────────────────────────
    pipeline_status, _, checkpoint_status = governance_pipeline_status(governance.get("verdict", "review"))
    checkpoint_notes = (
        f"Route: {route.get('target_agent')}; "
        f"Triage: {triage.get('priority')}/{triage.get('category')}; "
        f"QA: {len(qa.get('test_cases', []))} cases; "
        f"Governance: {governance.get('verdict')}"
    )
    try:
        checkpoint = run_agent(
            agent="workflow-ops.checkpoint-agent",
            payload={
                "workflow_id": workflow_id,
                "stage": "incident-response",
                "status": checkpoint_status,
                "notes": checkpoint_notes,
            },
            mode=mode, model=model, base_url=base_url,
        )
    except ValidationError:
        checkpoint = {
            "checkpoint_id": f"{workflow_id}:incident-response:{checkpoint_status}",
            "recorded": True,
            "summary": f"Fallback checkpoint for {workflow_id}",
        }

    if store and run_id:
        save_stage(store, run_id, "checkpoint", checkpoint)

    result: dict[str, object] = {
        "workflow_id": workflow_id,
        "route": route,
        "triage": triage,
        "qa": qa,
        "synthesis": synthesis,
        "governance": governance,
        "checkpoint": checkpoint,
        "pipeline_status": pipeline_status,
    }
    if store and run_id:
        save_result(store, run_id, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run cross-domain incident pipeline: router -> triage -> qa -> synthesis -> governance -> checkpoint"
    )
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
    parser.add_argument("--state", action="store_true", help="Persist pipeline state to Redis")
    parser.add_argument("--run-id", default="", help="Pipeline run ID for state persistence")
    args = parser.parse_args()

    store = None
    run_id = args.run_id
    if args.state:
        store = connect_state()
        if not run_id:
            run_id = datetime.now(timezone.utc).strftime("incident-%Y%m%d-%H%M%S")

    path = Path(args.input)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        result = run_pipeline(payload, args.mode, args.model, args.base_url, run_id=run_id, store=store)
    except FileNotFoundError:
        print(f"input file not found: {path}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"input file is not valid JSON: {exc}", file=sys.stderr)
        return 2
    except ValidationError as exc:
        print(f"validation error: {exc}", file=sys.stderr)
        return 2

    if args.pretty:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
