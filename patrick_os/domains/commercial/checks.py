"""Checks that only make sense for commercial output.

These lived in the core check registry, which meant a fiction audit was evaluated
by a module that knew about testimonials and landing pages. They are contributed
by this pack now, and merged into the registry only when the commercial domain is
enabled.
"""

from __future__ import annotations

import re

from ...checks import BLOCKING, Finding, _hits


MANUFACTURED = re.compile(
    r"\b(?:write|writing|generate|generating|produce|producing|create|creating|"
    r"replace|replacing|source|sourcing|solicit|soliciting|seed|seeding|collect|collecting)\b"
    r"[^.!?\n]{0,60}\b(?:reviews?|testimonials?|ratings?|endorsements?|"
    r"references?|case\s+studies)\b",
    re.IGNORECASE,
)


def forbid_manufactured_evidence(text, config):
    """G-007. The same shipped email offered to 'replace those duplicates with
    distinct, verified reviews' — FTC review-authenticity exposure."""
    found = _hits(text, MANUFACTURED)
    if not found:
        return []
    return [
        Finding(
            "forbid_manufactured_evidence",
            BLOCKING,
            "offers to produce or replace the evidence it is measuring",
            evidence=sorted(set(found))[:5],
        )
    ]


MECHANISM_MARKERS = {
    "website": (r"site|website|homepage|landing\s+page|rebuild|redesign|"
                r"web\s+presence|page\s+speed"),
    "messaging": r"campaign|sequence|drip|outbound|cadence|newsletter|email\s+blast",
    "pricing": r"pricing|price\s+point|packaging|rate\s+card|retainer",
    "ops-automation": r"automat\w+|workflow|integration|pipeline|crm|zapier",
    "positioning": (r"claim|positioning|message|story|proof|wording|copy|"
                    r"headline|narrative"),
}

_ACTION = (r"(?:we|i|our team|patrick)\s+(?:can|could|will|would|should|recommend\w*|"
           r"propose|suggest)\s+[^.!?\n]{0,60}?"
           r"\b(?:build|rebuild|redesign|rewrite|implement|launch|create|develop|fix|"
           r"repair|migrate|automate|set\s+up|roll\s+out|deploy|add|introduce)\b"
           r"[^.!?\n]{0,60}?")


def forbid_other_mechanisms(text, config):
    """An artifact may only act inside the mechanism that was selected for it.

    Not the same as ``forbid_intervention_proposal``, which forbids ALL remedies
    and belongs to the diagnosis stage. By the artifact stage a mechanism has
    been chosen, so recommending action is the job -- recommending action from a
    DIFFERENT mechanism is mechanism selection happening a second time, later,
    without the gate. That is SF-03's pattern moved one stage downstream.
    """
    allowed = {m.lower() for m in config.get("allow", [])}
    findings = []
    for mechanism, markers in MECHANISM_MARKERS.items():
        if mechanism in allowed:
            continue
        pattern = re.compile(_ACTION + r"\b(?:" + markers + r")\b", re.IGNORECASE)
        found = _hits(text, pattern)
        if found:
            findings.append(Finding(
                "forbid_other_mechanisms", BLOCKING,
                f"recommends a {mechanism!r} intervention; this artifact is scoped to "
                + (", ".join(sorted(allowed)) or "no mechanism")
                + " and re-selecting here bypasses the mechanism-selection gate",
                evidence=[h.strip()[:90] for h in sorted(set(found))[:3]]))
    return findings


CHECKS = {
    "forbid_manufactured_evidence": forbid_manufactured_evidence,
    "forbid_other_mechanisms": forbid_other_mechanisms,
}
