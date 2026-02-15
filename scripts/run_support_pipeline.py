#!/usr/bin/env python3
"""Run support-ops triage -> reply drafting pipeline."""

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


def run_pipeline(payload: dict[str, object], mode: str, model: str, base_url: str) -> dict[str, object]:
    text = payload.get("text")
    customer_tier = payload.get("customer_tier", "free")
    customer_name = payload.get("customer_name")

    triage = run_agent(
        agent="support-ops.triage-agent",
        payload={"text": text, "customer_tier": customer_tier},
        mode=mode,
        model=model,
        base_url=base_url,
    )
    draft = run_agent(
        agent="support-ops.reply-drafter-agent",
        payload={
            "customer_name": customer_name,
            "priority": triage["priority"],
            "category": triage["category"],
            "issue_summary": text,
        },
        mode=mode,
        model=model,
        base_url=base_url,
    )

    return {"triage": triage, "draft": draft}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run support triage->reply pipeline")
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
