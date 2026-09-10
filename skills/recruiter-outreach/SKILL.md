---
name: recruiter-outreach
version: 1
purpose: Draft one candidate outreach message grounded in the candidate's own public record, or refuse when the record does not support a specific reason to contact them.
task_class: draft.outreach
channel: email
project: narrative-sourcing
outputs: draft
dry_run_default: true
sends: false
min_quality: 3
inputs:
  - name: role
    type: string
    required: true
    description: The role being filled. Title, level, and the one thing that makes it non-generic.
  - name: candidate_evidence
    type: string
    required: true
    description: Public, candidate-provided material only — their profile text, their talks, their repos. Pasted verbatim.
  - name: comp_range
    type: string
    required: false
    description: Posted range. If absent, the draft must say the range is not yet disclosed rather than omitting the subject.
  - name: why_them
    type: string
    required: false
    description: The specific reason this person. If blank, the skill derives one and shows its evidence, or refuses.
output_checks:
  - check: require_sections
    sections: Hook|Evidence table|Draft message
  - check: claims_have_sources
    section: Evidence table
  - check: forbid_perception_language
  - check: forbid_unmeasured_consequence
  - check: forbid_flattery
  - check: forbid_hype
  - check: forbid_email_address
---

# recruiter-outreach

## Purpose

Outreach that names something only this candidate's record contains, so the
candidate can tell in one read that a human looked. If the record does not
support that, the correct output is a refusal, not a better-worded template.

This is the narrative-sourcing method applied to a single message: read the
career as a story, show the proof, produce a human-gated draft.

## Inputs

- `role`: {{ role }}.
- `candidate_evidence`: verbatim public material. See Prerequisites.
- `comp_range`: {{ comp_range }}.
- `why_them`: the specific hook, if already known.

## Prerequisites

- Every fact used comes from `candidate_evidence`. Nothing is inferred from a
  name, a photo, a school, a company's reputation, or a gap in dates.
- No scraped, purchased, or inferred contact data enters this skill.
- The role is real and open. Drafting outreach for a pipeline-building requisition
  is a different, disclosed thing.

## Procedure

1. Read `candidate_evidence` and list the three most specific verifiable facts in
   it. Specific means: this sentence could not be pasted into another candidate's
   message.
2. If fewer than one such fact exists, output `insufficient evidence to contact`
   and stop. Do not proceed on company name, title, or school alone.
3. Choose the hook: the single fact that connects to {{ role }}. State the
   connection in one sentence.
4. Draft: one sentence naming the hook, one naming what the role offers that
   relates to it, one asking for a specific next step.
5. Compensation: if `comp_range` is given, state it. If not, say explicitly that
   the range is not yet disclosed and that Patrick will share it on reply. Never
   omit the subject silently.
6. Emit the draft plus an evidence table: each claim in the message mapped to the
   line of `candidate_evidence` it came from.

## Outputs

A draft file containing: `Hook`, `Evidence table`, `Draft message`, `Checks`,
`Disclosure`. Written to disk only. Patrick OS does not send, and holds no
candidate contact address.

## Quality checks

- Every factual claim about the candidate appears in the evidence table with a
  source line. A claim with no row is a defect, not a flourish.
- No sentence describes what the candidate wants, feels, is ready for, or is
  looking for. Their motivation was not measured.
- No flattery adjective: "impressive", "amazing", "rockstar", "passionate".
- The ask is one specific next step, not "let me know if interested".
- Compensation is addressed, one way or the other.
- The message would be false if pasted to a different candidate. If it would
  still read fine, the hook is not specific enough.

## Failure modes

- **Inferred motivation.** "I saw you've been at X for four years, you're
  probably ready for a change." Tenure is not intent, and the candidate can tell.
- **Prestige laundering.** Treating a well-known employer as a qualification.
- **Gap narration.** Inventing a reason for a break in dates. Never.
- **Protected-class inference** from a name, a photo, a school, or a graduation
  year. This is a stop condition, not a style note.
- **Template detectable at a glance.** Fails the paste-to-another-candidate test.

## Escalation

Stop and hand to a human when:

- The candidate's public material mentions a layoff, visa status, health, or
  caregiving. None of it goes in a message.
- The candidate appears to be a current colleague, a client's employee, or under
  a known non-solicit.
- The evidence supports the hook only by inference rather than by statement.
- The role's compensation is unknown *and* the requisition is not confirmed open.

## Examples

Input: `role=Staff Platform Engineer, on-call ownership sits with the team that
writes the service`, evidence = a conference talk abstract about deleting a
service mesh.

Correct output excerpt:

```
Hook: the talk "We deleted our service mesh" — the role's on-call model is the
same argument, made structurally.

Evidence table
| Claim in message                        | Source line in candidate_evidence |
| talk on removing a service mesh (2026)  | line 3                            |

Draft message
Your "we deleted our service mesh" talk argued that the team paging at 3am
should own the abstraction. This role is that, structurally: on-call sits with
the team that writes the service, and the platform group has no separate
pager. The posted range is $210–240k. Worth twenty minutes to see whether the
org chart matches the claim?

Checks: 3 claims, 3 evidence rows; no motivation language; comp stated;
paste-test fails for any other candidate. PASS
```

Correct output when the evidence is a title and an employer only:

```
insufficient evidence to contact — the record contains no fact specific enough
to justify a message. Find a talk, a repo, a post, or do not send.
```

## Regression fixtures

`fixtures/` asserts the refusal path is present in the composed procedure and
that this skill never routes to a provider that would put candidate material on
a third-party endpoint when the private route is requested.
