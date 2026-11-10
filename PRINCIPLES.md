# Operating principles

*Draft, 2026-11-07. Not settled until the project custodian accepts it.*

lect-kit is the public half of a set of tools for language revival. It has the data
structures, the scripts that build and check them, and notes on method. A community can
use it to compare a model of its language with what its speakers were recorded saying.
Apart from Japanese as a worked example, it contains no language.

The principles say how the kit is meant to work. Much of it isn't built yet.

When the kit refuses or blocks something, that's a default. A person can always decide
otherwise, and the kit keeps a note of who decided and why.

If anything else in the kit disagrees with these principles, the principles win.

## 1. Communities stay in control of their languages

A language belongs to its community. The community decides how it is modelled, taught,
written, classified and shared, who works on it, and what is done with the results. The
kit has no say in any of that. Code here must not make one of those decisions for a
community, and a default that suits one language's shape better than another's is a
bug.

Using the kit gives nobody authority over a language. That includes the people who
build the kit, the people who run it, and the agents that work on it. A model built with
lect-kit is a working tool for the community. It isn't a ruling on how the language
should be spoken.

## 2. Any account of a language describes a point in time

Living languages change. Sleeping languages can wake and grow again with new speakers.
A corpus records how particular people spoke at particular times and places. A model
built from it can only describe that record. It can't say how the language must be
spoken now or later.

So the kit records the circumstances of every account as well as the sources allow:

- When it was recorded or written.
- Where.
- Who spoke.
- Who recorded or wrote it down.

Many old sources leave some of these out or get them wrong. The kit records what is
known, says how it is known (stated in the source, inferred, or supplied by family or
community), and leaves a gap rather than guessing. Where the records disagree, it keeps
both.

A model, a measurement or a rendered table says which corpus and model version it came
from. Nothing the kit produces calls itself the correct or standard form. A form
that the corpus doesn't hold is described as unrecorded, never as wrong, and a
community is free to use it, change it or leave it.

## 3. No language content from the communities that use the kit

Nothing from the language of any community that uses the kit goes in this repository.
That means no words, forms, sentences, glosses, recordings, transcripts, page images,
place names, personal names or cultural knowledge. It applies to code, tests, comments,
commit messages, issues and docs.

The one real language in the kit is Japanese, as a worked example. It lives in
`examples/demo/japanese/` and is built from public-domain sources. Tests that need
something Japanese can't show use abstract fixtures in `examples/demo/fixtures/`, which
don't pretend to be a language at all. `examples/demo/README.md` explains why.

Don't copy anything in from a project that uses the kit, even to illustrate a point.
Work out the general idea and show it with the Japanese example or a fixture.

Speakers aren't named here. Thanking them is the job of each community's own materials.

Restricted terms aren't kept here either, not even as a list to check against. The
checker reads a community's list from that community's own checkout when it runs, and
never stores it or prints what it matched. [What goes in this repository](docs/content_rules.md) explains
more.

If you're not sure whether something counts, leave it out and ask the project custodian.

## 4. Classification runs through every layer

Communities restrict some knowledge to some people. A language's words, forms and
sentences can be restricted as well as its stories. The kit supports this as part of
the data model rather than as a filter added at the end.

- **The community defines its tiers.** The kit ships with no tier names and assumes no
  order between them. A community says which tiers exist and which tiers a reader of
  each one may see. Two tiers can be closed to each other.
- **Every record carries a tier.** That includes corpus spans, analysis records,
  lexemes, senses, rules, slots, constructions, links between lects, practice items and
  notes. A record without its own tier takes the tier of what contains it.
- **Each tier can hold a full model.** A tier can have its own corpus, lexemes, rules,
  constructions and outputs. A tier's model can build on the tiers its readers may see,
  never the other way round.
- **Each build is for one audience.** A build reads only the tiers that audience may
  see, and everything it produces is for that audience. The general build has to come
  out the same whether or not the restricted material is present.
- **A result is at least as restricted as what it came from.** A form built from a
  restricted lexeme is restricted, even if every rule that built it is general.
