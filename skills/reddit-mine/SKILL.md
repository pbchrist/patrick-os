---
name: reddit-mine
version: 1
purpose: Turn a subreddit window into dated, quoted evidence of a specific pain, with the unsupported readings named as unsupported.
task_class: research.mine
channel: reddit
outputs: report
dry_run_default: true
stage: signal
mechanism_agnostic: true
investment_tier: note
sends: false
inputs:
  - name: subreddit
    type: string
    required: true
    description: Subreddit name without the r/ prefix, e.g. recruiting.
  - name: pain_hypothesis
    type: string
    required: true
    description: The specific pain being tested for. "Recruiters distrust AI-written outreach" — not "recruiting problems".
  - name: window_days
    type: integer
    required: false
    default: 14
    description: How far back to read. Older threads need a dated caveat.
  - name: retrieval_backend
    type: string
    required: false
    default: manual-export
    description: How the threads are obtained, from config/retrieval.json. The skill's logic does not change with the backend; only where the text comes from does.
  - name: retrieved_material
    type: string
    required: false
    default: ""
    description: Source bundle injected by Patrick OS retrieval, or pasted/exported source material for manual-export.
  - name: min_quotes
    type: integer
    required: false
    default: 5
    description: Below this, the run reports insufficient evidence rather than padding.
output_checks:
  - check: require_sections
    sections: Hypothesis|Supports|Contradicts|Adjacent|Verdict
  - check: verdict_in_vocabulary
    label: Verdict
    allowed: supported|contradicted|mixed|insufficient evidence
  - check: quotes_are_sourced
    sections: Supports|Contradicts|Adjacent
  - check: counts_are_numeric
  - check: forbid_perception_language
  - check: forbid_hype
---

# reddit-mine

## Purpose

A subreddit is fragments. This produces the evidence half of FRAGMENTS -> HIDDEN
PATTERN -> EVIDENCE TEST, and stops there deliberately. It does not diagnose, it
does not decide, and it does not write outreach.

A good result is a report a skeptic can audit: every claim traceable to a dated
permalink, and an explicit list of the readings the evidence does *not* support.

## Inputs

- `subreddit`: r/{{ subreddit }}, read-only.
- `pain_hypothesis`: {{ pain_hypothesis }}. A hypothesis narrow enough to be
  wrong. If it cannot be falsified by what people wrote, it is not a hypothesis.
- `window_days`: {{ window_days }} days back from today.
- `min_quotes`: {{ min_quotes }}.

## Prerequisites

- A working retrieval backend. **This skill does not assume it can read Reddit
  directly**, and direct agent browsing is currently `blocked`: verified twice on
  real runs, Reddit serves a "Prove your humanity" challenge to logged-out
  programmatic reads. See `config/retrieval.json`.
- That is a retrieval-layer failure and nothing else. No model, provider, or
  routing change addresses it, and swapping any of them would not have moved it.
  The backend is `{{ retrieval_backend }}`.
- Public reading only, whichever backend is used. No scraping around a block,
  no account impersonation, rate limits respected.
- The hypothesis is written down *before* reading. A hypothesis formed after
  reading is a summary wearing a hypothesis costume.

## Procedure

1. Restate `pain_hypothesis` as a claim that could be shown false, and write down
   what evidence would falsify it. Both go in the report header.
2. Analyze the source bundle supplied in `retrieved_material`. Patrick OS obtains
   it through the declared `{{ retrieval_backend }}` before the worker runs. For
   `manual-export`, the bundle is pasted/exported material supplied by the human.
   Do not browse Reddit yourself and do not attempt a different backend.
   **If `retrieved_material` is empty or reports a retrieval failure** — anti-bot challenge, rate limit, no retrieval tool
   available to you, any reason — stop here and emit the declared report format
   with every section present, `Author count: 0`, and
   `Verdict: insufficient evidence`, naming the retrieval failure verbatim under
   Supports. Do not emit prose about what you attempted, and do not reconstruct a
   single quote from memory. A retrieval failure is a fact about the retrieval,
   and the report still has to be a report (G-009).
