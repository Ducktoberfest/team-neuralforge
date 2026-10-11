import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core import (check_correction, guide, load_notebook, new_session, predict,
                  reveal, save_notebook, sync_code)
from exercises import BASKET, EXERCISES
from runner import Runner
from tutor import Gemma, ModelError, context_for, parse_decision


class TestModel:
    """Test double only. The app has no fake-live-model mode."""
    model = "test-double"

    def __init__(self):
        self.contexts = []

    def decide(self, context):
        self.contexts.append(context)
        actions = context["allowed_actions"]
        action = "run_case" if actions == ["run_case"] else actions[0]
        case = "provided_empty" if "provided_empty" in context["allowed_case_ids"] else None
        item = {"action": action, "message": "What does the observed result tell you about the caller's basket?",
                "case_id": case if action == "run_case" else None,
                "evidence_ids": [context["evidence"][-1]["id"]] if context["evidence"] else []}
        return json.dumps(item), 3


class UnavailableModel:
    model = "unavailable"

    def decide(self, context):
        raise ModelError("Test service unavailable")


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.runner = Runner("trusted-local", allow_trusted=True)
        self.model = TestModel()
        self.session = new_session(BASKET)

    def test_reviewed_examples_and_solutions_execute(self):
        expected_initial = {"basket": ["apple", "banana"], "largest": 0, "total": 5}
        for exercise in EXERCISES.values():
            with self.subTest(exercise=exercise.id):
                result = self.runner.run(exercise, exercise.starter, "prediction")
                self.assertEqual(result["status"], "completed", result)
                self.assertEqual(result["actual"], expected_initial[exercise.id])
                for case in exercise.cases:
                    result = self.runner.run(exercise, exercise.solution, case.id)
                    self.assertTrue(result["passed"], result)

    def test_complete_learning_path_and_revision_invalidation(self):
        predict(self.session, BASKET, self.runner, self.model, '["banana"]', 5,
                "I expected a separate basket each time.")
        self.assertFalse(self.session["prediction_matches_execution"])
        self.assertEqual(self.session["stage"], "guide")
        partial = BASKET.solution.replace("items is None", "not items")
        sync_code(self.session, partial)
        check_correction(self.session, BASKET, self.runner, self.model)
        self.assertIsNone(self.session["verified_hash"])
        self.assertEqual(self.session["runs"][-1]["case_id"], "provided_empty")
        self.assertFalse(self.session["runs"][-1]["passed"])
        self.assertEqual(self.model.contexts[-1]["current_code"], partial)
        sync_code(self.session, BASKET.solution)
        check_correction(self.session, BASKET, self.runner, self.model)
        self.assertEqual(self.session["verified_hash"], self.session["code_hash"])
        self.assertEqual(self.session["outcome"], "checked_cases_passed")
        self.assertEqual(len([r for r in self.session["runs"] if r["code_hash"] == self.session["code_hash"]]), 5)
        sync_code(self.session, BASKET.solution + "\n# another revision\n")
        self.assertIsNone(self.session["verified_hash"])
        self.assertEqual(self.session["outcome"], "in_progress")
        ctx = context_for(self.session, BASKET, "reply", ["ask_question"], [])
        self.assertEqual(ctx["evidence"], [])

    def test_no_fake_ai_success_when_unavailable(self):
        predict(self.session, BASKET, self.runner, UnavailableModel(), '["banana"]', 2, "Unsure")
        self.assertEqual(self.session["model_calls"], 0)
        self.assertEqual(self.session["model_unavailable_events"], 1)
        self.assertIn("unavailable", self.session["messages"][-1]["source"])
        self.assertEqual(self.session["initial_observation"], ["apple", "banana"])

    def test_runner_failure_preserves_prediction_stage(self):
        predict(self.session, BASKET, Runner("trusted-local"), self.model, '["banana"]', 4, "")
        self.assertEqual(self.session["stage"], "predict")
        self.assertIsNone(self.session["initial_observation"])
        self.assertEqual(len(self.model.contexts), 0)

    def test_repeat_prediction_does_not_duplicate_runs(self):
        for _ in range(2):
            predict(self.session, BASKET, self.runner, self.model, '["apple", "banana"]', 5, "Shared default")
        self.assertTrue(self.session["prediction_matches_execution"])
        self.assertEqual(len(self.session["runs"]), 1)

    def test_notebook_upsert_reveal_and_no_model_key(self):
        reveal(self.session)
        sync_code(self.session, BASKET.solution)
        check_correction(self.session, BASKET, self.runner, self.model)
        with tempfile.TemporaryDirectory() as directory:
            save_notebook(self.session, directory)
            save_notebook(self.session, directory)
            records = load_notebook(directory)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["outcome"], "checked_cases_passed_after_reveal")
            self.assertNotIn("api_key", json.dumps(records))

    def test_timeout_syntax_and_output_limit(self):
        short = Runner("trusted-local", allow_trusted=True, timeout=0.25)
        result = short.run(BASKET, "while True:\n    pass\n", "prediction")
        self.assertEqual(result["status"], "timeout")
        result = self.runner.run(BASKET, "def broken(:", "prediction")
        self.assertEqual(result["status"], "syntax_error")
        noisy = "print('x' * 20000)\n" + BASKET.solution
        result = self.runner.run(BASKET, noisy, "prediction")
        self.assertTrue(result["output_truncated"])
        self.assertEqual(len(result["stdout"]), 4096)

    def test_api_key_not_in_child_environment(self):
        code = 'import os\ndef add_item(*args):\n    return [os.environ.get("GEMINI_API_KEY", "absent")]\n'
        with patch.dict(os.environ, {"GEMINI_API_KEY": "sentinel-not-a-real-key"}):
            result = self.runner.run(BASKET, code, "prediction")
        self.assertEqual(result["actual"], ["absent"])

    def test_unknown_actions_cases_evidence_and_spoilers_rejected(self):
        ctx = context_for(self.session, BASKET, "check", ["ask_question", "run_case"], ["provided_empty"])
        base = {"action": "ask_question", "message": "What do you observe?", "case_id": None, "evidence_ids": []}
        for update in [{"action": "shell"}, {"action": "run_case", "case_id": "unknown"},
                       {"evidence_ids": ["fabricated"]}, {"message": "Use items is None to fix it."},
                       {"message": "Your code is proven correct."}]:
            with self.subTest(update=update), self.assertRaises(ModelError):
                parse_decision(json.dumps({**base, **update}), ctx)
        self.assertEqual(parse_decision(json.dumps(base), ctx), base)

    def test_prompt_excludes_reference_solution(self):
        ctx = context_for(self.session, BASKET, "reply", ["ask_question"], [])
        self.assertNotIn("items is None", json.dumps(ctx))
        self.assertEqual(ctx["confidence"], None)

    def test_google_transport_hides_thought_parts(self):
        from io import BytesIO
        response = {"candidates": [{"content": {"parts": [
            {"text": "private thought", "thought": True}, {"text": "visible answer"}]}}]}
        with patch("tutor.request.urlopen", return_value=BytesIO(json.dumps(response).encode())) as call:
            text, _ = Gemma(key="test-key").decide({"event": "test"})
        self.assertEqual(text, "visible answer")
        sent = json.loads(call.call_args.args[0].data)
        self.assertEqual(sent["generationConfig"]["thinkingConfig"]["thinkingLevel"], "minimal")

    def test_stronger_hint_preserves_learner_context(self):
        predict(self.session, BASKET, self.runner, self.model, '["banana"]', 1, "I don't know yet")
        guide(self.session, BASKET, self.runner, self.model, "Does the list survive?", stronger=True)
        ctx = self.model.contexts[-1]
        self.assertEqual(ctx["hint_level"], 1)
        self.assertEqual(ctx["confidence"], 1)
        self.assertEqual(ctx["recent_messages"][-1]["text"], "Does the list survive?")


if __name__ == "__main__":
    unittest.main()
