from __future__ import annotations

import re
import unittest
from pathlib import Path

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


class AgentSchemaTests(unittest.TestCase):
    def test_agent_yaml_minimum_schema_consistency(self) -> None:
        root = Path(__file__).resolve().parents[1]
        projects_root = root / "catalog" / "projects"
        failures: list[str] = []

        for project_dir in projects_root.iterdir():
            agents_dir = project_dir / "agents"
            if not agents_dir.exists():
                continue

            for agent_dir in agents_dir.iterdir():
                if not agent_dir.is_dir():
                    continue

                agent_yaml = agent_dir / "agent.yaml"
                if not agent_yaml.exists():
                    continue

                text = agent_yaml.read_text(encoding="utf-8")
                id_match = re.search(r"^id:\s*(.+)$", text, flags=re.MULTILINE)
                name_match = re.search(r"^name:\s*(.+)$", text, flags=re.MULTILINE)
                version_match = re.search(r"^version:\s*(.+)$", text, flags=re.MULTILINE)

                if not id_match:
                    failures.append(f"{agent_yaml.relative_to(root)} missing id")
                    continue
                if not name_match:
                    failures.append(f"{agent_yaml.relative_to(root)} missing name")
                    continue
                if not version_match:
                    failures.append(f"{agent_yaml.relative_to(root)} missing version")
                    continue

                declared_id = id_match.group(1).strip()
                declared_name = name_match.group(1).strip()
                declared_version = version_match.group(1).strip()

                expected_project = project_dir.name
                expected_agent = agent_dir.name
                expected_id = f"{expected_project}.{expected_agent}"

                if declared_id != expected_id:
                    failures.append(
                        f"{agent_yaml.relative_to(root)} id mismatch: expected {expected_id}, got {declared_id}"
                    )
                if declared_name != expected_agent:
                    failures.append(
                        f"{agent_yaml.relative_to(root)} name mismatch: expected {expected_agent}, got {declared_name}"
                    )
                if not SEMVER_RE.match(declared_version):
                    failures.append(
                        f"{agent_yaml.relative_to(root)} invalid semver version: {declared_version}"
                    )

                if "\ninputs:" not in text:
                    failures.append(f"{agent_yaml.relative_to(root)} missing inputs section")
                if "\noutputs:" not in text:
                    failures.append(f"{agent_yaml.relative_to(root)} missing outputs section")

        if failures:
            self.fail("agent schema failures:\n" + "\n".join(sorted(failures)))


if __name__ == "__main__":
    unittest.main()
