#!/usr/bin/env python3
"""Run workflow-ops router -> target agent -> checkpoint pipeline."""

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
    }


def run_pipeline(payload: dict[str, object], mode: str, model: str, base_url: str) -> dict[str, object]:
    task = payload.get("task")
    available_agents = payload.get("available_agents", [])
    agent_payloads = payload.get("agent_payloads", {})
    workflow_id = payload.get("workflow_id")

    if not isinstance(workflow_id, str) or not workflow_id.strip():
        workflow_id = datetime.now(timezone.utc).strftime("wf-%Y%m%d-%H%M%S")
    if not isinstance(agent_payloads, dict):
        agent_payloads = {}

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

    target_agent = route["target_agent"]
    custom_payload = agent_payloads.get(target_agent)
    if isinstance(custom_payload, dict):
        target_payload = custom_payload
    else:
        try:
            target_payload = _default_target_payload(target_agent, task)
        except ValidationError as exc:
            return _degraded_output("route-resolution", str(exc), workflow_id)

    try:
        target_output = run_agent(
            agent=target_agent,
            payload=target_payload,
            mode=mode,
            model=model,
            base_url=base_url,
        )
    except ValidationError as exc:
        return _degraded_output("target", str(exc), workflow_id)

    checkpoint_notes = f"Routed to {target_agent} with priority {route['priority']}"
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
        return out

    return {
        "workflow_id": workflow_id,
        "route": route,
        "target_output": target_output,
        "checkpoint": checkpoint,
        "pipeline_status": "ok",
    }


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
    args = parser.parse_args()

    path = Path(args.input)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        result = run_pipeline(payload, args.mode, args.model, args.base_url)
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
