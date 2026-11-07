"""Tests for lectkit.tiers, on the Japanese demo register and abstract fixtures (lect id fx)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lectkit import tiers  # noqa: E402

FIXTURE = ROOT / "examples/demo/japanese/jp-tiers.yaml"


def write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "fx-tiers.yaml"
    p.write_text(body, encoding="utf-8")
    return p


def test_fixture_is_consistent():
    reg = tiers.load(FIXTURE)
    assert reg.problems == []
    assert set(reg.tiers) == {"jp-open", "jp-a", "jp-b", "jp-c", "jp-p", "jp-q"}


def test_closed_pairs():
    pairs = set(tiers.load(FIXTURE).closed_pairs())
    assert ("jp-p", "jp-q") in pairs
    assert ("jp-a", "jp-b") in pairs
    assert ("jp-b", "jp-c") not in pairs
    assert ("jp-open", "jp-a") not in pairs


@pytest.mark.parametrize("body, needle", [
    ("register: 1\ntiers:\n - {id: x, name: X, sees: [y], store: {path: s, remote: allowed}}\n",
     "sees unknown tier"),
    ("register: 1\ntiers:\n - {id: x, name: X, sees: [x], store: {path: s, remote: allowed}}\n",
     "cannot list itself"),
    ("register: 1\ntiers:\n - {id: x, name: X, sees: [], store: {path: s, remote: maybe}}\n",
     "store.remote must be"),
    ("register: 1\ntiers:\n - {id: '9x', name: X, sees: [], store: {path: s, remote: none}}\n",
     "not a valid identifier"),
    ("register: 1\ntiers:\n - {id: x, name: X, sees: []}\n", "store.path is required"),
    ("register: 1\ntiers:\n - {id: x, sees: [], store: {path: s, remote: none}}\n",
     "name is required"),
    ("register: 2\ntiers:\n - {id: x, name: X, sees: [], store: {path: s, remote: none}}\n",
     "register: must be 1"),
    ("register: 1\ntiers:\n - {id: x, name: X, sees: [], store: {path: s, remote: none}}\n"
     " - {id: y, name: Y, sees: [], store: {path: s, remote: none}}\n", "share one store"),
    ("register: 1\ntiers:\n - {id: x, name: X, sees: [], store: {path: s, remote: none}}\n"
     " - {id: x, name: X2, sees: [], store: {path: t, remote: none}}\n", "duplicate id"),
])
def test_rejects(tmp_path, body, needle):
    reg = tiers.load(write(tmp_path, body))
    assert any(needle in p for p in reg.problems), reg.problems


def test_sees_must_be_written_in_full(tmp_path):
    body = ("register: 1\ntiers:\n"
            " - {id: o, name: O, sees: [], store: {path: o, remote: allowed}}\n"
            " - {id: a, name: A, sees: [o], store: {path: a, remote: allowed}}\n"
            " - {id: b, name: B, sees: [a], store: {path: b, remote: none}}\n")
    reg = tiers.load(write(tmp_path, body))
    assert any("b: sees must also list 'o'" in p for p in reg.problems)


def test_cycle(tmp_path):
    body = ("register: 1\ntiers:\n"
            " - {id: a, name: A, sees: [b], store: {path: a, remote: none}}\n"
            " - {id: b, name: B, sees: [a], store: {path: b, remote: none}}\n")
    assert any("cycle" in p for p in tiers.load(write(tmp_path, body)).problems)


def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_stores(tmp_path):
    for s in ("open", "closed"):
        (tmp_path / s).mkdir()
        _git("init", "-q", cwd=tmp_path / s)
    _git("remote", "add", "origin", "https://example.invalid/x.git", cwd=tmp_path / "closed")
    body = ("register: 1\ntiers:\n"
            " - {id: o, name: O, sees: [], store: {path: open, remote: allowed}}\n"
            " - {id: c, name: C, sees: [o], store: {path: closed, remote: none}}\n"
            " - {id: g, name: G, sees: [o], store: {path: gone, remote: none}}\n")
    reg = tiers.load(write(tmp_path, body))
    assert reg.problems == []
    problems, absent = tiers.check_stores(reg)
    assert absent == ["g"]
    assert len(problems) == 1 and problems[0].startswith("c: store has 1 git remote")


def test_store_inside_another_repository_is_not_a_checkout(tmp_path):
    parent = tmp_path / "fx-parent"
    (parent / "inner").mkdir(parents=True)
    _git("init", "-q", cwd=parent)
    body = ("register: 1\ntiers:\n"
            " - {id: c, name: C, sees: [], store: {path: fx-parent/inner, remote: none}}\n")
    problems, absent = tiers.check_stores(tiers.load(write(tmp_path, body)))
    assert absent == []
    assert problems == ["c: store is not the top of its own git checkout"]


def test_nested_stores(tmp_path):
    body = ("register: 1\ntiers:\n"
            " - {id: o, name: O, sees: [], store: {path: s, remote: allowed}}\n"
            " - {id: c, name: C, sees: [o], store: {path: s/c, remote: none}}\n")
    reg = tiers.load(write(tmp_path, body))
    assert reg.problems == ["c: store lies inside the store of o"]


def test_remote_is_required(tmp_path):
    body = ("register: 1\ntiers:\n"
            " - {id: o, name: O, sees: [], store: {path: s}}\n")
    reg = tiers.load(write(tmp_path, body))
    assert reg.problems == ["o: store.remote is required"]
    assert reg.tiers["o"].remote == "none"   # an unclear rule is read as the stricter one


def test_cli_says_when_stores_are_skipped(tmp_path, capsys):
    sys.path.insert(0, str(ROOT / "scripts"))
    import check_tier_register as cli
    bad = write(tmp_path, "register: 1\ntiers:\n - {id: o, name: O, sees: [o], store: {path: s, remote: none}}\n")
    assert cli.main([str(bad), "--stores"]) == 1
    assert "stores not checked" in capsys.readouterr().out


def test_cli_exit_codes(tmp_path, capsys):
    sys.path.insert(0, str(ROOT / "scripts"))
    import check_tier_register as cli
    assert cli.main([str(FIXTURE)]) == 0
    assert "[CLOSED] jp-p / jp-q" in capsys.readouterr().out
    bad = write(tmp_path, "register: 1\ntiers: []\n")
    assert cli.main([str(bad)]) == 1
