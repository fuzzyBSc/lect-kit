"""Local commit and push hooks for a store's checkout.

Carries out knowledge/spec_classification.md, "Commit and push hooks". Hooks run locally,
by someone who holds every higher store they need. A commit rests on current evidence for
its tree; a push screens every commit it would publish, message included.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Callable, Iterable

from lectkit import audience_db, denylist, proposal, tiers

ZERO = "0" * 40


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise proposal.ProposalError(f"git {args[0]} failed in this store")
    return r.stdout


def evidence_problems(register_path: Path, low: str, repo: Path, tree: str) -> list[str]:
    """Why the evidence for `tree` isn't current; empty when it is."""
    reg = tiers.load(register_path)
    if reg.problems:
        return ["the register has problems"]
    f = proposal.git_dir(repo) / proposal.EVIDENCE_DIR / f"{tree}.json"
    if not f.is_file():
        return ["no evidence for this tree"]
    try:
        ev = json.loads(f.read_text(encoding="utf-8"))
    except ValueError:
        return ["the evidence record is damaged"]
    out = []
    want = sorted(proposal.higher_tiers(reg, low))
    if ev.get("tier") != low or ev.get("tree") != tree:
        out.append("the evidence is for another store or tree")
    if ev.get("screened_for") != want or sorted(ev.get("higher_digests", {})) != want:
        out.append("the evidence doesn't cover exactly the higher tiers")
    if ev.get("register_digest") != proposal._file_digest(register_path):
        out.append("the register has changed since the scan")
    for t in want:
        store = reg.tiers[t].store_path
        if store is None or not store.is_dir() or tiers.git_remotes(store) is None:
            out.append(f"{t}: store not on this machine")
        elif audience_db.store_digest(t, store, skip_kit=True) != ev.get("higher_digests", {}).get(t):
            out.append(f"{t}: store has changed since the scan")
    return out


def _report(res: proposal.ProposalResult, say: Callable[[str], None], what: str) -> bool:
    """Print a proposal result; True when it passes."""
    for v in res.verdicts:
        if v["outcome"] == "hold":
            causes = ", ".join(f"{k} {n}" for k, n in v.get("causes", {}).items())
            say(f"[HOLD] {what}: screened for {v['screened_for']} (held by {causes})")
            for loc in v["locations"]:
                say(f"  {loc['rel']}:{loc['line']}: not allowed in {res.tier}")
    for g in res.gaps:
        say(f"[GAP] {what}: {g} store not on this machine; not screened for it")
    return not res.held and not res.gaps and bool(res.verdicts)


def excluded_file_hits(reg, tier: str, repo: Path, tree: str) -> list[tuple[str, int]]:
    """(path, line) where a file the tier excludes from its material, as committed in
    `tree`, holds a term from the tier's own term registers. An excluded file isn't
    looked for in lower stores, so a registered term must not sit in one."""
    t = reg.tiers[tier]
    if not t.terms:
        return []
    missing = [p for p in t.terms if not p.is_file()]
    if missing:
        raise proposal.ProposalError(f"{tier}: a term register named in the register is missing")
    files = proposal.tree_files(repo, tree)
    staged = files.get(audience_db.EXCLUDE_FILE)
    if staged is None:
        return []
    blob = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", staged[1]], capture_output=True)
    try:
        patterns = audience_db.parse_patterns(blob.stdout.decode("utf-8-sig"))
    except (UnicodeDecodeError, audience_db.BuildError) as e:
        raise proposal.ProposalError(f"{tier}: the staged exclusion list can't be read: {e}") from None
    if not t.terms or not patterns:
        return []
    try:
        pats = denylist.matchers(t.terms)
    except SystemExit:
        raise proposal.ProposalError(f"{tier}: a term register can't be read") from None
    out = []
    for path, (mode, sha) in sorted(files.items()):
        if not audience_db.excluded(patterns, path):
            continue
        blob = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", sha], capture_output=True)
        text = blob.stdout.decode("utf-8", "replace")
        out += [(path, n) for n in denylist.hits(text.splitlines(), pats)]
    return out


def pre_commit(register_path: Path, low: str, repo: Path,
               say: Callable[[str], None] = print) -> int:
    try:
        reg = tiers.load(register_path)
        if reg.problems or low not in reg.tiers:
            say("[REFUSED] the register has problems or doesn't name this tier")
            return 1
        guarded = excluded_file_hits(reg, low, repo, proposal.staged_tree(repo))
        if guarded:
            for path, n in guarded:
                say(f"[REFUSED] {path}:{n}: a registered term in a file this tier excludes from "
                    f"its material; move it under the tier's material or rewrite it")
            return 1
        if reg.tiers[low].screening_only:
            bad = _screening_scope(reg, low, repo)
            if bad:
                for p in bad:
                    say(f"[REFUSED] {p}")
                return 1
        if not proposal.higher_tiers(reg, low):
            return 0                     # no tier sits above this one: nothing can be hidden from it
        tree = proposal.staged_tree(repo)
        if not evidence_problems(register_path, low, repo, tree):
            return 0
        res = proposal.run(register_path, low, repo, tree)
        if not _report(res, say, "staged tree"):
            say("[REFUSED] the commit isn't screened clean; fix the lines above, or review "
                "them in the higher tier, then commit again")
            return 1
        proposal.write_evidence(repo, res)
        left = evidence_problems(register_path, low, repo, tree)
        if left:
            for p in left:
                say(f"[REFUSED] {p}")
            return 1
        return 0
    except proposal.ProposalError as e:
        say(f"[REFUSED] {e}")
        return 1


