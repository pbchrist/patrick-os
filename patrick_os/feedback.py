"""The feedback compiler.

Given what Patrick OS produced and what Patrick actually sent, work out what
changed, why it probably changed, how far the correction should travel, and what
rule -- if any -- should be written down.

The load-bearing design decision is that **capture and promotion are separate
verbs**. ``feedback add`` observes and classifies; it never edits a voice file.
``feedback promote`` edits exactly one voice file, runs the regression suite, and
rolls the edit back if the suite fails. A correction cannot leak into the
system's permanent behavior without a human naming it.

The second load-bearing decision: a correction observed **once** is local, always.
Scope escalates on *repetition across contexts*, never on the compiler's opinion
about how general an edit felt. A single edit that swaps a company name is not
evidence of a rule, no matter how confidently it could be phrased as one.
"""

from __future__ import annotations

import difflib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import voice
from .skills import root

# --- edit kinds -----------------------------------------------------------
# A "surface" edit touches only values a rule could never generalize: a name, a
# number, a date, a URL. Surface edits are permanently local -- they are excluded
# from repetition counting entirely, so ten name corrections never add up to one
# rule.
SURFACE = "surface"
DELETION = "deletion"
INSERTION = "insertion"
REWRITE = "rewrite"
REJECTION = "rejection"
CORRECTION = "correction"

ESCALATION_THRESHOLD = 2

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD = re.compile(r"[A-Za-z']+")
_STOPWORDS = frozenset(
    """a an and are as at be been but by can could did do does for from had has have
    he her his i if in into is it its me my no not of on or our out she should so
    than that the their them then there these they this to too us was we were what
    when which who will with would you your""".split()
)
_PROPER_NOUNISH = re.compile(
    r"^(?:[A-Z][\w'&.-]*|\d[\d,.:/%$-]*|https?://\S+|\S+@\S+\.\S+)$"
)


class FeedbackError(ValueError):
    pass


# --- diffing --------------------------------------------------------------
def sentences(text):
    return [s.strip() for s in _SENTENCE_SPLIT.split(text or "") if s.strip()]


def diff(original, edited):
    """Sentence-level changes between two versions. Returns a list of edit dicts."""
    before, after = sentences(original), sentences(edited)
    matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
    edits = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        removed = before[i1:i2]
        added = after[j1:j2]
        gone = sorted(set(_content_words(removed)) - set(_content_words(added)))
        new = sorted(set(_content_words(added)) - set(_content_words(removed)))
        edits.append(
            {
                "kind": classify_kind(removed, added),
                "removed": removed,
                "added": added,
                "removed_words": gone,
                "added_words": new,
                "signature": signature(removed, added),
            }
        )
    return edits


def classify_kind(removed, added):
    if removed and not added:
        return DELETION
    if added and not removed:
        return INSERTION
    if _only_surface_tokens(removed, added):
        return SURFACE
    return REWRITE


def _content_words(lines):
    words = []
    for line in lines:
        for word in _WORD.findall(line.lower()):
            if word not in _STOPWORDS and len(word) > 2:
                words.append(word)
    return words


def _only_surface_tokens(removed, added):
    """True when the edit changes only proper nouns, numbers, dates, URLs, emails.

    Requires the sentence skeleton to be otherwise identical: same shape, same
    content words, differing only in tokens that no voice rule could generalize.
    """
    if len(removed) != len(added) or not removed:
        return False
    for before, after in zip(removed, added):
        left, right = before.split(), after.split()
        if len(left) != len(right):
            return False
        changed = [(a, b) for a, b in zip(left, right) if a != b]
        if not changed:
            continue
        for a, b in changed:
            if not (_PROPER_NOUNISH.match(a.strip(".,;:!?")) and
                    _PROPER_NOUNISH.match(b.strip(".,;:!?"))):
                return False
    return True


def signature(removed, added):
    """A readable fingerprint for the log. Not the matching key -- see ``similar``.

    An exact fingerprint is the obvious way to count repetitions and the wrong
    one: the same correction made in slightly different words produces a
    different fingerprint, so escalation silently never fires and the compiler
    looks like it is working. Matching is done on word overlap instead.
    """
    kind = classify_kind(removed, added)
    if kind == SURFACE:
        return "surface:not-generalizable"
    gone = sorted(set(_content_words(removed)) - set(_content_words(added)))
    new = sorted(set(_content_words(added)) - set(_content_words(removed)))
    return f"{kind}:-{'|'.join(gone[:6])}:+{'|'.join(new[:6])}"


