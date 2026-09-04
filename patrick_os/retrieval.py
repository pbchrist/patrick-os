"""Retrieval: how a skill reads a source, separately from which model reasons over it.

Two lessons are built into this module, both learned the hard way.

**Retrieval failure is not inference failure.** Reddit blocking a logged-out
fetch says nothing about the model, the provider, or the routing. Reaching for a
different model in response is a category error.

**Do not generalize one runtime's capabilities to another.** Patrick OS reported
that autonomous Reddit research was impossible. That was measured against the Mac
Hermes -- v0.13.0, no web backend, browser disabled. The Beastmaster Hermes is
v0.20.4 with web, search and browser toolsets, Tavily search and browser
extraction, and it retrieves Reddit successfully. One install's limits were
reported as a fact about the world. Hence ``probe_runtime``: capability is
discovered from the runtime that will actually do the work, never assumed.
"""

from __future__ import annotations

import base64
import json
import re
import shlex
import subprocess

from .skills import root


class RetrievalError(RuntimeError):
    pass


def registry_path(base=None):
    return root(base) / "config" / "retrieval.json"


def load_registry(base=None):
    path = registry_path(base)
    if not path.is_file():
        raise RetrievalError(f"no retrieval registry at {path}")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


# --- runtimes -------------------------------------------------------------
class Runtime:
    """A Hermes installation Patrick OS can drive, local or over SSH."""

    def __init__(self, key, config):
        self.key = key
        self.config = config
        self.transport = config.get("transport", "local")
        self.command = config.get("command", "hermes")
        self.ssh_target = config.get("ssh_target")
        self.run_as = config.get("run_as")

    def wrap(self, remote_command):
        """Build the argv that runs ``remote_command`` on this runtime."""
        if self.transport == "local":
            return ["/bin/sh", "-lc", remote_command]
        if self.transport != "ssh":
            raise RetrievalError(f"{self.key}: unknown transport {self.transport!r}")
        if not self.ssh_target:
            raise RetrievalError(f"{self.key}: ssh transport needs ssh_target")
        inner = remote_command
        if self.run_as:
            inner = f"su - {shlex.quote(self.run_as)} -c {shlex.quote(remote_command)}"
        return ["ssh", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes",
                self.ssh_target, inner]

    def run(self, remote_command, *, timeout=600, stdin=None):
        completed = subprocess.run(
            self.wrap(remote_command), text=True, input=stdin,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout, check=False)
        return completed


class Capability:
    """What a runtime can actually do, discovered rather than declared."""

    def __init__(self, key, **fields):
        self.key = key
        self.reachable = fields.get("reachable", False)
        self.version = fields.get("version")
        self.toolsets = fields.get("toolsets") or []
        self.search_backend = fields.get("search_backend")
        self.extract_backend = fields.get("extract_backend")
        self.detail = fields.get("detail", "")

    @property
    def can_web_research(self):
        """Search plus some way to read what search found."""
        return bool(self.reachable
                    and {"web", "search"} & set(self.toolsets)
                    and self.search_backend)

    def as_dict(self):
        return {"runtime": self.key, "reachable": self.reachable,
                "version": self.version, "toolsets": self.toolsets,
                "search_backend": self.search_backend,
                "extract_backend": self.extract_backend,
                "can_web_research": self.can_web_research, "detail": self.detail}


_VERSION = re.compile(r"Hermes Agent v(\S+)")


