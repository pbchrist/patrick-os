---
id: "0008"
title: Audit the topology before concluding that capability is missing
kind: process
date: 2026-09-04
status: accepted
supersedes: 
---

# 0008 — Audit the topology before concluding that capability is missing

## Context

local-qwen returned connection refused, and from that single signal I concluded a second paid model provider was needed. Both halves were wrong. The endpoint was 127.0.0.1:8082, copied from Site Factory's .env.example, which is correct only when running on the inference box; llama.cpp was healthy the whole time on patrick-beastmaster. And a valid Codex ChatGPT OAuth credential was already present at ~/.codex/auth.json. I also reported openai-codex as unavailable when it is a current Hermes provider whose credential simply was not registered in Hermes' pool.

## Decision

Before reporting that infrastructure is missing, audit it end to end and report the concrete failure point for each unavailable route: what is configured, what is listening, what the service log says, and which credential stores hold what. patrick doctor --probe performs real reachability checks rather than inferring readiness from config presence, and patrick judges reports which independent pairs actually exist. Config presence is never reported as readiness.

## Alternatives considered

Ask the user to authenticate or purchase: fastest to type, and it externalises a diagnosis I had not done. Probe only the failing endpoint: would have found the wrong host but not the idle Codex credential, the crash-looping second server, or the fact that independence was already satisfiable.

## Consequences

The audit found four things one probe would not have: a stale host rather than a dead service, a CUDA OOM crash loop at 8429 restarts with a 490MB log, a valid unused Codex credential, and a borrowed 24k payload cap that belonged to a different route to the same machine. Judge independence is now satisfied at full strength with no purchase. Cost: doctor --probe makes real network and subprocess calls and is slower than reading config, which is why it is opt-in.
