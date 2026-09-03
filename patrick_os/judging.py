"""Judging a produced output.

Two layers, and the order matters. Site Factory finding SF-08, verified: its
deterministic lint ran *before* the judge and deleted the two evidence-richest
candidates over the word "metadata". So here the deterministic layer runs first
but only **annotates** on style; it eliminates only on fact integrity, and the
judge always sees the output regardless.

The independence rule is enforced in code rather than remembered. SF-07, verified
by measurement: Site Factory's judge shared a calibration example with its writer,
the single passing output scored 0.590 trigram similarity to that example against
0.015-0.081 for the four failures, and the judge's own rejection text cited "the
rhetorical structure of the positive calibration" as its standard. A judge that
shares an answer key with the writer produces a number carrying no information.

So: the judge provider must differ from the writer provider, and the judge prompt
is built from the skill's own quality checks -- never from an exemplar output.
There is deliberately no calibration example anywhere in this module.
"""

from __future__ import annotations

import json

from . import checks
from .router import TaskSpec, resolve
from .router import table as route_table


class JudgeError(RuntimeError):
    pass


class IndependenceError(JudgeError):
    """The judge and the writer are the same provider. Refuse rather than measure."""


def deterministic(skill, output):
    findings = checks.run(output, skill.output_checks)
    return {
        "verdict": checks.verdict(findings),
        "blocking": [f.as_dict() for f in findings if f.severity == checks.BLOCKING],
        "advisory": [f.as_dict() for f in findings if f.severity == checks.ADVISORY],
    }


def build_prompt(skill, output, deterministic_result):
    """The judge prompt is the skill's own quality checks, not an exemplar.

    Nothing in here shows the judge what a good answer looks like, because that is
    precisely how a judge stops measuring quality and starts measuring similarity.
    """
    lines = [
        "You are an independent judge. You did not write this output and you have",
        "no example of a good one. Judge it only against the criteria below.",
        "",
        f"## Skill: {skill.slug}",
        f"Purpose: {skill.purpose}",
        "",
        "## Required output shape",
        "",
        skill.section("Outputs") or "(none declared)",
        "",
        "## Quality checks the output must satisfy",
        "",
        skill.section("Quality checks") or "(none declared)",
        "",
        "## Failure modes to look for specifically",
        "",
        skill.section("Failure modes") or "(none declared)",
        "",
        "## Conditions that require escalation to a human",
        "",
        skill.section("Escalation") or "(none declared)",
        "",
        "## Deterministic checks already run",
        "",
        json.dumps(deterministic_result, indent=2),
        "",
        "Those cover only what a regex can see. Judge what it cannot: whether a",
        "claim is actually supported by the cited evidence, whether the output",
        "quietly exceeds what the evidence permits, and whether an escalation",
        "condition is met and was ignored.",
        "",
        "## Output under judgement",
        "",
        "-----BEGIN OUTPUT-----",
        output,
        "-----END OUTPUT-----",
        "",
        "Verdict vocabulary — these are four different things, do not collapse them:",
        "  pass      the output meets the bar and no escalation condition is met.",
        "  repair    fixable defects; the approach is right.",
        "  reject    a claim the evidence does not support, or a forbidden offer.",
        "  escalate  the output may be fine, but an Escalation condition above is",
        "            met and a human must decide. Use this instead of 'reject'",
        "            when your only finding is an escalation condition.",
        "",
        "Reply with JSON only, no prose around it:",
        '{"verdict": "pass" | "repair" | "reject" | "escalate",',
        ' "unsupported_claims": [{"quote": "...", "why": "..."}],',
        ' "escalation_required": true | false,',
        ' "escalation_reason": "..." | null,',
        ' "repairs": ["..."],',
        ' "reasoning": "one paragraph"}',
        "",
        "Quote verbatim from the output. Do not invent a quote. If you cannot",
        'quote it, it is not a finding. An empty findings list is a valid answer.',
    ]
    return "\n".join(lines)


def choose_judge(writer_provider_key, base=None, table=None):
    """Resolve a judge provider that is not the writer. Refuses rather than reuse."""
    table = table or route_table.load(base=base)
    decision = resolve(TaskSpec("judge", needs_capabilities=["judge"]), table)
    for candidate in decision.candidates:
        if candidate.key != writer_provider_key:
            return candidate.provider, decision
    raise IndependenceError(
        "no judge provider is available that differs from the writer "
        f"({writer_provider_key!r}). A judge sharing a model with the writer "
        "measures similarity, not quality (Site Factory SF-07). Refusing to judge."
    )


def judge(skill, output, *, writer_provider=None, base=None, table=None,
          transport=None, execute=False):
    """Run deterministic checks, then optionally an independent model judge."""
    result = {"skill": skill.slug, "deterministic": deterministic(skill, output)}
    if not execute:
        result["model_judge"] = None
        result["note"] = (
            "Deterministic layer only. Pass execute=True to call an independent "
            "judge provider."
        )
        return result

    provider, decision = choose_judge(writer_provider, base=base, table=table)
    prompt = build_prompt(skill, output, result["deterministic"])
    result["judge_provider"] = provider.key
    result["writer_provider"] = writer_provider
    result["judge_route"] = decision.route_name
    if transport is not None:
        raw = transport(prompt, provider=provider)
    else:
        from .router import adapters

        raw = adapters.complete(provider, prompt)
    result["model_judge"] = _parse_json(raw)
    result["model_judge_raw"] = raw
    return result


def _parse_json(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
            return value
        except json.JSONDecodeError:
            continue
    return {"verdict": "unparseable", "reasoning": cleaned[:500]}


def format_result(result):
    lines = []
    det = result["deterministic"]
    lines.append(f"deterministic: {det['verdict'].upper()}")
    for item in det["blocking"]:
        lines.append(f"  BLOCKING {item['check']}: {item['message']}")
        if item["evidence"]:
            lines.append("           evidence: " + "; ".join(str(e) for e in item["evidence"]))
    for item in det["advisory"]:
        lines.append(f"  advisory {item['check']}: {item['message']}")
        if item["evidence"]:
            lines.append("           evidence: " + "; ".join(str(e) for e in item["evidence"]))
    if not det["blocking"] and not det["advisory"]:
        lines.append("  no findings")
    model = result.get("model_judge")
    if model is None:
        lines.append("")
        lines.append(result.get("note", ""))
        return "\n".join(lines)
    lines.append("")
    lines.append(f"model judge:   {str(model.get('verdict', '?')).upper()}  "
                 f"(judge={result.get('judge_provider')}, "
                 f"writer={result.get('writer_provider')})")
    for claim in model.get("unsupported_claims") or []:
        lines.append(f"  unsupported: {claim.get('quote', '')!r}")
        lines.append(f"               {claim.get('why', '')}")
    if model.get("escalation_required"):
        lines.append(f"  ESCALATE: {model.get('escalation_reason')}")
    for repair in model.get("repairs") or []:
        lines.append(f"  repair: {repair}")
    if model.get("reasoning"):
        lines.append(f"  reasoning: {model['reasoning']}")
    return "\n".join(lines)
