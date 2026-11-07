"""Tests for lectkit.audience_db, on abstract fixtures only (lect id fx)."""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lectkit import audience_db as adb, tiers  # noqa: E402

FX_TIERS = """\
register: 1
tiers:
  - {id: fx-open, name: Open, sees: [], store: {path: stores/fx-open, remote: allowed}}
  - {id: fx-a, name: A, sees: [fx-open], store: {path: stores/fx-a, remote: allowed}}
  - {id: fx-c, name: C, sees: [fx-open, fx-a], store: {path: stores/fx-c, remote: none}}
  - {id: fx-p, name: P, sees: [fx-open], store: {path: stores/fx-p, remote: none}}
"""
REL = "lexicon/fx-nouns.yaml"
FILES = {
    "fx-open": {REL: "entries:\n- id: stemA\n  senses:\n  - id: stemA-s1\n    gloss: open gloss wordone\n",
                "fx-readme.md": "A shared line held in the open store.\n"},
    "fx-a": {REL: "entries:\n- id: stemA\n  senses:\n  - id: stemA-s1\n    gloss: open gloss wordone\n"
                  "  - id: stemA-s2\n    gloss: glossqz added at tier a here\n"},
    "fx-c": {REL: "# a comment fxcomment held at c\nentries:\n- id: stemB\n  count: 42\n"
                  "  senses:\n  - id: stemB-s1\n    gloss: glossqy\n",
             "fx-note.md": "A short note: fxnote.\n",
             "fx-image.png": b"\x89PNG\r\n\x1a\n\xff\x00"},
    "fx-p": {REL: "entries:\n- id: stemP\n"},
}


def setup(tmp_path: Path, files=FILES):
    reg_file = tmp_path / "fx-tiers.yaml"
    reg_file.write_text(FX_TIERS, encoding="utf-8")
    for t, fs in files.items():
        for rel, body in fs.items():
            f = tmp_path / "stores" / t / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(body, bytes):
                f.write_bytes(body)
            else:
                f.write_text(body, encoding="utf-8")
    reg = tiers.load(reg_file)
    assert reg.problems == []
    return reg, reg_file


def build(tmp_path, audience="fx-c"):
    reg, _ = setup(tmp_path)
    out = tmp_path / "build" / f"{audience}.sqlite"
    rep = adb.build(reg, audience, out)
    return adb.AudienceDB(out), rep


def test_model_tiers_come_from_location(tmp_path):
    db, rep = build(tmp_path)
    with db:
        assert rep.tiers == ["fx-open", "fx-a", "fx-c"]
        assert db.model_tiers("open gloss wordone") == {"fx-open"}   # restated at fx-a
        assert db.model_tiers("glossqz added at tier a here") == {"fx-a"}
        assert db.model_tiers("GLOSSQY") == {"fx-c"}
        assert db.model_tiers("42") == {"fx-c"}                       # numbers are content
        assert db.model_tiers("count") == {"fx-c"}     # keys are recorded at their tier
        assert db.model_tiers("stemB") == {"fx-c"}                    # ids
        assert db.model_tiers("a comment fxcomment held at c") == {"fx-c"}
        assert db.model_tiers("A short note: fxnote.") == {"fx-c"}    # short notes too


def test_source_values_keep_store_file_and_line(tmp_path):
    db, _ = build(tmp_path)
    with db:
        rows = set(db.con.execute(
            "SELECT tier, rel, line, kind FROM source_value WHERE norm = 'glossqy'"))
        assert rows == {("fx-c", REL, 7, "scalar")}
        rows = set(db.con.execute(
            "SELECT tier, line FROM source_value WHERE norm = 'open gloss wordone' AND kind='scalar'"))
        assert rows == {("fx-open", 5), ("fx-a", 5)}


def test_peer_store_is_not_read(tmp_path):
    db, _ = build(tmp_path)
    with db:
        assert db.model_tiers("stemP") == set()
        assert db.con.execute("SELECT count(*) FROM source_value WHERE tier = 'fx-p'").fetchone() == (0,)


def test_a_key_added_to_a_lower_mapping_is_content(tmp_path):
    files = {**FILES, "fx-c": {REL: "entries:\n- id: stemA\n  fxkeyqk: 1\n"}}
    reg, _ = setup(tmp_path, files)
    out = tmp_path / "build" / "fx-c.sqlite"
    adb.build(reg, "fx-c", out)
    with adb.AudienceDB(out) as db:
        assert db.model_tiers("fxkeyqk") == {"fx-c"}