3. For every comment that bears on the hypothesis, capture verbatim text, author
   handle, permalink, and date. Never paraphrase at capture time.
4. Sort into three buckets, and keep all three in the output:
   - **Supports** — the commenter describes the pain, unprompted.
   - **Contradicts** — the commenter describes the opposite, or describes the
     pain as already solved.
   - **Adjacent** — related, but does not bear on this hypothesis. Adjacent
     evidence is the most common way a mining report talks itself into a
     conclusion; keeping the bucket visible is what stops that.
5. Count. If Supports has fewer than {{ min_quotes }} distinct authors, the
   verdict is `insufficient evidence` and step 6 is skipped.
6. Name the pattern in one sentence, and immediately below it list every reading
   the evidence would also permit.
7. State the next evidence that would settle it.

## Outputs

A Markdown report, written to the run directory, with these sections in order:
Hypothesis, Falsifier, Supports, Contradicts, Adjacent, Author count, Verdict,
Competing readings, Next evidence.

Verdict is exactly one of: `supported`, `contradicted`, `mixed`,
`insufficient evidence`. A run that could not read the subreddit is
`insufficient evidence` in the normal format — not a status message, not an
apology, and not a summary of the attempt.

## Quality checks

- Every quote has a permalink and a date. No exceptions.
- Distinct-author count is stated as a number, not as "several" or "many".
- The Contradicts section is present even when empty, and says "none found in
  window" rather than being omitted.
- The report contains no sentence about what a reader "feels", "assumes", or
  "would think" — those are unmeasured claims about people nobody surveyed.
- No product, tool, or service of Patrick's is named anywhere in the report.

## Failure modes

- **Adjacent evidence promoted to support.** The single most likely failure. A
  thread about recruiting frustration in general is not evidence for a specific
  hypothesis about AI outreach.
- **One loud thread mistaken for a pattern.** Five quotes from one 40-comment
  thread is one data point, not five. Count distinct authors, not quotes.
- **Selection by search term.** Searching for the phrasing in the hypothesis
  finds the hypothesis. Read threads, then filter.
- **Stale window presented as current.** A 2024 thread quoted without its date
  reads as current sentiment. An archive backend lagging the requested window
  silently changes what is being measured; state the backend in the report.
- **Blaming the model for a retrieval failure.** Observed twice. Reddit blocking
  a logged-out read says nothing about the model, the provider, or the routing,
  and reaching for a different model in response is a category error.
- **Drift into diagnosis.** The moment the report proposes what to build, it has
  left its job and become an argument.

## Escalation

Stop and hand to a human when:

- Supports and Contradicts are both non-trivial — that is a real finding, and the
  synthesis is a human's call.
- The strongest evidence sits in a thread about an identifiable individual's
  employment situation.
- The hypothesis turns out to be unfalsifiable as written.

## Examples

Input: `subreddit=recruiting`, `pain_hypothesis=Recruiters can tell AI-written
outreach and it lowers reply rates`, `window_days=14`.

Excerpt of a correct output:

```
Verdict: mixed (9 distinct authors support, 4 contradict)

Supports
- "I can spot the ChatGPT em-dash cadence in two seconds and I archive it"
  — u/example, 2026-08-24, https://reddit.com/r/recruiting/comments/...

Contradicts
- "honestly half my best candidates came from templated sequences, nobody cares"
  — u/example2, 2026-08-27, https://reddit.com/r/recruiting/comments/...

Competing readings
- Recruiters dislike *bad* outreach and attribute it to AI after the fact.
- Reply rates fell for reasons unrelated to authorship (volume, market).
```

## Regression fixtures

`fixtures/` asserts that the composed work order carries the evidence-discipline
rules and that mining stays on a free provider.
