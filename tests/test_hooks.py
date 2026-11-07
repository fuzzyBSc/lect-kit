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
ACCEPT = ("- {text: gloss, tier: fx-open, reason: field name, by: 'human:fx-reviewer',"
          " at: '2026-01-01T00:00:00+00:00'}\n")
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
    reg, low = setup(tmp_path)
    write(low, REL, "entries:\n- id: stemA\n  gloss: open gloss wordone\n")
    r = commit(low)
    assert r.returncode == 0, r.stderr
    tree = git(low, "rev-parse", "HEAD^{tree}").stdout.strip()
    assert hooks.evidence_problems(reg, "fx-open", low, tree) == []


def test_a_staged_leak_is_refused(tmp_path):
    reg, low = setup(tmp_path)
    write(low, "fx-notes.md", "glossqy\n")
    r = commit(low)
    assert r.returncode != 0
    assert "fx-notes.md:1: not allowed in fx-open" in r.stderr and "glossqy" not in r.stderr
    assert git(low, "rev-parse", "--verify", "HEAD", check=False).returncode != 0


def test_evidence_goes_stale_when_a_higher_store_changes(tmp_path):
    reg, low = setup(tmp_path)
    write(low, "fx-notes.md", "fine\n")
    assert commit(low).returncode == 0
    tree = git(low, "rev-parse", "HEAD^{tree}").stdout.strip()
    (tmp_path / "stores" / "fx-a" / "fx-a-more.md").write_text("fine\n", encoding="utf-8")
    assert hooks.evidence_problems(reg, "fx-open", low, tree) == ["fx-a: store has changed since the scan"]
    (tmp_path / "fx-tiers.yaml").write_text(FX_TIERS.format(remote="allowed") + "\n", encoding="utf-8")
    assert "the register has changed since the scan" in hooks.evidence_problems(reg, "fx-open", low, tree)


def test_a_clean_push_passes(tmp_path):
    reg, low = setup(tmp_path)
    bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "fine\n")
    assert commit(low).returncode == 0
    r = push(low)
    assert r.returncode == 0, r.stderr


def test_every_pushed_commit_is_screened_not_only_the_last(tmp_path):
    reg, low = setup(tmp_path)
    bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "glossqy\n")
    assert commit(low, verify=False).returncode == 0          # skipped the hook
    write(low, "fx-notes.md", "fixed\n")
    assert commit(low).returncode == 0
    r = push(low)
    assert r.returncode != 0 and "not allowed in fx-open" in r.stderr


def test_a_commit_message_is_screened_on_push(tmp_path):
    reg, low = setup(tmp_path)
    bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "fine\n")
    assert commit(low, msg="add glossqy notes").returncode == 0      # pre-commit can't see it
    r = push(low)
    assert r.returncode != 0
    import re
    assert re.search(re.escape(proposal.MESSAGE_REL) + r":\d+: not allowed", r.stderr)
    assert "glossqy" not in r.stderr


def test_commits_the_remote_has_are_not_screened_again(tmp_path):
    reg, low = setup(tmp_path)
    remote = bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "glossqy\n")
    assert commit(low, verify=False).returncode == 0
    git(low, "push", "-q", "--no-verify", "origin", "main")       # already published
    write(low, "fx-notes.md", "fixed\n")
    assert commit(low).returncode == 0
    assert push(low).returncode == 0                               # only the new commit


def test_a_store_without_a_remote_never_pushes(tmp_path):
    reg, low = setup(tmp_path, remote="none")
    bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "fine\n")
    assert commit(low).returncode == 0
    r = push(low)
    assert r.returncode != 0 and "allows no remote" in r.stderr


def test_an_absent_higher_store_refuses_the_commit(tmp_path):
    import shutil
    reg, low = setup(tmp_path)
    shutil.rmtree(tmp_path / "stores" / "fx-a")
    write(low, "fx-notes.md", "fine\n")
    r = commit(low)
    assert r.returncode != 0 and "[GAP]" in r.stderr


def test_install_leaves_a_foreign_hook_alone(tmp_path):
    import install_hooks
    reg, low = setup(tmp_path)
    (low / ".git" / "hooks" / "pre-commit").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    args = ["--register", str(reg), "--tier", "fx-open", "--repo", str(low)]
    assert install_hooks.main(args) == 1
    assert install_hooks.main(args + ["--force"]) == 0
    assert install_hooks.MARK in (low / ".git" / "hooks" / "pre-commit").read_text(encoding="utf-8")


# --- second review ------------------------------------------------------------------

def test_an_author_name_is_screened_on_push(tmp_path):
    reg, low = setup(tmp_path)
    bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "fine\n")
    r = subprocess.run(["git", "-C", str(low), "-c", "user.name=glossqy", "-c",
                        "user.email=fx-tester", "commit", "-q", "-m", "fine"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    r = push(low)
    assert r.returncode != 0 and "glossqy" not in r.stderr


def test_a_file_name_is_screened(tmp_path):
    reg, low = setup(tmp_path)
    write(low, "glossqy/fx-notes.md", "fine\n")
    r = commit(low)
    assert r.returncode != 0 and f"{proposal.PATHS_REL}:" in r.stderr


def test_an_annotated_tag_message_is_screened(tmp_path):
    reg, low = setup(tmp_path)
    bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "fine\n")
    assert commit(low).returncode == 0
    assert push(low).returncode == 0
    git(low, "tag", "-a", "fx-v1", "-m", "release glossqy")
    r = git(low, "push", "-q", "origin", "fx-v1", check=False)
    assert r.returncode != 0 and "not allowed" in r.stderr


def test_stale_tracking_refs_dont_hide_commits(tmp_path):
    reg, low = setup(tmp_path)
    bare_remote(tmp_path, low)
    write(low, "fx-notes.md", "glossqy\n")
    assert commit(low, verify=False).returncode == 0
    head = git(low, "rev-parse", "HEAD").stdout.strip()
    git(low, "update-ref", "refs/remotes/origin/fake", head)     # claims the remote has it
    r = push(low)
    assert r.returncode != 0 and "not allowed in fx-open" in r.stderr


def test_an_unreadable_update_line_refuses(tmp_path):
    import io
    import lectkit_hook
    reg, low = setup(tmp_path)
    code = lectkit_hook.main(["pre-push", "--register", str(reg), "--tier", "fx-open",
                              "--repo", str(low), "origin", "x"], stdin=io.StringIO("garbage\n"))
    assert code == 1
