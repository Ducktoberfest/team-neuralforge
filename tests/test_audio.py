"""Unit tests for the DuckTutor sound effects and audio engine."""

import base64
import unittest
import wave
import io

from sound_effects import AVAILABLE_SOUNDS, get_sound_data_uri, synthesize_wav


class AudioTests(unittest.TestCase):
    def test_all_sounds_synthesize_valid_wav(self):
        for sound_name in AVAILABLE_SOUNDS:
            with self.subTest(sound=sound_name):
                raw = synthesize_wav(sound_name)
                self.assertTrue(len(raw) > 1000, f"Sound {sound_name} too short")
                self.assertTrue(raw.startswith(b"RIFF"), f"Sound {sound_name} not valid RIFF header")
                # Parse as wave
                with wave.open(io.BytesIO(raw), "rb") as wf:
                    self.assertEqual(wf.getnchannels(), 1)
                    self.assertEqual(wf.getsampwidth(), 2)
                    self.assertEqual(wf.getframerate(), 22050)
                    self.assertGreater(wf.getnframes(), 2000)

    def test_sound_data_uri_format(self):
        uri = get_sound_data_uri("quack")
        self.assertTrue(uri.startswith("data:audio/wav;base64,"))
        payload = uri[len("data:audio/wav;base64,"):]
        decoded = base64.b64decode(payload)
        self.assertTrue(decoded.startswith(b"RIFF"))

    def test_unknown_sound_raises_value_error(self):
        with self.assertRaises(ValueError):
            synthesize_wav("unknown_quack_type")  # type: ignore

    def test_squeeze_duck_button_and_audio_toggle_in_app(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from streamlit.testing.v1 import AppTest

        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"DATA_DIR": directory}):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
                app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=15).run()
                self.assertFalse(app.exception)
                # Verify squeeze button exists
                squeeze_btn = next((b for b in app.button if b.key == "squeeze_duck_btn"), None)
                self.assertIsNotNone(squeeze_btn, "squeeze_duck_btn should be present")
                squeeze_btn.click().run()
                self.assertFalse(app.exception)
                # Verify duck_audio_enabled checkbox exists
                audio_chk = next((c for c in app.checkbox if c.key == "duck_audio_enabled"), None)
                self.assertIsNotNone(audio_chk, "duck_audio_enabled should be present")
                self.assertTrue(audio_chk.value)


if __name__ == "__main__":
    unittest.main()