def test_passages(tmp_path):
    db, _ = build(tmp_path)
    with db:
        hits = db.con.execute("SELECT DISTINCT v.tier FROM model_passage p JOIN model_value v "
                              "ON v.id = p.value_id WHERE p.norm = 'glossqz added at tier a'").fetchall()
        assert hits == [("fx-a",)]


def test_media_is_skipped_and_recorded(tmp_path):
    db, rep = build(tmp_path)
    with db:
        assert rep.skipped_media == 1
        assert db.con.execute("SELECT tier, rel FROM skipped_file").fetchall() == [("fx-c", "fx-image.png")]


def test_leak_query_shape(tmp_path):
    """A value in fx-open's store that equals material fx-c added is a candidate leak.
    A value fx-c only restates from below isn't, and a key fx-c uses that fx-open also
    uses as a key is a field name."""
    files = {**FILES, "fx-open": {**FILES["fx-open"], "fx-leaked.md": "glossqy\nopen gloss wordone\n"}}
    reg, _ = setup(tmp_path, files)
    out = tmp_path / "build" / "fx-c.sqlite"
    adb.build(reg, "fx-c", out)
    with adb.AudienceDB(out) as db:
        q = """SELECT s.rel, s.line FROM source_value s
               WHERE s.tier = 'fx-open'
                 AND EXISTS (SELECT 1 FROM model_value m WHERE m.norm = s.norm AND m.tier = 'fx-c'
                             AND NOT (m.kind = 'key' AND EXISTS (
                                 SELECT 1 FROM model_value k WHERE k.kind = 'key'
                                 AND k.norm = m.norm AND k.tier = 'fx-open')))"""
        assert db.con.execute(q).fetchall() == [("fx-leaked.md", 1)]


def test_refuses_an_output_inside_any_store(tmp_path):
    reg, _ = setup(tmp_path)
    for t in ("fx-open", "fx-a", "fx-c", "fx-p"):
        with pytest.raises(adb.BuildError, match="inside a store"):
            adb.build(reg, "fx-c", tmp_path / "stores" / t / "fx-db.sqlite")


def test_absent_store_stops_the_build(tmp_path):
    import shutil
    reg, _ = setup(tmp_path)
    shutil.rmtree(tmp_path / "stores" / "fx-a")
    with pytest.raises(adb.BuildError, match="not on this machine: fx-a"):
        adb.build(reg, "fx-c", tmp_path / "build" / "fx-c.sqlite")


@pytest.mark.parametrize("rel, body, msg", [
    ("fx-doc.pdf", b"%PDF\xff\xfe\x00", "can't be read as UTF-8"),
    ("fx-bad.yaml", "a: [1\n", "not valid YAML"),
    ("fx-dup.yaml", "glossqy: 1\nglossqy: 2\n", "not valid YAML"),
])
def test_unreadable_files_stop_the_build_without_showing_content(tmp_path, rel, body, msg):
    files = {**FILES, "fx-c": {**FILES["fx-c"], rel: body}}
    reg, _ = setup(tmp_path, files)
    out = tmp_path / "build" / "fx-c.sqlite"
    with pytest.raises(adb.BuildError, match=msg) as e:
        adb.build(reg, "fx-c", out)
    assert "glossqy" not in str(e.value) and rel in str(e.value)
    assert not out.exists() and not out.with_name(out.name + ".building").exists()


def test_a_file_that_doesnt_compose_names_only_the_file(tmp_path):
    files = {**FILES, "fx-a": {REL: "entries:\n- id: stemA\n  senses: glossqx\n"}}
    reg, _ = setup(tmp_path, files)
    with pytest.raises(adb.BuildError, match="doesn't compose") as e:
        adb.build(reg, "fx-c", tmp_path / "build" / "fx-c.sqlite")
    assert "glossqx" not in str(e.value) and "stemA" not in str(e.value)


def test_symlinks_are_refused(tmp_path):
    reg, _ = setup(tmp_path)
    link = tmp_path / "stores" / "fx-c" / "fx-link.md"
    try:
        os.symlink(tmp_path / "fx-tiers.yaml", link)
    except (OSError, NotImplementedError):
        pytest.skip("this machine can't create symbolic links")
    with pytest.raises(adb.BuildError, match="symbolic links"):
        adb.build(reg, "fx-c", tmp_path / "build" / "fx-c.sqlite")


