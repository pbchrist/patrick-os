"""The architectural constraint: Patrick OS must not hard-code Site Factory as
the only or primary commercial workflow.

These tests exist to fail if that assumption creeps back in.
"""

import json
import subprocess
import sys
import unittest

from patrick_os import feedback, skills, voice
from patrick_os.domains.commercial import workflow as pipeline

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
        self.registry = pipeline.load_mechanisms(REPO / "config" / "domains" / "commercial-mechanisms.json")

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

    def test_only_commercial_skills_carry_commercial_vocabulary(self):
        """The scope correction, as a test. `stage` was once required of every
        skill, so a fiction skill could not validate -- it was made to name a
        position in a sales pipeline. Now it applies only inside the domain that
        defines it."""
        for skill in self.skills:
            if skill.domain == "commercial":
                self.assertIn(skill.stage, pipeline.STAGES,
                              f"{skill.slug} is commercial but has no valid stage")
            else:
                self.assertIsNone(skill.stage,
                                  f"{skill.slug} declares no domain yet carries a stage")

    def test_a_skill_in_no_domain_needs_none_of_it(self):
        """A plain OS skill is valid with no domain vocabulary at all."""
        generic = [s for s in self.skills if not s.domain]
        self.assertTrue(generic, "every skill became domain-bound; the core re-absorbed one")
        for skill in generic:
            self.assertEqual(skill.validate(), [], f"{skill.slug} is not valid")

    def test_commercial_skills_declare_mechanisms_or_say_they_are_agnostic(self):
        """Inside the commercial domain a skill that says nothing is assumed to
        serve the only mechanism anybody built. Outside it, the question is
        meaningless and is never asked."""
        for skill in self.skills:
            if skill.domain == "commercial":
                self.assertTrue(skill.mechanisms or skill.mechanism_agnostic,
                                f"{skill.slug} declares neither")

    def test_only_the_site_factory_skills_are_bound_to_the_website_mechanism(self):
        bound = sorted(s.slug for s in self.skills if "website" in s.mechanisms)
        self.assertEqual(bound, ["site-factory-email", "site-factory-prospect"])

    def test_the_general_skills_belong_to_no_domain_at_all(self):
        """These are OS skills. They were previously forced to declare
        mechanism_agnostic: true, which is a commercial answer to a commercial
        question they should never have been asked."""
        for slug in ("reddit-mine", "linkedin-reply", "recruiter-outreach",
                     "narrative-diagnosis", "weekly-close"):
            skill = skills.load_skill(slug, REPO)
            self.assertIsNone(skill.domain, f"{slug} became domain-bound")
            self.assertFalse(skill.mechanisms)


class ValidationTest(TempRootTest):
    def test_a_commercial_skill_with_no_stage_fails_validation(self):
        directory = self.write_skill("nostage")
        text = (directory / "SKILL.md").read_text().replace(
            "task_class: research", "task_class: research\ndomain: commercial\n"
            "mechanism_agnostic: true")
        (directory / "SKILL.md").write_text(text)
        problems = skills.load_skill("nostage", self.root).validate()
        self.assertTrue(any("must declare a stage" in p for p in problems), problems)

    def test_a_skill_with_no_domain_and_no_stage_is_perfectly_valid(self):
        self.write_skill("plain")
        self.assertEqual(skills.load_skill("plain", self.root).validate(), [])

    def test_an_unknown_domain_is_reported_rather_than_ignored(self):
        directory = self.write_skill("weird")
        text = (directory / "SKILL.md").read_text().replace(
            "task_class: research", "task_class: research\ndomain: astrology")
        (directory / "SKILL.md").write_text(text)
        problems = skills.load_skill("weird", self.root).validate()
        self.assertTrue(any("no domain pack" in p for p in problems), problems)

    def test_a_skill_naming_an_undeclared_mechanism_fails(self):
        directory = self.write_skill("badmech")
        text = (directory / "SKILL.md").read_text().replace(
            "task_class: research",
            "task_class: research\ndomain: commercial\nstage: qualification\n"
            "mechanisms:\n  - telepathy")
        (directory / "SKILL.md").write_text(text)
        problems = skills.load_skill("badmech", self.root).validate()
        self.assertTrue(any("unknown mechanism" in p for p in problems))

    def test_declaring_both_mechanisms_and_agnostic_fails(self):
        directory = self.write_skill("both")
        text = (directory / "SKILL.md").read_text().replace(
            "task_class: research",
            "task_class: research\ndomain: commercial\nstage: qualification\n"
            "mechanism_agnostic: true\nmechanisms:\n  - website")
        (directory / "SKILL.md").write_text(text)
        self.assertTrue(any("pick one" in p
                            for p in skills.load_skill("both", self.root).validate()))


