---
type: Spec
title: Change control and storage spec
description: Build detail for change history, review, backups per tier, restore tests, integrity manifests, formats and succession.
tags: [provenance, classification, process]
status: draft
generated: {by: agent:claude-opus-5.5, at: 2026-11-07T00:00:00+10:00}
---

# Change control and storage spec

Agent-facing build detail. Carries out `PRINCIPLES.md` §15, with §4, §5 and §13. The
human explanation is `docs/keeping-safe.md`. If the two disagree, stop and raise it.

None of it is built yet.

## What is authoritative

- **Sources:** corpus documents, original media, analysis records, paradigm files,
  classification, withdrawal and withholding records, labels, conversation records,
  config. Back up and protect these.
- **Derived:** the database (always ephemeral, see "Formats"), generated cells, rendered
  pages, practice items, search indexes, exchange packages. Rebuild these. Never treat a derived file as the only
  copy of anything.
- A build writes into a staging location and replaces the live output only when every
  stage passes, so a failed build leaves the previous output intact.

## Change history

- Each tier's store is a version-controlled repository (git by default, any tool with
  equivalent history allowed). One store per tier. Closed tiers never share a repository
  or a remote.
- Every change is a commit with author, time and message. The kit's tools write a
  commit for every change they make, with a `kind: human|ai` actor in the message
  trailer. Agent commits are marked as agent work.
- History is append-only by default. Kit tools never rewrite or discard history: no
  force-push, rebase, reset, amend, stash or clean. Undo is a new commit that restores
  the earlier state. A person can override this, and the override is recorded.
- Withdrawal (`knowledge/spec_icip.md`) is a commit that removes the material from the
  current version. Purging it from history is a separate, explicit, person-run operation
  the community chooses, with a record in the tier's store that it happened.

## Review before keeping

- Config can require a second reviewer per path or record type (classification records,
  public-audience config, terms, withdrawal) before a change is merged into the tier's
  main line. Reviewers are `human:` actors.
- Off by default except for changes that widen access: a change moving material to a
  more open tier, or adding a tier to an outside location's allowed list, needs a
  second human reviewer by default.

## Backups

- Config declares backup targets per tier: path or service, `kind` (`local`, `removable`,
  `offsite`, `service`), encryption, and who holds the key (roles, not names in shared
  config).
- A `service` target is a processing location under `knowledge/spec_icip.md` and
  `knowledge/spec_ai.md`, with the same tier allow-list and terms record.
- A backup check reports, per tier, how many targets exist, of how many kinds, and
  whether one is offsite. Below three copies, two kinds and one offsite is a warning
  by default.
- Backups of closed tiers are never written to the same target.
- Targets that leave the community's hands are encrypted by default.

## Restore tests

- A restore command rebuilds a tier's store from a backup into a scratch location and
  compares it with the integrity manifest.
- Each tier records the date of its last successful restore test. The backup check
  warns when it's older than a configured age.

## Integrity

- Each tier keeps a manifest of every source file: path, size, SHA-256, and the commit
  it was last changed in.
- An integrity check recomputes hashes and reports any file whose content changed
  without a commit, or that is missing. It names the file, never its content.
- Original media (audio, images) are stored unchanged, with the manifest entry. Working
  copies (trimmed clips, compressed images) are derived and say which original they
  come from.
- An external holding (an archive's original or preservation copy) is recorded as a reference with the
  holder's identifier, not copied in unless the community has it.

## Formats

- Sources are plain text (markdown, YAML, JSON, CSV) and open media formats (WAV or
  FLAC for audio, TIFF or PNG for images, PDF for documents as received).
- SQLite is never a storage format. A SQLite database is always ephemeral: built from
  sources, deleted and rebuilt at will, never backed up, exported, committed to a
  tier's store or treated as holding anything that isn't also in a source. A tool that
  would write a fact only to a database is a defect. Write it to a source and rebuild.
- No source may exist only in a binary or proprietary format. An import from one
  produces an open copy, and the original is kept as received.
- Export (`knowledge/spec_icip.md`) uses these same formats.

## Succession

- Config records, per tier, the roles that hold access and keys, and a restore
  procedure document kept in that tier's store. Roles, not names, in anything shared.
- The backup check warns when a tier lists fewer than two key-holding roles.

## Agents

- Agents never run history-rewriting or discarding commands in a community's store.
- Agents don't create backup targets or change backup config. They can report the
  backup check and draft a restore procedure for a person to review.

## Not decided yet

- Default maximum age for restore tests.
- Whether the kit supports a non-git history backend.
- How purge-from-history is recorded without keeping the purged content.
