from __future__ import annotations

import json
import unittest
from pathlib import Path

from local_agents.core import ValidationError
from local_agents.engine import (
    run_agent,
    run_artifact_inventory_agent,
    run_bundle_manifest_agent,
    run_bundle_seal_agent,
    run_router_agent,
)


class ArtifactOpsTests(unittest.TestCase):
    def test_pipeline_happy_path(self) -> None:
        inv = run_artifact_inventory_agent(
            {
                "run_id": "run-abc",
                "artifacts": [
                    {"logical_path": "data/in.csv", "role": "input", "inline_text": "a,b"},
                    {
                        "logical_path": "out/summary.json",
                        "role": "output",
                        "content_sha256": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
                    },
                ],
            }
        )
        self.assertEqual(inv["inventory_status"], "complete")
        self.assertEqual(len(inv["artifacts"]), 2)

        man = run_bundle_manifest_agent({"run_id": inv["run_id"], "inventory": inv})
        self.assertEqual(len(man["entries"]), 2)
        self.assertEqual(len(man["bundle_root_sha256"]), 64)

        seal = run_bundle_seal_agent(
            {
                "run_id": inv["run_id"],
                "bundle_root_sha256": man["bundle_root_sha256"],
                "lineage_records": [{"lineage_id": "ln-1", "action_taken": "export"}],
            }
        )
        self.assertEqual(seal["seal_status"], "sealed")
        self.assertTrue(seal["bundle_id"])
        self.assertEqual(seal["bundle_root_sha256"], man["bundle_root_sha256"])

    def test_inventory_partial_without_digest(self) -> None:
        inv = run_artifact_inventory_agent(
            {
                "run_id": "run-partial",
                "artifacts": [{"logical_path": "x.bin", "role": "output"}],
            }
        )
        self.assertEqual(inv["inventory_status"], "partial")
        self.assertEqual(inv["artifacts"][0]["content_sha256"], "")

    def test_inventory_requires_artifacts(self) -> None:
        with self.assertRaises(ValidationError):
            run_artifact_inventory_agent({"run_id": "r", "artifacts": []})

    def test_inventory_invalid_role(self) -> None:
        with self.assertRaises(ValidationError):
            run_artifact_inventory_agent(
                {
                    "run_id": "r",
                    "artifacts": [{"logical_path": "f", "role": "unknown", "inline_text": "x"}],
                }
            )

    def test_manifest_invalid_digest_in_inventory(self) -> None:
        inv = {
            "run_id": "r1",
            "artifacts": [
                {
                    "artifact_id": "a1",
                    "logical_path": "f.txt",
                    "role": "input",
                    "content_sha256": "not-hex",
                }
            ],
        }
        with self.assertRaises(ValidationError):
            run_bundle_manifest_agent({"run_id": "r1", "inventory": inv})

    def test_seal_sealed_with_gaps_without_lineage(self) -> None:
        seal = run_bundle_seal_agent(
            {
                "run_id": "r2",
                "bundle_root_sha256": "e8c02838120e8dd0302c6cf68a57bcc34978355f6f839522eaf29fa8ec36604a",
            }
        )
        self.assertEqual(seal["seal_status"], "sealed_with_gaps")

    def test_run_agent_aliases(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for agent_id, rel in (
            (
                "artifact-ops.artifact-inventory-agent",
                "catalog/projects/artifact-ops/agents/artifact-inventory-agent/examples/example-input.json",
            ),
            (
                "bundle-manifest-agent",
                "catalog/projects/artifact-ops/agents/bundle-manifest-agent/examples/example-input.json",
            ),
            (
                "bundle-seal-agent",
                "catalog/projects/artifact-ops/agents/bundle-seal-agent/examples/example-input.json",
            ),
        ):
            payload = json.loads((root / rel).read_text(encoding="utf-8"))
            out = run_agent(agent=agent_id, payload=payload)
            self.assertIsInstance(out, dict)
            self.assertGreater(len(out), 1)

    def test_router_artifact_ops_vs_lineage(self) -> None:
        inv = run_router_agent(
            {"task": "Create a reproducible artifact bundle for our training run outputs", "available_agents": []}
        )
        self.assertEqual(inv["target_agent"], "artifact-ops.artifact-inventory-agent")
        man = run_router_agent(
            {"task": "We need a bundle manifest checksum before archival", "available_agents": []}
        )
        self.assertEqual(man["target_agent"], "artifact-ops.bundle-manifest-agent")
        seal = run_router_agent({"task": "Seal run artifacts for compliance", "available_agents": []})
        self.assertEqual(seal["target_agent"], "artifact-ops.bundle-seal-agent")
        lin = run_router_agent({"task": "Write a decision lineage record for the audit trail", "available_agents": []})
        self.assertEqual(lin["target_agent"], "control-ops.lineage-recorder-agent")


if __name__ == "__main__":
    unittest.main()