def test_cli(tmp_path, capsys):
    import build_audience_db as cli
    _, reg_file = setup(tmp_path)
    out = tmp_path / "build" / "fx-c.sqlite"
    assert cli.main(["--register", str(reg_file), "--audience", "fx-c", "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "[BUILT] fx-c" in printed and "glossqy" not in printed
    # Rebuilding over an open database fails cleanly on systems that lock it.
    held = sqlite3.connect(out)
    code = cli.main(["--register", str(reg_file), "--audience", "fx-c", "--out", str(out)])
    held.close()
    assert code in (0, 1)
    assert not out.with_name(out.name + ".building").exists()


def test_restricted_keys_and_files_held_only_above(tmp_path):
    files = {**FILES, "fx-c": {**FILES["fx-c"],
             REL: "entries:\n- id: stemQ\n  info:\n    fxkeyq1: true\n    fxkeyq2: null\n",
             "fx-only-c.yaml": "fxtopq:\n  fxnestq: plain\n"}}
    reg, _ = setup(tmp_path, files)
    out = tmp_path / "build" / "fx-c.sqlite"
    adb.build(reg, "fx-c", out)
    with adb.AudienceDB(out) as db:
        for k in ("fxkeyq1", "fxkeyq2", "fxtopq", "fxnestq"):
            assert db.model_tiers(k) == {"fx-c"}, k
        line = db.con.execute("SELECT line FROM model_value WHERE norm = 'fxkeyq2'").fetchone()
        assert line == (5,)


def test_comments_are_read_outside_scalars(tmp_path):
    body = "a: x # fxcmtq\nnote: 'has # fxnotq'\nb: |\n  # fxblkq\n  y\n"
    files = {**FILES, "fx-c": {"fx-cmt.yaml": body}}
    reg, _ = setup(tmp_path, files)
    out = tmp_path / "build" / "fx-c.sqlite"
    adb.build(reg, "fx-c", out)
    with adb.AudienceDB(out) as db:
        rows = db.con.execute("SELECT line, norm FROM model_value WHERE kind = 'comment'").fetchall()
        assert rows == [(1, "fxcmtq")]


def test_model_rows_point_at_the_adding_line(tmp_path):
    db, _ = build(tmp_path)
    with db:
        assert db.con.execute(
            "SELECT tier, line FROM model_value WHERE norm = 'glossqz added at tier a here'"
        ).fetchone() == ("fx-a", 7)


def test_wrapped_passages_in_notes(tmp_path):
    files = {**FILES, "fx-c": {"fx-wrap.md": "one two three\nfour five six\n"}}
    reg, _ = setup(tmp_path, files)
    out = tmp_path / "build" / "fx-c.sqlite"
    adb.build(reg, "fx-c", out)
    with adb.AudienceDB(out) as db:
        assert db.con.execute(
            "SELECT count(*) FROM model_passage WHERE norm = 'two three four five six'"
        ).fetchone() == (1,)


@pytest.mark.parametrize("body, msg", [
    ("a: &x [1]\nb: *x\n", "uses an alias"),
    ("a: 1\n---\nb: 2\n", "more than one YAML document"),
])
def test_aliases_and_multiple_documents(tmp_path, body, msg):
    files = {**FILES, "fx-c": {"fx-odd.yaml": body}}
    reg, _ = setup(tmp_path, files)
    with pytest.raises(adb.BuildError, match=msg):
        adb.build(reg, "fx-c", tmp_path / "build" / "fx-c.sqlite")


def test_refuses_an_output_inside_a_git_working_tree(tmp_path):
    reg, _ = setup(tmp_path)
    (tmp_path / "fx-repo" / ".git").mkdir(parents=True)
    with pytest.raises(adb.BuildError, match="git working tree"):
        adb.build(reg, "fx-c", tmp_path / "fx-repo" / "fx-c.sqlite")


def test_every_table_and_row_carries_a_tier(tmp_path):
    db, rep = build(tmp_path)
    with db:
        assert db.classification == "fx-c"
        tables = [r[0] for r in db.con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        assert set(tables) == {"meta", "source_value", "model_value", "model_passage", "skipped_file"}
        for t in tables:
            cols = {r[1]: r[3] for r in db.con.execute(f"PRAGMA table_info({t})")}
            assert cols.get("tier") == 1, t          # present, and NOT NULL
            tiers_held = {r[0] for r in db.con.execute(f"SELECT DISTINCT tier FROM {t}")}
            assert tiers_held <= set(rep.tiers), t
        mismatched = db.con.execute(
            "SELECT count(*) FROM model_passage p JOIN model_value v ON v.id = p.value_id "
            "WHERE p.tier != v.tier").fetchone()[0]
        assert mismatched == 0
        assert db.con.execute("SELECT DISTINCT tier FROM model_passage WHERE norm = "
                              "'glossqz added at tier a'").fetchall() == [("fx-a",)]


@pytest.mark.parametrize("tamper", [
    "INSERT INTO source_value VALUES ('fx-p', 'x.md', 1, 'line', 'x', 'x')",
    "UPDATE model_passage SET tier = 'fx-open' WHERE tier = 'fx-c'",
])
def test_opening_a_database_checks_its_tiers(tmp_path, tamper):
    reg, _ = setup(tmp_path)
    out = tmp_path / "build" / "fx-c.sqlite"
    adb.build(reg, "fx-c", out)
    con = sqlite3.connect(out)
    con.execute(tamper)
    con.commit()
    con.close()
    with pytest.raises(adb.BuildError):
        adb.AudienceDB(out)


def test_a_git_store_is_read_by_what_git_holds(tmp_path):
    import subprocess
    reg, _ = setup(tmp_path)
    store = tmp_path / "stores" / "fx-c"
    subprocess.run(["git", "init", "-q", str(store)], check=True, capture_output=True)
    (store / ".gitignore").write_text("fx-cache/\n", encoding="utf-8")
    (store / "fx-cache").mkdir()
    (store / "fx-cache" / "fx-junk.bin").write_bytes(b"\xff\xfe\x00\x80")   # ignored: not read
    (store / "fx-new.md").write_text("fxnewq untracked but not ignored\n", encoding="utf-8")
    out = tmp_path / "build" / "fx-c.sqlite"
    adb.build(reg, "fx-c", out)                       # the ignored binary doesn't stop it
    with adb.AudienceDB(out) as db:
        assert db.model_tiers("fxnewq untracked but not ignored") == {"fx-c"}
        assert db.con.execute("SELECT count(*) FROM source_value WHERE rel LIKE 'fx-cache/%'"
                              ).fetchone() == (0,)


def test_a_text_file_is_layered_line_by_line(tmp_path):
    files = {**FILES,
             "fx-open": {**FILES["fx-open"], "fx-shared.md": "one shared line here\n"},
             "fx-c": {**FILES["fx-c"], "fx-shared.md": "one shared line here\nfxonlyc line\n"}}
    reg, _ = setup(tmp_path, files)
    out = tmp_path / "build" / "fx-c.sqlite"
    adb.build(reg, "fx-c", out)
    with adb.AudienceDB(out) as db:
        assert db.model_tiers("one shared line here") == {"fx-open"}     # restated by fx-c
        assert db.model_tiers("fxonlyc line") == {"fx-c"}



@pytest.mark.parametrize("pat, rel, hit", [
    ("README.md", "README.md", True),
    ("README.md", "paradigm/README.md", True),          # a bare name matches at any depth
    ("/README.md", "README.md", True),
    ("/README.md", "paradigm/README.md", False),        # a leading slash anchors
    ("**/README.md", "notREADME.md", False),
    ("**/README.md", "a/b/README.md", True),
    ("**/README.md", "README.md", True),
    ("a/**/b.md", "a/xb.md", False),
    ("a/**/b.md", "a/b.md", True),
    ("a/**/b.md", "a/x/y/b.md", True),
    ("docs/", "docs/x/y.md", True),
    ("docs/", "docsx/y.md", False),
    ("a/**", "a/x/y.md", True),
    ("*.pyc", "a/b.pyc", True),
    ("?.md", "ab.md", False),
    ("READ*.md", "sub/READX.md", True),
])
def test_exclusion_patterns(pat, rel, hit):
    assert adb.excluded([pat], rel) is hit


@pytest.mark.parametrize("line", ["!keep.md", "docs/a#b", "[ab].md", "a\\b.md"])
def test_unsupported_exclusion_syntax_is_an_error(line):
    with pytest.raises(adb.BuildError, match="unsupported"):
        adb.parse_patterns(line + "\n")


def test_exclusion_comments_and_blanks():
    assert adb.parse_patterns("# a comment\n\n/README.md\n") == ["/README.md"]


def test_lines_without_letters_or_digits_arent_material(tmp_path):
    files = {**FILES, "fx-c": {**FILES["fx-c"], "fx-c-table.md": "---\n| --- | --- |\nfxrowq cell\n"}}
    reg, _ = setup(tmp_path, files)
    out = tmp_path / "build" / "fx-c.sqlite"
    adb.build(reg, "fx-c", out)
    with adb.AudienceDB(out) as db:
        assert db.model_tiers("---") == set() and db.model_tiers("| --- | --- |") == set()
        assert db.model_tiers("fxrowq cell") == {"fx-c"}
        assert db.con.execute("SELECT count(*) FROM source_value WHERE norm = '---'").fetchone()[0] >= 1
