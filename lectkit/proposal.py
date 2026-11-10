"""Proposal scan: screen what a lower store would hold after a commit, for every higher tier.

Carries out knowledge/spec_classification.md, "Proposal scan". The proposal is the whole
staged tree. Each higher tier screens it in its own process, and only a filtered verdict
crosses back.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from lectkit import audience_db, layers, material_cache, scan, tiers
from lectkit.tiers import Register

VERDICT_KEYS = {"screened_for", "outcome", "basis", "by", "at", "tree", "locations", "causes"}
# The kinds of match a held line can have; a verdict counts held lines by them, never by text.
CAUSES = {"value", "token", "passage", "term"}
OUTCOMES = {"hold", "no_match"}
SCREENER = Path(__file__).resolve().parent.parent / "scripts" / "screen_for_tier.py"
EVIDENCE_DIR = "lectkit/evidence"      # inside the lower store's git directory
CACHE_DIR = "lectkit/material"         # inside the screening tier's git directory
MESSAGE_REL = ".lectkit-commit-message"  # where a commit or tag object is scanned, as one more file
PATHS_REL = ".lectkit-paths"             # every path in the tree, one per line: names are published too


class ProposalError(ValueError):
    pass


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise ProposalError(f"git {args[0]} failed in the lower store")
    return r.stdout.strip()


def staged_tree(repo: Path) -> str:
    return _git(repo, "write-tree")


def git_dir(repo: Path) -> Path:
    d = Path(_git(repo, "rev-parse", "--git-dir"))
    return d if d.is_absolute() else (repo / d).resolve()


def tree_files(repo: Path, tree: str) -> dict[str, tuple[str, str]]:
    """{path: (mode, blob)} for every entry of a tree, recursively."""
    r = subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", "-z", "--full-tree", tree],
                       capture_output=True)
    if r.returncode != 0:
        raise ProposalError("git ls-tree failed in the lower store")
    out = {}
    for entry in r.stdout.split(b"\0"):
        if not entry:
            continue
        meta, path = entry.split(b"\t", 1)
        mode, _kind, sha = meta.decode().split()
        out[path.decode("utf-8", "surrogateescape")] = (mode, sha)
    return out


def export_tree(repo: Path, tree: str, dest: Path) -> set[str]:
    """Write every file of `tree` into `dest` byte for byte, as it will be committed.

    Reads blobs straight from the object store, so nothing in the working copy, the
    index flags (skip-worktree, sparse checkout) or the repository's filters, encodings
    and line-ending settings changes what is scanned. A symbolic link or a submodule in
    the tree is an error: neither can be screened. Returns the paths written."""
    files = tree_files(repo, tree)
    targets = []
    for path, (mode, sha) in files.items():
        if mode == "120000":
            raise ProposalError(f"{path}: symbolic links can't be screened")
        if mode == "160000":
            raise ProposalError(f"{path}: submodules can't be screened")
        if mode not in ("100644", "100755"):
            raise ProposalError(f"{path}: an entry of mode {mode} can't be screened")
        target = (dest / path).resolve()
        if not target.is_relative_to(dest.resolve()):
            raise ProposalError(f"{path}: leaves the export")
        targets.append((path, sha, target))
    # Every blob in one `git cat-file --batch`: the same objects, one process.
    r = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch"], capture_output=True,
                       input="".join(f"{sha}\n" for _, sha, _ in targets).encode("ascii"))
    if r.returncode != 0:
        raise ProposalError("the tree can't be read from the object store")
    out, i = r.stdout, 0
    for path, sha, target in targets:
        nl = out.index(b"\n", i)
        head = out[i:nl].split()
        if len(head) != 3 or head[0].decode() != sha or head[1] != b"blob":
            raise ProposalError(f"{path}: can't be read from the object store")
        size = int(head[2])
        data = out[nl + 1:nl + 1 + size]
        if len(data) != size or out[nl + 1 + size:nl + 2 + size] != b"\n":
            raise ProposalError(f"{path}: can't be read from the object store")
        i = nl + 2 + size
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return set(files)


def _file_digest(p: Path) -> str:
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def higher_tiers(reg: Register, low: str) -> list[str]:
    return [t for t in reg.tiers if low in reg.tiers[t].sees]


def screen(reg: Register, tier: str, low: str, export: Path, tree: str) -> dict:
    """Screen `low`'s exported tree for `tier`. Runs inside that tier's own process."""
    view = tiers.with_store(reg, low, export)
    # Only what this screen needs: the proposal's own lines, and the material of the tiers
    # hidden from it, which the screening tier keeps between screens (material_cache.py).
    visible = {low, *reg.tiers[low].sees}
    hidden = {t for t in layers.order(reg, tier) if t not in visible}
    cache = material_cache.MaterialCache(git_dir(reg.tiers[tier].store_path) / CACHE_DIR,
                                         view, tier, _file_digest(reg.path))
    with tempfile.TemporaryDirectory(prefix="lectkit-db-") as d:
        db_path = Path(d) / f"{tier}.sqlite"
        audience_db.build(view, tier, db_path, source_tiers={low}, model_tiers=hidden,
                          cache=cache)
        with audience_db.AudienceDB(db_path) as db:
            rep = scan.scan(db, view, lows={low})
    held = [f for f in rep.open_findings if f.tier == low]
    locations = sorted({(f.rel, f.line) for f in held})
    causes: dict[str, int] = {}
    for f in held:
        for m in f.matches:
            causes[m] = causes.get(m, 0) + 1
    return {
        "screened_for": tier,
        "outcome": "hold" if locations else "no_match",
        "basis": "pattern-scan",
        "by": "process:lect-kit-scan",
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tree": tree,
        "locations": [{"rel": r, "line": n} for r, n in locations],
        "causes": dict(sorted(causes.items())),
    }


def accept_verdict(raw: str, tier: str, tree: str, paths: set[str] | None = None) -> dict:
    """The egress filter: a verdict in the fixed shape, or an error. Nothing else passes."""
    try:
        v = json.loads(raw)
    except ValueError:
        raise ProposalError(f"{tier}: the screen returned something other than a verdict") from None
    if not isinstance(v, dict) or set(v) != VERDICT_KEYS:
        raise ProposalError(f"{tier}: the screen returned something other than a verdict")
    if v["screened_for"] != tier or v["tree"] != tree or v["outcome"] not in OUTCOMES \
            or v["basis"] != "pattern-scan" or not isinstance(v["locations"], list):
        raise ProposalError(f"{tier}: the verdict doesn't match the request")
    for loc in v["locations"]:
        if not (isinstance(loc, dict) and set(loc) == {"rel", "line"}
                and isinstance(loc["rel"], str) and isinstance(loc["line"], int)
                and not isinstance(loc["line"], bool) and loc["line"] >= 1
                and (paths is None or loc["rel"] in paths)):
            raise ProposalError(f"{tier}: a verdict location isn't a file and line of the "
                                f"proposed tree")
    c = v["causes"]
    if not isinstance(c, dict) or set(c) - CAUSES or not all(
            isinstance(n, int) and not isinstance(n, bool) and n >= 1 for n in c.values()):
        raise ProposalError(f"{tier}: a verdict's causes aren't counts by kind of match")
    if (v["outcome"] == "hold") != bool(v["locations"]):
        raise ProposalError(f"{tier}: the verdict's outcome and locations disagree")
    return v


@dataclass
class ProposalResult:
    tier: str
    tree: str
    register_digest: str = ""
    verdicts: list[dict] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    higher_digests: dict[str, str] = field(default_factory=dict)

    @property
    def held(self) -> bool:
        return any(v["outcome"] == "hold" for v in self.verdicts)


def run(register_path: Path, low: str, repo: Path, tree: str | None = None,
        message: str | None = None) -> ProposalResult:
    """Screen `tree` (the staged tree when None) for every higher tier. With `message`, a
    commit message is screened too, as the file MESSAGE_REL of the proposed tree."""
    reg = tiers.load(register_path)
    if reg.problems:
        raise ProposalError("the register has problems; run check_tier_register")
    if low not in reg.tiers:
        raise ProposalError(f"unknown tier {low!r}")
    store = reg.tiers[low].store_path
    if store is None or store.resolve() != Path(repo).resolve():
        raise ProposalError(f"this checkout isn't the store the register gives for {low}")
    tree = tree or staged_tree(repo)
    res = ProposalResult(tier=low, tree=tree, register_digest=_file_digest(register_path))
    with tempfile.TemporaryDirectory(prefix="lectkit-proposal-") as d:
        export = Path(d) / "tree"
        export.mkdir()
        paths = export_tree(repo, tree, export)       # the tree by name: no race with the index
        if PATHS_REL in paths:
            raise ProposalError(f"the tree holds {PATHS_REL}, which is reserved")
        (export / PATHS_REL).write_text("".join(f"{p}\n" for p in sorted(paths)), encoding="utf-8")
        paths.add(PATHS_REL)
        if message is not None:
            if MESSAGE_REL in paths:
                raise ProposalError(f"the tree holds {MESSAGE_REL}, which is reserved")
            (export / MESSAGE_REL).write_text(message, encoding="utf-8")
            paths.add(MESSAGE_REL)
        present = []
        for t in higher_tiers(reg, low):
            ts = reg.tiers[t].store_path
            # A higher store counts only if it is there and is a checkout of its own: an
            # empty or stray folder at that path would screen nothing and pass.
            if ts is None or not ts.is_dir() or tiers.git_remotes(ts) is None:
                res.gaps.append(t)
            else:
                present.append(t)

        def one(t):
            # Each higher tier screens in its own process, reading only the export and its
            # own store, so the screens are independent and run side by side.
            ts = reg.tiers[t].store_path
            before = audience_db.store_digest(t, ts, skip_kit=True)
            r = subprocess.run(
                [sys.executable, "-E", str(SCREENER), "--register", str(register_path),
                 "--tier", t, "--lower", low, "--export", str(export), "--tree", tree],
                capture_output=True, text=True)
            return t, r, before, audience_db.store_digest(t, ts, skip_kit=True)

        workers = max(1, min(len(present), os.cpu_count() or 1))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            done = list(pool.map(one, present))          # results in register order
        for t, r, before, after in done:
            if r.returncode != 0:
                raise ProposalError(f"{t}: the screen couldn't run")
            res.verdicts.append(accept_verdict(r.stdout, t, tree, paths))
            if after != before:
                raise ProposalError(f"{t}: the store changed while it was screening; run again")
            res.higher_digests[t] = before
    return res


def write_evidence(repo: Path, res: ProposalResult) -> Path:
    """Record that every higher tier present found no match in this tree."""
    if res.held:
        raise ProposalError("a held proposal has no evidence to record")
    if not res.verdicts:
        raise ProposalError("no higher tier was screened, so there is no evidence to record")
    if res.gaps:
        raise ProposalError("a higher tier wasn't screened, so there is no evidence to record")
    d = git_dir(repo) / EVIDENCE_DIR
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{res.tree}.json"
    f.write_text(json.dumps({
        "tier": res.tier, "tree": res.tree,
        "screened_for": sorted(v["screened_for"] for v in res.verdicts),
        "register_digest": res.register_digest,
        "higher_digests": dict(sorted(res.higher_digests.items())),
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2) + "\n", encoding="utf-8")
    return f
