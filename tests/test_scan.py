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
# fx-a's new sense uses the field name `gloss` too; fx-a decides that for itself.
A_FIELD_NAMES = {"fx-open": {"gloss"}}


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
    """`accepted` is fx-c's decisions, {lower tier: texts}: fx-c's material is what matches."""
    reg, _, out = setup(tmp_path, files)
    with adb.AudienceDB(out) as db:
        return scan.scan(db, reg, {"fx-c": accepted, "fx-a": A_FIELD_NAMES})


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
    # An fx-a passage and an fx-c id on one line: two tiers' material, most restrictive first.
    files = with_files(**{"fx-open": {"fx-notes.md": "alpha beta gamma delta epsilon zeta stemB-s1\n"}})
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
    # A decision for one lower tier's stores doesn't cover another's.
    files = with_files(**{"fx-a": {"fx-a-notes.md": "glossqy\n"}})
    rep = run(tmp_path, files, accepted={**FIELD_NAMES, "fx-open": FIELD_NAMES["fx-open"] | {"glossqy"}})
    assert ("fx-a", "fx-a-notes.md", 1) in where(rep)


def test_a_decision_lives_with_the_material_it_is_about(tmp_path):
    """fx-a's material matched in fx-open is decided in fx-a's store, and fx-c, which reads
    fx-a's store, honours it. fx-c's own accept file doesn't cover fx-a's material."""
    files = with_files(**{"fx-open": {"fx-notes.md": "see stemA-s2 here\n"}})
    reg, _, out = setup(tmp_path, files)
    kit = tmp_path / "stores" / "fx-a" / scan.ACCEPT_FILE
    kit.parent.mkdir(parents=True)
    kit.write_text("- {text: stemA-s2, tier: fx-open, reason: shared, by: 'human:fx-reviewer',"
                   " at: t}\n", encoding="utf-8")
    adb.build(reg, "fx-c", out)
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg, {"fx-c": FIELD_NAMES})
    assert ("fx-open", "fx-notes.md", 1) not in {(f.tier, f.rel, f.line) for f in rep.open_findings}
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg, {"fx-c": FIELD_NAMES | {"fx-open": {"stemA-s2"}}, "fx-a": {}})
    assert ("fx-open", "fx-notes.md", 1) in where(rep)


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


def accept_in(tmp_path, tier, low, texts):
    kit = tmp_path / "stores" / tier / scan.ACCEPT_FILE
    kit.parent.mkdir(parents=True, exist_ok=True)
    kit.write_text("".join(f"- {{text: {t}, tier: {low}, reason: field name,"
                           f" by: 'human:fx-reviewer', at: t}}\n" for t in sorted(texts)),
                   encoding="utf-8")


def test_decisions_are_read_from_the_stores(tmp_path):
    reg, _, out = setup(tmp_path, BASE)
    accept_in(tmp_path, "fx-c", "fx-open", {"gloss"})
    accept_in(tmp_path, "fx-a", "fx-open", {"gloss"})
    adb.build(reg, "fx-c", out)          # fx-a's kit folder is part of fx-a's store
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg)
    assert ("fx-open", REL, 5) not in where(rep)      # gloss accepted by both tiers
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
        return scan.scan(db, reg, {"fx-c": FIELD_NAMES, "fx-a": A_FIELD_NAMES}), reg, store


def review(reg, f):
    scan.record_review(reg, f, "checked: shared word in this note", "human:fx-reviewer",
                       "2026-01-01T00:00:00+00:00")


def notes(text):
    return with_files(**{"fx-open": {"fx-notes.md": text}})


def test_a_reviewed_entry_stays_cleared_while_it_doesnt_change(tmp_path):
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    f = find(rep, "fx-open", "fx-notes.md", 1)
    assert not f.cleared
    review(reg, f)
    rep, _, _ = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    assert find(rep, "fx-open", "fx-notes.md", 1).reviewed
    assert where(rep) == set()


def test_moving_the_entry_keeps_the_review(tmp_path):
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    review(reg, find(rep, "fx-open", "fx-notes.md", 1))
    rep, _, _ = scan_with_reviews(tmp_path, notes("a new first line\nsee stemB-s1 here\n"))
    assert find(rep, "fx-open", "fx-notes.md", 2).reviewed


def test_changing_the_entry_needs_a_new_review(tmp_path):
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    review(reg, find(rep, "fx-open", "fx-notes.md", 1))
    rep, _, _ = scan_with_reviews(tmp_path, notes("see stemB-s1 there\n"))
    assert ("fx-open", "fx-notes.md", 1) in where(rep)


