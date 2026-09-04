# Architecture

## Patrick OS is an operating layer

Patrick OS makes Patrick's AI work smarter, more consistent, more reusable and
more coordinated across projects. It holds six things centrally: persistent
context and decision memory, reusable skills, model and tool routing,
independent judgment and QA, feedback-driven learning from corrections and
accepted outputs, and orchestration across distinct projects and agents.

**It is not a lead-generation system.** Site Factory, the Opportunity Engine,
recruiting, writing, research and fiction are consumers that run on top of it.

### The layering

```
    consumers      site-factory   opportunity-engine   (fiction, research, ...)
                          \             /
    domain packs        patrick_os/domains/commercial
                                 |
    operating layer     skills · voice · routing · judging · feedback ·
                        retrieval · decisions · orchestration
```

Core knows about skills, voice, routing, judging, feedback, retrieval and
orchestration — concerns identical whether the work is recruiting, fiction or
selling. It knows nothing about any of those subjects.

### The leak this corrects

`stage` was a required field on **every** skill, drawn from a commercial
pipeline. A fiction skill could not validate: it was made to name a position in a
sales workflow and declare which sales intervention it served. Mechanism
selection, investment tiers and sales outcomes sat beside the router as though
they were operating-system concerns. One consumer's vocabulary had become the
operating system's.

Four tests hold the boundary now: core imports no pack at load, no core module
imports a pack at module level, no commercial check sits in the core registry,
and every domain-less skill validates clean.

# The commercial domain: pipeline and mechanisms

*Everything below this line describes ONE domain pack, not Patrick OS.*

**Status:** the shape is declared and enforced. The engine is not built, on
purpose. See `decisions/0006`.

## The correction this document records

Site Factory was operating one abstraction too low. Its implicit model was:

```
find a bad website  ->  build a better website
```

Which means the tooling that happened to exist chose the intervention. That is
backwards, and it is the direct cause of Site Factory finding SF-03: a Cloudflare
challenge became a qualified website-rebuild opportunity at score 90, because a
website rebuild was the only thing the system could conclude.

The durable model:

```
signals -> qualification -> diagnosis -> mechanism selection
        -> sales artifact -> outreach -> result -> learning
```

**Site Factory is an executor for web-based interventions. It is not the
top-level decision engine.** Mechanism selection sits above it and may conclude
that no web intervention is warranted, or that a non-web mechanism is.

## Three axes, deliberately not collapsed

Patrick OS tracks three orthogonal things. Conflating any two is how a system
ends up believing "commercial work" means "the thing Site Factory does".

| Axis | Question | Declared in | Consumed by |
|---|---|---|---|
| `task_class` | Which *model* should do this? | `SKILL.md`, resolved via `config/routes.json` | the router |
| `stage` | Where in the *pipeline* does this sit? | `SKILL.md` | `patrick pipeline`, future orchestration |
| `mechanism` | What *intervention* is being sold or delivered? | `SKILL.md` + `config/mechanisms.json` | mechanism selection (unbuilt) |
| `investment_tier` | How much has been *committed*? | `SKILL.md` | tier gating (unbuilt) |

A qualification step and an outreach step can share a task class and belong to
different stages. A website rebuild and a pricing change can share a stage and be
different mechanisms. The axes move independently.

## Stages

| Stage | Produces | Covered by |
|---|---|---|
| `signal` | Dated, sourced evidence. No claim. | `reddit-mine` |
| `qualification` | pursue / watch / suppress, and *who would buy* | `site-factory-prospect` |
| `diagnosis` | What is actually wrong beneath the presented story | `narrative-diagnosis` |
| `mechanism-selection` | Which intervention the diagnosis implies, or `none` | `mechanism-selection` + `patrick select` |
| `sales-artifact` | The thing a buyer sees: audit, one-pager, demo | `narrative-decision-audit` |
| `outreach` | Getting it in front of the decider | `linkedin-reply`, `recruiter-outreach`, `site-factory-email` |
| `result` | What happened. Recorded whether or not it flatters. | `patrick result record` — tooling, not a skill |
| `learning` | What the result changes | `weekly-close` + the feedback compiler |

