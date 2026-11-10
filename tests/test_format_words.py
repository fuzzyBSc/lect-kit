"""Tests for lectkit.format_words, on abstract fixtures only (lect id fx)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lectkit import audience_db as adb, format_words, scan, tiers  # noqa: E402

SCHEMA = """\
id: https://lect-kit.example/schemas/fx
name: fx
classes:
  FxEntry:
    attributes:
      fxpos: {range: FxPos}
      fxhead: {range: string}
enums:
  FxPos:
    permissible_values: {fxnoun: {}, fxverb: {}}
"""
REL = "lexicon/fx.yaml"


def build(tmp_path, monkeypatch, files, terms=None):
    sd = tmp_path / "schemas"
    sd.mkdir(parents=True)
    (sd / "fx.yaml").write_text(SCHEMA, encoding="utf-8")
    monkeypatch.setattr(format_words, "SCHEMA_DIR", sd)
    c_terms = ", terms: [stores/fx-c/fx-terms.yaml]" if terms is not None else ""
    reg_file = tmp_path / "fx-tiers.yaml"
    reg_file.write_text(
        "register: 1\ntiers:\n"
        "  - {id: fx-open, name: Openqz, sees: [], store: {path: stores/fx-open, remote: allowed}}\n"
        f"  - {{id: fx-c, name: Cqzx, sees: [fx-open], store: {{path: stores/fx-c, remote: none}}{c_terms}}}\n",
        encoding="utf-8")
    if terms is not None:
        files.setdefault("fx-c", {})["fx-terms.yaml"] = terms
    for t, fs in files.items():
        for rel, body in fs.items():
            f = tmp_path / "stores" / t / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body, encoding="utf-8")
    reg = tiers.load(reg_file)
    assert reg.problems == []
    out = tmp_path / "fx-c.sqlite"
    adb.build(reg, "fx-c", out)
    return reg, out


def test_declared_words_need_no_grant_but_prose_does(tmp_path, monkeypatch):
    """@AC-cross_tier_scan-24."""
    reg, out = build(tmp_path, monkeypatch, {
        "fx-open": {REL: "entries:\n- fxhead: openq\n  fxpos: fxnoun\n",
                    "notes.md": "nothing here\nthe fxnoun word\n"},
        "fx-c": {REL: "entries:\n- fxhead: hiddenqz\n  fxpos: fxnoun\n"},
    })
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg)
    held = {(f.rel, f.line) for f in rep.open_findings}
    assert (REL, 2) not in held and (REL, 3) not in held
    assert ("notes.md", 2) not in held     # fx-c wrote fxnoun only as a declared value
    reg, out = build(tmp_path / "b", monkeypatch, {
        "fx-open": {"notes.md": "nothing here\nthe fxnoun word\n"},
        "fx-c": {REL: "entries:\n- fxhead: hiddenqz\n  fxpos: fxnoun\n",
                 "c-notes.md": "the fxnoun word\n"},    # the same line in fx-c's prose: material
    })
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg)
    assert ("notes.md", 2) in {(f.rel, f.line) for f in rep.open_findings}


def test_a_term_register_match_stops_the_build(tmp_path, monkeypatch):
    """@AC-cross_tier_scan-25. A term register that matches a format word."""
    with pytest.raises(adb.BuildError) as e:
        build(tmp_path, monkeypatch, {"fx-open": {REL: "entries: []\n"}},
              terms="terms:\n- term: fxverb\n")
    assert "fxverb" in str(e.value) and "fx-c" in str(e.value)


def test_a_restricted_tier_using_a_format_word_as_an_id_stops_the_build(tmp_path, monkeypatch):
    """@AC-cross_tier_scan-25. A restricted tier writing a format word as an identifier."""
    with pytest.raises(adb.BuildError) as e:
        build(tmp_path, monkeypatch, {
            "fx-open": {REL: "entries:\n- id: stemq\n"},
            "fx-c": {REL: "entries:\n- id: stemq\n- id: fxpos\n"},
        }, terms="terms:\n- term: unrelatedqx\n")
    assert "fxpos" in str(e.value)


def test_a_tiers_name_is_its_material_until_it_grants_it(tmp_path, monkeypatch):
    """@AC-cross_tier_scan-26. A tier's name passes into a lower tier only by that tier's explicit grant."""
    from conftest import grant_yaml
    files = {"fx-open": {"notes.md": "nothing here\nCqzx\n"},
             "fx-c": {REL: "entries:\n- fxhead: hiddenqz\n  tier: Cqzx\n"}}
    reg, out = build(tmp_path, monkeypatch, files)
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg)
    assert ("notes.md", 2) in {(f.rel, f.line) for f in rep.open_findings}     # held: no grant yet
    files["fx-c"][".lectkit/accepted_matches.yaml"] = grant_yaml([("Cqzx", "fx-open", "the tier's name")])
    reg, out = build(tmp_path / "granted", monkeypatch, files)
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg)
    assert ("notes.md", 2) not in {(f.rel, f.line) for f in rep.open_findings}


def test_a_digest_field_holds_hex_only(tmp_path):
    """@AC-cross_tier_scan-29. A field declared as a digest passes a hex hash, and nothing else."""
    sd = tmp_path / "schemas"; sd.mkdir()
    (sd / "fx.yaml").write_text(
        "id: https://lect-kit.example/schemas/fx\nname: fx\ntypes:\n"
        "  digest: {typeof: string, pattern: '^[0-9a-f]{12,128}$',\n"
        "           annotations: {lectkit_material: false}}\nclasses:\n  FxRow:\n    attributes:\n"
        "      fxsum: {range: digest}\n", encoding="utf-8")
    w = format_words.load(sd)
    assert w.is_value("fxsum", "a2257cbf190ce3d1bf7748226f457ebd")
    assert not w.is_value("fxsum", "hiddenqz word")
    assert not w.is_value("other", "a2257cbf190ce3d1bf7748226f457ebd")


def test_every_tier_may_name_itself(tmp_path, monkeypatch):
    """@AC-cross_tier_scan-30."""
    files = {"fx-open": {"notes.md": "nothing here\nOpenqz\nCqzx\n"},
             "fx-c": {REL: "entries:\n- fxhead: hiddenqz\n  tier: Openqz\n  also: Cqzx\n"}}
    reg, out = build(tmp_path, monkeypatch, files)
    with adb.AudienceDB(out) as db:
        held = {(f.rel, f.line) for f in scan.scan(db, reg).open_findings}
    assert ("notes.md", 2) not in held and ("notes.md", 3) in held



def test_a_shared_list_is_granted_by_version(tmp_path, monkeypatch):
    """@AC-cross_tier_scan-31. A tier grants a shared list in one line, and only where it grants it."""
    from lectkit import shared_lists
    ld = tmp_path / "lists"; ld.mkdir()
    (ld / "fxwords-v1.txt").write_text("# ordinary words\nhiddenqz\n", encoding="utf-8")
    monkeypatch.setattr(shared_lists, "LIST_DIR", ld)
    files = {"fx-open": {"notes.md": "nothing here\nhiddenqz\n"},
             "fx-c": {REL: "entries:\n- fxhead: hiddenqz\n"}}
    reg, out = build(tmp_path, monkeypatch, files)
    with adb.AudienceDB(out) as db:
        assert ("notes.md", 2) in {(f.rel, f.line) for f in scan.scan(db, reg).open_findings}
    files["fx-c"][".lectkit/accepted_matches.yaml"] = "fx-open: ['list:fxwords-v1']\n"
    reg, out = build(tmp_path / "g", monkeypatch, files)
    with adb.AudienceDB(out) as db:
        assert ("notes.md", 2) not in {(f.rel, f.line) for f in scan.scan(db, reg).open_findings}
    files["fx-c"][".lectkit/accepted_matches.yaml"] = "fx-open: ['list:nosuchqz-v1']\n"
    reg, out = build(tmp_path / "u", monkeypatch, files)
    with adb.AudienceDB(out) as db, pytest.raises(scan.ScanError):
        scan.scan(db, reg)


def test_a_shared_list_entry_a_register_matches_stops_the_build(tmp_path, monkeypatch):
    """@AC-cross_tier_scan-32. The kit can't release a restricted word through a shared list."""
    from lectkit import shared_lists
    ld = tmp_path / "lists"; ld.mkdir()
    (ld / "fxwords-v1.txt").write_text("plainqz\nsecretqz\n", encoding="utf-8")
    monkeypatch.setattr(shared_lists, "LIST_DIR", ld)
    with pytest.raises(adb.BuildError) as e:
        build(tmp_path, monkeypatch, {"fx-open": {REL: "entries: []\n"}},
              terms="terms:\n- term: secretqz\n")
    assert "fxwords-v1 entry 2" in str(e.value) and "secretqz" not in str(e.value)
