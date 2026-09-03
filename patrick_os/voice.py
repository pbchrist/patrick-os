"""The persistent voice/rules layer.

Voice rules are the durable half of Patrick OS: the part that survives a model
change, a vendor change, and a new chat window. They live as plain Markdown so a
human can read and edit them, but with enough structure that the feedback
compiler can append to exactly one file without rewriting anything a human wrote.

Scopes compose most-general-first, so a narrower rule is stated last and reads as
the override:

    global  ->  channel:<name>  ->  project:<name>  ->  skill:<slug>

Rule line format, one per line under ``## Rules``::

    - [G-004] Never claim customer behavior that was not measured.

The bracketed id is stable. Nothing renumbers; retired rules are struck by moving
them under ``## Retired``, never by deleting the id.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import frontmatter
from .skills import root

RULE_PATTERN = re.compile(r"^-\s*\[(?P<id>[A-Z]+-\d+)\]\s*(?P<text>.+?)\s*$")

# Two rule namespaces share this machinery. They are different KINDS of rule and
# must not share a file, because they answer different questions and are revised
# on different evidence:
#
#   voice/     how an output must read. Revised by edits to drafts.
#   strategy/  which opportunities and mechanisms are worth pursuing at all.
#              Revised by results -- money, replies, silence -- not by wording.
#
# Collapsing them would mean a lesson about which businesses to stop chasing gets
# filed next to a rule about em-dashes, and neither can be audited.
NAMESPACES = ("voice", "strategy")

SCOPE_PREFIXES = {
    "voice": {
        "global": "G",
        "channel": "C",
        "project": "P",
        "skill": "S",
    },
    "strategy": {
        "global": "ST",
        "mechanism": "M",
        "segment": "SG",
        "project": "PJ",
    },
}


class VoiceError(ValueError):
    pass


class Rule:
    def __init__(self, rule_id, text, scope, source_file):
        self.id = rule_id
        self.text = text
        self.scope = scope
        self.source_file = source_file

    def as_dict(self):
        return {"id": self.id, "scope": self.scope, "text": self.text}

    def __repr__(self):
        return f"<Rule {self.id} {self.scope}>"


def voice_dir(base=None, namespace="voice"):
    if namespace not in NAMESPACES:
        raise VoiceError(f"unknown namespace {namespace!r}; expected one of {NAMESPACES}")
    return root(base) / namespace


def scope_path(scope, base=None, namespace="voice"):
    """Map a scope string to the file that owns it."""
    directory = voice_dir(base, namespace)
    if scope == "global":
        return directory / "global.md"
    kind, _, name = scope.partition(":")
    if not name:
        raise VoiceError(f"scope {scope!r} needs a name, e.g. 'channel:linkedin'")
    allowed = set(SCOPE_PREFIXES[namespace]) - {"global"}
    if kind not in allowed:
        raise VoiceError(
            f"unknown {namespace} scope kind {kind!r}; expected global or one of: "
            + ", ".join(sorted(allowed))
        )
    return directory / (kind + "s") / f"{name}.md"


def parse_rules(text, scope, source_file):
    _, body = frontmatter.load(text)
    rules = []
    section = None
    for line in body.split("\n"):
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        if section != "rules":
            continue
        match = RULE_PATTERN.match(line.rstrip())
        if match:
            rules.append(Rule(match.group("id"), match.group("text"), scope, source_file))
    return rules


def load_scope(scope, base=None, namespace="voice"):
    path = scope_path(scope, base, namespace)
    if not path.is_file():
        return []
    with open(path, encoding="utf-8") as handle:
        return parse_rules(handle.read(), scope, str(path))


def compose(scopes, base=None, namespace="voice"):
    """Load every scope in order and return the flattened rule list."""
    rules = []
    for scope in scopes:
        rules.extend(load_scope(scope, base, namespace))
    return rules


def all_scopes(base=None, namespace="voice"):
    """Every scope that currently has a file."""
    directory = voice_dir(base, namespace)
    found = []
    if (directory / "global.md").is_file():
        found.append("global")
    for kind in sorted(set(SCOPE_PREFIXES[namespace]) - {"global"}):
        subdir = directory / (kind + "s")
        if subdir.is_dir():
            for file in sorted(subdir.glob("*.md")):
                found.append(f"{kind}:{file.stem}")
    return found


ANY_RULE_ID = re.compile(r"\[([A-Z]+)-(\d+)\]")


def next_rule_id(scope, base=None, namespace="voice"):
    """Allocate an id no rule in this file has ever used.

    Scans the whole file, not just the live ``## Rules`` section: a retired rule
    keeps its id forever so old outputs stay explainable, which means a retired
    id must never be handed out again.
    """
    prefix = SCOPE_PREFIXES[namespace][scope.partition(":")[0]]
    path = scope_path(scope, base, namespace)
    highest = 0
    if path.is_file():
        for found_prefix, number in ANY_RULE_ID.findall(path.read_text(encoding="utf-8")):
            if found_prefix == prefix:
                highest = max(highest, int(number))
    return f"{prefix}-{highest + 1:03d}"


def append_rule(scope, text, *, source=None, base=None, namespace="voice"):
    """Append one rule to the file that owns ``scope``. Returns the new rule id.

    Creates the file with a minimal header if the scope has no file yet. This is
    the *only* write path into voice/, so promotion is always a single, reviewable
    append rather than a rewrite.
    """
    path = scope_path(scope, base, namespace)
    rule_id = next_rule_id(scope, base, namespace)
    line = f"- [{rule_id}] {text.strip()}"
    if source:
        line += f"  (source: {source})"
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        header = (
            "---\n"
            f"scope: {scope}\n"
            f"namespace: {namespace}\n"
            "version: 1\n"
            "---\n\n"
            f"# {namespace.title()} — {scope}\n\n"
            "## Rules\n\n"
        )
        path.write_text(header + line + "\n", encoding="utf-8")
        return rule_id
    existing = path.read_text(encoding="utf-8")
    if "## Rules" not in existing:
        existing = existing.rstrip() + "\n\n## Rules\n"
    lines = existing.rstrip("\n").split("\n")
    # Insert at the end of the ## Rules section, before any later heading.
    start = next(i for i, value in enumerate(lines) if value.strip() == "## Rules")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    while end > start + 1 and lines[end - 1].strip() == "":
        end -= 1
    lines.insert(end, line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rule_id
