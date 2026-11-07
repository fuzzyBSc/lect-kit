"""Cross-tier scan: find material in a lower store that its readers mustn't see.

Carries out knowledge/spec_classification.md, "Cross-tier scan". Runs inside a higher
tier, on that audience's database. Findings name a store, file and line, never text.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from lectkit import denylist, yamlio
from lectkit.audience_db import (KIT_DIR, PASSAGE_WORDS, YAML_SUFFIXES, AudienceDB, normalise,
                                 store_digest)
from lectkit.tiers import Register

MIN_CHARS = 3
MAX_TOKENS = 4      # hidden values and ids up to this many words are also found inside lines
# Only items from structured data are looked for inside lines. A prose line or paragraph is
# matched whole or by passage: the words of a heading aren't lexical items.
STRUCTURED_KINDS = ("id", "key", "scalar")
ACCEPT_FILE = f"{KIT_DIR}/accepted_matches.yaml"
REVIEW_FILE = f"{KIT_DIR}/reviewed_findings.yaml"
KEY_FILE = f"{KIT_DIR}/scan_key"   # a secret of the scanning tier; never leaves its store


class ScanError(ValueError):
    pass


@dataclass(frozen=True)
class Finding:
    tier: str                    # the lower store's tier
    rel: str
    line: int
    matches: tuple[str, ...]     # kinds of match: value, token, passage
    hidden: tuple[str, ...]      # every hidden tier matched, most restrictive first
    entry: str = ""              # digest of the lower text the finding covers
    nth: int = 1                 # which copy of this entry in the file, counting from 1
    id: str = ""                 # keyed, so it can't be used to test guesses at hidden text
    accepted: bool = False       # every matched tier's accepted matches cover it
    reviewed: bool = False       # every matched tier's reviews cover it (and not all by accept)
    items: tuple = field(default=(), repr=False, compare=False)  # (tier, text) matched; in memory only

    @property
    def cleared(self) -> bool:
        return self.accepted or self.reviewed


@dataclass
class ScanReport:
    audience: str
    scanned: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def open_findings(self) -> list[Finding]:
        return [f for f in self.findings if not f.cleared]


def _digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _mac(key: bytes, *parts: str) -> str:
    return hmac.new(key, "\x1f".join(parts).encode("utf-8"), hashlib.sha256).hexdigest()


def read_key(store: Path) -> bytes | None:
    """A tier's key, or None if it has none yet."""
    f = store / KEY_FILE
    if not f.is_file():
        return None
    try:
        key = bytes.fromhex(f.read_text(encoding="ascii").strip())
    except (UnicodeDecodeError, ValueError):
        key = b""
    if len(key) != 32:
        raise ScanError(f"{KEY_FILE} is damaged; delete it and review findings again")
    return key


def scan_key(store: Path) -> bytes:
    """A tier's secret for finding ids and review digests, made on first use.

    Without it, an id or a review digest could be recomputed from guesses at hidden text
    by anyone holding the report, which would confirm the guess."""
    f = store / KEY_FILE
    if f.is_file():
        try:
            key = bytes.fromhex(f.read_text(encoding="ascii").strip())
        except (UnicodeDecodeError, ValueError):
            key = b""
        if len(key) != 32:
            raise ScanError(f"{KEY_FILE} is damaged; delete it and review findings again")
        return key
    f.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_bytes(32)
    f.write_text(key.hex() + "\n", encoding="ascii")     # text, so any reader of the store can read it
    return key


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", normalise(text))


