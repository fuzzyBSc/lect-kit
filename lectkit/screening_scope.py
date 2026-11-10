"""A screening-only tier holds only what the scan matches, and no prose.

Project custodian's rulings, 2026-11-09 (knowledge/spec_classification.md, "Gendered tiers
hold only what screening needs"). A tier the register marks `scope: screening` keeps its term
registers and its paradigm layer rows. Its research notes live elsewhere, and it writes no
project boilerplate: a comment, a label or a note in its files is prose that every tier below
would have to clear, and only that tier's own group could clear it.

`problems()` lists each breach by file and line, never by its text.
"""
from __future__ import annotations

from pathlib import Path

from lectkit import yamlio

KIT_DIR = ".lectkit"
# The keys a term-register entry needs for matching; anything else is prose.
TERM_KEYS = {"id", "variants", "pattern", "suffix_guard", "case_sensitive", "scope",
             "enforced", "register_name"}
YAML_SUFFIXES = {".yaml", ".yml"}


def problems(paths: list[str], read, term_files: set[str], excluded) -> list[str]:
    """Breaches in `paths` of a screening-only tier; `read(rel)` gives a file's text."""
    out: list[str] = []
    for rel in sorted(paths):
        if rel.startswith(f"{KIT_DIR}/") or excluded(rel):
            continue
        suffix = Path(rel).suffix.lower()
        if suffix not in YAML_SUFFIXES:
            out.append(f"{rel}: only YAML term registers and paradigm layers belong in a "
                       f"screening-only tier; notes live in the project's restricted folder")
            continue
        text = read(rel)
        for n, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("#"):
                out.append(f"{rel}:{n}: a comment; record a ruling as a field, not prose")
        if rel in term_files:
            doc = yamlio.load(text) or {}
            for i, e in enumerate(doc.get("entries") or [], 1):
                extra = sorted(set(e) - TERM_KEYS) if isinstance(e, dict) else []
                if extra:
                    out.append(f"{rel}: entry {i} has prose fields {extra}; only matching "
                               f"keys belong here")
    return out
