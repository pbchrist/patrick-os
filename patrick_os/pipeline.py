"""The commercial pipeline: stages, mechanisms, and investment tiers.

This module is deliberately thin. It declares the shape of the work Patrick OS
will eventually orchestrate, and validates that skills locate themselves inside
it. **It does not orchestrate anything yet** -- there is no Opportunity Engine
here, by decision (see decisions/0006).

The durable model is:

    signals -> qualification -> diagnosis -> mechanism selection
            -> sales artifact -> outreach -> result -> learning

Three axes, and keeping them separate is the whole point of this file:

``stage``            where in the commercial pipeline a skill sits.
``mechanism``        what kind of intervention is being sold or delivered.
``investment_tier``  how much has been committed so far.

None of these is ``task_class``. ``task_class`` answers "which model should do
this", which is a routing question and lives in ``config/routes.json``. A
qualification step and an outreach step can share a task class and still belong
to different stages; a website rebuild and a pricing change can share a stage and
still be different mechanisms. Collapsing the axes is how a system ends up
believing that "commercial work" means "the thing Site Factory does".
"""

from __future__ import annotations

import json

from .skills import root

# --- stages ---------------------------------------------------------------
# Ordered. A stage may only consume the output of a stage at or before it.
STAGES = (
    "signal",
    "qualification",
    "diagnosis",
    "mechanism-selection",
    "sales-artifact",
    "outreach",
    "result",
    "learning",
)

STAGE_PURPOSE = {
    "signal": "Raw evidence that something is happening. No claim, no judgement.",
    "qualification": "Is this an opportunity at all, and for whom? Produces pursue / watch / suppress.",
    "diagnosis": "What is actually wrong underneath the presented story, and what does the evidence support?",
    "mechanism-selection": "Which intervention the diagnosis actually implies. May conclude 'none yet'.",
    "sales-artifact": "The thing shown to a buyer: an audit, a one-pager, a demo, a proposal.",
    "outreach": "Getting the artifact in front of the person who can decide.",
    "result": "What actually happened. Replies, money, silence. Recorded whether or not it flatters.",
    "learning": "What the result changes about the rules, the mechanism, or the strategy.",
}


def stage_index(stage):
    try:
        return STAGES.index(stage)
    except ValueError as error:
        raise PipelineError(
            f"unknown stage {stage!r}; expected one of: {', '.join(STAGES)}"
        ) from error


# --- investment tiers -----------------------------------------------------
# Ordered cheapest first. Progressive investment means each tier must be earned
# by evidence from the one before it, not skipped because the buyer seems keen.
TIERS = ("note", "audit", "pilot", "build")

TIER_MEANING = {
    "note": "An observation written down. Costs minutes. Commits nothing.",
    "audit": "A paid or unpaid diagnostic artifact. The Narrative Decision Audit sits here.",
    "pilot": "A small, scoped, reversible intervention that tests the mechanism.",
    "build": "Full delivery. Only reachable when a pilot produced a measured result.",
}


def tier_index(tier):
    try:
        return TIERS.index(tier)
    except ValueError as error:
        raise PipelineError(
            f"unknown investment tier {tier!r}; expected one of: {', '.join(TIERS)}"
        ) from error


class PipelineError(ValueError):
    pass


# --- mechanisms -----------------------------------------------------------
class Mechanism:
    def __init__(self, key, config):
        self.key = key
        self.label = config.get("label", key)
        self.description = config.get("description", "")
        self.executors = list(config.get("executors", []))
        self.evidence_required = list(config.get("evidence_required", []))
        self.tiers = list(config.get("tiers", []))
        self.status = config.get("status", "declared")
        self.config = config

    def __repr__(self):
        return f"<Mechanism {self.key}>"

    def as_dict(self):
        return {
            "key": self.key,
            "label": self.label,
            "status": self.status,
            "executors": self.executors,
            "tiers": self.tiers,
        }


class MechanismRegistry:
    def __init__(self, data, source=None):
        self.source = source
        self.mechanisms = {k: Mechanism(k, v) for k, v in (data.get("mechanisms") or {}).items()}
        self.validate()

    def validate(self):
        if not self.mechanisms:
            raise PipelineError("mechanism registry declares no mechanisms")
        for mechanism in self.mechanisms.values():
            for tier in mechanism.tiers:
                tier_index(tier)

    def __contains__(self, key):
        return key in self.mechanisms

    def __getitem__(self, key):
        if key not in self.mechanisms:
            raise PipelineError(
                f"unknown mechanism {key!r}; declared: {', '.join(sorted(self.mechanisms))}"
            )
        return self.mechanisms[key]

    def keys(self):
        return sorted(self.mechanisms)


def registry_path(base=None):
    return root(base) / "config" / "mechanisms.json"


def load_mechanisms(path=None, base=None):
    target = path or registry_path(base)
    if not target.is_file():
        raise PipelineError(f"no mechanism registry at {target}")
    with open(target, encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as error:
            raise PipelineError(f"{target}: invalid JSON: {error}") from error
    return MechanismRegistry(data, source=str(target))


# --- coverage -------------------------------------------------------------
def coverage(skill_list, mechanisms=None):
    """Which stages and mechanisms currently have a skill, and which do not.

    This is the cheapest honest answer to "how much of the pipeline exists".
    Right now most of it does not, and a system that cannot say so will keep
    behaving as though the two stages it has are the whole business.
    """
    by_stage = {stage: [] for stage in STAGES}
    unstaged = []
    for skill in skill_list:
        stage = skill.meta.get("stage")
        if stage in by_stage:
            by_stage[stage].append(skill.slug)
        else:
            unstaged.append(skill.slug)
    by_mechanism = {}
    if mechanisms is not None:
        for key in mechanisms.keys():
            by_mechanism[key] = []
        for skill in skill_list:
            for key in skill.meta.get("mechanisms") or []:
                by_mechanism.setdefault(key, []).append(skill.slug)
    return {"by_stage": by_stage, "unstaged": unstaged, "by_mechanism": by_mechanism}
