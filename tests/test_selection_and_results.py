"""Mechanism selection and result intake.

Selection is the stage whose absence let Site Factory's executor make the
decision. These tests pin the property that makes it a selection rather than a
justification: it can conclude that nothing is warranted, and the code decides
rather than the model.
"""

import unittest

from patrick_os.domains.commercial import results
from patrick_os.domains.commercial import selection
from patrick_os.domains.commercial import workflow as pipeline

from tests.support import REPO, TempRootTest


def registry():
    return pipeline.load_mechanisms(REPO / "config" / "domains" / "commercial-mechanisms.json")


class SelectorPurityTest(unittest.TestCase):
    def test_selection_needs_no_model_no_network_no_keys(self):
        """If a decision can only be observed by running a model, it cannot be
        regression-tested. Same reasoning as router.resolve."""
        import sys
        result = selection.select(selection.Profile(), registry())
        self.assertIsNotNone(result.chosen)
        for module in ("anthropic", "openai"):
            self.assertNotIn(module, sys.modules)

    def test_an_empty_profile_selects_none(self):
        self.assertEqual(selection.select(selection.Profile(), registry()).chosen.key,
                         "none")

    def test_none_is_always_eligible_and_always_last(self):
        """A selector that cannot conclude 'no intervention is supported' is not
        selecting; it is justifying the tool it already has."""
        profile = selection.Profile(contradicted_claims=5, buyer_identified=True)
        result = selection.select(profile, registry())
        self.assertEqual(result.eligible[-1].key, "none")

    def test_unknown_profile_field_is_refused(self):
        with self.assertRaises(selection.SelectionError):
            selection.Profile(vibes="good")

    def test_a_precondition_typo_is_refused_rather_than_silently_false(self):
        """A misspelled field evaluating false would disqualify a mechanism for
        no reason, and nothing would say so."""
        with self.assertRaises(selection.SelectionError):
            selection._evaluate(["buyer_identifed", "eq", True], selection.Profile())


class SF03Test(unittest.TestCase):
    """The finding this whole stage exists to prevent, as a standing test."""

    def test_a_failed_retrieval_cannot_select_a_web_intervention(self):
        profile = selection.Profile(
            retrieval_ok=False, identity_confidence="high", buyer_identified=True,
            observations=[{"domain": "website", "severity": "high"}])
        result = selection.select(profile, registry())
        self.assertEqual(result.chosen.key, "none")
        reasons = dict(result.rejected)
        self.assertIn("retrieval_ok", reasons["website"])

    def test_identity_below_medium_cannot_select_a_web_intervention(self):
        """SF-05: the observed defects may belong to a stranger's website."""
        profile = selection.Profile(
            retrieval_ok=True, identity_confidence="low", buyer_identified=True,
            observations=[{"domain": "website", "severity": "high"}])
        result = selection.select(profile, registry())
        self.assertNotIn("website", [c.key for c in result.eligible])

    def test_no_buyer_cannot_select_a_paid_intervention(self):
        """SF-12 and strategy rule ST-001."""
        profile = selection.Profile(
            retrieval_ok=True, identity_confidence="high", buyer_identified=False,
            contradicted_claims=3, observations=[{"domain": "website"}])
        result = selection.select(profile, registry())
        self.assertEqual(result.chosen.key, "none")


class CapabilityGapTest(unittest.TestCase):
    def test_supported_but_unexecutable_is_not_reported_as_rejected(self):
        """"The right intervention is X and we cannot do X" is a strategic
        finding. Folding it into 'preconditions failed' would bury it."""
        profile = selection.Profile(
            retrieval_ok=True, identity_confidence="high", buyer_identified=True,
            contradicted_claims=2, observations=[{"domain": "website"}])
        result = selection.select(profile, registry())
        gap = dict(result.capability_gap)
        self.assertIn("website", gap)
        self.assertIn("blocked", gap["website"])
        self.assertNotIn("website", dict(result.rejected))


class TierTest(unittest.TestCase):
    def test_a_tier_is_not_advanced_without_a_measured_result(self):
        """ST-002. Site Factory reached automated outbound with zero validated
        demand, which is the failure this ordering prevents."""
        profile = selection.Profile(current_tier="note", measured_result_available=False)
        self.assertEqual(selection.select(profile, registry()).tier, "note")

    def test_a_measured_result_advances_exactly_one_tier(self):
        profile = selection.Profile(current_tier="note", measured_result_available=True)
        self.assertEqual(selection.select(profile, registry()).tier, "audit")

    def test_the_last_tier_does_not_overflow(self):
        profile = selection.Profile(current_tier="build", measured_result_available=True)
        self.assertEqual(selection.select(profile, registry()).tier, "build")


class ResultIntakeTest(TempRootTest):
    def test_a_result_without_evidence_is_refused(self):
        with self.assertRaises(results.ResultError) as caught:
            results.record(opportunity="Acme", mechanism="positioning", tier="audit",
                           outcome="paid", evidence="", base=self.root)
        self.assertIn("memory", str(caught.exception))

    def test_silence_is_a_first_class_outcome(self):
        """A results log that only records wins measures enthusiasm."""
        self.assertIn("no_reply", results.OUTCOMES)
        entry = results.record(opportunity="Acme", mechanism="positioning", tier="audit",
                               outcome="no_reply", evidence="Sent 2026-09-01; no reply "
                               "in 14 days.", base=self.root)
        self.assertEqual(entry["outcome"], "no_reply")
        self.assertFalse(entry["advances_tier"])

    def test_only_a_real_response_advances_a_tier(self):
        for outcome, advances in (("no_reply", False), ("declined", False),
                                  ("reply", True), ("paid", True)):
            entry = results.record(opportunity="X", mechanism="positioning",
                                   tier="note", outcome=outcome,
                                   evidence="recorded from the inbox", base=self.root)
            self.assertEqual(entry["advances_tier"], advances, outcome)

    def test_an_unknown_outcome_is_refused(self):
        with self.assertRaises(results.ResultError):
            results.record(opportunity="X", mechanism="positioning", tier="note",
                           outcome="went well", evidence="e", base=self.root)

    def test_a_repeated_pattern_prompts_a_strategy_rule_but_writes_none(self):
        """Same discipline as the feedback compiler: one result is a data point,
        three is a pattern, and the human still writes the rule."""
        for index in range(3):
            entry = results.record(opportunity=f"biz-{index}", mechanism="website",
                                   tier="audit", outcome="no_reply",
                                   evidence="no reply in 14 days", base=self.root)
        self.assertIn("patrick feedback strategy", entry["lesson_prompt"])
        from patrick_os import voice
        self.assertEqual(voice.load_scope("mechanism:website", self.root, "strategy"), [],
                         "recording a result must never write a strategy rule by itself")

    def test_one_result_does_not_prompt(self):
        entry = results.record(opportunity="X", mechanism="website", tier="note",
                               outcome="no_reply", evidence="e", base=self.root)
        self.assertEqual(entry["lesson_prompt"], "")

    def test_results_round_trip(self):
        results.record(opportunity="Acme", mechanism="positioning", tier="audit",
                       outcome="paid", evidence="invoice 1041 cleared", amount="$500",
                       base=self.root)
        rows = results.load_all(self.root)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["amount"], "$500")
        self.assertEqual(results.summary(self.root)["by_mechanism"]["positioning"]["paid"], 1)


if __name__ == "__main__":
    unittest.main()
