from __future__ import annotations

import json
import unittest
from pathlib import Path

EXPECTED_ENVS = {"dev", "staging", "prod"}
EXPECTED_ASI = {f"ASI{index:02d}" for index in range(1, 11)}


class PolicyPackTests(unittest.TestCase):
    def test_policy_pack_exists_and_has_required_shape(self) -> None:
        root = Path(__file__).resolve().parents[1]
        path = root / "policy" / "asi-control-baselines.json"
        self.assertTrue(path.exists(), "policy pack file is missing")

        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload.get("policy_pack"), "asi-control-baselines")
        self.assertIsInstance(payload.get("version"), str)

        envs = payload.get("environments")
        self.assertIsInstance(envs, dict)
        self.assertEqual(set(envs.keys()), EXPECTED_ENVS)

        for env_name in EXPECTED_ENVS:
            env = envs[env_name]
            self.assertIn(env.get("change_control"), {"relaxed", "moderate", "strict"})
            self.assertIsInstance(env.get("human_approval_required"), bool)
            self.assertIsInstance(env.get("llm_mode_allowed"), bool)

            asi_controls = env.get("asi_controls")
            self.assertIsInstance(asi_controls, dict)
            self.assertEqual(set(asi_controls.keys()), EXPECTED_ASI)

            for asi in EXPECTED_ASI:
                entry = asi_controls[asi]
                self.assertEqual(entry.get("baseline"), "required")
                controls = entry.get("controls")
                self.assertIsInstance(controls, list)
                self.assertGreaterEqual(len(controls), 2)
                self.assertTrue(all(isinstance(item, str) and item.strip() for item in controls))


if __name__ == "__main__":
    unittest.main()
