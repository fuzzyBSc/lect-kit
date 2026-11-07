---
type: Spec
title: Classification spec
description: Build detail for community-defined tiers, per-tier paradigms, per-audience builds and leak checks.
tags: [classification]
status: draft
generated: {by: agent:claude-opus-5.5, at: 2026-11-07T18:00:00+10:00}
---

# Classification spec

Agent-facing build detail for classification. Carries out `PRINCIPLES.md` §4. The human
explanation is `docs/classification.md`. If the two disagree, stop and raise it.

Only the register file is built so far.

Classification here means who may see something under a community's own rules. It is a
different thing from evidence quality or review state, and the kit keeps them apart.

## Tiers are the community's

A project declares its tiers in a tier register. The kit has no built-in tier names.
The Japanese demo register (`examples/demo/japanese/jp-tiers.yaml`) uses illustrative ones (`jp-open`, `jp-a`, `jp-b`).

Each tier entry has:

- An ID and a display name chosen by the community.
- **Sees:** the tiers a reader of this tier may also see. This is a plain list, not a
  ranking, so a community can describe tiers that are nested, side by side, or closed to
  each other. For example, `jp-a` and `jp-b` might each see `jp-open` but not each
  other.
- Where the tier's material is stored (see below).
- Who may classify into it, as the community decides.

The kit checks that the register is consistent. For example, every tier named in a
**sees** list must exist. It doesn't decide what the tiers should be.

### Register file (built: `lectkit/tiers.py`, `scripts/check_tier_register.py`)

The register is one YAML file in the project, at a path the project chooses:

```yaml
register: 1
tiers:
  - id: jp-open
    name: Open
    sees: []
    store: {path: ../stores/jp-open, remote: allowed}
  - id: jp-a
    name: Tier A
    sees: [jp-open]
    store: {path: ../stores/jp-a, remote: none}
    classifiers: ["human:jp-a-reviewers"]
```

- `store.path` and `store.remote` are both required. `store.path` is relative to the
  register file. `store.remote` is `allowed` or `none`; a missing or unknown value is an
  error, and the tier is treated as `none` meanwhile.
  A tier with `remote: none` is kept only on machines its readers hold. Its store can't
  have a git remote, and the check fails if it has one.
- `classifiers` is optional: the actors who may classify into the tier.
- **Sees is written out in full.** If `jp-b` sees `jp-a` and `jp-a` sees
  `jp-open`, then `jp-b` must list both. The check fails on a missing one rather than
  inferring it, so anyone reading the file can see exactly who reads what.
- Two tiers are **closed** to each other when neither sees the other. The check reports
  the closed pairs, because every separation check uses them.
- Two tiers can't share a store, one tier's store can't lie inside another's, and a tier
  can't list itself.
- `python scripts/check_tier_register.py <register> [--stores]` runs the checks. With
  `--stores` it also opens each store that exists on disk and checks its remotes against
  `store.remote`. A store must be the top of its own git checkout; a folder inside some
  other repository fails. A store that isn't present is reported, not passed, and so is a
  machine without git. Stores aren't checked while the register itself has problems.

A **higher** tier's scanner reads the stores its `sees` list names. Nothing reads a store
in the other direction.

There is one more state, separate from the tiers: **unread**. Material nobody has read
and classified yet is unread. No build uses it, whatever tier it might turn out to be.
A pattern scan can flag likely restricted material, but it can't clear anything. Only
reading does that.

## Aligning with standard schemes

Communities should be able to adopt a published scheme instead of designing tiers from
nothing. Scheme descriptors live in `schemes/` (names, codes, categories and links only).

- **Start from a scheme.** A setup command reads a descriptor and drafts a tier register
  and attribution and terms settings from each label's `suggests` field. For example, a
  `restricts` label proposes a tier that isn't open, and a `permits` label proposes a
  publication term. The draft is `status: draft` until a person accepts each item.
- **Map existing tiers.** A tier entry may list `aligns_with: [{scheme, id}]`, using the descriptor's `id`, never its
  display `code`. The kit
  uses it to emit the matching labels in rendered pages and exchange packages, and to
  read labels on incoming material.
