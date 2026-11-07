---
type: Spec
title: ICIP spec
description: Build detail for withdrawal, attribution, community labels, local processing, publication terms, withholding the deceased, review gates and export.
tags: [provenance, classification, exchange, content]
status: draft
generated: {by: agent:claude-opus-5.5, at: 2026-11-07T00:00:00+10:00}
sources:
  - {id: janke, resource: "https://www.terrijanke.com.au/icip"}
  - {id: aiatsis, resource: "https://aiatsis.gov.au/research/ethical-research/code-ethics"}
  - {id: care, resource: "https://casrai.org/news/care-alongside-fair-indigenous-data-governance-tk-labels"}
  - {id: localcontexts, resource: "https://www.infoclio.ch/en/node/185250"}
  - {id: tehiku, resource: "https://spectrum.ieee.org/indigenous-ai-voice-models-maori"}
---

# ICIP spec

Agent-facing build detail for ICIP. Carries out `PRINCIPLES.md` §5, with §1, §4 and §9.
The human explanation is `docs/icip.md`. If the two disagree, stop and raise it.

None of it is built yet. Sources in frontmatter are pointers for background. Don't quote
a framework's wording from memory; check the primary document first.

## Defaults

Every mechanism here is off or restrictive by default, and the community changes it.
A person can override any default. The override is recorded with who and why
(`PRINCIPLES.md` intro).

## Withdrawal

- A **withdrawal record** names material (document, span, lexeme, sense, construction)
  and carries `by`, `at`, `reason?`. It lives in the community's own store, in the tier
  of the material it names.
- Every build drops withdrawn material and everything derived from it, using the same
  derivation tracking as tier inheritance (`knowledge/spec_classification.md`).
- **Withdrawal test:** a build with the material withdrawn must equal a build where the
  material never existed. Same shape as the general-build test.
- For each exchange package that included the material, generate a withdrawal notice to
  the recipient. A person sends it. Never send automatically.
- Withdrawal doesn't delete the community's own copy unless the community asks.

## Attribution

- The project config holds attribution text per community, and optionally per
  knowledge holder or source, as the community writes it.
- Every rendered page, practice set, report and exchange header carries the attribution
  for the material it uses. A build fails by default if material has no attribution.
- Attribution is separate from provenance (`generated`, classification records).
  Provenance says who did the work; attribution says whose knowledge it is.

## Community labels

- Records may carry a list of labels, each a `{scheme, id, text?, url?}`. Schemes
  include Local Contexts TK and BC Labels and Notices. Others are allowed.
- Labels inherit like tiers: a record without labels takes its container's.
- Rendering shows labels beside the material. Exchange packages carry them.
- Labels state protocol. They never widen access beyond what the tier allows.
- Scheme descriptors, alignment with tiers and Hub import are in
  `knowledge/spec_classification.md` ("Aligning with standard schemes").

## Where processing happens

- Project config declares **processing locations**: `local` and any named outside
  services (including AI services). Each location lists the tiers it may receive.
- Default: `local` only, for every tier.
- Any tool that sends text off the machine (an agent harness, a hosted model, a remote
  database) goes through one gate that checks the tier against the location's list,
  and refuses by default. Log what was sent, where, when, by whom, by tier and record
  ID, never the content.
- Agents working on a community project read this setting before reading material.
  An agent that can't confirm its location is allowed for a tier doesn't read that tier.

## Publication terms

- Project config holds terms of use per audience build, including an AI-training
  statement (`allowed`, `not allowed`, or community text) and an optional licence ID
  or URL for community data.
- Rendered HTML carries the terms visibly, plus machine-readable signals: a meta tag,
  and a `robots.txt` and `ai.txt`-style file in the output root. Document that these
  are requests, not enforcement.
- Exchange packages carry the terms in their header.

## People who have passed away

- A **withholding record** names a person (by an ID in the community's store, never by
  name in shared output) and what to withhold: `name`, `voice`, `image`, or any mix.
  It has `from`, `until?` (open-ended if absent), `by` and `at`.
- Builds replace a withheld name with the community's chosen placeholder text,
  and leave out withheld audio and images. Citations still resolve to an anchor, so the
  evidence stays checkable by people allowed to see it.
- This is separate from tiers and doesn't change any record's tier.
- When `until` passes, the next build restores the material and reports that it did,
  so a person can check before publishing.

## Review before publication

- Config can name review gates per output type (constructed sentences, practice sets,
  tables, exchange packages) and who may approve (`human:` actors only).
- With a gate on, unapproved items don't go into published outputs by default. Approval
  is recorded as `verified` on the item.
- Off by default, because each community decides whether it wants this.

## Export

- One command exports everything a community has put in: corpus, analysis, paradigm per
  tier, classification, withdrawal and withholding records, labels, attribution and
  config. It uses the kit's own open source formats (markdown, YAML, JSON, CSV and
  open media), with a manifest and the kit version. It never exports a database:
  databases are ephemeral and rebuilt from these files.
- Export is per tier and writes only to destinations the community names. It never
  merges tiers.

## The demo

The Japanese demo uses public-domain sources. Exclude Ainu and Ryukyuan material, and
any text whose content belongs to another Indigenous people, even when it's out of
copyright. Those communities' ICIP applies.

## Not decided yet

- Format of withdrawal, withholding and label records, and where each lives.
- How an exchange recipient acknowledges a withdrawal notice.
- Which machine-readable AI-training signals to emit. Conventions are still settling.
- Governance of lect-kit itself: who guides it and how communities using it have a
  voice. The project custodian decides.
