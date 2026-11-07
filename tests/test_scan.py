"""Tests for lectkit.scan, on abstract fixtures only (lect id fx)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lectkit import audience_db as adb, scan, tiers  # noqa: E402

FX_TIERS = """\
register: 1
tiers:
  - {id: fx-open, name: Open, sees: [], store: {path: stores/fx-open, remote: allowed}}
  - {id: fx-a, name: A, sees: [fx-open], store: {path: stores/fx-a, remote: allowed}}
  - {id: fx-c, name: C, sees: [fx-open, fx-a], store: {path: stores/fx-c, remote: none}}
"""
REL = "lexicon/fx-nouns.yaml"
OPEN_LEX = "entries:\n- id: stemA\n  senses:\n  - id: stemA-s1\n    gloss: open gloss wordone\n"
BASE = {
    "fx-open": {REL: OPEN_LEX},
    "fx-a": {REL: OPEN_LEX + "  - id: stemA-s2\n    gloss: alpha beta gamma delta epsilon zeta\n"},
    "fx-c": {REL: "entries:\n- id: stemB\n  fxkeyqz: 2\n  senses:\n  - id: stemB-s1\n    gloss: glossqy\n"},
}
# The field names fx-c's new record shares with the stores below: decided once by a person.
FIELD_NAMES = {"fx-open": {"entries", "senses", "gloss"}, "fx-a": {"entries", "senses", "gloss"}}


def with_files(**extra):
    files = {t: dict(fs) for t, fs in BASE.items()}
    for t, fs in extra.items():
        files[t].update(fs)
    return files


def setup(tmp_path, files):
    reg_file = tmp_path / "fx-tiers.yaml"
    reg_file.write_text(FX_TIERS, encoding="utf-8")
    for t, fs in files.items():
        for rel, body in fs.items():
            f = tmp_path / "stores" / t / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body, encoding="utf-8")
    reg = tiers.load(reg_file)
    assert reg.problems == []
    out = tmp_path / "build" / "fx-c.sqlite"
    adb.build(reg, "fx-c", out)
    return reg, reg_file, out


def run(tmp_path, files, accepted=FIELD_NAMES):
    reg, _, out = setup(tmp_path, files)
    with adb.AudienceDB(out) as db:
        return scan.scan(db, reg, accepted)


def where(rep):
    return {(f.tier, f.rel, f.line) for f in rep.open_findings}


def find(rep, tier, rel, line):
    return next(f for f in rep.findings if (f.tier, f.rel, f.line) == (tier, rel, line))


def test_clean_stores_have_no_open_findings(tmp_path):
    rep = run(tmp_path, BASE)
    assert rep.scanned == ["fx-open", "fx-a"]
    assert where(rep) == set()


def test_field_names_need_a_decision(tmp_path):
    rep = run(tmp_path, BASE, accepted={})
    assert ("fx-open", REL, 3) in where(rep)          # `senses` is also a key in fx-c's new record
    assert ("fx-open", REL, 1) not in where(rep)      # `entries` fx-c only restates


def test_exact_value(tmp_path):
    rep = run(tmp_path, with_files(**{"fx-open": {"fx-notes.md": "nothing here\nglossqy\n"}}))
    assert where(rep) == {("fx-open", "fx-notes.md", 2)}
    assert find(rep, "fx-open", "fx-notes.md", 2).matches == ("value",)


def test_a_restricted_id_inside_a_longer_line(tmp_path):
    rep = run(tmp_path, with_files(**{"fx-open": {"fx-notes.md": "see stemB-s1 here\n"}}))
    f = find(rep, "fx-open", "fx-notes.md", 1)
    assert f.matches == ("token",) and f.hidden == ("fx-c",) and not f.accepted


def test_a_passage_split_across_lines(tmp_path):
    rep = run(tmp_path, with_files(**{"fx-open": {"fx-notes.md": "it said alpha beta gamma\ndelta epsilon, then\n"}}))
    f = find(rep, "fx-open", "fx-notes.md", 1)
    assert f.matches == ("passage",) and f.hidden == ("fx-a",)


def test_the_lower_store_cant_exempt_a_restricted_key_by_using_it(tmp_path):
    rep = run(tmp_path, with_files(**{"fx-open": {"fx-planted.yaml": "fxkeyqz: 1\n",
                                                  "fx-notes.md": "fxkeyqz\n"}}))
    assert {("fx-open", "fx-planted.yaml", 1), ("fx-open", "fx-notes.md", 1)} <= where(rep)


def test_every_hidden_tier_is_named_most_restrictive_first(tmp_path):
    files = with_files(**{"fx-c": {"fx-c-notes.md": "alpha beta gamma delta epsilon zeta\n"},
                          "fx-open": {"fx-notes.md": "alpha beta gamma delta epsilon zeta\n"}})
    f = find(run(tmp_path, files), "fx-open", "fx-notes.md", 1)
    assert f.hidden == ("fx-c", "fx-a")


def test_a_lower_stores_kit_folder_is_read(tmp_path):
    rep = run(tmp_path, with_files(**{"fx-open": {".lectkit/fx-hidden.md": "glossqy\n"}}))
    assert ("fx-open", ".lectkit/fx-hidden.md", 1) in where(rep)


def test_accepting_one_match_doesnt_accept_another_on_the_line(tmp_path):
    files = with_files(**{"fx-open": {"fx-notes.md": "glossqy and stemB here\n"}})
    rep = run(tmp_path, files, accepted={**FIELD_NAMES, "fx-open": FIELD_NAMES["fx-open"] | {"glossqy"}})
    assert ("fx-open", "fx-notes.md", 1) in where(rep)          # stemB is still open
    rep = run(tmp_path, files, accepted={**FIELD_NAMES,
                                         "fx-open": FIELD_NAMES["fx-open"] | {"glossqy", "stemB"}})
    assert ("fx-open", "fx-notes.md", 1) not in where(rep)
    # A decision for one tier's stores doesn't cover another's.
    files = with_files(**{"fx-a": {"fx-a-notes.md": "glossqy\n"}})
    rep = run(tmp_path, files, accepted={**FIELD_NAMES, "fx-open": FIELD_NAMES["fx-open"] | {"glossqy"}})
    assert ("fx-a", "fx-a-notes.md", 1) in where(rep)


def test_a_changed_store_refuses_the_scan(tmp_path):
    reg, _, out = setup(tmp_path, BASE)
    (tmp_path / "stores" / "fx-open" / REL).write_text(OPEN_LEX + "# changed\n", encoding="utf-8")
    with adb.AudienceDB(out) as db, pytest.raises(scan.ScanError, match="changed since"):
        scan.scan(db, reg)


def test_a_changed_lower_kit_folder_also_refuses_the_scan(tmp_path):
    reg, _, out = setup(tmp_path, BASE)
    kit = tmp_path / "stores" / "fx-open" / ".lectkit" / "x.md"
    kit.parent.mkdir(parents=True)
    kit.write_text("x\n", encoding="utf-8")
    with adb.AudienceDB(out) as db, pytest.raises(scan.ScanError, match="changed since"):
        scan.scan(db, reg)


def test_the_scanning_tiers_kit_folder_isnt_read(tmp_path):
    reg, _, out = setup(tmp_path, BASE)
    kit = tmp_path / "stores" / "fx-c" / scan.ACCEPT_FILE
    kit.parent.mkdir(parents=True)
    kit.write_text("- {text: gloss, tier: fx-open, reason: field name, by: 'human:fx-reviewer',"
                   " at: '2026-01-01T00:00:00+00:00'}\n", encoding="utf-8")
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg, scan.load_accepted(kit, reg))   # still fresh
    assert ("fx-open", REL, 5) not in where(rep)      # gloss accepted
    assert ("fx-open", REL, 3) in where(rep)          # senses not


@pytest.mark.parametrize("body", ["- {text: x}\n", "a: 1\n",
                                  "- {text: x, tier: fx-z, reason: r, by: b, at: t}\n"])
def test_bad_accept_file(tmp_path, body):
    reg, _, _ = setup(tmp_path, BASE)
    f = tmp_path / "fx-accepted.yaml"
    f.write_text(body, encoding="utf-8")
    with pytest.raises(scan.ScanError):
        scan.load_accepted(f, reg)


def test_cli(tmp_path, capsys):
    import scan_tiers as cli
    files = with_files(**{"fx-open": {"fx-notes.md": "nothing\nsee stemB-s1 here\n"}})
    _, reg_file, out = setup(tmp_path, files)
    args = ["--register", str(reg_file), "--db", str(out)]
    assert cli.main(args) == 1
    printed = capsys.readouterr().out
    import re as _re
    assert _re.search(r"\[MATCH\] [0-9a-f]{12} fx-open: fx-notes.md:2: token matches fx-c material",
                      printed)
    for word in ("glossqy", "alpha", "stemb", "stemB", "fxkeyqz"):
        assert word not in printed
    # A report goes under the scanning tier's .lectkit/ or outside every store, never lower.
    assert cli.main(args + ["--out", str(tmp_path / "stores" / "fx-open" / "fx-report.txt")]) == 3
    assert not (tmp_path / "stores" / "fx-open" / "fx-report.txt").exists()
    assert cli.main(args + ["--out", str(tmp_path / "stores" / "fx-c" / "fx-report.txt")]) == 3
    assert cli.main(args + ["--out", str(tmp_path / "stores" / "fx-c" / ".lectkit" / "reports"
                                         / "fx-report.txt")]) == 1
    assert cli.main(args + ["--out", str(tmp_path / "reports" / "fx-report.txt")]) == 1


# --- reviews of exact entries ---------------------------------------------------------

def scan_with_reviews(tmp_path, files):
    reg, _, out = setup(tmp_path, files)
    store = tmp_path / "stores" / "fx-c"
    with adb.AudienceDB(out) as db:
        return scan.scan(db, reg, FIELD_NAMES, scan.load_reviews(store / scan.REVIEW_FILE, reg)), reg, store


def review(store, f):
    scan.record_review(store, f, "checked: shared word in this note", "human:fx-reviewer",
                       "2026-01-01T00:00:00+00:00")


def notes(text):
    return with_files(**{"fx-open": {"fx-notes.md": text}})


def test_a_reviewed_entry_stays_cleared_while_it_doesnt_change(tmp_path):
    rep, _, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    f = find(rep, "fx-open", "fx-notes.md", 1)
    assert not f.cleared
    review(store, f)
    rep, _, _ = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    assert find(rep, "fx-open", "fx-notes.md", 1).reviewed
    assert where(rep) == set()


def test_moving_the_entry_keeps_the_review(tmp_path):
    rep, _, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    review(store, find(rep, "fx-open", "fx-notes.md", 1))
    rep, _, _ = scan_with_reviews(tmp_path, notes("a new first line\nsee stemB-s1 here\n"))
    assert find(rep, "fx-open", "fx-notes.md", 2).reviewed


def test_changing_the_entry_needs_a_new_review(tmp_path):
    rep, _, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    review(store, find(rep, "fx-open", "fx-notes.md", 1))
    rep, _, _ = scan_with_reviews(tmp_path, notes("see stemB-s1 there\n"))
    assert ("fx-open", "fx-notes.md", 1) in where(rep)


def test_a_new_hidden_match_on_the_entry_needs_a_new_review(tmp_path):
    rep, _, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    review(store, find(rep, "fx-open", "fx-notes.md", 1))
    files = notes("see stemB-s1 here\n")
    files["fx-c"]["fx-c-more.yaml"] = "entries:\n- id: fxsee\n  w: see stemB-s1 here\n"
    rep, _, _ = scan_with_reviews(tmp_path, files)
    assert ("fx-open", "fx-notes.md", 1) in where(rep)


def test_the_same_text_in_another_file_isnt_covered(tmp_path):
    rep, _, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    review(store, find(rep, "fx-open", "fx-notes.md", 1))
    files = notes("see stemB-s1 here\n")
    files["fx-open"]["fx-other.md"] = "see stemB-s1 here\n"
    rep, _, _ = scan_with_reviews(tmp_path, files)
    assert where(rep) == {("fx-open", "fx-other.md", 1)}


def test_a_review_names_a_person(tmp_path):
    rep, _, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    f = find(rep, "fx-open", "fx-notes.md", 1)
    with pytest.raises(scan.ScanError, match="person"):
        scan.record_review(store, f, "fine", "agent:fx-model", "2026-01-01T00:00:00+00:00")
    with pytest.raises(scan.ScanError, match="reason"):
        scan.record_review(store, f, " ", "human:fx-reviewer", "2026-01-01T00:00:00+00:00")
    (store / scan.REVIEW_FILE).parent.mkdir(parents=True, exist_ok=True)
    (store / scan.REVIEW_FILE).write_text(
        f"- {{tier: fx-open, rel: fx-notes.md, entry: {f.entry}, matched: [], reason: r,"
        f" by: 'agent:fx-model', at: t}}\n", encoding="utf-8")
    reg = tiers.load(tmp_path / "fx-tiers.yaml")
    with pytest.raises(scan.ScanError, match="person"):
        scan.load_reviews(store / scan.REVIEW_FILE, reg)


def test_review_cli(tmp_path, capsys):
    import re as _re
    import review_finding
    import scan_tiers as cli
    _, reg_file, out = setup(tmp_path, notes("see stemB-s1 here\n"))
    kit = tmp_path / "stores" / "fx-c" / scan.ACCEPT_FILE
    kit.parent.mkdir(parents=True, exist_ok=True)
    kit.write_text("".join(
        f"- {{text: {t}, tier: {low}, reason: field name, by: 'human:fx-reviewer', at: t}}\n"
        for low, ts in FIELD_NAMES.items() for t in sorted(ts)), encoding="utf-8")
    adb.build(tiers.load(reg_file), "fx-c", out)      # rebuild: unaffected by fx-c's .lectkit
    args = ["--register", str(reg_file), "--db", str(out)]
    assert cli.main(args) == 1
    fid = _re.search(r"\[MATCH\] (\w+) fx-open: fx-notes.md:1", capsys.readouterr().out).group(1)
    assert review_finding.main(args + ["--id", fid, "--reason", "shared", "--by", "human:fx-reviewer"]) == 0
    assert cli.main(args) == 0
    assert "1 reviewed" in capsys.readouterr().out
    assert review_finding.main(args + ["--id", "nope", "--reason", "x", "--by", "human:x"]) == 3


# --- second review ------------------------------------------------------------------

def test_a_hidden_item_changing_tier_needs_a_new_review(tmp_path):
    files = notes("fxshiftq here\n")
    files["fx-a"]["fx-a-more.yaml"] = "entries:\n- id: fxa1\n  w: fxshiftq\n"
    rep, _, store = scan_with_reviews(tmp_path, files)
    f = find(rep, "fx-open", "fx-notes.md", 1)
    assert f.hidden == ("fx-a",)
    review(store, f)
    files = notes("fxshiftq here\n")
    files["fx-c"]["fx-c-more.yaml"] = "entries:\n- id: fxc1\n  w: fxshiftq\n"   # now at fx-c
    rep, _, _ = scan_with_reviews(tmp_path, files)
    assert ("fx-open", "fx-notes.md", 1) in where(rep)


def test_a_passage_review_covers_every_line_it_spans(tmp_path):
    files = notes("it said alpha beta gamma\ndelta epsilon, then\n")
    rep, _, store = scan_with_reviews(tmp_path, files)
    review(store, find(rep, "fx-open", "fx-notes.md", 1))
    rep, _, _ = scan_with_reviews(tmp_path, notes("it said alpha beta gamma\ndelta epsilon, and more\n"))
    assert ("fx-open", "fx-notes.md", 1) in where(rep)       # line 2 changed under the passage


def test_a_copied_line_is_a_new_finding(tmp_path):
    rep, _, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    review(store, find(rep, "fx-open", "fx-notes.md", 1))
    rep, _, _ = scan_with_reviews(tmp_path, notes("see stemB-s1 here\nsee stemB-s1 here\n"))
    assert where(rep) == {("fx-open", "fx-notes.md", 2)}


def test_ids_and_review_digests_are_keyed_by_the_scanning_tier(tmp_path):
    rep, _, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    f = find(rep, "fx-open", "fx-notes.md", 1)
    key = bytes.fromhex((store / scan.KEY_FILE).read_text(encoding="ascii").strip())
    assert len(key) == 32
    # Someone without the key can't reproduce the id from the line and a guessed word.
    guess = scan._digest(f.tier, f.rel, f.entry, str(f.nth), scan._digest("stemb s1"))[:12]
    assert f.id != guess and "stemb" not in f.id
    # The key never enters the database or any lower store.
    assert not list((tmp_path / "stores" / "fx-open").rglob("scan_key"))


def test_recording_a_review_keeps_the_file_valid(tmp_path):
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\nglossqy\n"))
    path = store / scan.REVIEW_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]", encoding="utf-8")              # flow style, no trailing newline
    review(store, find(rep, "fx-open", "fx-notes.md", 1))
    review(store, find(rep, "fx-open", "fx-notes.md", 2))
    assert len(scan.load_reviews(path, reg)) == 2


def test_prose_lines_arent_looked_for_inside_lines(tmp_path):
    files = with_files(**{"fx-c": {"fx-c-notes.md": "fxheadq rules\n"},
                          "fx-open": {"fx-notes.md": "the fxheadq rules apply here\n"}})
    rep = run(tmp_path, files)
    assert ("fx-open", "fx-notes.md", 1) not in where(rep)
    files["fx-open"]["fx-notes.md"] = "fxheadq rules\n"           # the whole line still matches
    assert ("fx-open", "fx-notes.md", 1) in where(run(tmp_path, files))
