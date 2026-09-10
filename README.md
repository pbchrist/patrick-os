# Patrick OS

**The canonical failing test in this repository is an email my own system sent.**

It scored PASS. 90.0. Evidence fidelity 5 out of 5. It contained the sentence
*"To a new visitor, that looks like a copy-paste error rather than a full roster
of happy clients"* — a claim about the mental state of a person nobody surveyed —
and it offered to replace a business's duplicated reviews with "distinct,
verified reviews," which is offering to manufacture the evidence you are being
paid to measure.

Three separate prompts in that codebase forbade exactly this. The model judge
scored it perfect anyway.

That email is now `skills/site-factory-email/fixtures/behavioral/shipped-sunrise-email.json`,
and every commit has to prove it still gets caught.

That is what this repository is. Not a framework. A set of rules that exist
because something specific went wrong, each one carrying the receipt.

---

## The rule this repository exists to enforce

**Do not solve a recurring task by writing a larger prompt.**

A prohibition stated only inside a prompt is not enforcement. It is a wish. Write
down the procedure, the voice, the facts, and the routing once; version them;
test them; let any model execute against them. Then check the output with code
that cannot be talked out of its finding.

Patrick OS is model-agnostic by construction. No vendor SDK is imported at module
load. Every provider — a local Qwen server, Hermes, Anthropic, OpenAI — is a row
in `config/routes.json`, and routing is a pure function that resolves with no
keys and no network. Claude is a worker inside this system, not the system.

## What is actually true right now

Stated plainly, because the whole point of the thing is refusing to overclaim:

- **300 checks pass, 0 fail.** `./patrick test`. No install, no virtualenv, no
  dependencies, Python 3.9+. The suite is offline and runs no model.
- **Nothing in v1 sends anything, anywhere.** Not email, not a post, not a
  webhook. There is no send path in the codebase to disable. See `decisions/0004`.
- **The voice layer is scaffolding, not a finished voice model.** Its rules were
  derived from two documents. A real voice model needs a corpus of actual
  outputs, edits, and rejections. Every rule carries provenance so it can be
  traced, revised, or retired when that corpus exists.
- **This has not made any money and no evidence says anyone else wants it.**
  It is infrastructure for one person's work that happens to be legible to
  others. `projects/` records that verdict for every project it tracks, in those
  words, on purpose.

If you came here for a growth-hack framework, the vocabulary list in
`voice/global.md` bans "unlock", "supercharge", "game-changer", "secret weapon",
and "10x", and a check enforces it. You will not enjoy this.

## The three failures that shaped the design

Every real rule here has a receipt. These three are the load-bearing ones.

**A judge that shares a model with the writer measures nothing.**
Measured, not assumed: when a calibration example leaked into the judge prompt,
the single passing output scored **0.590** trigram similarity to that example,
against **0.015–0.081** for the four failures. The judge then cited "the
rhetorical structure of the positive calibration" as its standard. It was
grading recall of the example. So: the judge provider must differ from the writer
provider or Patrick OS refuses to judge at all, and the judge prompt is built
from the skill's own criteria and contains no exemplar output.

**A style lint that can eliminate will eliminate the truth.**
A quality filter deleted the two most evidence-rich candidates over the word
"metadata". Checks now come in two severities and the line between them is
absolute: **blocking** is fact integrity — an unmeasured claim, a
manufactured-evidence offer, a leaked address, a missing citation — and kills an
output. **Advisory** is style, and annotates for repair. Advisory can never
eliminate.

**Fluency is not evidence of correctness.**
The overreach quoted at the top of this file was the best-written thing the
system produced. That is precisely why it was dangerous, and why no model score
is permitted to be the last word on fact integrity.

## Learning that resists its own enthusiasm

Corrections are captured, but a correction seen **once** is local and never
becomes a rule. Scope escalates only on repetition across contexts — same skill,
then project, then channel, then global. Edits touching only names, numbers,
dates, or URLs are excluded from counting entirely, so ten name fixes never sum
to one rule. Promotion runs the regression suite and restores the voice file
byte-for-byte if it fails.

Three layers, and one of them is deliberately a dead end: `output` lessons
promote into `voice/`; `strategy` lessons promote into `strategy/` and require
evidence; `workflow` lessons are **refused** for promotion, because this system
rewrites rules, not procedures.

## What Patrick OS is

Patrick OS is the **operating layer for Patrick's AI work**. It is not a
lead-generation system, a Site Factory wrapper, or an opportunity engine.

