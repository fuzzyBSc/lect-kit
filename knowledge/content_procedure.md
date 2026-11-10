---
type: Procedure
title: Content procedure
description: What may enter this public repository, the pre-commit steps, and how the content checker behaves.
tags: [content, process]
status: draft
generated: {by: agent:claude-opus-5.5, at: 2026-11-07T18:00:00+10:00}
---

# Content procedure

Agent procedure for keeping community language content out of this public repository.
Carries out `PRINCIPLES.md` §3 and §6. People read `docs/content_rules.md` for the policy.

## Allowed

- Code, schemas, schema docs, method notes.
- Japanese in `examples/demo/japanese/`, from public-domain sources only, written for
  this repository, not copied from copyrighted or share-alike data. No Ainu or Ryukyuan
  material, or other material belonging to an Indigenous people, even if out of copyright.
- Abstract fixtures in `examples/demo/fixtures/` (labels like `stemA`, `sfx-erg-1`).
- Generic linguistic terms. References to published methods and software.

## Refuse

- Any word, form, sentence or gloss from the language of a community that uses the kit.
- Speaker, informant or family names, with or without honorifics.
- Restricted or culturally sensitive terms, or any list of them.
- Corpus text, transcripts, recordings, page images, tape or archive identifiers.
- Rulings, history or decisions of a consuming project. Generalise the mechanism.
- The names of consuming projects or their repositories.
- Personal paths, email addresses, machine names, credentials.

If unsure, leave it out and ask the project custodian.

## Before every commit

1. Read the whole diff. Never commit a file you haven't read.
2. Run the checker with the consuming project's lists:

   ```bash
   python scripts/check_content.py --deny <lexicon list> --deny <restricted-term registers>
   ```

   Or set `LECT_KIT_DENY` to the paths, separated by the OS path separator.
3. On a hit, remove the content or rewrite it with the Japanese demo or a fixture. Don't
   disguise it.
4. Without deny-lists the checker runs generic checks only and says so. That isn't
   enough for a change upstreamed from a consuming project.

## Checker behaviour (`scripts/check_content.py`)

- Deny-lists are read only from run-time paths. Never copy, cache or log them, and never
  write one into this repository.
- Plain text lists: one term per line, `#` comments.
- JSON or YAML (`.yaml`, `.yml`): only strings under `term`, `form`, `word`, `headword`,
  `lemma` keys (terms), `variant`, `variants` keys (each matched as a whole word) or
  `pattern`, `regex` keys (regexes, case-insensitive by default) count. A bare list counts as terms.
  Every other key, such as labels, notes, ids and flags, is ignored, so none of them
  produces false hits. A variant or pattern that isn't a valid regex is matched literally
  rather than dropped. Two per-entry options follow the term registers' own tooling: an
  entry with `case_sensitive: true` matches its terms, variants and patterns only in the
  case written, and an entry's `suffix_guard` regex is appended after each of its variants
  (not its patterns) to exclude a look-alike word. An invalid guard stops the run. Any
  other key is ignored.
- Terms and variants match as whole words even when they hold or sit next to
  punctuation, and both the list and the files are NFC-normalised. YAML is read with every
  value as text.
- A path that doesn't exist and a file that can't be decoded are errors. A directory is
  expanded. A deny-list that doesn't exist, isn't UTF-8, or is a folder with no lists stops the
  run, and the error names the file only. A deny-list folder is read as the `.yaml`,
  `.yml` and `.json` lists under it, outside hidden folders, so a project can pass the
  folder its lists live in. A plain text list is named on its own, so notes kept beside
  the lists can't become terms. The hooks and the scan read term registers the same way.
- Generic checks: honorific followed by a capitalised name, tape-style identifiers,
  personal paths, email addresses.
- A hit prints file and line only, never the matched text. Exit 1 on any hit.
- `examples/demo/` is checked like everything else, because romanised Japanese can
  collide with a community's words. A person decides each collision.
- A pass means the checker found nothing it was told to look for. It isn't a clearance.
