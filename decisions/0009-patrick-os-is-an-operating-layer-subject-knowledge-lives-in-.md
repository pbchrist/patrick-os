---
id: "0009"
title: Patrick OS is an operating layer; subject knowledge lives in domain packs
kind: architecture
date: 2026-09-04
status: accepted
supersedes: 
---

# 0009 — Patrick OS is an operating layer; subject knowledge lives in domain packs

## Context

Patrick OS had absorbed one consumer's vocabulary. stage was a REQUIRED field on every skill, drawn from a commercial pursuit pipeline, and mechanism selection, investment tiers and sales outcomes sat in the core beside the router. A fiction skill could not validate: it was made to name a position in a sales workflow and state which sales intervention it served. Verified by attempting to validate a scene-audit skill, which failed on both counts. docs/ARCHITECTURE.md opened by presenting the commercial pipeline as the top-level model of Patrick OS.

## Decision

Patrick OS is the operating layer: persistent context and decision memory, reusable skills, model and tool routing, independent judgment and QA, feedback-driven learning, and orchestration across projects and agents. Subject knowledge moves into domain packs under patrick_os/domains/. The commercial pack owns the pursuit workflow, mechanism registry, investment tiers, outcome vocabulary and the two commercial output checks. A skill declares a domain only if it does subject-specific work; a skill with no domain is a plain OS skill and validates with no domain vocabulary at all.

## Alternatives considered

Leave it and rely on discipline: the leak happened by accident once and would again, because nothing objected. Delete the commercial machinery: it works, it is used, and the instruction was to demote it rather than lose it. Separate repositories: premature, and it would break the single decision log and feedback loop that are the point of an operating layer.

## Consequences

Four tests hold the boundary: core imports no pack at load (checked in a subprocess, since sys.modules is global), no core module imports a pack at module level, no commercial check sits in the core registry, and every domain-less skill validates clean. Cost: a domain check resolves through a second lookup, and a genuinely cross-domain concept now has to be argued about rather than assumed into the core. patrick pipeline is relabelled as a commercial-domain view; patrick skills list is the OS view and shows each skill's domain. Site Factory behaviour is unchanged -- this is a move and a relabel, not a rewrite.
