---
name: site-factory-email
version: 1
purpose: Draft one commercial email from a verified prospect record, as a file a human carries, with no send path and no live recipient.
task_class: draft.email
channel: email
project: site-factory
outputs: draft
dry_run_default: true
sends: false
min_quality: 3
inputs:
  - name: prospect_record
    type: string
    required: true
    description: The output of site-factory-prospect, verbatim. Not a summary of it.
  - name: offer
    type: string
    required: true
    description: What is being offered, in one sentence, and what it costs.
  - name: recipient_role
    type: string
    required: false
    description: The role of the intended reader, e.g. "practice owner". Never an email address.
---

# site-factory-email

## Purpose

Draft the email Site Factory would have sent, under the constraints its own
teardown established, and stop at a file. This skill exists because the pipeline
produced a fluent, high-scoring email containing an unmeasured claim about
customer perception and an offer to manufacture reviews — and every automated
gate passed it.

## Inputs

- `prospect_record`: verbatim output of `site-factory-prospect`.
- `offer`: {{ offer }}
- `recipient_role`: {{ recipient_role }}

## Prerequisites

- The prospect record's identity confidence is `medium` or `high`. At `none`,
  there is no email to write.
- The record's `fetch_status` is `ok`. A record with a failed retrieval cannot
  produce an email, because there is nothing observed to write about.
- **No recipient address is accepted by this skill, ever.** Patrick OS holds no
  contact data for this pipeline. SF-06 is verified: contact selection will
  return an arbitrary harvested address if it is the only candidate.
- Gate 2 is NO-GO. This draft cannot be sent by anyone, through any path, today.

## Procedure

1. Copy the identity confidence and `fetch_status` from `prospect_record` into
   the draft header. If either is missing, stop and say so.
2. Pick exactly one observation. The most specific one, not the most alarming.
3. Write the subject line naming that observation. Not the offer, not a question.
4. Write the body: one sentence stating the observation, one stating the
   consequence *the evidence supports*, one making the ask. Three sentences.
5. **Consequence discipline.** The consequence sentence may describe only what is
   mechanically true — "the same review appears three times" supports "the
   testimonial section shows one reviewer, not several". It does not support any
   sentence about what a visitor concludes, feels, or does. That exact overreach
   shipped at evidence_fidelity 5/5.
6. State the offer and its price, once, plainly.
7. Sign once. Then read the rendered draft and confirm the signature block
   appears exactly once — two candidates scored 100/100 while containing
   "Patrick Bradley" twice, and that bug shipped in the Cool Blew output.
8. Emit the draft with a claim table: every sentence making a factual claim,
   mapped to the line of `prospect_record` it came from.
9. Emit the compliance block as *unsatisfied*: no postal address, no unsubscribe
   URL, no verified sending domain. Say plainly that this draft is not lawful to
   send as commercial email until those exist.

## Outputs

A draft file with: `Identity`, `Fetch status`, `Subject`, `Body`, `Claim table`,
`Compliance status: NOT SATISFIED`, `Send status: NOT SENDABLE (Gate 2 NO-GO)`.

Written to the run directory. No recipient field exists in the output format.

## Quality checks

- Body is at most four sentences.
- Every factual claim has a row in the claim table sourced to `prospect_record`.
- No sentence describes what a visitor, customer, or reader thinks, feels,
  assumes, concludes, or does. Search the draft for "looks like", "seems",
  "comes across", "a visitor", "customers may" — each is a defect.
- No offer to produce, replace, solicit, or seed reviews, testimonials, or
  ratings. This is FTC review-authenticity exposure, not a style preference.
- The signature block appears exactly once.
- No pipeline quality score is cited (SF-07).
- The compliance block is present and says NOT SATISFIED.
- No email address appears anywhere in the output.

## Failure modes

- **Fluent overreach.** The verified case: "To a new visitor, that looks like a
  copy-paste error rather than a full roster of happy clients." Scored 90.0,
  evidence_fidelity 5/5, forbidden by three separate prompts, shipped anyway.
- **Manufactured-evidence offer.** The same email offered to "replace those
  duplicates with distinct, verified reviews".
- **Duplicated signature** at a perfect deterministic score.
- **Writing from a failed fetch**, producing "{host} isn't loading right now".
- **Score citation** as evidence of quality.

## Escalation

Stop and hand to a human when:

- The observation concerns a named individual — a reviewer, an employee.
- The business is in a regulated category (medical, dental, legal, financial)
  and the observation touches its claims about outcomes.
- Identity confidence is `medium` rather than `high`.
- Anyone asks for a recipient address to be added. That is a Gate 2 conversation.

## Examples

Input: the Sunrise Dentistry prospect record at identity `medium`, offer =
"a Narrative Decision Audit, $500".

Correct output excerpt:

```
Identity: medium    Fetch status: ok
Subject: The same review appears three times on your homepage

Body:
The testimonial carousel on your homepage shows the review card reading
"Dana Reyes" three times in a row. The section therefore displays one reviewer
rather than several. I do a $500 Narrative Decision Audit that goes through a
site's claims this way — worth twenty minutes?

Patrick

Claim table
| Claim                                  | Source in prospect_record |
| "Dana Reyes" card appears three times    | Observations, line 1      |
| section displays one reviewer          | derived, mechanical       |

Compliance status: NOT SATISFIED — no postal address, no unsubscribe URL, no
verified sending domain.
Send status: NOT SENDABLE (Gate 2 NO-GO).
```

The rejected version of the same email, for contrast: "To a new visitor, that
looks like a copy-paste error rather than a full roster of happy clients." No
visitor was surveyed. That sentence is the defect this skill exists to prevent.

## Regression fixtures

`fixtures/` asserts the perception-language ban, the no-recipient rule, and the
compliance block all reach the work order, and that the draft route does not fall
to the writer model that Site Factory's contaminated judge shares an answer key
with.
