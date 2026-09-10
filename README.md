# Patrick OS

**Patrick OS is a control plane for AI work.** It turns recurring tasks into versioned procedures, routes each job to the right model, carries project context and decisions forward, checks outputs against deterministic rules, and converts repeated corrections into durable improvements. The models are replaceable workers. Patrick OS is the layer that remembers what they should do, what they got wrong, and what must never break again.

> **Do not solve a recurring task by writing a larger prompt.**

Prompts are instructions. They are not enforcement. If a behavior matters, Patrick OS moves it into something durable: a procedure, a routing rule, a fact record, a test, or a check that can fail independently of the model producing the work.

## Why this exists

The canonical failing test in this repository is an email my own system actually sent.

It scored **PASS. 90.0. Evidence fidelity: 5/5.** It also made an unsupported claim about what a hypothetical website visitor would think and offered to replace duplicated reviews with "distinct, verified reviews", effectively offering to manufacture the evidence it was supposed to evaluate.

Three prompts forbade that behavior. The model did it anyway. The model judge approved it anyway.

That email is now a permanent behavioral fixture:

`skills/site-factory-email/fixtures/behavioral/shipped-sunrise-email.json`

Every commit must prove that the failure still gets caught.

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

## Three failures that shaped the system

### A judge that shares a model with the writer measures nothing

A calibration example once leaked into a judge prompt. The single passing output showed **0.590 trigram similarity** to that example; the four failures measured only **0.015–0.081**. The judge was rewarding resemblance to its calibration example instead of independently evaluating the work.

Patrick OS therefore requires the judge provider to differ from the writer provider. If independence cannot be established, it refuses to judge.

### Style cannot overrule evidence

A quality filter once deleted the two most evidence-rich candidates because they used the word `metadata`.

Checks are separated by severity:

- **blocking**: fact integrity, unsupported claims, manufactured evidence, leaked addresses, missing citations
- **advisory**: style, register, openings, length, phrasing

Advisory checks may request repair. They may never eliminate an otherwise truthful output.

### Fluency is not evidence of correctness

The email that caused the canonical regression test was also one of the best-written outputs the system had produced.

No model score is permitted to be the final authority on fact integrity when a deterministic check can establish the answer instead.

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

The model is the worker. Patrick OS determines the procedure, context, route, checks, and what gets remembered afterward.

## Current state

- **300 checks pass, 0 fail.** `./patrick test`
- **No install, virtualenv, or third-party Python dependencies.** Python 3.9+.
- **Nothing in v1 sends anything anywhere.** No email, post, webhook, or hidden send path.
- **The voice layer is provisional.** Its rules come from a small corpus and retain provenance so they can be revised as better evidence accumulates.

## Model routing

Task classes name work, not vendors. Providers and fallbacks live in `config/routes.json`, and `patrick route <task-class>` explains a routing decision without calling anything.

Routes can require local execution for sensitive material, prefer stronger writers for human-facing work, and reject a judge that is not independent of the writer. Credentials are not stored in routing config.

## Learning

Patrick OS captures corrections without turning every edit into doctrine.

A correction starts local. Scope expands only when the same pattern repeats across contexts. Changes to names, numbers, dates, or URLs do not count as evidence of a behavioral rule. Promotion runs the regression suite and rolls the rule back if it breaks existing behavior.

Output lessons can become voice rules. Strategy lessons require evidence. Workflow changes are made deliberately rather than inferred from edits.

## Domains

The core holds concerns that apply across kinds of work. Subject-specific vocabulary lives in domain packs under `patrick_os/domains/`, so a commercial workflow does not force commercial concepts onto unrelated work.

A skill with no domain is a normal Patrick OS skill. Domain-specific skills declare the domain whose contract they use. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the details.

## Quick start

```sh
./patrick doctor --probe
./patrick skills list
./patrick route judge.copy
./patrick run reddit-mine --input subreddit=recruiting --input pain_hypothesis='...'
./patrick judge site-factory-email --output draft.md
./patrick test
```

`patrick run` is dry-run by default. It composes the work order and resolves the route but calls nothing. `--execute` calls the selected provider and writes the result to disk.

## Repository layout

| Directory | Purpose |
|---|---|
| `skills/` | Reusable procedures plus behavioral fixtures |
| `projects/` | Project truth records: facts and constraints |
| `decisions/` | Decisions that should stay decided |
| `voice/` | Rules for how output should read |
| `strategy/` | Evidence-backed rules for what is worth pursuing |
| `feedback/` | Corrections, proposals, and promotion history |
| `domains/` | Subject-specific knowledge and contracts |
| `config/` | Routing, retrieval, and domain configuration |
| `tests/` | Unit and structural tests |
| `runs/` | Local execution artifacts; gitignored |
| `docs/` | Architecture and infrastructure documentation |

## Adding a skill

1. Copy the skill template into `skills/<slug>/SKILL.md`.
2. Define the procedure, inputs, output contract, checks, and routing requirements.
3. Declare a domain only when the skill performs domain-specific work.
4. Add at least one fixture under `skills/<slug>/fixtures/`.
5. Run `./patrick test <slug>`.

Validation fails malformed skills, missing required sections, missing fixtures, and any skill that declares a send path.
