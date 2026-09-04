"""The regression harness.

Two layers, both offline:

1. **Structural** -- every skill parses, declares every required section, and has
   at least one fixture. A skill that cannot be validated cannot be trusted to
   carry a rule.
2. **Fixture** -- each fixture binds inputs, composes a work order, resolves a
   route, and asserts against the result. Assertions are deliberately about the
   *composed work order and the routing decision*, not about model output: those
   are the parts Patrick OS is responsible for, and they are reproducible.

Fixture shape (``skills/<slug>/fixtures/<name>.json``)::

    {
      "name": "escalates-on-thin-evidence",
      "inputs": {"subreddit": "recruiting", "window_days": 7},
      "expect": {
        "must_contain": ["G-002"],
        "must_not_contain": ["unlock"],
        "route_provider": "local-qwen",
        "route_allows": ["local-qwen", "hermes-codex"],
        "route_denies": ["anthropic-opus"],
        "invalid_inputs": false
      }
    }
"""

from __future__ import annotations

import re
import unittest
from io import StringIO

_WHITESPACE = re.compile(r"\s+")


def _flat(text):
    return _WHITESPACE.sub(" ", text).strip().lower()

from . import runner, skills
from .router import table as route_table


def check_fixture(skill, fixture, table, base=None):
    """Run one fixture. Returns a list of failure strings (empty means pass)."""
    expect = fixture.get("expect") or {}
    failures = []
    inputs = fixture.get("inputs") or {}

    if expect.get("invalid_inputs"):
        try:
            skill.bind(inputs)
        except skills.SkillError:
            return []
        return ["expected input binding to fail, but it succeeded"]

    try:
        planned = runner.plan(skill, inputs, base=base, table=table)
    except skills.SkillError as error:
        return [f"input binding failed: {error}"]

    work_order = planned["work_order"]
    # Whitespace-insensitive: a skill's prose is hard-wrapped, so a phrase that
    # spans a line break is present but would not match a literal search. Fixtures
    # should assert on content, not on where the author happened to wrap.
    lowered = _flat(work_order)
    for needle in expect.get("must_contain", []):
        if _flat(needle) not in lowered:
            failures.append(f"work order is missing required text {needle!r}")
    for needle in expect.get("must_not_contain", []):
        if _flat(needle) in lowered:
            failures.append(f"work order contains forbidden text {needle!r}")

    decision = planned["decision"]
    chosen = decision.chosen.key if decision.chosen else None
    if "route_provider" in expect and chosen != expect["route_provider"]:
        failures.append(
            f"route chose {chosen!r}, fixture expects {expect['route_provider']!r}"
        )
    if "route_route" in expect and decision.route_name != expect["route_route"]:
        failures.append(
            f"matched route {decision.route_name!r}, fixture expects {expect['route_route']!r}"
        )
    eligible = {c.key for c in decision.candidates}
    for key in expect.get("route_allows", []):
        if key not in eligible:
            failures.append(f"provider {key!r} should be eligible but was rejected")
    for key in expect.get("route_denies", []):
        if key in eligible:
            failures.append(f"provider {key!r} should be ineligible but was eligible")
    if expect.get("max_payload_bytes") is not None:
        size = len(work_order.encode("utf-8"))
        if size > expect["max_payload_bytes"]:
            failures.append(
                f"work order is {size} bytes, above the fixture cap "
                f"{expect['max_payload_bytes']}"
            )
    return failures


def check_behavioral(skill, fixture):
    """Run a skill's declared output checks against a real produced output."""
    from . import checks

    findings = checks.run(fixture["output"], skill.output_checks,
                          fixture.get("context"))
    verdict = checks.verdict(findings)
    failures = []
    if verdict != fixture["expect_verdict"]:
        failures.append(
            f"verdict {verdict!r}, fixture expects {fixture['expect_verdict']!r}"
            + (f" (found: {[f.check for f in findings]})" if findings else " (no findings)")
        )
    fired = {f.check for f in findings}
    for expected in fixture.get("expect_defects", []):
        if expected not in fired:
            failures.append(f"expected check {expected!r} to fire, it did not")
    for unexpected in sorted(fired - set(fixture.get("expect_defects", []))):
        if fixture.get("allow_extra_defects"):
            continue
        failures.append(f"check {unexpected!r} fired but the fixture does not expect it")
    return failures