- **Checking open material doesn't leak what the checker knows.** Whoever screens
  open material for a restricted tier works inside that tier and sends back a verdict,
  never their reasons. Tiers closed to each other have separate screeners.
- **Unread is not general.** Material nobody has read yet has its own state, and no
  build uses it until someone has classified it.
- **Restricted material stays where the community keeps it.** The kit reads each tier
  from wherever the community stores it, and never copies one tier into a store meant
  for another.

The community decides what goes in which tier and who classifies it. The kit records
who classified each record, when, and on what basis. Reading the material counts as a
basis; matching it against a list of patterns doesn't.

## 5. Cultural and intellectual property stays with its community

Indigenous Cultural and Intellectual Property (ICIP) is a community's rights in its
language, knowledge and cultural expression. Those rights belong to the community as a
whole and last indefinitely. They don't depend on copyright. Material that is out of
copyright, or published long ago, can still carry them, and lect-kit's MIT licence
covers only the kit's own code and documents.

The kit is built to respect those rights wherever a community uses it. That draws on
published practice, including Terri Janke's True Tracks principles, the AIATSIS Code of
Ethics, the CARE principles and Indigenous data sovereignty principles.

- **Consent can be withdrawn.** A community can take material out at any time, and the
  kit rebuilds every output without it.
- **Credit goes in the outputs.** Tables, practice and exchange packages acknowledge the
  community and the knowledge holders, in the form the community chooses.
- **The community's own labels travel with its material,** such as Traditional
  Knowledge Labels and Notices, and appear wherever the material does.
- **Communities choose where their data is processed.** The kit can run entirely on a
  community's own machines. By default, no material goes to an outside service, an AI
  service included, unless the community has decided that it may.
- **Published outputs carry the community's terms,** including whether the material
  may be used to train AI. A notice can't stop every misuse, so the kit doesn't claim it
  can.
- **Everything published carries every reasonable control against AI training.**
  Unless the community has decided otherwise, each published set says in plain words
  that it may not be used to train AI, and carries every machine-readable signal and
  server rule the kit knows of: in the pages and files themselves, in `robots.txt` and
  similar files, and in server configuration such as `.htaccess`. The kit keeps that
  list current as conventions change.
- **People who have passed away are respected.** A community can withhold a person's
  name, voice or image from outputs, for a time or indefinitely, without reclassifying
  anything.
- **A community can ask for review before anything is published,** by people it
  trusts, as a setting it turns on.
- **Benefit stays with the community.** A community can take everything back out in
  open formats at any time. The kit doesn't make it easier to extract a community's
  material than to use it on the community's terms.

## 6. Everything here is public

The licence is MIT. Anything pushed can be copied, cached and used for training, and
deleting it later doesn't undo that. So someone reads every change in full before it's
committed, and runs `scripts/check_content.py` on it. Passing the checker is the minimum.
It only finds what it has been told to look for.

## 7. Keep the model and the record apart

The model of the language (the paradigm, a list of claims) and the corpus (what speakers
said) each load into one database. Neither reads the other. Anything we publish reads
the database. Because nobody lined the two up by hand, a gap between what the model
predicts and what was recorded is worth looking into. It may mean the model is wrong, or
the transcription, or that nobody happened to record the form.

The model holds claims and nothing else. No evidence, no statuses, no counts. Whether a
form is attested gets worked out from the corpus every time, never typed in.

The corpus is never edited to suit the model. If a recorder got something wrong, the
correction is added next to the original line.

Scripts should enforce these boundaries rather than leaving them to memory. A script
can only catch the crossings it can see, so the ones it can't see get written down.

## 8. Each language on its own evidence

A lect is a language under the name its speakers or community give it. Every lect is
modelled from its own evidence using the same structures, with no tables copied across
from a neighbour. lect-kit does not model a family tree. If two lects share something,
that is a claim, and it is written as a link with its evidence and a test that could
prove it wrong.

## 9. Custodians of related languages can share their paradigms, and talk

One aim of the kit is that the custodians of related languages can exchange paradigms,
so each can learn about the other's cognates. Neighbouring languages often fill each
other's gaps, and a word recorded on one side can point to where to look on the other.

