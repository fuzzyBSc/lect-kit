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
- The AI-training statement defaults to `not allowed`. A community can change it per
  build, recorded with who and why.
- Exchange packages carry the terms in their header.

### Training controls in published sets

*Project custodian's ruling, 2026-11-08:* every published set carries the most
appropriate controls against AI training that can be put in text, in the files of the
set, or in server configuration shipped with it. While the statement is `not allowed`,
a build emits all of the following. Exact syntax comes from each convention's current
document, checked when the emitter is built, not from memory.

- **Plain text.** Every page shows the terms near the top, and every downloadable file
  (CSV, JSON, YAML, markdown, text) carries them in a header comment or a sibling
  `TERMS` file. The default text says the material may not be used to train, fine-tune
  or evaluate AI models, and that the rights holders reserve text and data mining
  rights, including under Article 4(3) of the EU DSM Directive. The community can
  replace the text; the reservation sentence stays unless they remove it on the record.
- **HTML head.** TDMRep `tdm-reservation` and `tdm-policy` meta tags, a robots meta tag
  with `noai, noimageai`, and a link to the terms page.
- **`robots.txt`.** A `__usage_ai-training` group disallowing everything; the IETF AI
  Preferences usage line (`Content-Usage`) saying no training; Cloudflare's
  `Content-Signal` line with `ai-train=no`; and a `Disallow: /` group for each known
  training crawler. Whether search crawlers may index is a separate community setting,
  default allowed.
- **Other root files.** `/.well-known/tdmrep.json`, `ai.txt`, and a terms page. Add new
  conventions here when they have a published specification.
- **HTTP headers.** `tdm-reservation`, `tdm-policy`, `X-Robots-Tag: noai, noimageai`
  and the AI Preferences `Content-Usage` header, written in the host's own format: an
  `.htaccess` for Apache, a `_headers` file for static hosts that read one, and an
  nginx snippet in the build report for the person who runs the server.
- **Crawler blocking.** The `.htaccess` also refuses requests from the known training
  crawlers by user agent (403). This is the only control that blocks a crawler that
  ignores signals, and it only works on hosts that honour `.htaccess`.
- **Embedded metadata.** Images, audio, video and PDF carry the terms in XMP, with IPTC
  `plus:DataMining` set to prohibited, and EPUB and PDF carry TDMRep properties. A file
  the kit can't write metadata into is listed in the build report.

Rules around them:

- The crawler list and signal syntax are a data file in `schemes/`, with each entry's
  source URL and the date it was checked, and a `stale_after`. A build warns when the
  file is stale. Updating it is part of keeping the kit current (`PRINCIPLES.md` §14).
- The build report says which controls the chosen host will actually serve (a host that
  ignores `.htaccess` or `_headers` gets none of those) and that every control except
  server blocking is a request.
- A public build fails if any control is missing, unless a recorded override says which
  one and why.
- If the statement is `allowed` or community text, the build emits that instead and
  none of the blocking rules.

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
- The schema of the crawler and signal data file.
- Whether a set behind a login still gets the full set of controls (default: yes).
- Governance of lect-kit itself: who guides it and how communities using it have a
  voice. The project custodian decides.
