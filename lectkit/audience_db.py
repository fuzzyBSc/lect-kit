"""An audience's database of everything it can see, with the tier of every value.

Carries out knowledge/spec_classification.md, "Audience database". The database holds
readable restricted text: it's as restricted as the most restricted tier in it, built
outside every store, and ephemeral.
"""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import subprocess
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from lectkit import format_words, layers, shared_lists, yamlio
from lectkit.tiers import Register

FORMAT = "1"
PASSAGE_WORDS = 5
YAML_SUFFIXES = {".yaml", ".yml"}
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".wav", ".mp3", ".flac", ".ogg",
                  ".m4a", ".mp4", ".webm"}

KIT_DIR = ".lectkit"   # kit configuration in a store, such as accepted scan matches
# A tier's recorded decisions about matches. They're scanned as source, but they're neither
# model material (an accepted text would otherwise match the stores below) nor part of a
# store's digest (recording a decision would otherwise make every database above stale).
# Grants, reviews and drafts are the tier's own material and are screened like any other
# file (project custodian's ruling, 2026-11-09): a grant lives in the granting tier, and as
# plain lists (lectkit/grants.py) they add only what they release. Only the scan key
# is kept out: it is a secret, not knowledge.
DECISION_FILES = {f"{KIT_DIR}/scan_key"}
# A tier's own list of files in its store that aren't its material (README, agent notes,
# .gitignore...). The tier decides. It's part of the store's digest, since it changes what
# the database holds, but it isn't material itself.
EXCLUDE_FILE = f"{KIT_DIR}/not_material.txt"
# A tier's own list of fields whose values are structure, not knowledge: enumerations and
# bookkeeping (a status, a type, a tag list, a generated-by stamp). It covers YAML keys and
# markdown frontmatter keys. Like the exclusion list, it's digested but isn't material.
STRUCTURE_FILE = f"{KIT_DIR}/structure.yaml"


def structure_fields(store: Path) -> set[str]:
    f = store / STRUCTURE_FILE
    if not f.is_file():
        return set()
    try:
        d = yamlio.load_file(f)
    except yamlio.YamlError:
        raise BuildError(f"{STRUCTURE_FILE} is not valid YAML") from None
    fields = (d or {}).get("fields", []) if isinstance(d, dict) else None
    if not isinstance(fields, list) or not all(isinstance(x, str) and x for x in fields):
        raise BuildError(f"{STRUCTURE_FILE} must be {{fields: [field names]}}")
    return set(fields)


# In a YAML file a structure field's value is cleared only when it is short: a sentence
# under a field named `type` or `status` is still content.
STRUCTURE_MAX_WORDS = 3
# The keys of a term register whose values are rules (terms, variants, patterns).
RULE_KEYS = {"term", "terms", "form", "forms", "word", "words", "headword", "lemma",
             "variant", "variants", "pattern", "patterns", "regex",
             "suffix_guard"}   # a regex appended to a pattern to rule out a look-alike

FRONTMATTER_KEY = re.compile(r"^([A-Za-z_][\w-]*)\s*:")


def frontmatter_structure_lines(lines: list[str], fields: set[str]) -> set[int]:
    """Line numbers (from 1) of frontmatter lines whose key is a structure field."""
    if not fields or not lines or lines[0].strip() != "---":
        return set()
    out = set()
    for n, line in enumerate(lines[1:], 2):
        if line.strip() == "---":
            return out
        m = FRONTMATTER_KEY.match(line)
        if m and m.group(1) in fields:
            out.add(n)
    return set()                          # never closed: not frontmatter, so nothing is cleared


UNSUPPORTED = set("![]\\")


def parse_patterns(text: str, where: str = EXCLUDE_FILE) -> list[str]:
    """Patterns from the text of an exclusion list.

    One pattern per line. A line starting with `#` is a comment. `*` matches within one
    folder level, `?` one character, `**` any number of folder levels. A pattern without
    a slash, other than a trailing one, matches a name at any depth, so `README.md`
    excludes every README. Use a leading `/` (`/README.md`) to mean only the top-level
    file. A trailing `/` matches a folder and everything in it. Negation (`!`), character
    classes, backslashes and `#` after the start of a line aren't supported. They are
    errors rather than guesses, because a misread pattern can hide material."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if UNSUPPORTED & set(line) or "#" in line:
            raise BuildError(f"{where}:{n}: unsupported pattern syntax (no !, [ ], \\ or #)")
        out.append(line)
    return out


def not_material(store: Path) -> list[str]:
    """The patterns in a store's EXCLUDE_FILE, as it is on disk."""
    f = store / EXCLUDE_FILE
    if not f.is_file():
        return []
    return parse_patterns(f.read_text(encoding="utf-8-sig"))


