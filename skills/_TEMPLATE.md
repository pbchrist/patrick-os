---
name: skill-slug
version: 1
purpose: One sentence. What repeated work does this remove?
task_class: research
channel: null
project: null
outputs: report
dry_run_default: true
sends: false
inputs:
  - name: example
    type: string
    required: true
    description: What this input is and where it comes from.
---

# skill-slug

Every section below is required. `patrick test` fails a skill that is missing one,
because a procedure with no failure modes is a procedure nobody has run twice.

Use `{{ input_name }}` anywhere in the body to interpolate a bound input.

## Purpose

Why this exists, and what a good result looks like from the outside.

## Inputs

Each declared input, what a valid value looks like, and where it comes from.

## Prerequisites

What must be true before this runs. Credentials, files, an authenticated session,
a prior skill's output. State it even when it is obvious.

## Procedure

Numbered steps. Concrete enough that a different worker -- a different model, a
different person -- produces a comparable result.

## Outputs

The exact artifact. Format, destination, and who consumes it.

## Quality checks

What must be true of the output before a human sees it. Write these as things
that can be checked, not as aspirations.

## Failure modes

The specific ways this has gone wrong or would go wrong, and what each looks like
from the outside.

## Escalation

The conditions under which this stops and asks a human. Be generous here.

## Examples

At least one worked example: the input, and a short excerpt of the right output.
