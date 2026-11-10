---
type: Procedure
title: Feature procedure
description: How agent-written Gherkin features link specs to tests and code, the traceability and coverage checks, and where they run.
tags: [process]
status: draft
generated: {by: agent:claude-opus-5.5, at: 2026-11-07T19:00:00+10:00}
---

# Feature procedure

Agent procedure for showing that every test and every piece of code answers a stated
need. Carries out `PRINCIPLES.md` §6 and §13: changes are read through, and a passing
check isn't a person looking, so a person needs something to look at. People read
`docs/README.md` for what `features/` is.

*Project custodian's ruling, 2026-11-07:* tests and code must meet a business-level
need, so each is traceable to a Gherkin feature. The features are an affordance for
review, kept alongside the code and its tests.

## Layers

- **Specs** (`knowledge/spec_*.md`) stay, and stay freeform. They hold design and build
  detail and aren't restated as scenarios.
- **Features** (`features/*.feature`) are the next layer down, and they govern code and
  tests directly. One file per mechanism or output. Its description says who wants it,
  what and why, and names the spec section it carries out. Each scenario is one
  behaviour a person could check by hand: the *Given* is the state of the data, the
  *Then* is what appears in the file, output or exit code.
- **Tests and code** sit under the features.

## Writing them

- The agent writes the feature **before the code**, to show what it understood the ask
  to be. Mechanisms that were built before this ruling get their features now. Nothing
  is exempt.
- Each scenario carries a tag `@AC-<key>-<n>`, where `<key>` is the file's name
  (`tier_register.feature` → `@AC-tier_register-1`). Numbers are never reused.
- Every test names the tags it exercises in its docstring. A test that exercises no
  scenario either gets one, or is deleted.
- Scenarios use only the Japanese demo and the abstract fixtures (`content_procedure.md`).
- No Gherkin runner. The tags carry the link, and tests stay ordinary pytest.

## Checks

- **Traceability** (`scripts/check_feature_traceability.py`): it fails on a scenario
  with no tag or more than one, a tag that doesn't use its file's key, a tag used twice,
  a tag that no test names, a test that names no tag, and a test that names a tag that
  doesn't exist. Tests are found the way pytest finds them. Only test docstrings are
  read, so tag-shaped text elsewhere in a test file doesn't count.
- **Coverage**: coverage.py, a test-only dependency pinned in `requirements-test.txt`,
  configured in `.coveragerc`. `patch = subprocess` counts the scripts tests start as
  subprocesses, including the ones git runs as hooks in temporary repositories. Each
  process writes its own data file in the repository root, and `coverage combine`
  merges them. These files are git-ignored and never committed. The report fails below
  the floor in `.coveragerc`: 85% of the lines in `lectkit/` and `scripts/` was agreed,
  and it went to 90% once the features landed with coverage at 93%. It rises as gaps
  close and never falls.
  Every test is tagged, so code no test reaches is code with no stated need. It gets a
  scenario, or it's deleted.
- **Where they run:** both join the checks `CLAUDE.md` requires before a commit.
  `.github/workflows/checks.yml` runs the knowledge checks, the traceability check and
  the tests under coverage on every pull request and every push to `main`, on Linux and
  Windows. The content checker stays local, because its deny-lists belong to each
  project and never reach this repository or its CI.

## Not decided yet

- Whether the floor later counts branches as well as lines.
