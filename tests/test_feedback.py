"""The feedback compiler's one non-negotiable property:

    a correction observed once never becomes a rule.

Everything else in this module exists to make that property falsifiable rather
than asserted in a docstring.
"""

import unittest

from patrick_os import feedback, voice

from tests.support import TempRootTest


class DiffTest(TempRootTest):
    def test_surface_edit_is_detected(self):
        edits = feedback.diff(
            "We reviewed the homepage for Acme Dental in March.",
            "We reviewed the homepage for Sunrise Dental in April.",
        )
        self.assertEqual([e["kind"] for e in edits], [feedback.SURFACE])

    def test_rewrite_is_not_mistaken_for_a_surface_edit(self):
        edits = feedback.diff(
            "To a new visitor this looks like a copy-paste error.",
            "The same review card appears three times.",
        )
        self.assertEqual(edits[0]["kind"], feedback.REWRITE)

    def test_deletion_and_insertion(self):
        self.assertEqual(feedback.diff("One. Two.", "One.")[0]["kind"], feedback.DELETION)
        self.assertEqual(feedback.diff("One.", "One. Two.")[0]["kind"], feedback.INSERTION)

    def test_same_correction_in_different_words_is_recognised_as_the_same(self):
        """Escalation counts repetitions, so matching has to survive rephrasing --
        otherwise the same correction made twice never adds up and the compiler
        looks like it is working while learning nothing."""
        first = feedback.diff("I am excited to unlock your growth potential.",
                              "I am writing about your homepage.")
        second = feedback.diff("We can unlock the growth potential here.",
                               "We looked at the homepage here.")
        self.assertNotEqual(first[0]["signature"], second[0]["signature"],
                            "these rephrasings do have different fingerprints")
        self.assertTrue(feedback.similar(first[0], second[0]),
                        "but they are the same correction and must match")

    def test_unrelated_corrections_do_not_match(self):
        first = feedback.diff("I am excited to unlock your growth potential.",
                              "I am writing about your homepage.")
        second = feedback.diff("Please confirm the invoice due date.",
                               "Please confirm the scheduling window.")
        self.assertFalse(feedback.similar(first[0], second[0]))

    def test_surface_edits_never_match_even_each_other(self):
        a = feedback.diff("Report for Acme Dental.", "Report for Sunrise Dental.")
        b = feedback.diff("Report for Acme Dental.", "Report for Ironwood Dental.")
        self.assertFalse(feedback.similar(a[0], b[0]))

    def test_identical_versions_raise(self):
        with self.assertRaises(feedback.FeedbackError):
            feedback.add(original="Same text.", edited="Same text.", base=self.root)


class LocalCorrectionTest(TempRootTest):
    """FIXTURE 1 — a one-off proper-noun edit must classify local and produce no rule."""

    def test_single_proper_noun_edit_produces_no_proposal(self):
        entry = feedback.add(
            original="I looked at the homepage for Acme Dental.",
            edited="I looked at the homepage for Sunrise Dental.",
            skill="site-factory-email",
            channel="email",
            base=self.root,
        )
        self.assertEqual(entry["status"], "recorded-local")
        self.assertEqual(entry["proposals"], [])
        self.assertEqual(entry["edits"][0]["scope"], "local")
        self.assertIn("names, numbers, dates, or URLs", entry["edits"][0]["rationale"])

    def test_repeated_proper_noun_edits_still_never_generalize(self):
        """Ten name corrections must not add up to one rule. Surface edits are
        excluded from repetition counting entirely, not merely under-counted."""
        for name in ("Sunrise", "Ironwood", "Cedar", "RoofPro", "CoolBlew"):
            entry = feedback.add(
                original="I looked at the homepage for Acme Dental.",
                edited=f"I looked at the homepage for {name} Dental.",
                skill="site-factory-email",
                channel="email",
                base=self.root,
            )
            self.assertEqual(entry["proposals"], [], f"{name} produced a rule proposal")
        self.assertEqual(len(feedback.load_all(self.root)), 5)

    def test_a_novel_substantive_edit_is_local_on_first_sight(self):
        """Not just proper nouns: ANY correction is local the first time. Scope
        comes from repetition across contexts, never from how general it sounds."""
        entry = feedback.add(
            original="This will unlock significant growth for your practice.",
            edited="The homepage lists three duplicate reviews.",
            skill="site-factory-email",
            channel="email",
            base=self.root,
        )
        self.assertEqual(entry["edits"][0]["scope"], "local")
        self.assertEqual(entry["proposals"], [])
        self.assertIn("until it repeats", entry["edits"][0]["rationale"])

    def test_promoting_a_local_entry_is_refused(self):
        entry = feedback.add(
            original="Written for Acme Dental.", edited="Written for Sunrise Dental.",
            skill="site-factory-email", base=self.root,
        )
        with self.assertRaises(feedback.FeedbackError) as caught:
            feedback.promote(entry["id"], base=self.root, verify=lambda: (True, {}))
        self.assertIn("must not become a rule", str(caught.exception))


