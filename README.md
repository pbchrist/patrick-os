# Patrick OS

**Patrick OS is a control plane for AI work.** It turns recurring tasks into versioned procedures, routes each job to the right model, carries project context and decisions forward, checks outputs against deterministic rules, and converts repeated corrections into durable improvements. The models are replaceable workers. Patrick OS is the layer that remembers what they should do, what they got wrong, and what must never break again.

The premise is simple:

> **Do not solve a recurring task by writing a larger prompt.**

Prompts are instructions. They are not enforcement. If a behavior matters, Patrick OS moves it into something durable: a procedure, a routing rule, a fact record, a test, or a check that can fail independently of the model producing the work.

## Why this exists

The canonical failing test in this repository is an email my own system actually sent.

It scored **PASS. 90.0. Evidence fidelity: 5/5.** It also made an unsupported claim about what a hypothetical website visitor would think and offered to replace duplicated reviews with "distinct, verified reviews" — effectively offering to manufacture the evidence it was supposed to evaluate.

Three prompts forbade that behavior. The model did it anyway. The model judge approved it anyway.

That email is now a permanent behavioral fixture:

`skills/site-factory-email/fixtures/behavioral/shipped-sunrise-email.json`

Every commit must prove that the failure still gets caught.

That is the operating principle of Patrick OS:

**If a mistake matters, do not merely tell the model not to make it. Build a system that detects it.**

## What Patrick OS controls

| Concern | Where it lives |
|---|---|
| **Procedures** | `skills/` |
| **Project facts and decisions** | `projects/`, `decisions/` |
| **Model and tool routing** | `config/routes.json`, `patrick_os/router/` |
| **Deterministic QA and independent judgment** | `patrick_os/checks.py`, `judging.py` |
| **Voice and strategy rules** | `voice/`, `strategy/` |
| **Feedback and learned corrections** | `feedback/` |
| **Domain-specific knowledge** | `patrick_os/domains/` |
| **Execution and retrieval** | `runner.py`, `retrieval.py` |

Site Factory, the Opportunity Engine, recruiting, research, writing, and fiction are **consumers** of Patrick OS. They are not Patrick OS.

## What is true right now

No pitch language. No implied capabilities.

- **300 checks pass, 0 fail.** `./patrick test`
- **No install, virtualenv, or third-party Python dependencies.** Python 3.9+.
- **Nothing in v1 sends anything anywhere.** No email, post, webhook, or hidden send path.
- **The voice layer is provisional.** It is scaffolding derived from a small corpus, not a finished model of Patrick's voice.
- **This has not made money, and there is no evidence that anyone else wants Patrick OS as a product.** It is infrastructure for Patrick's work.
- **The Opportunity Engine is not built yet.** Its commercial architecture exists as a domain; it is not the operating system itself.

## The three rules that shaped the system

### 1. A judge that shares a model with the writer measures nothing

A calibration example once leaked into a judge prompt. The single passing output showed **0.590 trigram similarity** to that example; the four failures measured only **0.015–0.081**. The judge was rewarding resemblance to its calibration example, not independently evaluating the work.

Patrick OS therefore requires the judge provider to differ from the writer provider. If independence cannot be established, it refuses to judge.

### 2. Style cannot overrule evidence

A quality filter once deleted the two most evidence-rich candidates because they used the word `metadata`.

Checks are now separated by severity:

- **blocking**: fact integrity, unsupported claims, manufactured evidence, leaked addresses, missing citations
- **advisory**: style, register, openings, length, phrasing

Advisory checks may request repair. They may never eliminate an otherwise truthful output.

### 3. Fluency is not evidence of correctness

The email that caused the canonical regression test was also one of the best-written outputs the system had produced.

That is precisely the problem. No model score is permitted to be the final authority on fact integrity when a deterministic check can establish the answer instead.

## How work moves through Patrick OS

```text
skill + project facts + voice/strategy rules
                    │
                    v
               work order
                    │
                    v
                  router
                    │
                    v
                 provider
                    │
                    v
               draft on disk
                    │
          ┌─────────┴─────────┐
          v                   v
 deterministic checks   independent judge
          │                   │
          └─────────┬─────────┘
                    v
               human result
                    │
                    v
                 feedback
                    │
          repeated + supported?
                    │
                    v
             durable rule
```

