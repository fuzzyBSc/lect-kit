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

from lectkit import denylist, grants, shared_lists, yamlio
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
    # Per matched tier, the entry and copy number over that tier's own matches only, so a
    # review a lower screen recorded still holds in a screen that also sees a higher tier.
    per_tier: dict = field(default_factory=dict, repr=False, compare=False)

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


# Data formats that can't carry anyone's material, so they're taken out of a line before it
# is matched (project custodian's ruling, 2026-11-10). Each is a whole shape, never a word:
# - a hash: 7 to 64 hex characters with at least one digit and one letter, standing alone,
#   as git and every digest print one (a list of hashes could never be kept in lect-kit);
# - a date, or a date-time with its time zone (ISO 8601);
# - git's own timestamp, seconds since 1970 followed by a zone, as in a commit's headers.
FORMATS = re.compile(
    r"(?<![\w-])(?=[0-9a-f]*[0-9])(?=[0-9a-f]*[a-f])[0-9a-f]{7,64}(?![\w-])"
    r"|(?<![\w-])\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?(?![\w-])"
    r"|(?<![\w-])\d{9,10} [+-]\d{4}(?![\w-])", re.IGNORECASE)


def mask_formats(text: str) -> str:
    """`text` with every hash, date-time and git timestamp replaced by a placeholder word.
    A placeholder, not a space: the words either side of a date must stay apart, as the
    date's own digits kept them, or masking would make passages the line never held."""
    return FORMATS.sub(f" {FORMAT_PLACEHOLDER} ", text)


FORMAT_PLACEHOLDER = "lectkitformatmasked"   # never a word of any tier's material


def load_accepted(path: Path, reg: Register, owner: str | None = None) -> dict[str, set[str]]:
    """{lower tier: {normalised matched text}} from one tier's grants (lectkit/grants.py).

    The file lives in the store of the tier whose material is matched: that tier decides
    that an item of its own is shared with a lower tier, not leaked to it. A grant lives only
    in the granting tier, and only to a tier below it (project custodian's ruling,
    2026-11-09): with `owner` given, a grant to any other tier is refused."""
    try:
        doc = grants.load_grants(path)
    except grants.GrantError as e:
        raise ScanError(f"{ACCEPT_FILE}: {e}") from None
    out: dict[str, set[str]] = {}
    for to, items in doc.items():
        if to not in reg.tiers:
            raise ScanError(f"{ACCEPT_FILE} grants to an unknown tier")
        if owner is not None and to not in reg.tiers[owner].sees:
            raise ScanError(f"{owner}: {ACCEPT_FILE} grants to {to}, which is not "
                            f"a tier below {owner}; a grant goes only from a tier to one it sees")
        try:
            items = shared_lists.expand(items)       # `list:<name>`: a shared list by version
        except shared_lists.ListError as e:
            raise ScanError(f"{ACCEPT_FILE}: {e}") from None
        for x in items:
            out.setdefault(to, set()).add(" ".join(_words(x)) or normalise(x))
    return out


Review = tuple  # (lower tier, rel, entry, frozenset(matched), nth)


def load_reviews(path: Path, reg: Register, owner: str | None = None) -> set[Review]:
    """People's reviews of exact lower entries (lectkit/grants.py). Absent means none. With
    `owner` given, a review of a tier that is not below the owner is refused, as for grants."""
    try:
        doc = grants.load_reviews(path)
    except grants.GrantError as e:
        raise ScanError(f"{REVIEW_FILE}: {e}") from None
    out = set()
    for tier, rows in doc.items():
        if tier not in reg.tiers:
            raise ScanError(f"{REVIEW_FILE} reviews an unknown tier")
        if owner is not None and tier not in reg.tiers[owner].sees:
            raise ScanError(f"{owner}: {REVIEW_FILE} reviews {tier}, which is "
                            f"not a tier below {owner}")
        for r in rows:
            out.add((tier, r["rel"], r["entry"], frozenset(r["matched"]), r["nth"]))
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
    written = []
    by_tier: dict[str, set[str]] = {}
    for tier, text in f.items:
        by_tier.setdefault(tier, set()).add(text)
    for tier, texts in sorted(by_tier.items()):
        store = reg.tiers[tier].store_path
        path = store / REVIEW_FILE
        try:
            doc = grants.load_reviews(path)
        except grants.GrantError as e:
            raise ScanError(f"{tier}: {REVIEW_FILE}: {e}") from None
        entry, nth = f.per_tier.get(tier, (f.entry, f.nth))
        row = {"rel": _digest("rel", f.rel), "entry": entry,
               "matched": _item_digests(scan_key(store), tier, texts), "nth": nth}
        if tier == scanning:
            row = {"id": f.id, **row}
        # Who reviewed it, and why, is the tier's commit; the file holds the row only.
        doc.setdefault(f.tier, []).append(row)
        grants.write(path, doc)
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


