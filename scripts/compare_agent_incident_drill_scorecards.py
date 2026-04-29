#!/usr/bin/env python3
"""Compare scorecard sections from two agent incident drill JSON outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def extract_meta(out: dict[str, Any]) -> dict[str, Any]:
    return {
        "workflow_id": out.get("workflow_id"),
        "scenario": out.get("scenario"),
        "pipeline_status": out.get("pipeline_status"),
    }


def diff_drill_scorecards(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    b_sc = baseline.get("scorecard")
    c_sc = current.get("scorecard")
    if not isinstance(b_sc, dict):
        raise ValueError("baseline output missing scorecard object")
    if not isinstance(c_sc, dict):
        raise ValueError("current output missing scorecard object")

    keys = sorted(set(b_sc) | set(c_sc))
    scorecard_delta: dict[str, dict[str, Any]] = {}
    for key in keys:
        bv = b_sc.get(key)
        cv = c_sc.get(key)
        scorecard_delta[key] = {
            "baseline": bv,
            "current": cv,
            "changed": bv != cv,
        }

    return {
        "baseline": extract_meta(baseline),
        "current": extract_meta(current),
        "scorecard_delta": scorecard_delta,
        "any_scorecard_change": any(scorecard_delta[k]["changed"] for k in scorecard_delta),
    }


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be a JSON object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare scorecard fields between two agent incident drill output JSON files",
    )
    parser.add_argument("--baseline", required=True, help="Path to first drill output JSON")
    parser.add_argument("--current", required=True, help="Path to second drill output JSON")
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON")
    args = parser.parse_args()

    base_path = Path(args.baseline)
    cur_path = Path(args.current)
    try:
        result = diff_drill_scorecards(_load(base_path), _load(cur_path))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
