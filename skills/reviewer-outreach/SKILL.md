---
name: reviewer-outreach
version: 4
purpose: Research, qualify, and draft one book-reviewer outreach packet without inventing or aging facts, then declare whether it is safe for a separately authorized sender to use.
task_class: draft.outreach
stage: outreach
mechanism_agnostic: true
investment_tier: pilot
channel: email
project: gate-of-nyandor-reviewer-outreach
outputs: send_packet
dry_run_default: true
sends: false
inputs:
  - name: reviewer_record
    type: string
    required: true
    description: Canonical CRM row for the reviewer or publication.
  - name: project_facts
    type: string
    required: true
    description: Current Gate of Nyandor facts and campaign constraints, including any authorized batch ceiling.
---

# reviewer-outreach

## Purpose

Produce a reviewer-outreach packet that survives scrutiny. The opening must be specific enough to prove current research happened, but every specific claim must still be true when the recipient reads it. A personalized sentence that is stale, inferred, or wrong is worse than a generic one because it advertises fake research.

The governing durable gates live in `config/reviewer-outreach.json`. This skill never sends. It can only emit `SENDABLE`, `FORM REQUIRED`, or `NOT SENDABLE` with evidence. Temporary operating choices such as daily volume, ramp speed, and attachment compression are campaign state, not permanent doctrine.

The canonical tracker for contact state is the `All Reviewers (351)` sheet. Helper, filtered, ranked, copied, or derived tabs are never authoritative for whether a reviewer has already been contacted.

## Inputs

- `reviewer_record`: the live CRM row from the canonical tracker. Status, prior contact state, contact route, genre fit, and notes come from here.
- `project_facts`: current book positioning and operational constraints supplied at runtime, including the human-authorized maximum number of sends for a batch when applicable.

## Prerequisites

- Read `config/reviewer-outreach.json` before doing anything else.
- The canonical tracker and Nyandor Gmail sent history are both available for duplicate-contact checks.
- Live web access is available. A stale directory entry alone is never sufficient.
- If a live send is later authorized, the execution layer must obey the send/writeback handshake in this skill before moving to another recipient.

## Procedure

1. **Check prior contact first in both authoritative sources.** Search the `All Reviewers (351)` canonical tracker and Nyandor Gmail sent history. If either source shows prior contact, decline, opt-out, suppression, or a previous send, output `NOT SENDABLE` unless the human explicitly requested a follow-up workflow. If the two sources disagree, output `NOT SENDABLE` and stop. Do not use helper tabs to resolve contact state.
2. **Verify the live policy.** Open the review policy/contact page on the current site. Record the URL, retrieval date, whether requests are open, accepted genres/formats, series policy if stated, and the required contact route.
3. **Honor the route.** If the reviewer requires a form, the packet must say `FORM REQUIRED`. Do not manufacture an email path because an address exists elsewhere.
4. **Verify current activity.** Find a current post, review, list, event, or policy statement that is genuinely useful for personalization.
5. **Match wording to evidence age.** Words such as `recent`, `currently`, `still`, `this week`, `your latest`, or equivalent require evidence recent enough to support that exact wording. There is no fixed day count. If the evidence does not justify a present-tense or recency claim, reframe it historically or remove it.
6. **Build an evidence ledger before writing.** For every reviewer-specific factual claim, capture: claim, source URL, source date when available, and retrieval date. If the claim cannot be mapped to evidence, remove it.
7. **Check fit.** Confirm current evidence supports adult fantasy / epic fantasy / speculative fantasy or another defensible fit. Do not qualify a reviewer from follower count alone.
8. **Draft the opening from evidence.** The first sentence should be specific to the reviewer and must pass the paste test: if it could be sent unchanged to another reviewer, it is not personalized enough.
9. **Use the approved book architecture.** The books branch from the same Voyd into different timestreams. Book One follows the failure path; Book Two follows the success path; consequences bleed between them. Do not dismiss Book One as unnecessary. Offer Book One as the way to experience the paired structure from the beginning.
10. **Specify the approved package.** Nyandor sender identity; real clickable BookFunnel link supplied at runtime; side-by-side covers attachment; Nyandor author signature.
11. **Apply style gates.** No em dash. No fake urgency. No demand for a positive review. No launch-pressure language. One recipient per message.
12. **Emit the packet.** Include evidence, subject, body, required attachment, contact route, and exactly one of: `SENDABLE`, `FORM REQUIRED`, or `NOT SENDABLE`.
13. **Specify writeback.** The packet must name the canonical CRM fields the execution layer must update after a successful send. This skill does not claim the writeback occurred.
14. **Bind the execution contract.** Any live sender using this packet must re-run the duplicate-contact check immediately before sending, then after a successful send must write `Contacted`, the actual send date, and an execution note to `All Reviewers (351)` and verify that write before any next recipient can be sent.
15. **Enforce the batch ceiling literally.** If the human authorizes N sends, N is the hard maximum number of send actions. A duplicate, conflict, failed writeback, or other error does not create permission for a replacement or compensating send. Stop the batch and hand control back to the human.

