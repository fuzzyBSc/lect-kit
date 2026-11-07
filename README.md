# lect-kit

Data structures and tools for checking a model of a language against what its speakers
were recorded saying. It grew out of work on one group of Aboriginal languages and is
being generalised so other languages' projects can use it. It holds no community's
language.

Each community keeps its own recordings, model and teaching materials in its own
repository and uses lect-kit for the structures and the checks.

It's early days. The principles and content rules are drafted. No code has been
moved in yet.

- [Operating principles](PRINCIPLES.md): what the kit is for and what stays in a
  community's hands.
- [The guide](docs/README.md): how the kit works, classification, cultural and
  intellectual property, using AI or not, sharing with related languages, keeping
  material safe, and what goes in this repository.

Agents working on the kit keep their specs and notes in [knowledge/](knowledge/README.md).

## What it will do

- Keep a community's record of its language and its model of the language apart, and
  compare them, so gaps between the two show up.
- Work out every word form the model predicts, and mark each one as recorded or built.
- Read old spellings into a modern spelling, with a set of rules for each source.
- Count how well the model fits the record, and by default refuse changes that make the
  fit worse.
- Carry a community's classification through everything, with a separate build for each
  audience.
- Respect a community's cultural and intellectual property: withdrawal, credit, its own
  labels, local processing, terms on published pages, and care for people who have
  passed away.
- Let the custodians of related languages share models on their own terms and find
  cognates.
- Work entirely without AI. Communities that choose to use AI can keep their knowledge
  out of AI training, and nothing goes to an AI service by default.
- Keep a history of every change, backups per tier with restore checks, and formats
  that outlast the kit.
- Produce word-form tables, checked sentences for learners, practice, and a checker for
  proposed sentences, each saying where its material came from.

The [guide](docs/README.md) explains each of these.

## Examples

The worked example is Japanese, built from public-domain texts. lect-kit isn't a tool for
Japanese. We chose it because it is a language the project custodian speaks and can
check, and it has a large speaker population that will not be affected by any errors
here. It is also very different from the languages the kit was first built for. Some
tests also use abstract data that isn't a language. [The demo page](examples/demo/README.md) explains why.

MIT licence, with an ICIP notice. See [LICENSE](LICENSE).
