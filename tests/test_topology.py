"""The provider topology, pinned.

Written after an audit found that `local-qwen` had been "connection refused" for
one reason only: the endpoint was 127.0.0.1:8082, copied from Site Factory's
.env.example, which assumes you run ON the inference box. The service was fine.
The conclusion drawn from that -- that another paid provider was needed -- was
wrong, and these tests exist so the same class of mistake fails loudly.
"""

import json
import unittest

from patrick_os import judging
from patrick_os.router import table as route_table
from patrick_os.router.spec import Provider

from tests.support import REPO


def table():
    return route_table.load(REPO / "config" / "routes.json")


class EndpointTest(unittest.TestCase):
    def test_no_provider_points_at_localhost(self):
        """The inference servers run on another machine. A loopback address in
        this table means someone copied a config that assumed otherwise."""
        raw = json.loads((REPO / "config" / "routes.json").read_text())
        for key, config in raw["providers"].items():
            url = str(config.get("base_url", ""))
            for loopback in ("127.0.0.1", "localhost", "::1"):
                self.assertNotIn(loopback, url,
                                 f"{key} points at {loopback}; llama.cpp is remote")

    def test_the_local_endpoint_is_the_verified_one(self):
        provider = table().providers["local-qwen"]
        self.assertEqual(provider.config["base_url"], "http://100.73.250.50:8082/v1")
        self.assertTrue(provider.local)

    def test_the_measured_payload_cap_replaced_the_borrowed_one(self):
        """24000 was the Cloudflare tunnel's cap, a different route to the same
        box. 65536 was measured against this endpoint."""
        provider = table().providers["local-qwen"]
        self.assertEqual(provider.max_request_bytes, 65536)

    def test_every_provider_declares_a_vendor(self):
        for key, provider in table().providers.items():
            self.assertTrue(provider.config.get("vendor"),
                            f"{key} has no vendor; judge independence ranks on it")


class IndependenceRankingTest(unittest.TestCase):
    """Independence is a property of vendors, not of provider keys."""

    def provider(self, key, vendor):
        return Provider(key, {"adapter": "openai_http", "vendor": vendor})

    def test_a_different_vendor_outranks_a_second_model_from_one_vendor(self):
        writer = self.provider("w", "openai")
        self.assertEqual(judging.independence_of(self.provider("a", "local"), writer), 2)
        self.assertEqual(judging.independence_of(self.provider("b", "openai"), writer), 1)

    def test_the_writer_can_never_judge_itself(self):
        writer = self.provider("w", "openai")
        self.assertEqual(judging.independence_of(writer, writer), 0)

    def test_candidates_are_ordered_by_vendor_independence(self):
        strongest, _ = judging.independent_candidates("codex-cli", table=table())
        self.assertNotEqual(strongest[0].vendor, table().providers["codex-cli"].vendor,
                            "the top judge must be a different vendor when one exists")

    def test_every_declared_provider_has_a_different_vendor_judge_available(self):
        """Not about reachability -- about whether the table can express strong
        independence at all. If it cannot, no amount of credentials would help."""
        t = table()
        for key in t.providers:
            candidates, _ = judging.independent_candidates(key, table=t)
            best = judging.independence_of(candidates[0], t.providers[key])
            self.assertEqual(best, 2, f"{key} has no different-vendor judge declared")

    def test_two_vendors_are_reachable_without_any_paid_credential(self):
        """The audit's conclusion, pinned: local llama.cpp and the Codex CLI's
        existing ChatGPT OAuth are two distinct vendors, and neither is a
        purchase. Anthropic and the OpenAI pay-per-token path must stay optional."""
        t = table()
        free = {p.vendor for p in t.providers.values()
                if p.cost_per_1k == 0.0 and not p.config.get("api_key_env", "").startswith(
                    ("ANTHROPIC", "OPENAI_API_KEY_PATRICK"))}
        self.assertGreaterEqual(len(free), 2, f"only these free vendors: {free}")
        self.assertIn("local-llamacpp", free)

    def test_no_route_prefers_a_provider_that_requires_a_purchase(self):
        raw = json.loads((REPO / "config" / "routes.json").read_text())
        paid = {k for k, c in raw["providers"].items() if c.get("cost_per_1k", 0) > 0}
        for route in raw["routes"] + [raw["default"]]:
            prefer = route.get("prefer", [])
            for index, key in enumerate(prefer):
                if key in paid:
                    self.assertGreater(index, 0,
                                       f"route {route.get('task_class', 'default')!r} "
                                       f"prefers paid provider {key} first")


class AdapterTest(unittest.TestCase):
    def test_codex_adapter_is_registered_and_imports_no_sdk(self):
        import sys
        from patrick_os.router import adapters
        module = adapters.get("codex_cli")
        self.assertTrue(hasattr(module, "complete"))
        self.assertNotIn("openai", sys.modules)

    def test_codex_argv_is_read_only_and_repo_agnostic(self):
        from patrick_os.router.adapters import codex_cli
        provider = Provider("codex-cli", {"adapter": "codex_cli", "command": "/bin/echo"})
        argv = codex_cli.build_argv(provider, "PROMPT")
        self.assertIn("--sandbox", argv)
        self.assertEqual(argv[argv.index("--sandbox") + 1], "read-only")
        self.assertIn("--skip-git-repo-check", argv)
        self.assertEqual(argv[-1], "PROMPT")

    def test_codex_transcript_framing_is_stripped(self):
        from patrick_os.router.adapters import codex_cli
        raw = "Reply with exactly: OK\ncodex\nOK\ntokens used\n5,130\n"
        self.assertEqual(codex_cli.strip_transcript(raw).strip(), "OK")

    def test_every_adapter_can_report_reachability(self):
        """doctor called a dead endpoint 'ready' because a base_url was written
        down. Config presence is not readiness."""
        from patrick_os.router import adapters
        for name in adapters.REGISTRY:
            self.assertTrue(hasattr(adapters.get(name), "probe"),
                            f"{name} cannot be probed, so doctor would have to guess")


# Retrieval moved to tests/test_retrieval.py when the backend registry was
# reworked around capability probing. Keeping a thinner duplicate here would mean
# two places to update and one of them silently going stale.


if __name__ == "__main__":
    unittest.main()