def load_accepted(path: Path, reg: Register) -> dict[str, set[str]]:
    """{lower tier: {normalised matched text}} from one tier's accepted-matches file.

    The file lives in the store of the tier whose material is matched: that tier decides
    that an item of its own is shared with a lower tier, not leaked to it."""
    if not path.is_file():
        return {}
    try:
        rows = yamlio.load_file(path)
    except yamlio.YamlError:
        raise ScanError(f"{ACCEPT_FILE} is not valid YAML") from None
    if rows is None:
        return {}
    if not isinstance(rows, list):
        raise ScanError(f"{ACCEPT_FILE} must be a list")
    out: dict[str, set[str]] = {}
    for i, r in enumerate(rows):
        if (not isinstance(r, dict) or not {"text", "tier", "reason", "by", "at"} <= set(r)
                or not isinstance(r["text"], str) or r["tier"] not in reg.tiers):
            raise ScanError(f"{ACCEPT_FILE} entry {i + 1} needs text, a known tier, reason, by "
                            f"and at")
        out.setdefault(r["tier"], set()).add(" ".join(_words(r["text"])) or normalise(r["text"]))
    return out


Review = tuple  # (lower tier, rel, entry, frozenset(matched), nth)
REVIEW_KEYS = {"tier", "rel", "entry", "matched", "nth", "reason", "by", "at"}


def load_reviews(path: Path, reg: Register) -> set[Review]:
    """People's reviews of exact lower entries. Absent means none."""
    if not path.is_file():
        return set()
    try:
        rows = yamlio.load_file(path)
    except yamlio.YamlError:
        raise ScanError(f"{REVIEW_FILE} is not valid YAML") from None
    if rows is None:
        return set()
    if not isinstance(rows, list):
        raise ScanError(f"{REVIEW_FILE} must be a list")
    out = set()
    for i, r in enumerate(rows):
        ok = (isinstance(r, dict) and set(r) - {"id"} == REVIEW_KEYS
              and r["tier"] in reg.tiers and isinstance(r["rel"], str)
              and isinstance(r["entry"], str) and isinstance(r["matched"], list)
              and all(isinstance(m, str) for m in r["matched"])
              and isinstance(r["nth"], int) and not isinstance(r["nth"], bool) and r["nth"] >= 1
              and isinstance(r["by"], str) and r["by"].startswith("human:"))
        if not ok:
            raise ScanError(f"{REVIEW_FILE} entry {i + 1} needs exactly tier, rel, entry, "
                            f"matched, nth, reason, at (an id is optional), and by naming a "
                            f"person (human:...)")
        out.add((r["tier"], r["rel"], r["entry"], frozenset(r["matched"]), r["nth"]))
    return out


def _item_digests(key: bytes, tier: str, texts) -> list[str]:
    return sorted({_mac(key, "item", tier, t) for t in texts})


def record_review(reg: Register, f: Finding, reason: str, by: str, at: str,
                  scanning: str | None = None) -> list[Path]:
    """Record a person's review of one finding in the store of each tier whose material it
    matched, so every scanner above that tier honours it. Returns the files written.

    The finding's id is kept only in the scanning tier's own record: elsewhere it would
    tell a lower tier's readers nothing they can use, beyond that someone above looked."""
    if not by.startswith("human:"):
        raise ScanError("a review is recorded for a person: by must be human:<name or role>")
    if not reason.strip():
        raise ScanError("a review needs a reason")
    if not f.items:
        raise ScanError("this finding carries no matched items to review")
    import yaml
    written = []
    by_tier: dict[str, set[str]] = {}
    for tier, text in f.items:
        by_tier.setdefault(tier, set()).add(text)
    for tier, texts in sorted(by_tier.items()):
        store = reg.tiers[tier].store_path
        path = store / REVIEW_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        if path.is_file():
            try:
                rows = yamlio.load_file(path) or []
            except yamlio.YamlError:
                raise ScanError(f"{tier}: {REVIEW_FILE} is not valid YAML") from None
            if not isinstance(rows, list):
                raise ScanError(f"{tier}: {REVIEW_FILE} must be a list")
        row = {"tier": f.tier, "rel": f.rel, "entry": f.entry,
               "matched": _item_digests(scan_key(store), tier, texts), "nth": f.nth,
               "reason": reason, "by": by, "at": at}
        if tier == scanning:
            row = {"id": f.id, **row}
        rows.append(row)
        tmp = path.with_name(path.name + ".writing")
        tmp.write_text(yaml.safe_dump(rows, sort_keys=False, allow_unicode=True), encoding="utf-8")
        tmp.replace(path)
        written.append(path)
    return written