The model is the worker. The surrounding system decides what context it receives, what procedure it follows, which provider performs the work, how the result is checked, and what gets remembered afterward.

## Domains

Patrick OS core contains only concerns that are true across kinds of work. Subject-specific vocabulary lives in domain packs under `patrick_os/domains/`.

The commercial domain, for example, defines pursuit stages, intervention mechanisms, investment tiers, and outcome types. That vocabulary does not belong in fiction, recruiting, or general research, so tests enforce that the core does not import it structurally.

A skill with **no domain** is a normal Patrick OS skill and is valid as-is. A domain-specific skill declares its domain and satisfies that domain's contract.

`patrick pipeline` is therefore a view of the **commercial domain**, not a diagram of Patrick OS itself.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full domain interfaces and `decisions/0006` for the architectural decision.

## Model routing

Task classes name the work. They do not name vendors.

| Route | Preference | Reason |
|---|---|---|
| `research` | local-qwen → hermes-copilot | high-volume, low-stakes work can stay local/free |
| `draft` | anthropic-opus → hermes-copilot | human-facing work gets the strongest available writer |
| `judge` | hermes-copilot; denies local-qwen when it wrote the draft | writer and judge must be independent |
| `private` | local-qwen; `require_local` | sensitive material stays on the machine |

`patrick route <task-class>` explains the choice and every rejected alternative without calling a provider.

Credentials are never stored in routing config. Config contains only the name of the environment variable that holds a credential. See `.env.example`.

## Learning without turning every correction into doctrine

Patrick OS captures corrections, but one correction does not automatically become a global rule.

A correction starts local. Scope can expand only when the same pattern repeats across contexts. Changes to names, numbers, dates, or URLs do not count as evidence of a behavioral rule. Promotion runs the regression suite and rolls the rule back if it breaks existing behavior.

The learning paths are deliberately separate:

- `output` lessons can promote into `voice/`
- `strategy` lessons can promote into `strategy/`, with evidence required
- `workflow` lessons are refused for automatic promotion because procedures should be changed deliberately, not inferred from edits

## Quick start

```sh
./patrick doctor --probe
./patrick judges
./patrick skills list
./patrick skills show reddit-mine --body
./patrick route judge.copy
./patrick run reddit-mine --input subreddit=recruiting --input pain_hypothesis='...'
./patrick judge site-factory-email --output draft.md
./patrick pipeline
./patrick select --profile p.json
./patrick result record --outcome no_reply --evidence '...'
./patrick voice --strategy
./patrick test
```

`patrick run` is dry-run by default: it composes the work order and resolves the route but calls nothing. `--execute` calls the selected provider and writes the result to disk.

**Nothing in v1 sends anything anywhere.** See `decisions/0004`.

## Repository layout

| Directory | Purpose |
|---|---|
| `skills/` | Reusable procedures plus behavioral fixtures |
| `projects/` | Project truth records: facts and constraints, never procedure |
| `decisions/` | Decisions that should stay decided |
| `voice/` | Evidence-backed rules for how output should read |
| `strategy/` | Evidence-backed rules for what is worth pursuing |
| `feedback/` | Corrections, classifications, proposals, and promotion history |
| `domains/` | Subject-specific knowledge and contracts |
| `config/` | Routing, retrieval, enabled domains, and domain configuration |
| `tests/` | Unit and structural tests |
| `runs/` | Local execution artifacts; gitignored |
| `docs/` | Architecture and infrastructure documentation |

## Adding a skill

1. Copy the skill template into `skills/<slug>/SKILL.md`.
2. Define the procedure, inputs, output contract, checks, and routing requirements.
3. Declare a `domain` only if the skill performs domain-specific work. Plain OS skills require no domain. Domain skills must satisfy their domain's metadata contract.
4. Add at least one fixture under `skills/<slug>/fixtures/`.
5. Run `./patrick test <slug>`.

Validation fails malformed skills, missing required sections, missing fixtures, and any skill that declares a send path.

## Judging an output

```sh
./patrick judge <skill> --output <file>
```

This runs the skill's deterministic `output_checks` offline.

`--execute` may add an independent model judge, but two properties are enforced in code:

1. The judge provider must differ from the writer provider.
2. The judge prompt is built from the skill's criteria and contains no exemplar output.

Verdicts are `pass`, `repair`, `reject`, and `escalate`. `escalate` is intentionally distinct from `reject`: requiring a human decision does not mean the work is bad.
