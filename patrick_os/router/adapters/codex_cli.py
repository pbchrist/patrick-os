"""OpenAI Codex as a provider, via its CLI.

Uses the ChatGPT OAuth already stored in ~/.codex/auth.json. No API key is read,
copied, or required, and Patrick OS never touches that file -- the CLI owns it.

Why this exists: Hermes declares an `openai-codex` provider (it is a current
provider in v0.13.0, not an obsolete alias), but that provider needs the Codex
credential registered in Hermes' OWN credential pool, and on this machine the
pool holds only `copilot` and `nous`. The credential itself is present and valid;
it just lives in the Codex CLI's store. Going through the CLI uses the
credential that exists instead of asking for one that does not.

Codex is an agent, not a completion endpoint, so it is invoked read-only and
outside any git repo check, and its transcript framing is stripped from stdout.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess


class TransportError(RuntimeError):
    pass


MAX_PROMPT_BYTES = 200_000

# `codex exec` prints a short transcript around the model's reply: a banner, the
# echoed prompt, a "codex" marker, and a token count. The reply is what sits
# between the marker and the token count.
_TOKENS_LINE = re.compile(r"^tokens used\s*$", re.IGNORECASE | re.MULTILINE)
_MARKER_LINE = re.compile(r"^codex\s*$", re.IGNORECASE | re.MULTILINE)


def resolve_command(provider):
    command = provider.config.get("command") or os.getenv("PATRICK_CODEX_COMMAND") or "codex"
    found = shutil.which(command)
    if not found:
        raise TransportError(f"{provider.key}: codex CLI not found on PATH as {command!r}")
    return found


def authenticated(provider=None):
    """Is a Codex credential present? Checked without reading any secret value."""
    path = os.path.expanduser(
        (provider.config.get("auth_file") if provider else None) or "~/.codex/auth.json")
    if not os.path.isfile(path):
        return False, f"no credential file at {path}"
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        return False, f"{path} unreadable: {type(error).__name__}"
    mode = data.get("auth_mode")
    has_token = bool((data.get("tokens") or {}).get("access_token")) or bool(
        data.get("OPENAI_API_KEY"))
    if not has_token:
        return False, f"{path} has no access token; run `codex login`"
    return True, f"{mode or 'token'} credential present"


def probe(provider, *, timeout=8):
    """Credential and binary present. Does not spend a Codex turn."""
    try:
        resolve_command(provider)
    except TransportError as error:
        return False, str(error)
    return authenticated(provider)


def build_argv(provider, prompt):
    argv = [resolve_command(provider), "exec",
            "--sandbox", provider.config.get("sandbox", "read-only"),
            "--skip-git-repo-check"]
    if provider.model:
        argv += ["-m", provider.model]
    argv += list(provider.config.get("extra_args", []))
    argv += [prompt]
    return argv


def strip_transcript(text):
    """Return the model's reply, without codex's surrounding transcript."""
    body = text
    marker = list(_MARKER_LINE.finditer(body))
    if marker:
        body = body[marker[-1].end():]
    tokens = _TOKENS_LINE.search(body)
    if tokens:
        body = body[: tokens.start()]
    return body.strip() + "\n"


def complete(provider, prompt, *, timeout=300, workdir=None):
    size = len(prompt.encode("utf-8"))
    if size > MAX_PROMPT_BYTES:
        raise TransportError(
            f"{provider.key}: prompt is {size} bytes, above the {MAX_PROMPT_BYTES}-byte limit")
    ok, detail = authenticated(provider)
    if not ok:
        raise TransportError(f"{provider.key}: {detail}")
    completed = subprocess.run(
        build_argv(provider, prompt),
        cwd=str(workdir) if workdir else None,
        text=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()[-500:]
        raise TransportError(f"{provider.key}: codex exited {completed.returncode}: {detail}")
    return strip_transcript(completed.stdout)
