---
type: Tracker
title: Principles in practice
description: Which mechanism keeps each operating principle, and the gaps still open.
tags: [process]
status: draft
generated: {by: agent:claude-opus-5.5, at: 2026-11-07T00:00:00+10:00}
---

# Principles in practice

Agent-maintained tracker: what keeps each principle in `PRINCIPLES.md` working, and what is still missing. Update it whenever a mechanism lands or a gap is found.

| § | Principle | Kept by | Missing |
|---|---|---|---|
| 1 | Communities stay in control | Code makes no choices about a language. Projects configure them | Once code arrives, check its defaults for bias towards the first project's language |
| 2 | Any account describes a point in time | Nothing yet | Date, place, speaker and recorder on every corpus document, each with how it is known. Versions on models and rendered tables. No output may call a form correct or standard |
| 3 | No language content | `knowledge/content_procedure.md`, `scripts/check_content.py` with lists supplied at run time, the Japanese demo and abstract fixtures | The checker only finds what it's given. No pre-commit hook yet. The Japanese demo has no content yet, so nobody has checked any |
| 4 | Classification runs through every layer | `knowledge/spec_classification.md` (design only), `schemes/localcontexts-tk-labels.yaml` | Tier register, per-record tiers, per-tier paradigm stores, per-audience builds, the general-build test, leak checks, screening queue, verdict egress filter and separation check are all still to build |
| 5 | Cultural and intellectual property stays with its community | `knowledge/spec_icip.md` (design only), ICIP notice in `LICENSE`, `schemes/` descriptor for TK Labels | Withdrawal, attribution, labels, processing-location gate, publication terms, withholding, review gates and export are all still to build. Governance of the kit is undecided |
| 6 | Everything here is public | Reading every diff, `check_content.py` | No check on pull requests yet |
| 7 | Keep the model and the record apart | Nothing yet | Comes with the layer guard and database build |
| 8 | Each language on its own evidence | Nothing yet | Comes with the lect register and the links schema |
| 9 | Custodians can share paradigms, and talk | `knowledge/spec_exchange.md` (design only) | Package format, terms of use, per-recipient sharing, cognate proposals, conversation sheets and records, and the feedback note are all still to build |
| 10 | Fix the schema | Review | |
| 11 | Measure the fit | Nothing yet | Comes with the scoreboard |
| 12 | Say who made it | Nothing yet | Comes with the corpus metadata schema |
| 13 | AI is optional, and kept out of training | `docs/ai.md`, `knowledge/spec_ai.md` (design only), `CLAUDE.md` | Human-only test runs, the AI service gate and terms records are still to build. A page on how the kit was built |
| 14 | Stay in step with users | The work steps in `CLAUDE.md` | No project uses the kit yet. No versioning policy yet |
| 15 | Look after the record for the long term | `docs/keeping-safe.md`, `knowledge/spec_storage.md` (design only) | Change history, review gates, backup check, restore tests, integrity manifests and succession records are all still to build |

## Conflicts

None so far.
