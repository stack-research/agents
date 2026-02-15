from __future__ import annotations

import unittest

from scripts.run_support_pipeline import run_pipeline


class SupportPipelineTests(unittest.TestCase):
    def test_pipeline_output_shape(self) -> None:
        out = run_pipeline(
            {
                "text": "Customers cannot sign in after password reset.",
                "customer_tier": "pro",
                "customer_name": "Alex",
            },
            mode="deterministic",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )
        self.assertIn("triage", out)
        self.assertIn("draft", out)
        self.assertIn("priority", out["triage"])
        self.assertIn("category", out["triage"])
        self.assertIn("subject", out["draft"])
        self.assertIn("reply", out["draft"])


if __name__ == "__main__":
    unittest.main()
