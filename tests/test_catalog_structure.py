from __future__ import annotations

import unittest
from pathlib import Path

REQUIRED_FILES = [
    "agent.yaml",
    "prompts/system.md",
    "workflows/runbook.md",
    "examples/example-input.json",
    "examples/example-output.json",
    "tests/smoke.md",
]


class CatalogStructureTests(unittest.TestCase):
    def test_required_files_exist_for_each_agent(self) -> None:
        root = Path(__file__).resolve().parents[1]
        agents_root = root / "catalog" / "projects"
        missing: list[str] = []

        for project_dir in agents_root.iterdir():
            agents_dir = project_dir / "agents"
            if not agents_dir.exists():
                continue
            for agent_dir in agents_dir.iterdir():
                if not agent_dir.is_dir():
                    continue
                for rel_path in REQUIRED_FILES:
                    candidate = agent_dir / rel_path
                    if not candidate.exists():
                        missing.append(str(candidate.relative_to(root)))

        if missing:
            self.fail("missing required files:\n" + "\n".join(sorted(missing)))


if __name__ == "__main__":
    unittest.main()