def test_a_new_hidden_match_on_the_entry_needs_a_new_review(tmp_path):
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    review(reg, find(rep, "fx-open", "fx-notes.md", 1))
    files = notes("see stemB-s1 here\n")
    files["fx-c"]["fx-c-more.yaml"] = "entries:\n- id: fxsee\n  w: see stemB-s1 here\n"
    rep, _, _ = scan_with_reviews(tmp_path, files)
    assert ("fx-open", "fx-notes.md", 1) in where(rep)


def test_the_same_text_in_another_file_isnt_covered(tmp_path):
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    review(reg, find(rep, "fx-open", "fx-notes.md", 1))
    files = notes("see stemB-s1 here\n")
    files["fx-open"]["fx-other.md"] = "see stemB-s1 here\n"
    rep, _, _ = scan_with_reviews(tmp_path, files)
    assert where(rep) == {("fx-open", "fx-other.md", 1)}


def test_a_review_names_a_person(tmp_path):
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    f = find(rep, "fx-open", "fx-notes.md", 1)
    with pytest.raises(scan.ScanError, match="person"):
        scan.record_review(reg, f, "fine", "agent:fx-model", "2026-01-01T00:00:00+00:00")
    with pytest.raises(scan.ScanError, match="reason"):
        scan.record_review(reg, f, " ", "human:fx-reviewer", "2026-01-01T00:00:00+00:00")
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
    accept_in(tmp_path, "fx-a", "fx-open", {"gloss"})
    adb.build(tiers.load(reg_file), "fx-c", out)
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
    rep, reg, store = scan_with_reviews(tmp_path, files)
    f = find(rep, "fx-open", "fx-notes.md", 1)
    assert f.hidden == ("fx-a",)
    review(reg, f)
    (tmp_path / "stores" / "fx-a" / "fx-a-more.yaml").unlink()    # it leaves fx-a ...
    files = notes("fxshiftq here\n")
    files["fx-c"]["fx-c-more.yaml"] = "entries:\n- id: fxc1\n  w: fxshiftq\n"   # ... for fx-c
    rep, _, _ = scan_with_reviews(tmp_path, files)
    assert ("fx-open", "fx-notes.md", 1) in where(rep)


def test_a_passage_review_covers_every_line_it_spans(tmp_path):
    files = notes("it said alpha beta gamma\ndelta epsilon, then\n")
    rep, reg, store = scan_with_reviews(tmp_path, files)
    review(reg, find(rep, "fx-open", "fx-notes.md", 1))
    rep, _, _ = scan_with_reviews(tmp_path, notes("it said alpha beta gamma\ndelta epsilon, and more\n"))
    assert ("fx-open", "fx-notes.md", 1) in where(rep)       # line 2 changed under the passage


def test_a_copied_line_is_a_new_finding(tmp_path):
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    review(reg, find(rep, "fx-open", "fx-notes.md", 1))
    rep, _, _ = scan_with_reviews(tmp_path, notes("see stemB-s1 here\nsee stemB-s1 here\n"))
    assert where(rep) == {("fx-open", "fx-notes.md", 2)}


def test_ids_and_review_digests_are_keyed_by_the_scanning_tier(tmp_path):
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    f = find(rep, "fx-open", "fx-notes.md", 1)
    key = bytes.fromhex((store / scan.KEY_FILE).read_text(encoding="ascii").strip())
    assert len(key) == 32
    # Someone without the key can't reproduce the id from the line and a guessed word.
    guess = scan._digest(f.tier, f.rel, f.entry, str(f.nth), "fx-c\x1fstemb s1")[:12]
    assert f.id != guess and "stemb" not in f.id
    # The key never enters the database or any lower store.
    assert not list((tmp_path / "stores" / "fx-open").rglob("scan_key"))


def test_recording_a_review_keeps_the_file_valid(tmp_path):
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\nglossqy\n"))
    path = store / scan.REVIEW_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]", encoding="utf-8")              # flow style, no trailing newline
    review(reg, find(rep, "fx-open", "fx-notes.md", 1))
    review(reg, find(rep, "fx-open", "fx-notes.md", 2))
    assert len(scan.load_reviews(path, reg)) == 2


def test_prose_lines_arent_looked_for_inside_lines(tmp_path):
    files = with_files(**{"fx-c": {"fx-c-notes.md": "fxheadq rules\n"},
                          "fx-open": {"fx-notes.md": "the fxheadq rules apply here\n"}})
    rep = run(tmp_path, files)
    assert ("fx-open", "fx-notes.md", 1) not in where(rep)
    files["fx-open"]["fx-notes.md"] = "fxheadq rules\n"           # the whole line still matches
    assert ("fx-open", "fx-notes.md", 1) in where(run(tmp_path, files))