def probe_runtime(runtime, *, timeout=60):
    """Ask a runtime what it supports. Never infers from another install."""
    command = (f"{shlex.quote(runtime.command)} version 2>&1 | head -3; "
               "echo '---CONFIG---'; "
               "cat ~/.hermes/config.yaml 2>/dev/null")
    try:
        completed = runtime.run(command, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as error:
        return Capability(runtime.key, reachable=False,
                          detail=f"{type(error).__name__}: {str(error)[:90]}")
    output = completed.stdout or ""
    if completed.returncode and "Hermes Agent" not in output:
        detail = (completed.stderr or output).strip()[-120:]
        return Capability(runtime.key, reachable=False, detail=detail or "no response")

    version = None
    found = _VERSION.search(output)
    if found:
        version = found.group(1)

    config = output.split("---CONFIG---", 1)[-1]
    toolsets = []
    block = re.search(r"^toolsets:\s*$((?:\n\s*-\s*\S+)+)", config, re.MULTILINE)
    if block:
        toolsets = re.findall(r"-\s*(\S+)", block.group(1))
    web = re.search(r"^web:\s*$((?:\n\s{2,}\S+:.*)+)", config, re.MULTILINE)
    search_backend = extract_backend = None
    if web:
        search = re.search(r"search_backend:\s*(\S+)", web.group(1))
        extract = re.search(r"extract_backend:\s*(\S+)", web.group(1))
        backend = re.search(r"^\s*backend:\s*(\S+)", web.group(1), re.MULTILINE)
        search_backend = (search or backend).group(1) if (search or backend) else None
        extract_backend = extract.group(1) if extract else None
    return Capability(runtime.key, reachable=True, version=version, toolsets=toolsets,
                      search_backend=search_backend, extract_backend=extract_backend,
                      detail=f"v{version or '?'}, toolsets: {', '.join(toolsets) or 'none'}")


def runtimes(base=None):
    data = load_registry(base)
    return {k: Runtime(k, v) for k, v in (data.get("runtimes") or {}).items()}


def probe_all(base=None, timeout=60):
    return {k: probe_runtime(r, timeout=timeout) for k, r in runtimes(base).items()}


def choose_runtime(requirement="web_research", base=None, capabilities=None):
    """The runtime that can do this, discovered. Raises with what each lacked."""
    caps = capabilities or probe_all(base)
    for key, capability in caps.items():
        if requirement == "web_research" and capability.can_web_research:
            return key, capability
        if requirement == "any" and capability.reachable:
            return key, capability
    reasons = "; ".join(f"{k}: {c.detail or 'no capability'}" for k, c in caps.items())
    raise RetrievalError(
        f"no runtime satisfies {requirement!r}. Probed -- {reasons}")


# --- the hermes-web backend ----------------------------------------------
SEARCH_FIRST_CONTRACT = """\
You are a retrieval worker. Return sources, not analysis.

Method, in this order. Do not skip to a later step while an earlier one can work:
1. Use web search to find the material. Search is the primary path.
2. Use web extract or the browser to read what search returned.
3. Where a site blocks direct extraction, use an indexed or public archive of it
   (for Reddit, arctic-shift.photon-reddit.com is one such archive) and keep the
   ORIGINAL permalink as the citation.

Never begin by raw-fetching the site. A site blocking a direct fetch does not
mean the material is unavailable, and treating it that way ends the job early.

For every item you must preserve: the original permalink, the author handle if
shown, the date, and the text verbatim. Never reconstruct a quote from memory and
never write a URL you did not receive from a tool. If you retrieved nothing,
return an empty list -- that is a valid answer.

Return ONLY JSON matching this shape, with no prose around it:
{"items": [{"url": "...", "title": "...", "author": "...", "date": "...",
            "text": "...", "via": "search|extract|archive"}],
 "notes": "what worked, what was blocked, and which archive was used if any"}
"""


def hermes_web(query, *, runtime_key=None, base=None, timeout=900, max_turns=12,
               model=None, capabilities=None, **_ignored):
    """Retrieve via a Hermes runtime's web/search/browser toolsets.

    Config is deliberately NOT ignored here. The isolation flags Patrick OS uses
    for judging (--ignore-rules --ignore-user-config) would switch off the very
    toolsets this depends on, since they are declared in config.yaml.
    """
    caps = capabilities or probe_all(base)
    if runtime_key is None:
        runtime_key, capability = choose_runtime("web_research", base, caps)
    else:
        capability = caps.get(runtime_key)
        if capability is None or not capability.can_web_research:
            raise RetrievalError(
                f"runtime {runtime_key!r} cannot do web research: "
                f"{capability.detail if capability else 'not declared'}")
    runtime = runtimes(base)[runtime_key]

    prompt = SEARCH_FIRST_CONTRACT + "\n\nTASK\n" + query
    encoded = base64.b64encode(prompt.encode("utf-8")).decode("ascii")
    remote = (
        f"set -e; f=$(mktemp); echo {encoded} | base64 -d > \"$f\"; "
        f"{shlex.quote(runtime.command)} chat -Q "
        f"-t {shlex.quote(','.join(t for t in ('web', 'search', 'browser') if t in capability.toolsets))} "
        f"--source tool --max-turns {int(max_turns)} "
        + (f"-m {shlex.quote(model)} " if model else "")
        + "--query-file \"$f\"; rm -f \"$f\""
    )
    completed = runtime.run(remote, timeout=timeout)
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()[-400:]
        raise RetrievalError(
            f"{runtime_key}: hermes exited {completed.returncode}: {detail}")
    payload = _parse_json(completed.stdout)
    payload.setdefault("items", [])
    payload["_runtime"] = runtime_key
    payload["_capability"] = capability.as_dict()
    return payload


_SESSION_LINE = re.compile(r"^\s*session_id:\s*\S+\s*$", re.MULTILINE)


def _parse_json(text):
    cleaned = _SESSION_LINE.sub("", text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.S).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    best = None
    for index, char in enumerate(cleaned):
        if char not in "{[":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "items" in value:
            return value
        best = best or value
    if isinstance(best, list):
        return {"items": best}
    raise RetrievalError("retrieval worker did not return JSON:\n" + cleaned[:400])


# --- the reddit-archive backend ------------------------------------------
ARCHIVE_BASE = "https://arctic-shift.photon-reddit.com/api"

# urllib's default User-Agent is rejected by the archive; curl's is not. Identify
# the caller honestly rather than impersonating a browser.
ARCHIVE_UA = "patrick-os/0.1 (research; contact via repository owner)"


def reddit_archive(query, *, base=None, subreddit=None, window_days=90, limit=40,
                   timeout=90, **_ignored):
    """Query the Arctic Shift public Reddit archive directly, with no model.

    Deterministic where ``hermes-web`` is not. The same request returned 12 items
    on one run and 0 on the next, because an agent was rediscovering the archive
    each time and its queries timed out. Here the archive is called from Python:
    same query, same answer, and nothing in the path can invent a permalink
    because nothing in the path is a model.

    Search-first still leads -- this is the archive rung of that ladder, reached
    when direct extraction is blocked, which for Reddit it always is.
    """
    import urllib.parse
    import urllib.request
    from datetime import datetime, timedelta, timezone

    if not subreddit:
        found = re.search(r"r/([A-Za-z0-9_]+)", query or "")
        if not found:
            raise RetrievalError(
                "reddit-archive needs a subreddit; none given and none found in the query")
        subreddit = found.group(1)
    after = (datetime.now(timezone.utc) - timedelta(days=int(window_days))).date().isoformat()

    items = []
    for kind in ("posts", "comments"):
        params = urllib.parse.urlencode({
            "subreddit": subreddit, "limit": int(limit), "sort": "desc", "after": after})
        url = f"{ARCHIVE_BASE}/{kind}/search?{params}"
        request = urllib.request.Request(url, headers={"User-Agent": ARCHIVE_UA,
                                                       "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.load(response)
        except Exception as error:  # noqa: BLE001 - reported, not raised
            items.append({"_error": f"{kind}: {type(error).__name__}: {str(error)[:80]}"})
            continue
        for row in (payload.get("data") or []):
            permalink = row.get("permalink") or ""
            if permalink and not permalink.startswith("http"):
                permalink = "https://www.reddit.com" + permalink
            created = row.get("created_utc")
            date = ""
            if created:
                date = datetime.fromtimestamp(int(created), timezone.utc).date().isoformat()
            text = row.get("selftext") or row.get("body") or ""
            if not text.strip() or text.strip() in ("[deleted]", "[removed]"):
                continue
            items.append({
                "url": permalink, "title": row.get("title") or "",
                "author": row.get("author") or "", "date": date,
                "text": text, "via": "archive", "kind": kind[:-1],
            })
    errors = [i["_error"] for i in items if "_error" in i]
    items = [i for i in items if "_error" not in i]
    return {
        "items": items,
        "notes": (f"Arctic Shift archive, r/{subreddit}, items since {after}. "
                  f"{len(items)} retrieved."
                  + (f" Errors: {'; '.join(errors)}" if errors else "")),
        "_runtime": "direct-http",
        "_capability": {"runtime": "direct-http", "reachable": True,
                        "detail": "Arctic Shift public archive, no model in the path"},
    }


BACKENDS = {"hermes-web": hermes_web, "reddit-archive": reddit_archive}


def retrieve(query, *, backend="hermes-web", base=None, chain=None, **kwargs):
    """Run a backend, falling through the declared chain when one yields nothing.

    Empty is a legitimate answer and is never faked -- but an empty result caused
    by one agent's archive query timing out is not the same finding as "there is
    nothing there", and the chain exists so the two are not confused.
    """
    order = [backend] + [b for b in (chain or []) if b != backend]
    attempts = []
    last = None
    for name in order:
        if name not in BACKENDS:
            attempts.append({"backend": name, "items": 0,
                             "note": "declared but not executable here"})
            continue
        try:
            payload = BACKENDS[name](query, base=base, **kwargs)
        except RetrievalError as error:
            attempts.append({"backend": name, "items": 0, "note": str(error)[:200]})
            continue
        count = len(payload.get("items") or [])
        attempts.append({"backend": name, "items": count,
                         "note": str(payload.get("notes") or "")[:200]})
        last = payload
        if count:
            payload["_backend"] = name
            payload["_attempts"] = attempts
            return payload
    if last is None:
        raise RetrievalError("no backend produced a result: "
                             + "; ".join(f"{a['backend']}: {a['note']}" for a in attempts))
    last["_backend"] = order[-1]
    last["_attempts"] = attempts
    return last
