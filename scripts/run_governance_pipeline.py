#!/usr/bin/env python3
"""Run control-ops governance pipeline: scope-validator -> target agent -> lineage-recorder -> checkpoint."""

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


def _degraded_output(stage: str, reason: str, workflow_id: str) -> dict[str, object]:
    reason_lower = reason.lower()
    block_code = "unknown"
    if "must be" in reason_lower or "missing" in reason_lower:
        block_code = "validation_error"
    elif "timeout" in reason_lower:
        block_code = "timeout"
    elif "policy" in reason_lower:
        block_code = "policy_block"
    return {
        "workflow_id": workflow_id,
        "scope_validation": {
            "verdict": "review",
            "findings": ["Pipeline degraded; manual governance review required."],
            "risk_level": "high",
        },
        "target_output": {
            "status": "degraded",
            "reason": "manual review required",
        },
        "lineage": {
            "lineage_id": "degraded",
            "record": {},
            "integrity_check": "partial",
        },
        "checkpoint": {
            "checkpoint_id": f"{workflow_id}:governance:failed",
            "recorded": True,
            "summary": f"Governance pipeline degraded at stage {stage}: {reason}",
        },
        "pipeline_status": "degraded",
        "failure_stage": stage,
        "failure_reason": reason,
        "why_blocked": {
            "block_code": block_code,
            "block_stage": stage,
            "block_reasons": [reason],
            "required_actions": ["Run manual governance review before retry"],
            "can_retry": False,
        },
    }