def test_a_tiers_decision_files_dont_match_the_stores_below(tmp_path):
    """What fx-a records as decisions is read and scanned, but isn't fx-a material, so an
    accepted text can't make fx-open's lines into findings."""
    files = with_files(**{"fx-a": {".lectkit/accepted_matches.yaml":
                                   "- {text: fxkitq shared phrase line, tier: fx-open, reason: r,"
                                   " by: 'human:fx-reviewer', at: t}\n"},
                          "fx-open": {"fx-notes.md": "fxkitq shared phrase line\n"}})
    assert ("fx-open", "fx-notes.md", 1) not in where(run(tmp_path, files))


def test_recording_a_review_below_doesnt_stale_the_scan(tmp_path):
    files = with_files(**{"fx-open": {"fx-notes.md": "see stemA-s2 here\n"}})   # fx-a material
    reg, _, out = setup(tmp_path, files)
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg, {"fx-c": FIELD_NAMES, "fx-a": A_FIELD_NAMES})
        f = find(rep, "fx-open", "fx-notes.md", 1)
        assert f.hidden == ("fx-a",)
        written = scan.record_review(reg, f, "shared", "human:fx-reviewer", "t", scanning="fx-c")
        assert [p.parts[-3] for p in written] == ["fx-a"]
        rep = scan.scan(db, reg, {"fx-c": FIELD_NAMES, "fx-a": A_FIELD_NAMES})  # no rebuild
    assert find(rep, "fx-open", "fx-notes.md", 1).reviewed
    text = written[0].read_text(encoding="utf-8")
    assert "stema" not in text.lower() and "id:" not in text.split("tier:")[0]


def test_other_kit_files_are_still_model_material(tmp_path):
    files = with_files(**{"fx-a": {".lectkit/fx-a-note.md": "fxkitq phrase line\n"},
                          "fx-open": {"fx-notes.md": "fxkitq phrase line\n"}})
    assert ("fx-open", "fx-notes.md", 1) in where(run(tmp_path, files))


def test_decision_arguments_are_checked(tmp_path):
    reg, _, out = setup(tmp_path, BASE)
    with adb.AudienceDB(out) as db, pytest.raises(scan.ScanError, match="accepted must be"):
        scan.scan(db, reg, {"fx-open": {"gloss"}})


def test_text_held_at_two_tiers_names_both(tmp_path):
    """No tier decides for another: the same text held at two tiers needs both decisions,
    since one spelling can carry a different meaning at each."""
    files = with_files(**{"fx-a": {"fx-a-notes.md": "fxsharedq line held twice\n"},
                          "fx-c": {"fx-c-notes.md": "intro\nfxsharedq line held twice\nmore\n"},
                          "fx-open": {"fx-notes.md": "fxsharedq line held twice\n"}})
    f = find(run(tmp_path, files), "fx-open", "fx-notes.md", 1)
    assert f.hidden == ("fx-c", "fx-a")


def test_a_tier_decides_which_of_its_files_arent_material(tmp_path):
    files = with_files(**{"fx-c": {"fx-readme.md": "fxinfraq repository boilerplate line\n",
                                   "lexicon/fx-c-notes.md": "fxcontentq material line\n",
                                   ".lectkit/not_material.txt": "fx-readme.md\n"},
                          "fx-open": {"fx-notes.md": "fxinfraq repository boilerplate line\n"
                                                     "fxcontentq material line\n",
                                      ".lectkit/not_material.txt": "fx-notes.md\n"}})
    rep = run(tmp_path, files)
    hit_lines = {f.line for f in rep.open_findings if f.rel == "fx-notes.md"}
    # fx-c's README isn't its material; its lexicon is. fx-open excluding its own file
    # changes nothing: a lower store is screened whole, and only a higher tier decides.
    assert hit_lines == {2}


TERM_TIERS = """\
register: 1
tiers:
  - {id: fx-open, name: Open, sees: [], store: {path: stores/fx-open, remote: allowed}}
  - {id: fx-a, name: A, sees: [fx-open], store: {path: stores/fx-a, remote: allowed}}
  - {id: fx-c, name: C, sees: [fx-open, fx-a], store: {path: stores/fx-c, remote: none},
     terms: [stores/fx-c/knowledge/fx-c-terms.yaml]}
"""


def term_setup(tmp_path, files):
    reg, reg_file, out = setup(tmp_path, files)
    reg_file.write_text(TERM_TIERS, encoding="utf-8")
    reg = tiers.load(reg_file)
    adb.build(reg, "fx-c", out)
    return reg, out


