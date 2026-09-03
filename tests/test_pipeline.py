"""The architectural constraint: Patrick OS must not hard-code Site Factory as
the only or primary commercial workflow.

These tests exist to fail if that assumption creeps back in.
"""

import unittest

from patrick_os import feedback, pipeline, skills, voice

from tests.support import REPO, TempRootTest


class VocabularyTest(unittest.TestCase):
    def test_stages_are_the_declared_pipeline_in_order(self):
        self.assertEqual(pipeline.STAGES, (
            "signal", "qualification", "diagnosis", "mechanism-selection",
            "sales-artifact", "outreach", "result", "learning"))

    def test_investment_tiers_are_ordered_cheapest_first(self):
        self.assertEqual(pipeline.TIERS, ("note", "audit", "pilot", "build"))
        self.assertLess(pipeline.tier_index("note"), pipeline.tier_index("build"))

    def test_unknown_stage_and_tier_are_rejected(self):
        for call, bad in ((pipeline.stage_index, "selling"), (pipeline.tier_index, "huge")):
            with self.assertRaises(pipeline.PipelineError):
                call(bad)

    def test_every_stage_has_a_stated_purpose(self):
        for stage in pipeline.STAGES:
            self.assertTrue(pipeline.STAGE_PURPOSE.get(stage))


class MechanismRegistryTest(unittest.TestCase):
    def setUp(self):
        self.registry = pipeline.load_mechanisms(REPO / "config" / "mechanisms.json")

    def test_non_website_mechanisms_are_declared(self):
        """The whole point of the registry. If website is the only row, the
        architecture still assumes every intervention is a web intervention."""
        keys = set(self.registry.keys())
        self.assertIn("website", keys)
        self.assertTrue(keys - {"website", "none"},
                        "no non-website mechanism is declared")
        self.assertIn("positioning", keys)

    def test_a_no_intervention_outcome_exists(self):
        """Mechanism selection that cannot conclude 'nothing yet' is not
        selection. Site Factory SF-03 turned a crawler timeout into a qualified
        rebuild at score 90 precisely because it had no way to say this."""
        self.assertIn("none", self.registry)

    def test_site_factory_is_an_executor_of_one_mechanism_not_all_of_them(self):
        owning = [k for k in self.registry.keys()
                  if "site-factory" in self.registry[k].executors]
        self.assertEqual(owning, ["website"])

    def test_every_mechanism_declares_valid_tiers(self):
        for key in self.registry.keys():
            for tier in self.registry[key].tiers:
                self.assertIn(tier, pipeline.TIERS)

    def test_unknown_mechanism_lookup_is_refused(self):
        with self.assertRaises(pipeline.PipelineError):
            self.registry["telepathy"]


class SkillPositionTest(unittest.TestCase):
    def setUp(self):
        self.skills = skills.list_skills(REPO)

    def test_every_skill_declares_a_stage(self):
        for skill in self.skills:
            self.assertIn(skill.stage, pipeline.STAGES, f"{skill.slug} has no valid stage")

    def test_every_skill_declares_mechanisms_or_says_it_is_agnostic(self):
        """A skill that says nothing is assumed to serve the only mechanism
        anybody built. That assumption is the thing being designed out."""
        for skill in self.skills:
            self.assertTrue(skill.mechanisms or skill.mechanism_agnostic,
                            f"{skill.slug} declares neither")

    def test_only_the_site_factory_skills_are_bound_to_the_website_mechanism(self):
        bound = sorted(s.slug for s in self.skills if "website" in s.mechanisms)
        self.assertEqual(bound, ["site-factory-email", "site-factory-prospect"])

    def test_the_general_skills_are_not_bound_to_any_mechanism(self):
        for slug in ("reddit-mine", "linkedin-reply", "recruiter-outreach"):
            skill = skills.load_skill(slug, REPO)
            self.assertTrue(skill.mechanism_agnostic, f"{slug} became mechanism-bound")


