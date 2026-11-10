---
type: Directory Guide
title: Agent knowledge directory guide
description: What each file in knowledge/ holds, the rules agents follow to keep it current, and the frontmatter profile.
tags: [process]
status: draft
generated: {by: agent:claude-opus-5.5, at: 2026-11-07T00:00:00+10:00}
---

# knowledge/

Agent knowledge for lect-kit: specs, procedures and trackers that agents build from and
keep current. It is open for people to inspect, but it's written for agents. People
should start at `README.md`, `PRINCIPLES.md` and `docs/`.

## Files

| File | Holds |
|---|---|
| `content_procedure.md` | What may enter the repository, the pre-commit procedure, how the content checker behaves |
| `feature_procedure.md` | How Gherkin features link specs to tests and code, and the traceability and coverage checks |
| `spec_workflow.md` | Build detail for the corpus, paradigm, join, rendering, constructed speech, practice and checking |
| `spec_classification.md` | Build detail for tiers, per-tier paradigms, per-audience builds and leak checks |
| `spec_icip.md` | Build detail for withdrawal, attribution, labels, processing location, publication terms, withholding, review gates and export |
| `spec_ai.md` | Build detail for human-only operation, the AI processing gate and provider checks |
| `spec_storage.md` | Build detail for change history, review, per-tier backups, restore tests, integrity, formats and succession |
| `spec_exchange.md` | Build detail for exchange packages and cognate proposals |
| `principles_in_practice.md` | Which mechanism keeps each principle, and the open gaps |

## Gardening rules

- **Keep it current.** When code, a schema or a decision changes, update the file that
  describes it in the same change. A stale spec is worse than none.
- **Cite the human source.** Every spec names the `PRINCIPLES.md` sections it carries
  out and the `docs/` page that explains it. If a spec and its human page disagree, stop
  and raise it. Don't quietly fix either.
  `python scripts/check_knowledge_refs.py` checks the citations resolve.
- **One fact, one place.** Don't restate the principles or the human docs here. Link
  to them and add only the build detail.
- **Say what's undecided.** Each spec ends with a "Not decided yet" list. Move items off
  it only when a person decides.
- **Keep it inspectable.** Plain markdown, sentence-case headings, no generated noise. A
  person checking an agent's work should be able to read any file here.
- **Same content rules as everywhere.** Nothing here may hold a community's language,
  names or restricted terms (`content_procedure.md`).
- **Prune.** Delete what no longer applies, and record in the change why it went.

## Identifiers

Identifiers the kit defines or reads (scheme and label IDs, tier IDs, lect IDs, record
IDs, config keys) match `[A-Za-z_-][A-Za-z0-9_-]*` by default: a letter, underscore
or hyphen, then any of those or digits. A publisher's own code or display
name, such as a Local Contexts abbreviation with a space in it, is kept as display text
in a separate field and never used as an identifier. `python scripts/check_identifiers.py`
checks the files in `schemes/`.

## Frontmatter (Open Knowledge Format)

Every markdown file in `knowledge/`, this one included, opens with YAML frontmatter in
the Open Knowledge Format (OKF) v0.2. This section is lect-kit's profile of it. Where
it is stricter than OKF, it wins. `python scripts/check_knowledge_frontmatter.py`
enforces it.

Required:

| Key | Rule |
|---|---|
| `type` | One of: `Spec`, `Procedure`, `Tracker`, `Directory Guide`, `Design Note`, `Decision` |
| `title` | Short noun phrase, sentence case, no trailing full stop |
| `description` | One sentence ending in a full stop, at most 220 characters, saying what the file holds |

Optional:

| Key | Rule |
|---|---|
| `tags` | At most four, from: `corpus`, `paradigm`, `rendering`, `practice`, `classification`, `exchange`, `content`, `provenance`, `measurement`, `process` |
| `status` | `draft`, `stable` or `deprecated`. Absent means `stable` |
| `generated` | `{by: <actor>, at: <ISO 8601 datetime with offset>}`. Set it when you write or substantially rewrite a file. An agent actor is `agent:<model>`, a person is `human:<name or role>` |
| `verified` | A list of `{by, at}`. Only a person's review goes here, with a `human:` actor. A passing checker isn't verification |
| `sources` | A list of `{resource, id?}`, each a repository path or URL |
| `stale_after` | An ISO 8601 datetime after which the file should be rechecked |

No other keys. Add a key to this table before using it.

There's no `classification` key, because nothing in this repository has a tier other
than public. If that changes, the profile changes first.
