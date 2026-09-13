---
name: reviewer-outreach
version: 1
purpose: Research, qualify, personalize, and execute one book-reviewer outreach message without inventing or aging facts, then record the send in the canonical tracker.
task_class: draft.outreach
stage: outreach
mechanism_agnostic: true
investment_tier: pilot
channel: email
project: gate-of-nyandor-reviewer-outreach
outputs: outreach_record
dry_run_default: true
sends: true
inputs:
  - name: reviewer_record
    type: string
    required: true
    description: Canonical CRM row for the reviewer or publication.
  - name: project_facts
    type: string
    required: true
    description: Current Gate of Nyandor truth record.
  - name: send_authorization
    type: boolean
    required: true
    description: Explicit human approval for this send or approved batch.
---

# reviewer-outreach

## Purpose

Send reviewer outreach that survives scrutiny. The message must be specific enough to prove current research happened, but every specific claim must still be true when the recipient reads it. A personalized sentence that is stale, inferred, or wrong is worse than a generic one because it advertises fake research.

The governing hard gates live in `config/reviewer-outreach.json`. This procedure applies them.

## Inputs

- `reviewer_record`: the live CRM row. Status, prior contact state, contact route, genre fit, and notes come from here.
- `project_facts`: current book positioning and operational constraints.
- `send_authorization`: explicit human approval. `false` means draft only.

## Prerequisites

- Read `config/reviewer-outreach.json` before doing anything else.
- Read the project truth record before drafting.
- The CRM and Gmail sent history are both available for duplicate-contact checks.
- Live web access is available. A stale directory entry alone is never sufficient.
- The current daily send count is known before an external send.

## Procedure

1. **Check prior contact first.** Search the canonical tracker and sent mail. If the reviewer was already contacted, declined, opted out, or is suppressed, stop unless the human explicitly directs a follow-up.
2. **Verify the live policy.** Open the review policy/contact page on the current site. Record the URL, retrieval date, whether requests are open, accepted genres/formats, series policy if stated, and the required contact route.
3. **Honor the route.** If the reviewer requires a form, use the form workflow or stop. Do not substitute an email simply because an address can be found elsewhere.
4. **Verify current activity.** Find a current post, review, list, event, or policy statement that is genuinely useful for personalization.
5. **Apply the freshness gate.** Any wording such as `recent`, `currently`, `still`, `this week`, `your latest`, or equivalent requires a dated source within `personalization_freshness_days` from the config. Older evidence may be used only with historically accurate wording. If the date is unclear, do not make a time-sensitive claim.
6. **Build an evidence ledger before writing.** For every reviewer-specific factual claim, capture: claim, source URL, source date, retrieval date. If the claim cannot be mapped to evidence, remove it.
7. **Check fit.** Confirm current evidence supports adult fantasy / epic fantasy / speculative fantasy or another defensible fit. Do not contact based on follower count alone.
8. **Draft the opening from evidence.** The first sentence should be specific to the reviewer and must pass the paste test: if it could be sent unchanged to another reviewer, it is not personalized enough.
9. **Use the approved book architecture.** The books branch from the same Voyd into different timestreams. Book One follows the failure path; Book Two follows the success path; consequences bleed between them. Do not dismiss Book One as unnecessary. Offer Book One as the way to experience the paired structure from the beginning.
10. **Use the approved package.** Send from the Nyandor sender identity. Include the real clickable BookFunnel link supplied at runtime and the side-by-side covers attachment. Keep the attachment under the configured byte limit.
11. **Apply style gates.** No em dash. No fake urgency. No demand for a positive review. No launch-pressure language. One recipient per message.
12. **Check volume.** Do not exceed `daily_send_cap` unless the human explicitly changes that operating limit.
13. **Human gate.** If `send_authorization=false`, produce the draft and evidence ledger only. If true, send only after all quality checks pass.
14. **Write back immediately.** Update the canonical tracker with Contacted status and send date. Preserve enough notes to reconstruct why this reviewer was contacted. External leads not already in the tracker must be added rather than left outside the system.

## Outputs

An outreach record containing:

- Reviewer/publication
- Live-policy status and URL
- Current-activity evidence
- Personalization evidence ledger
- Subject
- Final body
- Attachment check
- Send status
- Send date
- Tracking writeback status

## Quality checks

- Every reviewer-specific factual claim has a source URL and source date.
- Any present-tense or recency claim passes the configured freshness window.
- The review policy was checked live during the current run.
- The reviewer is currently open to the requested contact route, or the output stops without sending.
- Prior-contact history was checked in both CRM and sent mail.
- The message does not say or imply that Book One is disposable or irrelevant.
- The paired-timeline explanation remains accurate.
- The side-by-side cover asset is attached and under the configured size limit.
- The BookFunnel link is clickable and supplied at runtime, not hard-coded into this public repository.
- The sender identity is Nyandor.
- The message contains no em dash.
- Daily volume remains within the configured cap unless explicitly overridden.
- The CRM writeback succeeds after send.

## Failure modes

- **Stale personalization.** Present-tense wording built from an old post. This creates the appearance of fabricated research. The fix is to verify the date and either find current evidence, reframe historically, or remove the line.
- **Directory truth treated as live truth.** A directory says requests are open while the current site says closed. The current site wins.
- **Wrong contact channel.** The reviewer asks for a form and receives unsolicited email anyway.
- **Book One dismissal.** Saying `Book One isn't required` after explaining that the two books are structurally paired undercuts the concept.
- **Attachment omission.** The side-by-side covers are part of the explanation, not decoration.
- **Oversized attachment.** A prior deliverability test flagged the original 1.86 MB PNG. Use the compressed asset under the configured limit.
- **Wrong sender.** Sending book outreach from an unrelated personal account sacrifices brand coherence and contaminates campaign state.
- **Tracking gap.** A message is sent but not recorded, making duplicate contact and follow-up logic unreliable.
- **Volume spike.** A new sender account jumps from a few messages to a large batch. Stay inside the current cap unless deliberately changed.

## Escalation

Stop and hand to a human when:

- Review policy and directory disagree and the current site is ambiguous.
- The only personalization evidence is stale or undated.
- The reviewer charges money and the distinction between editorial review and promotional service is unclear.
- Series-order requirements conflict with the planned pitch.
- The correct contact route is inaccessible.
- Prior-contact history is contradictory.
- The message would need a claim that cannot be sourced.
- The requested send would exceed the configured daily cap.

## Examples

### Correct freshness use

Evidence: Fantasy Book Critic published SPFBO XI coverage dated within the current freshness window.

Acceptable opening:

`I've been following your SPFBO XI coverage, and since you're still actively digging through self-published fantasy, I thought The Divergent Path might be worth putting on your radar.`

This wording is allowed only because the live, dated evidence supports `still actively` at send time.

### Stale-source refusal

Evidence: the only SPFBO article found is from 2021.

Incorrect:

`I see you're still covering SPFBO...`

Correct action:

Find current evidence or remove the present-tense claim. Do not convert old evidence into a current relationship by wording alone.