class ValidationTest(TempRootTest):
    def test_a_skill_with_no_stage_fails_validation(self):
        directory = self.write_skill("nostage")
        text = (directory / "SKILL.md").read_text().replace("stage: signal\n", "")
        (directory / "SKILL.md").write_text(text)
        problems = skills.load_skill("nostage", self.root).validate()
        self.assertTrue(any("missing front-matter field: stage" in p for p in problems))

    def test_a_skill_naming_an_undeclared_mechanism_fails(self):
        directory = self.write_skill("badmech")
        text = (directory / "SKILL.md").read_text().replace(
            "mechanism_agnostic: true", "mechanisms:\n  - telepathy")
        (directory / "SKILL.md").write_text(text)
        problems = skills.load_skill("badmech", self.root).validate()
        self.assertTrue(any("unknown mechanism" in p for p in problems))

    def test_declaring_both_mechanisms_and_agnostic_fails(self):
        directory = self.write_skill("both")
        text = (directory / "SKILL.md").read_text().replace(
            "mechanism_agnostic: true", "mechanism_agnostic: true\nmechanisms:\n  - website")
        (directory / "SKILL.md").write_text(text)
        self.assertTrue(any("pick one" in p
                            for p in skills.load_skill("both", self.root).validate()))


class CoverageTest(unittest.TestCase):
    def test_coverage_reports_the_stages_that_have_nothing(self):
        """The gap must be visible. Five of eight stages are empty, and a system
        that cannot say so behaves as though the three it has are the business."""
        registry = pipeline.load_mechanisms(REPO / "config" / "mechanisms.json")
        report = pipeline.coverage(skills.list_skills(REPO), registry)
        empty = [s for s in pipeline.STAGES if not report["by_stage"][s]]
        for stage in ("diagnosis", "mechanism-selection", "sales-artifact"):
            self.assertIn(stage, empty, f"{stage} unexpectedly has a skill")
        self.assertTrue(report["by_stage"]["signal"])

    def test_coverage_reports_mechanisms_with_no_executor(self):
        registry = pipeline.load_mechanisms(REPO / "config" / "mechanisms.json")
        report = pipeline.coverage(skills.list_skills(REPO), registry)
        self.assertEqual(report["by_mechanism"]["positioning"], [])
        self.assertTrue(report["by_mechanism"]["website"])


class StrategyLayerTest(TempRootTest):
    """Strategy feedback answers a different question from voice feedback and
    must not land in the same place."""

    def test_a_strategy_lesson_without_evidence_is_refused(self):
        with self.assertRaises(feedback.FeedbackError) as caught:
            feedback.add_strategy(lesson="Stop chasing dentists", evidence="",
                                  base=self.root)
        self.assertIn("hunch", str(caught.exception))

    def test_a_strategy_lesson_proposes_on_first_sight(self):
        """Unlike an inferred voice rule, a strategy lesson comes from a result a
        human observed. There is nothing to corroborate by repetition."""
        entry = feedback.add_strategy(
            lesson="Cosmetic web defects have never produced a reply.",
            evidence="0 of 5 benchmark businesses replied.",
            mechanism="website", base=self.root)
        self.assertEqual(entry["layer"], "strategy")
        self.assertEqual(entry["proposals"][0]["scope"], "mechanism:website")

    def test_strategy_promotion_lands_in_strategy_not_voice(self):
        entry = feedback.add_strategy(
            lesson="An opportunity with no buyer is not an opportunity.",
            evidence="SF-12: no buyer for 2 of 5.", mechanism="website",
            base=self.root)
        result = feedback.promote(entry["id"], base=self.root, verify=lambda: (True, {}))
        self.assertEqual(result["namespace"], "strategy")
        self.assertTrue(voice.load_scope("mechanism:website", self.root, "strategy"))
        self.assertEqual(voice.load_scope("global", self.root, "voice"), [])

    def test_strategy_and_voice_scopes_do_not_share_a_vocabulary(self):
        with self.assertRaises(voice.VoiceError):
            voice.scope_path("channel:email", self.root, "strategy")
        with self.assertRaises(voice.VoiceError):
            voice.scope_path("mechanism:website", self.root, "voice")

    def test_workflow_feedback_refuses_to_auto_edit_a_procedure(self):
        """Patrick OS rewrites rules, not procedures. A workflow change is a code
        change and belongs in a commit a human made."""
        entry = feedback.add_strategy(
            lesson="x", evidence="y", mechanism="website", base=self.root)
        stored = feedback.load_entry(entry["id"], self.root)
        stored["proposals"][0]["layer"] = feedback.WORKFLOW
        feedback.save_entry(stored, self.root)
        with self.assertRaises(feedback.FeedbackError) as caught:
            feedback.promote(entry["id"], base=self.root, verify=lambda: (True, {}))
        self.assertIn("by hand", str(caught.exception))

    def test_default_layer_is_output_so_existing_behaviour_is_unchanged(self):
        entry = feedback.add(original="This will unlock growth.",
                             edited="The homepage lists three reviews.",
                             skill="demo", channel="email", base=self.root)
        self.assertEqual(entry["layer"], "output")


if __name__ == "__main__":
    unittest.main()