- **Labels on records.** A record's labels (see `knowledge/spec_icip.md`) are checked
  against its tier. A restricting label on a record whose tier is open is an error by
  default. The kit never changes the tier itself; a person resolves it.
- **Unmapped restricting label.** Incoming material carrying a restricting label that no
  local tier is aligned with is treated as unread, so no build uses it, and is reported.
- **Who applied it.** Every label records `applied_by` (`community`, `institution`,
  `researcher`) as the scheme defines. A community-only label applied by anyone else is
  flagged.
- **Local Contexts Hub.** Optionally fetch a project's labels and the community's own
  label text from the Hub API by project ID, and store the ID, the text and the Hub URL.
  Refresh on request. Fetching is a network call, so it goes through the processing gate
  (`knowledge/spec_icip.md`). It only sends the project ID.

## Every record carries a tier

| Layer | Records that carry a tier |
|---|---|
| Corpus | Documents (a default), spans within them, analysis records |
| Paradigm | Lexemes, senses, classes, slots, allomorph rules, suffix-order rules, constructions, lect links |
| Outputs | Generated cells, tables, constructed sentences, practice items, reports |
| Notes | Research notes and anything else authored |

A record without its own tier takes the tier of its container. A span inside a document
takes the document's default unless the document lists it differently. A sense takes its
lexeme's tier unless it has its own. A child can be more restricted than its container.
It can't be less restricted, because that would let a general view open a restricted
container to reach it.

Each classification records who made it (`kind: human` or `kind: ai`), when, and the
basis (`read` or `pattern-scan`). An AI classification is a draft until a person the
community trusts accepts it.

## A paradigm split by tier

Each tier can hold a full model of its own: lexemes, senses, rules, slots, constructions
and links. A tier's paradigm lives in that tier's own store, laid out like any other.

A tier's model may build on the tiers its readers can see. A restricted tier can add
lexemes that take the general verb classes, or add a suffix that stacks on general
slots. It can't change or remove anything in a tier its readers see. It can only add.
That keeps the general model the same whether or not restricted tiers are loaded.

A tier can also hold a sense of a general word. The word stays in the general register
with its general senses, and the restricted sense lives in the restricted tier and
points to it. A general build sees the word and none of the restricted senses.

## Builds are per audience

A build is run for one audience, meaning one tier and the tiers it sees. It loads only
those tiers' corpus and paradigm, and writes everything to a store for that audience:
database, tables, practice items, search index and measures. Each audience gets its own
copy, and builds never share one.

**The general-build test:** building the open tier with every restricted store absent
must give exactly the same result as building it with them present. A difference means
something restricted is leaking into the general build. The test runs on every build.

## Results take the tier of their inputs

A generated cell's tier combines its lexeme's tier with the tiers of every rule that
built it. A constructed sentence's tier combines its words, its frame and its
construction. In practice:

- A form built from a restricted lexeme is restricted, even if every rule is general.
- A general lexeme built with a restricted suffix is restricted.
- A sentence with one restricted word is restricted.
- A count over restricted material is restricted. A general measure counts general
  material only.

When inputs come from two tiers closed to each other, no audience can see the result.
The kit reports that and doesn't build it.

## Checking outputs for leaks

Besides the general-build test:

- Each audience's outputs are checked against the restricted-term registers of the tiers
  that audience can't see. The registers are read at run time from the community's
  stores. Hits are reported by file and line, never by the matched text.
- A spelling that matches both a general and a restricted lexeme is flagged for a person
  to decide. The kit doesn't guess which one is meant.

## Screening open material: containment

Checking whether material is safe for an open audience needs knowledge the open
audience mustn't have, so the check is done by someone or something allowed to see the
restricted tier. The design keeps that knowledge from flowing back out with the answer.

### Roles

- **Screener for tier T:** a person, or a process acting for one, allowed to see tier T.
  It reads material bound for an audience that can't see T and decides whether any of it
  belongs in T.
- **One screener per closed tier.** If tiers A and B are closed to each other, A's
  screener and B's screener are separate. They never share a person's notes, a process,
  a store or an agent context. Open material is screened by each in turn.
- **Requester:** whoever wants the material screened. Usually works in the open tier and
  never sees the screener's working.

