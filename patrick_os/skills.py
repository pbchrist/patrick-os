"""Skill discovery, validation, and input binding.

A skill is a directory under ``skills/`` containing ``SKILL.md`` and an optional
``fixtures/`` directory. ``SKILL.md`` is front-matter (strict subset, see
``frontmatter``) plus a Markdown body whose ``##`` headings are the procedural
sections the brief requires.

Skills are data. Nothing in this module executes a procedure or calls a model --
that is ``runner``'s job -- so a skill can be validated with no network, no keys,
and no provider configured.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import frontmatter

REQUIRED_FIELDS = ("name", "version", "purpose", "task_class")

REQUIRED_SECTIONS = (
    "Purpose",
    "Inputs",
    "Prerequisites",
    "Procedure",
    "Outputs",
    "Quality checks",
    "Failure modes",
    "Escalation",
    "Examples",
)

# Skills that produce something a human would send. v1 never sends; these only
# ever write a draft to disk.
OUTWARD_OUTPUTS = {"draft", "message", "email", "reply", "comment"}


class SkillError(ValueError):
    pass


class Skill:
    def __init__(self, slug, path, meta, body, base=None):
        self.slug = slug
        self.path = path
        self.meta = meta
        self.body = body
        self._base = base

    # -- declared metadata ------------------------------------------------
    @property
    def name(self):
        return self.meta.get("name", self.slug)

    @property
    def purpose(self):
        return self.meta.get("purpose", "")

    @property
    def task_class(self):
        return self.meta.get("task_class", "")

    @property
    def channel(self):
        return self.meta.get("channel")

    @property
    def project(self):
        return self.meta.get("project")

    @property
    def output_kind(self):
        return self.meta.get("outputs", "report")

    @property
    def dry_run_default(self):
        return bool(self.meta.get("dry_run_default", True))

    @property
    def sends(self):
        """True only if the skill has an implemented outbound path. Always False in v1."""
        return bool(self.meta.get("sends", False))

    @property
    def is_outward(self):
        return self.output_kind in OUTWARD_OUTPUTS

    @property
    def inputs(self):
        declared = self.meta.get("inputs") or []
        spec = []
        for item in declared:
            if isinstance(item, dict):
                spec.append(item)
            else:
                spec.append({"name": str(item), "required": True})
        return spec

    @property
    def voice_scopes(self):
        """Voice rule files this skill composes, most general first."""
        scopes = ["global"]
        if self.channel:
            scopes.append(f"channel:{self.channel}")
        if self.project:
            scopes.append(f"project:{self.project}")
        scopes.append(f"skill:{self.slug}")
        return scopes

    # -- body sections ----------------------------------------------------
    def sections(self):
        found = {}
        current = None
        buffer = []
        for line in self.body.split("\n"):
            if line.startswith("## "):
                if current is not None:
                    found[current] = "\n".join(buffer).strip()
                current = line[3:].strip()
                buffer = []
            elif current is not None:
                buffer.append(line)
        if current is not None:
            found[current] = "\n".join(buffer).strip()
        return found

    def section(self, title):
        return self.sections().get(title, "")

    # -- domain -------------------------------------------------------------
    @property
    def domain(self):
        """Which KIND of work this skill belongs to, if any.

        Optional by design. Most OS skills belong to no domain; only skills doing
        subject-specific work claim one, and only then do that domain's rules
        apply.
        """
        return self.meta.get("domain")

    @property
    def stage(self):
        """Position within the declaring domain's workflow, if it has one.

        Core reads this and interprets nothing. What the value may be, and
        whether it is required, is the domain's business.
        """
        return self.meta.get("stage")

    @property
    def mechanisms(self):
        """Intervention types this skill can serve. Empty means mechanism-agnostic."""
        declared = self.meta.get("mechanisms")
        if isinstance(declared, str):
            return [declared]
        return list(declared or [])

    @property
    def mechanism_agnostic(self):
        return bool(self.meta.get("mechanism_agnostic", False))

    @property
    def investment_tier(self):
        return self.meta.get("investment_tier")

    # -- retrieval ---------------------------------------------------------
    @property
    def retrieval_source(self):
        """Which source this skill reads, from config/retrieval.json. None means
        the skill is given its material and reads nothing itself."""
        return self.meta.get("retrieval_source")

    @property
    def retrieval_query(self):
        """Template for the retrieval request, interpolated with bound inputs."""
        return self.meta.get("retrieval_query")

    @property
    def output_checks(self):
        return self.meta.get("output_checks") or []

    # -- fixtures ---------------------------------------------------------
    def behavioral_fixtures(self):
        """Fixtures that assert on a real produced OUTPUT, not on the work order.

        Structural fixtures prove the right rules reached the worker. These prove
        a specific bad output is caught -- and the canonical ones are outputs that
        actually shipped.
        """
        directory = self.path / "fixtures" / "behavioral"
        if not directory.is_dir():
            return []
        loaded = []
        for file in sorted(directory.glob("*.json")):
            with open(file, encoding="utf-8") as handle:
                try:
                    data = json.load(handle)
                except json.JSONDecodeError as error:
                    raise SkillError(f"{file}: invalid JSON fixture: {error}") from error
            data.setdefault("name", file.stem)
            data["_path"] = str(file)
            for field in ("output", "expect_verdict"):
                if field not in data:
                    raise SkillError(f"{file}: behavioral fixture needs a {field!r} field")
            loaded.append(data)
        return loaded

    def fixtures(self):
        directory = self.path / "fixtures"
        if not directory.is_dir():
            return []
        loaded = []
        for file in sorted(directory.glob("*.json")):
            with open(file, encoding="utf-8") as handle:
                try:
                    data = json.load(handle)
                except json.JSONDecodeError as error:
                    raise SkillError(f"{file}: invalid JSON fixture: {error}") from error
            data.setdefault("name", file.stem)
            data["_path"] = str(file)
            loaded.append(data)
        return loaded

    # -- input binding ----------------------------------------------------
    def bind(self, provided):
        """Validate ``provided`` against declared inputs; return the bound mapping."""
        bound = {}
        declared_names = set()
        missing = []
        for spec in self.inputs:
            key = spec.get("name")
            if not key:
                raise SkillError(f"{self.slug}: an input entry has no 'name'")
            declared_names.add(key)
            if key in provided:
                bound[key] = provided[key]
            elif "default" in spec:
                bound[key] = spec["default"]
            elif spec.get("required", True):
                missing.append(key)
        unknown = sorted(set(provided) - declared_names)
        problems = []
        if missing:
            problems.append("missing required input(s): " + ", ".join(sorted(missing)))
        if unknown:
            problems.append("unknown input(s): " + ", ".join(unknown))
        if problems:
            raise SkillError(f"{self.slug}: " + "; ".join(problems))
        return bound

    def _domain_problems(self):
        """Ask the skill's declared domain whether it is well-formed.

        A skill that declares no domain is a plain OS skill and gets no domain
        rules at all. That is the point: this method used to require every skill
        to name a stage in a commercial pipeline and state which sales
        intervention it served, so a fiction skill could not validate. One
        consumer's vocabulary had become the operating system's.
        """
        if not self.domain:
            return []
        from . import domains

        try:
            return domains.validate_skill(self.domain, self)
        except domains.DomainError as error:
            return [str(error)]

    def bind_partial(self, provided):
        """Bind what is present, ignoring absent required inputs.

        Used to interpolate a retrieval query before the retrieved material --
        itself a required input -- exists.
        """
        bound = {}
        for spec in self.inputs:
            key = spec.get("name")
            if key in provided:
                bound[key] = provided[key]
            elif "default" in spec:
                bound[key] = spec["default"]
        return bound

    def validate(self):
        """Return a list of problem strings. Empty list means the skill is well-formed."""
        problems = []
        for field in REQUIRED_FIELDS:
            if self.meta.get(field) in (None, ""):
                problems.append(f"missing required front-matter field: {field}")
        if self.meta.get("name") and self.meta["name"] != self.slug:
            problems.append(
                f"front-matter name {self.meta['name']!r} does not match directory {self.slug!r}"
            )
        present = set(self.sections())
        for title in REQUIRED_SECTIONS:
            if title not in present:
                problems.append(f"missing section: ## {title}")
        seen = set()
        for spec in self.inputs:
            if not isinstance(spec, dict) or "name" not in spec:
                problems.append(f"malformed input entry: {spec!r}")
                continue
            name = spec["name"]
            if name in seen:
                # A duplicate silently wins in binding, so a later optional entry
                # can quietly cancel an earlier required one -- which happened,
                # and would have let a mining skill run with no source material
                # and report that as a finding about the world.
                problems.append(
                    f"input {name!r} is declared more than once; the last declaration "
                    "silently wins when inputs are bound")
            seen.add(name)
        if self.is_outward and self.sends:
            problems.append(
                "outward-facing skill declares sends: true -- v1 has no send path"
            )
        if not self.dry_run_default:
            problems.append("dry_run_default must be true; dry run is the default everywhere")
        problems.extend(self._domain_problems())
        if not self.fixtures():
            problems.append("no regression fixtures under fixtures/")
        if self.output_checks:
            from . import checks as checks_module

            for entry in self.output_checks:
                name = entry.get("check") if isinstance(entry, dict) else entry
                try:
                    checks_module.resolve_check(name, self._base)
                except checks_module.CheckError:
                    problems.append(f"declares unknown output check: {name}")
            if not self.behavioral_fixtures():
                problems.append(
                    "declares output_checks but has no behavioral fixtures under "
                    "fixtures/behavioral/ -- a check nothing exercises is decoration"
                )
        return problems


def root(explicit=None):
    """Resolve the Patrick OS repository root."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.getenv("PATRICK_OS_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def skills_dir(base=None):
    return root(base) / "skills"


def load_skill(slug, base=None):
    directory = skills_dir(base) / slug
    file = directory / "SKILL.md"
    if not file.is_file():
        raise SkillError(f"no skill named {slug!r} (looked for {file})")
    with open(file, encoding="utf-8") as handle:
        text = handle.read()
    try:
        meta, body = frontmatter.load(text)
    except frontmatter.FrontmatterError as error:
        raise SkillError(f"{file}: {error}") from error
    return Skill(slug, directory, meta, body, base=base)


def list_skills(base=None):
    directory = skills_dir(base)
    if not directory.is_dir():
        return []
    found = []
    for child in sorted(directory.iterdir()):
        if child.name.startswith("_") or not child.is_dir():
            continue
        if (child / "SKILL.md").is_file():
            found.append(load_skill(child.name, base))
    return found
