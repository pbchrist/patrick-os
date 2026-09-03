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

from . import decisions, feedback, runner, skills, testing, voice
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
    record = runner.run(skill, provided, execute=execute, base=args.root)
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


def cmd_feedback(args):
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
        print(f"recorded {entry['id']}  status={entry['status']}")
        for edit in entry["edits"]:
            print(f"  {edit['kind']:9} scope={edit['scope']:22} {edit['rationale']}")
        if entry["proposals"]:
            print("\nproposals (nothing applied yet):")
            for index, proposal in enumerate(entry["proposals"]):
                print(f"  [{index}] {proposal['scope']}: {proposal['rule']}")
            print(f"\napply with: patrick feedback promote {entry['id']}")
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

        print("\nprovider readiness (credentials are read from the environment, "
              "never from config):")
        for key, provider in sorted(table.providers.items()):
            if provider.adapter == "hermes_cli":
                import shutil

                command = provider.config.get("command", "hermes")
                state = "ready" if shutil.which(command) else f"MISSING ({command} not on PATH)"
            else:
                env_name = provider.config.get("api_key_env")
                has_env = bool(env_name and os.getenv(env_name))
                has_inline = bool(provider.config.get("api_key"))
                state = "ready" if (has_env or has_inline) else f"no ${env_name}"
            print(f"  {key:16} {provider.adapter:14} {state}")
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
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("voice", help="show composed voice rules")
    p.add_argument("action", nargs="?", choices=["show"], default="show")
    p.add_argument("--scope")
    p.add_argument("--skill")
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
    p.add_argument("action", choices=["add", "list", "show", "promote", "reject"])
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
    p.add_argument("--reason")
    p.set_defaults(func=cmd_feedback)

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

    p = sub.add_parser("doctor", help="check the environment without calling a provider")
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
        if args.action in {"show", "promote", "reject"} and not args.id:
            parser.error(f"feedback {args.action} requires an id")
    if args.command == "decision" and args.action == "add" and not args.title:
        parser.error("decision add requires --title")
    try:
        return args.func(args)
    except (skills.SkillError, voice.VoiceError, feedback.FeedbackError,
            decisions.DecisionError, route_table.RouteTableError, runner.RunError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except FileNotFoundError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
