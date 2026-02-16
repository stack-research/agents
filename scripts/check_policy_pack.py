#!/usr/bin/env python3
"""Validate runtime mode against policy pack environment baselines."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def evaluate_runtime_policy(policy: dict[str, Any], env_name: str, mode: str) -> tuple[bool, str]:
    environments = policy.get("environments")
    if not isinstance(environments, dict):
        return False, "policy missing environments map"

    env = environments.get(env_name)
    if not isinstance(env, dict):
        return False, f"unknown environment: {env_name}"

    llm_mode_allowed = env.get("llm_mode_allowed")
    if not isinstance(llm_mode_allowed, bool):
        return False, f"environment {env_name} has invalid llm_mode_allowed value"

    normalized_mode = mode.strip().lower()
    if normalized_mode not in {"deterministic", "llm"}:
        return False, f"unsupported mode: {mode}"

    if normalized_mode == "llm" and not llm_mode_allowed:
        return False, f"policy violation: llm mode is not allowed in {env_name}"

    return True, f"policy check passed for env={env_name}, mode={normalized_mode}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check runtime settings against ASI policy pack")
    parser.add_argument("--env", default=os.getenv("POLICY_ENV", "dev"), help="Environment (dev|staging|prod)")
    parser.add_argument(
        "--mode",
        default=os.getenv("AGENT_MODE", "deterministic"),
        help="Runtime mode to validate (deterministic|llm)",
    )
    parser.add_argument(
        "--policy-file",
        default=str(ROOT / "policy" / "asi-control-baselines.json"),
        help="Path to policy pack JSON file",
    )
    args = parser.parse_args()

    policy_path = Path(args.policy_file)
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"policy file not found: {policy_path}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"policy file is not valid JSON: {exc}", file=sys.stderr)
        return 2

    ok, message = evaluate_runtime_policy(policy, args.env, args.mode)
    if ok:
        print(message)
        return 0

    print(message, file=sys.stderr)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
