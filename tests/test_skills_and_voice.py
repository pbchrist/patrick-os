"""Skill parsing, input binding, voice composition, and work-order assembly."""

import unittest

from patrick_os import runner, skills, voice
from patrick_os.router import table as route_table

from tests.support import REPO, TempRootTest


class BindingTest(TempRootTest):
    def setUp(self):
        super().setUp()
        self.write_skill("demo")
        self.skill = skills.load_skill("demo", self.root)

    def test_defaults_fill_in(self):
        self.assertEqual(self.skill.bind({"topic": "x"}), {"topic": "x", "depth": 2})

    def test_missing_required_input_is_named(self):
        with self.assertRaises(skills.SkillError) as caught:
            self.skill.bind({})
        self.assertIn("missing required input(s): topic", str(caught.exception))

    def test_unknown_input_is_rejected_not_ignored(self):
        """A typo'd input silently dropped is a run that quietly did the wrong
        thing. Fail instead."""
        with self.assertRaises(skills.SkillError) as caught:
            self.skill.bind({"topic": "x", "dpeth": 3})
        self.assertIn("unknown input(s): dpeth", str(caught.exception))

    def test_sections_are_extracted(self):
        self.assertEqual(self.skill.section("Purpose"), "p")
        self.assertIn("Look at", self.skill.section("Procedure"))


class ValidationTest(TempRootTest):
    def test_missing_section_is_a_structural_failure(self):
        directory = self.write_skill("broken")
        text = (directory / "SKILL.md").read_text().replace("## Escalation\ne\n", "")
        (directory / "SKILL.md").write_text(text)
        problems = skills.load_skill("broken", self.root).validate()
        self.assertIn("missing section: ## Escalation", problems)

    def test_missing_fixtures_is_a_structural_failure(self):
        directory = self.write_skill("nofixtures")
        for file in (directory / "fixtures").glob("*.json"):
            file.unlink()
        self.assertIn("no regression fixtures under fixtures/",
                      skills.load_skill("nofixtures", self.root).validate())

    def test_name_must_match_directory(self):
        directory = self.write_skill("mismatch")
        text = (directory / "SKILL.md").read_text().replace("name: mismatch", "name: other")
        (directory / "SKILL.md").write_text(text)
        problems = skills.load_skill("mismatch", self.root).validate()
        self.assertTrue(any("does not match directory" in p for p in problems))

    def test_dry_run_cannot_be_defaulted_off(self):
        directory = self.write_skill("eager")
        text = (directory / "SKILL.md").read_text().replace(
            "dry_run_default: true", "dry_run_default: false")
        (directory / "SKILL.md").write_text(text)
        self.assertIn("dry_run_default must be true; dry run is the default everywhere",
                      skills.load_skill("eager", self.root).validate())


class VoiceCompositionTest(TempRootTest):
    def setUp(self):
        super().setUp()
        self.write_voice("global.md", "---\nscope: global\n---\n\n## Rules\n\n"
                                      "- [G-001] Global rule.\n")
        self.write_voice("channels/email.md", "---\nscope: channel:email\n---\n\n## Rules\n\n"
                                              "- [C-001] Email rule.\n")
        self.write_voice("skills/demo.md", "---\nscope: skill:demo\n---\n\n## Rules\n\n"
                                           "- [S-001] Skill rule.\n")

    def test_scopes_compose_general_to_specific(self):
        rules = voice.compose(["global", "channel:email", "skill:demo"], self.root)
        self.assertEqual([r.id for r in rules], ["G-001", "C-001", "S-001"])

    def test_missing_scope_file_is_empty_not_an_error(self):
        self.assertEqual(voice.load_scope("channel:carrier-pigeon", self.root), [])

    def test_retired_rules_are_not_composed(self):
        """Rules move to ## Retired rather than being deleted, so ids stay unique
        and old outputs stay explainable. Retired rules must not still apply."""
        self.write_voice("global.md",
                         "---\nscope: global\n---\n\n## Rules\n\n- [G-001] Live.\n\n"
                         "## Retired\n\n- [G-002] Dead.\n")
        self.assertEqual([r.id for r in voice.load_scope("global", self.root)], ["G-001"])

    def test_append_allocates_the_next_id_and_keeps_existing_text(self):
        rule_id = voice.append_rule("global", "New rule.", source="feedback F-1",
                                    base=self.root)
        self.assertEqual(rule_id, "G-002")
        text = voice.scope_path("global", self.root).read_text()
        self.assertIn("- [G-001] Global rule.", text)
        self.assertIn("- [G-002] New rule.  (source: feedback F-1)", text)

    def test_append_inserts_inside_rules_not_after_a_later_heading(self):
        self.write_voice("global.md",
                         "---\nscope: global\n---\n\n## Rules\n\n- [G-001] Live.\n\n"
                         "## Retired\n\n- [G-009] Dead.\n")
        voice.append_rule("global", "Added.", base=self.root)
        lines = voice.scope_path("global", self.root).read_text().split("\n")
        self.assertLess(lines.index("- [G-010] Added."), lines.index("## Retired"))

    def test_unknown_scope_kind_is_rejected(self):
        with self.assertRaises(voice.VoiceError):
            voice.scope_path("team:sales", self.root)


