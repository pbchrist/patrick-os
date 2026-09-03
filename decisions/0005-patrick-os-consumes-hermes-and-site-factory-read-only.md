---
id: "0005"
title: Patrick OS consumes Hermes and Site Factory read-only
kind: architecture
date: 2026-09-03
status: accepted
supersedes: 
---

# 0005 — Patrick OS consumes Hermes and Site Factory read-only

## Context

Hermes is an upstream Nous Research repo at v0.13.0 with live git history at ~/.hermes/hermes-agent. Site Factory is 27 modules on the audit/site-factory-20260901 branch of the private pbchrist/hermes-projects repo, with both gates NO-GO. Breaking either while adding a layer on top would be a straightforward own-goal.

## Decision

Patrick OS writes nothing into ~/.hermes/, ~/.claude/skills/, or hermes-projects. Hermes is consumed as a provider by shelling out to 'hermes chat -Q' with the exact argv Site Factory's llm_client.py already uses -- reusing its OAuth logins rather than copying keys. Site Factory is consumed as facts: its verified defects are written into projects/site-factory.md and enforced as gates inside two skills that run outside its pipeline.

## Alternatives considered

Patch site-factory directly to fix SF-03/SF-05/SF-06: correct eventually, but it is a NO-GO codebase mid-audit and not what was asked for here. Install Patrick OS skills into ~/.hermes/skills/: couples the two and makes Hermes' behavior depend on this repo.

## Consequences

Hermes and Site Factory behave today exactly as they did before Patrick OS existed. The argv Patrick OS sends to Hermes is asserted by a test, so a drift in that interface fails loudly rather than at runtime.