class CoverageTest(unittest.TestCase):
    def test_coverage_distinguishes_covered_stages_from_empty_ones(self):
        """The gap must stay visible. This asserts the mechanism works, not a
        particular snapshot of it -- pinning the empty list would mean every new
        skill breaks a test that is not about that skill."""
        registry = pipeline.load_mechanisms(REPO / "config" / "domains" / "commercial-mechanisms.json")
        report = pipeline.coverage(skills.list_skills(REPO), registry)
        covered = [s for s in pipeline.STAGES if report["by_stage"][s]]
        empty = [s for s in pipeline.STAGES if not report["by_stage"][s]]
        self.assertTrue(covered and empty,
                        "coverage must report both sides or it is not a gap report")
        self.assertEqual(len(covered) + len(empty), len(pipeline.STAGES))
        for stage in covered:
            for slug in report["by_stage"][stage]:
                self.assertEqual(skills.load_skill(slug, REPO).stage, stage)

    def test_a_stage_served_by_tooling_is_not_reported_as_a_gap(self):
        """Recording what happened is data intake, not a model task -- a model
        should never decide what an outcome was. Showing it as an empty stage
        would be a false gap; showing a skill there would be a false claim."""
        registry = pipeline.load_mechanisms(REPO / "config" / "domains" / "commercial-mechanisms.json")
        report = pipeline.coverage(skills.list_skills(REPO), registry)
        self.assertEqual(report["by_stage"]["result"], [])
        self.assertIn("result", report["tooling"])
        self.assertIn("result", report["covered"])
        self.assertNotIn("result", report["empty"])

    def test_coverage_counts_only_skills_inside_the_domain(self):
        """Coverage is a view of ONE domain, not of Patrick OS. An OS skill that
        happens to do research must not be counted as commercial signal work."""
        registry = pipeline.load_mechanisms(
            REPO / "config" / "domains" / "commercial-mechanisms.json")
        commercial = [s for s in skills.list_skills(REPO) if s.domain == "commercial"]
        report = pipeline.coverage(commercial, registry)
        for stage, owners in report["by_stage"].items():
            for slug in owners:
                self.assertEqual(skills.load_skill(slug, REPO).domain, "commercial")

    def test_coverage_reports_mechanisms_with_no_executor(self):
        """Asserts the reporting works, not a snapshot of which mechanisms are
        covered -- that changes every time a skill lands, and pinning it would
        make unrelated work fail this test."""
        registry = pipeline.load_mechanisms(REPO / "config" / "domains" / "commercial-mechanisms.json")
        report = pipeline.coverage(skills.list_skills(REPO), registry)
        uncovered = [k for k in registry.keys() if not report["by_mechanism"].get(k)]
        self.assertTrue(uncovered, "some mechanism should still lack a skill")
        for key in uncovered:
            for skill in skills.list_skills(REPO):
                self.assertNotIn(key, skill.mechanisms)
        for key, slugs in report["by_mechanism"].items():
            for slug in slugs:
                self.assertIn(key, skills.load_skill(slug, REPO).mechanisms)

    def test_a_mechanism_with_an_executor_declares_it_and_vice_versa(self):
        """The registry's executors list and the skills' mechanisms list are two
        halves of one fact. They drifting apart is how positioning ended up
        credited to a mechanism-agnostic skill."""
        registry = pipeline.load_mechanisms(REPO / "config" / "domains" / "commercial-mechanisms.json")
        for key in registry.keys():
            for slug in registry[key].executors:
                if slug in {s.slug for s in skills.list_skills(REPO)}:
                    self.assertIn(key, skills.load_skill(slug, REPO).mechanisms,
                                  f"{slug} is listed as executor of {key} but does "
                                  "not declare that mechanism")


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


