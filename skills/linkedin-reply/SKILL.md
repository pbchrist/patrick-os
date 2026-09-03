---
name: linkedin-reply
version: 1
purpose: Draft a short LinkedIn reply that adds one thing the original post did not contain, or decline to reply at all.
task_class: draft.reply
channel: linkedin
outputs: draft
dry_run_default: true
sends: false
min_quality: 3
inputs:
  - name: post_text
    type: string
    required: true
    description: The full text of the post being replied to. Not a summary of it.
  - name: post_author
    type: string
    required: true
    description: Who wrote it, and their relationship to Patrick if any.
  - name: angle
    type: string
    required: false
    description: The one thing to add. Omit it and the skill picks one, then says which and why.
  - name: max_sentences
    type: integer
    required: false
    default: 4
---

# linkedin-reply

## Purpose

Most LinkedIn replies are agreement with extra words. This drafts the version
that is worth the poster's attention, or returns `no reply warranted` — which is
a legitimate, common, and correct output.

## Inputs

- `post_text`: verbatim.
- `post_author`: {{ post_author }}.
- `angle`: the addition. If blank, the draft names the angle it chose.
- `max_sentences`: {{ max_sentences }}.

## Prerequisites

- The full post text, not an excerpt. Replying to an excerpt is how a reply ends
  up arguing with something the poster did not say.
- If the post makes a factual claim Patrick intends to dispute, the counter-source
  must be in hand before drafting.

## Procedure

1. Identify the post's actual claim in one sentence. If the post has no claim,
   output `no reply warranted` and stop.
2. Decide what a reply would add: a number, a counterexample, a mechanism, or a
   named constraint the post ignored. If none of those is available, output
   `no reply warranted` and stop. Agreement is not an addition.
3. Draft at most {{ max_sentences }} sentences.
4. Cut the first sentence if it restates the post. It usually does.
5. Run the quality checks below against the draft, and report any that fail
   rather than silently rewriting until they pass.
6. Emit the draft, the angle chosen, and the one-line reason it is worth posting.

## Outputs

A draft file containing: `Angle`, `Why worth posting`, `Draft`, `Checks`. Nothing
is posted. Patrick copies it or discards it.

## Quality checks

- At most {{ max_sentences }} sentences.
- Does not open with the author's first name, and does not open with "Great post".
- No emoji, no "Thoughts?", no line-broken listicle formatting.
- Any market, salary, or hiring-rate figure names its source in the same sentence.
- Contains at least one thing not present in the original post.
- Does not mention any of Patrick's products unless the post is explicitly about
  that product.

## Failure modes

- **Fluent agreement.** Passes every stylistic check and adds nothing. This is
  the default failure and the reason step 2 can terminate the skill.
- **Borrowed authority.** A confident statistic with no source. On LinkedIn this
  is the most expensive error available, because it is public and permanent.
- **Arguing with a strawman** built from an excerpt.
- **Position drift.** A reply that contradicts something Patrick posted earlier.
  Patrick OS has no memory of his post history, so this cannot be checked here —
  it is an escalation, not a check.

## Escalation

Stop and hand to a human when:

- The post concerns a live client, employer, or an identifiable candidate.
- The reply would correct the author publicly.
- The post is about layoffs, discrimination, or an individual's dismissal.
- The right reply depends on what Patrick has posted before.

## Examples

Input: a post claiming "AI screening removes bias from hiring".

Correct output:

```
Angle: named constraint the post ignored
Why worth posting: the post treats the training data as neutral; that is the
whole question, and it is checkable.

Draft:
A screen trained on past hires reproduces whoever got hired before. The 2018
Amazon resume tool is the cited example — it downgraded resumes containing
"women's" because that is what the history contained. Bias moves from the
interviewer to the training set; it does not leave the system.

Checks: 3 sentences; source named inline; no product mention. PASS
```

Correct output for a post that just says "hiring is hard right now":

```
no reply warranted — the post makes no claim to add to.
```

## Regression fixtures

`fixtures/` asserts that LinkedIn brevity rules and the "no reply warranted"
escape hatch survive into the work order, and that replies do not route to the
cheap local model.