def run_suite(base=None, only=None, include_unit=True):
    """Run structural checks, fixtures, and (optionally) the unit tests."""
    report = {"skills": [], "unit": None, "ok": True, "counts": {"pass": 0, "fail": 0}}
    try:
        table = route_table.load(base=base)
    except Exception as error:  # noqa: BLE001 - reported, not raised
        report["ok"] = False
        report["error"] = f"route table failed to load: {error}"
        return report

    targets = [skills.load_skill(only, base)] if only else skills.list_skills(base)
    for skill in targets:
        entry = {"skill": skill.slug, "structural": [], "fixtures": []}
        entry["structural"] = skill.validate()
        if entry["structural"]:
            report["ok"] = False
            report["counts"]["fail"] += 1
        else:
            report["counts"]["pass"] += 1
        for fixture in skill.fixtures():
            failures = check_fixture(skill, fixture, table, base)
            entry["fixtures"].append(
                {"name": fixture.get("name"), "failures": failures, "ok": not failures}
            )
            if failures:
                report["ok"] = False
                report["counts"]["fail"] += 1
            else:
                report["counts"]["pass"] += 1
        entry["behavioral"] = []
        for fixture in skill.behavioral_fixtures():
            failures = check_behavioral(skill, fixture)
            entry["behavioral"].append(
                {"name": fixture.get("name"), "failures": failures, "ok": not failures}
            )
            if failures:
                report["ok"] = False
                report["counts"]["fail"] += 1
            else:
                report["counts"]["pass"] += 1
        report["skills"].append(entry)

    if include_unit:
        report["unit"] = _run_unit_tests(base)
        if not report["unit"]["ok"]:
            report["ok"] = False
        report["counts"]["pass"] += report["unit"]["passed"]
        report["counts"]["fail"] += report["unit"]["failed"]
    return report


def _run_unit_tests(base=None):
    directory = skills.root(base) / "tests"
    if not directory.is_dir():
        return {"ok": True, "passed": 0, "failed": 0, "output": "no tests/ directory"}
    loader = unittest.TestLoader()
    suite = loader.discover(str(directory), top_level_dir=str(skills.root(base)))
    stream = StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    failed = len(result.failures) + len(result.errors)
    return {
        "ok": result.wasSuccessful(),
        "passed": result.testsRun - failed,
        "failed": failed,
        "output": stream.getvalue(),
    }


def format_report(report):
    lines = []
    if report.get("error"):
        lines.append(f"FAIL  {report['error']}")
    for entry in report["skills"]:
        if entry["structural"]:
            lines.append(f"FAIL  {entry['skill']}  (structure)")
            for problem in entry["structural"]:
                lines.append(f"        - {problem}")
        else:
            lines.append(f"ok    {entry['skill']}  (structure)")
        for fixture in entry["fixtures"]:
            if fixture["ok"]:
                lines.append(f"ok    {entry['skill']} :: {fixture['name']}")
            else:
                lines.append(f"FAIL  {entry['skill']} :: {fixture['name']}")
                for problem in fixture["failures"]:
                    lines.append(f"        - {problem}")
        for fixture in entry.get("behavioral", []):
            label = f"{entry['skill']} :: [behavioral] {fixture['name']}"
            if fixture["ok"]:
                lines.append(f"ok    {label}")
            else:
                lines.append(f"FAIL  {label}")
                for problem in fixture["failures"]:
                    lines.append(f"        - {problem}")
    unit = report.get("unit")
    if unit:
        state = "ok   " if unit["ok"] else "FAIL "
        lines.append(f"{state} unit tests: {unit['passed']} passed, {unit['failed']} failed")
        if not unit["ok"]:
            lines.append(unit["output"])
    counts = report["counts"]
    lines.append("")
    lines.append(
        f"{'PASS' if report['ok'] else 'FAIL'} — {counts['pass']} passed, {counts['fail']} failed"
    )
    return "\n".join(lines)
