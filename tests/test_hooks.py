"""Tests for lectkit.hooks, with real git commits and pushes (lect id fx)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lectkit import hooks, proposal  # noqa: E402

FX_TIERS = """\
register: 1
tiers:
  - {{id: fx-open, name: Open, sees: [], store: {{path: stores/fx-open, remote: {remote}}}}}
  - {{id: fx-a, name: A, sees: [fx-open], store: {{path: stores/fx-a, remote: none}}}}
"""
REL = "lexicon/fx-nouns.yaml"
# fx-a's copy repeats the container name to add to the list; with no schema here it's
# fx-a's material, released like the field name.
ACCEPT = "fx-open: [gloss, entries]\n"
ID = ["-c", "user.name=fx-tester", "-c", "user.email=fx-tester"]


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *ID, *args], capture_output=True, text=True,
                          check=check)


def setup(tmp_path, remote="allowed"):
    reg = tmp_path / "fx-tiers.yaml"
    reg.write_text(FX_TIERS.format(remote=remote), encoding="utf-8")
    for t, body in {"fx-open": "entries:\n- id: stemA\n  gloss: open gloss wordone\n",
                    "fx-a": "entries:\n- id: stemB\n  gloss: glossqy\n"}.items():
        f = tmp_path / "stores" / t / REL
        f.parent.mkdir(parents=True)
        f.write_text(body, encoding="utf-8")
    kit = tmp_path / "stores" / "fx-a" / ".lectkit" / "accepted_matches.yaml"
    kit.parent.mkdir(parents=True)
    kit.write_text(ACCEPT, encoding="utf-8")
    git(tmp_path / "stores" / "fx-a", "init", "-q")
    low = tmp_path / "stores" / "fx-open"
    git(low, "init", "-q", "-b", "main")
    import install_hooks
    assert install_hooks.main(["--register", str(reg), "--tier", "fx-open", "--repo", str(low)]) == 0
    return reg, low


def write(low, rel, body):
    f = low / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    git(low, "add", rel)


def commit(low, msg="fx change", verify=True):
    return git(low, "commit", "-q", "-m", msg, *([] if verify else ["--no-verify"]), check=False)


def bare_remote(tmp_path, low):
    remote = tmp_path / "fx-remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, capture_output=True)
    git(low, "remote", "add", "origin", str(remote))
    return remote


def push(low):
    return git(low, "push", "-q", "origin", "main", check=False)


def test_a_clean_commit_passes_and_leaves_evidence(tmp_path):
    """@AC-commit_hooks-1. A clean commit is made and its evidence is current."""
    reg, low = setup(tmp_path)
    write(low, REL, "entries:\n- id: stemA\n  gloss: open gloss wordone\n")
    r = commit(low)
    assert r.returncode == 0, r.stderr
    tree = git(low, "rev-parse", "HEAD^{tree}").stdout.strip()
    assert hooks.evidence_problems(reg, "fx-open", low, tree) == []


def test_a_staged_leak_is_refused(tmp_path):
    """@AC-commit_hooks-2. A staged leak refuses the commit, by file and line only."""
    reg, low = setup(tmp_path)
    write(low, "fx-notes.md", "glossqy\n")
    r = commit(low)
    assert r.returncode != 0
    assert "fx-notes.md:1: not allowed in fx-open" in r.stderr and "glossqy" not in r.stderr
    assert git(low, "rev-parse", "--verify", "HEAD", check=False).returncode != 0


def test_evidence_goes_stale_when_a_higher_store_changes(tmp_path):
    """@AC-commit_hooks-3. A changed higher store or register makes evidence stale."""
    reg, low = setup(tmp_path)
    write(low, "fx-notes.md", "fine\n")
    assert commit(low).returncode == 0
    tree = git(low, "rev-parse", "HEAD^{tree}").stdout.strip()
    (tmp_path / "stores" / "fx-a" / "fx-a-more.md").write_text("fine\n", encoding="utf-8")
    assert hooks.evidence_problems(reg, "fx-open", low, tree) == ["fx-a: store has changed since the scan"]
    (tmp_path / "fx-tiers.yaml").write_text(FX_TIERS.format(remote="allowed") + "\n", encoding="utf-8")
    assert "the register has changed since the scan" in hooks.evidence_problems(reg, "fx-open", low, tree)


def test_a_clean_push_passes(tmp_path):
    """@AC-commit_hooks-10. A clean push goes ahead."""
    reg, low = setup(tmp_path)
    bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "fine\n")
    assert commit(low).returncode == 0
    r = push(low)
    assert r.returncode == 0, r.stderr


def test_every_pushed_commit_is_screened_not_only_the_last(tmp_path):
    """@AC-commit_hooks-11. An earlier commit that skipped its hook is screened on push."""
    reg, low = setup(tmp_path)
    bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "glossqy\n")
    assert commit(low, verify=False).returncode == 0          # skipped the hook
    write(low, "fx-notes.md", "fixed\n")
    assert commit(low).returncode == 0
    r = push(low)
    assert r.returncode != 0 and "not allowed in fx-open" in r.stderr


def test_a_commit_message_is_screened_on_push(tmp_path):
    """@AC-commit_hooks-14. A commit message is screened on push, without echoing it."""
    reg, low = setup(tmp_path)
    bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "fine\n")
    assert commit(low, msg="add glossqy notes").returncode != 0      # the commit-msg hook refuses
    # A commit can still arrive unscreened (made before the hook, or elsewhere): push catches it.
    assert commit(low, msg="add glossqy notes", verify=False).returncode == 0
    r = push(low)
    assert r.returncode != 0
    import re
    assert re.search(re.escape(proposal.MESSAGE_REL) + r":\d+: not allowed", r.stderr)
    assert "glossqy" not in r.stderr


def test_commits_the_remote_has_are_not_screened_again(tmp_path):
    """@AC-commit_hooks-12. Commits the remote already has aren't screened again."""
    reg, low = setup(tmp_path)
    remote = bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "glossqy\n")
    assert commit(low, verify=False).returncode == 0
    git(low, "push", "-q", "--no-verify", "origin", "main")       # already published
    write(low, "fx-notes.md", "fixed\n")
    assert commit(low).returncode == 0
    assert push(low).returncode == 0                               # only the new commit


