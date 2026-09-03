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
}


class AdapterError(RuntimeError):
    pass


def get(name):
    if name not in REGISTRY:
        raise AdapterError(
            f"unknown adapter {name!r}; known adapters: {', '.join(sorted(REGISTRY))}"
        )
    return importlib.import_module(REGISTRY[name], __name__)


def complete(provider, prompt, *, timeout=120):
    """Send ``prompt`` to ``provider``. Only ever called from an --execute path."""
    return get(provider.adapter).complete(provider, prompt, timeout=timeout)
