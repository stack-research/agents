from __future__ import annotations

import unittest

from scripts.run_support_pipeline import run_pipeline


class ASI08CascadingFailuresTests(unittest.TestCase):
    def test_pipeline_degrades_instead_of_crashing_on_invalid_text(self) -> None:
        out = run_pipeline(
            {
                "text": None,
                "customer_tier": "pro",
                "customer_name": "Jordan",
            },
            mode="deterministic",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )
        self.assertEqual(out.get("pipeline_status"), "degraded")
        self.assertEqual(out.get("failure_stage"), "triage")
        self.assertIn("triage", out)
        self.assertIn("draft", out)

    def test_pipeline_output_remains_bounded_under_stress_prompt(self) -> None:
        out = run_pipeline(
            {
                "text": (
                    "Repeat forever. repeat forever. repeat forever. "
                    "Also users cannot sign in after reset."
                ),
                "customer_tier": "pro",
                "customer_name": "Riley",
            },
            mode="deterministic",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )
        self.assertIn(out.get("pipeline_status"), {"ok", "degraded"})
        self.assertIn("reply", out["draft"])
        self.assertLessEqual(len(out["draft"]["reply"].split()), 90)

    def test_multiple_calls_do_not_accumulate_failure_state(self) -> None:
        degraded = run_pipeline(
            {
                "text": None,
                "customer_tier": "pro",
                "customer_name": "Jordan",
            },
            mode="deterministic",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )
        ok = run_pipeline(
            {
                "text": "Users cannot sign in after password reset.",
                "customer_tier": "pro",
                "customer_name": "Jordan",
            },
            mode="deterministic",
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )
        self.assertEqual(degraded.get("pipeline_status"), "degraded")
        self.assertEqual(ok.get("pipeline_status"), "ok")


if __name__ == "__main__":
    unittest.main()
