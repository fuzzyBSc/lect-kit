---
type: Spec
title: Workflow spec
description: Build detail for the corpus, paradigm, join, rendering, constructed speech, practice and checking stages.
tags: [corpus, paradigm, rendering, practice]
status: draft
generated: {by: agent:claude-opus-5.5, at: 2026-11-07T00:00:00+10:00}
---

# Workflow spec

Agent-facing build detail for the workflow. Carries out `PRINCIPLES.md` §2, §4, §7 and §11.
The human explanation is `docs/workflow.md`. If the two disagree, stop and raise it.

How lect-kit is meant to work end to end. None of it is built in this repository yet.
The design comes from a working project, and this page describes it without that
project's language or its file names. Where a part is still undecided, the page says so.

There are seven stages. The first three build the model and test it against the record.
The last four use the result.

1. Corpus: what speakers said, as recorded.
2. Paradigm: the model, a set of claims about the language.
3. The join: every form the model predicts, checked against the corpus.
4. Rendering: paradigm tables a reader can look at.
5. Constructing new speech from the model.
6. Learner practice.
7. Checking proposed speech.

Every output of stages 3 to 7 is stamped with the corpus and model versions it came from
(`PRINCIPLES.md` §2). It describes that record at that point. It never says how the
language should be spoken.

Every stage runs for one audience at a time (`PRINCIPLES.md` §4, `knowledge/spec_classification.md`).
An audience is a classification tier plus the tiers its readers may see. The build loads
only that audience's corpus and paradigm and writes its own outputs, so a general build
never touches restricted material. Each stage below works the same way for every
audience.

## 1. Corpus

A corpus is a set of documents, one per recording or written source. Each is a text file
with metadata at the top. The metadata covers:

- What the source is and under what conditions it was made.
- When and where it was recorded or written.
- Who spoke, and which lect each speaker spoke.
- Who recorded or wrote it down.
- A default classification tier and how it was decided. Spans with a different tier are
  listed in the document itself.

Date, place, speaker and recorder are recorded as well as the source allows. Each says
how it is known (stated in the source, inferred, or supplied by family or community).
An unknown is left empty rather than guessed. Where records disagree, both are kept.

Each line or passage has a stable anchor, such as a timestamp in a recording or a minted
ID in a written source, so anything can cite it exactly.

The recorded text is never edited to suit the model. When a recorder's gloss, spelling or
word division is wrong, the correction goes in an analysis block next to the original,
with a date and a reason. The analysis layer can also say which word a token is, and
which role it plays in a sentence.

The build reads the corpus into three tables in an ephemeral database, rebuilt from
the sources on every build and never stored or backed up (`knowledge/spec_storage.md`). They hold documents, utterances
(with anchor, speaker, lect, text and translation) and tokens (with the written form, a
normalised matching key and, if known, the lexeme).

Not decided yet: the exact anchor scheme for written sources, and how much of the
recording metadata is required rather than optional.

## 2. Paradigm

The paradigm holds claims only. No evidence, statuses or counts go in it. It has:

- **A lexeme register.** One row per word, with an ID, a headword, glosses, part of
  speech, and which lects it is expected in.
- **Classes.** Inflection classes, with any subtypes conditioned by a stem's shape.
- **Slots.** Each slot is a named list of parts (the stem plus the suffixes it takes).
  Optional fields say which allomorph applies and which host it attaches to.
- **Allomorph rules.** Which shape a suffix takes in which environment.
- **Suffix order.** Which suffixes may follow which, so stacked forms are built rather
  than listed.
- **Phonology.** Allowed sound sequences, and how forms are spelled and split into
  syllables.
- **A lect register.** The named languages being modelled. lect-kit doesn't model a
  family tree.

Each record carries a classification tier. A tier can hold its own lexemes, senses,
rules, slots and constructions in its own store, building on the tiers its readers may
see. A cell's tier combines the tiers of its lexeme and of every rule that built it.

A generator reads the paradigm and writes out every predicted form. Each form is a cell,
keyed by (lexeme, slot, lect). Each cell records the form and the rule steps that built
it, so a wrong form can be traced to the rule that made it. A cell with no form means no
rule produced one.

Not decided yet: the schema details. The working project's tables were shaped around its
own language and will need generalising (see `PRINCIPLES.md` §10).

## 3. The join

The join compares each predicted cell with the corpus tokens in the same lect. Matching
uses the normalised key, so differences in hyphens or spelling conventions don't block a
match, but a match needs the same sequence of sounds.