class LayeringTest(unittest.TestCase):
    """Patrick OS is the operating layer. Domains run on top of it.

    The rule these tests hold: core knows about skills, voice, routing, judging,
    feedback, retrieval and orchestration. It knows nothing about selling,
    recruiting, fiction, or research. When that boundary broke, `stage` became a
    required field on every skill and a fiction skill could not validate.
    """

    CORE = ["frontmatter", "skills", "voice", "projects", "runner", "feedback",
            "judging", "checks", "testing", "decisions", "retrieval", "cli"]

    def test_no_core_module_imports_a_domain_pack_at_load(self):
        """Run in a subprocess: sys.modules is global, so another test importing
        a pack would make this pass or fail for reasons unrelated to the core.

        The domain LOADER (patrick_os.domains) is core infrastructure, the same
        way the adapter registry is. What must never load is a pack.
        """
        script = (
            "import importlib, sys\n"
            f"for n in {self.CORE!r}: importlib.import_module('patrick_os.' + n)\n"
            "packs = [m for m in sys.modules "
            "if m.startswith('patrick_os.domains.')]\n"
            "print(','.join(sorted(packs)))\n"
        )
        completed = subprocess.run([sys.executable, "-c", script], cwd=str(REPO),
                                   text=True, capture_output=True, check=True)
        leaked = [m for m in completed.stdout.strip().split(",") if m]
        self.assertEqual(leaked, [], f"core import pulled in domain packs: {leaked}")

    def test_no_core_module_mentions_a_domain_pack_at_module_level(self):
        """Lazy imports inside functions are fine and intended; a module-level
        `from .domains...` would make the dependency structural."""
        for name in self.CORE:
            source = (REPO / "patrick_os" / f"{name}.py").read_text()
            for line in source.split("\n"):
                if not line.startswith(("import ", "from ")):
                    continue
                if "domains." in line or "domains import" in line:
                    self.fail(f"{name}.py imports a domain PACK at module level: {line}")

    def test_the_core_check_registry_holds_no_commercial_check(self):
        from patrick_os import checks
        from patrick_os.domains import commercial
        self.assertTrue(commercial.CHECKS)
        for name in commercial.CHECKS:
            self.assertNotIn(name, checks.REGISTRY,
                             f"{name} is a commercial check sitting in the core registry")

    def test_a_domain_check_still_resolves_for_a_skill_that_declares_it(self):
        from patrick_os import checks
        self.assertTrue(callable(checks.resolve_check("forbid_manufactured_evidence")))

    def test_commercial_config_lives_under_the_domain_not_beside_the_router(self):
        self.assertFalse((REPO / "config" / "mechanisms.json").exists(),
                         "mechanisms.json is domain config and must not sit in config/ root")
        self.assertTrue((REPO / "config" / "domains" / "commercial-mechanisms.json").is_file())

    def test_site_factory_is_a_consumer_inside_a_domain_not_the_domain(self):
        registry = json.loads((REPO / "config" / "domains.json").read_text())
        consumers = registry["domains"]["commercial"]["consumers"]
        self.assertIn("site-factory", consumers)
        self.assertGreater(len(consumers), 1,
                           "a domain with one consumer is that consumer wearing a hat")

    def test_the_os_serves_skills_that_belong_to_no_domain(self):
        """The acceptance test for the scope correction: a skill about fiction,
        research or writing must be first-class without touching commerce."""
        generic = [s for s in skills.list_skills(REPO) if not s.domain]
        self.assertGreaterEqual(len(generic), 4)
        for skill in generic:
            self.assertEqual(skill.validate(), [])
