"""Result intake: what actually happened.

The missing half of learning, and the reason ``strategy/`` was empty. The
feedback compiler captures what Patrick changed about an *output*; nothing
captured what a *prospect did*. Voice rules are revised by edits; strategy rules
are revised by results, so with no result intake there was no legitimate way to
write one.

Two rules make this useful rather than a diary:

**Evidence is mandatory.** An outcome with nothing behind it is a memory, and
memories drift toward whatever story is being told now.

**Silence is an outcome.** ``no_reply`` is a first-class value, recorded with the
same weight as a sale. A results log that only records wins measures enthusiasm.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from . import workflow as pipeline
from ...skills import root

OUTCOMES = (
    "no_reply",      # sent, nothing came back. The most common real outcome.
    "reply",         # a human responded, any sentiment
    "meeting",       # a conversation happened
    "declined",      # an explicit no
    "paid",          # money changed hands
    "suppressed",    # we stopped before sending, on purpose
    "abandoned",     # we stopped without deciding
)

# Outcomes that earn the next investment tier. Progressive investment, ST-002.
ADVANCING = {"reply", "meeting", "paid"}


class ResultError(ValueError):
    pass


def results_path(base=None):
    return root(base) / "results" / "results.jsonl"


def load_all(base=None):
    path = results_path(base)
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def record(*, opportunity, mechanism, tier, outcome, evidence, amount=None,
           note=None, base=None):
    if outcome not in OUTCOMES:
        raise ResultError(f"outcome must be one of: {', '.join(OUTCOMES)}")
    if tier not in pipeline.TIERS:
        raise ResultError(f"tier must be one of: {', '.join(pipeline.TIERS)}")
    if not (evidence or "").strip():
        raise ResultError(
            "a result needs evidence: what establishes that this happened? An "
            "outcome with nothing behind it is a memory, and memories drift "
            "toward whatever story is being told now."
        )
    rows = load_all(base)
    entry = {
        "id": f"R-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{len(rows) + 1:03d}",
        "recorded": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "opportunity": opportunity,
        "mechanism": mechanism,
        "tier": tier,
        "outcome": outcome,
        "evidence": evidence,
        "amount": amount,
        "note": note,
    }
    entry["advances_tier"] = outcome in ADVANCING
    entry["lesson_prompt"] = _lesson_prompt(entry, rows)
    path = results_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def _lesson_prompt(entry, history):
    """Nudge toward a strategy rule when a pattern has actually repeated.

    Deliberately a prompt and not an automatic rule. Same discipline as the
    feedback compiler: one result is a data point, and the human writes the rule.
    """
    same = [r for r in history
            if r.get("mechanism") == entry["mechanism"]
            and r.get("outcome") == entry["outcome"]]
    if len(same) + 1 < 3:
        return ""
    return (
        f"{len(same) + 1} results now record {entry['outcome']!r} for mechanism "
        f"{entry['mechanism']!r}. That is a pattern, not a data point. If it means "
        f"something, write it down:\n"
        f"  patrick feedback strategy --mechanism {entry['mechanism']} \\\n"
        f"    --text \"...\" --evidence \"{len(same) + 1} results: see results/results.jsonl\""
    )


def summary(base=None):
    rows = load_all(base)
    by_mechanism = {}
    for row in rows:
        bucket = by_mechanism.setdefault(row.get("mechanism", "?"), {})
        bucket[row.get("outcome", "?")] = bucket.get(row.get("outcome", "?"), 0) + 1
    return {"count": len(rows), "by_mechanism": by_mechanism}


def format_table(rows):
    lines = [f"{'id':17} {'mechanism':16} {'tier':7} {'outcome':11} opportunity"]
    for row in rows:
        lines.append(
            f"{row['id']:17} {str(row.get('mechanism')):16} {str(row.get('tier')):7} "
            f"{str(row.get('outcome')):11} {row.get('opportunity')}")
    stats = {}
    for row in rows:
        stats[row.get("outcome")] = stats.get(row.get("outcome"), 0) + 1
    lines.append("")
    lines.append("  ".join(f"{k}={v}" for k, v in sorted(stats.items())))
    return "\n".join(lines)
