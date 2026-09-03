---
name: narrative-sourcing
stage: EXECUTE
repo: pbchrist/narrative-sourcing (public)
local: ~/Desktop/📁 PROJECTS/APPS & SOFTWARE/Narrative Sourcing/APP
live: https://pbchrist.github.io/narrative-sourcing/
updated: 2026-09-03
---

# narrative-sourcing — truth record

Facts and constraints only. Procedure belongs in a skill; style belongs in
`voice/`. Everything below is quoted from or checked against the repo, not
recalled.

## What is it?

A browser tool that reconstructs a candidate's career arc from their own public
material and hands the recruiter a sourced brief. From its README: "the reading
is the part the machine can do. The writing has to stay human because that's the
part that can't be faked."

## Who is it for?

Recruiters doing individual outreach, not sequence operators.

## What phase is it in?

EXECUTE. Working software, published live, with a published ablation.

## What evidence says anybody wants it?

An ablation was run and published, "including the part where the effect is
smaller than I expected and not statistically significant." Grading is by the
deterministic check the product ships; no model judges it. That is honest
evidence of a *measured* result, and it is currently a weak one. Adoption
evidence: none recorded here yet. Treat as **unvalidated** for demand, not bad.

## What evidence says it produced money?

None on file. No payment record has been checked into this truth record.

## What is the next irreversible action?

Per the positioning note: correct the identity-mixing and semantic-evidence
defects, then test whether the interpretation changes real recruiters'
decisions. Do not build surrounding machinery before that.

## What condition pauses or kills it?

Recruiters read the brief and make the same decision they would have made
without it.

## Hard constraints (these govern every skill that touches this project)

- **It does not send messages. It never will, on purpose.** Any Patrick OS skill
  scoped to this project produces a human-gated brief or draft, never an
  outbound action.
- Every claim quotes its source word for word. A claim without a quotable source
  does not go in the brief.
- Nothing is inferred from a name, a photo, a school, or a gap in dates.
- The model endpoint is an off-repo Cloudflare tunnel with a **24 KB request-body
  cap**. This is why `local-qwen` carries `max_request_bytes: 24000` in
  `config/routes.json` — a work order over that size must route elsewhere rather
  than fail at the socket.
- PDF and docx parsing is hand-rolled in `docs/app.js`. There is no parsing
  library to lean on; malformed input is a real failure mode, not a hypothetical.
