"""An audience's database of everything it can see, with the tier of every value.

Carries out knowledge/spec_classification.md, "Audience database". The database holds
readable restricted text: it's as restricted as the most restricted tier in it, built
outside every store, and ephemeral.
"""
from __future__ import annotations

import os
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from lectkit import layers, yamlio
from lectkit.tiers import Register

FORMAT = "1"
PASSAGE_WORDS = 5
YAML_SUFFIXES = {".yaml", ".yml"}
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".wav", ".mp3", ".flac", ".ogg",
                  ".m4a", ".mp4", ".webm"}

SCHEMA = """
-- Every table has a `tier` column, and every row carries the tier its content belongs to.
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL, tier TEXT NOT NULL);
CREATE TABLE source_value (
  tier TEXT NOT NULL, rel TEXT NOT NULL, line INTEGER NOT NULL,
  kind TEXT NOT NULL,            -- key | scalar | comment | line
  text TEXT NOT NULL, norm TEXT NOT NULL);
CREATE TABLE model_value (
  id INTEGER PRIMARY KEY, rel TEXT NOT NULL, path TEXT NOT NULL,
  kind TEXT NOT NULL,            -- id | key | scalar | comment | line | paragraph
  text TEXT NOT NULL, norm TEXT NOT NULL, tier TEXT NOT NULL,
  line INTEGER);                 -- where the adding tier's file writes it, if known
CREATE TABLE model_passage (norm TEXT NOT NULL, value_id INTEGER NOT NULL, tier TEXT NOT NULL);
CREATE TABLE skipped_file (tier TEXT NOT NULL, rel TEXT NOT NULL);
CREATE INDEX source_norm ON source_value (norm);
CREATE INDEX model_norm ON model_value (norm, tier);
CREATE INDEX passage_norm ON model_passage (norm, tier);
"""


class BuildError(ValueError):
    pass


def normalise(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def passages(text: str) -> Iterator[str]:
    w = re.findall(r"\w+", normalise(text))
    for i in range(len(w) - PASSAGE_WORDS + 1):
        yield " ".join(w[i:i + PASSAGE_WORDS])


def store_files(tier: str, store: Path) -> Iterator[Path]:
    """Every file in a store, outside .git. A symbolic link anywhere is an error: it could
    pull in material from outside the store, or hide material the walk wouldn't reach."""
    for root, dirs, files in os.walk(store, followlinks=False):
        rp = Path(root)
        if rp == store:
            dirs[:] = [d for d in dirs if d != ".git"]
        for name in dirs + files:
            if (rp / name).is_symlink():
                raise BuildError(f"{tier}: {(rp / name).relative_to(store).as_posix()}: "
                                 f"symbolic links aren't allowed in a store")
        dirs.sort()
        for name in sorted(files):
            yield rp / name


def _walk(node: Any, path: tuple) -> Iterator[tuple[tuple, Any]]:
    yield path, node
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk(v, path + (k,))
    elif isinstance(node, list):
        for i, item in enumerate(node):
            step = ("id", item[layers.ID]) if isinstance(item, dict) and layers.ID in item else ("#", i)
            yield from _walk(item, path + (step,))


@dataclass
class BuildReport:
    audience: str
    tiers: list[str] = field(default_factory=list)
    files: int = 0
    skipped_media: int = 0
    source_values: int = 0
    model_values: int = 0


def _inside_a_store(reg: Register, out: Path) -> str | None:
    o = out.resolve()
    for t in reg.tiers.values():
        if t.store_path is not None and (o == t.store_path or t.store_path in o.parents):
            return t.id
    for d in o.parents:
        if (d / ".git").exists():
            return f"a git working tree at {d.name}"
    return None


def build(reg: Register, audience: str, out: Path) -> BuildReport:
    """Build `audience`'s database into the SQLite file `out`, replacing any earlier one."""
    inside = _inside_a_store(reg, out)
    if inside:
        raise BuildError(f"the database can't be written inside a store or a git working "
                         f"tree (it lies in {inside})")
    order = layers.order(reg, audience)
    absent = [t for t in order if reg.tiers[t].store_path is None
              or not reg.tiers[t].store_path.is_dir()]
    if absent:
        raise BuildError(f"stores not on this machine: {', '.join(absent)}")
    rep = BuildReport(audience=audience, tiers=order)

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".building")
    if tmp.exists():
        tmp.unlink()
    con = sqlite3.connect(tmp)
    ok = False
    try:
        con.executescript(SCHEMA)
        # The database as a whole is the audience's. Its description (format, audience,
        # the tiers read) is register information, so it carries the lowest tier read.
        base = order[0]
        con.executemany("INSERT INTO meta VALUES (?, ?, ?)",
                        [("format", FORMAT, base), ("audience", audience, base),
                         ("tiers", " ".join(order), base), ("classification", audience, base)])
        _fill(con, reg, order, audience, rep)
        verify(con, order)
        con.commit()
        con.close()
        os.replace(tmp, out)
        ok = True
    finally:
        con.close()
        if not ok and tmp.exists():
            tmp.unlink()
    return rep


