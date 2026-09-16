---
name: reviewer-outreach
version: 5
purpose: Research, qualify, draft, and safely execute reviewer outreach while keeping the canonical tracker synchronized with sends and replies.
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

Keep reviewer outreach accurate, deduplicated, and synchronized. The canonical tracker is `All Reviewers (351)`. Helper, filtered, ranked, copied, or derived tabs are never authoritative for contact state or response state.

The governing durable gates live in `config/reviewer-outreach.json`. This skill is automatically applicable to Gate of Nyandor reviewer-send intent such as `send`, `send more`, `send N more`, `reach out to reviewers`, or equivalent wording. The human does not need to name the skill.

The skill also owns reply-state reconciliation. A reviewer reply observed in Nyandor Gmail or explicitly reported by the human must be written back to `All Reviewers (351)` promptly. The human handling the conversational reply does not disable tracker maintenance.

## Inputs

- `reviewer_record`: the live CRM row from `All Reviewers (351)`.
- `project_facts`: current book positioning, sender identity, BookFunnel link, cover asset, and any authorized batch ceiling.

## Prerequisites

- Read `config/reviewer-outreach.json` first.
- Use `All Reviewers (351)` as the sole canonical tracker.
- Nyandor Gmail inbox and sent history must be available for reply reconciliation and duplicate checks.
- Live web access must be available for policy/activity verification before a new recipient is qualified.

## Procedure

1. **Reconcile replies before choosing new recipients.** Search Nyandor Gmail for replies from previously contacted reviewers that are not yet reflected in `All Reviewers (351)`. Match each reply to the canonical row. Update `Response` to `Yes`, `No`, or `Follow-up/Other` as supported by the message, and append a concise dated note. Verify the tracker writeback before selecting any new recipient.
2. **Honor human-reported replies immediately.** If the human says a reviewer replied, treat that as an instruction to update the canonical tracker now. Do not wait for a later batch. If the stated outcome is clear, write it. If the outcome is ambiguous, read the message before classifying it.
3. **Check prior contact in both authoritative sources.** Before every send, search `All Reviewers (351)` and Nyandor Gmail sent history. If either shows prior contact, decline, opt-out, suppression, or a previous send, the reviewer is `NOT SENDABLE` unless the human explicitly requested a follow-up. If the two sources disagree, stop.
4. **Verify the live policy.** Open the current review policy/contact page. Record whether requests are open, accepted genres/formats, series policy if stated, and the required contact route.
5. **Honor the route.** If the reviewer requires a form, mark `FORM REQUIRED`. Do not invent an email route because an address exists elsewhere.
6. **Verify current activity.** Find current evidence useful for personalization. Do not turn old evidence into a present-tense claim.
7. **Build an evidence ledger.** Every reviewer-specific factual claim must map to a source URL and source date when available.
8. **Check fit.** Confirm current evidence supports adult fantasy, epic fantasy, speculative fantasy, or another defensible fit.
9. **Draft from evidence.** The opening must be specific enough that it could not be pasted unchanged to another reviewer.
10. **Use approved book architecture.** Book One follows the failure path; Book Two follows the success path; consequences bleed between timestreams. Do not dismiss Book One as irrelevant.
11. **Use the approved package.** Nyandor sender identity, live BookFunnel link supplied at runtime, side-by-side covers, Nyandor author signature.
12. **Apply style gates.** No em dash. No fake urgency. No demand for a positive review. No launch-pressure language. One recipient per message.
13. **Re-check immediately before send.** Re-run the canonical-sheet and Gmail duplicate check immediately before the send action.
14. **Write back immediately after send.** After a successful send, write `Contacted`, the actual send date, and a concise execution note to `All Reviewers (351)`. Read the row back and verify it before any next send.
15. **Enforce the batch ceiling literally.** If the human authorizes N sends, N is the hard maximum number of send actions. A duplicate, failed writeback, or other error does not authorize a replacement or compensating send. Stop the batch.

## Outputs

A reviewer packet or execution decision containing:

- reviewer/publication
- live-policy status and URL
- current-activity evidence
- personalization evidence ledger
- required contact route
- subject and final body
- required attachment check
- exactly one of `SENDABLE`, `FORM REQUIRED`, or `NOT SENDABLE`
- required post-send tracker fields
- current authorized batch ceiling when applicable
- confirmation that reply reconciliation was completed before recipient selection

## Quality checks

- `All Reviewers (351)` is the only authoritative tracker.
- Nyandor inbox replies are reconciled before new-recipient selection.
- Human-reported replies are written back promptly.
- `Response` reflects the actual reply outcome and Notes contain a dated concise summary.
- Prior-contact history is checked in both canonical tracker and Nyandor sent history before every send.
- No helper or derived sheet determines contact state.
- Live policy and contact route are verified.
- Every reviewer-specific factual claim is sourced.
- The sender identity is Nyandor.
- The side-by-side cover asset is required.
- No em dash appears in the outreach message.
- A successful send cannot be followed by another send until tracker writeback is verified.
- A batch never exceeds the human-authorized send count.

## Failure modes

- **Unreconciled reply.** Gmail contains a reviewer response while the sheet still shows no response. Update and verify the sheet before selecting new recipients.
- **Misclassified reply.** A nuanced response is forced into Yes/No without evidence. Use `Follow-up/Other` and a note instead.
- **Tracking gap.** A send or observed reply is not written back immediately. Stop the workflow until corrected.
- **Helper-tab drift.** A derived or stale tab is used for contact state. Re-run against `All Reviewers (351)`.
- **State conflict.** Tracker and Gmail disagree about prior contact. Do not send.
- **Compensating send.** An error is treated as permission to exceed the authorized batch size. Stop instead.
- **Wrong contact route.** A form-only reviewer is emailed directly.
- **Stale personalization.** Present-tense wording rests on evidence too old to support it.

## Escalation

Stop and hand control back to the human when:

- a reply cannot be matched confidently to a tracker row
- a reply outcome is ambiguous and the message cannot be read
- tracker and Gmail disagree about prior contact
- a tracker writeback fails or cannot be verified
- policy and directory evidence conflict materially
- the authorized batch ceiling is reached
- any duplicate or execution error occurs during a live batch

## Examples

### Reply reconciliation

Nyandor Gmail contains a decline from Alex at Spells and Spaceships. Before any new reviewer is selected, update the canonical row to `Response = No` and append a dated note stating that Alex declined. Read the row back to verify the write.

Nyandor Gmail contains an acceptance from Ashley at bonesandbookspines. Update `Response = Yes`, append a dated acceptance note, and verify the row.

### Live-send handshake

For every authorized recipient:

1. Reconcile outstanding replies.
2. Re-check `All Reviewers (351)`.
3. Re-check Nyandor Gmail sent history.
4. If clear, send once.
5. Immediately write Contacted, send date, and note.
6. Read the row back and verify it.
7. Only then proceed to the next recipient.

If any step fails, the batch stops. There is no compensating send.
