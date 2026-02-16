#!/usr/bin/env python3
"""Run planner-executor planner -> executor pipeline."""

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


def _degraded_output(stage: str, reason: str) -> dict[str, object]:
    return {
        "plan": {
            "plan_steps": [
                "Clarify objective and constraints with a human reviewer",
                "Create a minimal safe checklist and approval gate",
                "Execute approved steps and summarize the outcome",
            ],
            "risk_level": "medium",
        },
        "execution": {
            "status": "partial",
            "completed_steps": 1,
            "blocked_steps": 2,
            "summary": "Pipeline degraded due to validation failure. Work was escalated for manual review.",
        },
        "pipeline_status": "degraded",
        "failure_stage": stage,
        "failure_reason": reason,
    }


def run_pipeline(payload: dict[str, object], mode: str, model: str, base_url: str) -> dict[str, object]:
    goal = payload.get("goal")
    constraints = payload.get("constraints", [])
    context = payload.get("context", "")

    try:
        plan = run_agent(
            agent="planner-executor.planner-agent",
            payload={"goal": goal, "constraints": constraints},
            mode=mode,
            model=model,
            base_url=base_url,
        )
    except ValidationError as exc:
        return _degraded_output("planner", str(exc))

    try:
        execution = run_agent(
            agent="planner-executor.executor-agent",
            payload={"plan_steps": plan["plan_steps"], "context": context},
            mode=mode,
            model=model,
            base_url=base_url,
        )
    except ValidationError as exc:
        out = _degraded_output("executor", str(exc))
        out["plan"] = plan
        return out

    return {"plan": plan, "execution": execution, "pipeline_status": "ok"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run planner->executor pipeline")
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
