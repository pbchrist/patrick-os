---
scope: evidence
source: Site Factory Teardown - 2026-09-01, findings SF-03 and SF-07
captured: 2026-09-03
---

# Evidence — infrastructure failure is not a finding about the world

SF-03, verified by execution: `qualify_website_redesign()` returned
`{'qualified': True, 'score': 90}` whenever the crawler could not reach a site.
"Unreachable" includes Cloudflare challenges, 403s on our own User-Agent, TLS
quirks, and timeouts. The generated email then told a business owner
"{host} isn't loading right now" — a fabricated factual assertion about a live
business, produced by our own infrastructure failure.

SF-07, verified by measurement: the single calibration example scored 0.590
trigram similarity to the one passing output, versus 0.015–0.081 for the four
failures. The judge's own rejection text cited "the rhetorical structure of the
positive calibration" as its standard. A judge sharing an answer key with the
writer produces a number that carries no information.

Supports: G-009, and the `judge` route's hard `deny` of the writer model in
`config/routes.json`.