def test_a_term_register_is_applied_as_rules(tmp_path):
    files = with_files(**{
        "fx-c": {"knowledge/fx-c-terms.yaml":
                 "tier: fx-c\nentries:\n- {id: t1, label: a label phrase here, variants: [fxtermq]}\n"
                 "- {id: t2, label: other, pattern: 'fxpat[a-z]+q'}\n"},
        "fx-open": {"fx-notes.md": "it says fxtermq here\nfxpatzzq too\na label phrase here\n"}})
    reg, out = term_setup(tmp_path, files)
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg, {"fx-c": FIELD_NAMES, "fx-a": A_FIELD_NAMES})
        assert "fx-c" in db.model_tiers("a label phrase here")       # labels stay material
        assert "fx-c" not in db.model_tiers("fxpat[a-z]+q")          # a pattern is a rule only
    got = {(f.line, f.matches) for f in rep.open_findings if f.rel == "fx-notes.md"}
    assert got == {(1, ("term",)), (2, ("term",)), (3, ("value",))}


def test_structure_fields_are_pre_cleared(tmp_path):
    files = with_files(**{
        "fx-c": {".lectkit/structure.yaml": "fields: [status, type, tags]\n",
                 "fx-c-more.yaml": "entries:\n- id: fxs1\n  status: fxdraftq\n  w: fxkeepq\n",
                 "fx-c-note.md": "---\ntype: fxnoteq\ntitle: fxtitleq\n---\nbody\n"},
        "fx-open": {"fx-notes.md": "fxdraftq\nfxkeepq\ntype: fxnoteq\ntitle: fxtitleq\n"}})
    rep = run(tmp_path, files)
    lines = {f.line for f in rep.open_findings if f.rel == "fx-notes.md"}
    assert lines == {2, 4}     # the status value and the type line are structure; the rest isn't



def test_structure_fields_clear_only_short_values_under_their_own_key(tmp_path):
    files = with_files(**{
        "fx-c": {".lectkit/structure.yaml": "fields: [type, tags]\n",
                 "fx-c-more.yaml": "entries:\n- id: fxs2\n  type: fxenumq\n"
                                   "  tags: [fxtagq]\n"
                                   "  examples:\n  - {type: fxlong sentence here held q}\n",
                 "fx-c-open.md": "---\ntype: fxunclosedq\nbody line\n"},
        "fx-open": {"fx-notes.md": "fxenumq\nfxtagq\nfxlong sentence here held q\ntype: fxunclosedq\n"}})
    rep = run(tmp_path, files)
    lines = {f.line for f in rep.open_findings if f.rel == "fx-notes.md"}
    assert lines == {3, 4}    # a long value under `type` is content; an unclosed fence isn't frontmatter


def test_a_lower_stores_structure_list_doesnt_change_its_screening(tmp_path):
    files = with_files(**{
        "fx-open": {".lectkit/structure.yaml": "fields: [w]\n", "fx-notes.md": "w: glossqy\n"}})
    assert ("fx-open", "fx-notes.md", 1) in where(run(tmp_path, files))


def test_structure_and_exclusion_lists_are_digested(tmp_path):
    reg, _, out = setup(tmp_path, BASE)
    kit = tmp_path / "stores" / "fx-a" / ".lectkit" / "structure.yaml"
    kit.parent.mkdir(parents=True, exist_ok=True)
    kit.write_text("fields: [type]\n", encoding="utf-8")
    with adb.AudienceDB(out) as db, pytest.raises(scan.ScanError, match="changed since"):
        scan.scan(db, reg)


def test_a_missing_term_register_stops_the_scan(tmp_path):
    reg, reg_file, out = setup(tmp_path, BASE)
    reg_file.write_text(TERM_TIERS, encoding="utf-8")
    reg = tiers.load(reg_file)
    adb.build(reg, "fx-c", out)
    with adb.AudienceDB(out) as db, pytest.raises(scan.ScanError, match="missing"):
        scan.scan(db, reg)


def test_a_suffix_guard_is_part_of_a_rule(tmp_path):
    files = with_files(**{
        "fx-c": {"knowledge/fx-c-terms.yaml":
                 "entries:\n- {id: t1, label: x, variants: [fxtermq], suffix_guard: '(?!-[a-z])'}\n"},
        "fx-open": {"fx-notes.md": "re.compile('[A-Z]')\n"}})
    reg, out = term_setup(tmp_path, files)
    with adb.AudienceDB(out) as db:
        assert "fx-c" not in db.model_tiers("(?!-[a-z])")


def test_a_term_registers_keys_are_its_format(tmp_path):
    files = with_files(**{
        "fx-c": {"knowledge/fx-c-terms.yaml": "entries:\n- {id: t1, fxregkeyq: x, label: fxlabelq phrase}\n"},
        "fx-open": {"fx-notes.md": "fxregkeyq\n"}})
    reg, out = term_setup(tmp_path, files)
    with adb.AudienceDB(out) as db:
        assert "fx-c" not in db.model_tiers("fxregkeyq")
        assert "fx-c" in db.model_tiers("fxlabelq phrase")
