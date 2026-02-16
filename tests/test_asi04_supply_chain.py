from __future__ import annotations

import unittest
from pathlib import Path

from local_agents.core import ValidationError
from local_agents.engine import run_agent


class ASI04SupplyChainTests(unittest.TestCase):
    def test_docker_compose_pins_ollama_image(self) -> None:
        root = Path(__file__).resolve().parents[1]
        compose = (root / "docker-compose.yml").read_text(encoding="utf-8").lower()
        self.assertIn("ollama/ollama@sha256:", compose)
        self.assertNotIn("ollama/ollama:latest", compose)

    def test_unapproved_llm_model_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            run_agent(
                agent="starter-kit.classifier-agent",
                payload={"text": "Please add SSO support."},
                mode="llm",
                model="evilmodel:latest",
                base_url="http://localhost:11434",
            )

    def test_nonlocal_llm_host_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            run_agent(
                agent="starter-kit.classifier-agent",
                payload={"text": "Please add SSO support."},
                mode="llm",
                model="llama3.2:3b",
                base_url="http://attacker.example:11434",
            )


if __name__ == "__main__":
    unittest.main()
