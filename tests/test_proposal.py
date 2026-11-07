"""Tests for lectkit.proposal, with real git checkouts of abstract stores (lect id fx)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lectkit import proposal  # noqa: E402

FX_TIERS = """\
register: 1
tiers:
  - {id: fx-open, name: Open, sees: [], store: {path: stores/fx-open, remote: allowed}}
  - {id: fx-a, name: A, sees: [fx-open], store: {path: stores/fx-a, remote: none}}
  - {id: fx-p, name: P, sees: [fx-open], store: {path: stores/fx-p, remote: none}}
"""
REL = "lexicon/fx-nouns.yaml"
OPEN_LEX = "entries:\n- id: stemA\n  gloss: open gloss wordone\n"
A_LEX = "entries:\n- id: stemB\n  gloss: glossqy\n"
P_LEX = "entries:\n- id: stemP\n  gloss: glossqp\n"


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def setup(tmp_path, with_p=True):
    (tmp_path / "fx-tiers.yaml").write_text(FX_TIERS, encoding="utf-8")
    stores = {"fx-open": OPEN_LEX, "fx-a": A_LEX}
    if with_p:
        stores["fx-p"] = P_LEX
    for t, body in stores.items():
        f = tmp_path / "stores" / t / REL
        f.parent.mkdir(parents=True)
        f.write_text(body, encoding="utf-8")
    # Each higher tier has decided once that the field name it shares is not a leak.
    for t in stores:
        if t != "fx-open":
            kit = tmp_path / "stores" / t / ".lectkit" / "accepted_matches.yaml"
            kit.parent.mkdir(parents=True)
            kit.write_text("- {text: gloss, tier: fx-open, reason: field name,"
                           " by: 'human:fx-reviewer', at: '2026-01-01T00:00:00+00:00'}\n",
                           encoding="utf-8")
    for t in stores:
        if t != "fx-open":
            git(tmp_path / "stores" / t, "init", "-q")   # each store is a checkout of its own
    low = tmp_path / "stores" / "fx-open"
    git(low, "init", "-q")
    git(low, "add", "-A")
    return tmp_path / "fx-tiers.yaml", low


def stage(low, rel, body):
    f = low / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    git(low, "add", rel)


def test_a_clean_proposal_records_evidence(tmp_path):
    reg, low = setup(tmp_path)
    res = proposal.run(reg, "fx-open", low)
    assert sorted(v["screened_for"] for v in res.verdicts) == ["fx-a", "fx-p"]
    assert not res.held and res.gaps == []
    f = proposal.write_evidence(low, res)
    ev = json.loads(f.read_text(encoding="utf-8"))
    assert ev["tree"] == res.tree and ev["screened_for"] == ["fx-a", "fx-p"]
    assert ".git" in f.parts                       # never in the working tree


def test_a_staged_leak_is_held_by_the_tier_it_belongs_to_only(tmp_path):
    reg, low = setup(tmp_path)
    stage(low, "fx-notes.md", "fine\nglossqy here\n")
    res = proposal.run(reg, "fx-open", low)
    by = {v["screened_for"]: v for v in res.verdicts}
    assert by["fx-a"]["outcome"] == "hold"
    assert by["fx-a"]["locations"] == [{"rel": "fx-notes.md", "line": 2}]
    assert by["fx-p"]["outcome"] == "no_match"
    with pytest.raises(proposal.ProposalError):
        proposal.write_evidence(low, res)


def test_the_whole_tree_is_screened_not_only_the_change(tmp_path):
    reg, low = setup(tmp_path)
    stage(low, "fx-old.md", "glossqp\n")                 # already staged earlier
    stage(low, "fx-new.md", "unrelated\n")               # the change being made now
    res = proposal.run(reg, "fx-open", low)
    assert {v["screened_for"]: v["outcome"] for v in res.verdicts}["fx-p"] == "hold"


def test_the_index_is_screened_not_the_working_copy(tmp_path):
    reg, low = setup(tmp_path)
    stage(low, "fx-notes.md", "glossqy\n")
    (low / "fx-notes.md").write_text("cleaned in the working copy only\n", encoding="utf-8")
    assert proposal.run(reg, "fx-open", low).held
    (low / "fx-draft.md").write_text("glossqy\n", encoding="utf-8")   # not staged
    git(low, "add", "fx-notes.md")
    assert not proposal.run(reg, "fx-open", low).held


def test_an_absent_higher_store_is_a_gap(tmp_path):
    reg, low = setup(tmp_path, with_p=False)
    res = proposal.run(reg, "fx-open", low)
    assert res.gaps == ["fx-p"] and [v["screened_for"] for v in res.verdicts] == ["fx-a"]
    with pytest.raises(proposal.ProposalError, match="wasn't screened"):
        proposal.write_evidence(low, res)
    import scan_proposal as cli
    assert cli.main(["--register", str(reg), "--tier", "fx-open", "--repo", str(low)]) == 2


def test_the_checkout_must_be_the_registered_store(tmp_path):
    reg, _ = setup(tmp_path)
    other = tmp_path / "fx-elsewhere"
    other.mkdir()
    git(other, "init", "-q")
    with pytest.raises(proposal.ProposalError, match="isn't the store"):
        proposal.run(reg, "fx-open", other)


GOOD = {"screened_for": "fx-a", "outcome": "no_match", "basis": "pattern-scan",
        "by": "process:lect-kit-scan", "at": "2026-01-01T00:00:00+00:00", "tree": "t1",
        "locations": []}


@pytest.mark.parametrize("bad", [
    {**GOOD, "note": "glossqy"},                              # anything extra is refused
    {**GOOD, "screened_for": "fx-p"},
    {**GOOD, "tree": "t2"},
    {**GOOD, "outcome": "clear"},                             # a pattern scan can't clear
    {**GOOD, "outcome": "hold"},                              # a hold names locations
    {**GOOD, "locations": [{"rel": "x", "line": 1}]},
    {**GOOD, "outcome": "hold", "locations": [{"rel": "x", "line": 1, "text": "glossqy"}]},
])
def test_the_egress_filter(bad):
    with pytest.raises(proposal.ProposalError):
        proposal.accept_verdict(json.dumps(bad), "fx-a", "t1")
    with pytest.raises(proposal.ProposalError):
        proposal.accept_verdict("glossqy is the problem", "fx-a", "t1")
    assert proposal.accept_verdict(json.dumps(GOOD), "fx-a", "t1") == GOOD


def test_cli(tmp_path, capsys):
    import scan_proposal as cli
    reg, low = setup(tmp_path)
    assert cli.main(["--register", str(reg), "--tier", "fx-open", "--repo", str(low)]) == 0
    assert "[EVIDENCE]" in capsys.readouterr().out
    stage(low, "fx-notes.md", "glossqy\n")
    assert cli.main(["--register", str(reg), "--tier", "fx-open", "--repo", str(low)]) == 1
    out = capsys.readouterr().out
    assert "fx-notes.md:1: not allowed in fx-open" in out and "glossqy" not in out


# --- review findings ------------------------------------------------------------------

def test_a_skip_worktree_file_is_still_screened(tmp_path):
    reg, low = setup(tmp_path)
    stage(low, "fx-hidden.md", "glossqy\n")
    git(low, "update-index", "--skip-worktree", "fx-hidden.md")
    (low / "fx-hidden.md").unlink()
    assert proposal.run(reg, "fx-open", low).held


def test_filters_and_line_endings_dont_change_what_is_scanned(tmp_path):
    reg, low = setup(tmp_path)
    (low / ".gitattributes").write_text("*.md filter=fxhide\n", encoding="utf-8")
    git(low, "config", "filter.fxhide.smudge", "echo smudged")
    git(low, "config", "core.autocrlf", "true")
    stage(low, ".gitattributes", "*.md filter=fxhide\n")
    stage(low, "fx-notes.md", "glossqy\n")
    res = proposal.run(reg, "fx-open", low)
    by = {v["screened_for"]: v for v in res.verdicts}
    assert by["fx-a"]["locations"] == [{"rel": "fx-notes.md", "line": 1}]


def test_a_symlink_in_the_tree_is_refused(tmp_path):
    reg, low = setup(tmp_path)
    blob = subprocess.run(["git", "-C", str(low), "hash-object", "-w", "--stdin"],
                          input=b"fx-target", capture_output=True, check=True).stdout.decode().strip()
    git(low, "update-index", "--add", "--cacheinfo", f"120000,{blob},fx-link")
    with pytest.raises(proposal.ProposalError, match="symbolic links"):
        proposal.run(reg, "fx-open", low)


def test_evidence_names_the_scanned_tree_and_the_higher_state(tmp_path):
    reg, low = setup(tmp_path)
    res = proposal.run(reg, "fx-open", low)
    ev = json.loads(proposal.write_evidence(low, res).read_text(encoding="utf-8"))
    tree = subprocess.run(["git", "-C", str(low), "write-tree"], capture_output=True,
                          text=True, check=True).stdout.strip()
    assert ev["tree"] == tree
    assert set(ev["higher_digests"]) == {"fx-a", "fx-p"} and ev["register_digest"]
    # A higher store that changes gives a different digest, so a hook can see the
    # evidence is stale.
    (tmp_path / "stores" / "fx-a" / "fx-a-more.md").write_text("glossqz\n", encoding="utf-8")
    again = proposal.run(reg, "fx-open", low)
    assert again.higher_digests["fx-a"] != ev["higher_digests"]["fx-a"]


def test_no_evidence_when_nothing_was_screened(tmp_path):
    reg_file = tmp_path / "fx-tiers.yaml"
    reg_file.write_text(FX_TIERS, encoding="utf-8")
    low = tmp_path / "stores" / "fx-open"
    low.mkdir(parents=True)
    git(low, "init", "-q")
    stage(low, REL, OPEN_LEX)
    res = proposal.run(reg_file, "fx-open", low)
    assert res.verdicts == [] and res.gaps == ["fx-a", "fx-p"]
    with pytest.raises(proposal.ProposalError, match="no higher tier"):
        proposal.write_evidence(low, res)


def test_a_screen_that_fails_never_passes(tmp_path, monkeypatch):
    reg, low = setup(tmp_path)
    (tmp_path / "stores" / "fx-a" / "fx-bad.yaml").write_text("a: [1\n", encoding="utf-8")
    with pytest.raises(proposal.ProposalError, match="couldn't run"):
        proposal.run(reg, "fx-open", low)


def test_egress_refuses_a_location_outside_the_tree():
    held = {**GOOD, "outcome": "hold", "locations": [{"rel": "glossqy", "line": 1}]}
    with pytest.raises(proposal.ProposalError, match="proposed tree"):
        proposal.accept_verdict(json.dumps(held), "fx-a", "t1", {"fx-notes.md"})
    held = {**GOOD, "outcome": "hold", "locations": [{"rel": "fx-notes.md", "line": 0}]}
    with pytest.raises(proposal.ProposalError):
        proposal.accept_verdict(json.dumps(held), "fx-a", "t1", {"fx-notes.md"})


def test_an_empty_folder_is_not_a_higher_store(tmp_path):
    reg, low = setup(tmp_path, with_p=False)
    (tmp_path / "stores" / "fx-p").mkdir()                # there, but not a checkout
    res = proposal.run(reg, "fx-open", low)
    assert res.gaps == ["fx-p"]
    import scan_proposal as cli
    assert cli.main(["--register", str(reg), "--tier", "fx-open", "--repo", str(low)]) == 2
    assert not (low / ".git" / "lectkit" / "evidence").exists()
