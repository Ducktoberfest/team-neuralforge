import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from core import new_session, save_notebook, update_problem

ROOT = Path(__file__).parents[1]
ANSWER = json.dumps({"action": "explain_concept", "message": "A return value gives a result to the caller. Printing displays text. Other code can use a returned result.",
                     "case_id": None, "evidence_ids": [], "learning_note": "Learner is asking about printing and returning."})


class OwnCodeInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"DATA_DIR": self.directory.name, "GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.directory.cleanup()

    def app(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
        self.assertFalse(app.exception)
        return app

    def test_default_chat_needs_no_execution_opt_in_and_calls_only_on_submit(self):
        with patch("tutor.Gemma.decide", return_value=(ANSWER, 80)) as call:
            app = self.app()
            self.assertEqual(app.selectbox(key="workspace_mode").value, "own_code")
            self.assertFalse(any(c.key == "trusted_code" for c in app.checkbox))
            self.assertEqual(len(list(Path(self.directory.name).glob("*.json"))), 0)
            app.run()
            self.assertEqual(call.call_count, 0)
            sid = app.session_state["session"]["id"]
            app.chat_input(key=f"own_chat_{sid}").set_value("What is print versus return?").run()
            self.assertFalse(app.exception)
            self.assertEqual(call.call_count, 1)
            self.assertEqual(app.session_state["session"]["model_calls"], 1)
            self.assertEqual(app.session_state["session"]["runs"], [])
            app.run()
            self.assertEqual(call.call_count, 1)
            self.assertEqual(len(list(Path(self.directory.name).glob("*.json"))), 1)

    def test_workspace_switch_preserves_code_and_problem_fields(self):
        app = self.app()
        sid = app.session_state["session"]["id"]
        app.text_area(key=f"editor_{sid}").set_value("console.log(total);").run()
        app.text_area(key=f"goal_{sid}").set_value("Print the shopping total").run()
        app.selectbox(key=f"language_{sid}").set_value("JavaScript").run()
        app.text_area(key=f"reported_output_{sid}").set_value("ReferenceError: total is not defined").run()
        app.selectbox(key="workspace_mode").set_value("practice").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["session"]["exercise_id"], "basket")
        app.selectbox(key="workspace_mode").set_value("own_code").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["session"]["id"], sid)
        self.assertEqual(app.text_area(key=f"editor_{sid}").value, "console.log(total);")
        self.assertEqual(app.text_area(key=f"goal_{sid}").value, "Print the shopping total")
        self.assertEqual(app.selectbox(key=f"language_{sid}").value, "JavaScript")
        self.assertIn("ReferenceError", app.text_area(key=f"reported_output_{sid}").value)

    def test_resumed_own_session_restores_all_inputs_and_notes(self):
        saved = new_session()
        update_problem(saved, "SELECT name FROM users", "Find names", "No rows", "SQL", "I understand filtering.")
        save_notebook(saved, self.directory.name)
        app = self.app()
        app.button(key="load_session_btn").click().run()
        self.assertFalse(app.exception)
        sid = saved["id"]
        self.assertEqual(app.session_state["session"]["id"], sid)
        self.assertEqual(app.text_area(key=f"editor_{sid}").value, saved["code"])
        self.assertEqual(app.text_area(key=f"learner_notes_{sid}").value, saved["learner_notes"])
        self.assertEqual(app.selectbox(key=f"language_{sid}").value, "SQL")
        self.assertEqual(app.text_area(key=f"reported_output_{sid}").value, "No rows")

    def test_edited_code_keeps_old_output_stale_until_user_confirms(self):
        from tutor import reported_output_is_current
        app = self.app()
        sid = app.session_state["session"]["id"]
        app.text_area(key=f"editor_{sid}").set_value("print(1 / 0)").run()
        app.text_area(key=f"reported_output_{sid}").set_value("ZeroDivisionError").run()
        self.assertTrue(reported_output_is_current(app.session_state["session"]))
        app.text_area(key=f"editor_{sid}").set_value("print(2 / 0)").run()
        self.assertFalse(reported_output_is_current(app.session_state["session"]))
        app.button(key=f"confirm_output_{sid}").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(reported_output_is_current(app.session_state["session"]))