def _remote_has(repo: Path, remote: str) -> list[str]:
    """Commits the remote really has, from the remote itself, that exist here.

    Local remote-tracking refs aren't trusted: they can be stale, point at another
    repository after a URL change, or be made by hand. If the remote can't be asked,
    nothing is excluded and everything is screened."""
    if not remote:
        return []
    r = subprocess.run(["git", "-C", str(repo), "ls-remote", remote], capture_output=True, text=True)
    if r.returncode != 0:
        return []
    shas = {line.split()[0] for line in r.stdout.splitlines() if line.strip()}
    have = []
    for s in sorted(shas):
        t = subprocess.run(["git", "-C", str(repo), "cat-file", "-t", s], capture_output=True, text=True)
        if t.returncode == 0 and t.stdout.strip() in ("commit", "tag"):
            have.append(s)
    return have


def _commits(repo: Path, local: str, remote_sha: str, remote: str) -> list[str]:
    exclude = [remote_sha] if remote_sha != ZERO else _remote_has(repo, remote)
    args = ["rev-list", "--reverse", local] + ([f"^{s}" for s in exclude])
    return _git(repo, *args).split()


def _object_text(repo: Path, sha: str) -> str:
    """The whole commit or tag object as published: headers (author, committer, tagger,
    embedded merged-tag messages, signatures) and message. A message in another encoding
    is decoded with it, and one that can't be decoded refuses."""
    body = subprocess.run(["git", "-C", str(repo), "cat-file", "-p", sha], capture_output=True)
    if body.returncode != 0:
        raise proposal.ProposalError("git cat-file failed in this store")
    raw = body.stdout
    head = raw.split(b"\n\n", 1)[0]
    enc = "utf-8"
    for line in head.split(b"\n"):
        if line.startswith(b"encoding "):
            enc = line[len(b"encoding "):].decode("ascii", "replace").strip()
    try:
        return raw.decode(enc)
    except (LookupError, UnicodeDecodeError):
        raise proposal.ProposalError(f"{sha[:12]}: can't be read as text in its encoding") from None


def pre_push(register_path: Path, low: str, repo: Path, remote: str, updates: Iterable[str],
             say: Callable[[str], None] = print) -> int:
    try:
        reg = tiers.load(register_path)
        if reg.problems or low not in reg.tiers:
            say("[REFUSED] the register has problems")
            return 1
        if reg.tiers[low].remote == "none":
            say(f"[REFUSED] {low} is kept off every server: its tier allows no remote")
            return 1
        for line in updates:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) != 4:
                say("[REFUSED] git sent an update this hook can't read")
                return 1
            local_ref, local_sha, _remote_ref, remote_sha = parts
            if local_sha == ZERO:
                continue                 # deleting a remote ref publishes nothing
            if _git(repo, "cat-file", "-t", local_sha).strip() == "tag":
                res = proposal.run(register_path, low, repo,
                                   _git(repo, "rev-parse", f"{local_sha}^{{tree}}").strip(),
                                   _object_text(repo, local_sha))
                if not _report(res, say, f"tag {local_ref}"):
                    say("[REFUSED] the push isn't screened clean")
                    return 1
            for c in _commits(repo, local_sha, remote_sha, remote):
                tree = _git(repo, "rev-parse", f"{c}^{{tree}}").strip()
                res = proposal.run(register_path, low, repo, tree, _object_text(repo, c))
                if not _report(res, say, f"commit {c[:12]}"):
                    say("[REFUSED] the push isn't screened clean")
                    return 1
        return 0
    except proposal.ProposalError as e:
        say(f"[REFUSED] {e}")
        return 1


def _screening_scope(reg, tier: str, repo: Path) -> list[str]:
    """A screening-only tier's staged files, checked for prose (lectkit/screening_scope.py)."""
    from lectkit import audience_db, screening_scope
    store = reg.tiers[tier].store_path
    pats = audience_db.not_material(store)
    paths = subprocess.run(["git", "-c", "core.quotepath=off", "-C", str(repo), "ls-files"], capture_output=True,
                           text=True, check=True).stdout.splitlines()
    read = lambda rel: subprocess.run(["git", "-C", str(repo), "show", f":{rel}"],  # noqa: E731
                                      capture_output=True, check=True).stdout.decode("utf-8")
    terms = {p.relative_to(store.resolve()).as_posix() for p in reg.tiers[tier].terms
             if store.resolve() in p.parents}
    return screening_scope.problems([p for p in paths if p], read, terms,
                                    lambda rel: audience_db.excluded(pats, rel))


def commit_msg(register_path: Path, low: str, repo: Path, msg_file: Path,
               say: Callable[[str], None] = print) -> int:
    """Screen a commit's message and its author and committer lines before the commit is
    made. The pre-commit hook can't: neither exists yet when it runs, so without this they
    were first screened at push."""
    try:
        reg = tiers.load(register_path)
        if reg.problems or low not in reg.tiers:
            say("[REFUSED] the register has problems or doesn't name this tier")
            return 1
        if not proposal.higher_tiers(reg, low):
            return 0
        raw = Path(msg_file).read_text(encoding="utf-8")
        message = "".join(f"{x}\n" for x in raw.splitlines() if not x.startswith("#"))
        ident = {k: _git(repo, "var", f"GIT_{k.upper()}_IDENT").strip()
                 for k in ("author", "committer")}
        text = f"author {ident['author']}\ncommitter {ident['committer']}\n\n{message}"
        res = proposal.run(register_path, low, repo, proposal.staged_tree(repo), text)
        if not _report(res, say, "commit message"):
            say(f"[REFUSED] the message or author lines aren't screened clean (they are "
                f"{proposal.MESSAGE_REL} above); reword them, then commit again")
            return 1
        return 0
    except proposal.ProposalError as e:
        say(f"[REFUSED] {e}")
        return 1
