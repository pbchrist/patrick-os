---
id: "0004"
title: Patrick OS v1 has no send path at all
kind: product
date: 2026-09-03
status: accepted
supersedes: 
---

# 0004 — Patrick OS v1 has no send path at all

## Context

Three of the five skills are outward-facing. Site Factory's teardown found the documented kill switch (TEST_MODE) was read by zero lines of Python, and narrative-sourcing states outright that it does not send messages and never will.

## Decision

No skill declares sends: true, and skill validation fails any that does. --execute writes a draft to a file and stops. site-factory-email accepts no recipient address as an input, and its output format has no recipient field.

## Alternatives considered

A dry-run flag defaulting to on: that is what Site Factory believed it had. A flag that can be flipped is not the same as an absent code path.

## Consequences

Patrick moves every outbound message by hand. That is the intended cost, and it is what makes SF-06 unreachable from here.
