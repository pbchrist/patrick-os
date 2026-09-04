"""Source retrieval backends for Patrick OS.

Inference and retrieval are deliberately separate. A model should never be asked
"try to browse Reddit" and then blamed when Reddit blocks logged-out reads.
This module obtains source material first; workers only analyze the material they
are handed.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


class RetrievalError(RuntimeError):
    pass


def _config(base=None):
    root = Path(base or Path(__file__).resolve().parents[1])
    return json.loads((root / "config" / "retrieval.json").read_text(encoding="utf-8"))


def backend_status(source, backend, *, base=None):
    try:
        return _config(base)["sources"][source]["backends"][backend]
    except KeyError as exc:
        raise RetrievalError(f"unknown retrieval backend {source}:{backend}") from exc


def _reddit_token(client_id, client_secret, *, opener=urllib.request.urlopen):
    body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request(
        "https://www.reddit.com/api/v1/access_token",
        data=body,
        headers={
            "Authorization": f"Basic {basic}",
            "User-Agent": "patrick-os/0.1 (local research tool)",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with opener(req, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RetrievalError(f"Reddit OAuth token request failed: {exc}") from exc
    token = payload.get("access_token")
    if not token:
        raise RetrievalError(f"Reddit OAuth token response had no access_token: {payload.get('error') or 'unknown error'}")
    return token


def _reddit_json(path, token, *, opener=urllib.request.urlopen):
    req = urllib.request.Request(
        "https://oauth.reddit.com" + path,
        headers={
            "Authorization": f"bearer {token}",
            "User-Agent": "patrick-os/0.1 (local research tool)",
        },
    )
    try:
        with opener(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RetrievalError(f"Reddit API read failed for {path}: {exc}") from exc


def fetch_reddit(subreddit, *, window_days=14, max_posts=50, max_comments_per_post=100,
                 base=None, opener=urllib.request.urlopen, now=None):
    """Fetch recent public Reddit submissions + comments using app-only OAuth.

    Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET. No Reddit username or
    password is stored or needed; this reads public content only.
    """
    client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RetrievalError(
            "reddit-api requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET; "
            "create one Reddit OAuth app and set those two environment variables"
        )
    token = _reddit_token(client_id, client_secret, opener=opener)
    now_ts = (now or datetime.now(timezone.utc)).timestamp()
    cutoff = now_ts - int(window_days) * 86400
    listing = _reddit_json(
        f"/r/{urllib.parse.quote(subreddit)}/new?limit={min(int(max_posts), 100)}&raw_json=1",
        token, opener=opener,
    )
    posts = []
    for child in listing.get("data", {}).get("children", []):
        d = child.get("data", {})
        created = float(d.get("created_utc") or 0)
        if created < cutoff:
            continue
        post = {
            "kind": "post",
            "id": d.get("id"),
            "author": d.get("author"),
            "created_utc": created,
            "date": datetime.fromtimestamp(created, timezone.utc).isoformat(),
            "title": d.get("title") or "",
            "text": d.get("selftext") or "",
            "permalink": "https://www.reddit.com" + (d.get("permalink") or ""),
            "score": d.get("score"),
            "num_comments": d.get("num_comments"),
            "comments": [],
        }
        pid = d.get("id")
        if pid:
            thread = _reddit_json(
                f"/comments/{urllib.parse.quote(pid)}?limit={min(int(max_comments_per_post), 500)}&depth=4&raw_json=1",
                token, opener=opener,
            )
            if isinstance(thread, list) and len(thread) > 1:
                stack = list(thread[1].get("data", {}).get("children", []))
                while stack and len(post["comments"]) < int(max_comments_per_post):
                    item = stack.pop(0)
                    if item.get("kind") != "t1":
                        continue
                    c = item.get("data", {})
                    ccreated = float(c.get("created_utc") or 0)
                    if ccreated >= cutoff:
                        post["comments"].append({
                            "author": c.get("author"),
                            "created_utc": ccreated,
                            "date": datetime.fromtimestamp(ccreated, timezone.utc).isoformat(),
                            "text": c.get("body") or "",
                            "permalink": "https://www.reddit.com" + (c.get("permalink") or ""),
                            "score": c.get("score"),
                        })
                    replies = c.get("replies")
                    if isinstance(replies, dict):
                        stack.extend(replies.get("data", {}).get("children", []))
        posts.append(post)
    return {
        "source": "reddit",
        "backend": "reddit-api",
        "subreddit": subreddit,
        "window_days": int(window_days),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "post_count": len(posts),
        "posts": posts,
    }


def fetch(source, backend, inputs, *, base=None):
    if source == "reddit" and backend == "reddit-api":
        return fetch_reddit(
            inputs["subreddit"],
            window_days=inputs.get("window_days", 14),
            base=base,
        )
    raise RetrievalError(f"retrieval backend not implemented: {source}:{backend}")


def render_bundle(bundle):
    """Stable text form for worker prompts; JSON keeps provenance explicit."""
    return json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True)