### What crosses back (the verdict)

A verdict is the only thing that leaves the screener, and its shape is fixed:

| Field | Values |
|---|---|
| `target` | The record or span screened (ID or file and line range) |
| `outcome` | `clear`, `hold`, or `refer` |
| `screened_for` | Tier ID |
| `by` | `human:<role>` or `agent:<model>` acting for a named human role |
| `at` | ISO 8601 datetime with offset |
| `basis` | `read` or `pattern-scan` |

- `hold` means "don't publish this to the open audience". `refer` means "a person with
  authority for this tier needs to look".
- No free text, no matched term, no suggested rewording, no reason beyond the outcome.
  Even "this word is a problem" tells the requester which word. The verdict says the
  span, not the word.
- A `pattern-scan` verdict can only `hold` or `refer`. Only a `read` verdict by a person
  can `clear` (`PRINCIPLES.md` §4: unread is not general).
- The screener's reasoning, notes and the term it matched stay in tier T's store, linked
  to the verdict ID.

The verdict still says something: that a span matters to tier T. Communities accept that
small disclosure. To keep it small, verdicts give spans rather than words, and a
requester can't run the screener over and over to narrow one span down (rate-limit
repeat screens of the same target and refer them to a person).

### Fixing held material

The requester doesn't learn why a span was held, so the screener's side does the fixing:

1. The screener, or a person in tier T, proposes a replacement for the held span.
2. The replacement is itself screened before it goes back.
3. Only the replacement and a new verdict cross back. The original reason stays in T.

Where no clean replacement exists, the span is removed from the open build. The open
record is never edited to hint at what was there.

### Human-only

- The community names screeners for each tier, as people it trusts. Each closed tier
  has its own.
- Requests go through a queue the requester can write to and screeners can read, holding
  targets only.
- Screeners read the target in their own space, against their own registers and
  knowledge, and record the verdict in the fixed shape. Notes go in their tier's store.
- Verdicts go back through the queue. A requester sees verdicts and nothing else.
- Every change to the target after a `clear` needs a fresh screen.

### Machine-assisted

The same flow, with a process doing the first pass for a human screener.

- **The screening process runs inside tier T.** It runs where T's material lives, with
  read access to T's registers, under the processing-location rules for T
  (`knowledge/spec_icip.md`, `knowledge/spec_ai.md`). An AI screener is only allowed
  where the community has allowed AI for T.
- **One context, one tier.** A screening agent starts fresh for each tier, loads only
  that tier's registers and the target, and is discarded after. It never carries a
  session into open work or into another tier. Open-tier agents never load a restricted
  register.
- **Egress filter.** Everything the screening process returns passes through a filter
  that accepts only verdict records in the fixed shape. Any other output, including free
  text, is dropped and logged in T. The filter also re-checks each outgoing record
  against T's register and refuses one that contains a registered term.
- **Pattern scan first, reading second.** A deterministic scan against T's register
  gives `hold` or `refer`. An agent's reading can add `hold` or `refer`. Neither can
  `clear` on its own. A human screener reviews and only a person's `read` verdict clears.
- **Logs stay in T.** What was screened, by what, and what it matched is logged in T's
  store only.

### Checks

- A **verdict schema check** at the egress filter (above).
- A **leak check** on every open build against every closed tier's register, run inside
  each tier the same way, returning verdicts only.
- A **separation check** on config: no screener, process or store serves two tiers that
  are closed to each other.

## Storage

A community may keep each tier in a separate place, such as its own repository with its
own access rules. The kit takes a path for each tier from the project's configuration
and reads only what the audience may see. It never writes one tier's material into
another tier's store, and never merges stores. How material moves between tiers is up
to the community's own process.

## Not decided yet

- The queue format for screening requests and verdicts, and where it lives.
- How many repeat screens of one target are allowed before it goes to a person.

- Descriptors for Local Contexts BC Labels and Notices, and for other schemes communities ask for.

- How a restricted tier refers to a general record without the general store holding
  any trace of the reference.
- Whether unread material should get a build of its own, so the people screening it can
  work with the tools.
- How search and the semantic index are split per audience.
