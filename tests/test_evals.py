"""Generic eval runner: discovers and validates all evals/cases.json fixtures."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from local_agents.engine import run_agent


ROOT = Path(__file__).resolve().parents[1]
EVAL_SCHEMA = json.loads((ROOT / "schemas" / "eval-case.json").read_text())


def _resolve_field(obj: Any, path: str) -> Any:
    """Resolve a dot-separated field path against a nested object."""
    for part in path.split("."):
        if isinstance(obj, dict):
            obj = obj[part]
        elif isinstance(obj, list) and part.isdigit():
            obj = obj[int(part)]
        else:
            raise KeyError(f"cannot resolve '{part}' in {type(obj).__name__}")
    return obj


def _check_assertion(output: dict, assertion: dict) -> str | None:
    """Return an error message if the assertion fails, else None."""
    field = assertion["field"]
    op = assertion["op"]
    expected = assertion["value"]

    try:
        actual = _resolve_field(output, field)
    except (KeyError, IndexError, TypeError) as exc:
        return f"{field}: field not found ({exc})"

    if op == "eq":
        if actual != expected:
            return f"{field}: expected {expected!r}, got {actual!r}"

    elif op == "in":
        if actual not in expected:
            return f"{field}: {actual!r} not in {expected!r}"

    elif op == "type":
        type_map = {
            "string": str, "int": int, "float": float,
            "number": (int, float), "list": list, "dict": dict, "bool": bool,
        }
        expected_type = type_map.get(expected)
        if expected_type is None:
            return f"{field}: unknown type '{expected}'"
        if not isinstance(actual, expected_type):
            return f"{field}: expected type {expected}, got {type(actual).__name__}"

    elif op == "length":
        if len(actual) != expected:
            return f"{field}: expected length {expected}, got {len(actual)}"

    elif op == "min_length":
        if len(actual) < expected:
            return f"{field}: length {len(actual)} < min {expected}"

    elif op == "max_length":
        if len(actual) > expected:
            return f"{field}: length {len(actual)} > max {expected}"

    elif op == "contains":
        if isinstance(actual, str):
            if expected not in actual:
                return f"{field}: string does not contain {expected!r}"
        elif isinstance(actual, list):
            if expected not in actual:
                return f"{field}: list does not contain {expected!r}"
        else:
            return f"{field}: contains requires string or list, got {type(actual).__name__}"

    elif op == "matches":
        if not isinstance(actual, str):
            return f"{field}: matches requires string, got {type(actual).__name__}"
        if not re.search(expected, actual):
            return f"{field}: does not match pattern {expected!r}"

    elif op == "range":
        lo, hi = expected
        if not (lo <= actual <= hi):
            return f"{field}: {actual} not in range [{lo}, {hi}]"

    elif op == "has_keys":
        if not isinstance(actual, dict):
            return f"{field}: has_keys requires dict, got {type(actual).__name__}"
        missing = [k for k in expected if k not in actual]
        if missing:
            return f"{field}: missing keys {missing}"

    elif op == "max_words":
        if not isinstance(actual, str):
            return f"{field}: max_words requires string, got {type(actual).__name__}"
        word_count = len(actual.split())
        if word_count > expected:
            return f"{field}: {word_count} words > max {expected}"

    else:
        return f"{field}: unknown operator '{op}'"

    return None


def _discover_fixtures() -> list[tuple[Path, dict]]:
    """Find and load all evals/cases.json files in the catalog."""
    fixtures = []
    for path in sorted(ROOT.glob("catalog/projects/*/agents/*/evals/cases.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        fixtures.append((path, data))
    return fixtures


class EvalFixtureSchemaTests(unittest.TestCase):
    """Validate that all eval fixture files conform to the eval-case schema."""

    def test_all_fixtures_valid_schema(self) -> None:
        failures: list[str] = []
        for path, data in _discover_fixtures():
            try:
                jsonschema.validate(data, EVAL_SCHEMA)
            except jsonschema.ValidationError as exc:
                failures.append(f"{path.relative_to(ROOT)}: {exc.message}")
        if failures:
            self.fail("eval fixture schema violations:\n" + "\n".join(sorted(failures)))

    def test_fixture_agent_id_matches_directory(self) -> None:
        failures: list[str] = []
        for path, data in _discover_fixtures():
            parts = path.relative_to(ROOT / "catalog" / "projects").parts
            expected_id = f"{parts[0]}.{parts[2]}"
            if data["agent_id"] != expected_id:
                failures.append(
                    f"{path.relative_to(ROOT)}: agent_id {data['agent_id']!r} "
                    f"!= expected {expected_id!r}"
                )
        if failures:
            self.fail("agent_id mismatches:\n" + "\n".join(sorted(failures)))

    def test_case_ids_unique(self) -> None:
        failures: list[str] = []
        for path, data in _discover_fixtures():
            ids = [c["id"] for c in data["cases"]]
            dupes = [x for x in ids if ids.count(x) > 1]
            if dupes:
                failures.append(f"{path.relative_to(ROOT)}: duplicate case ids: {set(dupes)}")
        if failures:
            self.fail("duplicate case ids:\n" + "\n".join(sorted(failures)))


class EvalBenchmarkTests(unittest.TestCase):
    """Run every eval case against the deterministic engine and validate results."""

    def test_eval_cases(self) -> None:
        fixtures = _discover_fixtures()
        self.assertTrue(len(fixtures) > 0, "no eval fixtures found")

        failures: list[str] = []
        total = 0

        for path, data in fixtures:
            agent_id = data["agent_id"]
            for case in data["cases"]:
                total += 1
                case_label = f"{agent_id}::{case['id']}"

                try:
                    output = run_agent(agent_id, case["input"])
                except Exception as exc:
                    failures.append(f"{case_label}: agent raised {type(exc).__name__}: {exc}")
                    continue

                # Exact output match
                if "expected_output" in case:
                    if output != case["expected_output"]:
                        failures.append(
                            f"{case_label}: output mismatch\n"
                            f"  expected: {json.dumps(case['expected_output'], indent=2)}\n"
                            f"  actual:   {json.dumps(output, indent=2)}"
                        )

                # Assertion checks
                for assertion in case.get("assertions", []):
                    err = _check_assertion(output, assertion)
                    if err:
                        failures.append(f"{case_label}: {err}")

        if failures:
            header = f"{len(failures)} failure(s) across {total} eval cases"
            self.fail(f"{header}:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
