---
name: narrative-decision-audit
version: 1
purpose: Turn a completed diagnosis into the artifact a buyer reads and decides from — preserve, eliminate, reposition, or test — with the evidence behind every line.
task_class: draft.artifact
stage: sales-artifact
mechanisms:
  - positioning
investment_tier: audit
channel: null
project: null
outputs: report
dry_run_default: true
sends: false
min_quality: 3
output_checks:
  - check: require_sections
    sections: What the evidence supports|What it does not|Recommendations|Evidence|What this audit cannot tell you
  - check: citations_resolve
    section: Evidence
    sources: diagnosis
  - check: forbid_other_mechanisms
    allow: positioning
  - check: forbid_perception_language
  - check: forbid_manufactured_evidence
  - check: forbid_hype
  - check: forbid_flattery
  - check: forbid_email_address
inputs:
  - name: subject
    type: string
    required: true
    description: Who the audit is about.
  - name: diagnosis
    type: string
    required: true
    description: The output of narrative-diagnosis, verbatim. Every claim in the audit must trace to it.
  - name: buyer_role
    type: string
    required: false
    description: Who will read this and can act on it. "Unknown" is a valid answer and changes the recommendations.
  - name: price
    type: string
    required: false
    description: What this audit costs, if it is being sold. Omit for an unpaid one.
---

# narrative-decision-audit

## Purpose

The SALES-ARTIFACT stage, and the only executor of the `positioning` mechanism.

Patrick's positioning note names this as the cash engine's repeatable offer:
ingest the material, identify the story being told, separate supported claims
from aspirations and contradictions, surface the hidden problem, recommend what
to preserve, eliminate, reposition, or test, and show the evidence behind every
conclusion.

The diagnosis already did the separating. This turns it into something a buyer
can act on, and it is the first artifact in the pipeline that may recommend
action — because mechanism selection has, by this point, already chosen
`positioning`. Recommending a *website rebuild* here would be selecting a
different mechanism after the fact, and is out of scope by construction.

## Inputs

- `subject`: {{ subject }}
- `diagnosis`: verbatim output of `narrative-diagnosis`.
- `buyer_role`: {{ buyer_role }}
- `price`: {{ price }}

## Prerequisites

- A completed diagnosis exists. This skill does not diagnose; running it on raw
  material would collapse two stages and lose the evidence trail.
- Mechanism selection returned `positioning`. If it returned `none`, there is no
  audit to sell yet — that is a finding, not a blocker to route around.
- Every recommendation must trace to a line of `diagnosis`. Nothing new enters
  here; this stage repackages, it does not discover.

## Procedure

1. **State the story currently being told**, in one paragraph, in the subject's
   own framing. Not a critique — a fair restatement. A buyer who does not
   recognise their own story stops reading.
2. **What the evidence supports.** The claims the diagnosis marked `supported`,
   with their evidence. This section comes first because an audit that opens with
   failures reads as an attack and gets dismissed.
3. **What it does not.** The `unsupported` and `contradicted` claims, separated —
   they are different problems. Unsupported means unproven; contradicted means
   the subject's own material argues against it.
4. **The hidden problem**, in one sentence, carried from the diagnosis.
5. **Recommendations**, each labelled exactly one of:
   - `preserve` — supported, working, do not touch.
   - `eliminate` — contradicted or indefensible; stop saying it.
   - `reposition` — true but claimed at the wrong altitude or to the wrong buyer.
   - `test` — plausible, unproven, and cheap to check. Name the test.
   Each carries the evidence line it rests on. A recommendation with no evidence
   line is an opinion.
6. **What this audit cannot tell you.** The questions the material could not
   settle, and what would settle each. This section is not a disclaimer; it is
   the honest boundary of the work, and it is what separates this from a pitch.
7. If `price` is given, state it once, plainly, at the end.

## Outputs

A report with: `The story being told`, `What the evidence supports`,
`What it does not`, `The hidden problem`, `Recommendations`, `Evidence`,
`What this audit cannot tell you`.

`Evidence` is a table mapping each recommendation to the line of `diagnosis` it
rests on.

## Quality checks

- Every recommendation carries exactly one of the four labels.
- Every recommendation has an evidence row that resolves against `diagnosis`.
- Nothing appears that is not derivable from `diagnosis`.
- No recommendation proposes a non-positioning intervention — no rebuild, no
  campaign, no automation. Mechanism selection already ran.
- No sentence asserts what a customer or visitor perceives.
- `What this audit cannot tell you` is present and non-empty. An audit with no
  stated limits is a pitch.
- No flattery, no hype register.

## Failure modes

- **The pitch in audit clothing.** Findings shaped to make the next engagement
  obvious. The tell is a `What this audit cannot tell you` section that is thin
  or absent.
- **Recommending outside the mechanism.** "You also need a new site" is mechanism
  selection happening again, later, without the gate.
- **New claims entering at this stage.** Anything not in `diagnosis` arrived
  without an evidence trail, and the audit is the artifact the buyer trusts.
- **Every claim eliminated.** An audit where nothing is preserved is usually a
  failure of reading, not a business with nothing true about it.
- **Recommendation without a test.** `test` that does not name the test is
  `unsupported` wearing a verb.

## Escalation

Stop and hand to a human when:

- The diagnosis contains regulated claims — medical, financial, legal, safety.
- A recommendation would require the subject to retract something publicly.
- `buyer_role` is unknown. An audit with no identified reader cannot be
  scoped, and strategy rule ST-001 says an opportunity with no buyer is not one.
- Every claim classifies `eliminate`.

## Examples

Input: the narrative-sourcing diagnosis, `buyer_role=the founder`.

Correct output excerpt:

```
Recommendations
| # | Label      | Recommendation                                        |
| 1 | preserve   | Keep the published ablation, including the null result |
| 2 | eliminate  | Stop asserting "AI outreach doesn't work anymore"      |
| 3 | test       | Whether a brief changes a recruiter's decision: give 5 |
|   |            | recruiters the same candidate with and without a brief |

Evidence
| # | Rests on (line of diagnosis)                                     |
| 1 | "smaller than I expected and not statistically significant" — supported |
| 2 | "AI outreach doesn't work anymore" — unsupported, none in material |

What this audit cannot tell you
- Whether anyone wants the tool. No adoption record exists in the material.
- Whether the method generalises beyond the one ablation.
```

## Regression fixtures

`fixtures/` asserts the audit routes to a strong model and carries the
positioning-only constraint; `fixtures/behavioral/` asserts that an audit which
recommends a rebuild is blocked, and that a missing limits section is caught.
