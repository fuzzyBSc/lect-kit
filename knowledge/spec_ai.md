---
type: Spec
title: AI-optional operation spec
description: Build detail for human-only operation, the AI processing gate, training-exclusion records and provider checks.
tags: [process, content, provenance]
status: draft
generated: {by: agent:claude-opus-5.5, at: 2026-11-07T00:00:00+10:00}
---

# AI-optional operation spec

Agent-facing build detail. Carries out `PRINCIPLES.md` §13, with §5. The human
explanation is `docs/ai.md`. If the two disagree, stop and raise it.

None of it is built yet.

## Human-only is the baseline

- Every stage in `knowledge/spec_workflow.md` must run with no AI configured. Commands,
  checks and builds take no model, API key or network access to an AI service.
- AI-assisted steps (OCR drafts, candidate analyses, cognate suggestions, drafted text)
  are optional add-ons to a human step, never the only route. Each has a manual
  equivalent that is documented and tested.
- Tests run with AI disabled. A test suite that needs an AI service to pass is a defect.
- Anything an AI produces is recorded with `kind: ai` and `status: ai-draft` or
  `review: open` until a `human:` actor accepts it (`PRINCIPLES.md` §12).
- Human docs are written for people working by hand. Don't write steps that assume an
  agent will do them.

## The AI processing gate

The processing-location gate in `knowledge/spec_icip.md` covers AI services. In addition:

- Each AI service entry in project config records: provider, account type, whether it
  trains on submitted data, how to turn training off, retention period and purpose, and
  whether those terms are contractual. It also records who checked, when, and a link or
  copy reference to the terms. The kit doesn't supply these values. A person fills them
  in.
- By default the gate refuses a service whose entry says training is on, or is unknown,
  or whose terms check is older than a configured age. A person can override, and the
  override is recorded.
- Local models are a location type of their own (`local-model`) and need no training
  entry, but the gate still checks the tier.
- The gate logs every send: service, tier, record IDs, time, actor. Never the content.

## Agents working on a community's project

- Before reading community material, an agent confirms its own service is an allowed
  location for that tier. If it can't confirm, it doesn't read that tier and says so.
- Agents don't paste community material into issues, pull requests, commit messages or
  any other place outside the community's store.
- This repository (lect-kit) holds no community material, so agents here aren't
  exposed to it. The rule applies when the kit runs in a community's project.

## Publication

- Rendered outputs carry the community's AI-training statement (`knowledge/spec_icip.md`
  "Publication terms"). Docs and output say plainly that it's a request.
- A build for a public audience lists every record it publishes by tier, so a person can
  see what will be exposed to collection before it goes out.

## Not decided yet

- The config format for AI service entries.
- The default maximum age of a terms check.
- Whether to ship a starter checklist for common providers. Their terms change, so any
  list would need dating and re-checking.
