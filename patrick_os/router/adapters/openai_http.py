"""Any OpenAI-compatible /chat/completions endpoint: the local Qwen server,
OpenAI itself, or anything else that speaks the same shape.

Credentials come from the environment variable named in the route table. No key
is ever written into config or into a run record.
"""

from __future__ import annotations

import json
import os
import urllib.request


class TransportError(RuntimeError):
    pass


def _setting(provider, key, env_key, default=None):
    env_name = provider.config.get(env_key)
    if env_name:
        value = os.getenv(env_name)
        if value:
            return value
    return provider.config.get(key, default)


def complete(provider, prompt, *, timeout=120):
    base = _setting(provider, "base_url", "base_url_env")
    if not base:
        raise TransportError(f"{provider.key}: no base_url configured")
    api_key = _setting(provider, "api_key", "api_key_env")
    if not api_key:
        raise TransportError(
            f"{provider.key}: no API key; set ${provider.config.get('api_key_env')}"
        )
    body = json.dumps(
        {
            "model": provider.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": provider.config.get("temperature", 0.2),
            "max_tokens": provider.config.get("max_tokens", 2000),
        }
    ).encode()
    if provider.max_request_bytes is not None and len(body) > provider.max_request_bytes:
        raise TransportError(
            f"{provider.key}: request body {len(body)} bytes exceeds the "
            f"{provider.max_request_bytes}-byte limit for this endpoint"
        )
    request = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + api_key},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    return payload["choices"][0]["message"]["content"]
