"""Behavioral layer: do the checks catch a real bad output, and is the judge
structurally prevented from grading its own writer?

The canonical fixture in this file is not invented. It is the email Site Factory
actually produced and certified at PASS / 90.0 / evidence_fidelity 5/5.
"""

import unittest

from patrick_os import checks, judging, skills
from patrick_os.router import table as route_table

from tests.support import REPO

SHIPPED = (
    "I was looking at your site and noticed the same review from \"Dana Reyes\" "
    "appears three times on your homepage. To a new visitor, that looks like a "
    "copy-paste error rather than a full roster of happy clients.\n\n"
    "I can replace those duplicates with distinct, verified reviews and clean up "
    "the encoding errors.\n"
)


class FactIntegrityTest(unittest.TestCase):
    def fire(self, name, text, config=None):
        return checks.REGISTRY[name](text, config or {})

    def test_the_shipped_sentence_is_caught(self):
        found = self.fire("forbid_perception_language", SHIPPED)
        self.assertTrue(found)
        self.assertEqual(found[0].severity, checks.BLOCKING)

    def test_the_shipped_offer_is_caught(self):
        self.assertTrue(self.fire("forbid_manufactured_evidence", SHIPPED))

    def test_a_mechanical_consequence_is_not_flagged(self):
        """The correct version of the same claim must pass, or the check is just
        a ban on writing about the observation at all."""
        clean = ("The review card reading \"Dana Reyes\" appears three times in the "
                 "carousel. The section therefore displays one reviewer rather "
                 "than several.")
        self.assertEqual(self.fire("forbid_perception_language", clean), [])
        self.assertEqual(self.fire("forbid_manufactured_evidence", clean), [])

    def test_signature_counts_blocks_not_mentions(self):
        prose = "Patrick will follow up on Thursday.\n\nPatrick\n"
        self.assertEqual(self.fire("signature_once", prose, {"name": "Patrick"}), [])
        doubled = "Body text here.\n\nPatrick\n\nBest,\nPatrick\n"
        self.assertTrue(self.fire("signature_once", doubled, {"name": "Patrick"}))

    def test_verdict_vocabulary_rejects_smuggled_confidence(self):
        config = {"allowed": ["supported", "mixed", "insufficient evidence"]}
        self.assertTrue(self.fire("verdict_in_vocabulary",
                                  "Verdict: strongly supported, act on it", config))
        self.assertEqual(self.fire("verdict_in_vocabulary", "Verdict: mixed (9 of 13)",
                                   config), [])

    def test_quote_without_permalink_is_caught(self):
        text = 'Supports\n- "I archive them on sight"\n'
        self.assertTrue(self.fire("quotes_are_sourced", text))
        sourced = ('Supports\n- "I archive them on sight" -- u/x, 2026-08-24, '
                   'https://reddit.com/r/recruiting/comments/aaa\n')
        self.assertEqual(self.fire("quotes_are_sourced", sourced), [])

    def test_a_prepositional_phrase_is_not_perception_language(self):
        """False positive from a real recruiter-outreach run: "facts unique to
        the candidate:" tripped the check. Naming a person is not ascribing a
        perception to them; the construction needs the verb."""
        for benign in ("Identified specific, quotable facts unique to the candidate:",
                       "I sent the brief to the customer yesterday.",
                       "This role would be relevant to a prospect in platform work."):
            self.assertEqual(self.fire("forbid_perception_language", benign), [],
                             f"false positive on: {benign}")

    def test_the_to_a_visitor_construction_is_still_caught(self):
        for bad in ("To a new visitor, that looks like a copy-paste error.",
                    "To the customer this appears broken.",
                    "To a reader it seems unfinished."):
            self.assertTrue(self.fire("forbid_perception_language", bad),
                            f"missed: {bad}")

    def test_a_named_phrase_is_not_treated_as_a_mined_quote(self):
        """False positive from a real run: a retrieval-failure line naming the
        anti-bot challenge \"Prove your humanity\" was flagged as an unsourced
        quote. A mined comment is a sentence; a short phrase is a term."""
        text = ('Supports\n- none collected: Reddit returned an anti-bot challenge '
                '("Prove your humanity") for logged-out reads on 2026-09-03.\n')
        self.assertEqual(self.fire("quotes_are_sourced", text), [])

    def test_a_real_unsourced_quote_is_still_caught_alongside_that_exemption(self):
        text = ('Supports\n- "I can spot the ChatGPT cadence in two seconds and I '
                'archive it immediately"\n')
        self.assertTrue(self.fire("quotes_are_sourced", text))

    def test_sourcing_applies_only_to_the_evidence_sections(self):
        """False positive from a real run: the Hypothesis section restates the
        hypothesis in quotes, and the check demanded a permalink for it. Only
        mined evidence needs a source."""
        text = ('# Hypothesis\n\n"Recruiters can tell AI-written outreach."\n\n'
                '# Supports\n\nRetrieval failure: no threads were read.\n')
        config = {"sections": ["Supports", "Contradicts", "Adjacent"]}
        self.assertEqual(self.fire("quotes_are_sourced", text, config), [])

    def test_an_unsourced_quote_inside_supports_is_still_caught_when_scoped(self):
        text = ('# Hypothesis\n\n"A hypothesis."\n\n'
                '# Supports\n- "I can spot the ChatGPT cadence in two seconds and archive it"\n')
        config = {"sections": ["Supports", "Contradicts", "Adjacent"]}
        self.assertTrue(self.fire("quotes_are_sourced", text, config))

    def test_email_address_is_caught(self):
        self.assertTrue(self.fire("forbid_email_address", "reach me at a@b.co"))


