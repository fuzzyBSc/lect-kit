---
type: Spec
title: Classification spec
description: Build detail for community-defined tiers, per-tier paradigms, per-audience builds and leak checks.
tags: [classification]
status: draft
generated: {by: agent:claude-opus-5.5, at: 2026-11-07T21:00:00+10:00}
---

# Classification spec

Agent-facing build detail for classification. Carries out `PRINCIPLES.md` §4. The human
explanation is `docs/classification.md`. If the two disagree, stop and raise it.

The register file, layered files, the audience database, the cross-tier scan, the proposal scan and the commit and push hooks are built so far.

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

### Layered files (built: `lectkit/layers.py`, `scripts/compose_layers.py`)

Every file format is layered. There's no separate overlay format. A tier that adds to a
file keeps a file **in the same form**, at the **same relative path and file name** in
its own store, naming the same records and holding only what it adds:

```yaml
# stores/fx-open/lexicon/fx-nouns.yaml
entries:
  - id: stemA
    senses:
      - {id: stemA-s1, gloss: glossA1}

# stores/fx-a/lexicon/fx-nouns.yaml (same path, same form)
entries:
  - id: stemA                  # the same lexeme
    senses:
      - {id: stemA-s2, gloss: glossA2}   # an added sense, tier fx-a
  - id: stemC                  # a whole new lexeme, tier fx-a
    senses:
      - {id: stemC-s1, gloss: glossC1}
```

- **Location decides the tier.** A record, sense or value takes the tier of the store
  whose file added it. A field inside a file that names a tier isn't read as one.
- **Order comes from the register.** Composing for an audience reads the file from the
  audience's own store and from every store its `sees` list names, and applies each tier
  after every tier it sees. Formats declare nothing about layering.
- **A higher layer only adds.** The rule is the same for every format:
  - a mapping key a lower layer lacks is added; one it has is merged if both values are
    mappings or both are lists, and must be equal otherwise;
  - in a list, a mapping with an `id` joins the lower item with the same `id` and merges
    into it; a new `id` is appended; any other item (a plain value, or a mapping
    without an `id`) is appended unless an equal item is already there.
  Nothing a lower layer holds is changed, reordered or removed. A differing value, or a
  value whose type differs from the one below, is an error. Restating an equal value adds
  nothing.
- **Ids.** Records, and sub-records a higher tier may extend or cite such as senses,
  carry an `id` (text or an integer) unique within their list. An id may not name a sense
  held at a higher tier. Composing can't check that, because a lower audience never
  loads the higher layer; the higher tier's own leak scan does.
- **Renames.** A record that replaces older ones lists their ids under `replaces`. Only a
  record a layer adds can carry `replaces`: a higher layer can't add it to a record a lower
  layer holds. In each layer and in the composed result, an id under `replaces` is an
  error if a record in the same list still uses it, or if two records claim it. A higher
  layer's item whose `id` matches no record but is claimed under `replaces` joins the
  claiming record. The old record doesn't point forward.
- **The result says each value's tier.** Composing returns the merged document and,
  for each record and value, the tier that added it, so every reader of a composed file
  treats an added sense as its own tier's.
- **An absent store is reported**, never passed: the view it gives is incomplete.
- **Files are read strictly** (`lectkit/yamlio.py`): a repeated key is an error, only
  `true`/`false` are booleans (so words like `no` and `on` stay text), and dates stay
  text.

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

### Audience database (built: `lectkit/audience_db.py`, `scripts/build_audience_db.py`)

A term register only finds material that names a restricted thing. It misses material
that describes one, and material copied from a tier's own records. So each audience builds
a database of **everything it can see**, with the tier of every value, and its leak scanner
queries that.

- **One audience, one database.** It's built from the audience's own store and every store
  its `sees` list names. A store in that list that's absent stops the build, because the
  database would then wrongly show material held below as if it weren't.
