"""Shared lists a tier can grant by reference: one versioned list of ordinary English and
project wording, approved once, granted in one line.

Project custodian's ruling, 2026-11-09 (knowledge/spec_classification.md, "One shared English
list, granted by version"):

- lect-kit keeps each version as a file in `lectkit/lists/<name>.txt`, one item per line. A
  version never changes once a tier grants it; a change is a new version.
- A tier grants a version by writing `list:<name>` as an item under the lower tier, in its own
  `.lectkit/accepted_matches.yaml`. The project custodian approves each version for every
  tier.
- The kit can't release a restricted word this way: every audience build refuses to run while
  any tier's term register matches an entry of any list.
"""
from __future__ import annotations

import re
from pathlib import Path

from lectkit import denylist

LIST_DIR = Path(__file__).resolve().parent / "lists"
REF = re.compile(r"^list:([a-z0-9][a-z0-9-]*)$")


class ListError(ValueError):
    pass


def names(list_dir: Path | None = None) -> list[str]:
    d = LIST_DIR if list_dir is None else list_dir
    return sorted(p.stem for p in d.glob("*.txt"))


def load(name: str, list_dir: Path | None = None) -> list[str]:
    p = (LIST_DIR if list_dir is None else list_dir) / f"{name}.txt"
    if not p.is_file():
        raise ListError(f"no shared list {name!r}")
    return [s.strip() for s in p.read_text(encoding="utf-8").splitlines()
            if s.strip() and not s.lstrip().startswith("#")]


def expand(items: list[str], list_dir: Path | None = None) -> list[str]:
    """`items` with every `list:<name>` followed by that list's entries. Granting a list
    releases the reference too, since every tier that grants it writes the same line."""
    out: list[str] = []
    for x in items:
        m = REF.match(x)
        out += [x] + (load(m.group(1), list_dir) if m else [])
    return out


def conflicts(reg, list_dir: Path | None = None) -> list[str]:
    """Each place a tier's term register matches a shared-list entry. Messages name the list,
    the entry's line and the tier, never the term."""
    out: list[str] = []
    lists = {n: load(n, list_dir) for n in names(list_dir)}
    for tid, t in reg.tiers.items():
        if not t.terms or not lists:
            continue
        try:
            pats = denylist.matchers([p for p in t.terms if Path(p).exists()])
        except SystemExit:
            out.append(f"{tid}: its term register can't be read, so shared lists can't be checked")
            continue
        for n, entries in lists.items():
            for line_no, entry in enumerate(entries, 1):
                if any(rx.search(entry) for rx in pats):
                    out.append(f"{tid}: shared list {n} entry {line_no} matches the tier's term register")
    return out
