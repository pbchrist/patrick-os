---
id: "0003"
title: Feedback capture and rule promotion are separate human-gated verbs
kind: process
date: 2026-09-03
status: accepted
supersedes: 
---

# 0003 — Feedback capture and rule promotion are separate human-gated verbs

## Context

The brief's feedback sequence ends with 'apply if it improves results', which invites auto-application. A correction that silently becomes a permanent rule is how a voice layer drifts away from the person it is supposed to represent.

## Decision

'patrick feedback add' observes, diffs, classifies, and proposes -- and never writes to voice/. 'patrick feedback promote' writes exactly one rule to exactly one file, runs the regression suite, and restores the file byte-for-byte if the suite fails. A correction seen once is always classified local and produces no proposal. Edits that touch only names, numbers, dates, or URLs are excluded from repetition counting entirely, so ten name corrections never sum to one rule.

## Alternatives considered

Auto-apply with a confidence threshold: the threshold is a guess, and the failure mode is silent and cumulative. Manual rule editing only: loses the repetition signal that makes a rule justified.

## Consequences

Learning is slower and always reversible; every promoted rule has a changelog entry naming its source, occurrence count, and revert instruction. Two regression tests hold the line: a one-off proper-noun edit must produce no rule, and a rollback must leave the voice file byte-identical.