- **Two views of each file:**
  - `source_value`: every scalar, mapping key, comment and line of every file in every
    store read, with the store's tier, the file's relative path and the line number. This
    is what a scanner reports against.
  - `model_value`: every value, key and id as the composed model holds it (`Layered
    files`), with the tier that added it and the line where that tier's file writes it. Layered YAML files are composed, so a value a higher tier
    only restates keeps its lower tier. Other text files are layered too, line by line and
    paragraph by paragraph: copies at one path are one file, lowest tier first, and a line
    a lower copy already holds keeps that lower tier. Paragraphs let a passage that wraps
    across lines still match.
    Comments are read outside the spans of scalars, so a `#` inside a quoted or block
    scalar isn't taken for one.
  - `model_passage` holds every run of 5 consecutive normalised words in a model value,
    so a copied or lightly edited passage still matches.
- **Kit configuration isn't read.** The audience's own store keeps kit configuration and
  reports, such as accepted scan matches, in `.lectkit/`. The database doesn't read that
  folder. Every other store's `.lectkit/` is read like any other folder.
- **Store digests.** The database records a digest of every file it read from each store,
  by path and content, so a later step can tell when a store has changed.
- **Every row keeps its classification.** Every table has a `tier` column and every row
  carries a tier: a source row its store's, a model row the tier that added it, a passage
  the tier of the value it was cut from, a skipped file its store's. The database's own
  description (format, audience, tiers read) carries the lowest tier read, and the
  database as a whole is classified as its audience. A row whose tier the audience doesn't
  read, a table without a `tier` column, or a passage whose tier differs from its value's
  fails the build, and fails again whenever the database is opened.
- **Normalised text** (NFC, case-folded, whitespace collapsed) sits beside the original,
  so lookups don't depend on spelling case or Unicode form.
- **Keys.** Every mapping key is recorded at the tier that added it, because in a
  free-form mapping a key can be content.
- **What a leak looks like, for the scanner.** A value in a store of tier L that equals
  (or shares a passage with) model material added by a tier L can't see is a candidate
  leak. A value the higher tier only restates from below isn't its material, so it never
  matches. An ordinary word that both tiers hold on their own does match, and a person
  decides it, as with any spelling shared by an open and a restricted lexeme.
- **What a store holds.** In a store that is a git checkout of its own, the store's files
  are the ones git tracks plus new ones it doesn't ignore. Ignored files, such as editor
  folders, caches and build output, aren't part of it. Elsewhere every file is read.
- **Files.** A symbolic link anywhere in a store stops the build, and so does a YAML file
  with an alias or more than one document. A file that isn't UTF-8
  text stops it too, unless it's an image, audio or video file, which is counted and
  left out. A YAML file that doesn't parse or doesn't compose stops it. Errors name the
  store and file, never its content.
- **The database holds readable restricted text.** It's as restricted as the most
  restricted tier it holds, and it's ephemeral: it's built on request into a path
  outside every store in the register and outside any git working tree, written to a temporary file and moved into place
  only when complete, and never committed, backed up or copied.

### Cross-tier scan (built: `lectkit/scan.py`, `scripts/scan_tiers.py`)

The scan runs inside a higher tier, on that audience's database, and checks every lower
store in it for material that store's readers mustn't see.

- **For each store of tier L** in the database, the hidden tiers are the ones the
  database holds that L doesn't see. Hidden material is every model value, key and id
  those tiers added (at least 3 characters) and every five-word passage cut from it. A
  YAML file in L's store is read by its keys, scalars and comments, and any other file
  by its lines. A line **matches** when:
  - its whole text equals hidden material (`value`);
  - a run of up to 4 words in it equals a hidden value, key or id from structured data,
    such as an id inside a sentence (`token`). Prose lines and paragraphs aren't looked for
    inside other lines, because the words of a heading or a note aren't lexical items.
    They match whole or by passage; or
  - a five-word passage equals a hidden one, counting words across line ends, so a
    passage that wraps still matches. The finding is on the line where the passage
    starts (`passage`).
