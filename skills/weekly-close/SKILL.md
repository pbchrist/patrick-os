---
name: weekly-close
version: 1
purpose: Close the week honestly — what moved, what is now inactive, what is still unvalidated, and what a result changed — without letting effort read as progress.
task_class: diagnosis.review
channel: null
project: null
outputs: report
dry_run_default: true
sends: false
min_quality: 3
output_checks:
  - check: require_sections
    sections: Moved|Inactive|Unvalidated|Results this week|Lessons proposed|Nothing changed
  - check: counts_are_numeric
  - check: forbid_hype
  - check: forbid_perception_language
  - check: forbid_intervention_proposal
inputs:
  - name: projects
    type: string
    required: true
    description: The project truth records, verbatim. Their stage and next irreversible action are what get tested.
  - name: results
    type: string
    required: false
    description: Results recorded this week, from `patrick result list`. Empty is the common and honest case.
  - name: feedback
    type: string
    required: false
    description: Feedback entries recorded this week, from `patrick feedback list`.
  - name: week_ending
    type: string
    required: true
    description: The date this week closes, ISO format.
---

# weekly-close

## Purpose

The LEARNING stage. A week produces activity; this asks what the activity
changed, and refuses the two substitutions that make a review worthless:
**effort reported as progress**, and **a project called ongoing because someone
touched it**.

Patrick's own operating note supplies the vocabulary and the discipline: *no
evidence means unvalidated, not bad; no next action means inactive, not
ongoing.* This skill applies both, by force, to every project every week.

## Inputs

- `projects`: the truth records, verbatim.
- `results`: {{ results }}
- `feedback`: {{ feedback }}
- `week_ending`: {{ week_ending }}

## Prerequisites

- The truth records are current. A review of stale records reviews the records.
- `results` is what was recorded, not what is remembered. An outcome nobody
  wrote down did not happen for the purposes of this review.

## Procedure

1. For each project in `projects`, state its stage and its next irreversible
   action, quoted from the record.
2. **Moved** — projects where the next irreversible action changed, or a
   recorded result arrived. Cite the specific change. Work done that did not
   change either is not movement, and belongs in `Nothing changed`.
3. **Inactive** — every project whose record names no next action. Use the word
   inactive. Not paused, not simmering, not ongoing.
4. **Unvalidated** — every project with no evidence that anyone wants it. Use the
   word unvalidated. Not failing, not early, not promising.
5. **Results this week** — from `results` only. If empty, say `no results
   recorded this week` and say what that means: nothing was sent, or nothing came
   back. Both are findings.
6. **Lessons proposed** — where a result or a repeated correction suggests a rule,
   name the rule and the command that would record it. Propose; never assert that
   it has been applied.
7. **Nothing changed** — every project that saw activity but no change in stage,
   next action, or evidence. This section existing is the point of the review.
8. State counts as numbers throughout.

## Outputs

A report with: `Moved`, `Inactive`, `Unvalidated`, `Results this week`,
`Lessons proposed`, `Nothing changed`.

## Quality checks

- Every project in `projects` appears in exactly one of Moved, Inactive, or
  Nothing changed.
- Counts are numbers, never "several" or "a few".
- A project with no next action is labelled `inactive`, in those words.
- A project with no demand evidence is labelled `unvalidated`, in those words.
- `Nothing changed` is present. If it is empty on a real week, that claim needs
  to be defended, not assumed.
- No intervention is proposed. This is a review, and choosing what to do next is
  a different stage with its own gate.
- No project is described as promising, exciting, or close.

## Failure modes

- **Effort as progress.** "Made significant headway on X" with no change to the
  next irreversible action. The most common way a weekly review becomes a
  morale exercise.
- **Ongoing as a hiding place.** A project with no next action described as
  in-progress. The whole vocabulary exists to make that impossible to write.
- **Silent omission.** Dropping a project from the review because there is
  nothing good to say. Every project appears every week.
- **Retroactive optimism about a null result.** A published null result is a
  result. Recording it as "inconclusive, needs more data" is how it stops
  counting.
- **Proposing the fix.** A review that ends in a plan has skipped diagnosis and
  mechanism selection.

## Escalation

Stop and hand to a human when:

- A project has been in `Nothing changed` for three consecutive weeks. That is a
  decision about the project, not a line in a report.
- The truth records and the results log disagree about what happened.
- Every project lands in `Inactive`.

## Examples

Input: two projects, one with a next action and no evidence, one with neither.

Correct output excerpt:

```
Moved
- 0 projects moved this week.

Inactive
- site-factory: inactive. The record names no next irreversible action beyond
  "clear Gate 1", which was also last week's.

Unvalidated
- narrative-sourcing: unvalidated. 0 adoption records, 0 payment records.
- site-factory: unvalidated. 0 buyers identified across 5 benchmark businesses.

Results this week
- no results recorded this week. Nothing was sent, so nothing came back.

Lessons proposed
- None. 0 results and 1 correction is not a pattern.

Nothing changed
- narrative-sourcing: the ablation was published before this week; the next
  irreversible action is unchanged from last week.
```

## Regression fixtures

`fixtures/` asserts the vocabulary reaches the work order;
`fixtures/behavioral/` asserts that effort-as-progress and the word "ongoing"
are caught.
