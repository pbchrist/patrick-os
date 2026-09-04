"""Deterministic checks on a produced output.

Structural fixtures prove the right rules reached the work order. These prove
something harder: that a *specific bad output* is caught. Each check is a pure
function over text, so behavioral regression runs offline, on every commit, with
no model and no network — and the outputs it runs against are real ones,
including the email Site Factory actually shipped.

Two severities, and the distinction is load-bearing. Site Factory finding SF-08,
verified: its deterministic spam-lint ran before the judge and deleted the two
evidence-richest candidates over the word "metadata", while a fatal duplicated
signature sailed through at 100/100. The lesson the teardown drew was explicit —
"style rules must annotate for repair, not eliminate; only fact-integrity rules
should block."

    blocking  — fact integrity. An unmeasured claim, a fabricated citation, a
                manufactured-evidence offer, a leaked address. These kill an
                output.
    advisory  — style. Hype register, an opener, length. These annotate an
                output for repair and never eliminate it.

Checks are declared per skill in `SKILL.md` front-matter under `output_checks`
and are therefore data, not code:

    output_checks:
      - check: forbid_perception_language
      - check: max_sentences
        section: Body
        limit: 4
"""

from __future__ import annotations

import re

BLOCKING = "blocking"
ADVISORY = "advisory"

REGISTRY = {}


class CheckError(ValueError):
    pass


class Finding:
    def __init__(self, check, severity, message, evidence=None):
        self.check = check
        self.severity = severity
        self.message = message
        self.evidence = evidence

    def as_dict(self):
        return {
            "check": self.check,
            "severity": self.severity,
            "message": self.message,
            "evidence": self.evidence,
        }

    def __repr__(self):
        return f"<{self.severity} {self.check}: {self.message}>"


def check(name, severity):
    def register(function):
        function.check_name = name
        function.severity = severity
        REGISTRY[name] = function
        return function

    return register


# --- helpers --------------------------------------------------------------
_SENTENCE = re.compile(r"[^.!?]+[.!?]")