GLOBAL_FLAGS = re.compile(r"\(\?[aiLmsux]+\)")


def _gates(pats: list) -> tuple[list, list]:
    """(alone, [(gate, members)]) for one tier's term patterns. Each gate is one alternation
    of patterns that share a flag set: a line it doesn't match matches none of its members,
    so only a line it matches is tried member by member, exactly as before. A pattern with
    groups (a backreference would count them across the alternation) or a global inline
    flag can't share an alternation, so it is always tried on its own."""
    alone, by_flags = [], {}
    for rx in pats:
        if rx.groups or GLOBAL_FLAGS.search(rx.pattern):
            alone.append(rx)
        else:
            core = _literal_core(rx)
            # A pattern that is a literal between lookarounds is gated on that literal: the
            # lookarounds take no width, so wherever it matches, its literal matches too
            # under the same flags, and the regex engine applies the same case rules.
            part = re.escape(core) if core else f"(?:{rx.pattern})"
            by_flags.setdefault((rx.flags, core is not None), []).append((part, rx))
    gates = []
    for (flags, _), members in by_flags.items():
        try:
            gates.append((re.compile("|".join(p for p, _ in members), flags),
                          [rx for _, rx in members]))
        except re.error:
            alone += [rx for _, rx in members]
    return alone, gates


