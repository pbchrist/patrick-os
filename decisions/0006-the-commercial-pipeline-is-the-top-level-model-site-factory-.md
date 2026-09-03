---
id: "0006"
title: The commercial pipeline is the top-level model; Site Factory is a mechanism executor
kind: architecture
date: 2026-09-03
status: accepted
supersedes: 
---

# 0006 — The commercial pipeline is the top-level model; Site Factory is a mechanism executor

## Context

Site Factory was operating as the top-level commercial decision engine, with an implicit model of 'find a bad website -> build a better website'. That lets the tooling that happens to exist choose the intervention, and it is the direct cause of verified finding SF-03: a Cloudflare challenge became a qualified website-rebuild opportunity at score 90, because a rebuild was the only conclusion the system could reach. Patrick's own positioning note names the Narrative Decision Audit as the cash engine's repeatable offer, and that is a positioning intervention, not a web one.

## Decision

The durable model is signals -> qualification -> diagnosis -> mechanism selection -> sales artifact -> outreach -> result -> learning. Site Factory is the executor for the 'website' mechanism only. Patrick OS now tracks stage, mechanism, and investment tier as three axes separate from task_class, all declared per skill and validated; mechanisms live in config/mechanisms.json so a non-web intervention is a config edit; strategy/ exists as a rule namespace distinct from voice/, with its own scope vocabulary and a mandatory evidence requirement; and patrick pipeline prints stage and mechanism coverage so the gaps are visible. The Opportunity Engine itself is NOT built.

## Alternatives considered

Build the Opportunity Engine now: explicitly deferred by the user until the OS core and Site Factory correctness work are stable, and it would be built on an unvalidated core. Leave the architecture implicit and remember the constraint: an architecture nothing enforces is a preference, and the next skill added would have defaulted to the website mechanism. Widen voice/ scopes to carry strategy rules: collapses two kinds of rule revised on different evidence into one file, so a lesson about which buyers to stop chasing would sit next to a rule about em-dashes.

## Consequences

A skill that will not say where it sits in the pipeline now fails validation, which is a deliberate cost paid on every future skill. patrick pipeline reports 3 of 8 stages covered, and the three empty ones in the middle -- diagnosis, mechanism-selection, sales-artifact -- are precisely the decision layer whose absence let the executor make the decision. The 'positioning' mechanism is declared with no executor, which surfaces that the cash engine's actual offer has no implementation. Nothing orchestrates stages yet: pipeline.stage_index exists for ordering checks and nothing calls it. Strategy rules have no reader until mechanism selection is built, which is the correct order -- the destination must exist before the lessons do, or they get written into voice/ where they do not belong.
