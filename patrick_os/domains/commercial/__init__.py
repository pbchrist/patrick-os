"""The commercial domain: finding, qualifying and serving paying work.

Everything here was once in the core, where it did not belong. `stage` was a
required field on every skill and a fiction skill could not validate; mechanism
selection, investment tiers and sales outcomes sat beside the router as though
they were operating-system concerns.

Site Factory is an executor for one mechanism inside this domain. It is not the
domain, and the domain is not Patrick OS.
"""

from __future__ import annotations

from . import checks as _checks
from . import results, selection, workflow  # noqa: F401  (re-exported)

CHECKS = _checks.CHECKS


def validate_skill(skill):
    """Rules that apply to a skill BECAUSE it declares domain: commercial.

    None of this reaches a skill that declares no domain -- that is the whole
    reason the pack exists.
    """
    problems = []
    stage = skill.meta.get("stage")
    if not stage:
        problems.append(
            "commercial skills must declare a stage (one of: "
            + ", ".join(workflow.STAGES) + ")")
    elif stage not in workflow.STAGES:
        problems.append(
            f"unknown stage {stage!r}; expected one of: " + ", ".join(workflow.STAGES))

    tier = skill.meta.get("investment_tier")
    if tier and tier not in workflow.TIERS:
        problems.append(
            f"unknown investment_tier {tier!r}; expected one of: "
            + ", ".join(workflow.TIERS))

    declared = skill.meta.get("mechanisms")
    if isinstance(declared, str):
        declared = [declared]
    declared = list(declared or [])
    agnostic = bool(skill.meta.get("mechanism_agnostic", False))
    if declared and agnostic:
        problems.append("declares both mechanisms and mechanism_agnostic: true; pick one")
    if not declared and not agnostic:
        problems.append(
            "declares neither mechanisms nor mechanism_agnostic: true -- inside this "
            "domain a skill that does not say which interventions it serves is assumed "
            "to serve the only one anybody built")
    if declared:
        try:
            registry = workflow.load_mechanisms(base=skill._base)
        except workflow.PipelineError as error:
            problems.append(str(error))
        else:
            for key in declared:
                if key not in registry:
                    problems.append(
                        f"unknown mechanism {key!r}; declared in the commercial pack: "
                        + ", ".join(registry.keys()))
    return problems