def test_a_store_without_a_remote_never_pushes(tmp_path):
    """@AC-commit_hooks-17. A tier with remote: none refuses every push."""
    reg, low = setup(tmp_path, remote="none")
    bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "fine\n")
    assert commit(low).returncode == 0
    r = push(low)
    assert r.returncode != 0 and "allows no remote" in r.stderr


def test_an_absent_higher_store_refuses_the_commit(tmp_path):
    """@AC-commit_hooks-5. An absent higher store refuses the commit as a gap."""
    import shutil
    reg, low = setup(tmp_path)
    shutil.rmtree(tmp_path / "stores" / "fx-a")
    write(low, "fx-notes.md", "fine\n")
    r = commit(low)
    assert r.returncode != 0 and "[GAP]" in r.stderr


def test_install_leaves_a_foreign_hook_alone(tmp_path):
    """@AC-commit_hooks-19. A hook lect-kit didn't write is replaced only with --force."""
    import install_hooks
    reg, low = setup(tmp_path)
    (low / ".git" / "hooks" / "pre-commit").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    args = ["--register", str(reg), "--tier", "fx-open", "--repo", str(low)]
    assert install_hooks.main(args) == 1
    assert install_hooks.main(args + ["--force"]) == 0
    assert install_hooks.MARK in (low / ".git" / "hooks" / "pre-commit").read_text(encoding="utf-8")


# --- second review ------------------------------------------------------------------

def test_an_author_name_is_screened_on_push(tmp_path):
    """@AC-commit_hooks-14. An author name is screened on push, without echoing it."""
    reg, low = setup(tmp_path)
    bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "fine\n")
    r = subprocess.run(["git", "-C", str(low), "-c", "user.name=glossqy", "-c",
                        "user.email=fx-tester", "commit", "-q", "-m", "fine"],
                       capture_output=True, text=True)
    assert r.returncode != 0                                         # refused at commit now
    r = subprocess.run(["git", "-C", str(low), "-c", "user.name=glossqy", "-c",
                        "user.email=fx-tester", "commit", "-q", "--no-verify", "-m", "fine"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    r = push(low)
    assert r.returncode != 0 and "glossqy" not in r.stderr


def test_a_file_name_is_screened(tmp_path):
    """@AC-proposal_scan-6. A folder name is screened through the list of paths."""
    reg, low = setup(tmp_path)
    write(low, "glossqy/fx-notes.md", "fine\n")
    r = commit(low)
    assert r.returncode != 0 and f"{proposal.PATHS_REL}:" in r.stderr


def test_an_annotated_tag_message_is_screened(tmp_path):
    """@AC-commit_hooks-15. An annotated tag's message is screened on push."""
    reg, low = setup(tmp_path)
    bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "fine\n")
    assert commit(low).returncode == 0
    assert push(low).returncode == 0
    git(low, "tag", "-a", "fx-v1", "-m", "release glossqy")
    r = git(low, "push", "-q", "origin", "fx-v1", check=False)
    assert r.returncode != 0 and "not allowed" in r.stderr


def test_stale_tracking_refs_dont_hide_commits(tmp_path):
    """@AC-commit_hooks-13. A tracking ref that claims the remote has a commit doesn't hide it."""
    reg, low = setup(tmp_path)
    bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "glossqy\n")
    assert commit(low, verify=False).returncode == 0
    head = git(low, "rev-parse", "HEAD").stdout.strip()
    git(low, "update-ref", "refs/remotes/origin/fake", head)     # claims the remote has it
    r = push(low)
    assert r.returncode != 0 and "not allowed in fx-open" in r.stderr


