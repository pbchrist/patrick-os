---
name: site-factory
stage: DECIDE
repo: pbchrist/hermes-projects (private)
path_in_repo: site-factory/
branch: audit/site-factory-20260901
audit: ~/Desktop/📁 PROJECTS/APPS & SOFTWARE/Site Factory/AUDITS & HANDOFFS/Site Factory Teardown - 2026-09-01.html
updated: 2026-09-03
---

# site-factory — truth record

## What is it?

A prospect-discovery and commercial-email pipeline: 27 modules, ~2,317 LoC, in
`site-factory/` on the `audit/site-factory-20260901` branch of the private
`pbchrist/hermes-projects` repo. It is **not** on `main`.

## Who is it for?

Iconic's prospecting: find a small business with an observable website problem,
produce an evidence-backed observation, offer a Narrative Decision Audit.

## What phase is it in?

DECIDE. Both gates are NO-GO as of the 2026-09-01 adversarial teardown.

## What evidence says anybody wants it?

None. Finding SF-12: no buyer exists for 2 of the 5 benchmark businesses, and
there is no buyer-qualification layer. Demand is **unvalidated**.

## What evidence says it produced money?

None on file.

## What is the next irreversible action?

Clear Gate 1 (twelve acceptance criteria in the teardown's §8) before any
automated test-email generation resumes. Estimated 1–2 weeks of focused work.

## What condition pauses or kills it?

Any live send before Gate 2 clears. Gate 2 additionally requires legal
compliance, entity-verification accuracy, and buyer qualification — "none of
which currently exist in any form. Not weeks away."

## Verified defects that constrain every skill scoped here

Verified by execution in the teardown, not inferred:

- **SF-03** — crawler failure is converted into a sellable rebuild opportunity.
  `qualify_website_redesign()` returns `{'qualified': True, 'score': 90}`
  whenever `reachable` is false, and "unreachable" includes Cloudflare
  challenges, 403s on our User-Agent, TLS quirks, and timeouts. The email then
  asserts "{host} isn't loading right now" to a business owner. Highest
  reputational-risk path in the codebase.
- **SF-05** — official-site verification accepts a single-token name match
  (`ok = score>=35 or (len(name_tokens)==1 and name_hits==1)`), so "Sunrise",
  "Ironwood", and "Cedar" verify against any page containing the word once, at
  `confidence: high`. Every downstream claim can be about someone else's site.
- **SF-06** — contact selection will return an arbitrary harvested address with
  `score=0` if it is the only candidate. Nothing asserts the recipient is
  affiliated with the business.
- **SF-07** — one calibration example contaminates writer, judge, benchmark, and
  test suite. The single passing output scored 0.590 trigram similarity to the
  calibration text; the four failures scored 0.015–0.081. No score the system
  produces carries information.
- **SF-08 / SF-09** — the deterministic spam-lint runs before the judge and
  deletes the strongest candidates; a single `NEITHER` verdict discards the whole
  pool and control falls back to picking by spam-word count.

## What has since been remediated (present on the branch, post-teardown)

`outbound_guard.py`, `halt_outbound.py`, and `buyer_qualification.py` now exist.
`outbound_guard.resolve_recipient()` fails closed: `SITE_FACTORY_SEND_MODE`
defaults to `off`, a halt file and env flag can stop everything, suppressed
statuses block sends, live mode requires a per-business approval token plus
compliance approval plus verified SPF/DKIM/DMARC plus a warmed domain plus a
daily cap plus bounce/complaint-rate circuit breakers.

This closes SF-01 and SF-04 mechanically. It does **not** close SF-03, SF-05,
SF-06, or SF-07, which are correctness defects rather than outbound controls.

## Position in the architecture

Site Factory is the **executor for the `website` mechanism** (see
`config/mechanisms.json` and `decisions/0006`). It is not the top-level
commercial decision engine, and the model "find a bad website → build a better
website" is one abstraction too low.

Mechanism selection sits above it. That stage does not exist yet, which is why
SF-03 was possible at all: with no layer able to conclude "no web intervention is
warranted", a crawler timeout could only come out the other side as a qualified
rebuild at score 90.

Its two skills cover `qualification` and `outreach` for one mechanism — 2 of 8
stages, 1 of 6 mechanisms. `patrick pipeline` prints the rest.

## Integration boundary for Patrick OS

Patrick OS **reads** this project and **writes nothing into it**. No file in
`hermes-projects` is modified, no branch is pushed, no environment variable it
owns is set by Patrick OS. The skills here produce artifacts a human carries
across. Site Factory's behavior today is exactly its behavior before Patrick OS
existed.