# Two corrections are "the same correction" when this much of what they strip out
# overlaps. Tuned so rephrasings match and unrelated edits do not; raising it
# makes the compiler slower to learn, lowering it makes it learn wrong things.
SIMILARITY_THRESHOLD = 0.5
MIN_SHARED_WORDS = 2


def _words_of(edit, field):
    stored = edit.get(field)
    if stored is not None:
        return set(stored)
    source = "removed" if field == "removed_words" else "added"
    other = "added" if field == "removed_words" else "removed"
    return set(_content_words(edit.get(source, []))) - set(_content_words(edit.get(other, [])))


def _overlaps(a, b):
    if not a or not b:
        return False
    shared = a & b
    if len(shared) < min(MIN_SHARED_WORDS, len(a), len(b)):
        return False
    return len(shared) / len(a | b) >= SIMILARITY_THRESHOLD


def similar(left, right):
    """Do two edits represent the same correction?

    Matched in BOTH directions, because a correction can be defined by what it
    removes *or* by what it adds. Replacing "worth twenty minutes?" with "worth
    twenty minutes on Thursday or Friday?" strips different words each time it is
    made, but always adds the same thing -- a concrete day. Keying only on removed
    words missed that class of correction entirely, so it never escalated.

    Surface edits never match anything, including each other -- that is what
    makes them permanently un-generalizable rather than merely slow to escalate.
    """
    if left.get("kind") == SURFACE or right.get("kind") == SURFACE:
        return False
    if left.get("kind") != right.get("kind"):
        return False
    return (
        _overlaps(_words_of(left, "removed_words"), _words_of(right, "removed_words"))
        or _overlaps(_words_of(left, "added_words"), _words_of(right, "added_words"))
    )


# --- storage --------------------------------------------------------------
def inbox_dir(base=None):
    return root(base) / "feedback" / "inbox"


def changelog_path(base=None):
    return root(base) / "feedback" / "CHANGELOG.md"


def load_all(base=None):
    directory = inbox_dir(base)
    if not directory.is_dir():
        return []
    entries = []
    for file in sorted(directory.glob("*.json")):
        entries.append(json.loads(file.read_text(encoding="utf-8")))
    return entries


def load_entry(entry_id, base=None):
    path = inbox_dir(base) / f"{entry_id}.json"
    if not path.is_file():
        raise FeedbackError(f"no feedback entry {entry_id!r} (looked for {path})")
    return json.loads(path.read_text(encoding="utf-8"))


def save_entry(entry, base=None):
    directory = inbox_dir(base)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{entry['id']}.json"
    path.write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _next_id(base=None):
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    existing = [e["id"] for e in load_all(base) if e["id"].startswith(f"F-{today}-")]
    return f"F-{today}-{len(existing) + 1:03d}"


# --- classification -------------------------------------------------------
def escalate(edit, history, *, skill, channel, project):
    """Decide how far one correction should travel.

    ``history`` is the list of prior entries. Returns ``(scope, occurrences,
    rationale)``. ``scope`` is ``"local"`` when the correction must not become a
    rule.
    """
    if edit["kind"] == SURFACE:
        return (
            "local",
            1,
            "edit changes only names, numbers, dates, or URLs; no rule could "
            "generalize it correctly",
        )

    contexts = [{"skill": skill, "channel": channel, "project": project}]
    for entry in history:
        for prior in entry.get("edits", []):
            if similar(edit, prior):
                contexts.append(
                    {
                        "skill": entry.get("skill"),
                        "channel": entry.get("channel"),
                        "project": entry.get("project"),
                    }
                )
    occurrences = len(contexts)
    if occurrences < ESCALATION_THRESHOLD:
        return (
            "local",
            occurrences,
            f"seen {occurrences} time; a correction is local until it repeats "
            f"({ESCALATION_THRESHOLD} needed)",
        )

    skills = {c["skill"] for c in contexts if c["skill"]}
    channels = {c["channel"] for c in contexts if c["channel"]}
    all_projects = {c["project"] for c in contexts if c["project"]}

    if len(skills) <= 1 and skill:
        return f"skill:{skill}", occurrences, (
            f"seen {occurrences} times, all in skill {skill!r}"
        )
    if len(all_projects) == 1 and all(c["project"] for c in contexts):
        name = next(iter(all_projects))
        return f"project:{name}", occurrences, (
            f"seen {occurrences} times across {len(skills)} skills, all in project {name!r}"
        )
    if len(channels) == 1 and all(c["channel"] for c in contexts):
        name = next(iter(channels))
        return f"channel:{name}", occurrences, (
            f"seen {occurrences} times across {len(skills)} skills, all on channel {name!r}"
        )
    return "global", occurrences, (
        f"seen {occurrences} times across {len(skills)} skills and "
        f"{len(channels) or 'no'} channels"
    )


