from __future__ import annotations

import json
import os
import unittest
from unittest import mock

from patrick_os import retrieval, runner, skills


class RedditRetrievalTest(unittest.TestCase):
    def test_missing_credentials_is_explicit(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(retrieval.RetrievalError) as ctx:
                retrieval.fetch_reddit("passive_income")
        self.assertIn("REDDIT_CLIENT_ID", str(ctx.exception))
        self.assertIn("REDDIT_CLIENT_SECRET", str(ctx.exception))

    def test_runner_injects_retrieval_failure_before_worker(self):
        skill = skills.load_skill("reddit-mine")
        planned = runner.plan(skill, {
            "subreddit": "passive_income",
            "pain_hypothesis": "test hypothesis",
            "retrieval_backend": "reddit-api",
        })
        material = planned["inputs"]["retrieved_material"]
        payload = json.loads(material)
        self.assertEqual(payload["backend"], "reddit-api")
        self.assertIn("retrieval_error", payload)
        self.assertIn("Analyze the source bundle supplied", planned["work_order"])

    def test_manual_export_is_not_retrieved(self):
        skill = skills.load_skill("reddit-mine")
        planned = runner.plan(skill, {
            "subreddit": "passive_income",
            "pain_hypothesis": "test hypothesis",
            "retrieved_material": "PASTED THREAD",
        })
        self.assertEqual(planned["inputs"]["retrieved_material"], "PASTED THREAD")


if __name__ == "__main__":
    unittest.main()
