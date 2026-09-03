"""Project truth records.

One file per project under ``projects/``, answering the seven questions from
Patrick's own operating system note. Facts only -- no procedure. If something in
here would be true for a second project, it belongs in a skill or a voice rule.
"""

from __future__ import annotations

from . import frontmatter
from .skills import root

QUESTIONS = (
    "What is it?",
    "Who is it for?",
    "What phase is it in?",
    "What evidence says anybody wants it?",
    "What evidence says it produced money?",
    "What is the next irreversible action?",
    "What condition pauses or kills it?",
)

STAGES = ("CAPTURE", "DECODE", "DECIDE", "EXECUTE", "PROOF", "ARCHIVE")


def projects_dir(base=None):
    return root(base) / "projects"


def load(slug, base=None):
    path = projects_dir(base) / f"{slug}.md"
    if not path.is_file():
        return None
    meta, body = frontmatter.load(path.read_text(encoding="utf-8"))
    return {"slug": slug, "meta": meta, "body": body, "path": str(path)}


def list_projects(base=None):
    directory = projects_dir(base)
    if not directory.is_dir():
        return []
    return [load(p.stem, base) for p in sorted(directory.glob("*.md"))]


def facts_block(slug, base=None):
    """The text a work order embeds for a project. Empty string if unknown."""
    record = load(slug, base)
    if record is None:
        return ""
    return record["body"].strip()