def _rules(reg: Register, tier: str) -> list:
    t = reg.tiers[tier]
    missing = [p for p in t.terms if not p.is_file()]
    if missing:
        raise ScanError(f"{tier}: a term register named in the register is missing")
    try:
        return denylist.matchers(t.terms)
    except SystemExit:
        raise ScanError(f"{tier}: a term register can't be read") from None


def check_fresh(db: AudienceDB, reg: Register) -> None:
    for t in db.tiers:
        store = reg.tiers[t].store_path if t in reg.tiers else None
        if store is None or not store.is_dir():
            raise ScanError(f"{t}: store not on this machine")
        if store_digest(t, store, t == db.audience) != db.digests.get(t):
            raise ScanError(f"{t}: store has changed since the database was built; rebuild it")


def _key(norm: str) -> str:
    return " ".join(_words(norm)) or norm


def scan(db: AudienceDB, reg: Register,
         accepted: dict[str, dict[str, set[str]]] | None = None,
         reviewed: dict[str, set[Review]] | None = None) -> ScanReport:
    """Every line of every lower store that matches material hidden from that store.

    A line matches when its whole text equals hidden material, when a run of up to
    MAX_TOKENS words in it equals a short hidden value or id, or when a five-word
    passage, counted across line ends in the file, equals one in hidden material.

    A finding is cleared when, for every tier whose material it matched, that tier has
    accepted those items for the lower tier, or a person's review recorded in that tier's
    store covers this exact entry: the same file, the same text, the same copy and the same
    items. Decisions are read from each tier's store unless `accepted` or `reviewed`
    ({material tier: ...}) is given for it."""
    if db.audience not in reg.tiers or set(db.tiers) - set(reg.tiers):
        raise ScanError("the database was built from a different register")
    check_fresh(db, reg)
    accepted = dict(accepted or {})
    reviewed = dict(reviewed or {})
    for t, d in accepted.items():
        if t not in reg.tiers or not isinstance(d, dict) or not all(
                isinstance(v, (set, frozenset)) for v in d.values()):
            raise ScanError("accepted must be {material tier: {lower tier: set of texts}}")
    for t, d in reviewed.items():
        if t not in reg.tiers or not isinstance(d, (set, frozenset)):
            raise ScanError("reviewed must be {material tier: set of reviews}")
    keys: dict[str, bytes | None] = {}
    for t in db.tiers:
        store = reg.tiers[t].store_path
        if t not in accepted:
            accepted[t] = load_accepted(store / ACCEPT_FILE, reg)
        if t not in reviewed:
            reviewed[t] = load_reviews(store / REVIEW_FILE, reg)
        keys[t] = read_key(store)
    key = scan_key(reg.tiers[db.audience].store_path)
    rank = {t: i for i, t in enumerate(reg.tiers)}
    rep = ScanReport(audience=db.audience)
    for low in db.tiers:
        visible = {low, *reg.tiers[low].sees}
        hidden = [t for t in db.tiers if t not in visible]
        if not hidden:
            continue
        rep.scanned.append(low)
        hq = ",".join("?" * len(hidden))
        values: dict[str, set[str]] = {}
        items: dict[str, set[str]] = {}      # structured items, also found inside lines
        for norm, tier, kind in db.con.execute(
                f"SELECT norm, tier, kind FROM model_value WHERE tier IN ({hq})", hidden):
            if len(norm) >= MIN_CHARS:
                values.setdefault(_key(norm), set()).add(tier)
                if kind in STRUCTURED_KINDS:
                    items.setdefault(_key(norm), set()).add(tier)
        longest = max((len(k.split()) for k in items if len(k.split()) <= MAX_TOKENS), default=0)
        hidden_passages: dict[str, set[str]] = {}
        for norm, tier in db.con.execute(
                f"SELECT norm, tier FROM model_passage WHERE tier IN ({hq})", hidden):
            hidden_passages.setdefault(norm, set()).add(tier)
        # Each hidden tier's term registers, applied as terms and patterns.
        rules = {t: _rules(reg, t) for t in hidden}


        hits: dict[tuple[str, int], set[tuple[str, str, str]]] = {}
        spans: dict[tuple[str, int], set[int]] = {}

        def hit(rel, line, kind, tiers, matched, lines=()):
            for t in tiers:
                hits.setdefault((rel, line), set()).add((kind, t, matched))
            spans.setdefault((rel, line), {line}).update(lines)

        streams: dict[str, list[tuple[str, int]]] = {}
        texts: dict[tuple[str, int], list[str]] = {}
        for rel, line, kind, text, norm in db.con.execute(
                "SELECT rel, line, kind, text, norm FROM source_value WHERE tier = ? "
                "ORDER BY rel, line, rowid", (low,)):
            structured = Path(rel).suffix.lower() in YAML_SUFFIXES
            if structured and kind == "line":
                continue         # a YAML file is read by its keys, scalars and comments
            texts.setdefault((rel, line), []).append(norm)
            k = _key(norm)
            if len(norm) >= MIN_CHARS and k in values:
                hit(rel, line, "value", values[k], k)
            w = _words(text)
            for n in range(1, longest + 1):
                for i in range(len(w) - n + 1):
                    g = " ".join(w[i:i + n])
                    if g != k and g in items and len(g) >= MIN_CHARS:
                        hit(rel, line, "token", items[g], g)
            if rules:
                raw = denylist.nfc(text)
                for t, pats in rules.items():
                    for rx in pats:
                        if rx.search(raw):
                            hit(rel, line, "term", {t}, "term:" + rx.pattern)
            streams.setdefault(rel, []).extend((x, line) for x in w)
        for rel, stream in streams.items():
            for i in range(len(stream) - PASSAGE_WORDS + 1):
                p = " ".join(x for x, _ in stream[i:i + PASSAGE_WORDS])
                if p in hidden_passages:
                    covered = {ln for _, ln in stream[i:i + PASSAGE_WORDS]}
                    hit(rel, stream[i][1], "passage", hidden_passages[p], p, covered)

        seen: dict[tuple, int] = {}
        for (rel, line), ms in sorted(hits.items()):
            # The entry is every line the finding covers, so a passage's later lines count.
            entry = _digest(*(t for ln in sorted(spans[(rel, line)]) for t in texts.get((rel, ln), [])))
            items = tuple(sorted({(m[1], m[2]) for m in ms}))
            nth = seen[(rel, entry, items)] = seen.get((rel, entry, items), 0) + 1
            by_tier: dict[str, set[str]] = {}
            for tier, text in items:
                by_tier.setdefault(tier, set()).add(text)
            acc = rev = True
            for tier, texts_t in by_tier.items():
                ok = {_key(normalise(x)) for x in accepted[tier].get(low, set())}
                t_acc = texts_t <= ok
                k = keys.get(tier)
                t_rev = k is not None and (
                    (low, rel, entry, frozenset(_item_digests(k, tier, texts_t)), nth)
                    in reviewed[tier])
                acc = acc and t_acc
                rev = rev and (t_acc or t_rev)
            rep.findings.append(Finding(
                low, rel, line,
                matches=tuple(sorted({m[0] for m in ms})),
                hidden=tuple(sorted(by_tier, key=lambda t: -rank[t])),
                entry=entry, nth=nth,
                id=_mac(key, "id", low, rel, entry, str(nth), *(f"{a}\x1f{b}" for a, b in items))[:12],
                accepted=acc, reviewed=rev and not acc, items=items))
    return rep


def report_path_allowed(reg: Register, scanning_tier: str, out: Path) -> bool:
    """A report may go under the scanning tier's own `.lectkit/` folder, which the
    database doesn't read, or outside every store. Never into any other store."""
    o = out.resolve()
    holders = [t for t in reg.tiers.values()
               if t.store_path is not None and (o == t.store_path or t.store_path in o.parents)]
    if not holders:
        return True
    return all(t.id == scanning_tier for t in holders) and \
        (reg.tiers[scanning_tier].store_path / KIT_DIR) in o.parents