def test_an_unreadable_update_line_refuses(tmp_path):
    """@AC-commit_hooks-16. An update line the hook can't read refuses the push."""
    import io
    import lectkit_hook
    reg, low = setup(tmp_path)
    code = lectkit_hook.main(["pre-push", "--register", str(reg), "--tier", "fx-open",
                              "--repo", str(low), "origin", "x"], stdin=io.StringIO("garbage\n"))
    assert code == 1


def test_a_tier_with_nothing_above_it_commits(tmp_path):
    """@AC-commit_hooks-6. A tier no other tier sees commits at once."""
    reg, _ = setup(tmp_path)
    top = tmp_path / "stores" / "fx-a"
    import install_hooks
    assert install_hooks.main(["--register", str(reg), "--tier", "fx-a", "--repo", str(top)]) == 0
    write(top, "fx-a-notes.md", "glossqy\n")
    r = commit(top)
    assert r.returncode == 0, r.stderr


def test_a_registered_term_in_an_excluded_file_refuses_the_commit(tmp_path):
    """@AC-commit_hooks-7. A registered term in an excluded file refuses; in material it commits."""
    reg, _ = setup(tmp_path)
    terms = tmp_path / "fx-a-terms.yaml"
    terms.write_text("entries:\n- {id: t1, label: x, variants: [fxguardq]}\n", encoding="utf-8")
    reg.write_text(reg.read_text(encoding="utf-8").replace(
        "store: {path: stores/fx-a, remote: none}}",
        "store: {path: stores/fx-a, remote: none}, terms: [fx-a-terms.yaml]}"), encoding="utf-8")
    top = tmp_path / "stores" / "fx-a"
    write(top, ".lectkit/not_material.txt", "/README.md\n")     # staged, as the guard reads it
    import install_hooks
    assert install_hooks.main(["--register", str(reg), "--tier", "fx-a", "--repo", str(top)]) == 0
    write(top, "README.md", "about fxguardq here\n")
    r = commit(top)
    assert r.returncode != 0 and "README.md:1: a registered term" in r.stderr
    assert "fxguardq" not in r.stderr
    write(top, "README.md", "a plain readme\n")
    write(top, "notes/fx-a-notes.md", "about fxguardq here\n")     # material: allowed here
    assert commit(top).returncode == 0



def test_the_guard_reads_the_staged_exclusion_list(tmp_path):
    """@AC-commit_hooks-8. The guard reads the staged exclusion list, not the working copy."""
    reg, _ = setup(tmp_path)
    terms = tmp_path / "fx-a-terms.yaml"
    terms.write_text("entries:\n- {id: t1, label: x, variants: [fxguardq]}\n", encoding="utf-8")
    reg.write_text(reg.read_text(encoding="utf-8").replace(
        "store: {path: stores/fx-a, remote: none}}",
        "store: {path: stores/fx-a, remote: none}, terms: [fx-a-terms.yaml]}"), encoding="utf-8")
    top = tmp_path / "stores" / "fx-a"
    import install_hooks
    assert install_hooks.main(["--register", str(reg), "--tier", "fx-a", "--repo", str(top)]) == 0
    write(top, ".lectkit/not_material.txt", "/docs/\n")          # staged: a folder pattern
    write(top, "docs/fx-a-guide.md", "about fxguardq\n")
    (top / ".lectkit" / "not_material.txt").write_text("# nothing\n", encoding="utf-8")  # working copy
    r = commit(top)
    assert r.returncode != 0 and "docs/fx-a-guide.md:1: a registered term" in r.stderr


