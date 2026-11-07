# The demo

lect-kit needs examples and tests, and they can't use the language of any community that
uses the kit. That leaves two choices, and we use both.

## Why Japanese

We first planned a made-up demo language and dropped the idea. A made-up language goes
wrong in one of two ways.

If it borrows too much, it ends up resembling whatever its designer knows best, and for
this kit that's the language it was first built for. A made-up language with that
language's suffixes, verb classes and sound changes would be the same language in
disguise, which is exactly the leak the content rules are there to stop.

If it borrows too little, it's too tidy. Real languages have irregular verbs, sound
changes where pieces join, exceptions and spelling histories. Those are what show a
schema to be wrong, and a demo without them won't.

Japanese avoids most of both. It's unrelated to the languages the kit was built for,
and it works quite differently, so the example is unlikely to drift towards them.
It's real, so its mess is real too. Many people can read it and say when the example is wrong, and the
project custodian speaks it at an intermediate level.

It also fits what the kit does:

- Verb classes whose endings change by class, like the te and ta forms of godan verbs
  (書く → 書いて, 読む → 読んで).
- Suffixes that stack in a fixed order (食べ-させ-られ-たく-なかった), which is what the
  suffix-order tables are for.
- A historical spelling, the pre-1946 kana spelling (歴史的仮名遣い), which maps onto
  modern spelling by rules with exceptions, much as old recorders' spellings map onto a
  modern orthography.
- Old public-domain texts that can stand in for a historical record to test the model
  against.

lect-kit is not a tool for Japanese. The example is there to show how the structures
work.

## What the Japanese demo covers

To start with, only what can be checked:

- Modern standard Japanese verbs, adjectives and the copula. That means classes, endings
  and the order suffixes stack in.
- Converting historical kana spelling to modern spelling.
- A small corpus of short passages from public-domain texts (for example from Aozora
  Bunko), used as the record the model is tested against.

Pitch accent and regional dialects are left out until someone who can check them is
involved. Getting those wrong in public would be worse than leaving them out.

## Rules for the Japanese demo

- **Write the data, don't copy it.** Tables are written for this repository and checked
  against references. Modern dictionaries and reference grammars are copyrighted, and
  Wiktionary's tables are share-alike, so we cite them but don't take data from them.
- **Corpus text is public domain only,** and each passage names its source.
- **No Ainu or Ryukyuan material,** and nothing else whose content belongs to another
  Indigenous people. Being out of copyright doesn't free it of that community's rights.
- **Mark what's unchecked.** Anything an agent drafted that a person hasn't checked
  carries `review: open`, the same as any other AI draft. The project custodian checks
  as far as his Japanese goes. Anything beyond that stays marked unchecked until someone
  who can confirm it has.
- **The deny-list check runs here too.** Short Japanese syllables written in Latin letters
  could happen to spell a word from a community's language. The checker reports those
  matches so a person can look at each one, instead of skipping this folder.

## Abstract fixtures

Japanese can't show everything the kit needs. It marks subject and object with
particles, in a nominative-accusative pattern, so it has no ergative case. Its record is
large and well studied, so it doesn't show the problems of a sleeping language's record,
such as a few recorded speakers, a recorder's gloss that needs correcting, or a text a
missionary wrote rather than a speaker said.

For those, tests use fixtures in `fixtures/`. They don't try to look like a language.
Their forms are labels like `stemA`, `sfx-erg-1` and `speaker-1`, so they're unlikely
to resemble anything real. Each fixture says which mechanism it tests.
