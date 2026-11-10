# CLAUDE.md for lect-kit

Notes for agents working here. Read `PRINCIPLES.md` first. Where this file and the
principles disagree, follow the principles.

## What this repository is

The public part of a set of tools for language revival. It has data structures, the
scripts that build and check them, and notes on method, and it contains no language.
Language projects use it from their own repositories.

## Rules

Agent knowledge lives in `knowledge/`. Read `knowledge/README.md` first, then
`knowledge/content_procedure.md` before changing anything, and the matching
`knowledge/spec_*.md` before building a part. Keep those files current as you work
(gardening rules in `knowledge/README.md`). `docs/` is for people. Don't put agent
procedure or build detail there, and when a change affects what a person needs to know,
update the matching `docs/` page in plain language. In short:

- Don't bring a word, form, sentence, gloss, name or identifier in from a language
  project or anywhere else. That includes commit messages and pull requests.
- Examples use the Japanese demo in `examples/demo/japanese/`, and tests can also use
  the abstract fixtures in `examples/demo/fixtures/`. Read `examples/demo/README.md`
  before adding to either.
- Restricted-term lists stay in the project that owns them. The checker reads them from
  there when it runs. Never write one into this repository.
- The repository is public, so read the whole diff and run
  `python scripts/check_content.py` with the project's deny-lists before committing.
  A pass means the checker found nothing it was told to look for.
- Every markdown file in `knowledge/` carries OKF frontmatter (profile in
  `knowledge/README.md`), and identifiers follow the rule there. Before committing, also
  run `python scripts/check_knowledge_frontmatter.py`,
  `python scripts/check_knowledge_refs.py` and `python scripts/check_identifiers.py`.
- Every test and every piece of code traces to a scenario in `features/`, written before
  the code (`knowledge/feature_procedure.md`). Specs stay freeform above the features.
  Before committing, also run `python scripts/check_feature_traceability.py` and the
  tests under coverage (`python -m coverage erase`, then
  `python -m coverage run -m pytest -q tests`, `python -m coverage combine -q` and
  `python -m coverage report`, which fails below the floor). Install what they need
  with `python -m pip install -r requirements-test.txt`. CI runs the same on every pull
  request.
- Never push from here to a community's repository, and don't add one as a remote.
  Material moves between them only by the community's own process.
- No destructive git commands. Reading history with git is fine.
- Commit or push only when the project custodian asks.
- Code here can't import from a language project or name its paths. The kit defines a standard layout instead: each format's schema names the file name patterns that hold it, as a starting point for every project. A project adds to it in `.lectkit/formats.yaml` for files the patterns don't cover, and can't give a file a different format from the one its pattern names. (Project custodian's ruling, 2026-11-08.)
- SQLite and any other database is ephemeral. Never store a fact only in a database,
  never commit, back up or export one. Write to a source file and rebuild
  (`knowledge/spec_storage.md`).
- AI is optional. Nothing you build may need an AI to run or to pass its tests, and every
  AI-assisted step needs a documented manual route (`knowledge/spec_ai.md`).

## How work usually goes

Most jobs start with something that already works in a language project.

1. Find it there and note what about it is specific to that language.
2. Design the general version, schema first and code second.
3. Build it here and test it with the Japanese demo or a fixture.
4. Switch the project over to the released version, then delete its own copy once its
   checks pass. That last step happens in the project's own checkout.

## Words we use

The person leading the project is the project custodian. Use both words every time.
Cite rulings as *Project custodian's ruling, <date>*.

A lect is a language under the name its speakers or community give it.
