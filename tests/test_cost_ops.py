from __future__ import annotations

import json
import unittest
from pathlib import Path

from local_agents.core import ValidationError
from local_agents.engine import (
    run_agent,
    run_budget_guardrail_agent,
    run_cost_attribution_agent,
    run_pipeline_optimizer_agent,
    run_router_agent,
)


class CostOpsTests(unittest.TestCase):
    def test_cost_ops_flow(self) -> None:
        attr = run_cost_attribution_agent(
            {
                "run_id": "r1",
                "stages": [
                    {"stage_name": "a", "tokens_in": 1000, "tokens_out": 500, "runtime_ms": 2000},
                    {"stage_name": "b", "tokens_in": 2000, "tokens_out": 1000, "runtime_ms": 3000},
                ],
            }
        )
        self.assertGreater(attr["total_cost_usd"], 0)
        guard = run_budget_guardrail_agent(
            {
                "run_id": "r1",
                "attribution": attr,
                "budget_limits": {"run_limit_usd": 0.001, "warning_ratio": 0.8, "stage_limit_usd": 0.001},
            }
        )
        self.assertIn(guard["budget_status"], {"within", "warning", "breach"})
        opt = run_pipeline_optimizer_agent({"run_id": "r1", "attribution": attr, "guardrails": guard})
        self.assertGreaterEqual(len(opt["optimization_suggestions"]), 1)

    def test_negative_metrics_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            run_cost_attribution_agent(
                {"run_id": "r", "stages": [{"stage_name": "x", "tokens_in": -1, "tokens_out": 0, "runtime_ms": 1}]}
            )

    def test_aliases(self) -> None:
        root = Path(__file__).resolve().parents[1]
        mapping = (
            ("cost-ops.cost-attribution-agent", "catalog/projects/cost-ops/agents/cost-attribution-agent/examples/example-input.json"),
            ("budget-guardrail-agent", "catalog/projects/cost-ops/agents/budget-guardrail-agent/examples/example-input.json"),
            ("pipeline-optimizer-agent", "catalog/projects/cost-ops/agents/pipeline-optimizer-agent/examples/example-input.json"),
        )
        for agent, rel in mapping:
            payload = json.loads((root / rel).read_text(encoding="utf-8"))
            out = run_agent(agent=agent, payload=payload)
            self.assertIsInstance(out, dict)

    def test_router_targets(self) -> None:
        self.assertEqual(
            run_router_agent({"task": "Need a token cost breakdown for this run", "available_agents": []})["target_agent"],
            "cost-ops.cost-attribution-agent",
        )


if __name__ == "__main__":
    unittest.main()