def section_text(text, title):
    """Extract a labelled block. Accepts '## Title', 'Title:' or 'Title' on its own line."""
    if not title:
        return text
    pattern = re.compile(
        rf"^(?:#{{1,6}}\s*)?{re.escape(title)}\s*:?\s*$", re.IGNORECASE | re.MULTILINE
    )
    match = pattern.search(text)
    if not match:
        inline = re.compile(rf"^{re.escape(title)}\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
        found = inline.search(text)
        return found.group(1) if found else ""
    rest = text[match.end():]
    end = re.search(r"^(?:#{1,6}\s*)?[A-Z][A-Za-z ]{2,40}\s*:?\s*$", rest, re.MULTILINE)
    return rest[: end.start()] if end else rest


def _hits(text, pattern):
    return [m.group(0) for m in pattern.finditer(text)]


# --- fact-integrity checks (blocking) -------------------------------------
PERCEPTION = re.compile(
    r"\b("
    r"looks?\s+like|seems?\s+(?:like|to)|comes?\s+across|reads?\s+as|"
    r"(?:a|the|new|potential|prospective)\s+(?:visitor|customer|reader|prospect|candidate)s?\s+"
    r"(?:will|would|may|might|can|could|tends?\s+to|assume|think|feel|conclude|see|notice|wonder)|"
    r"(?:customers?|visitors?|readers?|prospects?|candidates?|people)\s+"
    r"(?:will|would|may|might)\s+\w+|"
    r"gives?\s+the\s+impression|creates?\s+the\s+impression|"
    # "To a new visitor, that looks like a copy-paste error" -- the construction
    # must actually ascribe a perception. Requiring the verb is what separates it
    # from "facts unique to the candidate:", a plain prepositional phrase that
    # this pattern flagged on a real run.
    r"to\s+(?:a|the|any)\s+(?:new\s+|potential\s+|prospective\s+)?"
    r"(?:visitor|customer|reader|prospect|candidate|user)s?\b[^.!?\n]{0,40}?"
    r"\b(?:looks?|seems?|appears?|reads?|feels?|comes?\s+across|"
    r"will\s+\w+|would\s+\w+|is\s+likely)\b|"
    r"you(?:'re|\sare)\s+probably\s+(?:ready|looking|open)"
    r")\b",
    re.IGNORECASE,
)


@check("forbid_perception_language", BLOCKING)
def forbid_perception_language(text, config):
    """G-002. The exact defect that shipped at evidence_fidelity 5/5:
    'To a new visitor, that looks like a copy-paste error...'"""
    found = _hits(text, PERCEPTION)
    if not found:
        return []
    return [
        Finding(
            "forbid_perception_language",
            BLOCKING,
            "states what a person perceives, concludes, or feels — nobody was surveyed",
            evidence=sorted(set(found))[:5],
        )
    ]


MANUFACTURED = re.compile(
    r"\b(?:write|writing|generate|generating|produce|producing|create|creating|"
    r"replace|replacing|source|sourcing|solicit|soliciting|seed|seeding|collect|collecting)\b"
    r"[^.!?\n]{0,60}\b(?:reviews?|testimonials?|ratings?|endorsements?|"
    r"references?|case\s+studies)\b",
    re.IGNORECASE,
)


@check("forbid_manufactured_evidence", BLOCKING)
def forbid_manufactured_evidence(text, config):
    """G-007. The same shipped email offered to 'replace those duplicates with
    distinct, verified reviews' — FTC review-authenticity exposure."""
    found = _hits(text, MANUFACTURED)
    if not found:
        return []
    return [
        Finding(
            "forbid_manufactured_evidence",
            BLOCKING,
            "offers to produce or replace the evidence it is measuring",
            evidence=sorted(set(found))[:5],
        )
    ]


EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")


@check("forbid_email_address", BLOCKING)
def forbid_email_address(text, config):
    """SF-06. Contact selection returns arbitrary harvested addresses; the way to
    make that unreachable is to hold no address at all."""
    found = [a for a in _hits(text, EMAIL) if not a.lower().endswith(("example.com", "example.org"))]
    if not found:
        return []
    return [
        Finding("forbid_email_address", BLOCKING,
                "contains an email address; this skill must hold no contact data",
                evidence=sorted(set(found))[:5])
    ]


SIGNOFF = re.compile(r"^\s*(?:best|thanks|regards|sincerely|cheers|warmly)\b[,.]?\s*$",
                     re.IGNORECASE)


@check("signature_once", BLOCKING)
def signature_once(text, config):
    """Two candidates scored 100/100 while containing the signature name twice,
    and that bug shipped in the Cool Blew output.

    Counts sign-off BLOCKS, not name mentions: a name inside a sentence is prose,
    a name alone on a line is a signature. Counting mentions would either miss the
    defect (limit raised to tolerate prose) or fire on every legitimate draft.
    """
    name = config.get("name", "Patrick")
    limit = int(config.get("limit", 1))
    lines = text.split("\n")
    blocks = 0
    for index, line in enumerate(lines):
        if line.strip() != name and not line.strip().startswith(name + " "):
            continue
        if len(line.strip()) > len(name) + 20:
            continue
        previous = lines[index - 1].strip() if index else ""
        if line.strip() == name or SIGNOFF.match(previous):
            blocks += 1
    if blocks <= limit:
        return []
    return [
        Finding("signature_once", BLOCKING,
                f"signature block for {name!r} appears {blocks} times; expected at most {limit}")
    ]


@check("require_sections", BLOCKING)
def require_sections(text, config):
    missing = [t for t in config.get("sections", []) if not section_text(text, t).strip()]
    if not missing:
        return []
    return [
        Finding("require_sections", BLOCKING,
                "output is missing required section(s): " + ", ".join(missing))
    ]


@check("require_phrases", BLOCKING)
def require_phrases(text, config):
    lowered = text.lower()
    missing = [p for p in config.get("phrases", []) if p.lower() not in lowered]
    if not missing:
        return []
    return [
        Finding("require_phrases", BLOCKING,
                "output is missing required text: " + ", ".join(repr(p) for p in missing))
    ]


CITED_QUOTE = re.compile(r'["“].+?["”]', re.DOTALL)
URL = re.compile(r"https?://\S+")
DATE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|"
                  r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s*\d{4})\b",
                  re.IGNORECASE)


