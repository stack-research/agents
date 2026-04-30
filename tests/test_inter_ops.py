from __future__ import annotations

import json
import unittest
from pathlib import Path

from local_agents.core import ValidationError
from local_agents.engine import run_agent, run_router_agent, run_schema_compat_validator_agent


class InterOpsTests(unittest.TestCase):
    def test_schema_compat_warning_case(self) -> None:
        out = run_schema_compat_validator_agent(
            {
                "contract_name": "order.v2",
                "compat_mode": "backward",
                "producer_schema": {
                    "required": ["order_id"],
                    "properties": {"order_id": {"type": "string"}, "currency": {"type": "string"}},
                },
                "consumer_schema": {
                    "required": ["order_id"],
                    "properties": {
                        "order_id": {"type": "string"},
                        "currency": {"type": "string"},
                        "channel": {"type": "string"},
                    },
                },
            }
        )
        self.assertEqual(out["compatibility_status"], "compatible_with_warnings")
        self.assertEqual(out["breaking_changes"], [])
        self.assertGreaterEqual(len(out["non_breaking_changes"]), 1)

    def test_schema_compat_incompatible_required_missing(self) -> None:
        out = run_schema_compat_validator_agent(
            {
                "contract_name": "user.v1",
                "compat_mode": "backward",
                "producer_schema": {
                    "required": ["user_id", "email"],
                    "properties": {"user_id": {"type": "string"}, "email": {"type": "string"}},
                },
                "consumer_schema": {
                    "required": ["user_id"],
                    "properties": {"user_id": {"type": "string"}},
                },
            }
        )
        self.assertEqual(out["compatibility_status"], "incompatible")
        self.assertGreaterEqual(len(out["breaking_changes"]), 1)

    def test_schema_compat_invalid_mode(self) -> None:
        with self.assertRaises(ValidationError):
            run_schema_compat_validator_agent(
                {
                    "contract_name": "x",
                    "compat_mode": "invalid",
                    "producer_schema": {"required": [], "properties": {"a": {"type": "string"}}},
                    "consumer_schema": {"required": [], "properties": {"a": {"type": "string"}}},
                }
            )

    def test_run_agent_aliases(self) -> None:
        root = Path(__file__).resolve().parents[1]
        payload = json.loads(
            (
                root
                / "catalog/projects/inter-ops/agents/schema-compat-validator-agent/examples/example-input.json"
            ).read_text(encoding="utf-8")
        )
        for agent in ("inter-ops.schema-compat-validator-agent", "schema-compat-validator-agent"):
            out = run_agent(agent=agent, payload=payload)
            self.assertIn(out["compatibility_status"], {"compatible", "compatible_with_warnings", "incompatible"})

    def test_router_inter_ops_target(self) -> None:
        out = run_router_agent(
            {"task": "Run schema compatibility check between producer and consumer contracts", "available_agents": []}
        )
        self.assertEqual(out["target_agent"], "inter-ops.schema-compat-validator-agent")


if __name__ == "__main__":
    unittest.main()
