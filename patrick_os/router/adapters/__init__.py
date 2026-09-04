"""Provider adapters, imported lazily.

Importing this package must never import a vendor SDK or read a credential.
``get(name)`` imports the adapter module only when a call is actually about to
happen, so ``patrick route`` and the whole test suite run on a machine with no
keys, no network, and no local model.
"""

from __future__ import annotations

import importlib

REGISTRY = {
    "openai_http": ".openai_http",
    "hermes_cli": ".hermes_cli",
    "anthropic_api": ".anthropic_api",
    "codex_cli": ".codex_cli",
}


class AdapterError(RuntimeError):
    pass


def get(name):
    if name not in REGISTRY:
        raise AdapterError(
            f"unknown adapter {name!r}; known adapters: {', '.join(sorted(REGISTRY))}"
        )
    return importlib.import_module(REGISTRY[name], __name__)


def probe(provider, *, timeout=8):
    """Can this provider actually be reached right now? (ok, human-readable why).

    Config presence is not readiness. `doctor` reported a dead endpoint as
    "ready" because a base_url was written down, which is exactly the kind of
    claim this whole system exists not to make.
    """
    module = get(provider.adapter)
    if not hasattr(module, "probe"):
        return None, f"{provider.adapter} has no probe; readiness unknown"
    try:
        return module.probe(provider, timeout=timeout)
    except Exception as error:  # noqa: BLE001
        return False, f"{type(error).__name__}: {str(error)[:90]}"


def complete(provider, prompt, *, timeout=120, workdir=None):
    """Send ``prompt`` to ``provider``. Only ever called from an --execute path.

    ``workdir`` is where a subprocess-backed provider is allowed to touch the
    filesystem. Agentic providers have file tools and will use them: a real run
    of ``recruiter-outreach`` had the worker write its draft to the repository
    root. The runner owns artifact placement, so the worker is given a sandbox.
    """
    module = get(provider.adapter)
    try:
        return module.complete(provider, prompt, timeout=timeout, workdir=workdir)
    except TypeError:
        # HTTP adapters have no filesystem to contain.
        return module.complete(provider, prompt, timeout=timeout)
