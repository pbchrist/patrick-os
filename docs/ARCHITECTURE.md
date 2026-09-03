# Architecture: the commercial pipeline

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

| Stage | Produces | Has a skill? |
|---|---|---|
| `signal` | Dated, sourced evidence. No claim. | `reddit-mine` |
| `qualification` | pursue / watch / suppress, and *who would buy* | `site-factory-prospect` |
| `diagnosis` | What is actually wrong beneath the presented story | **none** |
| `mechanism-selection` | Which intervention the diagnosis implies, or `none` | **none** |
| `sales-artifact` | The thing a buyer sees: audit, one-pager, demo | **none** |
| `outreach` | Getting it in front of the decider | `linkedin-reply`, `recruiter-outreach`, `site-factory-email` |
| `result` | What happened. Recorded whether or not it flatters. | **none** |
| `learning` | What the result changes | partially — the feedback compiler |

`patrick pipeline` prints this live. Three of eight stages are covered, and the
three missing ones in the middle are exactly the decision layer whose absence let
the executor make the decision.

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

- opportunity discovery and ingestion
- the qualification engine, diagnosis engine, and mechanism selector
- tier-advancement gating (the rule exists; nothing enforces it)
- any non-website executor
- cross-stage orchestration — nothing chains stage outputs to stage inputs

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

**Mechanism selector** — `(diagnosis, mechanism registry, strategy rules) ->
ranked mechanisms with reasons`. It should be a pure function over a declarative
table, exactly like `router.resolve`, and testable with no model. The router is
the working precedent to copy.

**Result intake** — the missing half of learning. `feedback add` captures what
Patrick changed about an *output*; nothing captures what a *prospect did*. Until
result intake exists, `strategy/` can only be written by hand, which is why it
is nearly empty and honestly so.

## What did not change

The Site Factory skills, their gates, and their fixtures are untouched by this
work. Both gates remain NO-GO. The two skills are now labelled as executors of
one mechanism rather than as the commercial workflow, which is a change of
framing enforced by tests — not a change of behaviour.
