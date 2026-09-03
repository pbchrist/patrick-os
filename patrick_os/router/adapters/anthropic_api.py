"""Anthropic Messages API over plain HTTP.

Deliberately not the `anthropic` SDK: Patrick OS core stays dependency-free, and
Claude stays one interchangeable worker among several rather than a build-time
requirement of the system.
"""

from __future__ import annotations

import json
import os
import urllib.request


class TransportError(RuntimeError):
    pass


def complete(provider, prompt, *, timeout=120):
    env_name = provider.config.get("api_key_env", "ANTHROPIC_API_KEY")
    api_key = os.getenv(env_name)
    if not api_key:
        raise TransportError(f"{provider.key}: no API key; set ${env_name}")
    base = provider.config.get("base_url", "https://api.anthropic.com")
    body = json.dumps(
        {
            "model": provider.model,
            "max_tokens": provider.config.get("max_tokens", 2000),
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()
    request = urllib.request.Request(
        base.rstrip("/") + "/v1/messages",
        data=body,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": provider.config.get("api_version", "2023-06-01"),
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    return "".join(block.get("text", "") for block in payload.get("content", []))