NO_EVIDENCE_LINE = re.compile(r"^\s*[-*]?\s*(?:none\b|no\s+(?:quotes?|evidence|threads?))",
                              re.IGNORECASE)


@check("quotes_are_sourced", BLOCKING)
def quotes_are_sourced(text, config):
    """C-003/C-004. An undated, unlinked Reddit quote is unusable six weeks later
    and unverifiable today.

    Two exemptions, both learned from false positives on real output:
    a line that explicitly records the absence of evidence is not a quote, and a
    short quoted phrase is a term being named ("Prove your humanity"), not a
    mined comment. A mined comment is a sentence.
    """
    minimum_words = int(config.get("min_quote_words", 5))
    findings = []
    for block in config.get("sections", [None]):
        body = section_text(text, block) if block else text
        for line in body.split("\n"):
            if NO_EVIDENCE_LINE.match(line):
                continue
            quotes = CITED_QUOTE.findall(line)
            if not quotes:
                continue
            if all(len(q.split()) < minimum_words for q in quotes):
                continue
            window = line
            index = body.find(line)
            if index >= 0:
                window = body[index: index + len(line) + 200]
            if not URL.search(window):
                findings.append(Finding("quotes_are_sourced", BLOCKING,
                                        "quote has no permalink", evidence=[line.strip()[:120]]))
            elif not DATE.search(window):
                findings.append(Finding("quotes_are_sourced", BLOCKING,
                                        "quote has no date", evidence=[line.strip()[:120]]))
    return findings


VAGUE_COUNT = re.compile(r"\b(?:several|many|a\s+few|numerous|multiple|lots\s+of|"
                         r"a\s+number\s+of|plenty\s+of)\b", re.IGNORECASE)


@check("counts_are_numeric", BLOCKING)
def counts_are_numeric(text, config):
    """'Several recruiters said' is not a count. G-001: the evidence has a size."""
    body = section_text(text, config.get("section")) if config.get("section") else text
    found = _hits(body, VAGUE_COUNT)
    if not found:
        return []
    return [
        Finding("counts_are_numeric", BLOCKING,
                "uses a vague quantity where a count belongs",
                evidence=sorted(set(found))[:5])
    ]


@check("verdict_in_vocabulary", BLOCKING)
def verdict_in_vocabulary(text, config):
    allowed = [v.lower() for v in config.get("allowed", [])]
    label = config.get("label", "Verdict")
    found = section_text(text, label).strip().lower()
    if not found:
        return [Finding("verdict_in_vocabulary", BLOCKING, f"no {label} stated")]
    # The verdict must BE one of the allowed values, not merely contain one.
    # "strongly supported, act on it" contains "supported" and is exactly the
    # kind of smuggled confidence a controlled vocabulary exists to stop.
    # A trailing parenthetical is detail, not verdict: "mixed (9 of 13)" is fine.
    bare = found.split("(")[0].split("\n")[0].strip().strip(".;:,").strip()
    if bare in allowed:
        return []
    return [
        Finding("verdict_in_vocabulary", BLOCKING,
                f"{label} is not one of: " + ", ".join(allowed),
                evidence=[found[:80]])
    ]


CLAIM_ROW = re.compile(r"^\s*\|(?!\s*-)(?P<cells>.+)\|\s*$", re.MULTILINE)


@check("claims_have_sources", BLOCKING)
def claims_have_sources(text, config):
    """Every row of a claim table must carry a source cell. A claim with no row
    is a flourish; a row with no source is worse, because it looks cited."""
    body = section_text(text, config.get("section", "Claim table"))
    if not body.strip():
        return [Finding("claims_have_sources", BLOCKING, "no claim table found")]
    unsourced = []
    for match in CLAIM_ROW.finditer(body):
        cells = [c.strip() for c in match.group("cells").split("|")]
        if len(cells) < 2 or not cells[-1]:
            unsourced.append(cells[0][:80] if cells else "")
            continue
        if cells[0].lower().startswith("claim"):
            continue
    if not unsourced:
        return []
    return [Finding("claims_have_sources", BLOCKING,
                    "claim table row has no source", evidence=unsourced[:5])]


