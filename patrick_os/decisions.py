"""The decision log.

A decision is a thing that stays decided. Recording one costs thirty seconds and
saves the argument being re-run in a fresh chat window six weeks later, which is
the specific failure this repository exists to prevent.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import frontmatter
from .skills import root

KINDS = ("architecture", "business", "product", "process")


class DecisionError(ValueError):
    pass


def decisions_dir(base=None):
    return root(base) / "decisions"


def _slugify(title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:60] or "decision"


def next_number(base=None):
    directory = decisions_dir(base)
    if not directory.is_dir():
        return 1
    highest = 0
    for file in directory.glob("*.md"):
        match = re.match(r"(\d{4})-", file.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def add(title, *, kind="architecture", context="", decision="", consequences="",
        alternatives="", supersedes=None, base=None):
    if kind not in KINDS:
        raise DecisionError(f"kind must be one of {', '.join(KINDS)}")
    number = next_number(base)
    directory = decisions_dir(base)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{number:04d}-{_slugify(title)}.md"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    body = f"""---
id: "{number:04d}"
title: {title}
kind: {kind}
date: {today}
status: accepted
supersedes: {supersedes or ''}
---

# {number:04d} — {title}

## Context

{context.strip() or 'TODO'}

## Decision

{decision.strip() or 'TODO'}

## Alternatives considered

{alternatives.strip() or 'TODO'}

## Consequences

{consequences.strip() or 'TODO'}
"""
    path.write_text(body, encoding="utf-8")
    return {"id": f"{number:04d}", "path": str(path), "title": title}


def list_decisions(base=None):
    directory = decisions_dir(base)
    if not directory.is_dir():
        return []
    found = []
    for file in sorted(directory.glob("*.md")):
        meta, _ = frontmatter.load(file.read_text(encoding="utf-8"))
        found.append({"path": str(file), "meta": meta})
    return found
