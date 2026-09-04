---
name: mechanism-selection
version: 1
purpose: Extract a structured profile from a diagnosis so the deterministic selector can choose the intervention — or conclude that none is supported.
task_class: mechanism-selection
domain: commercial
stage: mechanism-selection
mechanism_agnostic: true
investment_tier: note
channel: null
project: null
outputs: report
dry_run_default: true
sends: false
min_quality: 3
output_checks:
  - check: require_sections
    sections: Profile|Field notes|Uncertain
  - check: forbid_intervention_proposal
  - check: forbid_perception_language
  - check: forbid_hype
inputs:
  - name: diagnosis
    type: string
    required: true
    description: The output of narrative-diagnosis, verbatim.
  - name: buyer_evidence
    type: string
    required: false
    description: What establishes that a person exists who can buy and decide. Absent means buyer_identified is false.
  - name: current_tier
    type: string
    required: false
    default: note
    description: The investment tier already reached. note, audit, pilot, or build.
---

# mechanism-selection

## Purpose

This skill does **not** choose the mechanism. It extracts a structured profile
from the diagnosis, and `patrick_os/selection.py` — a pure function over the
precondition table in `config/mechanisms.json` — makes the choice.

That split is the entire design. A model asked to choose an intervention will
choose one it knows how to execute; that is how "find a bad website" became
"build a better website", and how a Cloudflare challenge became a qualified
rebuild at score 90. So the model's job here is narrow and checkable: read the
diagnosis, report what is in it, and flag what it could not determine.

Extraction is a reading task. Selection is a policy decision, and policy belongs
in a table a human can read and a test can pin.

## Inputs

- `diagnosis`: verbatim output of `narrative-diagnosis`.
- `buyer_evidence`: {{ buyer_evidence }}
- `current_tier`: {{ current_tier }}

## Prerequisites

- A completed diagnosis. Selecting from raw material would mean selecting from
  an interpretation nobody checked.
- The mechanism registry is the authority on what may be selected. Do not
  propose an intervention that is not a declared mechanism.

## Procedure

1. Read `diagnosis` and fill in each profile field below. Report only what the
   diagnosis states. Where it does not say, use the conservative default and
   record the field under `Uncertain` — a guess here silently changes the
   decision, because these values feed a deterministic gate.

   - `retrieval_ok` — did the material actually get retrieved? Any retrieval
     failure makes this `false`.
   - `identity_confidence` — `none`, `low`, `medium`, or `high`. If the
     diagnosis does not establish identity, it is `none`.
   - `buyer_identified` — `true` only if `buyer_evidence` names a person or role
     who can decide. "The company exists" is not buyer evidence.
   - `supported_claims`, `unsupported_claims`, `contradicted_claims` — counts.
   - `observations` — a list of `{domain, severity}`. Domain is one of
     `website`, `messaging`, `pricing`, `operations`, `positioning`.
   - `measured_result_available` — is there a measured outcome **from the current
     tier of this opportunity**? Not "a measurement exists somewhere", not "they
     published a study", not "we did the work". A published ablation about the
     method is not a measured result from a note-tier engagement with this buyer.
     This field advances the investment tier, so a generous reading of it spends
     money the evidence has not earned (ST-002). Default `false`.
   - `regulated_claims` — does the material make medical, financial, legal, or
     safety claims?

2. Emit the profile as a JSON object under `## Profile`.
3. Under `## Field notes`, give the line of the diagnosis each non-default value
   came from.
4. Under `## Uncertain`, list every field you could not determine and the
   conservative default you used. An empty list is suspicious on a real
   diagnosis; say so if the diagnosis genuinely settled everything.
5. Stop. Do not name a mechanism, do not rank mechanisms, and do not recommend
   an action. Run `patrick select --profile <file>` to get the decision.

## Outputs

A report with `## Profile` (a JSON object), `## Field notes`, and `## Uncertain`.

The selection itself comes from `patrick select`, which reads the profile and
prints the chosen mechanism, the eligible set, the capability gap, and every
rejection with its reason.

## Quality checks

- `## Profile` contains valid JSON with only declared profile fields.
- Every non-default value has a field note citing the diagnosis.
- No mechanism is named as a recommendation anywhere in the output.
- No intervention is proposed.
- Conservative defaults are used for anything the diagnosis did not establish,
  and each appears under `Uncertain`.

## Failure modes

- **Choosing anyway.** Naming a mechanism in the notes, or ordering the profile
  fields to imply one. The selector is the decider; this output is evidence.
- **Optimistic defaults.** Setting `buyer_identified` true because a company
  exists, or `identity_confidence` high because the name matched once. Each
  optimistic default flips a gate that exists to catch exactly that.
- **Borrowed measurement.** Observed on a real run: `measured_result_available`
  was set true because the subject had published an ablation. That is a
  measurement about the method, not a result from this engagement at this tier,
  and it advanced the tier from `note` to `audit` on evidence that had nothing to
  do with the opportunity. The question is always "what did *this* tier of *this*
  opportunity produce".
- **Inventing observations** to reach a domain threshold. A domain count is a
  gate; padding it is defeating the gate.
- **Empty `Uncertain`** on a diagnosis that plainly left things open.
- **Treating `none` as failure.** `none` is the correct answer for most
  prospects most of the time.

## Escalation

Stop and hand to a human when:

- `regulated_claims` is true.
- The diagnosis and `buyer_evidence` disagree about who the buyer is.
- Every profile field lands on its conservative default — that says the
  diagnosis was too thin to select from, which is a finding about the diagnosis.

## Examples

Input: a diagnosis where retrieval failed.

Correct output:

```
## Profile
{"retrieval_ok": false, "identity_confidence": "none", "buyer_identified": false,
 "supported_claims": 0, "unsupported_claims": 0, "contradicted_claims": 0,
 "observations": [], "measured_result_available": false, "current_tier": "note",
 "regulated_claims": false}

## Field notes
- retrieval_ok: "retrieval_failed: cloudflare-challenge" — the diagnosis records
  that nothing was retrieved.

## Uncertain
- identity_confidence: nothing was retrieved, so identity could not be assessed;
  used the conservative default `none`.
- All claim counts: no claims could be read.
```

`patrick select` on that profile returns `none`, with `website` rejected for
`retrieval_ok=False`. That is SF-03 refusing to happen.

## Regression fixtures

`fixtures/` asserts the extraction-only framing survives composition;
`fixtures/behavioral/` asserts that an output naming a mechanism is blocked.