## Outputs

A send packet containing:

- Reviewer/publication
- Live-policy status and URL
- Current-activity evidence
- Personalization evidence ledger
- Required contact route
- Subject
- Final body
- Required attachment check
- `SENDABLE`, `FORM REQUIRED`, or `NOT SENDABLE`
- Required post-send CRM writeback fields
- Execution contract requiring pre-send duplicate recheck and verified post-send writeback
- Authorized batch ceiling when supplied at runtime

No live recipient address is required in the artifact. No send action exists in this skill.

## Quality checks

- Every reviewer-specific factual claim has a source URL and, when available, a source date.
- Present-tense and recency wording is no stronger than the evidence supports.
- The review policy was checked live during the current run.
- The reviewer is currently open to the requested contact route, or the packet is not `SENDABLE`.
- Prior-contact history was checked in both `All Reviewers (351)` and Nyandor Gmail sent history.
- No helper, ranked, filtered, copied, or derived sheet was used as authoritative contact state.
- The message does not say or imply that Book One is disposable or irrelevant.
- The paired-timeline explanation remains accurate.
- The packet requires the side-by-side cover asset.
- The BookFunnel link is supplied at runtime, not hard-coded into this public repository.
- The sender identity is Nyandor.
- The message contains no em dash.
- The packet states exactly what must be written back after execution.
- A successful send cannot be followed by another send until the canonical tracker writeback is verified.
- A batch never exceeds the human-authorized number of send actions, including when an earlier send was a duplicate or mistake.

## Failure modes

- **Stale personalization.** Present-tense wording built from evidence too old to support it. Find current evidence, reframe historically, or remove the line.
- **Directory truth treated as live truth.** A directory says requests are open while the current site says closed. The current site wins.
- **Wrong contact channel.** The reviewer asks for a form but the packet pretends email is acceptable.
- **Book One dismissal.** Saying `Book One isn't required` after explaining that the books are structurally paired undercuts the concept.
- **Attachment omission.** The side-by-side covers are part of the explanation, not decoration.
- **Wrong sender identity.** The packet names an unrelated personal sender instead of Nyandor.
- **Tracking gap.** A send occurs without immediate canonical-tracker writeback and verification. Stop the batch before any next send.
- **Helper-tab drift.** A derived or stale sheet is used to decide contact state. Re-run against `All Reviewers (351)` and Gmail before proceeding.
- **Compensating send.** An error or duplicate is treated as permission to add another recipient beyond the authorized send count. Stop the batch instead.
- **State conflict.** Tracker and Gmail disagree about prior contact. Do not send.
- **Control-plane send path.** Any future edit that gives this skill the ability to send violates Patrick OS v1 architecture.

## Escalation

Output `NOT SENDABLE` and hand to a human when:

- Review policy and directory disagree and the current site is ambiguous.
- The only personalization evidence is stale or undated and the message depends on a current claim.
- The reviewer charges money and the distinction between editorial review and promotional service is unclear.
- Series-order requirements conflict with the planned pitch.
- The correct contact route is inaccessible.
- Prior-contact history is contradictory between the canonical tracker and Gmail.
- A post-send writeback fails or cannot be verified.
- The authorized batch ceiling has been reached.
- Any duplicate or execution error occurs during a live batch.
- The message would need a claim that cannot be sourced.

## Examples

### Correct freshness use

Evidence: Fantasy Book Critic published SPFBO XI coverage immediately before outreach.

Acceptable opening:

`I've been following your SPFBO XI coverage, and since you're still actively digging through self-published fantasy, I thought The Divergent Path might be worth putting on your radar.`

This wording is allowed because live, dated evidence supports `still actively` at packet-generation time.

### Stale-source refusal

Evidence: the only SPFBO article found is from 2021.

Incorrect:

`I see you're still covering SPFBO...`

Correct action:

Find current evidence or remove the present-tense claim. Do not convert old evidence into a current relationship by wording alone.

### Live-send handshake

For every authorized recipient:

1. Re-check `All Reviewers (351)`.
2. Re-check Nyandor Gmail sent history.
3. If both are clear, send once.
4. Immediately write `Contacted`, the actual send date, and a send note to the canonical tracker.
5. Read the row back and verify the write.
6. Only then may the execution layer proceed to the next recipient.

If any step fails, the batch stops. There is no compensating send.

## Regression fixtures

- `fixtures/freshness-gate-present.json` asserts that the composed procedure contains the evidence-age discipline, the evidence-ledger requirement, and the explicit no-send boundary.
- `fixtures/execution-guard-present.json` asserts the canonical-tracker rule, dual-source duplicate check, send/writeback handshake, hard batch ceiling, and no-compensating-send rule.