class SeverityTest(unittest.TestCase):
    def test_style_annotates_and_never_blocks(self):
        """Site Factory SF-08: its lint deleted the two evidence-richest
        candidates over the word 'metadata' while a fatal duplicated signature
        passed at 100/100. Style must never eliminate."""
        findings = checks.run("This will unlock growth.", [{"check": "forbid_hype"}])
        self.assertTrue(findings)
        self.assertEqual(checks.verdict(findings), "repair")

    def test_fact_integrity_blocks(self):
        findings = checks.run(SHIPPED, [{"check": "forbid_perception_language"}])
        self.assertEqual(checks.verdict(findings), "blocked")

    def test_clean_output_has_no_findings(self):
        self.assertEqual(checks.verdict(checks.run("A plain sentence.", [])), "clean")

    def test_unknown_check_is_refused_loudly(self):
        with self.assertRaises(checks.CheckError):
            checks.run("x", [{"check": "vibes"}])


class JudgeIndependenceTest(unittest.TestCase):
    """SF-07, verified by measurement: a judge sharing an answer key with the
    writer produces a number that carries no information. Enforce, don't remember."""

    def setUp(self):
        self.table = route_table.load(REPO / "config" / "routes.json")

    def test_judge_is_never_the_writer(self):
        for writer in ("hermes-copilot", "anthropic-opus"):
            provider, _ = judging.choose_judge(writer, table=self.table)
            self.assertNotEqual(provider.key, writer)

    def test_judging_refuses_when_no_independent_judge_exists(self):
        from patrick_os.router.table import RouteTable
        solo = RouteTable({
            "providers": {"only": {"adapter": "hermes_cli", "capabilities": ["judge"],
                                   "quality": 4}},
            "routes": [{"task_class": "judge", "prefer": ["only"]}],
            "default": {"prefer": ["only"]},
        })
        with self.assertRaises(judging.IndependenceError):
            judging.choose_judge("only", table=solo)

    def test_judge_prompt_contains_no_exemplar_output(self):
        """The contamination vector was a calibration example in the judge prompt.
        There must be no 'here is a good one' anywhere in what the judge sees."""
        skill = skills.load_skill("site-factory-email", REPO)
        prompt = judging.build_prompt(skill, SHIPPED, {"verdict": "blocked"})
        lowered = prompt.lower()
        for phrase in ("calibration", "for example, a good", "here is a good",
                       "exemplar", "gold standard"):
            self.assertNotIn(phrase, lowered)
        self.assertIn("you have", lowered)
        self.assertIn("no example of a good one", lowered)

    def test_judge_prompt_carries_the_skill_criteria(self):
        skill = skills.load_skill("site-factory-email", REPO)
        prompt = judging.build_prompt(skill, "out", {})
        self.assertIn("Quality checks", prompt)
        self.assertIn("Escalation", prompt)
        self.assertIn("NOT SENDABLE", prompt)

    def test_deterministic_only_by_default(self):
        skill = skills.load_skill("site-factory-email", REPO)
        result = judging.judge(skill, SHIPPED, base=REPO, table=self.table)
        self.assertIsNone(result["model_judge"])
        self.assertEqual(result["deterministic"]["verdict"], "blocked")

    def test_model_judge_response_is_parsed_from_fenced_json(self):
        skill = skills.load_skill("linkedin-reply", REPO)
        result = judging.judge(
            skill, "Draft:\nA plain sentence.\n", writer_provider="anthropic-opus",
            base=REPO, table=self.table, execute=True,
            transport=lambda p, provider: '```json\n{"verdict": "pass"}\n```',
        )
        self.assertEqual(result["model_judge"]["verdict"], "pass")
        self.assertEqual(result["judge_provider"], "hermes-copilot")


class BehavioralFixtureTest(unittest.TestCase):
    def test_every_skill_with_checks_has_behavioral_fixtures(self):
        for skill in skills.list_skills(REPO):
            if skill.output_checks:
                self.assertTrue(skill.behavioral_fixtures(),
                                f"{skill.slug} declares checks nothing exercises")

    def test_every_skill_has_a_positive_and_a_negative_fixture(self):
        """A suite of only-negative fixtures passes trivially if the checks fire
        on everything. Each skill needs at least one output that must come back
        clean."""
        for skill in skills.list_skills(REPO):
            if not skill.output_checks:
                continue
            verdicts = {f["expect_verdict"] for f in skill.behavioral_fixtures()}
            self.assertIn("clean", verdicts, f"{skill.slug} has no passing fixture")
            self.assertTrue(verdicts - {"clean"}, f"{skill.slug} has no failing fixture")

    def test_every_behavioral_fixture_records_its_provenance(self):
        for skill in skills.list_skills(REPO):
            for fixture in skill.behavioral_fixtures():
                self.assertTrue(fixture.get("provenance"),
                                f"{skill.slug}::{fixture['name']} has no provenance")


if __name__ == "__main__":
    unittest.main()
