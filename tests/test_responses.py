import json
from io import BytesIO
import unittest
from unittest.mock import patch

from core import check_correction, decide, new_session, sync_code
from exercises import BASKET
from runner import Runner
from tutor import Gemma, InvalidResponse, ModelError, context_for, parse_decision


ANSWER = {"action": "ask_question", "message": "Which values contributed to that result?",
          "case_id": None, "evidence_ids": []}


class ReplySequence:
    model = "test-double"

    def __init__(self, replies):
        self.replies = iter(replies)
        self.contexts = []

    def decide(self, context):
        self.contexts.append(context)
        answer = next(self.replies)
        if isinstance(answer, Exception):
            raise answer
        return answer, 1


class ResponseTests(unittest.TestCase):
    def setUp(self):
        self.session = new_session(BASKET)
        self.context = context_for(self.session, BASKET, "test", ["ask_question"], [])

    def test_accepts_common_fences_and_bom(self):
        raw = json.dumps(ANSWER)
        for text in [raw, "\ufeff" + raw, "```\n" + raw + "\n```",
                     "```JSON\r\n" + raw + "\r\n```", "```json\n" + raw + "\n```"]:
            with self.subTest(text=text):
                self.assertEqual(parse_decision(text, self.context), ANSWER)

    def test_does_not_salvage_arbitrary_prose_or_truncated_objects(self):
        raw = json.dumps(ANSWER)
        for text in ["Here is my answer: " + raw, raw[:-2], raw + raw,
                     "```json\n" + raw + "\n```\nAlso change your code."]:
            with self.assertRaises(InvalidResponse):
                parse_decision(text, self.context)

    def test_repair_uses_same_evidence_and_displays_only_valid_reply(self):
        model = ReplySequence(["not JSON", json.dumps(ANSWER)])
        item = decide(self.session, BASKET, model, "test", ["ask_question"])
        self.assertEqual(item, ANSWER)
        self.assertEqual(len(model.contexts), 2)
        for key in ["current_code", "confidence", "evidence", "allowed_actions", "allowed_case_ids"]:
            self.assertEqual(model.contexts[0][key], model.contexts[1][key])
        self.assertIn("response_retry", model.contexts[1])
        self.assertEqual(len(self.session["messages"]), 1)
        self.assertTrue(self.session["messages"][0]["source"].startswith("Gemma"))
        self.assertEqual(self.session["model_requests"], 2)

    def test_two_failures_get_honest_format_label_and_stop(self):
        model = ReplySequence(["bad", "still bad"])
        self.assertIsNone(decide(self.session, BASKET, model, "test", ["ask_question"]))
        self.assertEqual(len(model.contexts), 2)
        self.assertEqual(self.session["messages"][-1]["source"], "Exercise hint · model response could not be used")
        self.assertEqual(self.session["model_calls"], 0)
        self.assertNotIn("bad", json.dumps(self.session["events"]))

    def test_connectivity_failure_does_not_trigger_format_retry(self):
        model = ReplySequence([ModelError("HTTP 429: quota")])
        decide(self.session, BASKET, model, "test", ["ask_question"])
        self.assertEqual(len(model.contexts), 1)
        self.assertIn("unavailable", self.session["messages"][-1]["source"])

    def test_repaired_challenge_cannot_cause_a_third_call(self):
        selection = {**ANSWER, "action": "run_case", "case_id": "provided_empty"}
        model = ReplySequence(["bad", json.dumps(selection)])
        sync_code(self.session, BASKET.solution)
        check_correction(self.session, BASKET, Runner("trusted-local", allow_trusted=True), model)
        self.assertEqual(len(model.contexts), 2)
        self.assertEqual(self.session["verified_hash"], self.session["code_hash"])
        self.assertEqual(self.session["messages"][-1]["source"], "Exercise feedback · per-action request limit")
        self.assertIn("5 checked cases passed", self.session["messages"][-1]["text"])

    def test_retry_cannot_bypass_action_validation(self):
        dangerous = {**ANSWER, "action": "run_case", "case_id": "shell"}
        model = ReplySequence(["bad", json.dumps(dangerous)])
        self.assertIsNone(decide(self.session, BASKET, model, "test", ["ask_question"]))
        self.assertEqual(self.session["runs"], [])

    def test_truncated_transport_reply_is_detected(self):
        body = {"candidates": [{"finishReason": "MAX_TOKENS",
                                "content": {"parts": [{"text": '{"action":'}]}}]}
        model = Gemma(key="test-key")
        with patch("tutor.request.urlopen", return_value=BytesIO(json.dumps(body).encode())):
            with self.assertRaises(InvalidResponse):
                model.decide(self.context)
        self.assertEqual(model.last_response_info["finish_reason"], "MAX_TOKENS")
        self.assertNotIn("test-key", json.dumps(model.last_response_info))


if __name__ == "__main__":
    unittest.main()