def _literal_core(rx) -> str | None:
    """The literal text of a pattern made only of literals and zero-width assertions."""
    from re import _parser
    try:
        tree = _parser.parse(rx.pattern, rx.flags)
    except Exception:
        return None
    out = []
    for op, av in tree:
        if op is _parser.LITERAL:
            out.append(chr(av))
        elif op not in (_parser.ASSERT, _parser.ASSERT_NOT, _parser.AT):
            return None
    return "".join(out) or None


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
         reviewed: dict[str, set[Review]] | None = None,
         lows: set[str] | None = None) -> ScanReport:
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
    # Decisions are read from the tiers whose material is matched: a tier's own grants
    # release its material to the tiers below it, so they can't bear on a screen of it.
    scanned = [t for t in db.tiers if lows is None or t in lows]
    deciding = {t for low in scanned for t in db.tiers
                if t != low and t not in reg.tiers[low].sees}
    for t in db.tiers:
        if t not in deciding:
            accepted.setdefault(t, {})
            reviewed.setdefault(t, set())
            keys[t] = None
            continue
        store = reg.tiers[t].store_path
        if t not in accepted:
            accepted[t] = load_accepted(store / ACCEPT_FILE, reg, owner=t)
        if t not in reviewed:
            reviewed[t] = load_reviews(store / REVIEW_FILE, reg, owner=t)
        keys[t] = read_key(store)
    key = scan_key(reg.tiers[db.audience].store_path)
    rank = {t: i for i, t in enumerate(reg.tiers)}
    rep = ScanReport(audience=db.audience)
    for low in db.tiers:
        if lows is not None and low not in lows:
            continue             # a screen asks about one lower tree only
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
        gates = {t: _gates(pats) for t, pats in rules.items()}

        hits: dict[tuple[str, int], set[tuple[str, str, str]]] = {}
        spans: dict[tuple[str, int], set[int]] = {}
        spans_t: dict[tuple[str, int, str], set[int]] = {}

        def hit(rel, line, kind, tiers, matched, lines=()):
            for t in tiers:
                hits.setdefault((rel, line), set()).add((kind, t, matched))
            spans.setdefault((rel, line), {line}).update(lines)
            for t in tiers:
                spans_t.setdefault((rel, line, t), {line}).update(lines)

        streams: dict[str, list[tuple[str, int]]] = {}
        texts: dict[tuple[str, int], list[str]] = {}
        for rel, line, kind, text, norm in db.con.execute(
                "SELECT rel, line, kind, text, norm FROM source_value WHERE tier = ? "
                "ORDER BY rel, line, rowid", (low,)):
            structured = Path(rel).suffix.lower() in YAML_SUFFIXES
            if structured and kind == "line":
                continue         # a YAML file is read by its keys, scalars and comments
            texts.setdefault((rel, line), []).append(norm)    # entries keep the line as written
            text = mask_formats(text)
            norm = normalise(text)
            k = _key(norm)
            if len(norm) >= MIN_CHARS and k in values:
                hit(rel, line, "value", values[k], k)
            w = _words(text)
            for n in range(1, longest + 1):
                for i in range(len(w) - n + 1):
                    if all(len(x) == 1 for x in w[i:i + n]):
                        continue   # a run of single letters is never a token match (2026-11-10)
                    g = " ".join(w[i:i + n])
                    if g != k and g in items and len(g) >= MIN_CHARS:
                        hit(rel, line, "token", items[g], g)
            if rules:
                raw = denylist.nfc(text)
                for t, (alone, tg) in gates.items():
                    tried = alone + [rx for gate, ms in tg if gate.search(raw) for rx in ms]
                    for rx in tried:
                        if rx.search(raw):
                            hit(rel, line, "term", {t}, "term:" + rx.pattern)
            # A passage never crosses a table's cell border: the border breaks the run.
            streams.setdefault(rel, []).extend(
                (x, line) for x in _words(text.replace("|", f" {FORMAT_PLACEHOLDER} ")))
        for rel, stream in streams.items():
            for i in range(len(stream) - PASSAGE_WORDS + 1):
                p = " ".join(x for x, _ in stream[i:i + PASSAGE_WORDS])
                if p in hidden_passages:
                    covered = {ln for _, ln in stream[i:i + PASSAGE_WORDS]}
                    hit(rel, stream[i][1], "passage", hidden_passages[p], p, covered)

        # What each tier has released to anything `low` sees, keyed once per tier. A grant to
        # a tier is visible to every tier that sees it, so what `tier` released to anything
        # `low` sees is already in `low`'s view. Every tier may name itself: its id and name
        # are in the register every tier reads (project custodian's ruling, 2026-11-09).
        released = {t: {_key(normalise(x)) for g in (low, *reg.tiers[low].sees)
                        for x in accepted[t].get(g, set())}
                    | {_key(normalise(x)) for x in (low, reg.tiers[low].name)}
                    for t in hidden}
        seen: dict[tuple, int] = {}
        seen_t: dict[tuple, int] = {}
        for (rel, line), ms in sorted(hits.items()):
            # The entry is every line the finding covers, so a passage's later lines count.
            entry = _digest(*(t for ln in sorted(spans[(rel, line)]) for t in texts.get((rel, ln), [])))
            items = tuple(sorted({(m[1], m[2]) for m in ms}))
            nth = seen[(rel, entry, items)] = seen.get((rel, entry, items), 0) + 1
            by_tier: dict[str, set[str]] = {}
            for tier, text in items:
                by_tier.setdefault(tier, set()).add(text)
            acc = rev = True
            per_tier = {}
            for tier, texts_t in sorted(by_tier.items()):
                e_t = _digest(*(x for ln in sorted(spans_t[(rel, line, tier)])
                                for x in texts.get((rel, ln), [])))
                sk = (rel, e_t, tier, frozenset(texts_t))
                n_t = seen_t[sk] = seen_t.get(sk, 0) + 1
                per_tier[tier] = (e_t, n_t)
                t_acc = {_key(normalise(x)) for x in texts_t} <= released[tier]   # keyed alike
                k = keys.get(tier)
                t_rev = k is not None and (
                    (low, _digest("rel", rel), e_t, frozenset(_item_digests(k, tier, texts_t)), n_t)
                    in reviewed[tier])
                acc = acc and t_acc
                rev = rev and (t_acc or t_rev)
            rep.findings.append(Finding(
                low, rel, line,
                matches=tuple(sorted({m[0] for m in ms})),
                hidden=tuple(sorted(by_tier, key=lambda t: -rank[t])),
                entry=entry, nth=nth,
                id=_mac(key, "id", low, rel, entry, str(nth), *(f"{a}\x1f{b}" for a, b in items))[:12],
                accepted=acc, reviewed=rev and not acc, items=items, per_tier=per_tier))
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
