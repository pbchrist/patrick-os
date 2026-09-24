import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from patrick_os import jev
from tests.support import REPO


class JevProfileTest(unittest.TestCase):
    def test_reviewer_profile_has_both_batch_phases(self):
        profile = jev.load_profile("reviewer-outreach", REPO)
        self.assertEqual(profile["model"], "jev-latest")
        self.assertEqual(profile["max_batch_items"], 20)
        self.assertIn("candidate", profile["phases"])
        self.assertIn("draft", profile["phases"])

    def test_deterministic_blocker_skips_semantic_questions_for_item(self):
        profile = jev.load_profile("reviewer-outreach", REPO)
        payload, meta = jev.build_request(profile, "candidate", [
            {"reviewer": "A", "deterministic_blockers": ["already sent"]},
            {"reviewer": "B"},
        ])
        self.assertEqual(len(payload["questions"]), 4)
        self.assertEqual(meta["immediate"][0]["verdict"], "block")
        self.assertTrue(all(key.startswith("i001__") for key in payload["questions"]))

    def test_batch_is_one_request_with_all_questions(self):
        seen = []
        state = [{"reviewer": "A"}, {"reviewer": "B"}, {"reviewer": "C"}]

        def transport(payload):
            seen.append(payload)
            answers = {}
            for key, question in payload["questions"].items():
                if question["type"] == "noul":
                    answers[key] = {"type": "noul", "noul": 0.99}
                else:
                    answers[key] = {
                        "type": "score", "score": 1.8,
                        "legend": {"0": "x", "1": "y", "2": "z"},
                        "probabilities": {"0": 0.0, "1": 0.2, "2": 0.8},
                        "confidence": 0.8,
                    }
            return {"model": "jev-test", "answers": answers,
                    "usage": {"input_tokens": 100, "output_tokens": 40}}

        result = jev.gate("reviewer-outreach", "candidate", state,
                          execute=True, base=REPO, transport=transport)
        self.assertEqual(len(seen), 1)
        self.assertEqual(result["question_count"], 12)
        self.assertEqual(result["verdict"], "pass")
        self.assertTrue(all(item["verdict"] == "pass" for item in result["items"]))

    def test_uncertain_semantic_answer_routes_to_review(self):
        def transport(payload):
            answers = {}
            for key, question in payload["questions"].items():
                if question["type"] == "noul":
                    answers[key] = {"type": "noul", "noul": 0.99}
                else:
                    answers[key] = {
                        "type": "score", "score": 0.90,
                        "legend": {"0": "x", "1": "y", "2": "z"},
                        "probabilities": {"0": 0.1, "1": 0.9, "2": 0.0},
                        "confidence": 0.7,
                    }
            return {"model": "jev-test", "answers": answers, "usage": {}}

        result = jev.gate("reviewer-outreach", "draft", {"draft": "x"},
                          execute=True, base=REPO, transport=transport)
        self.assertEqual(result["verdict"], "review")
        self.assertEqual(result["items"][0]["questions"]["human_tone"]["verdict"], "review")

    def test_missing_api_key_fails_closed(self):
        payload = {"state": {}, "model": "jev-latest", "questions": {
            "x": {"type": "noul", "instructions": "Is x true?"}
        }}
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(jev.JevError) as caught:
                jev.evaluate(payload)
        self.assertIn("fails closed", str(caught.exception))

    def test_batch_limit_is_enforced_before_network(self):
        profile = jev.load_profile("reviewer-outreach", REPO)
        with self.assertRaises(jev.JevError):
            jev.build_request(profile, "candidate", [{"n": i} for i in range(21)])


if __name__ == "__main__":
    unittest.main()