def _pattern_re(pat: str) -> re.Pattern:
    folder = pat.endswith("/")
    body = pat.rstrip("/")
    anchored = "/" in body                 # a leading or middle slash anchors, as in .gitignore
    p = body.lstrip("/")
    rx = ""
    i = 0
    while i < len(p):
        if p.startswith("**/", i):
            rx += "(?:.*/)?"               # zero or more whole folders
            i += 3
        elif p.startswith("**", i):
            rx += ".*"                     # a trailing ** : everything below
            i += 2
        elif p[i] == "*":
            rx += "[^/]*"
            i += 1
        elif p[i] == "?":
            rx += "[^/]"
            i += 1
        else:
            rx += re.escape(p[i])
            i += 1
    head = "" if anchored else r"(?:.*/)?"
    tail = r"/.*" if folder else r"(?:/.*)?"
    return re.compile(rf"^{head}{rx}{tail}$")


def excluded(patterns: list[str], rel: str) -> bool:
    return any(_pattern_re(p).match(rel) for p in patterns)

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


def store_files(tier: str, store: Path, skip_kit: bool = False) -> Iterator[Path]:
    """Every file in a store, outside .git. A symbolic link anywhere is an error: it could
    pull in material from outside the store, or hide material the walk wouldn't reach.
    `skip_kit` leaves out the store's .lectkit/ folder: only the scanning tier's own kit
    folder is skipped, so a lower store can't hide material there.

    In a store that is a git checkout of its own, the store's files are the ones git
    tracks plus new ones it doesn't ignore: ignored files (editor folders, caches, build
    output) aren't part of the store. Elsewhere every file is read."""
    listed = _git_listed(store)
    if listed is not None:
        for rel in listed:
            p = store / rel
            parts = Path(rel).parts
            if skip_kit and parts and parts[0] == KIT_DIR:
                continue
            for i in range(1, len(parts) + 1):
                if (store.joinpath(*parts[:i])).is_symlink():
                    raise BuildError(f"{tier}: {Path(*parts[:i]).as_posix()}: "
                                     f"symbolic links aren't allowed in a store")
            if p.is_file():
                yield p
        return
    for root, dirs, files in os.walk(store, followlinks=False):
        rp = Path(root)
        if rp == store:
            dirs[:] = [d for d in dirs if d != ".git" and not (skip_kit and d == KIT_DIR)]
        for name in dirs + files:
            if (rp / name).is_symlink():
                raise BuildError(f"{tier}: {(rp / name).relative_to(store).as_posix()}: "
                                 f"symbolic links aren't allowed in a store")
        dirs.sort()
        for name in sorted(files):
            yield rp / name


