"""The routing decision. A pure function of (TaskSpec, RouteTable).

No environment reads, no credentials, no network. Every rejection carries a
human-readable reason so ``patrick route`` can explain itself.
"""

from __future__ import annotations

from .spec import Candidate, Decision, LATENCY_ORDER, Rejection

# Large enough that no combination of quality, cost, and latency can reorder an
# explicit preference list.
_PREFERRED_BASE = 1_000_000.0
_RANK_STEP = 10_000.0


def resolve(task, table):
    route, route_name = table.match(task.task_class)
    prefer = list(route.get("prefer", []))
    deny = set(route.get("deny", []))
    require_local = bool(route.get("require_local", False)) or task.privacy == "local-only"
    min_quality = max(task.min_quality, int(route.get("min_quality", 0)))
    max_cost = task.max_cost_per_1k
    if route.get("max_cost_per_1k") is not None:
        limit = float(route["max_cost_per_1k"])
        max_cost = limit if max_cost is None else min(max_cost, limit)
    needs_tools = task.needs_tools or bool(route.get("needs_tools", False))
    needs_caps = set(task.needs_capabilities) | set(route.get("needs_capabilities", []))
    max_latency = task.max_latency_class or route.get("max_latency_class")

    candidates = []
    rejected = []
    for key, provider in table.providers.items():
        reason = _reject_reason(
            provider,
            task,
            deny=deny,
            require_local=require_local,
            min_quality=min_quality,
            max_cost=max_cost,
            needs_tools=needs_tools,
            needs_caps=needs_caps,
            max_latency=max_latency,
        )
        if reason:
            rejected.append(Rejection(key, reason))
            continue
        candidates.append(Candidate(provider, *_score(provider, prefer)))

    candidates.sort(key=lambda item: (-item.score, item.provider.key))
    rejected.sort(key=lambda item: item.provider_key)
    return Decision(task, candidates, rejected, route_name)


def _reject_reason(provider, task, *, deny, require_local, min_quality, max_cost,
                   needs_tools, needs_caps, max_latency):
    if provider.key in deny:
        return "denied by route"
    if require_local and not provider.local:
        return "route requires a local provider"
    missing = needs_caps - provider.capabilities
    if missing:
        return "missing capability: " + ", ".join(sorted(missing))
    if needs_tools and not provider.supports_tools:
        return "does not support tool use"
    if provider.quality < min_quality:
        return f"quality {provider.quality} below required {min_quality}"
    if max_cost is not None and provider.cost_per_1k > max_cost:
        return f"cost {provider.cost_per_1k} above cap {max_cost}"
    if max_latency is not None:
        allowed = LATENCY_ORDER.get(max_latency)
        actual = LATENCY_ORDER.get(provider.latency_class)
        if allowed is not None and actual is not None and actual > allowed:
            return f"latency class {provider.latency_class} slower than {max_latency}"
    if provider.max_request_bytes is not None and task.payload_bytes > provider.max_request_bytes:
        return (
            f"payload {task.payload_bytes} bytes exceeds provider limit "
            f"{provider.max_request_bytes}"
        )
    return None


def _score(provider, prefer):
    """An explicit ``prefer`` list is authoritative order, not a hint.

    Providers named by the route always outrank providers that merely qualify,
    and among named providers the declared position wins outright -- quality and
    cost never silently reorder a choice the route made on purpose. Those only
    break ties among the unnamed fallbacks.
    """
    reasons = []
    if provider.key in prefer:
        rank = prefer.index(provider.key)
        base = _PREFERRED_BASE - rank * _RANK_STEP
        reasons.append(f"preferred by route (position {rank + 1} of {len(prefer)})")
    else:
        base = 0.0
        reasons.append("not named by route; eligible fallback")
    base += provider.quality * 10
    reasons.append(f"quality {provider.quality}")
    base -= provider.cost_per_1k * 5
    reasons.append(f"cost {provider.cost_per_1k}/1k")
    base -= LATENCY_ORDER.get(provider.latency_class, 1)
    reasons.append(f"latency {provider.latency_class}")
    if provider.local:
        reasons.append("local (no data leaves the machine)")
    return base, reasons