def run_pipeline(
    payload: dict[str, object],
    mode: str,
    model: str,
    base_url: str,
    run_id: str = "",
    store: object | None = None,
) -> dict[str, object]:
    def _build_why_blocked(verdict: str, findings: list[str], stage: str) -> dict[str, object]:
        if verdict == "review":
            return {
                "block_code": "needs_review",
                "block_stage": stage,
                "block_reasons": findings[:3],
                "required_actions": [
                    "Collect missing governance evidence",
                    "Obtain explicit human approval",
                ],
                "can_retry": True,
            }
        if verdict == "fail":
            return {
                "block_code": "scope_violation",
                "block_stage": stage,
                "block_reasons": findings[:3],
                "required_actions": [
                    "Reduce requested permissions and scope",
                    "Add reversibility and traceability controls",
                ],
                "can_retry": False,
            }
        return {
            "block_code": "unknown",
            "block_stage": stage,
            "block_reasons": findings[:3],
            "required_actions": ["Manual governance review required"],
            "can_retry": False,
        }

    action_description = payload.get("action_description")
    permissions_requested = payload.get("permissions_requested")
    reversibility_plan = payload.get("reversibility_plan", "")
    scope_boundary = payload.get("scope_boundary", "")
    target_agent = payload.get("target_agent", "")
    target_payload = payload.get("target_payload", {})
    workflow_id = payload.get("workflow_id")

    if not isinstance(workflow_id, str) or not workflow_id.strip():
        workflow_id = datetime.now(timezone.utc).strftime("gov-%Y%m%d-%H%M%S")
    if not isinstance(target_payload, dict):
        target_payload = {}

    # Stage 1: Validate scope
    try:
        scope_validation = run_agent(
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
    except ValidationError as exc:
        return _degraded_output("scope-validator", str(exc), workflow_id)

    if store and run_id:
        save_stage(store, run_id, "scope-validator", scope_validation)

    # If scope validation does not pass, short-circuit with lineage and checkpoint.
    if scope_validation["verdict"] in {"review", "fail"}:
        pipeline_status, target_status, checkpoint_status = governance_pipeline_status(scope_validation["verdict"])
        short_circuit_reason = (
            "pending manual governance review"
            if scope_validation["verdict"] == "review"
            else "scope validation failed"
        )
        lineage_record = _record_lineage(
            workflow_id=workflow_id,
            trigger=f"governance gate for: {action_description}",
            knowledge=f"permissions: {permissions_requested}; scope: {scope_boundary}",
            rules_applied=[
                f"scope-verdict:{scope_validation['verdict']}",
                f"risk:{scope_validation['risk_level']}",
            ],
            alternatives_considered=["execute-target", "escalate-to-human"],
            action_taken=f"stopped before target execution: {short_circuit_reason}",
            mode=mode,
            model=model,
            base_url=base_url,
        )
        checkpoint = _record_checkpoint(
            workflow_id=workflow_id,
            stage="governance-gate",
            status=checkpoint_status,
            notes=f"Scope validation {scope_validation['verdict']}: {'; '.join(scope_validation['findings'][:2])}",
            mode=mode,
            model=model,
            base_url=base_url,
        )
        result = {
            "workflow_id": workflow_id,
            "scope_validation": scope_validation,
            "target_output": {"status": target_status, "reason": short_circuit_reason},
            "lineage": lineage_record,
            "checkpoint": checkpoint,
            "pipeline_status": pipeline_status,
            "why_blocked": _build_why_blocked(scope_validation["verdict"], scope_validation["findings"], "governance-gate"),
        }
        if store and run_id:
            save_stage(store, run_id, "lineage", lineage_record)
            save_stage(store, run_id, "checkpoint", checkpoint)
            save_result(store, run_id, result)
        return result

    # Stage 2: Execute target agent
    if not isinstance(target_agent, str) or not target_agent.strip():
        return _degraded_output("target-resolution", "no target_agent specified", workflow_id)

    try:
        target_output = run_agent(
            agent=target_agent,
            payload=target_payload,
            mode=mode,
            model=model,
            base_url=base_url,
        )
    except ValidationError as exc:
        out = _degraded_output("target", str(exc), workflow_id)
        out["scope_validation"] = scope_validation
        return out

    if store and run_id:
        save_stage(store, run_id, "target", target_output)

    # Stage 3: Record lineage
    lineage_record = _record_lineage(
        workflow_id=workflow_id,
        trigger=f"governance gate for: {action_description}",
        knowledge=f"permissions: {permissions_requested}; scope: {scope_boundary}",
        rules_applied=[f"scope-verdict:{scope_validation['verdict']}", f"risk:{scope_validation['risk_level']}"],
        alternatives_considered=["block-action", "escalate-to-human"],
        action_taken=f"executed {target_agent} after governance pass",
        mode=mode,
        model=model,
        base_url=base_url,
    )

    # Stage 4: Record checkpoint
    checkpoint = _record_checkpoint(
        workflow_id=workflow_id,
        stage="governance-complete",
        status="completed",
        notes=f"Scope verdict: {scope_validation['verdict']}; target: {target_agent}",
        mode=mode,
        model=model,
        base_url=base_url,
    )

    if store and run_id:
        save_stage(store, run_id, "lineage", lineage_record)
        save_stage(store, run_id, "checkpoint", checkpoint)

    result = {
        "workflow_id": workflow_id,
        "scope_validation": scope_validation,
        "target_output": target_output,
        "lineage": lineage_record,
        "checkpoint": checkpoint,
        "pipeline_status": "ok",
        "why_blocked": {
            "block_code": "none",
            "block_stage": "",
            "block_reasons": [],
            "required_actions": [],
            "can_retry": False,
        },
    }
    if store and run_id:
        save_result(store, run_id, result)
    return result


def _record_lineage(
    *,
    workflow_id: str,
    trigger: str,
    knowledge: str,
    rules_applied: list[str],
    alternatives_considered: list[str],
    action_taken: str,
    mode: str,
    model: str,
    base_url: str,
) -> dict[str, object]:
    try:
        return run_agent(
            agent="control-ops.lineage-recorder-agent",
            payload={
                "trigger": trigger,
                "knowledge": knowledge,
                "rules_applied": rules_applied,
                "alternatives_considered": alternatives_considered,
                "action_taken": action_taken,
            },
            mode=mode,
            model=model,
            base_url=base_url,
        )
    except ValidationError:
        return {"lineage_id": "degraded", "record": {}, "integrity_check": "partial"}


def _record_checkpoint(
    *,
    workflow_id: str,
    stage: str,
    status: str,
    notes: str,
    mode: str,
    model: str,
    base_url: str,
) -> dict[str, object]:
    try:
        return run_agent(
            agent="workflow-ops.checkpoint-agent",
            payload={
                "workflow_id": workflow_id,
                "stage": stage,
                "status": status,
                "notes": notes,
            },
            mode=mode,
            model=model,
            base_url=base_url,
        )
    except ValidationError:
        return {
            "checkpoint_id": f"{workflow_id}:{stage}:{status}",
            "recorded": True,
            "summary": f"Fallback checkpoint for {workflow_id} at {stage}",
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run governance pipeline: scope-validator -> target -> lineage-recorder -> checkpoint"
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
            run_id = datetime.now(timezone.utc).strftime("gov-%Y%m%d-%H%M%S")

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