`patrick pipeline` prints this live.

`result` is served by tooling rather than a skill on purpose: recording what
happened is data intake, and a model should never be the thing that decides what
an outcome was. Showing it as an empty stage would be a false gap; putting a
skill there would be a false claim.

**Every stage being covered is not the same as every stage being good.**
`patrick result list` is empty — nothing has been sent, so nothing has come back —
which means no mechanism has a measured outcome behind it and `strategy/` is
still written by hand.

## Mechanism selection: the model extracts, the code decides

The stage whose absence let the executor make the decision, and the one place
where the split matters most.

`mechanism-selection` (the skill) reads a diagnosis and emits a structured
profile: `retrieval_ok`, `identity_confidence`, `buyer_identified`, claim counts,
observations by domain, `measured_result_available`. It is explicitly forbidden
from naming a mechanism.

`patrick_os/selection.py` then decides, as a pure function over the
`preconditions` table in `config/mechanisms.json` — no model, no network, no
keys, fully regression-tested. Same shape as `router.resolve`, for the same
reason: a decision you can only observe by running a model is a decision you
cannot pin.

The reason for the split is not tidiness. **A model asked to choose an
intervention will choose one it knows how to execute.** That is how "find a bad
website" became "build a better website", and how a Cloudflare challenge became a
qualified rebuild at score 90. Preconditions encode SF-03 and SF-05 as data:
`website` requires `retrieval_ok` and `identity_confidence in [medium, high]`.

Three outcomes, kept separate because they mean different things:

- **eligible** — the evidence supports it and something here can execute it.
- **capability gap** — the evidence supports it and *nothing here can do it*.
  A strategic finding, not a rejection. Folding it into "rejected" would bury
  the most useful thing selection produces.
- **rejected** — the evidence does not support it, with the failing clause named.

`none` is always eligible and always last. A selector that cannot conclude "no
intervention is warranted" is not selecting; it is justifying the tool it has.

## Mechanisms

Declared in `config/mechanisms.json`, so adding a non-website intervention is a
config edit, never a code change. Each declares its executors, the evidence it
requires, and which investment tiers it supports.

Currently: `website` (executor: site-factory, status blocked), `positioning`,
`messaging`, `pricing`, `ops-automation`, and `none`.

`none` is load-bearing. Mechanism selection that cannot conclude "no intervention
is supported yet" is not selection.

`positioning` is the one to notice: per Patrick's own positioning note, the
Narrative Decision Audit is the cash engine's repeatable offer, and it is **not a
web intervention**. Nothing currently executes it. A website-shaped architecture
would never have surfaced that gap.

## Progressive investment

`note` → `audit` → `pilot` → `build`, cheapest first. Strategy rule `ST-002`:
do not advance a tier without a measured result from the tier below it. Site
Factory reached automated outbound with zero validated demand, which is the
failure this ordering exists to prevent.

## Feedback has three layers

| Layer | Lesson about | Revised by | Promotes into |
|---|---|---|---|
| `output` | How the writing reads | Edits to drafts | `voice/` |
| `workflow` | What the procedure does | Observed process failure | **nothing** — a human edits the skill and commits |
| `strategy` | What is worth pursuing | *Results*: money, replies, silence | `strategy/` |

Strategy is not output feedback with a wider scope; it answers a different
question and is revised on different evidence. `strategy/` uses its own scope
vocabulary — `mechanism:`, `segment:`, `project:`, `global` — and the two
namespaces reject each other's scopes.

Strategy feedback requires `--evidence` and is refused without it. This is
stricter than voice, deliberately: a wrong voice rule produces an awkward
sentence; a wrong strategy rule sends Patrick after the wrong buyers for a
quarter.

Workflow promotion is refused outright. Patrick OS rewrites rules, not
procedures.

## Checks that resolve against the source, not just the output

