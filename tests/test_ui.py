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


if __name__ == "__main__":
    unittest.main()