Finding a possible cognate is the start of something, not the end. Strong languages and
good language resources come from communities talking among themselves and with each
other. A possible cognate is a reason for those conversations: between the custodians
of two languages, and within each community, with Elders, speakers, families and
learners. The kit can prepare for those conversations and keep a record of what people
decide. It can't have them, and it doesn't stand in for them.

- **Sharing is the sender's decision.** A community chooses what to send, to whom, and
  on what terms. By default only material in tiers that both communities have agreed to
  share goes into an exchange.
- **The terms travel with the paradigm.** An exchange package carries who sent it, when,
  which model version it is, and the sender's terms of use. The recipient's tools keep
  those terms with it and don't publish it further by default.
- **A received paradigm stays the sender's.** It is held as a model of the sender's lect,
  next to the recipient's own. Nothing from it is copied into the recipient's model. If
  the recipient takes up a word or a rule, that is a decision in their own model, and
  it records where the idea came from.
- **Cognates are claims to test, and talk about.** The kit can propose candidate
  cognates by comparing glosses and sound correspondences. Each proposal is a link with
  its evidence and a test that could prove it wrong. People decide whether it holds,
  after talking with the people who know each language. Nothing changes in either
  community's model because of a proposal alone.
- **Corpus stays home.** An exchange carries the model, plus attestation summaries if
  the sender chooses to include them. Recordings and transcripts don't go in an exchange
  package. A community that wants to share them does that its own way.

## 10. Fix the schema

When the data can't hold a fact, change the schema at the point where that fact is
decided. Don't guess it back from spellings or slot names, and don't add an override
file. A rule that gets the right answer for the wrong reason is still a bug.

## 11. Measure the fit and don't let it slip

We count how well the model fits the corpus. A change that makes any count worse is
refused by default. Each count says what it measures, what getting it to zero would mean, and what
it leaves out, so the exclusions can be checked. The baseline only moves when someone
records a decision to move it.

## 12. Say who made it

Every record someone authors says who made it (`kind: human` or `kind: ai`, which agent,
which task, the date) and whether it has been reviewed. An AI draft never passes as a
person's decision.

## 13. AI is optional, and community knowledge stays out of AI training

A community can do all of its work with the kit without AI. Every part of the kit works
for people working by hand, and nothing depends on an AI being available. Using AI to
help is a choice each community makes, for the parts of the work it chooses.

A community's knowledge, including its corpus and its paradigm, should stay out of the
data used to train AI models. That includes the models a community chooses to work
with. The kit's guide sets out how to keep it out, and by default the kit sends nothing
to an AI service.

AI agents wrote a lot of this kit and still do. The docs say what they do and what
people decide. Their changes get the same checks and the same read-through as anyone
else's. A passing check doesn't mean a person has looked at something, and we don't say
it does.

## 14. Stay in step with the projects that use it

The kit is only worth having if real projects run on it.

When a project finds a better way of doing something, it gets generalised here with the
demo language, and the project then upgrades to the new release. Projects don't patch
their own copy of the kit.

The kit never depends on a project that uses it. It doesn't know their paths, layout or
names.

Changes that would break a project get a new version number and migration notes.

Each project keeps its own principles and content rules. The kit supplies the tools
that carry them out.

## 15. Look after the record for the long term

A community's record of its language may be the only one there is, and the work built on
it takes years. The kit helps a community keep both safe for the generations who come
after.

- **Every change can be traced and undone.** The kit keeps a history of who changed
  what, when and why. By default nothing is changed without that record, and old
  versions aren't erased.
- **More than one copy, in more than one place.** The kit makes it easy to keep backups,
  and to check that they can actually be restored. Backups follow the same rules as
  everything else: each tier's backups stay with the people allowed to see that tier,
  and a backup kept with an outside service counts as sending material to that service.
- **Plain, open formats.** A community's material is kept in formats people can open
  without the kit, so it outlasts the kit and any company.
- **More than one person can look after it.** Access, passwords and the steps to restore
  are held by more than one trusted person, as the community chooses, so the work
  doesn't depend on one person.
- **The original record comes first.** Everything the kit builds can be rebuilt from the
  record and the model. The record itself, including original recordings and images, is
  what most needs protecting.
