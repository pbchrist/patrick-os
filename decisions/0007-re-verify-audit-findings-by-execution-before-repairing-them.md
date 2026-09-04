---
id: "0007"
title: Re-verify audit findings by execution before repairing them
kind: process
date: 2026-09-04
status: accepted
supersedes: 
---

# 0007 — Re-verify audit findings by execution before repairing them

## Context

The plan was to fix SF-03, SF-05, SF-06, and SF-07 from the 2026-09-01 teardown. Re-running each finding against branch head 3e050f0 showed that commit 95bd2a3 had already repaired ten of twelve. Fixing them again would have produced a confident commit message describing work that was not done, and Patrick OS would have carried a truth record that was wrong about its own primary project.

## Decision

Every audit finding is re-verified by execution against current code before any repair is attempted, and the verification result is recorded in the project truth record as a status table with evidence per finding. A teardown is a measurement of a commit, not a standing description of a codebase.

## Alternatives considered

Trust the teardown and fix the named files: fast, and would have produced false claims plus redundant changes to code that was already correct. Read the code without executing: the teardown itself distinguished verified from inferred findings for exactly this reason, and two of the live defects here -- an argv the CLI rejects, and an exit code -- are invisible to reading.

## Consequences

Re-verification cost roughly one pass over the repo and found two live defects nobody had logged, both of the same shape as SF-01: a control that is documented and believed in but that no code path can execute. That shape is now worth searching for directly. The truth record in projects/site-factory.md is a status table with per-finding evidence rather than a list of assumed-live bugs, and the skill gates are documented as defence against regression rather than as descriptions of current behaviour.
