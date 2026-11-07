"""Cross-tier scan: find material in a lower store that its readers mustn't see.

Carries out knowledge/spec_classification.md, "Cross-tier scan". Runs inside a higher
tier, on that audience's database. Findings name a store, file and line, never text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from lectkit import yamlio
from lectkit.audience_db import (KIT_DIR, PASSAGE_WORDS, YAML_SUFFIXES, AudienceDB, normalise,
                                 store_digest)
from lectkit.tiers import Register

MIN_CHARS = 3
MAX_TOKENS = 4      # hidden values and ids up to this many words are also found inside lines
ACCEPT_FILE = f"{KIT_DIR}/accepted_matches.yaml"


class ScanError(ValueError):
    pass


@dataclass(frozen=True)
class Finding:
    tier: str                    # the lower store's tier
    rel: str
    line: int
    matches: tuple[str, ...]     # kinds of match: value, token, passage
    hidden: tuple[str, ...]      # every hidden tier matched, most restrictive first
    accepted: bool = False


@dataclass
class ScanReport:
    audience: str
    scanned: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def open_findings(self) -> list[Finding]:
        return [f for f in self.findings if not f.accepted]


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", normalise(text))


def load_accepted(path: Path, reg: Register) -> dict[str, set[str]]:
    """{lower tier: {normalised matched text}} from an accepted-matches file."""
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


def check_fresh(db: AudienceDB, reg: Register) -> None:
    for t in db.tiers:
        store = reg.tiers[t].store_path if t in reg.tiers else None
        if store is None or not store.is_dir():
            raise ScanError(f"{t}: store not on this machine")
        if store_digest(t, store, t == db.audience) != db.digests.get(t):
            raise ScanError(f"{t}: store has changed since the database was built; rebuild it")


def _key(norm: str) -> str:
    return " ".join(_words(norm)) or norm


def scan(db: AudienceDB, reg: Register, accepted: dict[str, set[str]] | None = None
         ) -> ScanReport:
    """Every line of every lower store that matches material hidden from that store.

    A line matches when its whole text equals hidden material, when a run of up to
    MAX_TOKENS words in it equals a short hidden value or id, or when a five-word
    passage, counted across line ends in the file, equals one in hidden material."""
    if db.audience not in reg.tiers or set(db.tiers) - set(reg.tiers):
        raise ScanError("the database was built from a different register")
    check_fresh(db, reg)
    accepted = accepted or {}
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
        for norm, tier in db.con.execute(
                f"SELECT norm, tier FROM model_value WHERE tier IN ({hq})", hidden):
            if len(norm) >= MIN_CHARS:
                values.setdefault(_key(norm), set()).add(tier)
        longest = max((len(k.split()) for k in values if len(k.split()) <= MAX_TOKENS), default=0)
        hidden_passages: dict[str, set[str]] = {}
        for norm, tier in db.con.execute(
                f"SELECT norm, tier FROM model_passage WHERE tier IN ({hq})", hidden):
            hidden_passages.setdefault(norm, set()).add(tier)

        hits: dict[tuple[str, int], set[tuple[str, str, str]]] = {}

        def hit(rel, line, kind, tiers, matched):
            for t in tiers:
                hits.setdefault((rel, line), set()).add((kind, t, matched))

        streams: dict[str, list[tuple[str, int]]] = {}
        for rel, line, kind, text, norm in db.con.execute(
                "SELECT rel, line, kind, text, norm FROM source_value WHERE tier = ? "
                "ORDER BY rel, line, rowid", (low,)):
            structured = Path(rel).suffix.lower() in YAML_SUFFIXES
            if structured and kind == "line":
                continue         # a YAML file is read by its keys, scalars and comments
            k = _key(norm)
            if len(norm) >= MIN_CHARS and k in values:
                hit(rel, line, "value", values[k], k)
            w = _words(text)
            for n in range(1, longest + 1):
                for i in range(len(w) - n + 1):
                    g = " ".join(w[i:i + n])
                    if g != k and g in values and len(g) >= MIN_CHARS:
                        hit(rel, line, "token", values[g], g)
            streams.setdefault(rel, []).extend((x, line) for x in w)
        for rel, stream in streams.items():
            for i in range(len(stream) - PASSAGE_WORDS + 1):
                p = " ".join(x for x, _ in stream[i:i + PASSAGE_WORDS])
                if p in hidden_passages:
                    hit(rel, stream[i][1], "passage", hidden_passages[p], p)

        ok = {_key(normalise(x)) for x in accepted.get(low, set())}
        for (rel, line), ms in sorted(hits.items()):
            rep.findings.append(Finding(
                low, rel, line,
                matches=tuple(sorted({m[0] for m in ms})),
                hidden=tuple(sorted({m[1] for m in ms}, key=lambda t: -rank[t])),
                accepted=all(m[2] in ok for m in ms)))
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
