import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from exercises import BASKET


class InterfaceTests(unittest.TestCase):
    def test_session_survives_reruns_and_reaches_notebook(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"DATA_DIR": directory}):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
                app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=15).run()
                self.assertFalse(app.exception)
                app.checkbox(key="trusted_code").check().run()
                app.radio[0].set_value('["banana"]')
                app.slider[0].set_value(5)
                [b for b in app.button if b.label == "Predict & run"][0].click().run()
                self.assertFalse(app.exception)
                session = app.session_state["session"]
                self.assertEqual(session["stage"], "guide")
                count = len(session["runs"])
                app.run()
                self.assertEqual(len(app.session_state["session"]["runs"]), count)
                editor = next(t for t in app.text_area if t.label == "Python editor")
                editor.set_value(BASKET.solution.replace("items is None", "not items")).run()
                app.button(key="check_correction").click().run()
                self.assertFalse(app.exception)
                self.assertIsNone(app.session_state["session"]["verified_hash"])
                next(t for t in app.text_area if t.label == "Python editor").set_value(BASKET.solution).run()
                app.button(key="check_correction").click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["session"]["stage"], "reflect")
                self.assertTrue(any("5 checked cases" in item.value for item in app.success))
                self.assertEqual(len(list(Path(directory).glob("*.json"))), 1)
                next(t for t in app.text_area if t.label == "Python editor").set_value(BASKET.starter).run()
                self.assertFalse(any("5 checked cases" in item.value for item in app.success))

    def test_saved_session_can_be_resumed(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"DATA_DIR": directory}):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
                saved = {
                    "schema_version": 1,
                    "id": "testsession123",
                    "exercise_id": "basket",
                    "exercise_version": 1,
                    "concept": "Shared mutable state",
                    "started_at": "2026-10-11T00:00:00Z",
                    "updated_at": "2026-10-11T00:05:00Z",
                    "stage": "guide",
                    "code": BASKET.solution,
                    "code_hash": "testhash",
                    "verified_hash": None,
                    "prediction": '["banana"]',
                    "confidence": 4,
                    "explanation": "test reason",
                    "initial_observation": ["apple", "banana"],
                    "prediction_matches_execution": False,
                    "messages": [{"role": "user", "text": "my reply", "source": "Learner"}],
                    "runs": [],
                    "events": [],
                    "attempts": 1,
                    "hint_level": 1,
                    "hint_count": 1,
                    "solution_viewed": False,
                    "outcome": "in_progress",
                    "model_calls": 1,
                    "model_unavailable_events": 0,
                    "followup_status": "not_attempted",
                }
                (Path(directory) / "testsession123.json").write_text(json.dumps(saved))

                app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=15).run()
                self.assertFalse(app.exception)
                load_btn = app.button(key="load_session_btn")
                load_btn.click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["session"]["id"], "testsession123")
                self.assertEqual(app.session_state["session"]["stage"], "guide")
                self.assertEqual(app.session_state["session"]["confidence"], 4)

    def test_transfer_check_interactive_ui(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"DATA_DIR": directory}):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
                from core import revision
                h = revision(BASKET.solution)
                saved = {
                    "schema_version": 1,
                    "id": "reflectsession456",
                    "exercise_id": "basket",
                    "exercise_version": 1,
                    "concept": "Shared mutable state",
                    "started_at": "2026-10-11T00:00:00Z",
                    "updated_at": "2026-10-11T00:05:00Z",
                    "stage": "reflect",
                    "code": BASKET.solution,
                    "code_hash": h,
                    "verified_hash": h,
                    "prediction": '["banana"]',
                    "confidence": 5,
                    "explanation": "test reason",
                    "initial_observation": ["apple", "banana"],
                    "prediction_matches_execution": False,
                    "messages": [],
                    "runs": [],
                    "events": [],
                    "attempts": 1,
                    "hint_level": 0,
                    "hint_count": 0,
                    "solution_viewed": False,
                    "outcome": "checked_cases_passed",
                    "model_calls": 1,
                    "model_unavailable_events": 0,
                    "followup_status": "not_attempted",
                }
                (Path(directory) / "reflectsession456.json").write_text(json.dumps(saved))
                app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=15).run()
                self.assertFalse(app.exception)
                app.button(key="load_session_btn").click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["session"]["stage"], "reflect")

                # Verify transfer radio exists and can submit a prediction
                transfer_radio = next(r for r in app.radio if r.key == "transfer_choice_reflectsession456")
                transfer_radio.set_value("[1, 2]")
                submit_btn = next(b for b in app.button if b.label == "Submit Transfer Prediction")
                submit_btn.click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["session"]["followup_status"], "correct_on_prepared_question")
                self.assertTrue(app.session_state["session"]["transfer_correct"])
                self.assertEqual(app.session_state["session"]["transfer_prediction"], "[1, 2]")
                self.assertTrue(any("Spot on!" in item.value for item in app.success))

    def test_31b_http_500_auto_recovery_ui(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"DATA_DIR": directory}):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
                saved = {
                    "schema_version": 1,
                    "id": "errsession789",
                    "exercise_id": "basket",
                    "exercise_version": 1,
                    "concept": "Shared mutable state",
                    "started_at": "2026-10-11T00:00:00Z",
                    "updated_at": "2026-10-11T00:05:00Z",
                    "stage": "guide",
                    "code": BASKET.starter,
                    "code_hash": "starterhash",
                    "verified_hash": None,
                    "prediction": '["banana"]',
                    "confidence": 3,
                    "explanation": "test reason",
                    "initial_observation": ["apple", "banana"],
                    "prediction_matches_execution": False,
                    "messages": [{"role": "assistant", "text": "Exercise hint", "source": "Exercise hint · live Gemma unavailable"}],
                    "runs": [],
                    "events": [{"type": "model_unavailable", "error": "HTTP 500: Model service internal error. If using gemma-4-31b-it, switch to gemma-4-26b-a4b-it."}],
                    "attempts": 0,
                    "hint_level": 0,
                    "hint_count": 0,
                    "solution_viewed": False,
                    "outcome": "in_progress",
                    "model_calls": 0,
                    "model_unavailable_events": 1,
                    "followup_status": "not_attempted",
                }
                (Path(directory) / "errsession789.json").write_text(json.dumps(saved))
                app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=15).run()
                self.assertFalse(app.exception)
                app.selectbox(key="gemma_model_select").set_value("gemma-4-31b-it").run()
                self.assertFalse(app.exception)
                app.button(key="load_session_btn").click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["session"]["stage"], "guide")

                # Verify actionable warning is rendered
                self.assertTrue(any("Gemma 31B encountered an upstream server error (HTTP 500)" in item.value for item in app.warning))

                # Verify recovery button is present and click it
                switch_btn = next(b for b in app.button if "Switch to Gemma 26B" in b.label)
                switch_btn.click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["gemma_model_select"], "gemma-4-26b-a4b-it")


if __name__ == "__main__":
    unittest.main()