def _git_listed(store: Path) -> list[str] | None:
    """Tracked and untracked-but-not-ignored paths, if `store` is the top of its own
    git checkout; None otherwise."""
    top = subprocess.run(["git", "-C", str(store), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != store.resolve():
        return None
    r = subprocess.run(["git", "-C", str(store), "ls-files", "-z", "--cached", "--others",
                        "--exclude-standard"], capture_output=True)
    if r.returncode != 0:
        raise BuildError("git ls-files failed in a store")
    return sorted({x.decode("utf-8", "surrogateescape")
                   for x in r.stdout.split(chr(0).encode()) if x})


def store_digest(tier: str, store: Path, skip_kit: bool = False) -> str:
    """A digest of every file the database reads from a store, by path and content."""
    h = hashlib.sha256()
    for p in store_files(tier, store, skip_kit):
        if p.relative_to(store).as_posix() in DECISION_FILES:
            continue
        h.update(p.relative_to(store).as_posix().encode("utf-8") + b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


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


def build(reg: Register, audience: str, out: Path, source_tiers: set[str] | None = None,
          model_tiers: set[str] | None = None, cache=None) -> BuildReport:
    """Build `audience`'s database into the SQLite file `out`, replacing any earlier one.
    A screen limits it to the tiers it needs (`_fill`)."""
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
                         ("tiers", " ".join(order), base), ("classification", audience, base)]
                        + [(f"digest:{t}", store_digest(t, reg.tiers[t].store_path, t == audience), t)
                           for t in order])
        _fill(con, reg, order, audience, rep, source_tiers, model_tiers, cache)
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
          rep: BuildReport, source_tiers: set[str] | None = None,
          model_tiers: set[str] | None = None, cache=None) -> None:
    """Fill the tables. `source_tiers` and `model_tiers` limit which tiers' source rows and
    model rows are written (all when None). A tier's material depends on its own store
    only, since a higher tier never restates, so `cache` (material_cache.MaterialCache)
    can hold it between builds."""
    source_tiers = set(order) if source_tiers is None else source_tiers
    model_tiers = set(order) if model_tiers is None else model_tiers
    cached = {t: cache.get(t) for t in model_tiers} if cache is not None else {}
    cached = {t: rows for t, rows in cached.items() if rows is not None}
    rows_of: dict[str, list[tuple]] = {t: [] for t in model_tiers if t not in cached}
    texts: dict[str, dict[str, str]] = {}   # rel -> {tier: text}
    for t in order:
        store = reg.tiers[t].store_path
        for p in store_files(t, store, t == audience):
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
        if t not in source_tiers:
            return
        con.execute("INSERT INTO source_value VALUES (?, ?, ?, ?, ?, ?)",
                    (t, rel, line, kind, s, normalise(s)))
        rep.source_values += 1

    # Format words: the kit's declared field names and enum values (format_words.py). The
    # kit may not declassify on its own, so the build stops while any tier treats one as
    # material.
    fw = format_words.load()
    clash = format_words.conflicts(reg, fw)
    if clash:
        raise BuildError("a lect-kit format word is material in a tier: " + "; ".join(clash))
    clash = shared_lists.conflicts(reg)
    if clash:
        raise BuildError("a shared list entry is material in a tier: " + "; ".join(clash))
    vocab = fw.all_words()
    exclusions = {t: not_material(reg.tiers[t].store_path) for t in order}
    structure = {t: structure_fields(reg.tiers[t].store_path) for t in order}
    # A tier's term registers are rules, applied as rules by the scan, not text to match.
    term_files = {t: {p.relative_to(reg.tiers[t].store_path.resolve()).as_posix()
                      for p in reg.tiers[t].terms
                      if reg.tiers[t].store_path.resolve() in p.parents} for t in order}

    def model(rel, path, kind, s, tier, line=None):
        if tier not in rows_of:
            return                        # not wanted, or already held in the cache
        if rel in DECISION_FILES or rel in (EXCLUDE_FILE, STRUCTURE_FILE):
            return                        # decisions are scanned as source, never as model
        if excluded(exclusions[tier], rel):
            return                        # the tier says this file isn't its material
        if not re.search(r"[^\W_]", s):
            return                        # no letter or digit (a fence, a rule): no knowledge
        if kind == "id" and s in vocab and reg.tiers[tier].terms:   # a restricted tier
            raise BuildError(f"{tier}: {rel}: writes the lect-kit format word '{s}' as an "
                             f"identifier, so the kit can't treat it as format")
        rows_of[tier].append((rel, path, kind, s, normalise(s), line, list(passages(s))))

    for rel in sorted(texts):
        by_tier = texts[rel]
        is_yaml = Path(rel).suffix.lower() in YAML_SUFFIXES
        # A copy is read when its source or material is wanted, or when its layers have to
        # be checked to compose with another tier's copy.
        # A tier's kit folder holds its own decisions, never a layer of a shared file.
        kit_file = rel.startswith(KIT_DIR + "/")
        layered = is_yaml and len(by_tier) > 1 and not kit_file
        by_tier = {t: x for t, x in by_tier.items()
                   if t in source_tiers or t in rows_of or layered}
        docs, line_of = {}, {}
        # Everything a tier's own copy of a file writes is that tier's material, whatever a
        # lower copy holds: a higher tier never restates (project custodian's ruling,
        # 2026-11-10). Crediting a restated value to the lower tier let a commit make a
        # higher tier's value its own by writing it into the same file. Repeats within one
        # tier's copy are recorded once.
        for t in [x for x in order if x in by_tier]:
            held: set[tuple[str, str]] = set()

            def added(kind, text, held=held):
                k = (kind, normalise(text))
                if k in held:
                    return False
                held.add(k)
                return True

            text = by_tier[t]
            lines = text.splitlines()
            for n, line in enumerate(lines, 1):
                if line.strip():
                    source(t, rel, n, "line", line)
            if not is_yaml:
                skip = frontmatter_structure_lines(lines, structure[t])
                for n, line in enumerate(lines, 1):
                    if line.strip() and n not in skip and added("line", line):
                        model(rel, f"#line{n}", "line", line, t, n)
                kept = ["" if n in skip else line for n, line in enumerate(lines, 1)]
                for start, para in _paragraphs(kept):
                    if added("paragraph", para):
                        model(rel, f"#para{start}", "paragraph", para, t, start)
                continue
            try:
                items = yamlio.source_items(text)
                for n, c in yamlio.comments(text):
                    source(t, rel, n, "comment", c)
                    if added("comment", c):
                        model(rel, f"#line{n}", "comment", c, t, n)
                docs[t] = yamlio.load(text)
            except yamlio.YamlError as e:
                what = "holds more than one YAML document" if "more than one" in str(e) else \
                    "is not valid YAML"
                raise BuildError(f"{t}: {rel}: {what}") from None
            line_of[t] = {}
            for n, kind, s, path in items:
                source(t, rel, n, kind, s)
                line_of[t].setdefault((kind, layers.where(path)), n)
        if not is_yaml or rel in DECISION_FILES:
            continue
        try:
            if not kit_file:
                layers.compose(docs, audience, reg)    # the layers must still compose
        except layers.LayerError:
            raise BuildError(f"{rel}: doesn't compose across tiers "
                             f"(run compose_layers for the detail)") from None

        def at(tier, kind, p):
            return line_of.get(tier, {}).get((kind, layers.where(p)))

        for t, own_doc in docs.items():
            _model_doc(rel, t, own_doc, model, at, fw, term_files, structure)

    for t in sorted(model_tiers):
        rows = cached[t] if t in cached else rows_of[t]
        if t not in cached and cache is not None:
            cache.put(t, rows)
        for rel, path, kind, s, norm, line, ps in rows:
            cur = con.execute("INSERT INTO model_value (rel, path, kind, text, norm, tier, line) "
                              "VALUES (?, ?, ?, ?, ?, ?, ?)", (rel, path, kind, s, norm, t, line))
            con.executemany("INSERT INTO model_passage VALUES (?, ?, ?)",
                            ((x, cur.lastrowid, t) for x in ps))
            rep.model_values += 1