def propose_rule(edit):
    """Phrase a candidate rule. Returns None when no honest rule can be phrased."""
    if edit["kind"] == SURFACE:
        return None
    gone = _content_words(edit["removed"])
    new = _content_words(edit["added"])
    dropped = [w for w in dict.fromkeys(gone) if w not in set(new)][:4]
    gained = [w for w in dict.fromkeys(new) if w not in set(gone)][:4]
    if edit["kind"] == DELETION:
        if not dropped:
            return None
        return "Do not include material about " + ", ".join(dropped) + "."
    if edit["kind"] == INSERTION:
        if not gained:
            return None
        return "Always include " + ", ".join(gained) + "."
    if dropped and gained:
        return (
            "Prefer " + ", ".join(gained) + " over " + ", ".join(dropped) + "."
        )
    if dropped:
        return "Do not use " + ", ".join(dropped) + "."
    return None


def _blank_entry(skill, channel, project, run_id, note, base):
    return {
        "id": _next_id(base),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "skill": skill,
        "channel": channel,
        "project": project,
        "run_id": run_id,
        "note": note,
        "status": "recorded",
        "edits": [],
        "proposals": [],
    }


def add_rejection(*, output, reason, skill=None, channel=None, project=None,
                  run_id=None, base=None):
    """An output Patrick threw away rather than edited.

    A rejection has no edited version to diff against, so the signal is the
    stated reason. It escalates on repetition exactly like an edit does: the
    first time Patrick rejects something for a given reason, that is one data
    point, not a rule.
    """
    if not (reason or "").strip():
        raise FeedbackError("a rejection needs a reason; the reason is the whole signal")
    entry = _blank_entry(skill, channel, project, run_id, reason, base)
    edit = {
        "kind": REJECTION,
        "removed": [output.strip()[:2000]],
        "added": [],
        "removed_words": sorted(set(_content_words([reason]))),
        "added_words": [],
        "signature": f"rejection:{'|'.join(sorted(set(_content_words([reason])))[:6])}",
        "reason": reason,
    }
    scope, occurrences, rationale = escalate(
        edit, load_all(base), skill=skill, channel=channel, project=project
    )
    edit.update({"scope": scope, "occurrences": occurrences, "rationale": rationale})
    entry["edits"].append(edit)
    if scope != "local":
        entry["proposals"].append({
            "scope": scope, "rule": reason.strip().rstrip(".") + ".",
            "signature": edit["signature"], "occurrences": occurrences,
            "rationale": rationale, "status": "proposed",
        })
    entry["status"] = "proposed" if entry["proposals"] else "recorded-local"
    save_entry(entry, base)
    return entry


def add_correction(*, correction, skill=None, channel=None, project=None,
                   scope=None, base=None):
    """An explicit instruction from Patrick: "stop naming the day of the week".

    This is the one intake path that proposes a rule on first sight, and the
    reason is not a loosened standard -- it is that the generalizing was done by
    the human. The repetition threshold exists to stop *Patrick OS* inferring a
    rule from one observation. It has no business second-guessing a rule Patrick
    stated outright.
    """
    if not (correction or "").strip():
        raise FeedbackError("a correction needs text")
    entry = _blank_entry(skill, channel, project, None, correction, base)
    if scope is None:
        if skill:
            scope = f"skill:{skill}"
        elif channel:
            scope = f"channel:{channel}"
        elif project:
            scope = f"project:{project}"
        else:
            scope = "global"
    entry["edits"].append({
        "kind": CORRECTION, "removed": [], "added": [correction.strip()],
        "removed_words": [], "added_words": sorted(set(_content_words([correction]))),
        "signature": f"correction:{'|'.join(sorted(set(_content_words([correction])))[:6])}",
        "scope": scope, "occurrences": 1,
        "rationale": "stated explicitly by the human; no repetition threshold applies",
    })
    entry["proposals"].append({
        "scope": scope, "rule": correction.strip(),
        "signature": entry["edits"][0]["signature"], "occurrences": 1,
        "rationale": "stated explicitly by the human", "status": "proposed",
    })
    entry["status"] = "proposed"
    save_entry(entry, base)
    return entry


