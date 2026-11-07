---
type: Spec
title: Exchange spec
description: Build detail for paradigm exchange packages, cognate proposals, and the conversation sheets and records that follow them.
tags: [exchange, paradigm]
status: draft
generated: {by: agent:claude-opus-5.5, at: 2026-11-07T00:00:00+10:00}
---

# Exchange spec

Agent-facing build detail for paradigm exchange and cognate proposals. Carries out
`PRINCIPLES.md` §9. The human explanation is `docs/exchange.md`. If the two disagree, stop
and raise it.

How the custodians of related languages can share paradigms so each can learn about the
other's cognates. None of it is built yet.

## What an exchange package holds

A package is a set of files the sender's tools write and the recipient's tools read. It
holds:

- **A header:**
  - the sending community and lect
  - the date, and the model and corpus versions it came from
  - which tiers it includes
  - the sender's terms of use
  - a contact for questions
- **The lect's paradigm** for the included tiers: lexemes with their glosses and senses,
  classes, slots, allomorph and suffix-order rules, phonology, and constructions.
- **Optionally, attestation summaries:** for each cell, whether it is recorded or built,
  and how many times it was recorded. No utterance text, speaker names or anchors, unless
  the sender chooses to include them.
- **Optionally, the sender's own cognate links** to other lects, with their evidence.

The package never holds recordings, transcripts or page images. A community that wants
to share those does it its own way.

The format is the same schema the kit uses inside a project, so a package can be read
with the same tools. Glosses are in a contact language both sides read. That's often
English, but the communities choose.

## Sending

1. The sender picks the tiers and the recipients. By default the tools offer only tiers
   the sender has marked as shareable with that recipient.
2. The tools build the package for that audience, the same way as any other build
   (`knowledge/spec_classification.md`), and run the general-build test and leak checks on it.
3. A person from the sending community reviews it and sends it. The tools don't send
   anything on their own.

## Receiving

The recipient's tools store the package as the sender's lect, with its header,
alongside the recipient's own model. In a recipient's project:

- The received paradigm can be browsed and its tables rendered, labelled with the
  sender's lect, version, date and terms.
- Nothing in it joins the recipient's own corpus or model. Measures of fit for the
  recipient's lect don't count it.
- It isn't included in anything the recipient publishes unless the terms allow that and
  a person decides to do it.
- A newer package from the same sender replaces the older one. The old one is kept for
  reference, labelled with its date.

## Finding cognates

With two lects' paradigms side by side, the kit can propose candidate cognates:

1. **Gloss matching:** pairs of lexemes whose glosses or senses overlap.
2. **Sound correspondences:** pairs whose forms differ in ways a stated correspondence
   between the two lects predicts. Correspondences are claims too, each with its
   evidence and a test that could prove it wrong.
3. **Shared grammar:** classes, suffixes or constructions with matching shapes and
   functions.

Each candidate is a proposed link with the evidence that suggested it, at
`status: proposed`. A proposal is never treated as a fact about either language, and
nothing in either community's model changes because of one.

## Conversations

A candidate is an input to conversations between people, within a community and
between communities. The kit supports those conversations and records their outcomes.
It doesn't run, schedule or stand in for them.

### Conversation sheets

- For one candidate or a group, generate a sheet for people (`docs/`-style plain
  language, printable). It holds:
  - the two forms side by side, with what each side's record and model hold (from the
    package's attestation summary on the other side, if included)
  - why the kit proposed them
  - open questions (meaning, use, whether both sides knew it, borrowing or chance,
    anything needing care)
  - labels and tier markings from either side
- A sheet is built for one audience, like any build. A sheet for a conversation with
  another community includes only what both sides' sharing settings allow.
- Within-community sheets are allowed to include material the other side hasn't shared
  with that community, but never material the other side sent under terms that forbid it.

### Conversation records

- A **conversation record** has: candidate IDs, `held_with` (which communities, and
  participants only as the community chooses to record them), `at`, outcomes per
  candidate, open questions, and follow-ups. Outcomes are written by `human:` actors
  only.
- Outcome per candidate: `agreed`, `not-cognate`, `open`, `withdrawn` (one side asks
  that it not be pursued), each with the community's own words as free text. The free
  text stays in the tier of the conversation's audience.
- A candidate's status moves only from a conversation record: `proposed` to `agreed`,
  `not-cognate` (kept with the reason so it isn't proposed again) or `withdrawn`. `open`
  leaves it proposed and listed as under discussion.
- Each community keeps its own record of a joint conversation. The kit can prepare a
  shared summary for both sides to agree on, and each side stores what it agrees to.
- A change to a model that came out of a conversation records the conversation ID as
  its origin (alongside the package it came from). It still never counts as evidence.

### Agents

- Agents may draft sheets and candidate lists. They don't write outcomes and don't mark
  a candidate agreed or rejected.
- Agents don't contact other communities. Any message to another community is prepared
  for a person to send.

A correspondence that keeps failing is reported, so the person maintaining it can see
where it breaks.

## Using what you learn

When a cognate points to a gap in your own record, it tells you where to look. The kit
can list, for each confirmed link:

- whether your own corpus has the word
- which cells your model builds for it
- what the sender's attestation summary says, if they included one

If you decide to add a word or rule to your own model because of a cognate, that's your
decision, made in your own model. The record says where the idea came from and links to
the package it came from. It doesn't count as evidence in your lect. Only your own
corpus can attest a form in your language.

## Sending feedback

The recipient may want to tell the sender about a correspondence, a likely gap or a
possible error. The kit can write those up as a note to the sender, with the evidence
from the recipient's side that the recipient chooses to share. The sender decides what
to do with it.

## Not decided yet

- The conversation record format, and how two communities reconcile their records of a joint conversation.
- Whether sheets should support languages other than the contact language, for conversations held in language.

- How the terms of use are written, so they can be read by people and checked by tools.
- How shareable tiers are declared per recipient.
- How lexeme IDs stay stable across versions of a package.
- Whether two communities can maintain shared correspondence links together, and who
  holds them.
