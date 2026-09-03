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

**The regression suite is structural, not behavioral.** It proves a work order
carries the right rules and routes to the right provider. It does not yet prove
the output is any good. Behavioral fixtures are the next layer.

## Quick start

No install. No virtualenv. No dependencies. Python 3.9 or newer.

```sh
./patrick doctor              # what is configured, what is reachable
./patrick skills list
./patrick skills show reddit-mine --body
./patrick route judge.copy    # explain a routing decision, calling nothing
./patrick run reddit-mine --input subreddit=recruiting --input pain_hypothesis='...'
./patrick test                # 116 checks
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
| `research` | local-qwen → hermes-codex              | high volume, low stakes, keep it free |
| `draft`    | anthropic-opus → hermes-codex          | anything a human signs gets the strongest writer |
| `judge`    | hermes-codex, **denies** local-qwen    | a judge sharing a model with the writer measures nothing |
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
