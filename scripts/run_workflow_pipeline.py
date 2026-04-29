#!/usr/bin/env python3
"""Run workflow-ops router -> target agent -> checkpoint pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from local_agents import ValidationError, run_agent
from local_agents.state import connect as connect_state, save_stage, save_result


def _default_target_payload(target_agent: str, task: object) -> dict[str, object]:
    if target_agent == "support-ops.triage-agent":
        return {"text": task, "customer_tier": "pro"}
    if target_agent == "qa-ops.test-case-generator-agent":
        return {"feature": task, "acceptance_criteria": []}
    if target_agent == "qa-ops.regression-triage-agent":
        return {"failure_summary": task, "changed_components": []}
    if target_agent == "research-ops.retrieval-agent":
        return {"query": task, "sources": [], "max_points": 4}
    if target_agent == "planner-executor.planner-agent":
        return {"goal": task, "constraints": []}
    if target_agent == "security-ops.agentic-security-scanner-agent":
        return {"target_path": "."}
    raise ValidationError(f"unsupported routed target agent: {target_agent}")


def _degraded_output(stage: str, reason: str, workflow_id: str) -> dict[str, object]:
    reason_lower = reason.lower()
    failure_code = "unknown"
    if "must be" in reason_lower or "validation" in reason_lower:
        failure_code = "validation_error"
    elif "missing prerequisite" in reason_lower:
        failure_code = "dependency_missing"
    elif "timeout" in reason_lower or "latency" in reason_lower:
        failure_code = "timeout"
    elif "policy" in reason_lower:
        failure_code = "policy_block"
    elif "unsupported routed target agent" in reason_lower:
        failure_code = "upstream_failure"
    return {
        "route": {
            "target_agent": "workflow-ops.checkpoint-agent",
            "priority": "p2",
            "rationale": "Pipeline degraded due to validation failure.",
        },
        "target_output": {
            "status": "degraded",
            "reason": "manual review required",
        },
        "checkpoint": {
            "checkpoint_id": f"{workflow_id}:pipeline:{stage}:failed",
            "recorded": True,
            "summary": f"Workflow pipeline degraded at stage {stage}: {reason}",
        },
        "pipeline_status": "degraded",
        "failure_stage": stage,
        "failure_reason": reason,
        "stage_timing": {},
        "failure_taxonomy": {
            "failure_class": failure_code,
            "stage": stage,
            "reason": reason,
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
    task = payload.get("task")
    available_agents = payload.get("available_agents", [])
    agent_payloads = payload.get("agent_payloads", {})
    workflow_id = payload.get("workflow_id")

    if not isinstance(workflow_id, str) or not workflow_id.strip():
        workflow_id = datetime.now(timezone.utc).strftime("wf-%Y%m%d-%H%M%S")
    if not isinstance(agent_payloads, dict):
        agent_payloads = {}
    stage_timing: dict[str, int] = {}

    stage_start = time.perf_counter()
    try:
        route = run_agent(
            agent="workflow-ops.router-agent",
            payload={"task": task, "available_agents": available_agents},
            mode=mode,
            model=model,
            base_url=base_url,
        )
    except ValidationError as exc:
        return _degraded_output("router", str(exc), workflow_id)
    stage_timing["router_ms"] = int((time.perf_counter() - stage_start) * 1000)

    if store and run_id:
        save_stage(store, run_id, "router", route)

    target_agent = route["target_agent"]
    custom_payload = agent_payloads.get(target_agent)
    if isinstance(custom_payload, dict):
        target_payload = custom_payload
    else:
        try:
            target_payload = _default_target_payload(target_agent, task)
        except ValidationError as exc:
            out = _degraded_output("route-resolution", str(exc), workflow_id)
            out["stage_timing"] = stage_timing
            return out

    stage_start = time.perf_counter()
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
        stage_timing["target_ms"] = int((time.perf_counter() - stage_start) * 1000)
        out["stage_timing"] = stage_timing
        return out
    stage_timing["target_ms"] = int((time.perf_counter() - stage_start) * 1000)

    if store and run_id:
        save_stage(store, run_id, "target", target_output)

    checkpoint_notes = f"Routed to {target_agent} with priority {route['priority']}"
    stage_start = time.perf_counter()
    try:
        checkpoint = run_agent(
            agent="workflow-ops.checkpoint-agent",
            payload={
                "workflow_id": workflow_id,
                "stage": "dispatch",
                "status": "completed",
                "notes": checkpoint_notes,
            },
            mode=mode,
            model=model,
            base_url=base_url,
        )
    except ValidationError as exc:
        out = _degraded_output("checkpoint", str(exc), workflow_id)
        out["route"] = route
        out["target_output"] = target_output
        stage_timing["checkpoint_ms"] = int((time.perf_counter() - stage_start) * 1000)
        out["stage_timing"] = stage_timing
        return out
    stage_timing["checkpoint_ms"] = int((time.perf_counter() - stage_start) * 1000)

    if store and run_id:
        save_stage(store, run_id, "checkpoint", checkpoint)

    result = {
        "workflow_id": workflow_id,
        "route": route,
        "target_output": target_output,
        "checkpoint": checkpoint,
        "pipeline_status": "ok",
        "stage_timing": stage_timing,
        "failure_taxonomy": {
            "failure_class": "none",
            "stage": "",
            "reason": "",
        },
    }
    if store and run_id:
        save_result(store, run_id, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run workflow router->target->checkpoint pipeline")
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
            run_id = datetime.now(timezone.utc).strftime("workflow-%Y%m%d-%H%M%S")

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
