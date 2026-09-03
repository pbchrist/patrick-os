---
scope: evidence
source: Site Factory Teardown - 2026-09-01, finding 4
captured: 2026-09-03
---

# Evidence — the sentence that broke the rule

Site Factory's highest-scoring output (PASS, 90.0, evidence_fidelity 5/5)
contained this sentence:

> "To a new visitor, that looks like a copy-paste error rather than a full roster
> of happy clients."

Nobody surveyed a new visitor. The claim is unmeasured customer perception. It
was forbidden in three separate prompts in that codebase and shipped anyway,
because no deterministic check could catch it and the LLM judge scored it
perfect.

The same email offered to "replace those duplicates with distinct, verified
reviews" — offering to produce reviews for a business, which is FTC
review-authenticity exposure, and a deliverable no evidence supported.

Two lessons, and they are different:

1. A prohibition stated only inside a prompt is not enforcement. (-> G-002)
2. The overreach was *fluent*. Fluency is what makes an unsupported claim
   dangerous, so fluency is not evidence of correctness. (-> G-007)

The contrast case, which is the version that should have shipped: naming the
observable fact — the same "Dana Reyes" review appears three times on the homepage —
without narrating what a stranger feels about it. (-> G-004)

Supports: G-002, G-004, G-007.