Its job is to make every project smarter, more consistent and more reusable than
it would be on its own, by holding six things centrally so that no project has to
reinvent them:

| | |
|---|---|
| **Persistent context and decisions** | `projects/`, `decisions/` |
| **Reusable skills** | `skills/` — procedures, not prompts |
| **Model and tool routing** | `config/routes.json`, `patrick_os/router/` |
| **Independent judgment and QA** | `patrick_os/checks.py`, `judging.py` |
| **Feedback-driven learning** | `feedback/`, `voice/`, `strategy/` |
| **Orchestration across projects** | `runner.py`, `retrieval.py`, `domains/` |

Site Factory, the Opportunity Engine, recruiting, writing, research and fiction
are **consumers** of Patrick OS. They are not Patrick OS.

## Domains

Subject knowledge lives in a domain pack under `patrick_os/domains/`, never in
the core. A domain declares the vocabulary true of one *kind* of work — the
commercial pack declares pursuit stages, intervention mechanisms, investment
tiers and outcome types.

**A skill that declares no domain is a plain OS skill and is valid as-is.** That
sentence is the correction: `stage` used to be required of every skill, drawn
from a commercial pipeline, so a fiction skill could not validate — it was made
to declare which sales intervention it served. Tests now enforce that no core
module imports a pack.

`patrick pipeline` is a view of the **commercial domain**, not of Patrick OS.
`patrick skills list` is the OS-level view. Full detail, including the interfaces future stages will need, is in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and `decisions/0006`. The
Opportunity Engine is deliberately **not** built yet.

## Quick start

No install. No virtualenv. No dependencies. Python 3.9 or newer.

```sh
./patrick doctor --probe      # what is ACTUALLY reachable, tested not inferred
./patrick judges              # which independent judge pairs exist right now
./patrick skills list
./patrick skills show reddit-mine --body
./patrick route judge.copy    # explain a routing decision, calling nothing
./patrick run reddit-mine --input subreddit=recruiting --input pain_hypothesis='...'
./patrick judge site-factory-email --output draft.md   # deterministic checks
./patrick pipeline            # stage and mechanism coverage
./patrick select --profile p.json      # choose a mechanism; deterministic
./patrick result record --outcome no_reply --evidence '...'  # what happened
./patrick voice --strategy    # rules about what is worth pursuing
./patrick test                # 300 checks, offline
```

`patrick run` is a dry run: it composes the work order and resolves the route,
and calls nothing. `--execute` calls the routed provider and writes the result to
a file. **Nothing in v1 sends anything anywhere** — see decision 0004.

## Layout

| Directory    | Holds                                                           |
|--------------|-----------------------------------------------------------------|
| `voice/`     | Durable style rules — *how an output reads* — scoped global → channel → project → skill, each citing its evidence. Provisional. |
| `strategy/`  | Rules about *what is worth pursuing*, scoped global → mechanism → segment → project. Evidence mandatory. |
| `skills/`    | One directory per procedure. `SKILL.md` plus `fixtures/`.       |
| `projects/`  | Per-project truth records. Facts and constraints, never procedure. |
| `feedback/`  | Captured corrections, their classification, and the changelog of every rule learned. |
| `schedules/` | Declarative recurring work. Names a skill; contains no logic.   |
| `decisions/` | Things that stay decided.                                       |
| `tests/`     | The unit suite. `patrick test` runs it alongside skill fixtures. |
| `domains/`   | Subject knowledge, per kind of work. `commercial/` holds what used to sit in the core. |
| `config/`    | `routes.json` (routing), `retrieval.json` (sources), `domains.json` (enabled packs), `domains/*` (per-domain config). |
| `docs/`      | `ARCHITECTURE.md` — the pipeline and the three axes. `TOPOLOGY.md` — the audited model and retrieval infrastructure. |
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

1. `cp skills/_TEMPLATE.md skills/<slug>/SKILL.md` and fill in every section,
   including `stage:` and either `mechanisms:` or `mechanism_agnostic: true` —
   a skill that will not say where it sits in the pipeline fails validation.
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
  repair and never eliminate — for the reason recorded above.

`--execute` adds an independent model judge. Two properties are enforced in code,
not remembered:

1. The judge provider must differ from the writer provider, or Patrick OS refuses
   to judge at all.
2. The judge prompt is built from the skill's own criteria and contains **no
   exemplar output** — the trigram measurement above is what happens otherwise.

Verdicts: `pass`, `repair`, `reject`, `escalate` — the last is separate on
purpose, because "a human must decide" is not the same as "this is bad".