def add(*, original, edited, skill=None, channel=None, project=None, run_id=None,
        note=None, base=None):
    """Record one correction. Classifies but never writes a voice rule."""
    edits = diff(original, edited)
    if not edits:
        raise FeedbackError("original and edited versions are identical; nothing to learn")
    history = load_all(base)
    entry = _blank_entry(skill, channel, project, run_id, note, base)
    for edit in edits:
        scope, occurrences, rationale = escalate(
            edit, history, skill=skill, channel=channel, project=project
        )
        record = dict(edit)
        record["scope"] = scope
        record["occurrences"] = occurrences
        record["rationale"] = rationale
        entry["edits"].append(record)
        if scope == "local":
            continue
        text = propose_rule(edit)
        if not text:
            continue
        entry["proposals"].append(
            {
                "scope": scope,
                "rule": text,
                "signature": edit["signature"],
                "occurrences": occurrences,
                "rationale": rationale,
                "status": "proposed",
            }
        )
    if entry["proposals"]:
        entry["status"] = "proposed"
    else:
        entry["status"] = "recorded-local"
    save_entry(entry, base)
    return entry


# --- promotion ------------------------------------------------------------
def promote(entry_id, *, index=0, scope=None, text=None, base=None, verify=None):
    """Apply one proposal to the voice layer, with a regression gate and rollback.

    ``verify`` is a zero-argument callable returning ``(ok, report)``. The default
    runs the full regression suite. If it fails, the voice file is restored byte
    for byte and the promotion is refused.
    """
    entry = load_entry(entry_id, base)
    proposals = entry.get("proposals") or []
    if not proposals:
        raise FeedbackError(
            f"{entry_id} has no proposals; it was classified "
            f"{entry.get('status')!r} and must not become a rule"
        )
    if index >= len(proposals):
        raise FeedbackError(f"{entry_id} has no proposal at index {index}")
    proposal = proposals[index]
    if proposal.get("status") == "promoted":
        raise FeedbackError(f"{entry_id} proposal {index} is already promoted")

    target_scope = scope or proposal["scope"]
    rule_text = text or proposal["rule"]

    path = voice.scope_path(target_scope, base)
    existed = path.is_file()
    before = path.read_text(encoding="utf-8") if existed else None

    rule_id = voice.append_rule(
        target_scope, rule_text, source=f"feedback {entry_id}", base=base
    )

    if verify is None:
        from .testing import run_suite

        def verify():
            report = run_suite(base=base)
            return report["ok"], report

    ok, report = verify()
    if not ok:
        if existed:
            path.write_text(before, encoding="utf-8")
        else:
            path.unlink(missing_ok=True)
        raise FeedbackError(
            f"promotion refused: appending {rule_id} to {target_scope} broke the "
            f"regression suite; the voice file was restored unchanged"
        )

    proposal["status"] = "promoted"
    proposal["rule_id"] = rule_id
    proposal["promoted_scope"] = target_scope
    proposal["promoted_text"] = rule_text
    proposal["promoted_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entry["status"] = (
        "promoted"
        if all(p.get("status") == "promoted" for p in proposals)
        else "partially-promoted"
    )
    save_entry(entry, base)
    _append_changelog(entry_id, rule_id, target_scope, rule_text, proposal, base)
    return {"rule_id": rule_id, "scope": target_scope, "text": rule_text, "report": report}


def reject(entry_id, *, index=0, reason=None, base=None):
    entry = load_entry(entry_id, base)
    proposals = entry.get("proposals") or []
    if index >= len(proposals):
        raise FeedbackError(f"{entry_id} has no proposal at index {index}")
    proposals[index]["status"] = "rejected"
    proposals[index]["rejected_reason"] = reason
    if all(p.get("status") in {"rejected", "promoted"} for p in proposals):
        entry["status"] = "closed"
    save_entry(entry, base)
    return entry


def _append_changelog(entry_id, rule_id, scope, text, proposal, base):
    path = changelog_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_text(
            "# Voice changelog\n\n"
            "Every rule Patrick OS learned, when, and from what. Append-only.\n",
            encoding="utf-8",
        )
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    path.write_text(
        path.read_text(encoding="utf-8").rstrip("\n")
        + f"\n\n## {stamp} — {rule_id} added to {scope}\n\n"
        + f"- Rule: {text}\n"
        + f"- Source: feedback {entry_id}\n"
        + f"- Occurrences before promotion: {proposal.get('occurrences')}\n"
        + f"- Why this scope: {proposal.get('rationale')}\n"
        + f"- To revert: delete the `[{rule_id}]` line from `{voice.scope_path(scope, base).relative_to(root(base))}`\n",
        encoding="utf-8",
    )
