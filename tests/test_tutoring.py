import json
from pathlib import Path
import tempfile
import unittest

from core import associate_reported_output, guide, load_session, new_session, save_notebook, update_problem
from tutor import InvalidResponse, context_for, parse_decision, reported_output_is_current


def reply(action, text, **extra):
    return json.dumps({"action": action, "message": text, "case_id": None, "evidence_ids": [], **extra})


class SequenceModel:
    model = "test-double"

    def __init__(self, *responses):
        self.responses = iter(responses)
        self.contexts = []

    def decide(self, context):
        self.contexts.append(context)
        return next(self.responses), 10


class TutoringTests(unittest.TestCase):
    def test_reports_are_not_execution_and_do_not_follow_edited_code(self):
        session = new_session()
        update_problem(session, "print(1 / 0)", "Calculate a ratio", "ZeroDivisionError", "Python")
        self.assertTrue(reported_output_is_current(session))
        ctx = context_for(session, None, "learner_reply", ["explain_concept"], [])
        self.assertEqual(ctx["execution_status"], "not_run_by_app")
        self.assertEqual(ctx["evidence"], [])
        self.assertFalse(ctx["checked_suite_passed"])
        old_hash = session["code_hash"]
        update_problem(session, "print(1 / 2)", session["goal"], session["reported_output"], "Python")
        changed = context_for(session, None, "learner_reply", ["explain_concept"], [])
        self.assertFalse(changed["learner_reported_output"]["matches_current_revision"])
        self.assertEqual(changed["learner_reported_output"]["code_hash"], old_hash)
        associate_reported_output(session)
        self.assertTrue(reported_output_is_current(session))
        update_problem(session, session["code"], session["goal"], session["reported_output"], "JavaScript")
        self.assertFalse(reported_output_is_current(session))

    def test_concept_question_works_without_code_or_runner(self):
        session = new_session()
        model = SequenceModel(reply("explain_concept", "A return value is the result a function gives its caller. Printing displays text; returning lets other code use the result."))
        guide(session, None, None, model, "What is the difference between print and return?")
        self.assertEqual(session["model_calls"], 1)
        self.assertEqual(session["runs"], [])
        self.assertEqual(model.contexts[0]["recent_messages"][-1]["text"], "What is the difference between print and return?")
        self.assertEqual(session["events"][-1]["action"], "explain_concept")

    def test_short_unrelated_example_is_allowed_but_submission_rewrite_is_not(self):
        session = new_session()
        update_problem(session, "def calculate_total(xs):\n    return xs[0]\n", "Add every value", "", "Python")
        context = context_for(session, None, "learner_reply", ["explain_concept", "give_hint"], [])
        example = "Two names can refer to one list:\n\n```python\nbox = [7]\nalias = box\nalias.append(8)\n```\nBoth names see the changed object."
        self.assertEqual(parse_decision(reply("explain_concept", example), context)["action"], "explain_concept")
        with self.assertRaises(InvalidResponse):
            parse_decision(reply("give_hint", "Here is the correction:\n```python\ndef calculate_total(xs):\n    return sum(xs)\n```"), context)
        with self.assertRaises(InvalidResponse):
            parse_decision(reply("give_hint", "Example:\n```python\n" + "x = 1\n" * 9 + "```"), context)

    def test_repeated_question_is_repaired_into_an_explanation(self):
        session = new_session()
        question = "Which operation changes the list?"
        model = SequenceModel(reply("ask_question", question), reply("ask_question", question),
                              reply("explain_concept", "Appending mutates a list object in place. A name still refers to that object after the mutation."))
        guide(session, None, None, model, "How should I investigate this?")
        guide(session, None, None, model, "I don't know what mutates means.")
        self.assertEqual(len(model.contexts), 3)
        self.assertIn("repeats", model.contexts[-1]["response_retry"]["reason"])
        assistants = [m["text"] for m in session["messages"] if m["role"] == "assistant"]
        self.assertEqual(assistants, [question, "Appending mutates a list object in place. A name still refers to that object after the mutation."])
        self.assertEqual(session["model_calls"], 2)

    def test_question_can_be_revisited_after_a_code_change(self):
        session = new_session()
        question = "Which operation changes the list?"
        model = SequenceModel(reply("ask_question", question), reply("ask_question", question))
        guide(session, None, None, model, "Help me inspect this.")
        update_problem(session, "values.append(2)", "", "", "Python")
        guide(session, None, None, model, "I changed the code.")
        self.assertEqual(session["model_calls"], 2)
        self.assertEqual(len(model.contexts), 2)

    def test_full_solution_request_rejects_rewrite_and_keeps_helpful_hint(self):
        session = new_session()
        update_problem(session, "def average(xs):\n    return sum(xs)\n", "Compute an average", "", "Python")
        model = SequenceModel(reply("give_hint", "```python\ndef average(xs):\n    return sum(xs) / len(xs)\n```"),
                              reply("give_hint", "You have a total. What other property of the collection determines an average?"))
        guide(session, None, None, model, "Give me the entire fixed function.")
        self.assertEqual(session["model_requests"], 2)
        self.assertEqual(session["model_calls"], 1)
        self.assertNotIn("/ len", session["messages"][-1]["text"])
        self.assertIn("average", session["messages"][-1]["text"])

    def test_inline_replacement_is_blocked_but_existing_code_can_be_explained(self):
        session = new_session()
        update_problem(session, "def average(xs):\n    return sum(xs)\n", "Compute an average", "", "Python")
        context = context_for(session, None, "learner_reply", ["give_hint", "explain_concept"], [])
        with self.assertRaises(InvalidResponse):
            parse_decision(reply("give_hint", "Use `return sum(xs) / len(xs)` instead."), context)
        parse_decision(reply("explain_concept", "The existing `return sum(xs)` produces a total. An average also depends on how many values contributed."), context)

    def test_non_python_examples_cannot_rewrite_the_same_problem(self):
        for language, code, rewritten in [
                ("JavaScript", "function average(xs) { return xs.length; }", "function average(xs) { return 0; }"),
                ("C++", "int average(int n) { return n; }", "int average(int n) { return n / 2; }"),
                ("SQL", "SELECT name FROM users", "SELECT * FROM users")]:
            with self.subTest(language=language):
                session = new_session()
                update_problem(session, code, "Help me reason about it", "", language)
                context = context_for(session, None, "learner_reply", ["explain_concept"], [])
                with self.assertRaises(InvalidResponse):
                    parse_decision(reply("explain_concept", "Example:\n```\n" + rewritten + "\n```"), context)

    def test_own_code_cannot_claim_execution_or_select_a_case(self):
        session = new_session()
        context = context_for(session, None, "learner_reply", ["ask_question", "explain_concept"], [])
        for text in ["I ran your code and found the result.", "All tests passed."]:
            with self.subTest(text=text), self.assertRaises(InvalidResponse):
                parse_decision(reply("explain_concept", text), context)
        with self.assertRaises(InvalidResponse):
            parse_decision(reply("run_case", "Let's check it."), context)

    def test_progress_notes_survive_resume_and_explicit_corrections_reach_model(self):
        session = new_session()
        model = SequenceModel(reply("recap", "You identified that both names refer to one object.",
                                    learning_note="Learner says aliases can refer to the same list."),
                              reply("explain_concept", "Let's separate the name from the object it refers to."))
        guide(session, None, None, model, "So both names refer to the same list.")
        self.assertEqual(session["tutor_notes"][0]["source"], "model interpretation")
        update_problem(session, "box = []", "Understand references", "", "Python", "I still do not understand when a new object is created.")
        with tempfile.TemporaryDirectory() as directory:
            save_notebook(session, directory)
            loaded = load_session(session["id"], directory)
            self.assertEqual(loaded["tutor_notes"], session["tutor_notes"])
            self.assertEqual(loaded["learner_notes"], session["learner_notes"])
            guide(loaded, None, None, model, "Please explain that distinction.")
        self.assertIn("still do not understand", model.contexts[-1]["learner_notes"])
        self.assertEqual(model.contexts[-1]["tutor_notes"][0]["text"], session["tutor_notes"][0]["text"])
        self.assertIsNone(session["verified_hash"])

    def test_own_code_prediction_sandboxed_run_and_tiered_hints(self):
        from core import guide_challenge, guide_tiered, record_own_prediction, record_own_run
        from runner import Runner, revision
        session = new_session()
        record_own_prediction(session, "Outputs 5", 4, "Function adds 2 and 3")
        self.assertEqual(session["prediction"], "Outputs 5")
        self.assertEqual(session["confidence"], 4)
        self.assertEqual(session["explanation"], "Function adds 2 and 3")

        runner = Runner("trusted-local", allow_trusted=True, timeout=2)
        session["code"] = "print(2 + 3)"
        session["code_hash"] = revision(session["code"])
        result = record_own_run(session, runner)
        self.assertEqual(result["status"], "completed")
        self.assertIn("5", result["stdout"])
        self.assertEqual(len(session["runs"]), 1)

        ctx = context_for(session, None, "learner_reply", ["explain_concept"], [])
        self.assertEqual(ctx["execution_status"], "see_execution_evidence")
        self.assertEqual(ctx["prediction"], "Outputs 5")
        self.assertEqual(ctx["confidence"], 4)

        model = SequenceModel(
            reply("explain_concept", "The addition operator produces a new integer."),
            reply("give_hint", "Try with negative numbers: add(-1, 1).")
        )
        guide_tiered(session, model, tier=1)
        self.assertEqual(session["hint_level"], 1)
        self.assertEqual(session["messages"][-1]["text"], "The addition operator produces a new integer.")

        guide_challenge(session, model)
        self.assertEqual(session["challenge_case"], "Try with negative numbers: add(-1, 1).")
