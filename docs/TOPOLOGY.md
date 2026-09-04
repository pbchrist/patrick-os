# Model and retrieval topology

Audited end to end 2026-09-04 by probing, not by reading config. Reproduce with
`patrick doctor --probe` and `patrick judges`.

## What was wrong, and what it cost

`local-qwen` was configured as `http://127.0.0.1:8082/v1`, copied from Site
Factory's `.env.example` — which is correct only when you run *on* the inference
box. llama.cpp runs on `patrick-beastmaster`. **The service was fine the whole
time; the host was wrong.**

From that single refused connection I concluded a paid provider was needed. That
was wrong twice over: the local model works, and a valid Codex credential was
already sitting in `~/.codex/auth.json`. The lesson is recorded in
`decisions/0008`.

## Inference topology

`patrick-beastmaster` (`100.73.250.50`, Tailscale) runs two `llama-server`
instances on one pair of GPUs:

| Port | Model | GPU | State |
|---|---|---|---|
| 8082 | `Qwen3.8-27B-Q4_K_M` (16G) | 0 (RTX 3090), pinned via `CUDA_VISIBLE_DEVICES=0` | **up** since 2026-09-01, 20.4/24 GB used |
| 8081 | `Qwen3.6-27B-Q6_K` (21G) | unpinned → targets GPU 0 | **down** — CUDA OOM |

**The 8081 crash loop.** `llama-server.service` had a restart counter of **8429**
and a 490 MB log. It declares no `CUDA_VISIBLE_DEVICES`, so it targets GPU 0,
which the 8082 service already holds at 20.4 of 24 GB. The idle GPU 1 (RTX 4060
Ti) has 16 GB free, and the Q6_K weights are 21 GB, so pinning alone will not fix
it. The loop was stopped:

```sh
ssh root@100.73.250.50 systemctl stop llama-server.service     # done
ssh root@100.73.250.50 systemctl start llama-server.service    # to undo
```

To actually restore a second local model, one of: a quant that fits GPU 1 under
16 GB (the existing `Qwen3.8-27B-Uncensored-Q4_K_M` is 16 G — too tight with KV
cache), a smaller model, or reduced context on GPU 1. **Not required** — one
local model is enough for independence.

**Request size.** 8, 32 and 64 KB bodies all succeeded against 8082, so
`max_request_bytes` is 65536. The previous 24000 was borrowed from the Cloudflare
tunnel `narrative-sourcing` uses — a *different route to the same machine*.

## Providers

| Provider | Vendor | Auth | State |
|---|---|---|---|
| `local-qwen` | `local-llamacpp` | none | **UP** — verified completion |
| `codex-cli` | `openai` | existing ChatGPT OAuth in `~/.codex/auth.json` | **UP** — verified completion |
| `hermes-copilot` / `-4o` | `github-copilot` | Hermes pool (`gh auth token`) | **UP** — verified with gpt-4.1 and gpt-4o |
| `hermes-nous` | `nous` | Hermes pool | credential present, **refresh token rejected** on use |
| `local-qwen-36` | `local-llamacpp` | none | **DOWN** — see crash loop above |
| `anthropic-opus` | `anthropic` | `ANTHROPIC_API_KEY` | not set — **optional, nothing prefers it first** |
| `openai-api` | `openai` | `OPENAI_API_KEY_PATRICK_OS` | not set — pay-per-token path to a vendor `codex-cli` already reaches free |

A test enforces that no route prefers a paid provider first.

## `openai-codex` is not an obsolete alias

It is a **current** provider in Hermes v0.13.0 (`run_agent.py` references it
throughout). Site Factory naming it is not a mistake.

What is missing is narrower than it looked: `openai-codex` reads **Hermes' own
credential pool**, and that pool holds only `copilot` and `nous`. The Codex
credential exists — `~/.codex/auth.json`, `auth_mode: chatgpt`, refreshed
2026-09-04 — it has just never been registered into Hermes.

Two ways to close it, neither a purchase: run `hermes auth` to add the Codex
credential to Hermes' pool, or use the Codex CLI directly, which is what Patrick
OS's `codex_cli` adapter does. Patrick OS took the second because it uses the
credential that exists rather than requiring a registration step.

## Judge independence

Ranked by **vendor**, not provider key: two providers from one vendor share a
model family and a safety stack.

- `2` — different vendor. Real independence.
- `1` — same vendor, different model. Clears the bar Site Factory's own
  `llm_client` enforces, and nothing more.
- `0` — the writer itself. Never permitted.

`patrick judges` reports the live pairing. Currently **every reachable writer has
a strong, different-vendor judge**, from `local-llamacpp` ↔ `openai` ↔
`github-copilot`. Nothing needs to be purchased or authenticated.

`local-qwen` used to be *denied* in the judge route. That encoded an assumption
that local was always the writer; once local turned out to be one of only two
freely reachable vendors, denying it would have removed the strongest available
judge. Verified in practice: asked to judge a Codex-written diagnosis, the local
model caught the circular-citation defect and explained it more precisely than
the Copilot judge had.

## Retrieval is a separate layer

`reddit-mine` cannot read Reddit. Verified twice: Reddit serves a "Prove your
humanity" challenge to logged-out programmatic reads.

**This is a retrieval-layer failure and nothing else.** No model, provider, or
routing change addresses it. Reaching for a different model in response is a
category error, and the skill's failure-modes section now says so.

`config/retrieval.json` declares backends per source with an explicit status, so
a blocked source is a backend swap rather than a skill rewrite. `agent-browse` is
`blocked` with its reason recorded. `reddit-api` is now implemented in
`patrick_os.retrieval` and performs public app-only OAuth retrieval *before* the
model runs; it needs `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`. No Reddit
username/password is required. `manual-export` remains the default until those
two environment variables are installed.
