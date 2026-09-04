---
name: narrative-diagnosis
version: 1
purpose: Separate what a business's own material claims from what its evidence supports, and name the gap — without proposing any intervention.
task_class: diagnosis
channel: null
project: null
outputs: report
dry_run_default: true
sends: false
min_quality: 3
output_checks:
  - check: require_sections
    sections: Claims|Contradictions|Hidden problem|Cannot be settled|Decision enabled
  - check: citations_resolve
    section: Claims
    sources: evidence_material
  - check: forbid_intervention_proposal
  - check: forbid_perception_language
  - check: forbid_hype
  - check: counts_are_numeric
    section: Hidden problem
inputs:
  - name: subject
    type: string
    required: true
    description: Whose story is being audited. A business, a product, a project.
  - name: claims_material
    type: string
    required: true
    description: What the subject says about itself, verbatim. Website copy, deck, README, profile. Their words, not a summary of them.
  - name: evidence_material
    type: string
    required: false
    description: What can be independently checked — measurements, records, published results, observable facts. Absent is a valid and common state.
  - name: stated_goal
    type: string
    required: false
    description: What the subject says it is trying to achieve, if stated. Used to test whether the claims serve it.
---

# narrative-diagnosis

## Purpose

This is the DIAGNOSIS stage: the middle of the pipeline, and the stage whose
absence let Site Factory's executor make the decision.

It answers one question — *what is really happening underneath the story being
presented?* — and it answers it by separating three things that fluent writing
routinely blends: what is claimed, what is supported, and what is contradicted.

It deliberately stops before saying what to do. That is mechanism selection, a
separate stage, and a diagnosis that arrives carrying its own remedy has already
made the choice.

## Inputs

- `subject`: {{ subject }}
- `claims_material`: their own words, verbatim. A summary has already done the
  interpretation this skill exists to do carefully.
- `evidence_material`: what can be checked. Often empty. That is a finding.
- `stated_goal`: {{ stated_goal }}

## Prerequisites

- `claims_material` is quoted, not paraphrased. Every claim in the output must
  be traceable to a span of it.
- Nothing outside the supplied material may be used as evidence. Not general
  knowledge about the industry, not the reputation of the company, not what
  similar businesses usually do.
- The reader is going to make a decision from this. It is not a critique.

## Procedure

1. **Extract claims.** List every assertion `claims_material` makes about the
   world — capability, outcome, scale, differentiation, demand. Quote each one
   verbatim and number it. Marketing adjectives are not claims; "trusted by
   hundreds of teams" is.
2. **Classify each claim** against `evidence_material` only:
   - `supported` — evidence in the material establishes it. Cite the span.
   - `unsupported` — no evidence either way. This is the default and is not an
     accusation.
   - `contradicted` — evidence in the material tells against it. Cite the span.
   Never mark a claim supported because it is plausible.
3. **Find internal contradictions** — places where two claims cannot both be
   true, or where a claim and the stated goal pull against each other. These are
   the highest-value findings, because the subject cannot dispute the source.
4. **Name the hidden problem** in one sentence: the gap between the story being
   told and what the material can actually support. State how many claims sit in
   each bucket, as numbers.
5. **State what cannot be settled** from this material, and what evidence would
   settle it. Be specific about the artifact: "a signed contract", "a bounce
   rate", "one customer who renewed".
6. **State the decision this enables** — what a reader now knows well enough to
   act on. If the answer is "not enough to decide anything yet", say exactly
   that; it is a legitimate and common diagnosis.
7. **Stop.** Do not propose a rebuild, a rewrite, a campaign, a price change, or
   any other intervention, and do not hint at one. If a remedy seems obvious,
   that is information for the next stage, not this one.

## Outputs

A report with these sections, in order: `Claims`, `Contradictions`,
`Hidden problem`, `Cannot be settled`, `Decision enabled`.

`Claims` is a table: number, verbatim quote, classification, and the evidence
span or `none in material`.

## Quality checks

- Every claim is quoted verbatim from `claims_material`. A paraphrased claim is
  a defect, because the paraphrase is where interpretation smuggles itself in.
- Every `supported` and `contradicted` classification cites a span of
  `evidence_material`. `unsupported` cites nothing, by definition.
- **Every cited span must appear verbatim in `evidence_material`.** Never cite
  `claims_material` as evidence for its own claim — that is circular — and never
  reconstruct a span from memory. A citation the reader cannot find is worse
  than no citation, because it looks like proof. This is checked mechanically.
- No intervention is proposed or implied. No "we can", no "the fix is", no "they
  need a".
- No sentence asserts what a customer, visitor, or reader perceives.
- The hidden problem is one sentence and contains counts as numbers.
- Nothing appears in the output that is not in the supplied material.
- `Cannot be settled` names a specific artifact per item, not "more data".

## Failure modes

- **The seductive reading.** A coherent, satisfying story that the evidence does
  not carry. This is the failure the whole method exists to prevent, and fluency
  is what makes it dangerous — the Site Factory output that shipped an unmeasured
  claim about visitor perception scored 5/5 on evidence fidelity.
- **Proposing the fix.** A stage violation, and the specific one that produced
  SF-03. Caught deterministically by `forbid_intervention_proposal`.
- **Treating absence as contradiction.** No evidence for a claim makes it
  `unsupported`. Only evidence *against* it makes it `contradicted`.
- **Auditing the prose instead of the claims.** Whether the copy is well written
  is not this skill's question.
- **Fabricated citations.** Observed on a real run of this skill: an evidence
  span was cited that appeared nowhere in the supplied material, and both the
  deterministic layer and the independent model judge passed the output. Now
  caught by `citations_resolve`, which resolves every span against the source.
- **Circular support.** Citing the subject's own claim as the evidence for it.
- **Importing outside knowledge.** "Most agencies in this space overstate
  headcount" is not evidence about this subject.
- **Grading rather than diagnosing.** A score is not a diagnosis. No score.

## Escalation

Stop and hand to a human when:

- The material makes a regulated claim — medical outcome, financial return,
  legal guarantee, safety. Naming it as unsupported has consequences beyond this
  report.
- A contradiction implicates a named individual rather than the organisation.
- The subject is a person rather than an organisation, and the diagnosis would
  be about their honesty.
- Every claim classifies `unsupported` and there is no `evidence_material` at
  all. That is a statement about the inputs, not about the subject.

## Examples

Input: `subject=A two-person agency`, claims_material containing "trusted by
hundreds of teams" and "we've been profitable since day one", evidence_material
containing three named client logos and no financials.

Correct output excerpt:

```
Claims
| # | Claim (verbatim)                        | Class       | Evidence span        |
| 1 | "trusted by hundreds of teams"          | contradicted| 3 named clients listed |
| 2 | "we've been profitable since day one"   | unsupported | none in material     |

Contradictions
- Claim 1 says "hundreds of teams"; the only enumeration in the material is
  three named clients. Both cannot be true of the same customer base.

Hidden problem
The material asserts scale it cannot evidence: 1 claim contradicted, 1
unsupported, 0 supported.

Cannot be settled
- Actual customer count: a customer list or an invoice count would settle it.
- Profitability: one filed return or a P&L for any single year.

Decision enabled
Do not repeat the "hundreds of teams" figure anywhere it could be checked. Not
enough here to decide whether the underlying business is sound.
```

## Regression fixtures

`fixtures/` asserts the diagnosis routes to a strong model and never to the cheap
one; `fixtures/behavioral/` asserts that a diagnosis carrying a remedy is blocked
even when everything else about it is correct.
