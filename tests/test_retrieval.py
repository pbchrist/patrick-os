"""Retrieval, and the capability-probing that keeps it honest.

Patrick OS once reported that autonomous Reddit research was impossible. That was
measured against a Hermes install with no web backend and stated as a fact about
the world. A second install on the same tailnet -- v0.20.4, web/search/browser
toolsets, Tavily search -- retrieves Reddit fine. These tests exist so capability
is discovered per runtime and never generalized again.
"""

import json
import unittest
from unittest import mock

from patrick_os import retrieval, skills

from tests.support import REPO

V20 = """Hermes Agent v0.20.4 (2026.8.18)
---CONFIG---
model:
  default: gpt-5.6-sol
  provider: openai-codex
toolsets:
- hermes-cli
- web
- search
- browser
web:
  backend: tavily
  search_backend: tavily
  extract_backend: browser
"""

V13 = """Hermes Agent v0.13.0
---CONFIG---
model:
  default: Qwen_Qwen3.6-27B-Q4_K_M.gguf
toolsets:
- hermes-cli
"""


class Completed:
    def __init__(self, stdout, returncode=0):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


def runtime(key="r", **config):
    config.setdefault("transport", "local")
    return retrieval.Runtime(key, config)


class CapabilityProbeTest(unittest.TestCase):
    def probe(self, output):
        target = runtime()
        with mock.patch.object(target, "run", return_value=Completed(output)):
            return retrieval.probe_runtime(target)

    def test_a_web_capable_runtime_is_detected(self):
        capability = self.probe(V20)
        self.assertTrue(capability.reachable)
        self.assertEqual(capability.version, "0.20.4")
        self.assertEqual(capability.search_backend, "tavily")
        self.assertEqual(capability.extract_backend, "browser")
        self.assertTrue(capability.can_web_research)

    def test_a_runtime_without_web_toolsets_is_not_web_capable(self):
        capability = self.probe(V13)
        self.assertTrue(capability.reachable)
        self.assertEqual(capability.version, "0.13.0")
        self.assertFalse(capability.can_web_research)

    def test_one_runtimes_limits_are_never_generalized_to_another(self):
        """The actual mistake, as a test: two runtimes, opposite answers."""
        capable = self.probe(V20)
        incapable = self.probe(V13)
        self.assertNotEqual(capable.can_web_research, incapable.can_web_research)

    def test_an_unreachable_runtime_reports_why(self):
        target = runtime()
        with mock.patch.object(target, "run", side_effect=OSError("no route to host")):
            capability = retrieval.probe_runtime(target)
        self.assertFalse(capability.reachable)
        self.assertIn("no route to host", capability.detail)

    def test_choosing_a_runtime_names_what_each_one_lacked(self):
        caps = {"a": retrieval.Capability("a", reachable=True, toolsets=["hermes-cli"],
                                          detail="no web"),
                "b": retrieval.Capability("b", reachable=False, detail="unreachable")}
        with self.assertRaises(retrieval.RetrievalError) as caught:
            retrieval.choose_runtime("web_research", capabilities=caps)
        self.assertIn("no web", str(caught.exception))
        self.assertIn("unreachable", str(caught.exception))


class SearchFirstContractTest(unittest.TestCase):
    def test_the_worker_is_told_to_search_first_and_never_raw_fetch(self):
        contract = retrieval.SEARCH_FIRST_CONTRACT
        self.assertIn("Use web search", contract)
        self.assertIn("Never begin by raw-fetching", contract)
        self.assertIn("does not\nmean the material is unavailable", contract)

    def test_the_contract_demands_original_permalinks(self):
        contract = retrieval.SEARCH_FIRST_CONTRACT
        self.assertIn("ORIGINAL permalink", contract)
        self.assertIn("never write a URL you did not receive from a tool", contract)

    def test_retrieval_does_not_disable_the_config_that_enables_its_toolsets(self):
        """The isolation flags Patrick OS uses for judging would switch off the
        web toolsets, which are declared in config.yaml. Asserted against the
        command actually built, not against the source text -- the source
        mentions those flags in order to explain why it omits them."""
        sent = {}
        target = runtime("hermes-beastmaster")
        capability = retrieval.Capability(
            "hermes-beastmaster", reachable=True,
            toolsets=["hermes-cli", "web", "search", "browser"], search_backend="tavily")

        def fake_run(command, **kwargs):
            sent["command"] = command
            return Completed('{"items": [], "notes": "n"}')

        with mock.patch.object(retrieval, "runtimes", return_value={"hermes-beastmaster": target}), \
             mock.patch.object(target, "run", side_effect=fake_run):
            retrieval.hermes_web("q", runtime_key="hermes-beastmaster",
                                 capabilities={"hermes-beastmaster": capability})
        built = sent["command"]
        self.assertNotIn("--ignore-user-config", built)
        self.assertNotIn("--safe-mode", built)
        self.assertIn("-t web,search,browser", built)
        self.assertIn("--query-file", built)


