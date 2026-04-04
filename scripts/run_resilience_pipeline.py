#!/usr/bin/env python3
"""Run control-ops resilience pipeline: blast-radius-assessor -> kill-path-auditor."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from local_agents import ValidationError, run_agent
from local_agents.control_ops import resilience_verdict_from_scores
from local_agents.state import connect as connect_state, save_stage, save_result


def _degraded_output(stage: str, reason: str) -> dict[str, object]:
    return {
        "blast_radius": {
            "risk_score": 50,
            "max_damage_potential": "medium",
            "detection_latency": "moderate",
            "containment_time": "moderate",
            "findings": ["Pipeline degraded; manual assessment required."],
            "recommended_controls": [
                "Conduct manual blast radius review",
                "Verify resource limits are in place",
                "Schedule kill path audit separately",
            ],
        },
        "kill_path": {
            "coverage_score": 0,
            "gaps": ["all levels: assessment unavailable due to pipeline degradation"],
            "escalation_readiness": "unprepared",
            "recommended_actions": [
                "Complete manual kill path audit",
                "Document all four shutdown levels",
                "Schedule kill path drill",
            ],
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
    run_id: str = "",
    store: object | None = None,
) -> dict[str, object]:
    service_name = payload.get("service_name")
    permissions = payload.get("permissions")
    dependencies = payload.get("dependencies", [])
    resource_limits = payload.get("resource_limits") or {}
    capabilities = payload.get("capabilities") or {}
    last_tested = payload.get("last_tested", "")

    # Stage 1: Assess blast radius
    try:
        blast_radius = run_agent(
            agent="control-ops.blast-radius-assessor-agent",
            payload={
                "service_name": service_name,
                "permissions": permissions,
                "dependencies": dependencies,
                "resource_limits": resource_limits,
            },
            mode=mode,
            model=model,
            base_url=base_url,
        )
    except ValidationError as exc:
        return _degraded_output("blast-radius-assessor", str(exc))

    if store and run_id:
        save_stage(store, run_id, "blast-radius", blast_radius)

    # Stage 2: Audit kill path (using same system_name)
    try:
        kill_path = run_agent(
            agent="control-ops.kill-path-auditor-agent",
            payload={
                "system_name": service_name,
                "capabilities": capabilities,
                "last_tested": last_tested,
            },
            mode=mode,
            model=model,
            base_url=base_url,
        )
    except ValidationError as exc:
        out = _degraded_output("kill-path-auditor", str(exc))
        out["blast_radius"] = blast_radius
        return out

    # Compute combined resilience assessment from the shared control-ops matrix.
    resilience_verdict = resilience_verdict_from_scores(
        blast_radius["risk_score"],
        kill_path["coverage_score"],
    )

    if store and run_id:
        save_stage(store, run_id, "kill-path", kill_path)

    result = {
        "blast_radius": blast_radius,
        "kill_path": kill_path,
        "resilience_verdict": resilience_verdict,
        "pipeline_status": "ok",
    }
    if store and run_id:
        save_result(store, run_id, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run resilience pipeline: blast-radius-assessor -> kill-path-auditor"
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
            from datetime import datetime, timezone
            run_id = datetime.now(timezone.utc).strftime("resilience-%Y%m%d-%H%M%S")

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
