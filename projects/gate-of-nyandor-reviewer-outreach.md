---
name: gate-of-nyandor-reviewer-outreach
stage: EXECUTE
updated: 2026-09-12
---

# gate-of-nyandor-reviewer-outreach

## Durable sources

- Campaign state lives in the external Google Sheet titled `TDP reviwer outreach`.
- Message history lives in the Nyandor Gmail account.
- Procedure lives in `skills/reviewer-outreach/SKILL.md`.
- Hard gates live in `config/reviewer-outreach.json`.
- Chat context is not the source of truth for campaign state.

## Book facts

- *The Divergent Path* is Book Two of *The Gate of Nyandor*.
- The Voyd creates branching timestreams.
- Book One follows the failure branch.
- Book Two follows the success branch.
- Consequences can bleed between the two realities.
- The paired covers visually express that structure.
- Book One must not be described as disposable or irrelevant.

## Operational facts

- Use the Nyandor sender identity.
- Current daily cap is defined in config.
- Current freshness window is defined in config.
- The side-by-side cover asset must meet the configured size limit.
- A real-format Mail-Tester check on 2026-09-12 scored 9/10; attachment size was the main actionable warning.
- Current reviewer-site policy overrides stale directory metadata.
- Time-sensitive personalization requires dated current evidence.

## Boundary

Patrick OS prepares and checks the send packet. It does not send. External execution requires separate human authorization and a separate connector action.