class BackendChainTest(unittest.TestCase):
    def test_an_empty_result_falls_through_to_the_next_backend(self):
        """An empty result caused by one agent's query timing out is not the same
        finding as 'there is nothing there'."""
        calls = []

        def empty(query, **kwargs):
            calls.append("empty")
            return {"items": [], "notes": "timed out"}

        def full(query, **kwargs):
            calls.append("full")
            return {"items": [{"url": "u"}], "notes": "ok"}

        with mock.patch.dict(retrieval.BACKENDS, {"a": empty, "b": full}, clear=True):
            payload = retrieval.retrieve("q", backend="a", chain=["b"])
        self.assertEqual(calls, ["empty", "full"])
        self.assertEqual(payload["_backend"], "b")

    def test_a_successful_backend_stops_the_chain(self):
        calls = []

        def full(query, **kwargs):
            calls.append("full")
            return {"items": [{"url": "u"}]}

        def never(query, **kwargs):
            calls.append("never")
            return {"items": []}

        with mock.patch.dict(retrieval.BACKENDS, {"a": full, "b": never}, clear=True):
            retrieval.retrieve("q", backend="a", chain=["b"])
        self.assertEqual(calls, ["full"])

    def test_every_attempt_is_recorded_even_when_all_are_empty(self):
        def empty(query, **kwargs):
            return {"items": [], "notes": "nothing"}

        with mock.patch.dict(retrieval.BACKENDS, {"a": empty, "b": empty}, clear=True):
            payload = retrieval.retrieve("q", backend="a", chain=["b"])
        self.assertEqual([a["backend"] for a in payload["_attempts"]], ["a", "b"])
        self.assertEqual(payload["items"], [])


class ArchiveBackendTest(unittest.TestCase):
    def test_permalinks_are_absolute_and_deleted_bodies_are_dropped(self):
        rows = {"data": [
            {"permalink": "/r/x/comments/1/a/", "author": "u1", "created_utc": 1780000000,
             "body": "real text"},
            {"permalink": "/r/x/comments/2/b/", "author": "u2", "created_utc": 1780000000,
             "body": "[deleted]"},
        ]}

        class Response:
            def __enter__(self_inner):
                return self_inner
            def __exit__(self_inner, *args):
                return False
            def read(self_inner):
                return json.dumps(rows).encode()

        with mock.patch("urllib.request.urlopen", return_value=Response()):
            payload = retrieval.reddit_archive("q", subreddit="x", limit=2)
        urls = [i["url"] for i in payload["items"]]
        self.assertTrue(all(u.startswith("https://www.reddit.com/") for u in urls))
        self.assertTrue(all("[deleted]" not in i["text"] for i in payload["items"]))

    def test_the_archive_path_invokes_no_runtime(self):
        """Deterministic where hermes-web is not: the same hermes-web request
        returned 12 items on one run and 0 on the next. Asserted by proving no
        runtime is driven, rather than by grepping for words."""
        class Response:
            def __enter__(self_inner):
                return self_inner
            def __exit__(self_inner, *args):
                return False
            def read(self_inner):
                return b'{"data": []}'

        with mock.patch.object(retrieval, "runtimes") as runtimes_called, \
             mock.patch.object(retrieval, "probe_all") as probe_called, \
             mock.patch("urllib.request.urlopen", return_value=Response()):
            retrieval.reddit_archive("q", subreddit="x", limit=1)
        runtimes_called.assert_not_called()
        probe_called.assert_not_called()

    def test_a_subreddit_is_required_and_inferred_from_the_query(self):
        with self.assertRaises(retrieval.RetrievalError):
            retrieval.reddit_archive("no subreddit here")


