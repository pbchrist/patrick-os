---
scope: global
namespace: strategy
version: 1
---

# Strategy — global

## Rules

- [ST-001] An opportunity with no identifiable buyer is not an opportunity. Record it as `watch`, never `pursue`.  (evidence: Site Factory teardown SF-12 — no buyer existed for 2 of the 5 benchmark businesses, and no buyer-qualification layer existed at all)
- [ST-002] Do not advance an investment tier without a measured result from the tier below it. note → audit → pilot → build.  (evidence: Site Factory reached automated outbound with zero validated demand; both gates are NO-GO)
- [ST-003] A mechanism must be selected from the diagnosis, not assumed from the tooling that happens to exist. "We have a website builder" is not a diagnosis.  (evidence: decisions/0006)
- [ST-004] "No intervention is supported yet" is a valid and expected outcome of mechanism selection. A selection process that cannot return it is not selecting.  (evidence: Site Factory SF-03 — a crawler timeout became a qualified rebuild opportunity at score 90)
