"""Mechanism selection: which intervention the diagnosis actually implies.

The stage whose absence let Site Factory's executor make the decision. SF-03
turned a Cloudflare challenge into a qualified website rebuild at score 90
because a rebuild was the only conclusion the system could reach.

**The model extracts; the code decides.** A diagnosis is prose, so a model reads
it and emits a structured profile. Selection itself is then a pure function over
that profile and a declarative precondition table — no model, no network, no
keys. That split is the whole point: if the model chose the mechanism, it would
choose the one it knows how to execute, which is the failure being designed out.

Same shape as ``router.resolve``, and for the same reason: a decision you can
only observe by running a model is a decision you cannot regression-test.
"""

from __future__ import annotations

from . import pipeline

# Profile fields a precondition may reference. Anything else is a typo, and a
# typo that silently evaluates false would disqualify a mechanism for no reason.
PROFILE_FIELDS = {
    "retrieval_ok": bool,
    "identity_confidence": str,      # none | low | medium | high
    "buyer_identified": bool,
    "supported_claims": int,
    "unsupported_claims": int,
    "contradicted_claims": int,
    "observations": list,            # [{"domain": str, "severity": str}]
    "measured_result_available": bool,
    "current_tier": str,
    "regulated_claims": bool,
}

OPERATORS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "in": lambda a, b: a in b,
    "not-in": lambda a, b: a not in b,
    "gte": lambda a, b: _num(a) >= _num(b),
    "lte": lambda a, b: _num(a) <= _num(b),
    "gt": lambda a, b: _num(a) > _num(b),
    "lt": lambda a, b: _num(a) < _num(b),
    "count-domain-gte": lambda a, b: None,   # handled specially
}


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("-inf")


class SelectionError(ValueError):
    pass


class Profile:
    """Structured facts extracted from a diagnosis. Deliberately small."""

    def __init__(self, **fields):
        unknown = set(fields) - set(PROFILE_FIELDS)
        if unknown:
            raise SelectionError(
                "unknown profile field(s): " + ", ".join(sorted(unknown))
                + "; known fields: " + ", ".join(sorted(PROFILE_FIELDS))
            )
        self.fields = {
            "retrieval_ok": True,
            "identity_confidence": "none",
            "buyer_identified": False,
            "supported_claims": 0,
            "unsupported_claims": 0,
            "contradicted_claims": 0,
            "observations": [],
            "measured_result_available": False,
            "current_tier": "note",
            "regulated_claims": False,
        }
        self.fields.update(fields)

    def get(self, name):
        return self.fields.get(name)

    def domain_count(self, domain):
        return sum(1 for o in self.fields["observations"] or []
                   if str(o.get("domain", "")).lower() == str(domain).lower())

    def as_dict(self):
        return dict(self.fields)


class Candidate:
    def __init__(self, mechanism, reasons):
        self.mechanism = mechanism
        self.reasons = list(reasons)

    @property
    def key(self):
        return self.mechanism.key

    def as_dict(self):
        return {"mechanism": self.key, "reasons": self.reasons}


class Selection:
    def __init__(self, profile, eligible, unexecutable, rejected, tier):
        self.profile = profile
        self.eligible = eligible
        self.unexecutable = unexecutable
        self.rejected = rejected
        self.tier = tier

    @property
    def chosen(self):
        """The selected mechanism. Never None -- 'none' is a real answer."""
        return self.eligible[0] if self.eligible else None

    @property
    def capability_gap(self):
        """Mechanisms the evidence supports that nothing here can execute.

        Kept separate from ``rejected`` on purpose. "The right intervention is X
        and we cannot do X" is a strategic finding -- it belongs in strategy/ and
        it is what tells Patrick where to build next. Folding it in with
        "preconditions failed" would bury it as a technicality.
        """
        return self.unexecutable

    def as_dict(self):
        return {
            "chosen": self.chosen.key if self.chosen else "none",
            "tier": self.tier,
            "eligible": [c.as_dict() for c in self.eligible],
            "capability_gap": [{"mechanism": k, "reason": r} for k, r in self.unexecutable],
            "rejected": [{"mechanism": k, "reason": r} for k, r in self.rejected],
            "profile": self.profile.as_dict(),
        }


