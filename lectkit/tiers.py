"""The tier register: which tiers a project has, who reads what, and where each is stored.

Carries out knowledge/spec_classification.md, "Register file". The kit has no built-in
tier names; a project writes its own register and this module only checks that it is
consistent.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

import yaml

ID = re.compile(r"^[A-Za-z_-][A-Za-z0-9_-]*$")
REMOTE_VALUES = ("allowed", "none")
FORMAT = 1


@dataclass(frozen=True)
class Tier:
    id: str
    name: str
    sees: tuple[str, ...]
    store_path: Path | None
    remote: str
    classifiers: tuple[str, ...] = ()
    terms: tuple[Path, ...] = ()    # the tier's term registers (deny lists), read at run time


@dataclass
class Register:
    path: Path
    tiers: dict[str, Tier] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)

    def closed_pairs(self) -> list[tuple[str, str]]:
        """Pairs of tiers where neither sees the other."""
        out = []
        for a, b in combinations(sorted(self.tiers), 2):
            if b not in self.tiers[a].sees and a not in self.tiers[b].sees:
                out.append((a, b))
        return out

    def readable_from(self, tier_id: str) -> tuple[str, ...]:
        """The tiers a reader of `tier_id` may also see, as the register writes them."""
        return self.tiers[tier_id].sees


def _closure(tiers: dict[str, Tier], start: str) -> set[str]:
    seen: set[str] = set()
    stack = list(tiers[start].sees)
    while stack:
        t = stack.pop()
        if t in seen or t not in tiers:
            continue
        seen.add(t)
        stack.extend(tiers[t].sees)
    return seen


def load(path: str | Path) -> Register:
    """Read and check a register file. Problems are collected, never raised."""
    path = Path(path)
    reg = Register(path=path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        reg.problems.append(f"cannot read register: {e.__class__.__name__}")
        return reg
    if not isinstance(data, dict):
        reg.problems.append("register is not a mapping")
        return reg
    if data.get("register") != FORMAT:
        reg.problems.append(f"register: must be {FORMAT}")
    rows = data.get("tiers")
    if not isinstance(rows, list) or not rows:
        reg.problems.append("tiers: must be a non-empty list")
        return reg

    raw_sees: dict[str, list] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            reg.problems.append(f"tiers[{i}]: not a mapping")
            continue
        tid = str(row.get("id", ""))
        if not ID.match(tid):
            reg.problems.append(f"tiers[{i}]: id {tid!r} is not a valid identifier")
            continue
        if tid in reg.tiers:
            reg.problems.append(f"{tid}: duplicate id")
            continue
        name = row.get("name")
        if not isinstance(name, str) or not name.strip():
            reg.problems.append(f"{tid}: name is required")
        sees = row.get("sees", [])
        if not isinstance(sees, list):
            reg.problems.append(f"{tid}: sees must be a list")
            sees = []
        store = row.get("store")
        store_path = None
        remote = "allowed"
        if not isinstance(store, dict) or not store.get("path"):
            reg.problems.append(f"{tid}: store.path is required")
        else:
            store_path = (path.parent / str(store["path"])).resolve()
            remote = store.get("remote")
            if remote is None:
                reg.problems.append(f"{tid}: store.remote is required")
                remote = "none"
            elif remote not in REMOTE_VALUES:
                reg.problems.append(f"{tid}: store.remote must be one of {', '.join(REMOTE_VALUES)}")
                remote = "none"   # treat an unclear value as the stricter one
        classifiers = row.get("classifiers", [])
        if not isinstance(classifiers, list):
            reg.problems.append(f"{tid}: classifiers must be a list")
            classifiers = []
        terms = row.get("terms", [])
        if not isinstance(terms, list):
            reg.problems.append(f"{tid}: terms must be a list of term-register files")
            terms = []
        term_paths = tuple((path.parent / str(t)).resolve() for t in terms)
        raw_sees[tid] = [str(s) for s in sees]
        reg.tiers[tid] = Tier(tid, str(name or ""), tuple(str(s) for s in sees), store_path,
                              remote, tuple(str(c) for c in classifiers), term_paths)

    for tid, sees in raw_sees.items():
        if tid in sees:
            reg.problems.append(f"{tid}: a tier cannot list itself in sees")
        for s in sees:
            if s not in reg.tiers:
                reg.problems.append(f"{tid}: sees unknown tier {s!r}")
        if len(set(sees)) != len(sees):
            reg.problems.append(f"{tid}: sees lists a tier twice")
    for tid in reg.tiers:
        missing = _closure(reg.tiers, tid) - set(reg.tiers[tid].sees) - {tid}
        for m in sorted(missing):
            reg.problems.append(f"{tid}: sees must also list {m!r} (reachable through another tier)")
        if tid in _closure(reg.tiers, tid):
            reg.problems.append(f"{tid}: sees forms a cycle back to itself")

    by_store: dict[Path, list[str]] = {}
    for t in reg.tiers.values():
        if t.store_path is not None:
            by_store.setdefault(t.store_path, []).append(t.id)
    for p, ids in by_store.items():
        if len(ids) > 1:
            reg.problems.append(f"{', '.join(sorted(ids))}: tiers share one store")
    stores = sorted(by_store)
    for a, b in combinations(stores, 2):
        if a in b.parents or b in a.parents:
            outer, inner = (a, b) if a in b.parents else (b, a)
            reg.problems.append(f"{by_store[inner][0]}: store lies inside the store of {by_store[outer][0]}")
    return reg


def _git(store: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(store), *args], capture_output=True, text=True,
                          check=False)


def git_remotes(store: Path) -> list[str] | None:
    """Remote names of a git store, or None if the store isn't the top of its own checkout.

    A folder inside some other repository is not a checkout of its own: asking it for
    remotes would answer for the parent repository."""
    top = _git(store, "rev-parse", "--show-toplevel")
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != store.resolve():
        return None
    r = _git(store, "remote")
    if r.returncode != 0:
        return None
    return [x for x in r.stdout.split() if x]


def check_stores(reg: Register) -> tuple[list[str], list[str]]:
    """Check each present store against its remote rule. Returns (problems, absent)."""
    problems, absent = [], []
    if shutil.which("git") is None:
        return ["git is not installed, so no store could be checked"], []
    for t in reg.tiers.values():
        if t.store_path is None:
            continue
        if not t.store_path.is_dir():
            absent.append(t.id)
            continue
        remotes = git_remotes(t.store_path)
        if remotes is None:
            problems.append(f"{t.id}: store is not the top of its own git checkout")
        elif t.remote == "none" and remotes:
            problems.append(f"{t.id}: store has {len(remotes)} git remote(s) but its tier allows none")
    return problems, absent


def with_store(reg: Register, tier: str, path: Path) -> Register:
    """A copy of the register in which `tier`'s store is `path`, such as an export of a
    store's staged tree. The register itself is unchanged."""
    from dataclasses import replace
    if tier not in reg.tiers:
        raise KeyError(tier)
    out = Register(path=reg.path, tiers=dict(reg.tiers), problems=list(reg.problems))
    out.tiers[tier] = replace(reg.tiers[tier], store_path=Path(path).resolve())
    return out
