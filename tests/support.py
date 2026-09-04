"""Shared helpers: a throwaway Patrick OS root so tests never touch the real repo."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

MINIMAL_SKILL = """---
name: {slug}
version: 1
purpose: test skill
task_class: {task_class}
channel: {channel}
project: {project}
outputs: report
dry_run_default: true
sends: false
inputs:
  - name: topic
    required: true
  - name: depth
    required: false
    default: 2
---

# {slug}

## Purpose
p
## Inputs
i
## Prerequisites
pre
## Procedure
Look at {{{{ topic }}}} to depth {{{{ depth }}}}.
## Outputs
o
## Quality checks
q
## Failure modes
f
## Escalation
e
## Examples
x
"""


class TempRootTest(unittest.TestCase):
    """A test case with an isolated Patrick OS root containing a real route table."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="patrick-os-test-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        for sub in ("skills", "voice/channels", "voice/projects", "voice/skills",
                    "strategy/mechanisms", "strategy/segments", "strategy/projects",
                    "projects", "feedback/inbox", "decisions", "config", "runs"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        for name in ("routes.json", "domains.json", "retrieval.json"):
            shutil.copy(REPO / "config" / name, self.root / "config" / name)
        (self.root / "config" / "domains").mkdir(exist_ok=True)
        shutil.copy(REPO / "config" / "domains" / "commercial-mechanisms.json",
                    self.root / "config" / "domains" / "commercial-mechanisms.json")

    def write_skill(self, slug, *, task_class="research", channel="null",
                    project="null", stage=None, fixtures=None):
        directory = self.root / "skills" / slug
        (directory / "fixtures").mkdir(parents=True, exist_ok=True)
        (directory / "SKILL.md").write_text(
            MINIMAL_SKILL.format(
                slug=slug, task_class=task_class, channel=channel, project=project
            ),
            encoding="utf-8",
        )
        for name, data in (fixtures or {"basic": {"inputs": {"topic": "x"}, "expect": {}}}).items():
            (directory / "fixtures" / f"{name}.json").write_text(
                json.dumps(data), encoding="utf-8"
            )
        return directory

    def write_voice(self, scope_file, body):
        path = self.root / "voice" / scope_file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path
