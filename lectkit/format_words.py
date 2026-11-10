"""The words lect-kit's schemas declare: field names, and the values a field's enumeration fixes.

Project custodian's ruling, 2026-11-08 (knowledge/spec_classification.md, "Format words need
no grant"): a field name the kit's schema declares, or an enumeration value it declares,
belongs to lect-kit and not to any tier, so no higher tier has to grant it before a lower
tier may write it. Everything a tier writes *into* a field stays the tier's material.

The exemption is narrow by position. A declared field name is format only where it is a key.
A declared value is format only where it is the whole value of a field whose range is that
enumeration. The same word in prose, a comment, an identifier or a gloss is material as
before.

lect-kit gets no power to declassify on its own (project custodian's ruling, 2026-11-08).
`conflicts()` checks every tier store on this machine, and the audience build refuses to run
while any format word is material in one:

- a term or pattern in a tier's term register matches it, or
- a tier writes it as an identifier.

A clash is fixed by renaming the field or value in the kit, or by the tier withdrawing the
term. It is never fixed by narrowing this check.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import re

from lectkit import denylist, yamlio

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas" / "linkml"


@dataclass(frozen=True)
class FormatWords:
    keys: frozenset[str] = frozenset()                     # declared field names
    values: dict[str, frozenset[str]] = field(default_factory=dict)  # field -> enum values
    patterns: dict[str, tuple] = field(default_factory=dict)  # field -> patterns of its format types

    def all_words(self) -> set[str]:
        return set(self.keys) | {v for vs in self.values.values() for v in vs}

    def is_key(self, k: object) -> bool:
        return isinstance(k, str) and k in self.keys

    def is_value(self, own: object, v: object) -> bool:
        if isinstance(own, str) and isinstance(v, str) and any(
                rx.fullmatch(v) for rx in self.patterns.get(own, ())):
            return True                   # a hash: no knowledge in it
        return isinstance(own, str) and isinstance(v, str) and v in self.values.get(own, ())


def load(schema_dir: Path | None = None) -> FormatWords:
    """Field names and enumeration values from every LinkML schema in `schema_dir`."""
    schema_dir = SCHEMA_DIR if schema_dir is None else schema_dir
    enums: dict[str, set[str]] = {}
    slots: dict[str, set[str]] = {}       # field name -> ranges declared for it
    fmt: dict[str, re.Pattern] = {}       # type name -> pattern, for non-material types
    for p in sorted(schema_dir.glob("*.yaml")):
        d = yamlio.load_file(p) or {}
        for name, e in (d.get("enums") or {}).items():
            enums.setdefault(name, set()).update(str(v) for v in ((e or {}).get("permissible_values") or {}))
        for name, ty in (d.get("types") or {}).items():
            ty = ty or {}
            if ty.get("pattern") and (ty.get("annotations") or {}).get("lectkit_material") is False:
                fmt[str(name)] = re.compile(str(ty["pattern"]))
        defs = [d.get("slots") or {}]
        for c in (d.get("classes") or {}).values():
            c = c or {}
            defs += [c.get("attributes") or {}, c.get("slot_usage") or {}]
        for block in defs:
            for name, spec in block.items():
                r = (spec or {}).get("range") if isinstance(spec, dict) else None
                slots.setdefault(str(name), set()).update([r] if r else [])
    values = {}
    for name, ranges in slots.items():
        vs = set().union(*(enums.get(r, set()) for r in ranges)) if ranges else set()
        if vs:
            values[name] = frozenset(vs)
    # A field is format-typed only if every range declared for it is a non-material type.
    patterns = {n: tuple(fmt[r] for r in rs) for n, rs in slots.items() if rs and rs <= set(fmt)}
    return FormatWords(frozenset(slots), values, patterns)


def conflicts(reg, words: FormatWords | None = None) -> list[str]:
    """Each way a format word is material in a tier store on this machine. Empty is clean.

    Messages name the format word (lect-kit's own, public vocabulary) and the tier, never
    the tier's term."""
    words = words or load()
    vocab = sorted(words.all_words())
    out: list[str] = []
    for tid, t in reg.tiers.items():
        if not t.terms:
            continue
        try:
            pats = denylist.matchers([p for p in t.terms if Path(p).exists()])
        except SystemExit:
            out.append(f"{tid}: its term register can't be read, so format words can't be checked")
            continue
        for w in vocab:
            if any(rx.search(w) for rx in pats):
                out.append(f"{tid}: the format word '{w}' matches the tier's term register")
    return out
