"""Vendor-neutral request/route types.

Nothing here imports a provider SDK, reads a credential, or opens a socket.
The whole point is that routing decisions are testable on a machine with no
API keys and no local model running.
"""

from __future__ import annotations


class TaskSpec:
    """What the work needs, stated without naming a vendor."""

    def __init__(
        self,
        task_class,
        *,
        payload_bytes=0,
        needs_capabilities=(),
        needs_tools=False,
        min_quality=0,
        max_cost_per_1k=None,
        max_latency_class=None,
        privacy="normal",
    ):
        self.task_class = task_class
        self.payload_bytes = int(payload_bytes)
        self.needs_capabilities = tuple(needs_capabilities)
        self.needs_tools = bool(needs_tools)
        self.min_quality = int(min_quality)
        self.max_cost_per_1k = max_cost_per_1k
        self.max_latency_class = max_latency_class
        self.privacy = privacy

    def as_dict(self):
        return {
            "task_class": self.task_class,
            "payload_bytes": self.payload_bytes,
            "needs_capabilities": list(self.needs_capabilities),
            "needs_tools": self.needs_tools,
            "min_quality": self.min_quality,
            "max_cost_per_1k": self.max_cost_per_1k,
            "max_latency_class": self.max_latency_class,
            "privacy": self.privacy,
        }


LATENCY_ORDER = {"fast": 0, "medium": 1, "slow": 2}


class Provider:
    """A declared provider entry from the route table. Config only, no client."""

    def __init__(self, key, config):
        self.key = key
        self.adapter = config.get("adapter")
        self.model = config.get("model")
        self.capabilities = set(config.get("capabilities", []))
        self.supports_tools = bool(config.get("supports_tools", False))
        self.quality = int(config.get("quality", 0))
        self.cost_per_1k = float(config.get("cost_per_1k", 0.0))
        self.latency_class = config.get("latency_class", "medium")
        self.max_request_bytes = config.get("max_request_bytes")
        self.max_context_tokens = config.get("max_context_tokens")
        self.local = bool(config.get("local", False))
        self.config = config

    def __repr__(self):
        return f"<Provider {self.key}>"


class Candidate:
    """A provider that survived filtering, with the reason it ranked where it did."""

    def __init__(self, provider, score, reasons):
        self.provider = provider
        self.score = score
        self.reasons = list(reasons)

    @property
    def key(self):
        return self.provider.key

    def as_dict(self):
        return {
            "provider": self.provider.key,
            "adapter": self.provider.adapter,
            "model": self.provider.model,
            "score": round(self.score, 4),
            "reasons": self.reasons,
        }


class Rejection:
    def __init__(self, provider_key, reason):
        self.provider_key = provider_key
        self.reason = reason

    def as_dict(self):
        return {"provider": self.provider_key, "reason": self.reason}


class Decision:
    def __init__(self, task, candidates, rejected, route_name):
        self.task = task
        self.candidates = candidates
        self.rejected = rejected
        self.route_name = route_name

    @property
    def chosen(self):
        return self.candidates[0] if self.candidates else None

    def as_dict(self):
        return {
            "route": self.route_name,
            "task": self.task.as_dict(),
            "chosen": self.chosen.as_dict() if self.chosen else None,
            "fallbacks": [c.as_dict() for c in self.candidates[1:]],
            "rejected": [r.as_dict() for r in self.rejected],
        }