def _fill(con: sqlite3.Connection, reg: Register, order: list[str], audience: str,
          rep: BuildReport) -> None:
    texts: dict[str, dict[str, str]] = {}   # rel -> {tier: text}
    for t in order:
        store = reg.tiers[t].store_path
        for p in store_files(t, store):
            rel = p.relative_to(store).as_posix()
            rep.files += 1
            try:
                text = p.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                if p.suffix.lower() in MEDIA_SUFFIXES:
                    rep.skipped_media += 1
                    con.execute("INSERT INTO skipped_file VALUES (?, ?)", (t, rel))
                    continue
                raise BuildError(f"{t}: {rel}: can't be read as UTF-8 text") from None
            texts.setdefault(rel, {})[t] = text

    def source(t, rel, line, kind, s):
        con.execute("INSERT INTO source_value VALUES (?, ?, ?, ?, ?, ?)",
                    (t, rel, line, kind, s, normalise(s)))
        rep.source_values += 1

    def model(rel, path, kind, s, tier, line=None):
        cur = con.execute("INSERT INTO model_value (rel, path, kind, text, norm, tier, line) "
                          "VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (rel, path, kind, s, normalise(s), tier, line))
        con.executemany("INSERT INTO model_passage VALUES (?, ?, ?)",
                        ((x, cur.lastrowid, tier) for x in passages(s)))
        rep.model_values += 1

    for rel in sorted(texts):
        by_tier = texts[rel]
        is_yaml = Path(rel).suffix.lower() in YAML_SUFFIXES
        docs, line_of = {}, {}
        for t, text in by_tier.items():
            lines = text.splitlines()
            for n, line in enumerate(lines, 1):
                if line.strip():
                    source(t, rel, n, "line", line)
            if not is_yaml:
                for n, line in enumerate(lines, 1):
                    if line.strip():
                        model(rel, f"#line{n}", "line", line, t, n)
                for start, para in _paragraphs(lines):
                    model(rel, f"#para{start}", "paragraph", para, t, start)
                continue
            try:
                items = yamlio.source_items(text)
                for n, c in yamlio.comments(text):
                    source(t, rel, n, "comment", c)
                    model(rel, f"#line{n}", "comment", c, t, n)
                docs[t] = yamlio.load(text)
            except yamlio.YamlError as e:
                what = "holds more than one YAML document" if "more than one" in str(e) else \
                    "uses an alias" if "alias" in str(e) else "is not valid YAML"
                raise BuildError(f"{t}: {rel}: {what}") from None
            line_of[t] = {}
            for n, kind, s, path in items:
                source(t, rel, n, kind, s)
                line_of[t].setdefault((kind, layers.where(path)), n)
        if not is_yaml:
            continue
        try:
            composed = layers.compose(docs, audience, reg)
        except layers.LayerError:
            raise BuildError(f"{rel}: doesn't compose across tiers "
                             f"(run compose_layers for the detail)") from None

        def at(tier, kind, p):
            return line_of.get(tier, {}).get((kind, layers.where(p)))

        for path, node in _walk(composed.doc, ()):
            if isinstance(node, dict):
                # Every key, at the tier that added it: in a free-form mapping a key can be
                # content. The scanner tells field names from content by what lower tiers hold.
                for k in node:
                    kt = composed.tier_of(path + (k,))
                    model(rel, layers.where(path + (k,)), "key", str(k), kt,
                          at(kt, "key", path + (k,)))
                if layers.ID in node and path and isinstance(path[-1], tuple) and path[-1][0] == "id":
                    t = composed.tier_of(path)
                    model(rel, layers.where(path), "id", str(node[layers.ID]), t,
                          at(t, "scalar", path + (layers.ID,)))
            elif node is not None and not isinstance(node, (list, bool)):
                t = composed.tier_of(path)
                model(rel, layers.where(path), "scalar", str(node), t, at(t, "scalar", path))


def _paragraphs(lines: list[str]) -> Iterator[tuple[int, str]]:
    """Blocks of two or more non-blank lines, joined, with the first line's number, so a
    passage that wraps across lines still matches."""
    block, start = [], 0
    for n, line in enumerate(lines + [""], 1):
        if line.strip():
            if not block:
                start = n
            block.append(line.strip())
        else:
            if len(block) > 1:
                yield start, " ".join(block)
            block = []


def verify(con: sqlite3.Connection, order: list[str]) -> None:
    """Every table has a `tier` column, and every row's tier is one the audience reads.
    A passage carries the tier of the value it was cut from."""
    allowed = set(order)
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
    for t in tables:
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
        if "tier" not in cols:
            raise BuildError(f"table {t} has no tier column")
        bad = {r[0] for r in con.execute(f"SELECT DISTINCT tier FROM {t}")} - allowed
        if bad:
            raise BuildError(f"table {t} holds rows of a tier the audience doesn't read")
    if con.execute("SELECT count(*) FROM model_passage p JOIN model_value v ON v.id = p.value_id "
                   "WHERE p.tier != v.tier").fetchone()[0]:
        raise BuildError("a passage's tier differs from its value's")


class AudienceDB:
    """Read-only access to a built audience database."""

    def __init__(self, path: Path):
        if not Path(path).is_file():
            raise BuildError(f"no database at {path}")
        self.con = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
        meta = {k: v for k, v, _ in self.con.execute("SELECT key, value, tier FROM meta")}
        if meta.get("format") != FORMAT:
            raise BuildError("not an audience database of this format")
        self.audience: str = meta["audience"]
        self.tiers: list[str] = meta["tiers"].split()
        self.classification: str = meta["classification"]
        verify(self.con, self.tiers)

    def close(self) -> None:
        self.con.close()

    def __enter__(self) -> "AudienceDB":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def model_tiers(self, text: str) -> set[str]:
        """The tiers whose model material includes this exact (normalised) text."""
        return {r[0] for r in self.con.execute(
            "SELECT DISTINCT tier FROM model_value WHERE norm = ?", (normalise(text),))}