class EscalationTest(TempRootTest):
    """FIXTURE 2 — a correction repeated across contexts escalates, and the scope
    it escalates to is determined by where the repetitions happened."""

    ORIGINAL = "This will unlock significant growth for your practice."
    EDITED = "The homepage lists three duplicate reviews."

    def test_second_occurrence_in_the_same_skill_scopes_to_that_skill(self):
        feedback.add(original=self.ORIGINAL, edited=self.EDITED,
                     skill="site-factory-email", channel="email", base=self.root)
        second = feedback.add(original=self.ORIGINAL, edited=self.EDITED,
                              skill="site-factory-email", channel="email", base=self.root)
        self.assertEqual(second["status"], "proposed")
        self.assertEqual(second["proposals"][0]["scope"], "skill:site-factory-email")
        self.assertEqual(second["proposals"][0]["occurrences"], 2)

    def test_same_channel_different_skills_scopes_to_the_channel(self):
        feedback.add(original=self.ORIGINAL, edited=self.EDITED,
                     skill="recruiter-outreach", channel="email", base=self.root)
        second = feedback.add(original=self.ORIGINAL, edited=self.EDITED,
                              skill="site-factory-email", channel="email", base=self.root)
        self.assertEqual(second["proposals"][0]["scope"], "channel:email")

    def test_different_channels_scopes_to_global(self):
        feedback.add(original=self.ORIGINAL, edited=self.EDITED,
                     skill="linkedin-reply", channel="linkedin", base=self.root)
        second = feedback.add(original=self.ORIGINAL, edited=self.EDITED,
                              skill="site-factory-email", channel="email", base=self.root)
        self.assertEqual(second["proposals"][0]["scope"], "global")

    def test_same_project_across_skills_scopes_to_the_project(self):
        feedback.add(original=self.ORIGINAL, edited=self.EDITED,
                     skill="site-factory-prospect", channel="reddit",
                     project="site-factory", base=self.root)
        second = feedback.add(original=self.ORIGINAL, edited=self.EDITED,
                              skill="site-factory-email", channel="email",
                              project="site-factory", base=self.root)
        self.assertEqual(second["proposals"][0]["scope"], "project:site-factory")

    def test_a_different_correction_does_not_count_toward_escalation(self):
        feedback.add(original="Totally unrelated sentence about scheduling.",
                     edited="A different unrelated sentence about invoices.",
                     skill="site-factory-email", channel="email", base=self.root)
        second = feedback.add(original=self.ORIGINAL, edited=self.EDITED,
                              skill="site-factory-email", channel="email", base=self.root)
        self.assertEqual(second["proposals"], [])


class PromotionTest(TempRootTest):
    ORIGINAL = "This will unlock significant growth for your practice."
    EDITED = "The homepage lists three duplicate reviews."

    def escalated_entry(self):
        feedback.add(original=self.ORIGINAL, edited=self.EDITED,
                     skill="site-factory-email", channel="email", base=self.root)
        return feedback.add(original=self.ORIGINAL, edited=self.EDITED,
                            skill="site-factory-email", channel="email", base=self.root)

    def test_promotion_appends_exactly_one_rule_and_logs_it(self):
        entry = self.escalated_entry()
        result = feedback.promote(entry["id"], base=self.root, verify=lambda: (True, {}))
        rules = voice.load_scope("skill:site-factory-email", self.root)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].id, result["rule_id"])
        changelog = feedback.changelog_path(self.root).read_text()
        self.assertIn(result["rule_id"], changelog)
        self.assertIn("To revert", changelog)

    def test_promotion_is_rolled_back_when_the_regression_suite_fails(self):
        """A rule that breaks the suite must leave the voice file byte-identical.
        Learning is never allowed to be a one-way door."""
        entry = self.escalated_entry()
        path = self.write_voice("skills/site-factory-email.md",
                                "---\nscope: skill:site-factory-email\n---\n\n## Rules\n\n"
                                "- [S-001] Existing rule.\n")
        before = path.read_text()
        with self.assertRaises(feedback.FeedbackError):
            feedback.promote(entry["id"], base=self.root, verify=lambda: (False, {"ok": False}))
        self.assertEqual(path.read_text(), before)
        self.assertEqual(len(voice.load_scope("skill:site-factory-email", self.root)), 1)

    def test_rollback_removes_a_file_that_did_not_exist_before(self):
        entry = self.escalated_entry()
        path = voice.scope_path("skill:site-factory-email", self.root)
        self.assertFalse(path.exists())
        with self.assertRaises(feedback.FeedbackError):
            feedback.promote(entry["id"], base=self.root, verify=lambda: (False, {}))
        self.assertFalse(path.exists())

    def test_double_promotion_is_refused(self):
        entry = self.escalated_entry()
        feedback.promote(entry["id"], base=self.root, verify=lambda: (True, {}))
        with self.assertRaises(feedback.FeedbackError):
            feedback.promote(entry["id"], base=self.root, verify=lambda: (True, {}))

    def test_human_can_override_scope_and_text(self):
        entry = self.escalated_entry()
        result = feedback.promote(entry["id"], base=self.root, scope="global",
                                  text="Say what is on the page, not what it unlocks.",
                                  verify=lambda: (True, {}))
        self.assertEqual(result["scope"], "global")
        self.assertEqual(voice.load_scope("global", self.root)[0].text.split("  (source")[0],
                         "Say what is on the page, not what it unlocks.")

    def test_rejecting_a_proposal_closes_it_without_touching_voice(self):
        entry = self.escalated_entry()
        feedback.reject(entry["id"], reason="too narrow to generalize", base=self.root)
        stored = feedback.load_entry(entry["id"], self.root)
        self.assertEqual(stored["proposals"][0]["status"], "rejected")
        self.assertEqual(stored["status"], "closed")
        self.assertEqual(voice.load_scope("skill:site-factory-email", self.root), [])


if __name__ == "__main__":
    unittest.main()
