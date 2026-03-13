from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from local_agents.engine import run_agent, run_agentic_security_scanner_agent
from local_agents.security_scanner import scan_repository_controls


class SecurityScannerTests(unittest.TestCase):
    def test_scanner_output_shape(self) -> None:
        out = run_agentic_security_scanner_agent({"target_path": "."})
        self.assertIn("summary", out)
        self.assertIn("risk_score", out)
        self.assertIn("findings", out)
        self.assertIsInstance(out["findings"], list)
        self.assertGreaterEqual(int(out["risk_score"]), 0)
        self.assertLessEqual(int(out["risk_score"]), 100)

    def test_scanner_alias_via_run_agent(self) -> None:
        out = run_agent(
            agent="security-ops.agentic-security-scanner-agent",
            payload={"target_path": "."},
        )
        self.assertIn("summary", out)

    def test_scanner_discovers_agents_via_glob(self) -> None:
        out = run_agentic_security_scanner_agent({"target_path": "."})
        self.assertIn("agents", out["summary"])
        # We have 25 agents in the catalog
        self.assertIn("findings", out)

    def test_scanner_custom_rules(self) -> None:
        """Scanner accepts a custom rules file and evaluates those rules."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create a minimal agent
            agent_dir = root / "my-agent"
            agent_dir.mkdir()
            (agent_dir / "agent.yaml").write_text("id: test.my-agent\n")
            (agent_dir / "README.md").write_text("This agent does things.\n")

            # Custom rules: check README contains "deploy"
            rules = {
                "agent_manifest": "agent.yaml",
                "agent_checks": [
                    {
                        "id": "CUSTOM-001",
                        "asi": "ASI01",
                        "severity": "low",
                        "title": "README missing deploy instructions",
                        "file": "README.md",
                        "contains": "deploy",
                        "recommendation": "Add deploy instructions.",
                    }
                ],
                "repo_checks": [],
            }
            rules_path = root / "rules.json"
            rules_path.write_text(json.dumps(rules))

            out = scan_repository_controls(str(root), rules_path=str(rules_path))
            self.assertEqual(len(out["findings"]), 1)
            self.assertEqual(out["findings"][0]["id"], "CUSTOM-001")

    def test_scanner_custom_rules_pass(self) -> None:
        """Custom rules that pass produce zero findings."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent_dir = root / "good-agent"
            agent_dir.mkdir()
            (agent_dir / "agent.yaml").write_text("id: test.good-agent\n")
            (agent_dir / "notes.md").write_text("This mentions deploy and rollback.\n")

            rules = {
                "agent_manifest": "agent.yaml",
                "agent_checks": [
                    {
                        "id": "CUSTOM-002",
                        "asi": "ASI08",
                        "severity": "medium",
                        "title": "Missing deploy reference",
                        "file": "notes.md",
                        "contains": "deploy",
                        "recommendation": "Add deploy reference.",
                    }
                ],
                "repo_checks": [],
            }
            rules_path = root / "rules.json"
            rules_path.write_text(json.dumps(rules))

            out = scan_repository_controls(str(root), rules_path=str(rules_path))
            self.assertEqual(len(out["findings"]), 0)
            self.assertEqual(out["risk_score"], 0)

    def test_scanner_contains_any(self) -> None:
        """contains_any passes when at least one term is present."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent_dir = root / "agent-a"
            agent_dir.mkdir()
            (agent_dir / "agent.yaml").write_text("id: test.agent-a\n")
            (agent_dir / "doc.md").write_text("We validate all inputs.\n")

            rules = {
                "agent_manifest": "agent.yaml",
                "agent_checks": [
                    {
                        "id": "ANY-001",
                        "asi": "ASI01",
                        "severity": "low",
                        "title": "Missing validation mention",
                        "file": "doc.md",
                        "contains_any": ["validate", "sanitize"],
                        "recommendation": "Add validation.",
                    }
                ],
                "repo_checks": [],
            }
            rules_path = root / "rules.json"
            rules_path.write_text(json.dumps(rules))

            out = scan_repository_controls(str(root), rules_path=str(rules_path))
            self.assertEqual(len(out["findings"]), 0)

    def test_scanner_contains_all_partial_fail(self) -> None:
        """contains_all fails when not all terms are present."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent_dir = root / "agent-b"
            agent_dir.mkdir()
            (agent_dir / "agent.yaml").write_text("id: test.agent-b\n")
            (agent_dir / "ignore.txt").write_text("__pycache__/\n")

            rules = {
                "agent_manifest": "agent.yaml",
                "agent_checks": [
                    {
                        "id": "ALL-001",
                        "asi": "ASI04",
                        "severity": "low",
                        "title": "Missing cache entries",
                        "file": "ignore.txt",
                        "contains_all": ["__pycache__/", "*.pyc"],
                        "recommendation": "Add both entries.",
                    }
                ],
                "repo_checks": [],
            }
            rules_path = root / "rules.json"
            rules_path.write_text(json.dumps(rules))

            out = scan_repository_controls(str(root), rules_path=str(rules_path))
            self.assertEqual(len(out["findings"]), 1)

    def test_scanner_exists_check(self) -> None:
        """exists check fires when required file is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent_dir = root / "agent-c"
            agent_dir.mkdir()
            (agent_dir / "agent.yaml").write_text("id: test.agent-c\n")

            rules = {
                "agent_manifest": "agent.yaml",
                "agent_checks": [],
                "repo_checks": [
                    {
                        "id": "EXIST-001",
                        "asi": "ASI04",
                        "severity": "low",
                        "title": "Missing Makefile",
                        "file": "Makefile",
                        "exists": True,
                        "recommendation": "Add a Makefile.",
                    }
                ],
            }
            rules_path = root / "rules.json"
            rules_path.write_text(json.dumps(rules))

            out = scan_repository_controls(str(root), rules_path=str(rules_path))
            self.assertEqual(len(out["findings"]), 1)
            self.assertEqual(out["findings"][0]["id"], "EXIST-001")

    def test_scanner_nested_catalog_discovery(self) -> None:
        """Glob discovery finds agents in arbitrary nested structures."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create deeply nested agents
            for name in ["deep/nested/agent-x", "flat-agent"]:
                d = root / name
                d.mkdir(parents=True)
                (d / "agent.yaml").write_text(f"id: test.{name.split('/')[-1]}\n")

            rules = {
                "agent_manifest": "agent.yaml",
                "agent_checks": [],
                "repo_checks": [],
            }
            rules_path = root / "rules.json"
            rules_path.write_text(json.dumps(rules))

            out = scan_repository_controls(str(root), rules_path=str(rules_path))
            self.assertIn("2 agents", out["summary"])

    def test_scanner_with_rules_path_payload(self) -> None:
        """rules_path can be passed via payload to run_agent."""
        out = run_agent(
            agent="security-ops.agentic-security-scanner-agent",
            payload={
                "target_path": ".",
                "rules_path": "policy/scanner-rules.json",
            },
        )
        self.assertIn("summary", out)
        self.assertIn("findings", out)


if __name__ == "__main__":
    unittest.main()
