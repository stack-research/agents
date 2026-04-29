from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.compare_agent_incident_drill_scorecards import diff_drill_scorecards


class CompareAgentIncidentDrillScorecardsTests(unittest.TestCase):
    def test_diff_detects_scope_change(self) -> None:
        baseline = {
            "workflow_id": "a",
            "scenario": "support-export-boundary",
            "pipeline_status": "needs_review",
            "scorecard": {
                "scope_validation": "review",
                "unsafe_action_executed": False,
                "lineage_complete": True,
                "kill_path_ready": True,
                "rollback_ready": True,
                "residual_exposure": "contained",
            },
        }
        current = {
            "workflow_id": "b",
            "scenario": "supply-chain-compromise",
            "pipeline_status": "blocked",
            "scorecard": {
                "scope_validation": "fail",
                "unsafe_action_executed": False,
                "lineage_complete": True,
                "kill_path_ready": True,
                "rollback_ready": True,
                "residual_exposure": "contained",
            },
        }
        out = diff_drill_scorecards(baseline, current)

        self.assertEqual(out["baseline"]["workflow_id"], "a")
        self.assertEqual(out["current"]["scenario"], "supply-chain-compromise")
        self.assertTrue(out["any_scorecard_change"])
        delta = out["scorecard_delta"]["scope_validation"]
        self.assertTrue(delta["changed"])
        self.assertEqual(delta["baseline"], "review")
        self.assertEqual(delta["current"], "fail")
        unchanged = out["scorecard_delta"]["unsafe_action_executed"]
        self.assertFalse(unchanged["changed"])

    def test_diff_identical_scorecards(self) -> None:
        body = {
            "workflow_id": "x",
            "scenario": "s",
            "pipeline_status": "needs_review",
            "scorecard": {
                "scope_validation": "review",
                "unsafe_action_executed": False,
                "lineage_complete": True,
                "kill_path_ready": True,
                "rollback_ready": True,
                "residual_exposure": "contained",
            },
        }
        out = diff_drill_scorecards(body, json.loads(json.dumps(body)))
        self.assertFalse(out["any_scorecard_change"])

    def test_diff_rejects_missing_scorecard(self) -> None:
        with self.assertRaises(ValueError):
            diff_drill_scorecards({"workflow_id": "a"}, {"scorecard": {}})

    def test_cli_on_temp_files(self) -> None:
        import subprocess

        root = Path(__file__).resolve().parents[1]
        a = {"scorecard": {"scope_validation": "review", "unsafe_action_executed": False}}
        b = {"scorecard": {"scope_validation": "fail", "unsafe_action_executed": False}}
        with tempfile.TemporaryDirectory() as tmp:
            p1 = Path(tmp) / "one.json"
            p2 = Path(tmp) / "two.json"
            p1.write_text(json.dumps(a), encoding="utf-8")
            p2.write_text(json.dumps(b), encoding="utf-8")
            proc = subprocess.run(
                [
                    "python3",
                    str(root / "scripts" / "compare_agent_incident_drill_scorecards.py"),
                    "--baseline",
                    str(p1),
                    "--current",
                    str(p2),
                ],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        parsed = json.loads(proc.stdout)
        self.assertTrue(parsed["any_scorecard_change"])


if __name__ == "__main__":
    unittest.main()
