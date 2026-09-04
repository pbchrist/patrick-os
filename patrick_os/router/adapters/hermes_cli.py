"""Hermes as a provider, via its CLI.

Patrick OS shells out to the `hermes` CLI and writes nothing into ~/.hermes.
Hermes' existing OAuth logins are reused rather than duplicated as API keys here,
and Hermes' own behavior is untouched.

A note on the argv, because it is easy to get wrong twice:

Site Factory's `llm_client.py::_hermes_json` (pbchrist/hermes-projects, branch
audit/site-factory-20260901) invokes

    hermes chat -Q --provider P -m M --reasoning low --safe-mode
                --source tool --max-turns 1 --query-file -

`hermes chat` at the installed v0.13.0 accepts none of `--reasoning`,
`--safe-mode`, or `--query-file`; it exits 2 with "unrecognized arguments". So
Patrick OS builds the invocation this CLI actually documents, and treats the
extra flags as per-provider `extra_args` in `config/routes.json` -- data, not
code -- so a Hermes upgrade that restores them is a config edit.

The subprocess also runs with ``cwd`` set to the run's own directory. Hermes is
an agent with file tools and will use them: on a real ``recruiter-outreach``
execute it wrote its draft to the Patrick OS repository root. The runner owns
where artifacts go, so the worker gets a sandbox instead of the working tree.

`--ignore-rules` and `--ignore-user-config` are included by default because
Hermes' own help describes them as the isolation flags for "third-party
integrations": without them a Patrick OS work order would silently inherit
Hermes' AGENTS.md, SOUL.md, memory, and preloaded skills, and the output would be
shaped by a voice layer that is not this one.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess


class TransportError(RuntimeError):
    pass


# The prompt travels as an argv element. macOS ARG_MAX is ~1 MB, but a work order
# anywhere near this size is a design problem, not a transport problem.
MAX_PROMPT_BYTES = 200_000


def resolve_command(provider):
    command = provider.config.get("command") or os.getenv("PATRICK_HERMES_COMMAND") or "hermes"
    found = shutil.which(command)
    if not found:
        raise TransportError(f"{provider.key}: hermes CLI not found on PATH as {command!r}")
    return found


def probe(provider, *, timeout=8):
    """Binary and declared provider present in Hermes' credential pool.

    Checked against `hermes auth` output rather than by making a call: a real
    call costs a model turn, and the question here is whether the credential
    exists, which the pool answers directly.
    """
    try:
        resolved = resolve_command(provider)
    except TransportError as error:
        return False, str(error)
    wanted = provider.config.get("hermes_provider")
    if not wanted:
        return True, "cli present; no hermes provider declared"
    try:
        listed = subprocess.run([resolved, "auth"], input="5\n", text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=timeout, check=False).stdout or ""
    except (OSError, subprocess.SubprocessError) as error:
        return False, f"could not read hermes credential pool: {type(error).__name__}"
    if re.search(rf"^{re.escape(wanted)}\s*\(", listed, re.MULTILINE):
        return True, (f"{wanted!r} in hermes credential pool "
                      "(pool membership; token validity is only knowable on use)")
    pool = re.findall(r"^(\w[\w-]*)\s*\(\d+ credential", listed, re.MULTILINE)
    return False, (f"{wanted!r} NOT in hermes credential pool; pool holds: "
                   + (", ".join(pool) or "(none)"))


def build_argv(provider, prompt):
    argv = [resolve_command(provider), "chat", "-Q"]
    if provider.config.get("hermes_provider"):
        argv += ["--provider", provider.config["hermes_provider"]]
    if provider.model:
        argv += ["-m", provider.model]
    argv += ["--source", "tool", "--max-turns", str(provider.config.get("max_turns", 1))]
    if provider.config.get("isolate", True):
        argv += ["--ignore-rules", "--ignore-user-config"]
    argv += list(provider.config.get("extra_args", []))
    argv += ["-q", prompt]
    return argv


def complete(provider, prompt, *, timeout=120, workdir=None):
    size = len(prompt.encode("utf-8"))
    if size > MAX_PROMPT_BYTES:
        raise TransportError(
            f"{provider.key}: prompt is {size} bytes, above the {MAX_PROMPT_BYTES}-byte "
            "argv limit for this adapter"
        )
    completed = subprocess.run(
        build_argv(provider, prompt),
        cwd=str(workdir) if workdir else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()[-500:]
        raise TransportError(f"{provider.key}: hermes exited {completed.returncode}: {detail}")
    return strip_session_noise(completed.stdout)


SESSION_LINE = re.compile(r"^\s*session_id:\s*\S+\s*$", re.MULTILINE)


def strip_session_noise(text):
    """`hermes chat -Q` still emits a trailing `session_id:` line. It is transport
    metadata, not model output, and it corrupts JSON parsing downstream."""
    return SESSION_LINE.sub("", text).strip() + "\n"
