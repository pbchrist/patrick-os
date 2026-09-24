---
name: reviewer-outreach
version: 6
purpose: Research, qualify, draft, and safely execute reviewer outreach while keeping the canonical tracker synchronized with sends and replies.
task_class: draft.reviewer-outreach
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
- Read `config/reviewer-outreach-jev.json` before semantic qualification or draft QA.
- Use `All Reviewers (351)` as the sole canonical tracker.
- Nyandor Gmail inbox, sent history, and current drafts must be available for reconciliation and duplicate checks.
- Live web access must be available for policy/activity verification before a new recipient is qualified.
- JEV never decides facts already known from the tracker or Gmail. Prior contact, duplicate state, existing drafts, send authorization, attachment/link/signature presence, and tracker writeback remain deterministic.
- JEV receives compact evidence records, not raw browser dumps, whole mailboxes, whole spreadsheets, or chat history. Up to 20 work items are evaluated in one System One request per phase.
- If JEV is unavailable or uncertain, escalate that semantic decision to a reasoning model or human. Never convert an unavailable gate into an automatic pass.

## Procedure

1. **Reconcile replies once before the batch.** Search Nyandor Gmail for replies from previously contacted reviewers not yet reflected in `All Reviewers (351)`. Match and write back `Response` plus a concise dated note, then verify the writes.
2. **Read the candidate window once.** Pull the relevant canonical rows in one batch and build a candidate pool. Do not re-read the same tracker row reviewer by reviewer.
3. **Apply deterministic state filters in batches.** Batch-check canonical contact state, Nyandor Sent Mail, and current drafts. Exclude prior contacts, duplicate reviewer identities, existing current drafts, suppressed/declined records, and explicit route conflicts before spending semantic judgment on them. JEV may not override any of these facts.
4. **Gather only compact live evidence for viable candidates.** For each surviving reviewer capture the current policy/route, one or two recent relevant reviews/posts, dates, a concrete taste signal, and source URLs. Do not retain full pages when a short sourced evidence packet establishes the fact.
5. **Run the JEV candidate gate as one batch.** Evaluate up to 20 compact reviewer records in one `candidate` phase request. The parallel questions judge current-policy support, current activity, Nyandor fit, and whether the evidence is specific enough to personalize. `block` means replace the candidate; `review` means a reasoning model or human resolves only that item; `pass` advances it. Exact state from step 3 remains authoritative.
6. **Draft from the approved evidence packets.** The opening must be reviewer-specific. Use the approved Nyandor architecture: all-cat civilization played straight, the Voyd, Book One failure path, Book Two success path, and the realities bleeding together. Preserve campaign-wide links, signature, and cover handling as standardized components rather than rediscovering them per reviewer.
7. **Run the JEV draft gate as one batch.** Evaluate up to 20 completed drafts in one `draft` phase request. It judges reviewer-specificity, evidence support, story-engine clarity, human tone, and semantic policy compliance. A failed semantic gate never grants itself permission to rewrite facts; repair or escalate the affected draft only.
8. **Run deterministic draft QA in bulk.** Verify exact recipient, DRAFT state, one signature, required hyperlinks, cover attachment where allowed, no em dash, no duplicate current draft, and any reviewer-specific no-copy-until-reply exception. These checks are code/state authority, not JEV questions.
9. **Create or update the Gmail drafts in compact batches.** Leave every message as DRAFT unless the human explicitly authorizes sending in the current interaction. Confirm the requested final draft count before reporting completion.
10. **Honor human-reported replies immediately.** If the human says a reviewer replied, update the canonical tracker now. If the outcome is ambiguous, read the message before classifying it.
11. **Before every actual send, re-check the authoritative state.** Search `All Reviewers (351)` and Nyandor Gmail sent history again. If either shows prior contact, decline, suppression, duplicate identity, or a state conflict, do not send unless the human explicitly requested a follow-up.
12. **Honor the current contact route.** If a reviewer requires a form, the final execution decision is `FORM REQUIRED`; do not invent an email route because an address exists elsewhere.
13. **Send only with explicit current authorization.** Drafting, JEV passes, research, and QA are not send permission.
14. **Write back immediately after each successful send.** Write `Contacted`, the actual send date, and a concise execution note to `All Reviewers (351)`. Read the row back and verify it before another send action.
15. **Enforce an authorized send ceiling literally.** If the human authorizes N sends, N is the hard maximum number of send actions. A duplicate, failure, or writeback problem does not authorize a compensating send. Stop the live-send batch on an execution error.

### Why the JEV split exists

The batch should not consume a conversation by asking a full reasoning model to repeatedly decide small semantic questions. Code owns exact facts and execution. JEV supplies typed semantic judgments over compact evidence. The writer receives only the surviving evidence packet and the decision result, not the entire audit trail.

### Legacy safety invariants retained verbatim

- **Reconcile replies before choosing new recipients.** This is still the first batch-level state operation.
- After reply updates, **verify the tracker writeback** before recipient selection continues.
- Every personalization evidence record keeps the **source date** when one is available.
- **Present-tense and recency wording is no stronger than the evidence supports.**
- **This skill never sends** by itself. It prepares and judges work; external execution still requires explicit human authorization.
- A failed, duplicate, or aborted live send does not create extra quota. **There is no compensating send.**

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
- Candidate semantic qualification is evaluated from compact evidence through the JEV candidate gate when available.
- Completed drafts pass the JEV draft gate or are explicitly escalated; missing JEV service is never treated as a pass.
- JEV never overrides canonical tracker/Gmail facts or grants send authority.
- Up to 20 items are fanned out in one JEV request per phase instead of one semantic model call per reviewer.

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