class RunnerWiringTest(unittest.TestCase):
    """The retrieval path must be exercised in-process, not only end to end.

    A refactor dropped Skill.bind_partial and every test still passed, because
    nothing called the runner's gather() without a live network. The end-to-end
    run caught it; a unit test should have.
    """

    def test_bind_partial_tolerates_the_not_yet_retrieved_input(self):
        skill = skills.load_skill("reddit-mine", REPO)
        bound = skill.bind_partial({"subreddit": "x", "pain_hypothesis": "y"})
        self.assertEqual(bound["subreddit"], "x")
        self.assertEqual(bound["window_days"], 14)
        self.assertNotIn("retrieved_material", bound)

    def test_gather_interpolates_the_query_and_records_provenance(self):
        from patrick_os import runner
        skill = skills.load_skill("reddit-mine", REPO)
        captured = {}

        def fake_retrieve(query, **kwargs):
            captured["query"] = query
            captured["kwargs"] = kwargs
            return {"items": [{"url": "u"}], "notes": "n", "_backend": "reddit-archive"}

        with mock.patch("patrick_os.retrieval.retrieve", side_effect=fake_retrieve):
            payload, provenance = runner.gather(
                skill, skill.bind_partial({"subreddit": "passive_income",
                                           "pain_hypothesis": "h"}), base=REPO)
        self.assertIn("r/passive_income", captured["query"])
        self.assertEqual(captured["kwargs"]["subreddit"], "passive_income")
        self.assertEqual(provenance["backend"], "reddit-archive")
        self.assertEqual(provenance["item_count"], 1)


class RegistryTest(unittest.TestCase):
    def registry(self):
        return json.loads((REPO / "config" / "retrieval.json").read_text())

    def test_both_runtimes_are_declared_and_distinguished(self):
        runtimes = self.registry()["runtimes"]
        self.assertIn("hermes-beastmaster", runtimes)
        self.assertIn("hermes-mac", runtimes)

    def test_direct_fetch_is_recorded_blocked_but_is_not_the_default(self):
        source = self.registry()["sources"]["reddit"]
        self.assertEqual(source["backends"]["direct-fetch"]["status"], "blocked")
        self.assertNotEqual(source["default_backend"], "direct-fetch")

    def test_reddit_api_is_optional_and_not_the_default(self):
        """It is a structured fallback, never a prerequisite."""
        source = self.registry()["sources"]["reddit"]
        self.assertEqual(source["backends"]["reddit-api"]["status"], "declared")
        self.assertNotEqual(source["default_backend"], "reddit-api")
        self.assertLess(source["backend_order"].index("hermes-web"),
                        source["backend_order"].index("reddit-api"))

    def test_manual_export_is_the_last_resort(self):
        self.assertEqual(self.registry()["sources"]["reddit"]["backend_order"][-1],
                         "manual-export")


class SkillWiringTest(unittest.TestCase):
    def test_reddit_mine_declares_a_source_and_does_not_fetch_itself(self):
        skill = skills.load_skill("reddit-mine", REPO)
        self.assertEqual(skill.retrieval_source, "reddit")
        self.assertIn("{{ subreddit }}", skill.retrieval_query)
        self.assertIn("retrieved_material", {i["name"] for i in skill.inputs})
        self.assertIn("does not fetch anything", skill.section("Prerequisites"))

    def test_the_retrieval_query_asks_for_contradicting_material(self):
        """A query phrased as the hypothesis finds the hypothesis."""
        skill = skills.load_skill("reddit-mine", REPO)
        self.assertIn("CONTRADICT", skill.retrieval_query)


if __name__ == "__main__":
    unittest.main()
