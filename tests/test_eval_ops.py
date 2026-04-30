from __future__ import annotations

import json
import unittest
from pathlib import Path

from local_agents.core import ValidationError
from local_agents.engine import (
    run_agent,
    run_benchmark_curator_agent,
    run_quality_drift_reporter_agent,
    run_regression_score_agent,
    run_router_agent,
)


class EvalOpsTests(unittest.TestCase):
    def test_benchmark_curator_happy_path(self) -> None:
        out = run_benchmark_curator_agent(
            {
                "benchmark_name": "tool-use-v1",
                "target_capability": "structured_json",
                "candidate_cases": [
                    {"case_id": "a", "title": "One"},
                    {"case_id": "a", "title": "Dup"},
                    {"case_id": "b", "title": "Two"},
                    {"case_id": "c", "title": "Three"},
                    {"case_id": "d", "title": "Four"},
                    {"case_id": "e", "title": "Fifth adversarial"},
                ],
            }
        )
        self.assertIn(out["curation_verdict"], {"ready", "needs_expansion", "sparse"})
        self.assertTrue(out["included_cases"])
        self.assertTrue(out["excluded_duplicates"])
        self.assertTrue(1 <= len(out["coverage_gaps"]) <= 4)
        self.assertTrue(out["curated_suite_id"])

    def test_benchmark_curator_requires_cases(self) -> None:
        with self.assertRaises(ValidationError):
            run_benchmark_curator_agent({"benchmark_name": "x", "candidate_cases": []})

    def test_regression_score_detects_drop(self) -> None:
        out = run_regression_score_agent(
            {
                "baseline_scores": {"accuracy": 0.9},
                "current_scores": {"accuracy": 0.8},
                "regression_threshold_percent": 5.0,
            }
        )
        self.assertTrue(out["regression_flag"])
        self.assertIn(out["verdict"], {"warn", "fail"})
        self.assertTrue(out["metric_deltas"])
        self.assertTrue(2 <= len(out["findings"]) <= 4)

    def test_regression_score_requires_shared_keys(self) -> None:
        with self.assertRaises(ValidationError):
            run_regression_score_agent(
                {"baseline_scores": {"a": 1}, "current_scores": {"b": 1}, "regression_threshold_percent": 5.0}
            )

    def test_quality_drift_degrading(self) -> None:
        out = run_quality_drift_reporter_agent(
            {
                "metric_name": "task_success_rate",
                "windows": [
                    {"window_label": "w1", "score": 0.9},
                    {"window_label": "w2", "score": 0.88},
                    {"window_label": "w3", "score": 0.7},
                ],
            }
        )
        self.assertIn(out["drift_severity"], {"none", "low", "medium", "high"})
        self.assertEqual(out["trend"], "degrading")
        self.assertLessEqual(len(out["windows_flagged"]), 4)
        self.assertTrue(out["report_summary"])

    def test_quality_drift_requires_two_windows(self) -> None:
        with self.assertRaises(ValidationError):
            run_quality_drift_reporter_agent(
                {"metric_name": "m", "windows": [{"window_label": "a", "score": 1.0}]}
            )

    def test_run_agent_aliases(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for agent_id, rel in (
            ("eval-ops.benchmark-curator-agent", "catalog/projects/eval-ops/agents/benchmark-curator-agent/examples/example-input.json"),
            ("regression-score-agent", "catalog/projects/eval-ops/agents/regression-score-agent/examples/example-input.json"),
            ("quality-drift-reporter-agent", "catalog/projects/eval-ops/agents/quality-drift-reporter-agent/examples/example-input.json"),
        ):
            payload = json.loads((root / rel).read_text(encoding="utf-8"))
            out = run_agent(agent=agent_id, payload=payload)
            self.assertIsInstance(out, dict)
            self.assertGreater(len(out), 1)

    def test_router_routes_eval_intents(self) -> None:
        bench = run_router_agent(
            {"task": "Please curate benchmark suite for tool-use eval", "available_agents": []}
        )
        self.assertEqual(bench["target_agent"], "eval-ops.benchmark-curator-agent")
        score = run_router_agent(
            {"task": "We need regression score on eval metrics after the change", "available_agents": []}
        )
        self.assertEqual(score["target_agent"], "eval-ops.regression-score-agent")
        drift = run_router_agent(
            {"task": "Report metric drift for quality over the last month", "available_agents": []}
        )
        self.assertEqual(drift["target_agent"], "eval-ops.quality-drift-reporter-agent")


if __name__ == "__main__":
    unittest.main()
