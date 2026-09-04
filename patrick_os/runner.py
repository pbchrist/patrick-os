"""Running a skill.

A run has two halves, and Patrick OS keeps them separate on purpose:

1. **Compose** -- deterministic. Voice rules + project facts + the skill's own
   procedure + the bound inputs are assembled into a single work order, and the
   router picks a provider. This half needs no network, no keys, and no model,
   which is exactly why the regression harness can assert against it.
2. **Execute** -- optional, off by default. The work order is handed to whichever
   provider the router chose.

Dry run is the default for every skill. ``--execute`` runs half 2 and writes the
model's output to a file. Nothing in v1 sends anything anywhere.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from . import projects, voice
from .router import TaskSpec, resolve
from .router import table as route_table
from .skills import root


class RunError(RuntimeError):
    pass


# What "this provider is unavailable" looks like across adapters. A failure here
# means try the next candidate; anything else is a bug and must propagate.
TRANSPORT_FAILURES = (
    urllib.error.URLError,
    OSError,
    subprocess.SubprocessError,
    RuntimeError,
    KeyError,
    ValueError,
)


def _stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def compose(skill, bound_inputs, *, base=None):
    """Build the work order text. Pure with respect to the repo contents."""
    rules = voice.compose(skill.voice_scopes, base)
    sections = skill.sections()
    lines = []
    lines.append(f"# Work order — {skill.slug}")
    lines.append("")
    lines.append(f"Skill version: {skill.meta.get('version')}")
    lines.append(f"Task class: {skill.task_class}")
    lines.append(f"Output kind: {skill.output_kind}")
    lines.append("")
    lines.append("You are a worker inside Patrick OS. The procedure below is the")
    lines.append("authority on *what* to do; the voice rules are the authority on")
    lines.append("*how the output must read*. Where they conflict, stop and escalate")
    lines.append("rather than choosing one.")
    lines.append("")
    lines.append("Return the finished artifact as your reply, in full. Do not write it")
    lines.append("to a file, do not summarise it, and do not describe what you did --")
    lines.append("Patrick OS captures your reply and owns where it is stored. A summary")
    lines.append("of the artifact is not the artifact.")
    lines.append("")

    lines.append(f"## Voice rules ({len(rules)}, most general first)")
    lines.append("")
    if rules:
        for rule in rules:
            lines.append(f"- [{rule.id}] ({rule.scope}) {rule.text}")
    else:
        lines.append("- (none defined for this skill's scopes)")
    lines.append("")

    if skill.project:
        facts = projects.facts_block(skill.project, base)
        lines.append(f"## Project facts — {skill.project}")
        lines.append("")
        lines.append(facts if facts else "- (no truth record on file)")
        lines.append("")

    lines.append("## Inputs")
    lines.append("")
    for key in sorted(bound_inputs):
        lines.append(f"- {key}: {bound_inputs[key]!r}")
    if not bound_inputs:
        lines.append("- (none)")
    lines.append("")

    for title in ("Purpose", "Prerequisites", "Procedure", "Outputs",
                  "Quality checks", "Failure modes", "Escalation"):
        if sections.get(title):
            lines.append(f"## {title}")
            lines.append("")
            lines.append(_interpolate(sections[title], bound_inputs))
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def _interpolate(text, bound_inputs):
    def replace(match):
        key = match.group(1)
        if key in bound_inputs:
            return str(bound_inputs[key])
        return match.group(0)

    return _PLACEHOLDER.sub(replace, text)


def _prepare_retrieval(skill, provided, *, base=None):
    """Populate source material before inference for skills with external sources."""
    prepared = dict(provided)
    if skill.slug != "reddit-mine":
        return prepared
    backend = prepared.get("retrieval_backend") or "manual-export"
    if backend == "manual-export":
        return prepared
    from . import retrieval
    try:
        bundle = retrieval.fetch("reddit", backend, prepared, base=base)
        prepared["retrieved_material"] = retrieval.render_bundle(bundle)
    except retrieval.RetrievalError as exc:
        # The skill has a defined failure report. Preserve the retrieval failure as
        # source material so the worker can emit that shape without inventing facts.
        prepared["retrieved_material"] = json.dumps({
            "source": "reddit", "backend": backend, "retrieval_error": str(exc)
        })
    return prepared


def plan(skill, provided, *, base=None, table=None):
    """Compose a work order and resolve a route, without calling anything."""
    provided = _prepare_retrieval(skill, provided, base=base)
    bound = skill.bind(provided)
    work_order = compose(skill, bound, base=base)
    table = table or route_table.load(base=base)
    task = TaskSpec(
        skill.task_class,
        payload_bytes=len(work_order.encode("utf-8")),
        needs_capabilities=skill.meta.get("needs_capabilities") or (),
        needs_tools=bool(skill.meta.get("needs_tools", False)),
        min_quality=int(skill.meta.get("min_quality", 0) or 0),
        privacy=skill.meta.get("privacy", "normal"),
    )
    decision = resolve(task, table)
    return {"skill": skill, "inputs": bound, "work_order": work_order, "decision": decision}


def run(skill, provided, *, execute=False, base=None, table=None, out_dir=None,
        transport=None):
    """Plan, then optionally execute. Writes a run record either way."""
    planned = plan(skill, provided, base=base, table=table)
    decision = planned["decision"]
    stamp = _stamp()
    run_id = f"{stamp}-{skill.slug}"
    directory = Path(out_dir) if out_dir else root(base) / "runs" / run_id
    directory.mkdir(parents=True, exist_ok=True)

    (directory / "workorder.md").write_text(planned["work_order"], encoding="utf-8")
    record = {
        "run_id": run_id,
        "skill": skill.slug,
        "skill_version": skill.meta.get("version"),
        "created": stamp,
        "mode": "execute" if execute else "dry-run",
        "inputs": planned["inputs"],
        "route": decision.as_dict(),
        "output_kind": skill.output_kind,
        "sent": False,
    }

    if not execute:
        record["note"] = (
            "Dry run. Work order composed and route resolved; no provider was called."
        )
        _write_record(directory, record)
        return record

    if decision.chosen is None:
        record["error"] = "no provider satisfied this skill's routing constraints"
        record["mode"] = "failed"
        _write_record(directory, record)
        raise RunError(record["error"])

    # The router already ranked fallbacks; a provider that is simply down should
    # cost the next one in the list, not the whole run. Every attempt is recorded
    # so a silent failover is still a visible one.
    attempts = []
    text = None
    provider = None
    # Anything the worker writes to disk lands here, not in the working tree.
    sandbox = directory / "worker"
    sandbox.mkdir(exist_ok=True)
    for candidate in decision.candidates:
        provider = candidate.provider
        try:
            if transport is not None:
                text = transport(planned["work_order"], provider=provider)
            else:
                from .router import adapters

                text = adapters.complete(provider, planned["work_order"],
                                         workdir=sandbox)
            attempts.append({"provider": provider.key, "ok": True})
            break
        except TRANSPORT_FAILURES as error:
            attempts.append(
                {"provider": provider.key, "ok": False,
                 "error": f"{type(error).__name__}: {error}"}
            )
            text = None
    record["attempts"] = attempts
    if text is None:
        record["mode"] = "failed"
        record["error"] = "every eligible provider failed"
        _write_record(directory, record)
        raise RunError(
            "every eligible provider failed:\n  "
            + "\n  ".join(f"{a['provider']}: {a['error']}" for a in attempts)
        )

    (directory / "output.md").write_text(text, encoding="utf-8")
    record["provider"] = provider.key
    record["output_path"] = str(directory / "output.md")
    stray = sorted(p.name for p in sandbox.iterdir())
    if stray:
        record["worker_wrote_files"] = stray
    if skill.is_outward:
        record["note"] = (
            "Outward-facing output written to disk as a DRAFT. Patrick OS has no send "
            "path in v1; a human moves this into the channel or discards it."
        )
    _write_record(directory, record)
    return record


def _write_record(directory, record):
    (directory / "run.json").write_text(
        json.dumps(record, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )


def env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