# --- style checks (advisory) ----------------------------------------------
HYPE = re.compile(r"\b(?:unlock|supercharge|game[- ]?changer|secret\s+weapon|10x|"
                  r"skyrocket|revolutionize|cutting[- ]edge|synerg\w+|"
                  r"leverage\s+(?:the\s+)?power)\b", re.IGNORECASE)


@check("forbid_hype", ADVISORY)
def forbid_hype(text, config):
    found = _hits(text, HYPE)
    if not found:
        return []
    return [Finding("forbid_hype", ADVISORY, "hype register (G-006)",
                    evidence=sorted(set(found))[:5])]


FLATTERY = re.compile(r"\b(?:impressive|amazing|incredible|rockstar|ninja|guru|"
                      r"passionate|world[- ]class|stellar|phenomenal)\b", re.IGNORECASE)


@check("forbid_flattery", ADVISORY)
def forbid_flattery(text, config):
    found = _hits(text, FLATTERY)
    if not found:
        return []
    return [Finding("forbid_flattery", ADVISORY, "flattery adjective",
                    evidence=sorted(set(found))[:5])]


@check("max_sentences", ADVISORY)
def max_sentences(text, config):
    body = section_text(text, config.get("section")) if config.get("section") else text
    count = len([s for s in _SENTENCE.findall(body) if s.strip()])
    limit = int(config.get("limit", 4))
    if count <= limit:
        return []
    return [Finding("max_sentences", ADVISORY,
                    f"{count} sentences, limit is {limit}")]


BAD_OPENER = re.compile(r"^\s*(?:great\s+post|love\s+this|so\s+true|this\.|"
                        r"couldn't\s+agree\s+more|well\s+said)", re.IGNORECASE)


@check("forbid_openers", ADVISORY)
def forbid_openers(text, config):
    body = section_text(text, config.get("section")) if config.get("section") else text
    for line in body.strip().split("\n"):
        if line.strip():
            if BAD_OPENER.match(line):
                return [Finding("forbid_openers", ADVISORY,
                                "agreement opener adds nothing", evidence=[line.strip()[:60]])]
            break
    return []


@check("forbid_emoji", ADVISORY)
def forbid_emoji(text, config):
    found = [c for c in text if ord(c) > 0x2500 and c not in "—–‘’“”…→←↔"]
    if not found:
        return []
    return [Finding("forbid_emoji", ADVISORY, "contains emoji or decorative glyphs",
                    evidence=sorted(set(found))[:5])]


# --- runner ---------------------------------------------------------------
def run(text, declared):
    """Run a skill's declared ``output_checks`` against ``text``."""
    findings = []
    for entry in declared or []:
        if isinstance(entry, str):
            entry = {"check": entry}
        name = entry.get("check")
        if name not in REGISTRY:
            raise CheckError(
                f"unknown check {name!r}; known checks: {', '.join(sorted(REGISTRY))}"
            )
        config = {k: v for k, v in entry.items() if k != "check"}
        for key in ("sections", "phrases", "allowed"):
            if isinstance(config.get(key), str):
                config[key] = [p.strip() for p in config[key].split("|") if p.strip()]
        findings.extend(REGISTRY[name](text, config))
    return findings


def verdict(findings):
    """blocked / repair / clean. Style never blocks (SF-08)."""
    if any(f.severity == BLOCKING for f in findings):
        return "blocked"
    if findings:
        return "repair"
    return "clean"


def format_findings(findings):
    if not findings:
        return "no findings"
    lines = []
    for finding in findings:
        line = f"  {finding.severity.upper():8} {finding.check}: {finding.message}"
        if finding.evidence:
            line += "\n           evidence: " + "; ".join(str(e) for e in finding.evidence)
        lines.append(line)
    return "\n".join(lines)
