---
name: site-factory-prospect
version: 1
purpose: Turn one candidate business into a verified-identity, observation-only prospect record, or suppress it — without modifying the Site Factory pipeline.
task_class: research.prospect
channel: null
project: site-factory
outputs: report
dry_run_default: true
domain: commercial
stage: qualification
mechanisms:
  - website
investment_tier: note
sends: false
inputs:
  - name: business_name
    type: string
    required: true
  - name: claimed_url
    type: string
    required: true
    description: The URL believed to be the business's official site. Believed, not verified.
  - name: fetch_status
    type: string
    required: true
    description: What actually happened when the page was fetched — one of ok, timeout, 403, cloudflare-challenge, tls-error, dns-error, other.
  - name: observations
    type: string
    required: false
    description: Verbatim observable facts from the retrieved page. Required when fetch_status is ok.
  - name: identity_signals
    type: string
    required: false
    description: What ties claimed_url to business_name — matched tokens, phone, address, schema.org name.
output_checks:
  - check: forbid_perception_language
  - check: forbid_manufactured_evidence
  - check: forbid_hype
  - check: forbid_email_address
---

# site-factory-prospect

## Purpose

Site Factory's prospecting layer has four verified correctness defects that
convert our own infrastructure failures and weak matches into confident claims
about strangers' businesses. This skill is the human-facing front door that
refuses to do that, and it does it *outside* the pipeline: nothing here edits
`site-factory/`.

## Inputs

- `business_name`: {{ business_name }}
- `claimed_url`: {{ claimed_url }}
- `fetch_status`: {{ fetch_status }}
- `observations`: verbatim, from the retrieved page only.
- `identity_signals`: the specific evidence tying the URL to the name.

## Prerequisites

- Read the site-factory truth record in `projects/site-factory.md` first. Both
  gates are NO-GO; this skill exists to produce a record, not to advance a send.
- `fetch_status` reflects what the fetcher actually reported. Guessing it defeats
  the entire skill.
- No Site Factory file is modified, no branch is pushed, no `SITE_FACTORY_*`
  variable is set.

## Procedure

1. **Fetch gate (SF-03).** If `fetch_status` is anything other than `ok`, emit
   `retrieval_failed` with the literal status and stop. Do not produce findings,
   do not produce an opportunity, and do not write any sentence about the state
   of the business's website. Our crawler failing is a fact about our crawler.
2. **Identity gate (SF-05).** Score `identity_signals`. A single matched name
   token is `confidence: none` regardless of how distinctive it feels —
   "Sunrise", "Ironwood", and "Cedar" each verified against a stranger's page
   under the old rule. Require at least two independent signals (token overlap
   plus phone, address, or schema.org name) for `confidence: medium`, and a
   direct self-identification on the page for `confidence: high`.
3. If confidence is `none`, emit `identity_unverified` and stop.
4. **Observation pass.** From `observations` only, list what is literally on the
   page. Each entry: the observable fact, and where on the page it appears.
5. **Severity.** Assign each observation `low`, `medium`, `high`, or `critical`
   from stated criteria, and write the criterion next to the grade. Note in the
   record that Site Factory's `observable_findings()` stamps every deterministic
   finding `medium` because of a positional-argument slip (SF-02) — so a `medium`
   coming out of that pipeline carries no information, and a severity here must
   not be copied from it.
6. **Buyer question.** State who at this business would buy, and what evidence
   says that person exists. "Unknown" is a valid and common answer (SF-12).
7. Emit the prospect record. Recommend `pursue`, `watch`, or `suppress`, and give
   the one condition that would change the recommendation.

## Outputs

A prospect record with: `Identity` (confidence + signals), `Fetch status`,
`Observations`, `Severity` (with criteria), `Buyer`, `Recommendation`,
`Condition that would change it`. Written to the run directory. Nothing is
written into `hermes-projects`.

## Quality checks

- `fetch_status` appears verbatim in the record.
- No sentence describes the business's website unless `fetch_status` is `ok`.
- Identity confidence is stated before any claim about the business.
- Every observation is something a person could point at on the page.
- No sentence describes what a visitor thinks, feels, or assumes.
- No severity is inherited from a Site Factory pipeline score.
- The record proposes no deliverable that would manufacture evidence.

## Failure modes

- **Infrastructure failure narrated as a finding.** SF-03, verified. The single
  most damaging output this skill can produce.
- **Confident claims about the wrong business.** SF-05, verified. Compounds with
  SF-06 into a detailed, confident, entirely wrong message to a stranger.
- **Severity laundering.** Copying `medium` out of the pipeline and treating it
  as a judgment. It is a default argument value.
- **Buyer assumed from business size.** A 12-person HVAC company having a website
  does not mean someone there buys marketing services.
- **Score citation.** Quoting a Site Factory quality score as evidence. SF-07:
  the judge shares an answer key with the writer.

## Escalation

Stop and hand to a human when:

- `fetch_status` is `ok` but the page contents contradict `business_name`.
- Identity confidence is `medium` and the observations would embarrass someone if
  the match is wrong.
- The observation set includes anything about an identifiable individual —
  a named employee, a reviewer, a personal address.
- Anyone asks for this record to feed a send. Gate 2 is NO-GO.

## Examples

Input: `business_name=Sunrise Dentistry`, `claimed_url=https://sunrisedental.example`,
`fetch_status=cloudflare-challenge`.

Correct output, in full:

```
retrieval_failed: cloudflare-challenge

Our fetcher did not retrieve this page. No finding, no severity, and no
opportunity is produced. Nothing is known about this website from this run.
```

Input: same business, `fetch_status=ok`, identity signals = two matched tokens
plus the phone number from the directory listing.

Correct output excerpt:

```
Identity: medium (2 name tokens + phone match; no schema.org name on page)
Fetch status: ok

Observations
- The review card reading "Dana Reyes" appears three times consecutively in the
  homepage testimonial carousel.
- Two product headings render mojibake ("Iâ€™m") in the services section.

Severity
- Duplicate testimonial — medium. Criterion: visible on the primary landing
  view, not a functional defect. (Not inherited from the pipeline; see SF-02.)

Buyer: unknown. No owner, marketing contact, or agency-of-record is identifiable
from the retrieved page.

Recommendation: watch.
Condition that would change it: an identifiable buyer, or a second independent
identity signal raising confidence to high.
```

## Regression fixtures

`fixtures/` asserts that the retrieval gate and the identity gate reach the work
order, that the truth record's verified defects come with it, and that a private
routing request keeps client material on the local model.
