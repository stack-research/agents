#!/usr/bin/env python3
"""Run local catalog agents against a JSON payload."""

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local catalog agent")
    parser.add_argument("--agent", required=True, help="Agent name or id")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument(
        "--mode",
        choices=["deterministic", "llm"],
        default=os.getenv("AGENT_MODE", "deterministic"),
        help="Execution mode (default from AGENT_MODE or deterministic)",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL", "llama3.2:3b"),
        help="LLM model name for llm mode",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("LLM_BASE_URL", "http://localhost:11434"),
        help="LLM base URL for llm mode",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty print output")
    args = parser.parse_args()

    payload_path = Path(args.input)
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        result = run_agent(
            agent=args.agent,
            payload=payload,
            mode=args.mode,
            model=args.model,
            base_url=args.base_url,
        )
    except FileNotFoundError:
        print(f"input file not found: {payload_path}", file=sys.stderr)
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
