import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core import (check_correction, guide, list_saved_sessions, load_env_file, load_notebook,
                  load_session, new_session, predict, record_transfer, reveal, save_notebook, sync_code)
from exercises import (BASKET, CLOSURES, COUNTDOWN, EXERCISES, SCOPE_LEAK,
                       SHALLOW_COPY, TransferReflection)
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
        expected_initial = {
            "basket": ["apple", "banana"],
            "largest": 0,
            "total": 5,
            "closures": [20, 20, 20],
            "countdown": [3, 2, 1],
            "shallow_copy": "Z",
            "scope_leak": "UnboundLocalError",
        }
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

    def test_shallow_copy_learning_path_and_verification(self):
        session = new_session(SHALLOW_COPY)
        predict(session, SHALLOW_COPY, self.runner, self.model, "A", 4, "I expected an independent copy")
        self.assertFalse(session["prediction_matches_execution"])
        self.assertEqual(session["initial_observation"], "Z")
        self.assertEqual(session["stage"], "guide")

        # Ineffective fix: grid.copy() is still shallow
        ineffective = "def clone_grid(grid):\n    return grid.copy()\n"
        sync_code(session, ineffective)
        check_correction(session, SHALLOW_COPY, self.runner, self.model)
        self.assertIsNone(session["verified_hash"])
        self.assertFalse(session["runs"][-1]["passed"])

        # Canonical solution
        sync_code(session, SHALLOW_COPY.solution)
        check_correction(session, SHALLOW_COPY, self.runner, self.model)
        self.assertEqual(session["verified_hash"], session["code_hash"])
        self.assertEqual(session["stage"], "reflect")
        self.assertEqual(session["outcome"], "checked_cases_passed")

    def test_scope_leak_learning_path_and_verification(self):
        session = new_session(SCOPE_LEAK)
        predict(session, SCOPE_LEAK, self.runner, self.model, "1", 5, "I expected count to increment")
        self.assertFalse(session["prediction_matches_execution"])
        self.assertEqual(session["initial_observation"], "UnboundLocalError")
        self.assertEqual(session["stage"], "guide")

        # Ineffective fix: assigning without nonlocal still triggers UnboundLocalError
        ineffective = ("def make_counter(start=0):\n"
                       "    count = start\n"
                       "    def tick(step=1):\n"
                       "        count = count + step\n"
                       "        return count\n"
                       "    return tick\n")
        sync_code(session, ineffective)
        check_correction(session, SCOPE_LEAK, self.runner, self.model)
        self.assertIsNone(session["verified_hash"])
        self.assertFalse(session["runs"][-1]["passed"])

        # Canonical solution
        sync_code(session, SCOPE_LEAK.solution)
        check_correction(session, SCOPE_LEAK, self.runner, self.model)
        self.assertEqual(session["verified_hash"], session["code_hash"])
        self.assertEqual(session["stage"], "reflect")
        self.assertEqual(session["outcome"], "checked_cases_passed")

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

    def test_context_separates_correct_prediction_from_failed_requirement(self):
        for choice, matched in [('["apple", "banana"]', True),
                                ('["banana"]', False), ("I'm not sure", None)]:
            with self.subTest(choice=choice):
                session = new_session(BASKET)
                model = TestModel()
                predict(session, BASKET, self.runner, model, choice, 5, "Testing the distinction")
                context = model.contexts[-1]
                review = context["prediction_review"]
                self.assertEqual(review["learner_prediction"], choice)
                self.assertEqual(review["observed_result"], ["apple", "banana"])
                self.assertEqual(review["required_result"], ["banana"])
                self.assertIs(review["matches_execution"], matched)
                self.assertEqual(review["code_hash"], session["code_hash"])
                evidence = context["evidence"][0]
                self.assertEqual(evidence["actual"], ["apple", "banana"])
                self.assertEqual(evidence["required_result"], ["banana"])
                self.assertFalse(evidence["passed"])
                self.assertNotIn("expected", evidence)
                original_hash = session["code_hash"]
                sync_code(session, BASKET.solution)
                edited = context_for(session, BASKET, "learner_reply", ["ask_question"], [])
                self.assertEqual(edited["prediction_review"]["code_hash"], original_hash)
                self.assertNotEqual(edited["code_hash"], original_hash)
                self.assertEqual(edited["evidence"], [])

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

    def test_session_save_and_hydration_restores_state_and_invalidates_hash(self):
        session = new_session(BASKET)
        predict(session, BASKET, self.runner, self.model, '["banana"]', 5, "Shared default argument")
        sync_code(session, BASKET.solution)
        check_correction(session, BASKET, self.runner, self.model)
        self.assertEqual(session["verified_hash"], session["code_hash"])
        self.assertEqual(session["stage"], "reflect")

        with tempfile.TemporaryDirectory() as directory:
            save_notebook(session, directory)

            saved_list = list_saved_sessions(directory)
            self.assertEqual(len(saved_list), 1)
            self.assertEqual(saved_list[0]["id"], session["id"])
            self.assertEqual(saved_list[0]["exercise_id"], "basket")

            loaded = load_session(session["id"], directory)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["id"], session["id"])
            self.assertEqual(loaded["exercise_id"], "basket")
            self.assertEqual(loaded["stage"], "reflect")
            self.assertEqual(loaded["code"], session["code"])
            self.assertEqual(loaded["learner_code"], session["code"])
            self.assertEqual(loaded["code_hash"], session["code_hash"])
            self.assertEqual(loaded["verified_hash"], session["code_hash"])
            self.assertEqual(loaded["prediction"], '["banana"]')
            self.assertEqual(loaded["confidence"], 5)
            self.assertEqual(loaded["explanation"], "Shared default argument")
            self.assertEqual(len(loaded["runs"]), len(session["runs"]))
            self.assertEqual(len(loaded["messages"]), len(session["messages"]))
            self.assertEqual(loaded["solution_viewed"], False)

            modified_code = loaded["code"] + "\n# whitespace or comment change\n"
            changed = sync_code(loaded, modified_code)
            self.assertTrue(changed)
            self.assertEqual(loaded["code"], modified_code)
            self.assertEqual(loaded["learner_code"], modified_code)
            self.assertIsNone(loaded["verified_hash"])
            self.assertEqual(loaded["outcome"], "in_progress")

            self.assertIsNone(load_session("nonexistent-uuid", directory))
            corrupt_file = Path(directory) / "corrupt.json"
            corrupt_file.write_text("invalid json")
            self.assertIsNone(load_session("corrupt", directory))

    def test_new_exercises_anti_spoiler_and_runner_validation(self):
        closures_session = new_session(CLOSURES)
        closures_ctx = context_for(closures_session, CLOSURES, "test", ["ask_question"], [])
        base = {"action": "ask_question", "message": "What is the value of i?", "case_id": None, "evidence_ids": []}
        for spoiler in ["Use i=i to fix the closure", "Bind as a default parameter"]:
            with self.subTest(spoiler=spoiler), self.assertRaises(ModelError):
                parse_decision(json.dumps({**base, "message": spoiler}), closures_ctx)

        countdown_session = new_session(COUNTDOWN)
        countdown_ctx = context_for(countdown_session, COUNTDOWN, "test", ["ask_question"], [])
        for spoiler in ["Check if n < 0 to return empty list", "Use n == 0 to stop"]:
            with self.subTest(spoiler=spoiler), self.assertRaises(ModelError):
                parse_decision(json.dumps({**base, "message": spoiler}), countdown_ctx)

        shallow_session = new_session(SHALLOW_COPY)
        shallow_ctx = context_for(shallow_session, SHALLOW_COPY, "test", ["ask_question"], [])
        for spoiler in ["Use deepcopy on the grid", "Do [list(row) for row in grid]"]:
            with self.subTest(spoiler=spoiler), self.assertRaises(ModelError):
                parse_decision(json.dumps({**base, "message": spoiler}), shallow_ctx)

        scope_session = new_session(SCOPE_LEAK)
        scope_ctx = context_for(scope_session, SCOPE_LEAK, "test", ["ask_question"], [])
        for spoiler in ["Add nonlocal count inside tick", "Store in count[0]"]:
            with self.subTest(spoiler=spoiler), self.assertRaises(ModelError):
                parse_decision(json.dumps({**base, "message": spoiler}), scope_ctx)

        valid_closures = parse_decision(json.dumps(base), closures_ctx)
        self.assertEqual(valid_closures["message"], "What is the value of i?")
        valid_countdown = parse_decision(json.dumps(base), countdown_ctx)
        self.assertEqual(valid_countdown["message"], "What is the value of i?")
        valid_shallow = parse_decision(json.dumps(base), shallow_ctx)
        self.assertEqual(valid_shallow["message"], "What is the value of i?")
        valid_scope = parse_decision(json.dumps(base), scope_ctx)
        self.assertEqual(valid_scope["message"], "What is the value of i?")

    def test_transfer_reflection_metadata_and_interactive_check(self):
        for exercise_id, exercise in EXERCISES.items():
            with self.subTest(exercise=exercise_id):
                reflection = exercise.reflection
                self.assertIsNotNone(reflection, f"Missing reflection in {exercise_id}")
                self.assertIsInstance(reflection, TransferReflection)
                self.assertIsInstance(reflection.transfer_snippet, str)
                self.assertGreater(len(reflection.transfer_snippet), 0)
                self.assertIsInstance(reflection.transfer_prompt, str)
                self.assertGreater(len(reflection.transfer_prompt), 0)
                self.assertIsInstance(reflection.transfer_choices, tuple)
                self.assertIn(len(reflection.transfer_choices), (3, 4))
                self.assertIsInstance(reflection.correct_choice_index, int)
                self.assertTrue(0 <= reflection.correct_choice_index < len(reflection.transfer_choices))
                self.assertIsInstance(reflection.explanation, str)
                self.assertGreater(len(reflection.explanation), 0)

                # Verify dict-style interface compatibility
                self.assertEqual(reflection["transfer_snippet"], reflection.transfer_snippet)
                self.assertEqual(reflection.get("transfer_prompt"), reflection.transfer_prompt)
                self.assertIn("transfer_choices", reflection)
                self.assertEqual(dict(reflection)["correct_choice_index"], reflection.correct_choice_index)

        # Interactive check execution & persistence testing
        session = new_session(BASKET)
        refl = BASKET.reflection
        wrong_choice = refl.transfer_choices[0]
        correct_choice = refl.transfer_choices[refl.correct_choice_index]

        # 1. Test incorrect submission
        is_correct = record_transfer(session, BASKET, wrong_choice, "My preliminary hypothesis")
        self.assertFalse(is_correct)
        self.assertEqual(session["followup_status"], "needs_review")
        self.assertFalse(session["transfer_correct"])
        self.assertEqual(session["transfer_prediction"], wrong_choice)
        self.assertEqual(session["followup_answer"]["prediction"], wrong_choice)
        self.assertEqual(session["events"][-1]["type"], "transfer_check_submitted")
        self.assertFalse(session["events"][-1]["correct"])

        # 2. Test correct submission
        is_correct = record_transfer(session, BASKET, correct_choice, "Both names point to same list")
        self.assertTrue(is_correct)
        self.assertEqual(session["followup_status"], "correct_on_prepared_question")
        self.assertTrue(session["transfer_correct"])
        self.assertEqual(session["transfer_prediction"], correct_choice)
        self.assertEqual(session["followup_answer"]["prediction"], correct_choice)
        self.assertEqual(session["reflection_response"]["prediction"], correct_choice)
        self.assertTrue(session["events"][-1]["correct"])

        # 3. Test persistence to disk and session hydration
        with tempfile.TemporaryDirectory() as directory:
            save_notebook(session, directory)
            loaded = load_session(session["id"], directory)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["transfer_prediction"], correct_choice)
            self.assertTrue(loaded["transfer_correct"])
            self.assertEqual(loaded["followup_status"], "correct_on_prepared_question")
            self.assertEqual(loaded["reflection_response"]["prediction"], correct_choice)

    def test_load_env_file_parser_behavior(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "# Leading comment\n"
                "\n"
                "SAMPLE_PLAIN_KEY=hello_world\n"
                "SAMPLE_DOUBLE_QUOTED=\"value with spaces and = sign\"\n"
                "SAMPLE_SINGLE_QUOTED='single_value'\n"
                "# Commented out key\n"
                "# INACTIVE_KEY=unused\n"
                "EXISTING_KEY=new_override_value\n"
            )
            with patch.dict(os.environ, {"EXISTING_KEY": "prior_system_value"}, clear=False):
                loaded = load_env_file(env_path)
                self.assertEqual(loaded["SAMPLE_PLAIN_KEY"], "hello_world")
                self.assertEqual(os.environ["SAMPLE_PLAIN_KEY"], "hello_world")
                self.assertEqual(loaded["SAMPLE_DOUBLE_QUOTED"], "value with spaces and = sign")
                self.assertEqual(loaded["SAMPLE_SINGLE_QUOTED"], "single_value")
                self.assertNotIn("INACTIVE_KEY", loaded)
                # Existing environment variable is preserved when override=False
                self.assertEqual(loaded["EXISTING_KEY"], "prior_system_value")
                self.assertEqual(os.environ["EXISTING_KEY"], "prior_system_value")

                # Test override=True
                loaded_override = load_env_file(env_path, override=True)
                self.assertEqual(loaded_override["EXISTING_KEY"], "new_override_value")
                self.assertEqual(os.environ["EXISTING_KEY"], "new_override_value")

    def test_app_boots_cleanly_with_and_without_api_key(self):
        from streamlit.testing.v1 import AppTest
        app_path = str(Path(__file__).parents[1] / "app.py")

        # 1. Boot without API key
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
            app_without = AppTest.from_file(app_path, default_timeout=15).run()
            self.assertFalse(app_without.exception)
            self.assertEqual(app_without.text_input(key="api_key").value, "")

        # 2. Boot with API key
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-env-key-999", "GOOGLE_API_KEY": ""}):
            app_with = AppTest.from_file(app_path, default_timeout=15).run()
            self.assertFalse(app_with.exception)
            self.assertEqual(app_with.text_input(key="api_key").value, "test-env-key-999")
            self.assertTrue(any("Loaded from local environment" in c.value for c in app_with.caption))


if __name__ == "__main__":
    unittest.main()

