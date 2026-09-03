---
id: "0001"
title: Patrick OS is stdlib-only Python with no install step
kind: architecture
date: 2026-09-03
status: accepted
supersedes: 
---

# 0001 — Patrick OS is stdlib-only Python with no install step

## Context

Hermes (~/.hermes/hermes-agent, Python 3.11, exact-pinned deps) is the dominant automation stack, but it requires a venv. The system python3 here is 3.9.6. Patrick OS must run in both, and must still run in five years when today's dependency set has rotted.

## Decision

Core is Python with zero third-party imports. Tests use stdlib unittest. Front-matter is parsed by a hand-written strict-subset parser rather than PyYAML. The ./patrick shim sets PYTHONPATH and calls python3 directly -- no venv, no pip, no lockfile.

## Alternatives considered

PyYAML plus pytest: better ergonomics, but adds an install step to a tool whose job is to still work on a bad day. A Node CLI: node 25 is present, but Hermes and every other automation here is Python. A hermes plugin: would couple Patrick OS to one vendor's agent, which is the exact thing the brief forbids.

## Consequences

The parser rejects YAML constructs it does not implement, loudly, and that rejection is itself tested. No dependency can break a run. Cost: no schema library, so skill validation is hand-written.