Most checks inspect the output in isolation. `citations_resolve` does not: it is
given the run's inputs and resolves every cited evidence span against the source
material.

It exists because of a specific failure. Running `narrative-diagnosis` on real
material produced an output citing `README states [...] No scraping, no batch
mode, no auto-send` as the evidence for a claim. That text appears nowhere in the
supplied `evidence_material`. **The deterministic layer passed it and the
independent model judge passed it.** A fabricated citation is the most damaging
defect available in an evidence-grounded system, because it produces exactly the
feeling of rigour that makes an unsupported reading persuasive.

Two lessons, and they generalise past this one check:

1. **A check that only reads the output cannot catch a claim about the input.**
   `checks.run(text, declared, context)` takes the run's inputs, and
   `patrick judge` loads them from `run.json` automatically — asking the operator
   to pass them again would make the check that matters most the one most often
   skipped.
2. **A control with a keyword-shaped hole is a decorative control.** The first
   version skipped table rows whose cell began with "evidence", "source" or
   "claim", to avoid re-checking header rows. That meant any fabrication written
   as `Evidence material: "..."` bypassed the check entirely. Header rows are now
   detected structurally, by the separator line that follows them.

Resolution is coverage-based rather than exact-substring: a span resolves when
80% of its words appear as a contiguous run in the source. Exact matching was the
first attempt and flagged a real quote that differed only by a label prefix and a
full stop. A check that pedantic gets switched off, and a switched-off check
catches nothing. Fabricated spans share almost no contiguous run with the source;
a real quote with a label bolted on shares nearly all of it.

## What was built now, and what was not

Built — the minimum that lets the rest arrive later without a rewrite:

- the stage, mechanism, and tier vocabularies, with validation
- `config/mechanisms.json` as a declarative registry with non-web entries
- `stage` / `mechanisms` / `mechanism_agnostic` / `investment_tier` on skills,
  **required** — a skill that will not say where it sits fails validation
- `strategy/` as a first-class rule namespace with its own scopes
- the `strategy` feedback layer, end to end through promotion
- `patrick pipeline`, so the coverage gap is visible rather than implied

Deliberately not built:

- opportunity discovery and ingestion — nothing finds prospects
- the opportunity record: stages are run by hand, output piped to input
- cross-stage orchestration — nothing chains stage outputs to stage inputs
- any executor for `messaging`, `pricing`, or `ops-automation`
- bulk corpus intake for `voice/`

## Interfaces that will need to exist

Recorded now so today's schemas do not have to be broken later.

**Opportunity record** — the object that travels the pipeline. Does not exist
yet. It will need: a stable id; the signals it came from, each dated and sourced;
qualification verdict and the buyer evidence behind it; the diagnosis; the
selected mechanism and *why that one over the alternatives*; the current
investment tier; and the result. `projects/site-factory.md`'s prospect record is
a stage-2 fragment of this, not the thing itself.

**Stage contract** — each stage should declare what it consumes and emits, so a
stage can only read the output of a stage at or before it. `pipeline.stage_index`
exists for that check; nothing calls it yet.

**Mechanism selector** — built. `patrick_os/selection.py`, pure, table-driven.

**Result intake** — built. `patrick result record` requires evidence and treats
`no_reply` as a first-class outcome, because a results log that only records wins
measures enthusiasm. After three matching results it *prompts* for a strategy
rule and writes none — same discipline as the feedback compiler.

**Tier advancement** — `note → audit → pilot → build`, advanced by
`measured_result_available` in the selector. A real run set that field true on
the strength of the subject's own published ablation, which advanced the tier on
a measurement that had nothing to do with the engagement. The field now specifies
"from the current tier of *this* opportunity", and the case is a fixture.

## What did not change

The Site Factory skills, their gates, and their fixtures are untouched by this
work. Both gates remain NO-GO. The two skills are now labelled as executors of
one mechanism rather than as the commercial workflow, which is a change of
framing enforced by tests — not a change of behaviour.
