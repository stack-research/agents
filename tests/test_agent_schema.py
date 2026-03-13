from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml
import jsonschema


def _load_schema() -> dict:
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "agent.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


class AgentSchemaTests(unittest.TestCase):
    """Validate every agent.yaml against the JSON Schema in schemas/agent.yaml.json."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = _load_schema()
        cls.root = Path(__file__).resolve().parents[1]
        cls.projects_root = cls.root / "catalog" / "projects"

    def _agent_yamls(self) -> list[tuple[Path, Path]]:
        """Return (project_dir, agent_yaml) pairs for all agents in the catalog."""
        results = []
        for project_dir in sorted(self.projects_root.iterdir()):
            agents_dir = project_dir / "agents"
            if not agents_dir.exists():
                continue
            for agent_dir in sorted(agents_dir.iterdir()):
                if not agent_dir.is_dir():
                    continue
                agent_yaml = agent_dir / "agent.yaml"
                if agent_yaml.exists():
                    results.append((project_dir, agent_dir, agent_yaml))
        return results

    def test_agent_yaml_json_schema(self) -> None:
        """Every agent.yaml must satisfy the JSON Schema."""
        failures: list[str] = []
        for _project_dir, _agent_dir, agent_yaml in self._agent_yamls():
            data = yaml.safe_load(agent_yaml.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(data, self.schema)
            except jsonschema.ValidationError as exc:
                path = " -> ".join(str(p) for p in exc.absolute_path) or "(root)"
                failures.append(
                    f"{agent_yaml.relative_to(self.root)}: {exc.message} (at {path})"
                )
        if failures:
            self.fail("agent.yaml JSON Schema violations:\n" + "\n".join(sorted(failures)))

    def test_agent_yaml_id_matches_directory(self) -> None:
        """id must be <project>.<agent-name> matching the directory names."""
        failures: list[str] = []
        for project_dir, agent_dir, agent_yaml in self._agent_yamls():
            data = yaml.safe_load(agent_yaml.read_text(encoding="utf-8"))
            expected_id = f"{project_dir.name}.{agent_dir.name}"
            declared_id = data.get("id", "")
            if declared_id != expected_id:
                failures.append(
                    f"{agent_yaml.relative_to(self.root)}: id mismatch: "
                    f"expected {expected_id!r}, got {declared_id!r}"
                )
        if failures:
            self.fail("agent.yaml id/directory mismatches:\n" + "\n".join(sorted(failures)))

    def test_agent_yaml_name_matches_directory(self) -> None:
        """name must match the agent directory name."""
        failures: list[str] = []
        for _project_dir, agent_dir, agent_yaml in self._agent_yamls():
            data = yaml.safe_load(agent_yaml.read_text(encoding="utf-8"))
            declared_name = data.get("name", "")
            if declared_name != agent_dir.name:
                failures.append(
                    f"{agent_yaml.relative_to(self.root)}: name mismatch: "
                    f"expected {agent_dir.name!r}, got {declared_name!r}"
                )
        if failures:
            self.fail("agent.yaml name/directory mismatches:\n" + "\n".join(sorted(failures)))


if __name__ == "__main__":
    unittest.main()