- **No exemptions are inferred.** Field names a hidden tier's new records share with the
  stores below (`senses`, `gloss`) match like anything else until a person accepts them.
  An exemption worked out from the lower store would let that store exempt a leaked term
  just by using it.
- **One finding per line.** A finding gives the tier and store, the file, the line, the
  kinds of match, and every hidden tier matched, most restrictive first. It never gives
  the text, from either side.
- **Accepted matches.** A person decides once that a matched item is shared, not leaked.
  Decisions are kept in the scanning tier's store, in `.lectkit/accepted_matches.yaml`,
  as a list of `{text, tier, reason, by, at}`. Here `text` is the matched item and `tier`
  is the lower tier whose stores the decision covers. A finding is accepted only when
  every item matched on its line is accepted. Only the scanning tier's own `.lectkit/` is
  left out of the database. A lower store's `.lectkit/` is read, scanned and digested
  like any other folder, so it can't hide material. Accepted findings are still counted
  and are listed with `--show-accepted`.
- **Reviewed findings.** When a person reviews a finding from the report and decides the
  lower entry is fine, `review_finding.py` saves that decision in the scanning tier's
  `.lectkit/reviewed_findings.yaml`, by the finding's id. It records the lower tier, the
  file, a digest of the lower text the finding covers (every line, for a passage that
  spans lines), which copy of that text in the file it is, keyed digests of the hidden
  items matched and their tiers, the reason, the person (`by: human:...`) and the time.
  A later scan clears that finding while all of these are unchanged, even if the entry
  moves to another line. The finding comes back for review in any of these cases:
  - the lower text changes, including a later line of a passage;
  - it matches a different hidden item;
  - a matched item moves to another tier;
  - the line is copied again.
  The same text in another file isn't covered.
- **Ids and review digests are keyed.** They're computed with a secret kept in the
  scanning tier's store (`.lectkit/scan_key`, as hex text), made on first use and never
  read into that tier's own database. Tiers above it can read it, as they can read the rest
  of its store. Without that key, someone holding a report couldn't confirm a guess at hidden
  text by recomputing an id. The review file and the key are as restricted as the
  scanning tier.
- **What a review proves.** `by: human:...` records who is responsible. It doesn't
  authenticate them: anything that can write the scanning tier's store could add a
  review. The guarantee is who can write that store.
- **Fresh or refused.** The database records a digest of every store it read. The scan
  recomputes them and refuses to run if any store has changed since the build.
- **Where the report goes.** The report is printed, or written under the scanning tier's
  own `.lectkit/` folder (which the database doesn't read, so the report can't make it
  stale) or outside every store. It is never written into a lower store, never committed
  there, and never pasted into a lower repository's pull request or issue.
- **Exit codes.** 0 means no unaccepted findings, 1 means findings, and 3 means the scan
  couldn't run (a stale database, or a bad accept file).
- **What it can't see.** Material written fresh in the lower store, which doesn't copy
  anything the higher tier holds, can't match. A scan that passes found nothing it was
  given to look for. It isn't a clearance.

### Proposal scan (built: `lectkit/proposal.py`, `scripts/scan_proposal.py`, `scripts/screen_for_tier.py`)

Before a commit lands in a store of tier L, every higher tier present on the machine
screens what L would hold after the commit.

- **The proposal is the whole staged tree**, not the diff: the tree `git write-tree`
  names, and every path in it, since file and folder names are published too. A leak already committed is caught with the new one, and everything a verdict
  mentions is part of what's proposed. The tree is exported **by name, blob by blob from
  the object store**, to a temporary folder outside every store, then scanned and
  deleted. Index flags (skip-worktree, sparse checkout), filters, encodings and
  line-ending settings therefore can't change what's scanned. The index can't change
  between naming the tree and exporting it, either. A symbolic link or a submodule in the
  tree stops the scan.