def _model_doc(rel, t, doc, model, at, fw, term_files, structure) -> None:
    """Every key, id and value tier `t`'s own copy of `rel` writes, as `t`'s material.
    Identifiers it uses to attach to a lower record are its material too."""
    for path, node in _walk(doc, ()):
        if isinstance(node, dict):
            # Every key: in a free-form mapping a key can be content.
            for k in node:
                if rel in term_files[t]:
                    continue          # a term register's keys are its format, not material
                if fw.is_key(k):
                    continue          # a field name the kit's schema declares: format
                model(rel, layers.where(path + (k,)), "key", str(k), t,
                      at(t, "key", path + (k,)))
            if layers.ID in node and path and isinstance(path[-1], tuple) and path[-1][0] == "id":
                model(rel, layers.where(path), "id", str(node[layers.ID]), t,
                      at(t, "scalar", path + (layers.ID,)))
        elif node is not None and not isinstance(node, (list, bool)):
            # The scalar's own field: its key, or the key of the list it sits in.
            own = path[-1] if path and isinstance(path[-1], str) else (
                path[-2] if len(path) > 1 and isinstance(path[-2], str) else None)
            if rel in term_files[t] and own in RULE_KEYS:
                continue              # a term or pattern: the scan applies it as a rule
            if fw.is_value(own, node):
                continue              # a value the field's declared enumeration fixes
            if own in structure[t] and len(str(node).split()) <= STRUCTURE_MAX_WORDS:
                continue              # a short value of a structure field: structure
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
        self.digests: dict[str, str] = {k.split(":", 1)[1]: v for k, v in meta.items()
                                        if k.startswith("digest:")}
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
