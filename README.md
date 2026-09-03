# Patrick OS

Reusable procedural infrastructure for repeated work.

The rule this repository exists to enforce: **do not solve a recurring task by
writing a larger prompt.** Write down the procedure, the voice, the facts, and
the routing once, version them, test them, and let any model execute against
them.

Patrick OS is model-agnostic by construction. No vendor SDK is imported at module
load. Every provider — a local Qwen server, Hermes, Anthropic, OpenAI — is a row
in `config/routes.json`, and routing is a pure function that resolves with no
keys and no network. Claude is a worker inside this system, not the system.

## Status

v0.1.0 — spine complete, five skills, 116 checks passing.

**The voice layer is scaffolding, not a finished voice model.** See
[`voice/README.md`](voice/README.md). The rules currently in `voice/` were
derived from two documents; a real voice model needs a corpus of Patrick's actual
outputs, edits, and rejections. Every rule carries provenance so it can be traced
back, revised, or retired when that corpus arrives.

**The regression suite has two layers.** Structural fixtures prove a work order
carries the right rules and routes to the right provider. Behavioral fixtures
prove a specific *produced output* is caught or passed — and the canonical
negative fixture is the email Site Factory actually shipped at PASS / 90.0 /
evidence_fidelity 5/5. Behavioral fixtures run offline, with no model.

## Quick start

No install. No virtualenv. No dependencies. Python 3.9 or newer.

```sh
./patrick doctor              # what is configured, what is reachable
./patrick skills list
./patrick skills show reddit-mine --body
./patrick route judge.copy    # explain a routing decision, calling nothing
./patrick run reddit-mine --input subreddit=recruiting --input pain_hypothesis='...'
./patrick judge site-factory-email --output draft.md   # deterministic checks
./patrick test                # 152 checks
```

`patrick run` is a dry run: it composes the work order and resolves the route,
and calls nothing. `--execute` calls the routed provider and writes the result to
a file. **Nothing in v1 sends anything anywhere** — see decision 0004.

## Layout

| Directory    | Holds                                                           |
|--------------|-----------------------------------------------------------------|
| `voice/`     | Durable style rules, scoped global → channel → project → skill, each citing its evidence. Provisional. |
| `skills/`    | One directory per procedure. `SKILL.md` plus `fixtures/`.       |
| `projects/`  | Per-project truth records. Facts and constraints, never procedure. |
| `feedback/`  | Captured corrections, their classification, and the changelog of every rule learned. |
| `schedules/` | Declarative recurring work. Names a skill; contains no logic.   |
| `decisions/` | Things that stay decided.                                       |
| `tests/`     | The unit suite. `patrick test` runs it alongside skill fixtures. |
| `config/`    | `routes.json` — the whole model-routing policy.                 |
| `runs/`      | Local run artifacts. Gitignored.                                |

## How the pieces fit

```
skill (procedure) ─┐
voice rules ───────┼──> work order ──> router ──> provider ──> draft on disk
project facts ─────┘                                              │
                                                                  v
                                        human edits it ──> patrick feedback add
                                                                  │
                                              (repeats?) ──> proposal
                                                                  │
                                            patrick feedback promote ──> one voice rule
                                                                          + changelog
```

A correction seen **once** is local and never becomes a rule. Scope escalates on
repetition across contexts — same skill, then project, then channel, then global.
Edits that touch only names, numbers, dates, or URLs are excluded from counting
entirely, so ten name corrections never sum to one rule. Promotion runs the
regression suite and restores the voice file byte-for-byte if it fails.

## Model routing

`config/routes.json` declares providers and the routes that select them. Task
classes name work, not vendors.

| Route      | Prefers                                | Why |
|------------|----------------------------------------|-----|
| `research` | local-qwen → hermes-copilot              | high volume, low stakes, keep it free |
| `draft`    | anthropic-opus → hermes-copilot          | anything a human signs gets the strongest writer |
| `judge`    | hermes-copilot, **denies** local-qwen    | a judge sharing a model with the writer measures nothing |
| `private`  | local-qwen, `require_local`            | client material and candidate PII stay on the machine |

`patrick route <task-class>` explains any decision, including every rejection and
its reason. If the chosen provider is down, the runner falls through the ranked
fallbacks and records every attempt.

Credentials are never stored in config — only the *name* of the environment
variable that holds one. See `.env.example`.

## Relationship to Hermes and Site Factory

Read-only, both. Patrick OS writes nothing into `~/.hermes/`, `~/.claude/skills/`,
or `pbchrist/hermes-projects`. Hermes is consumed as a provider by shelling out
to its CLI; Site Factory is consumed as *facts* — its verified defects are
recorded in `projects/site-factory.md` and enforced as gates inside two skills
that run outside its pipeline. Both behave exactly as they did before this
repository existed. See decision 0005.

## Adding a skill

1. `cp skills/_TEMPLATE.md skills/<slug>/SKILL.md` and fill in every section.
2. Write at least one fixture in `skills/<slug>/fixtures/`.
3. `./patrick test <slug>`.

`patrick test` fails a skill missing any required section, missing fixtures, or
declaring `sends: true`.

## Judging an output

`patrick judge <skill> --output <file>` runs the skill's declared `output_checks`
— pure functions over text, offline. Two severities, and the distinction comes
straight from Site Factory finding SF-08:

- **blocking** — fact integrity. An unmeasured claim, a manufactured-evidence
  offer, a leaked address, a missing citation. These kill an output.
- **advisory** — style. Hype register, an opener, length. These annotate for
  repair and never eliminate. SF-08 verified that a style-eliminating lint
  deleted the two evidence-richest candidates over the word "metadata".

`--execute` adds an independent model judge. Two properties are enforced in code,
not remembered:

1. The judge provider must differ from the writer provider, or Patrick OS refuses
   to judge at all.
2. The judge prompt is built from the skill's own criteria and contains **no
   exemplar output**. SF-07 measured what happens otherwise: the one passing
   output scored 0.590 trigram similarity to the calibration example against
   0.015–0.081 for the four failures, and the judge cited "the rhetorical
   structure of the positive calibration" as its standard.

Verdicts: `pass`, `repair`, `reject`, `escalate` — the last is separate on
purpose, because "a human must decide" is not the same as "this is bad".
