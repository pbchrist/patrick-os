# voice/ — provisional

**These rules are scaffolding. They are not a finished model of Patrick's voice.**

Every rule currently in this directory was derived from exactly two documents:

- `~/Desktop/LATEST — What Patrick Actually Does.md` — Patrick's own positioning
  note, quoted in `evidence/what-patrick-does.md`.
- `Site Factory Teardown - 2026-09-01` — an adversarial third-party audit, quoted
  in `evidence/sunrise-overreach.md` and `evidence/site-factory-teardown.md`.

That is two documents. A real voice model needs a corpus: Patrick's actual sent
outputs, the edits he made to drafts, the outputs he rejected outright, and his
explicit corrections. Until that corpus exists, treat everything here as a
starting hypothesis that the feedback compiler is expected to overturn.

Specifically, these rules are **under-evidenced** in the ways that matter most:

- They are almost entirely *prohibitions* derived from one audit of one failed
  pipeline. They describe what Patrick does not want. They barely describe what
  he sounds like when he is writing well.
- No rule here was derived from a real edit Patrick made to a real draft. That is
  the only evidence type that proves a rule rather than proposing one.
- The channel files (`linkedin`, `email`, `reddit`) are conventions, not
  observations. Nothing in them was measured against Patrick's actual posts.

## Provenance is mandatory

Every rule must be traceable to the evidence that produced it. Two forms:

```
- [G-002] Never claim customer behavior ...  (evidence: voice/evidence/sunrise-overreach.md)
- [S-001] Say what is on the page ...  (source: feedback F-20260903-002)
```

A rule with neither is an opinion, and this directory is not for opinions. When
the corpus arrives, the audit is mechanical: any rule with no `evidence:` and no
`source:` is a candidate for retirement.

Rules created by `patrick feedback promote` always carry a `source:` pointing at
the feedback entry, and the entry records the occurrence count, the contexts, and
the rationale for the scope chosen. `feedback/CHANGELOG.md` carries the same, plus
a revert instruction.

## Scope and composition

Rules compose most-general-first, so a narrower rule is stated last and reads as
the override:

```
global  ->  channel:<name>  ->  project:<name>  ->  skill:<slug>
```

`patrick voice show --skill <slug>` prints exactly what a given skill composes.

## Retiring a rule

Move it under `## Retired` in its file. Never delete it, and never reuse its id —
old outputs must stay explainable, and `next_rule_id` scans retired ids too.

## What the corpus intake should collect

When the real corpus arrives, the ingest wants, per item: the draft Patrick OS
(or anything else) produced, the version Patrick actually sent, the channel, the
project, and — where he said it — why. `patrick feedback add --original X
--edited Y --skill S --channel C` is the intake path, and it already refuses to
generalize anything it has only seen once.
