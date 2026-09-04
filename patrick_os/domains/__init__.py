"""Domain packs: everything Patrick OS knows that is true of one KIND of work.

The core is an operating layer. It knows about skills, voice, routing, judging,
feedback, retrieval and orchestration -- concerns that are the same whether the
work is recruiting, fiction, research, or selling. It must know nothing about any
of those subjects.

A domain pack is where subject knowledge lives: the stages a commercial pursuit
moves through, the interventions it can select between, what counts as an
outcome, and the checks that only make sense for that kind of output.

Why this boundary is load-bearing: before it existed, `stage` was a REQUIRED
field on every skill, drawn from a commercial pipeline. A fiction skill could not
validate -- it was made to declare which sales intervention it served. The core
had absorbed one consumer's vocabulary and was imposing it on all the others.

Rules, enforced by tests:
  - Core modules never import from ``patrick_os.domains``.
  - A skill that declares no ``domain`` is a plain OS skill and is valid.
  - A skill that declares one must satisfy that domain's own rules.
"""

from __future__ import annotations

import importlib
import json

from ..skills import root

REGISTRY_FILE = "domains.json"


class DomainError(ValueError):
    pass


def registry_path(base=None):
    return root(base) / "config" / REGISTRY_FILE


def declared(base=None):
    """Domains this installation has enabled, from config/domains.json."""
    path = registry_path(base)
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle).get("domains") or {}


def load(name):
    """Import a domain pack by name."""
    try:
        return importlib.import_module(f".{name}", __name__)
    except ModuleNotFoundError as error:
        raise DomainError(
            f"no domain pack named {name!r}; packs live in patrick_os/domains/"
        ) from error


def validate_skill(name, skill):
    """Ask a domain whether a skill claiming it is well-formed."""
    module = load(name)
    checker = getattr(module, "validate_skill", None)
    return list(checker(skill)) if checker else []


def checks_for(name):
    """Checks a domain contributes. Merged into the generic registry on demand."""
    module = load(name)
    return dict(getattr(module, "CHECKS", {}))


def all_checks(base=None):
    merged = {}
    for name in declared(base):
        try:
            merged.update(checks_for(name))
        except DomainError:
            continue
    return merged
