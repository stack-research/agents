from __future__ import annotations

import json
import unittest
from pathlib import Path

from local_agents.core import ValidationError
from local_agents.engine import (
    run_agent,
    run_blast_pattern_cluster_agent,
    run_failure_library_agent,
    run_rollback_playbook_agent,
    run_router_agent,
)


class FailureOpsTests(unittest.TestCase):
    def test_pipeline_happy_path(self) -> None:
        lib = run_failure_library_agent(
            {
                "incident_id": "inc-a",
                "observations": [
                    {
                        "service": "auth-api",
                        "symptom": "login 503",
                        "trigger": "deploy",
                        "impact": "high",
                        "environment": "prod",
                        "timeline_hint": "starts after rollout",
                    }
                ],
            }
        )
        self.assertIn(lib["library_status"], {"complete", "partial"})
        self.assertGreaterEqual(len(lib["failure_modes"]), 1)

        cl = run_blast_pattern_cluster_agent({"incident_id": lib["incident_id"], "failure_modes": lib["failure_modes"]})
        self.assertGreaterEqual(len(cl["clusters"]), 1)
        self.assertIn(cl["clusters"][0]["blast_pattern"], {"localized", "tier", "cross-system", "global"})

        rb = run_rollback_playbook_agent({"incident_id": lib["incident_id"], "clusters": cl["clusters"]})
        self.assertIn(rb["rollback_class"], {"standard", "elevated", "critical"})
        self.assertGreaterEqual(len(rb["steps"]), 1)
        self.assertGreaterEqual(len(rb["verification_checks"]), 1)

    def test_failure_library_requires_observations(self) -> None:
        with self.assertRaises(ValidationError):
            run_failure_library_agent({"incident_id": "x", "observations": []})

    def test_cluster_requires_failure_mode_id(self) -> None:
        with self.assertRaises(ValidationError):
            run_blast_pattern_cluster_agent({"incident_id": "x", "failure_modes": [{"service": "a", "impact": "high"}]})

    def test_playbook_requires_clusters(self) -> None:
        with self.assertRaises(ValidationError):
            run_rollback_playbook_agent({"incident_id": "x", "clusters": []})

    def test_run_agent_aliases(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for agent_id, rel in (
            (
                "failure-ops.failure-library-agent",
                "catalog/projects/failure-ops/agents/failure-library-agent/examples/example-input.json",
            ),
            (
                "blast-pattern-cluster-agent",
                "catalog/projects/failure-ops/agents/blast-pattern-cluster-agent/examples/example-input.json",
            ),
            (
                "rollback-playbook-agent",
                "catalog/projects/failure-ops/agents/rollback-playbook-agent/examples/example-input.json",
            ),
        ):
            payload = json.loads((root / rel).read_text(encoding="utf-8"))
            out = run_agent(agent=agent_id, payload=payload)
            self.assertIsInstance(out, dict)
            self.assertGreater(len(out), 1)

    def test_router_failure_ops_targets(self) -> None:
        lib = run_router_agent({"task": "Build a failure mode library from telemetry observations", "available_agents": []})
        self.assertEqual(lib["target_agent"], "failure-ops.failure-library-agent")
        cl = run_router_agent({"task": "Cluster these modes into blast patterns", "available_agents": []})
        self.assertEqual(cl["target_agent"], "failure-ops.blast-pattern-cluster-agent")
        rb = run_router_agent({"task": "Generate rollback playbook steps with guards", "available_agents": []})
        self.assertEqual(rb["target_agent"], "failure-ops.rollback-playbook-agent")


if __name__ == "__main__":
    unittest.main()
