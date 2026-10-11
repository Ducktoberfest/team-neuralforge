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


if __name__ == "__main__":
    unittest.main()
