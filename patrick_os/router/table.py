"""Loading and validating the declarative route table (config/routes.json)."""

from __future__ import annotations

import json
from pathlib import Path

from .spec import Provider


class RouteTableError(ValueError):
    pass


class RouteTable:
    def __init__(self, data, source=None):
        self.source = source
        self.providers = {}
        for key, config in (data.get("providers") or {}).items():
            self.providers[key] = Provider(key, config)
        self.routes = data.get("routes") or []
        self.default = data.get("default") or {}
        self.validate()

    def validate(self):
        if not self.providers:
            raise RouteTableError("route table declares no providers")
        for route in self.routes:
            if "task_class" not in route:
                raise RouteTableError(f"route entry has no task_class: {route!r}")
            for key in route.get("prefer", []):
                if key not in self.providers:
                    raise RouteTableError(
                        f"route {route['task_class']!r} prefers unknown provider {key!r}"
                    )
            for key in route.get("deny", []):
                if key not in self.providers:
                    raise RouteTableError(
                        f"route {route['task_class']!r} denies unknown provider {key!r}"
                    )
        for key in self.default.get("prefer", []):
            if key not in self.providers:
                raise RouteTableError(f"default route prefers unknown provider {key!r}")

    def match(self, task_class):
        """Longest dotted-prefix match wins; ``draft.outreach`` beats ``draft``."""
        best = None
        best_length = -1
        for route in self.routes:
            pattern = route["task_class"]
            if task_class == pattern or task_class.startswith(pattern + "."):
                if len(pattern) > best_length:
                    best, best_length = route, len(pattern)
        if best is not None:
            return best, best["task_class"]
        return dict(self.default), "default"


def default_path(base=None):
    from ..skills import root

    return root(base) / "config" / "routes.json"


def load(path=None, base=None):
    target = Path(path) if path else default_path(base)
    if not target.is_file():
        raise RouteTableError(f"no route table at {target}")
    with open(target, encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as error:
            raise RouteTableError(f"{target}: invalid JSON: {error}") from error
    return RouteTable(data, source=str(target))