def test_the_guard_refuses_when_a_term_register_is_missing(tmp_path):
    """@AC-commit_hooks-9. A missing term register refuses the commit."""
    reg, _ = setup(tmp_path)
    reg.write_text(reg.read_text(encoding="utf-8").replace(
        "store: {path: stores/fx-a, remote: none}}",
        "store: {path: stores/fx-a, remote: none}, terms: [fx-missing.yaml]}"), encoding="utf-8")
    top = tmp_path / "stores" / "fx-a"
    import install_hooks
    assert install_hooks.main(["--register", str(reg), "--tier", "fx-a", "--repo", str(top)]) == 0
    write(top, "fx-a-notes.md", "fine\n")
    r = commit(top)
    assert r.returncode != 0 and "term register" in r.stderr


def test_evidence_must_name_exactly_the_higher_tiers(tmp_path):
    """@AC-commit_hooks-4. Evidence that doesn't list every higher tier isn't current."""
    import json
    reg, low = setup(tmp_path)
    write(low, "fx-notes.md", "fine\n")
    assert commit(low).returncode == 0
    tree = git(low, "rev-parse", "HEAD^{tree}").stdout.strip()
    f = low / ".git" / proposal.EVIDENCE_DIR / f"{tree}.json"
    ev = json.loads(f.read_text(encoding="utf-8"))
    f.write_text(json.dumps({**ev, "screened_for": []}), encoding="utf-8")
    assert hooks.evidence_problems(reg, "fx-open", low, tree) == [
        "the evidence doesn't cover exactly the higher tiers"]


def test_a_remote_that_cant_be_asked_means_every_commit_is_screened(tmp_path):
    """@AC-commit_hooks-13. With no answer from the remote, every commit back to the root is screened."""
    reg, low = setup(tmp_path)
    bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "glossqy\n")
    assert commit(low, verify=False).returncode == 0
    git(low, "push", "-q", "--no-verify", "origin", "main")       # the real remote has it
    write(low, "fx-notes.md", "fixed\n")
    assert commit(low).returncode == 0
    head = git(low, "rev-parse", "HEAD").stdout.strip()
    said = []
    code = hooks.pre_push(reg, "fx-open", low, str(tmp_path / "fx-nowhere.git"),
                          [f"refs/heads/main {head} refs/heads/main {hooks.ZERO}"], said.append)
    assert code == 1 and any("not allowed in fx-open" in s for s in said)


def test_install_names_the_register_tier_and_kit_by_absolute_path(tmp_path):
    """@AC-commit_hooks-18. Both hooks name the register, tier and kit; another checkout gets none."""
    import install_hooks
    reg, low = setup(tmp_path)
    for name in ("pre-commit", "pre-push"):
        text = (low / ".git" / "hooks" / name).read_text(encoding="utf-8")
        assert reg.resolve().as_posix() in text and "--tier fx-open" in text
        assert install_hooks.HOOK.as_posix() in text
    other = tmp_path / "fx-elsewhere"
    other.mkdir()
    git(other, "init", "-q")
    assert install_hooks.main(["--register", str(reg), "--tier", "fx-open", "--repo", str(other)]) == 1
    assert not (other / ".git" / "hooks" / "pre-commit").exists()


def test_a_commit_in_a_linked_worktree_is_refused(tmp_path):
    """@AC-commit_hooks-20. A linked worktree isn't the registered store, so its commits refuse."""
    reg, low = setup(tmp_path)
    write(low, "fx-notes.md", "fine\n")
    assert commit(low).returncode == 0
    wt = tmp_path / "fx-worktree"
    git(low, "worktree", "add", "-q", str(wt))
    write(wt, "fx-more.md", "fine\n")
    r = commit(wt)
    assert r.returncode != 0 and "isn't the store" in r.stderr


def test_a_held_message_is_refused_when_the_commit_is_made(tmp_path):
    """@AC-commit_hooks-21. The commit-msg hook screens the message and author lines at commit."""
    reg, low = setup(tmp_path)
    write(low, "fx-notes.md", "fine\n")
    r = commit(low, "fx note about glossqy")
    assert r.returncode != 0 and "commit message" in r.stderr
    assert git(low, "rev-list", "--all", check=False).stdout == ""      # nothing committed
    assert commit(low, "fx note").returncode == 0