def _evaluate(clause, profile):
    """Evaluate one [field, op, value] precondition. Returns (ok, description)."""
    if not isinstance(clause, (list, tuple)) or len(clause) != 3:
        raise SelectionError(f"precondition must be [field, op, value], got {clause!r}")
    field, op, value = clause
    if op == "count-domain-gte":
        actual = profile.domain_count(value[0] if isinstance(value, list) else value)
        threshold = value[1] if isinstance(value, list) and len(value) > 1 else 1
        return actual >= threshold, (
            f"{actual} observation(s) in domain {value!r}, needs {threshold}")
    if field not in PROFILE_FIELDS:
        raise SelectionError(
            f"precondition references unknown profile field {field!r}; "
            "a typo here would silently disqualify a mechanism"
        )
    if op not in OPERATORS:
        raise SelectionError(f"unknown operator {op!r}")
    actual = profile.get(field)
    return OPERATORS[op](actual, value), f"{field}={actual!r} {op} {value!r}"


def select(profile, registry, strategy_rules=(), tier_policy=True):
    """Rank mechanisms the diagnosis supports. Pure. No model, no network.

    ``none`` is always eligible and always last, so selection can conclude that
    no intervention is warranted. A selector that cannot return that is not
    selecting -- it is justifying the tool it already has.
    """
    eligible = []
    unexecutable = []
    rejected = []
    for key in registry.keys():
        mechanism = registry[key]
        if key == "none":
            continue
        preconditions = mechanism.config.get("preconditions") or []
        failures = []
        passes = []
        for clause in preconditions:
            ok, description = _evaluate(clause, profile)
            (passes if ok else failures).append(description)
        if failures:
            rejected.append((key, "; ".join(failures)))
            continue
        # Preconditions passed: the evidence supports this intervention. Whether
        # anything here can DELIVER it is a separate question with a separate
        # answer, and conflating them would hide the capability gap.
        if mechanism.status == "blocked":
            unexecutable.append((key, "supported by the evidence, but the mechanism is "
                                      "blocked: its gates have not cleared"))
            continue
        if not mechanism.executors:
            unexecutable.append((key, "supported by the evidence, but no executor exists "
                                      "for it yet -- this is a capability gap, not a "
                                      "reason to do something else"))
            continue
        eligible.append(Candidate(mechanism, passes or ["no preconditions declared"]))

    eligible.sort(key=lambda c: c.key)
    if "none" in registry:
        eligible.append(Candidate(
            registry["none"],
            ["always available: concluding that no intervention is supported is a "
             "first-class outcome"]))

    tier = _tier_for(profile) if tier_policy else profile.get("current_tier")
    return Selection(profile, eligible, unexecutable, rejected, tier)


def _tier_for(profile):
    """Progressive investment: a tier must be earned by the one below it.

    Strategy rule ST-002. Site Factory reached automated outbound with zero
    validated demand, which is the failure this ordering exists to prevent.
    """
    current = profile.get("current_tier") or "note"
    index = pipeline.tier_index(current)
    if not profile.get("measured_result_available"):
        return current
    if index + 1 >= len(pipeline.TIERS):
        return current
    return pipeline.TIERS[index + 1]


def format_selection(selection):
    lines = []
    chosen = selection.chosen
    lines.append(f"mechanism: {chosen.key if chosen else 'none'}")
    lines.append(f"tier:      {selection.tier}")
    lines.append("")
    lines.append("eligible, in order:")
    for candidate in selection.eligible:
        lines.append(f"  {candidate.key:16} {'; '.join(candidate.reasons)}")
    if selection.unexecutable:
        lines.append("")
        lines.append("CAPABILITY GAP -- supported by the evidence, not executable here:")
        for key, reason in selection.unexecutable:
            lines.append(f"  {key:16} {reason}")
    if selection.rejected:
        lines.append("")
        lines.append("rejected -- the evidence does not support these:")
        for key, reason in selection.rejected:
            lines.append(f"  {key:16} {reason}")
    return "\n".join(lines)
