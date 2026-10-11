import json
from pathlib import Path
import unittest
from evaluate_tutor import run_case


class ReviewModel:
    model = "test-double"

    def decide(self, context):
        text = "Let us separate the object from the names that refer to it." if context["mode"] == "own_code" else "Your prediction matched execution; consider the independent-call requirement."
        return json.dumps({"action": "explain_concept", "message": text, "case_id": None, "evidence_ids": []}), 5


class EvaluationTests(unittest.TestCase):
    def test_scenario_report_preserves_live_reply_status_without_grading_teaching(self):
        cases = json.loads((Path(__file__).parents[1] / "conversation_evals.json").read_text())
        for case in cases:
            with self.subTest(case=case["id"]):
                report = run_case(case, ReviewModel())
                self.assertTrue(all(turn["usable_live_reply"] for turn in report["turns"]))
                self.assertEqual(report["human_review"]["status"], "not_scored")
                self.assertIsNone(report["human_review"]["scores"])
                self.assertEqual(report["rubric"], case["rubric"])
                self.assertLessEqual(report["model_requests"], 2 * len(report["turns"]))
                if case["mode"] == "own_code":
                    self.assertFalse(any(event["type"] == "execution" for event in report["events"]))
                    self.assertEqual(report["turns"][0]["code"], case.get("code", ""))
                    expected_code = case.get("code", "")
                    for fixture, turn in zip(case["turns"], report["turns"]):
                        expected_code = fixture.get("code", expected_code)
                        self.assertEqual(turn["code"], expected_code)
                        self.assertEqual(turn["goal"], case.get("goal", ""))
