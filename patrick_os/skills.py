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

    # -- pipeline position -------------------------------------------------
    @property
    def stage(self):
        """Where in the commercial pipeline this sits. Separate from task_class,
        which is a routing concern."""
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

    def _pipeline_problems(self):
        """A skill must say where in the commercial pipeline it sits.

        Not decoration: without it, nothing can tell that the two Site Factory
        skills cover two of eight stages and one of six mechanisms, and the
        system quietly behaves as though they are the whole business.
        """
        from . import pipeline

        problems = []
        if not self.stage:
            problems.append(
                "missing front-matter field: stage (one of: "
                + ", ".join(pipeline.STAGES) + ")"
            )
        elif self.stage not in pipeline.STAGES:
            problems.append(
                f"unknown stage {self.stage!r}; expected one of: "
                + ", ".join(pipeline.STAGES)
            )
        if self.investment_tier and self.investment_tier not in pipeline.TIERS:
            problems.append(
                f"unknown investment_tier {self.investment_tier!r}; expected one of: "
                + ", ".join(pipeline.TIERS)
            )
        if self.mechanisms and self.mechanism_agnostic:
            problems.append(
                "declares both mechanisms and mechanism_agnostic: true; pick one"
            )
        if not self.mechanisms and not self.mechanism_agnostic:
            problems.append(
                "declares neither mechanisms nor mechanism_agnostic: true -- a skill "
                "that does not say which interventions it serves is assumed to serve "
                "the only one anybody built, which is the failure this field exists "
                "to prevent"
            )
        if self.mechanisms:
            try:
                registry = pipeline.load_mechanisms(base=self._base)
            except pipeline.PipelineError as error:
                problems.append(str(error))
            else:
                for key in self.mechanisms:
                    if key not in registry:
                        problems.append(
                            f"unknown mechanism {key!r}; declared in "
                            f"config/mechanisms.json: {', '.join(registry.keys())}"
                        )
        return problems

    def bind_partial(self, provided):
        """Bind what is present, ignoring absent required inputs.

        Used to interpolate a retrieval query before the retrieved material -- a
        required input -- exists.
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
        for spec in self.inputs:
            if not isinstance(spec, dict) or "name" not in spec:
                problems.append(f"malformed input entry: {spec!r}")
        if self.is_outward and self.sends:
            problems.append(
                "outward-facing skill declares sends: true -- v1 has no send path"
            )
        if not self.dry_run_default:
            problems.append("dry_run_default must be true; dry run is the default everywhere")
        problems.extend(self._pipeline_problems())
        if not self.fixtures():
            problems.append("no regression fixtures under fixtures/")
        if self.output_checks:
            from . import checks as checks_module

            for entry in self.output_checks:
                name = entry.get("check") if isinstance(entry, dict) else entry
                if name not in checks_module.REGISTRY:
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
