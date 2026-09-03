---
id: "0002"
title: Model routing is a data table, not a code path
kind: architecture
date: 2026-09-03
status: accepted
supersedes: 
---

# 0002 — Model routing is a data table, not a code path

## Context

The brief requires support for a local Qwen endpoint, OpenAI, Anthropic, and future providers, and forbids hard-coding Patrick OS to Claude.

## Decision

config/routes.json declares providers and routes. resolve() is a pure function of (TaskSpec, RouteTable) with no environment reads, no credentials, and no network. Adapters are imported lazily by name, so importing the router pulls in no vendor SDK -- asserted by a test. Adding or retiring a provider is a JSON edit.

## Alternatives considered

A provider interface with a registry in code: still requires a code change per provider. LiteLLM or a similar shim: a dependency, and it decides the abstraction for us.

## Consequences

Routing is fully testable on a machine with no keys. Claude is one row in a table. The cost is that the table can express a route no adapter implements; the doctor command reports that.
