"""Routing must be decidable with no keys, no network, and no model running.

Every test here builds a table in memory or loads the shipped one and asserts on
the decision only -- if any of these ever needs a credential, the abstraction has
leaked and Patrick OS is no longer model-agnostic.
"""

import unittest

from patrick_os.router import TaskSpec, resolve
from patrick_os.router.table import RouteTable, RouteTableError
from patrick_os.router import table as route_table

from tests.support import REPO


def table(**overrides):
    data = {
        "providers": {
            "cheap-local": {
                "adapter": "openai_http", "model": "q", "local": True,
                "capabilities": ["text"], "quality": 2, "cost_per_1k": 0.0,
                "latency_class": "fast", "max_request_bytes": 1000,
            },
            "mid": {
                "adapter": "hermes_cli", "model": "m", "capabilities": ["text", "judge"],
                "supports_tools": True, "quality": 4, "cost_per_1k": 0.0,
                "latency_class": "slow",
            },
            "expensive": {
                "adapter": "anthropic_api", "model": "e",
                "capabilities": ["text", "judge", "long-context"],
                "supports_tools": True, "quality": 5, "cost_per_1k": 15.0,
                "latency_class": "medium",
            },
        },
        "routes": [{"task_class": "draft", "prefer": ["cheap-local", "mid"]}],
        "default": {"prefer": ["mid"]},
    }
    data.update(overrides)
    return RouteTable(data)


class ResolveTest(unittest.TestCase):
    def test_prefer_order_is_authoritative(self):
        """A route that names cheap-local first must get cheap-local, even though
        every other provider scores higher on quality. Preference is a decision,
        not a hint, and quality must never silently reorder it."""
        decision = resolve(TaskSpec("draft"), table())
        self.assertEqual(decision.chosen.key, "cheap-local")
        self.assertEqual([c.key for c in decision.candidates][:2], ["cheap-local", "mid"])

    def test_unnamed_providers_rank_below_named_ones(self):
        decision = resolve(TaskSpec("draft"), table())
        self.assertEqual(decision.candidates[-1].key, "expensive")

    def test_longest_prefix_wins(self):
        t = table(routes=[
            {"task_class": "draft", "prefer": ["cheap-local"]},
            {"task_class": "draft.email", "prefer": ["expensive"]},
        ])
        self.assertEqual(resolve(TaskSpec("draft.email"), t).route_name, "draft.email")
        self.assertEqual(resolve(TaskSpec("draft.reply"), t).route_name, "draft")

    def test_unmatched_class_falls_to_default(self):
        decision = resolve(TaskSpec("nothing.like.this"), table())
        self.assertEqual(decision.route_name, "default")
        self.assertEqual(decision.chosen.key, "mid")

    def test_payload_cap_fails_over_instead_of_erroring(self):
        """The local endpoint's 24k request-body cap is a routing fact. A work
        order over the limit must route elsewhere, not fail at the socket."""
        decision = resolve(TaskSpec("draft", payload_bytes=5000), table())
        self.assertEqual(decision.chosen.key, "mid")
        reasons = {r.provider_key: r.reason for r in decision.rejected}
        self.assertIn("exceeds provider limit", reasons["cheap-local"])

    def test_cost_cap_rejects_with_a_reason(self):
        t = table(routes=[{"task_class": "draft", "prefer": ["expensive", "mid"],
                           "max_cost_per_1k": 1.0}])
        decision = resolve(TaskSpec("draft"), t)
        self.assertEqual(decision.chosen.key, "mid")
        self.assertIn("above cap", {r.provider_key: r.reason for r in decision.rejected}["expensive"])

    def test_privacy_forces_local(self):
        decision = resolve(TaskSpec("draft", privacy="local-only"), table())
        self.assertEqual([c.key for c in decision.candidates], ["cheap-local"])

    def test_capability_and_tool_filters(self):
        t = table()
        self.assertNotIn("cheap-local",
                         {c.key for c in resolve(TaskSpec("draft", needs_capabilities=["judge"]), t).candidates})
        self.assertNotIn("cheap-local",
                         {c.key for c in resolve(TaskSpec("draft", needs_tools=True), t).candidates})

    def test_no_eligible_provider_yields_no_choice_not_an_exception(self):
        decision = resolve(TaskSpec("draft", min_quality=99), table())
        self.assertIsNone(decision.chosen)
        self.assertEqual(len(decision.rejected), 3)

    def test_decision_is_serialisable(self):
        payload = resolve(TaskSpec("draft"), table()).as_dict()
        self.assertEqual(payload["chosen"]["provider"], "cheap-local")
        self.assertTrue(payload["chosen"]["reasons"])