- **Higher tiers are every tier whose `sees` list names L.** For each one whose store is
  on the machine, a separate process (`screen_for_tier.py`) builds that tier's audience
  database in a temporary folder, with L's store replaced by the export, scans L's store
  only, and deletes the database. Tiers closed to each other are never screened in one
  process. A higher tier whose store is absent, or isn't a checkout of its own (an empty
  folder at that path, say), is a **gap**, reported by name, never a pass. Hooks run locally, by someone who holds the classified material they need, so a
  gap blocks: no evidence is written.
- **What crosses back is a verdict, filtered.** The runner accepts only
  `{screened_for, outcome, basis, by, at, tree, locations}` from each process, and drops
  anything else. `outcome` is `hold` or `no_match`. A pattern scan can't clear anything,
  so there's no `clear` (see "What crosses back" below). On `hold`, `locations` lists
  file and line in L's proposed tree, with nothing else, so the answer stays scoped to
  the proposal and adds no higher-tier material. A location must be a path in the
  proposed tree and a line from 1.
- **Evidence.** When every higher tier returns `no_match`, the runner writes an evidence record into L's git directory
  (`.git/lectkit/evidence/<tree>.json`), which is never committed. It holds the tree, the
  tiers screened, a digest of the register, a digest of each screened higher
  store and the time. The commit hooks (next) recompute the digests, so evidence goes
  stale when the register or a higher store changes.
- **What evidence proves.** It's an unsigned file that anything running as the same user
  could write. It shows that the scan ran. It doesn't stop someone who means to get round
  it, and the hooks treat it that way.
- **Process isolation, and its limits.** Each screen runs as its own Python process,
  started with `-E` so environment variables can't redirect it. (`-I` would also drop
  user site-packages, where the kit's dependencies may be installed.) Its temporary
  database lives in the system temporary folder and is deleted when the screen ends.
  Deletion is best effort: a killed screen can leave one behind, readable by the same
  user.
- **Exit codes.** 0 means every higher tier returned `no_match`. 1 means a hold. 2 means a
  higher tier wasn't screened. 3 means the scan couldn't run.

### Commit and push hooks (built: `lectkit/hooks.py`, `scripts/lectkit_hook.py`, `scripts/install_hooks.py`)

Hooks run locally, in each store's own checkout, and never on a server. Whoever runs them
holds the classified stores they need.

- **pre-commit** passes at once in a store whose tier no other tier sees (nothing there
  can be hidden from a tier above it). Otherwise it refuses unless there is current
  evidence for the staged tree. If there
  isn't, it runs the proposal scan, which writes evidence on a clean result, and then
  checks again. Another process can still change the index after the hook returns and
  before git writes the commit; the push hook screens every commit again, so that
  can't reach a remote.
- **Current evidence** for a tree means all of the following:
  - a record exists for that tree;
  - it names every higher tier, no more and no fewer;
  - the register's digest is unchanged;
  - each higher store is present, is a checkout of its own, and still has the digest
    recorded.
  A higher tier that adds material after the scan makes the evidence stale, and the
  tree is screened again.
- **pre-push** screens every commit being pushed that the remote doesn't already have,
  not just the last one. What the remote has is asked of the remote itself, not read
  from local tracking refs, which can be stale. If the remote can't be asked, every
  commit back to the root is screened. Each commit is screened afresh: its whole tree,
  plus the whole commit object as one more file. That covers the message, the author
  and committer names, embedded tag messages and signatures, decoded with the commit's
  own encoding. An annotated tag's whole object is screened the same way. All of these
  are published with the push. An update git sends that the hook can't read refuses.
  Any hold, gap or failure refuses the push. A store whose tier has `remote: none`
  refuses every push.
- **Installing.** `install_hooks.py` writes both hooks into a store's checkout. Each
  names the register, the store's tier and the kit by absolute path. It won't replace a
  hook it didn't write unless told to.
- **Limits.** A hook is a local check. These skip it:
  - `--no-verify`;
  - a `core.hooksPath` set elsewhere;
  - pushing from a clone without the hooks.

  It keeps an honest mistake from leaving a machine. It doesn't stop someone set on
  getting round it. In a linked worktree the checkout isn't the registered store, so
  every commit there is refused.

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
