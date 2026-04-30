"""Ensure Agent Skills under .agents/skills/ are present and reachable (layout + frontmatter)."""

from __future__ import annotations

import unittest
from pathlib import Path


class AgentsSkillsLayoutTests(unittest.TestCase):
    def test_stack_research_agents_testing_skill_reachable(self) -> None:
        root = Path(__file__).resolve().parents[1]
        skill_dir = root / ".agents" / "skills" / "stack-research-agents-testing"
        skill_md = skill_dir / "SKILL.md"
        ref_md = skill_dir / "references" / "repository-runtime-tests.md"

        self.assertTrue(skill_md.is_file(), f"missing {skill_md}")
        self.assertTrue(ref_md.is_file(), f"missing {ref_md}")

        text = skill_md.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"), "SKILL.md must start with YAML frontmatter")
        self.assertIn("name: stack-research-agents-testing", text)
        self.assertRegex(text, r"(?m)^description: .+")
        self.assertIn("[references/repository-runtime-tests.md]", text)

        ref_text = ref_md.read_text(encoding="utf-8")
        self.assertIn("scripts/run_agent.py", ref_text)
        self.assertIn("tests/test_engine.py", ref_text)

    def test_legacy_skill_paths_removed(self) -> None:
        root = Path(__file__).resolve().parents[1]
        legacy_cursor = root / ".cursor" / "skills" / "stack-research-agents-testing" / "SKILL.md"
        self.assertFalse(legacy_cursor.exists(), f"legacy skill should not exist: {legacy_cursor}")
        legacy_agents = root / "agents" / "skills" / "stack-research-agents-testing" / "SKILL.md"
        self.assertFalse(legacy_agents.exists(), f"non-dot agents/ skill path should not exist: {legacy_agents}")


if __name__ == "__main__":
    unittest.main()