class ShippedTableTest(unittest.TestCase):
    def setUp(self):
        self.table = route_table.load(REPO / "config" / "routes.json")

    def test_the_judge_route_offers_more_than_one_vendor(self):
        """SF-07 restated correctly. The old version of this test denied
        local-qwen in the judge route, which encoded an assumption that local was
        always the writer. Once the topology was audited, local llama.cpp turned
        out to be one of only two reachable vendors -- denying it would have
        removed the strongest independent judge available. The invariant is that
        the route can express a different-vendor pair, not that any one provider
        is excluded."""
        decision = resolve(TaskSpec("judge.copy"), self.table)
        vendors = {c.provider.vendor for c in decision.candidates}
        self.assertGreaterEqual(len(vendors), 2,
                                "the judge route must be able to offer two vendors")

    def test_the_judge_of_a_writer_is_never_that_writer(self):
        from patrick_os import judging
        for writer in self.table.providers:
            candidates, _ = judging.independent_candidates(writer, table=self.table)
            self.assertNotIn(writer, [c.key for c in candidates])

    def test_private_route_keeps_work_on_local_hardware(self):
        decision = resolve(TaskSpec("private.client-audit"), self.table)
        self.assertTrue(decision.candidates)
        for candidate in decision.candidates:
            self.assertTrue(candidate.provider.local,
                            f"{candidate.key} is not local; client material must not leave")

    def test_research_stays_free(self):
        decision = resolve(TaskSpec("research.mine"), self.table)
        self.assertEqual(decision.chosen.key, "local-qwen")
        self.assertEqual(decision.chosen.provider.cost_per_1k, 0.0)
        for candidate in decision.candidates:
            self.assertEqual(candidate.provider.cost_per_1k, 0.0)

    def test_local_endpoint_declares_its_measured_body_cap(self):
        """Was 24000, borrowed from the Cloudflare tunnel narrative-sourcing uses.
        That is a different route to the same box. 65536 was measured against
        this endpoint directly on 2026-09-04."""
        self.assertEqual(self.table.providers["local-qwen"].max_request_bytes, 65536)

    def test_openai_provider_does_not_reuse_the_local_api_key_variable(self):
        """OPENAI_API_KEY is set to the literal 'local' for the Qwen server in
        Site Factory's .env. Reusing it here would send a junk key to OpenAI."""
        self.assertNotEqual(
            self.table.providers["openai-api"].config["api_key_env"], "OPENAI_API_KEY"
        )

    def test_no_credential_value_is_stored_in_the_table(self):
        import json
        raw = json.loads((REPO / "config" / "routes.json").read_text())
        for key, provider in raw["providers"].items():
            for field, value in provider.items():
                if field == "api_key":
                    self.assertEqual(value, "local", f"{key} stores a real key in config")
                if isinstance(value, str):
                    self.assertFalse(value.startswith(("sk-", "sk_", "gho_")),
                                     f"{key}.{field} looks like a credential")


class TableValidationTest(unittest.TestCase):
    def test_unknown_preferred_provider_is_rejected(self):
        with self.assertRaises(RouteTableError):
            RouteTable({"providers": {"a": {"adapter": "openai_http"}},
                        "routes": [{"task_class": "x", "prefer": ["nope"]}]})

    def test_empty_provider_set_is_rejected(self):
        with self.assertRaises(RouteTableError):
            RouteTable({"providers": {}, "routes": []})


class AdapterImportTest(unittest.TestCase):
    def test_importing_adapters_package_pulls_in_no_vendor_sdk(self):
        """Patrick OS must run on a machine with no anthropic/openai package
        installed. Importing the registry must not change that."""
        import sys
        from patrick_os.router import adapters  # noqa: F401
        for module in ("anthropic", "openai"):
            self.assertNotIn(module, sys.modules, f"{module} was imported eagerly")

    def test_hermes_argv_matches_the_installed_cli(self):
        """Site Factory's invocation passes --reasoning/--safe-mode/--query-file,
        which hermes v0.13.0 rejects with exit 2. Assert the argv this CLI
        actually accepts, so a drift fails here rather than at runtime."""
        from patrick_os.router.adapters import hermes_cli
        from patrick_os.router.spec import Provider
        provider = Provider("hermes-copilot", {
            "adapter": "hermes_cli", "model": "gpt-5.6-sol", "command": "/bin/echo",
            "hermes_provider": "openai-codex",
        })
        argv = hermes_cli.build_argv(provider, "PROMPT")
        self.assertEqual(argv[1:], [
            "chat", "-Q", "--provider", "openai-codex", "-m", "gpt-5.6-sol",
            "--source", "tool", "--max-turns", "1",
            "--ignore-rules", "--ignore-user-config", "-q", "PROMPT",
        ])

    def test_hermes_isolation_flags_can_be_turned_off_by_config_not_by_code(self):
        from patrick_os.router.adapters import hermes_cli
        from patrick_os.router.spec import Provider
        provider = Provider("h", {"adapter": "hermes_cli", "command": "/bin/echo",
                                  "isolate": False, "extra_args": ["--yolo"]})
        argv = hermes_cli.build_argv(provider, "P")
        self.assertNotIn("--ignore-rules", argv)
        self.assertIn("--yolo", argv)

    def test_oversized_prompt_is_refused_before_exec(self):
        from patrick_os.router.adapters import hermes_cli
        from patrick_os.router.spec import Provider
        provider = Provider("h", {"adapter": "hermes_cli", "command": "/bin/echo"})
        with self.assertRaises(hermes_cli.TransportError):
            hermes_cli.complete(provider, "x" * (hermes_cli.MAX_PROMPT_BYTES + 1))


if __name__ == "__main__":
    unittest.main()