A cell starts as `unexamined`. The join can move it to one of these:

| Status | Meaning |
|---|---|
| `attested` | A token in the corpus matches, and the cell points to the utterance |
| `impossible` | The form breaks a phonotactic rule or a recorded restriction |
| `not_predicted` | The model doesn't produce this cell |
| `unattested` | A person has looked and decided the form is genuinely unrecorded. Only a person can set this |

When the evidence points elsewhere, the cell stays `unexamined` with a note saying why.
The working project checks in this order:

1. A recorder's gloss or an analysis block names a different word or slot.
2. A glosser has named this lexeme. That settles it.
3. Several cells build the same spelling. The reading closest to the corpus's own word
   division wins, and is marked as chosen that way.

The results go back into the database. Counts of how many tokens the model can place,
and how many cells are attested, are what the scoreboard measures.

## 4. Rendering

The first rendering is paradigm tables, one per lexeme or class. They are generated from
the database and never written by hand.

- Each cell shows the form, and whether it is recorded, built by the model, or not
  predicted. Recorded and built cells look different.
- A recorded cell can be opened to show the utterance it comes from, with the form
  highlighted, the translation, who said it, the lect and the anchor.
- A built cell can be opened to show the rule steps that made it.
- Every table says which corpus and model version it was built from.

The page is plain HTML with the table data inlined. Row and column labels come from the
slot definitions, not from code, so another language gets its own labels. By default the
build fails if a slot in the model has no row in the table. That way a table can't silently
leave cells out.

## 5. Constructing new speech

Learners need sentences nobody was recorded saying. The kit allows that within limits,
and every constructed sentence shows how it was made.

A constructed sentence is a block with its text, a gloss, the lect it is in, and a
**frame**. The frame is a recorded utterance whose shape the sentence borrows. If there
is no frame, the block has to say why.

The build checks every word in the declared lect:

1. If the corpus has the word in that lect, it is `recorded`.
2. Otherwise, if a paradigm cell in that lect builds it, it is `built`.
3. Otherwise, if it's a bare headword in the register, it is `headword`.
4. Otherwise it is `unplaced`, and by default the sentence isn't published.

A word recorded in another lect but not in the declared one isn't counted as support
for this sentence. The build writes the analysis back into
the block, so when the model or corpus changes, the change shows up in the block.

Grammar patterns (constructions) say which roles a sentence has and how each is marked.
They can check that a constructed sentence follows a recorded pattern. In the working
project they check recorded and flashcard sentences, but not constructed ones yet.

What this doesn't check: whether the sentence means what its gloss says, whether its word
order is natural, or whether anyone would say it. Passing means every word is placed and
the frame resolves. It doesn't mean a speaker approved the sentence.

## 6. Learner practice

Practice items are built only from sentences and forms that have already passed the
checks in stages 3 and 5. The item types include:

- Choosing the meaning of a sentence.
- Building a sentence from its words.
- Typing or saying a form from a paradigm table.

Every item tells the learner where its answer came from: recorded (with who said it and
when), built from the model, or constructed. A drill can be limited to recorded forms
only.

Answer checking compares normalised keys, so it accepts different hyphenation. It tries
the learner's own lect first. An answer that's right for a neighbouring lect, or right
apart from where the word is divided, gets its own feedback instead of being marked
wrong.

Practice never tests a learner on a form a person has marked as not expected in their
lect. How and with whom practice is used is each community's decision.

## 7. Checking proposed speech

Anyone can put a word or sentence to the checker and get a report for each word:

- Which paradigm cells build it, with their lexeme, slot and lect. If several cells
  build it, the word is flagged as ambiguous.
- How often the corpus has it in each lect, with citations.
- Whether it matches a headword in the register.
- If none of these, that it is unplaced.

The report doesn't give a score or say whether a sentence is grammatical. It shows what
supports each word and what doesn't, and leaves the judgement to the person asking. A
word the model can't place may still be good language, because the model and the corpus
are both incomplete.

## Build order

1. Read the corpus into the database.
2. Build the corpus's form index.
3. Generate the paradigm cells.
4. Run the join.
5. Load the results.
6. Stage constructed sentences and run their checks.
7. Build practice items.
8. Render tables and pages.

Each stage declares which layer it belongs to and what it may read. A stage that reads
outside its layer gets reported. The working project builds into a temporary database
and only replaces the live one when every stage passes.
