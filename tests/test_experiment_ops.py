from __future__ import annotations

import json
import unittest
from pathlib import Path

from local_agents.core import ValidationError
from local_agents.engine import (
    run_agent,
    run_experiment_plan_agent,
    run_hypothesis_registration_agent,
    run_result_adjudication_agent,
    run_router_agent,
)


class ExperimentOpsTests(unittest.TestCase):
    def test_hypothesis_registration_registered(self) -> None:
        out = run_hypothesis_registration_agent(
            {
                "hypothesis_statement": "Lowering cache TTL reduces p99 read latency for the catalog API.",
                "experiment_domain": "perf-cache",
            }
        )
        self.assertIn(out["registration_status"], {"registered", "needs_clarification"})
        self.assertTrue(out["hypothesis_id"])
        self.assertTrue(out["normalized_statement"])
        self.assertIsInstance(out["ambiguities"], list)
        self.assertTrue(out["registration_notes"])

    def test_hypothesis_registration_needs_clarification(self) -> None:
        out = run_hypothesis_registration_agent({"hypothesis_statement": "Maybe it helps sometimes."})
        self.assertEqual(out["registration_status"], "needs_clarification")
        self.assertTrue(out["ambiguities"])

    def test_hypothesis_registration_requires_statement(self) -> None:
        with self.assertRaises(ValidationError):
            run_hypothesis_registration_agent({"hypothesis_statement": "  "})

    def test_experiment_plan_happy_path(self) -> None:
        out = run_experiment_plan_agent(
            {
                "hypothesis_statement": "Trust badges increase checkout conversion for new users.",
                "constraints": {"max_variants": 4, "risk_tolerance": "low"},
            }
        )
        self.assertTrue(out["experiment_design_id"])
        self.assertGreaterEqual(len(out["variants"]), 2)
        self.assertLessEqual(len(out["variants"]), 6)
        self.assertTrue(out["success_metrics"])
        self.assertTrue(out["guardrails"])
        self.assertTrue(out["execution_risks"])
        self.assertTrue(out["next_steps"])

    def test_experiment_plan_requires_hypothesis(self) -> None:
        with self.assertRaises(ValidationError):
            run_experiment_plan_agent({"hypothesis_statement": ""})

    def test_result_adjudication_supports(self) -> None:
        out = run_result_adjudication_agent(
            {
                "hypothesis_statement": "One-click checkout increases conversion.",
                "observed_metrics": {"conversion_rate": 0.118},
                "primary_metric": "conversion_rate",
                "success_criteria": "conversion_rate above 0.10",
            }
        )
        self.assertEqual(out["adjudication_verdict"], "supports")
        self.assertIn(out["confidence"], {"low", "medium", "high"})
        self.assertGreaterEqual(len(out["caveats"]), 2)
        self.assertGreaterEqual(len(out["recommended_followups"]), 2)

    def test_result_adjudication_refutes(self) -> None:
        out = run_result_adjudication_agent(
            {
                "hypothesis_statement": "Feature improves task success rate.",
                "observed_metrics": {"task_success_rate": 0.71},
                "primary_metric": "task_success_rate",
                "success_criteria": "task_success_rate above 0.80",
            }
        )
        self.assertEqual(out["adjudication_verdict"], "refutes")

    def test_result_adjudication_requires_metrics(self) -> None:
        with self.assertRaises(ValidationError):
            run_result_adjudication_agent(
                {"hypothesis_statement": "x", "observed_metrics": {}}
            )

    def test_run_agent_aliases(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for agent_id, rel in (
            (
                "experiment-ops.hypothesis-registration-agent",
                "catalog/projects/experiment-ops/agents/hypothesis-registration-agent/examples/example-input.json",
            ),
            (
                "experiment-plan-agent",
                "catalog/projects/experiment-ops/agents/experiment-plan-agent/examples/example-input.json",
            ),
            (
                "result-adjudication-agent",
                "catalog/projects/experiment-ops/agents/result-adjudication-agent/examples/example-input.json",
            ),
        ):
            payload = json.loads((root / rel).read_text(encoding="utf-8"))
            out = run_agent(agent=agent_id, payload=payload)
            self.assertIsInstance(out, dict)
            self.assertGreater(len(out), 1)

    def test_router_routes_experiment_intents(self) -> None:
        hyp = run_router_agent(
            {"task": "Please register hypothesis for our checkout experiment", "available_agents": []}
        )
        self.assertEqual(hyp["target_agent"], "experiment-ops.hypothesis-registration-agent")
        plan = run_router_agent(
            {"task": "We need an experiment plan for the trust badge A/B test", "available_agents": []}
        )
        self.assertEqual(plan["target_agent"], "experiment-ops.experiment-plan-agent")
        adj = run_router_agent(
            {"task": "Adjudicate experiment results against our success criteria", "available_agents": []}
        )
        self.assertEqual(adj["target_agent"], "experiment-ops.result-adjudication-agent")


if __name__ == "__main__":
    unittest.main()
