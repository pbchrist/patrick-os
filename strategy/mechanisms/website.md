---
scope: mechanism:website
namespace: strategy
version: 1
---

# Strategy — mechanism:website

## Rules

- [M-001] A web intervention requires a retrieved page. If the fetch failed, no web mechanism may be selected, because nothing about the site is known.  (evidence: Site Factory SF-03, verified by execution)
- [M-002] A web intervention requires identity confidence of at least medium. Below that, the observed defects may belong to a stranger's website.  (evidence: Site Factory SF-05, verified by execution)
- [M-003] Do not select a web mechanism merely because a web defect exists. A duplicate testimonial is observable and may still be the least valuable thing wrong with the business.
- [M-004] Do not select a web mechanism for a business whose only observable defects are cosmetic; cosmetic defects have never produced a reply.  (source: feedback F-20260903-005)
