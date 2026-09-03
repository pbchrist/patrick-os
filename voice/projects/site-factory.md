---
scope: project:site-factory
version: 1
---

# Voice — site-factory

## Rules

- [P-001] Both gates are NO-GO. No output may be phrased as ready to send, and no output may imply sending is imminent.
- [P-002] A finding must come from something observable on the page. If the crawler failed, the finding is "we could not retrieve the page", never a claim about the business.
- [P-003] State the identity-verification confidence next to any claim about a business's website. A single-token name match is not verification (SF-05).
- [P-004] Never propose a deliverable that would manufacture the evidence it measures — writing reviews, generating testimonials, seeding ratings.
- [P-005] Do not cite a quality score produced by this pipeline as evidence of anything. Its judge is contaminated by a single calibration example (SF-07).