class WorkOrderTest(TempRootTest):
    def test_work_order_carries_rules_inputs_and_interpolation(self):
        self.write_skill("demo", channel="email")
        self.write_voice("global.md", "---\nscope: global\n---\n\n## Rules\n\n"
                                      "- [G-001] Global rule.\n")
        self.write_voice("channels/email.md", "---\nscope: channel:email\n---\n\n## Rules\n\n"
                                              "- [C-001] Email rule.\n")
        skill = skills.load_skill("demo", self.root)
        order = runner.compose(skill, skill.bind({"topic": "duplicate reviews"}),
                               base=self.root)
        self.assertIn("[G-001] (global) Global rule.", order)
        self.assertIn("[C-001] (channel:email) Email rule.", order)
        self.assertIn("- topic: 'duplicate reviews'", order)
        self.assertIn("Look at duplicate reviews to depth 2.", order)

    def test_unknown_placeholder_is_left_alone_not_blanked(self):
        self.write_skill("demo")
        directory = self.root / "skills" / "demo"
        (directory / "SKILL.md").write_text(
            (directory / "SKILL.md").read_text().replace(
                "Look at {{ topic }} to depth {{ depth }}.",
                "Look at {{ topic }} and {{ nope }}.")
        )
        skill = skills.load_skill("demo", self.root)
        order = runner.compose(skill, skill.bind({"topic": "x"}), base=self.root)
        self.assertIn("{{ nope }}", order)


class DryRunTest(TempRootTest):
    def test_dry_run_writes_a_record_and_calls_nothing(self):
        self.write_skill("demo")
        skill = skills.load_skill("demo", self.root)

        def explode(*args, **kwargs):
            raise AssertionError("a dry run must never call a provider")

        record = runner.run(skill, {"topic": "x"}, base=self.root, transport=explode)
        self.assertEqual(record["mode"], "dry-run")
        self.assertFalse(record["sent"])
        directory = self.root / "runs" / record["run_id"]
        self.assertTrue((directory / "workorder.md").is_file())
        self.assertTrue((directory / "run.json").is_file())
        self.assertFalse((directory / "output.md").exists())

    def test_execute_uses_the_routed_provider_and_still_does_not_send(self):
        self.write_skill("demo", task_class="draft")
        skill = skills.load_skill("demo", self.root)
        seen = {}

        def transport(prompt, provider):
            seen["provider"] = provider.key
            return "drafted text"

        record = runner.run(skill, {"topic": "x"}, execute=True, base=self.root,
                            transport=transport)
        self.assertEqual(seen["provider"], "anthropic-opus")
        self.assertFalse(record["sent"])
        self.assertEqual(
            (self.root / "runs" / record["run_id"] / "output.md").read_text(), "drafted text")


class FailoverTest(TempRootTest):
    def test_a_down_provider_costs_the_next_candidate_not_the_run(self):
        """The router already ranked fallbacks. A provider being down is exactly
        the situation that ranking exists for."""
        self.write_skill("demo", task_class="draft")
        skill = skills.load_skill("demo", self.root)
        tried = []

        def transport(prompt, provider):
            tried.append(provider.key)
            if provider.key == "anthropic-opus":
                raise OSError("[Errno 61] Connection refused")
            return "second provider answered"

        record = runner.run(skill, {"topic": "x"}, execute=True, base=self.root,
                            transport=transport)
        self.assertEqual(tried, ["anthropic-opus", "hermes-codex"])
        self.assertEqual(record["provider"], "hermes-codex")
        self.assertFalse(record["attempts"][0]["ok"])
        self.assertIn("Connection refused", record["attempts"][0]["error"])

    def test_all_providers_down_fails_with_every_reason_listed(self):
        self.write_skill("demo", task_class="draft")
        skill = skills.load_skill("demo", self.root)

        def transport(prompt, provider):
            raise OSError("refused")

        with self.assertRaises(runner.RunError) as caught:
            runner.run(skill, {"topic": "x"}, execute=True, base=self.root,
                       transport=transport)
        self.assertIn("anthropic-opus", str(caught.exception))
        self.assertIn("hermes-codex", str(caught.exception))


class ShippedSkillsTest(unittest.TestCase):
    """Properties every skill in this repository must hold, now and after edits."""

    def setUp(self):
        self.skills = skills.list_skills(REPO)
        self.table = route_table.load(REPO / "config" / "routes.json")

    def test_the_five_named_skills_exist(self):
        self.assertEqual(
            {s.slug for s in self.skills},
            {"reddit-mine", "linkedin-reply", "recruiter-outreach",
             "site-factory-prospect", "site-factory-email"},
        )

    def test_every_skill_is_structurally_valid(self):
        for skill in self.skills:
            self.assertEqual(skill.validate(), [], f"{skill.slug} is malformed")

    def test_no_skill_declares_a_send_path(self):
        for skill in self.skills:
            self.assertFalse(skill.sends, f"{skill.slug} declares sends: true")

    def test_every_skill_routes_somewhere(self):
        for skill in self.skills:
            plan = runner.plan(skill, self._sample_inputs(skill), base=REPO, table=self.table)
            self.assertIsNotNone(plan["decision"].chosen,
                                 f"{skill.slug} has no eligible provider")

    def test_every_skill_declares_an_escalation_section_with_content(self):
        for skill in self.skills:
            self.assertGreater(len(skill.section("Escalation")), 40,
                               f"{skill.slug} escalation section is a stub")

    @staticmethod
    def _sample_inputs(skill):
        values = {}
        for spec in skill.inputs:
            if spec.get("required", True) and "default" not in spec:
                values[spec["name"]] = "sample"
        return values


if __name__ == "__main__":
    unittest.main()
