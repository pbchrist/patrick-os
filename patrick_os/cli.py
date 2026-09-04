"""`patrick` — the task runner.

    patrick skills list
    patrick skills show <slug>
    patrick run <slug> --input k=v [--execute]
    patrick voice show [--scope S] [--skill S]
    patrick route <task-class> [--payload-bytes N] [--private]
    patrick feedback add --skill S --original f1 --edited f2
    patrick feedback list | show <id> | promote <id> | reject <id>
    patrick test [<slug>]
    patrick decision add --title "..." | list
    patrick doctor
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import decisions, feedback, judging, pipeline, results, retrieval, runner, selection, skills, testing, voice
from .router import TaskSpec, resolve
from .router import table as route_table


def _parse_inputs(pairs):
    parsed = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if not sep:
            raise SystemExit(f"--input expects key=value, got {pair!r}")
        key = key.strip()
        value = value.strip()
        try:
            parsed[key] = json.loads(value)
        except json.JSONDecodeError:
            parsed[key] = value
    return parsed


def _read(path):
    return Path(path).expanduser().read_text(encoding="utf-8")


# --- commands -------------------------------------------------------------
def cmd_skills(args):
    if args.action == "list":
        found = skills.list_skills(args.root)
        if not found:
            print("no skills found")
            return 0
        width = max(len(s.slug) for s in found)
        for skill in found:
            problems = skill.validate()
            flag = "  " if not problems else "! "
            print(f"{flag}{skill.slug.ljust(width)}  {skill.task_class:18} {skill.purpose}")
        if any(s.validate() for s in found):
            print("\n! = fails structural validation; run `patrick test` for detail")
        return 0

    skill = skills.load_skill(args.slug, args.root)
    print(f"# {skill.slug}  (v{skill.meta.get('version')})")
    print(f"purpose:     {skill.purpose}")
    print(f"task class:  {skill.task_class}")
    print(f"channel:     {skill.channel or '-'}")
    print(f"project:     {skill.project or '-'}")
    print(f"outputs:     {skill.output_kind}"
          + ("  (outward-facing: draft only, never sent)" if skill.is_outward else ""))
    print(f"dry run:     default {'on' if skill.dry_run_default else 'OFF'}")
    print(f"voice scopes: {' -> '.join(skill.voice_scopes)}")
    print("\ninputs:")
    for spec in skill.inputs:
        required = "required" if spec.get("required", True) else "optional"
        default = f", default={spec['default']!r}" if "default" in spec else ""
        print(f"  - {spec['name']} ({required}{default}) {spec.get('description', '')}")
    print("\nfixtures:")
    for fixture in skill.fixtures():
        print(f"  - {fixture['name']}")
    problems = skill.validate()
    if problems:
        print("\nSTRUCTURAL PROBLEMS:")
        for problem in problems:
            print(f"  - {problem}")
    if args.body:
        print("\n" + "-" * 60)
        print(skill.body.strip())
    return 0


def cmd_run(args):
    skill = skills.load_skill(args.slug, args.root)
    provided = _parse_inputs(args.input)
    execute = bool(args.execute)
    if execute and skill.is_outward:
        print(
            f"note: {skill.slug} is outward-facing. --execute writes a DRAFT to disk.\n"
            "      Patrick OS has no send path; a human moves it or discards it.",
            file=sys.stderr,
        )
    record = runner.run(skill, provided, execute=execute, base=args.root,
                        retrieve=args.retrieve, backend=args.backend)
    if args.json:
        print(json.dumps(record, indent=2, sort_keys=True, default=str))
        return 0
    print(f"run:      {record['run_id']}  ({record['mode']})")
    route = record["route"]
    chosen = route["chosen"]
    print(f"route:    {route['route']} -> {chosen['provider'] if chosen else 'NONE'}")
    if chosen:
        print(f"fallback: {', '.join(f['provider'] for f in route['fallbacks']) or '-'}")
    if route["rejected"]:
        print("rejected:")
        for item in route["rejected"]:
            print(f"          {item['provider']}: {item['reason']}")
    print(f"artifacts: {skills.root(args.root) / 'runs' / record['run_id']}")
    if record.get("note"):
        print(f"note:     {record['note']}")
    return 0


def cmd_voice(args):
    namespace = "strategy" if args.strategy else "voice"
    if namespace == "strategy":
        scopes = [args.scope] if args.scope else voice.all_scopes(args.root, namespace)
        rules = voice.compose(scopes, args.root, namespace)
        if not rules:
            print(f"no strategy rules for scopes: {', '.join(scopes) or '(none)'}")
            return 0
        print(f"# {len(rules)} strategy rules  ({' -> '.join(scopes)})\n")
        for rule in rules:
            print(f"[{rule.id}] ({rule.scope}) {rule.text}")
        return 0
    if args.skill:
        skill = skills.load_skill(args.skill, args.root)
        scopes = skill.voice_scopes
    elif args.scope:
        scopes = [args.scope]
    else:
        scopes = voice.all_scopes(args.root)
    rules = voice.compose(scopes, args.root)
    if not rules:
        print(f"no rules for scopes: {', '.join(scopes)}")
        return 0
    print(f"# {len(rules)} rules  ({' -> '.join(scopes)})\n")
    for rule in rules:
        print(f"[{rule.id}] ({rule.scope}) {rule.text}")
    return 0


def cmd_route(args):
    table = route_table.load(base=args.root)
    task = TaskSpec(
        args.task_class,
        payload_bytes=args.payload_bytes,
        needs_tools=args.needs_tools,
        min_quality=args.min_quality,
        privacy="local-only" if args.private else "normal",
    )
    decision = resolve(task, table)
    if args.json:
        print(json.dumps(decision.as_dict(), indent=2))
        return 0
    print(f"task class:  {args.task_class}")
    print(f"matched:     {decision.route_name}")
    print(f"chosen:      {decision.chosen.key if decision.chosen else 'NONE'}")
    for candidate in decision.candidates:
        print(f"  {candidate.key:16} score={candidate.score:>12.2f}  {'; '.join(candidate.reasons)}")
    for rejection in decision.rejected:
        print(f"  {rejection.provider_key:16} REJECTED     {rejection.reason}")
    return 0 if decision.chosen else 1


def _print_feedback(entry):
    print(f"recorded {entry['id']}  status={entry['status']}")
    for edit in entry["edits"]:
        print(f"  {edit['kind']:10} scope={edit['scope']:22} {edit['rationale']}")
    if entry["proposals"]:
        print("\nproposals (nothing applied yet):")
        for index, proposal in enumerate(entry["proposals"]):
            print(f"  [{index}] {proposal['scope']}: {proposal['rule']}")
        print("\nThe scope above is derived from where the correction repeated and is")
        print("usually right. The wording is phrased mechanically from the diff and")
        print("usually is not -- rewrite it when you promote:")
        print(f"  patrick feedback promote {entry['id']} --text \"...\"")
    else:
        print("\nNo rule proposed. A correction stays local until it repeats "
              "in another context.")
    return 0


def cmd_feedback(args):
    if args.action == "reject-output":
        entry = feedback.add_rejection(
            output=_read(args.output), reason=args.reason, skill=args.skill,
            channel=args.channel, project=args.project, run_id=args.run, base=args.root)
        return _print_feedback(entry)

    if args.action == "strategy":
        entry = feedback.add_strategy(
            lesson=args.text, evidence=args.evidence, scope=args.scope,
            mechanism=args.mechanism, segment=args.segment, project=args.project,
            base=args.root)
        print(f"recorded {entry['id']}  layer=strategy  status={entry['status']}")
        for index, proposal in enumerate(entry["proposals"]):
            print(f"  [{index}] {proposal['scope']}: {proposal['rule']}")
            print(f"       {proposal['rationale']}")
        print(f"\nThis promotes into strategy/, not voice/. Review the scope, then:")
        print(f"  patrick feedback promote {entry['id']}")
        return 0

    if args.action == "correct":
        entry = feedback.add_correction(
            correction=args.text, skill=args.skill, channel=args.channel,
            project=args.project, scope=args.scope, base=args.root)
        print(f"recorded {entry['id']}  status={entry['status']}")
        print("A correction you stated outright is proposed immediately -- the")
        print("repetition threshold exists to stop Patrick OS inferring rules, not")
        print("to second-guess yours. Review the scope, then:")
        print(f"  patrick feedback promote {entry['id']}")
        for index, proposal in enumerate(entry["proposals"]):
            print(f"  [{index}] {proposal['scope']}: {proposal['rule']}")
        return 0

    if args.action == "add":
        entry = feedback.add(
            original=_read(args.original),
            edited=_read(args.edited),
            skill=args.skill,
            channel=args.channel,
            project=args.project,
            run_id=args.run,
            note=args.note,
            base=args.root,
        )
        return _print_feedback(entry)
        if entry["proposals"]:
            print("\nproposals (nothing applied yet):")
            for index, proposal in enumerate(entry["proposals"]):
                print(f"  [{index}] {proposal['scope']}: {proposal['rule']}")
            print("\nThe scope above is derived from where the correction repeated and is")
            print("usually right. The wording is phrased mechanically from the diff and")
            print("usually is not -- rewrite it when you promote:")
            print(f"  patrick feedback promote {entry['id']} --text \"...\"")
        else:
            print("\nNo rule proposed. A correction stays local until it repeats "
                  "in another context.")
        return 0

    if args.action == "list":
        entries = feedback.load_all(args.root)
        if not entries:
            print("no feedback recorded")
            return 0
        for entry in entries:
            proposals = entry.get("proposals") or []
            print(f"{entry['id']}  {entry['status']:20} skill={entry.get('skill') or '-':22}"
                  f" proposals={len(proposals)}")
        return 0

    if args.action == "show":
        print(json.dumps(feedback.load_entry(args.id, args.root), indent=2, sort_keys=True))
        return 0

    if args.action == "promote":
        result = feedback.promote(
            args.id, index=args.index, scope=args.scope, text=args.text, base=args.root
        )
        print(f"promoted {result['rule_id']} into {result['scope']}")
        print(f"  {result['text']}")
        print("regression suite passed; changelog updated at feedback/CHANGELOG.md")
        return 0

    if args.action == "reject":
        feedback.reject(args.id, index=args.index, reason=args.reason, base=args.root)
        print(f"rejected proposal {args.index} of {args.id}")
        return 0
    return 1


def _run_context(output_path):
    """Load the inputs of the run that produced this output, if it came from one.

    Checks that resolve an output against its source need the source. When the
    output sits in a run directory, run.json already has it -- asking the user to
    pass it again would mean the check that matters most is the one most often
    skipped.
    """
    record = Path(output_path).expanduser().resolve().parent / "run.json"
    if not record.is_file():
        return {}
    try:
        data = json.loads(record.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {k: str(v) for k, v in (data.get("inputs") or {}).items()}


def cmd_judge(args):
    skill = skills.load_skill(args.slug, args.root)
    output = _read(args.output)
    context = {} if args.no_context else _run_context(args.output)
    try:
        result = judging.judge(skill, output, writer_provider=args.writer,
                               base=args.root, execute=args.execute, context=context)
    except judging.IndependenceError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(judging.format_result(result))
    return 0 if result["deterministic"]["verdict"] != "blocked" else 1


def cmd_test(args):
    report = testing.run_suite(
        base=args.root, only=args.slug, include_unit=not args.no_unit
    )
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(testing.format_report(report))
    return 0 if report["ok"] else 1


def cmd_decision(args):
    if args.action == "list":
        found = decisions.list_decisions(args.root)
        if not found:
            print("no decisions recorded")
            return 0
        for item in found:
            meta = item["meta"]
            print(f"{meta.get('id')}  {meta.get('date')}  {meta.get('kind'):13} "
                  f"{meta.get('title')}")
        return 0
    result = decisions.add(
        args.title,
        kind=args.kind,
        context=args.context or "",
        decision=args.decision or "",
        alternatives=args.alternatives or "",
        consequences=args.consequences or "",
        supersedes=args.supersedes,
        base=args.root,
    )
    print(f"recorded decision {result['id']} at {result['path']}")
    return 0


def cmd_select(args):
    """Choose a mechanism from an extracted profile. Deterministic; calls nothing."""
    raw = json.loads(_read(args.profile)) if args.profile else json.loads(args.json_profile)
    if isinstance(raw, dict) and "Profile" in raw:
        raw = raw["Profile"]
    profile = selection.Profile(**raw)
    registry = pipeline.load_mechanisms(base=args.root)
    result = selection.select(profile, registry)
    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
        return 0
    print(selection.format_selection(result))
    return 0


def cmd_result(args):
    if args.action == "record":
        entry = results.record(
            opportunity=args.opportunity, mechanism=args.mechanism, tier=args.tier,
            outcome=args.outcome, evidence=args.evidence, amount=args.amount,
            note=args.note, base=args.root)
        print(f"recorded {entry['id']}: {entry['opportunity']} / {entry['mechanism']} "
              f"/ {entry['tier']} -> {entry['outcome']}")
        if entry.get("lesson_prompt"):
            print("\n" + entry["lesson_prompt"])
        return 0
    rows = results.load_all(args.root)
    if not rows:
        print("no results recorded")
        print("Nothing has been sent, so nothing has come back. strategy/ can only be")
        print("written by hand until this has entries.")
        return 0
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    print(results.format_table(rows))
    return 0


def cmd_retrieval(args):
    if args.action == "probe":
        caps = retrieval.probe_all(args.root)
        if args.json:
            print(json.dumps({k: c.as_dict() for k, c in caps.items()}, indent=2))
            return 0
        print("Hermes runtimes, probed live. Capability is discovered per runtime and")
        print("never generalized from another install.\n")
        for key, capability in caps.items():
            mark = "UP  " if capability.reachable else "DOWN"
            web = "web-research YES" if capability.can_web_research else "web-research no "
            print(f"  {mark} {key:22} {web}  {capability.detail}")
            if capability.reachable and capability.search_backend:
                print(f"       search={capability.search_backend} "
                      f"extract={capability.extract_backend}")
        able = [k for k, c in caps.items() if c.can_web_research]
        print()
        print(f"  web research available on: {', '.join(able) or 'NONE'}")
        return 0 if able else 1

    if args.action == "fetch":
        payload = retrieval.retrieve(args.query, backend=args.backend, base=args.root,
                                     timeout=args.timeout)
        print(json.dumps(payload, indent=2))
        return 0

    registry = retrieval.load_registry(args.root)
    for name, source in (registry.get("sources") or {}).items():
        print(f"{name}  (default: {source['default_backend']})")
        for backend, spec in source["backends"].items():
            flag = "x" if spec.get("executable") else " "
            print(f"  [{flag}] {backend:16} {spec['status']:10} {spec.get('how','')[:70]}")
            if spec.get("blocked_reason"):
                print(f"      blocked: {spec['blocked_reason'][:90]}")
    return 0


def cmd_judges(args):
    """Which independent judge pairs actually exist right now.

    Answers the only question that matters about judge independence: given who
    wrote something, is there a reachable judge from a DIFFERENT vendor?
    """
    from .router import adapters

    table = route_table.load(base=args.root)
    reachable = {}
    for key, provider in sorted(table.providers.items()):
        ok, detail = adapters.probe(provider) if args.probe else (None, "not probed")
        reachable[key] = (ok, detail)

    print("independence is ranked by VENDOR, not provider key: two providers from")
    print("one vendor share a model family and a safety stack (Site Factory SF-07).")
    print()
    writers = [k for k, p in sorted(table.providers.items())
               if not args.probe or reachable[k][0]]
    if not writers:
        print("no reachable providers")
        return 1
    worst = None
    for writer in writers:
        try:
            candidates, _ = judging.independent_candidates(writer, base=args.root,
                                                           table=table)
        except judging.IndependenceError as error:
            print(f"  {writer:18} NO INDEPENDENT JUDGE -- {error}")
            worst = 0
            continue
        usable = [c for c in candidates if not args.probe or reachable[c.key][0]]
        if not usable:
            print(f"  {writer:18} no REACHABLE independent judge "
                  f"(declared: {', '.join(c.key for c in candidates)})")
            worst = 0
            continue
        best = usable[0]
        strength = judging.independence_of(best, table.providers[writer])
        worst = strength if worst is None else min(worst, strength)
        label = {2: "strong", 1: "WEAK  "}[strength]
        print(f"  writer {writer:18} -> judge {best.key:18} {label}  "
              f"({table.providers[writer].vendor} vs {best.vendor})")
    print()
    if worst == 2:
        print("Every reachable writer has a different-vendor judge. Independence is")
        print("satisfied by existing infrastructure; nothing needs to be purchased or")
        print("authenticated.")
    elif worst == 1:
        print("At least one writer can only be judged by its own vendor. That separates")
        print("the model and nothing else. A second reachable vendor would fix it.")
    else:
        print("At least one writer has no independent judge at all.")
    return 0


def cmd_pipeline(args):
    """Show how much of the commercial pipeline actually has a skill behind it."""
    found = skills.list_skills(args.root)
    registry = pipeline.load_mechanisms(base=args.root)
    report = pipeline.coverage(found, registry)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("signals -> qualification -> diagnosis -> mechanism selection")
    print("        -> sales artifact -> outreach -> result -> learning")
    print()
    print("STAGE COVERAGE")
    for stage in pipeline.STAGES:
        owners = report["by_stage"][stage]
        tool = report["tooling"].get(stage)
        if owners:
            print(f"  {stage:20} {', '.join(owners)}")
        elif tool:
            print(f"  {stage:20} [tooling] {tool.split(' — ')[0]}")
        else:
            print(f"· {stage:20} (nothing)")
        if args.verbose:
            print(f"    {pipeline.STAGE_PURPOSE[stage]}")
            if tool:
                print(f"    why tooling: {tool.split(' — ', 1)[-1]}")
    empty = len(report["empty"])
    print()
    print("MECHANISM COVERAGE")
    for key in registry.keys():
        mechanism = registry[key]
        owners = report["by_mechanism"].get(key) or []
        print(f"  {key:16} {mechanism.status:10} "
              f"{', '.join(owners) if owners else '(no skill)'}")
    print()
    agnostic = [s.slug for s in found if s.mechanism_agnostic]
    print(f"{len(report['covered'])}/{len(pipeline.STAGES)} stages covered "
          f"({len(report['tooling'])} by tooling); {empty} not.")
    print(f"mechanism-agnostic skills: {', '.join(agnostic) or 'none'}")
    if report["unstaged"]:
        print(f"UNSTAGED (will fail validation): {', '.join(report['unstaged'])}")
    print()
    if empty:
        print("The empty stages are the point. Patrick OS must not behave as though")
        print("the stages it has are the whole business.")
    else:
        print("Every stage is covered. That is not the same as every stage being good:")
        print("`patrick result list` is empty, so no mechanism has a measured outcome")
        print("behind it and strategy/ is still written by hand.")
    print("See docs/ARCHITECTURE.md and decisions/0006.")
    return 0


def cmd_doctor(args):
    base = skills.root(args.root)
    print(f"root:          {base}")
    ok = True
    try:
        table = route_table.load(base=args.root)
        print(f"route table:   {len(table.providers)} providers, {len(table.routes)} routes")
    except Exception as error:  # noqa: BLE001
        print(f"route table:   BROKEN — {error}")
        ok = False
        table = None
    found = skills.list_skills(args.root)
    print(f"skills:        {len(found)}")
    print(f"voice scopes:  {len(voice.all_scopes(args.root))}")
    print(f"feedback:      {len(feedback.load_all(args.root))} entries")
    print(f"decisions:     {len(decisions.list_decisions(args.root))}")
    if table:
        import os

        from .router import adapters

        print("\nproviders (credentials are read from the environment or from a CLI's "
              "own login, never from config)")
        if not args.probe:
            print("  configured only -- pass --probe to test reachability for real\n")
        for key, provider in sorted(table.providers.items()):
            vendor = f"[{provider.vendor}]"
            if args.probe:
                reachable, detail = adapters.probe(provider)
                mark = {True: "UP  ", False: "DOWN", None: "?   "}[reachable]
                print(f"  {mark} {key:18} {vendor:18} {detail}")
            else:
                print(f"       {key:18} {vendor:18} {provider.adapter}")
        if args.probe:
            print()
            vendors = sorted({p.vendor for p in table.providers.values()})
            print(f"  vendors declared: {', '.join(vendors)}")
            print("  judge independence needs two REACHABLE vendors; see "
                  "`patrick judges`.")
    return 0 if ok else 1


# --- parser ---------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(prog="patrick", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", help="Patrick OS repo root (default: $PATRICK_OS_ROOT)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("skills", help="list and inspect skills")
    p.add_argument("action", choices=["list", "show"])
    p.add_argument("slug", nargs="?")
    p.add_argument("--body", action="store_true", help="print the full procedure")
    p.set_defaults(func=cmd_skills)

    p = sub.add_parser("run", help="run a skill (dry run unless --execute)")
    p.add_argument("slug")
    p.add_argument("--input", action="append", metavar="K=V")
    p.add_argument("--execute", action="store_true",
                   help="actually call the routed provider; still never sends anything")
    p.add_argument("--retrieve", action="store_true", default=None,
                   help="fetch source material first (default: on when executing a "
                        "skill that declares a retrieval source)")
    p.add_argument("--no-retrieve", dest="retrieve", action="store_false")
    p.add_argument("--backend", help="override the retrieval backend")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("voice", help="show composed voice rules")
    p.add_argument("action", nargs="?", choices=["show"], default="show")
    p.add_argument("--scope")
    p.add_argument("--skill")
    p.add_argument("--strategy", action="store_true",
                   help="show strategy/ rules instead of voice/ rules")
    p.set_defaults(func=cmd_voice)

    p = sub.add_parser("route", help="explain a routing decision without calling anything")
    p.add_argument("task_class")
    p.add_argument("--payload-bytes", type=int, default=0)
    p.add_argument("--min-quality", type=int, default=0)
    p.add_argument("--needs-tools", action="store_true")
    p.add_argument("--private", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_route)

    p = sub.add_parser("feedback", help="record corrections and promote them into rules")
    p.add_argument("action", choices=["add", "reject-output", "correct", "strategy",
                                      "list", "show", "promote", "reject"])
    p.add_argument("id", nargs="?")
    p.add_argument("--original")
    p.add_argument("--edited")
    p.add_argument("--skill")
    p.add_argument("--channel")
    p.add_argument("--project")
    p.add_argument("--run")
    p.add_argument("--note")
    p.add_argument("--index", type=int, default=0)
    p.add_argument("--scope", help="override the classified scope when promoting")
    p.add_argument("--text", help="override the proposed rule text when promoting")
    p.add_argument("--reason", help="why an output was rejected, or why a proposal was")
    p.add_argument("--output", help="the rejected output file, for reject-output")
    p.add_argument("--evidence", help="the result that taught a strategy lesson")
    p.add_argument("--mechanism", help="strategy scope: one mechanism")
    p.add_argument("--segment", help="strategy scope: one buyer segment")
    p.set_defaults(func=cmd_feedback)

    p = sub.add_parser("judge", help="check an output against a skill's quality bar")
    p.add_argument("slug")
    p.add_argument("--output", required=True, help="file containing the produced output")
    p.add_argument("--writer", help="provider that wrote it; the judge must differ")
    p.add_argument("--no-context", action="store_true",
                   help="do not load the run's inputs; citations become unverifiable")
    p.add_argument("--execute", action="store_true",
                   help="also call an independent judge provider")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_judge)

    p = sub.add_parser("test", help="run the regression suite")
    p.add_argument("slug", nargs="?")
    p.add_argument("--no-unit", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_test)

    p = sub.add_parser("decision", help="log a durable decision")
    p.add_argument("action", choices=["add", "list"])
    p.add_argument("--title")
    p.add_argument("--kind", default="architecture", choices=list(decisions.KINDS))
    p.add_argument("--context")
    p.add_argument("--decision")
    p.add_argument("--alternatives")
    p.add_argument("--consequences")
    p.add_argument("--supersedes")
    p.set_defaults(func=cmd_decision)

    p = sub.add_parser("select", help="choose a mechanism from a profile; calls nothing")
    p.add_argument("--profile", help="file containing the profile JSON")
    p.add_argument("--json-profile", help="the profile JSON inline")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_select)

    p = sub.add_parser("result", help="record what actually happened, and read it back")
    p.add_argument("action", choices=["record", "list"])
    p.add_argument("--opportunity", help="what this result is about")
    p.add_argument("--mechanism")
    p.add_argument("--tier", default="note")
    p.add_argument("--outcome", help=", ".join(results.OUTCOMES))
    p.add_argument("--evidence", help="what establishes this outcome")
    p.add_argument("--amount", help="money, if any changed hands")
    p.add_argument("--note")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_result)

    p = sub.add_parser("retrieval", help="retrieval backends and runtime capability")
    p.add_argument("action", choices=["list", "probe", "fetch"], nargs="?", default="list")
    p.add_argument("--query")
    p.add_argument("--backend", default="hermes-web")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_retrieval)

    p = sub.add_parser("judges", help="which independent judge pairs exist right now")
    p.add_argument("--probe", action="store_true", default=True)
    p.add_argument("--no-probe", dest="probe", action="store_false")
    p.set_defaults(func=cmd_judges)

    p = sub.add_parser("pipeline", help="show stage and mechanism coverage")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_pipeline)

    p = sub.add_parser("doctor", help="check the environment")
    p.add_argument("--probe", action="store_true",
                   help="actually test each provider's reachability")
    p.set_defaults(func=cmd_doctor)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "skills" and args.action == "show" and not args.slug:
        parser.error("skills show requires a slug")
    if args.command == "feedback":
        if args.action == "add" and not (args.original and args.edited):
            parser.error("feedback add requires --original and --edited")
        if args.action == "reject-output" and not (args.output and args.reason):
            parser.error("feedback reject-output requires --output and --reason")
        if args.action == "correct" and not args.text:
            parser.error("feedback correct requires --text")
        if args.action == "strategy" and not (args.text and args.evidence):
            parser.error("feedback strategy requires --text and --evidence")
    if args.command == "select" and not (args.profile or args.json_profile):
        parser.error("select requires --profile or --json-profile")
    if args.command == "retrieval" and args.action == "fetch" and not args.query:
        parser.error("retrieval fetch requires --query")
    if args.command == "result" and args.action == "record":
        missing = [f for f in ("opportunity", "mechanism", "outcome", "evidence")
                   if not getattr(args, f)]
        if missing:
            parser.error("result record requires --" + ", --".join(missing))
        if args.action in {"show", "promote", "reject"} and not args.id:
            parser.error(f"feedback {args.action} requires an id")
    if args.command == "decision" and args.action == "add" and not args.title:
        parser.error("decision add requires --title")
    try:
        return args.func(args)
    except (skills.SkillError, voice.VoiceError, feedback.FeedbackError,
            decisions.DecisionError, route_table.RouteTableError, runner.RunError,
            judging.JudgeError, pipeline.PipelineError, selection.SelectionError,
            results.ResultError, retrieval.RetrievalError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except FileNotFoundError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except runner.TRANSPORT_FAILURES as error:
        # A provider being unreachable or unauthenticated is an environment
        # condition, not a crash. Say what happened and what to do about it.
        print(f"error: provider call failed: {type(error).__name__}: {error}",
              file=sys.stderr)
        print("hint: run `patrick doctor` to see which providers are configured.",
              file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
