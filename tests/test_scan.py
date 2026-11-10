"""Tests for lectkit.scan, on abstract fixtures only (lect id fx)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lectkit import audience_db as adb, scan, tiers  # noqa: E402
from conftest import grant_yaml, review_yaml  # noqa: E402

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
    # fx-a adds a sense to fx-open's stemA. It writes only its addition: a higher tier never
    # restates, and what its copy writes, the id it attaches to included, is its material.
    "fx-a": {REL: "entries:\n- id: stemA\n  senses:\n  - id: stemA-s2\n"
                  "    gloss: alpha beta gamma delta epsilon zeta\n"},
    "fx-c": {REL: "entries:\n- id: stemB\n  fxkeyqz: 2\n  senses:\n  - id: stemB-s1\n    gloss: glossqy\n"},
}
# The field names fx-c's new record shares with the stores below: decided once by a person.
FIELD_NAMES = {"fx-open": {"entries", "senses", "gloss"}, "fx-a": {"entries", "senses", "gloss"}}
# fx-a's new sense uses the field name `gloss` too; fx-a decides that for itself.
# The container names and the id it attaches with are fx-a's material too, released to fx-open.
A_FIELD_NAMES = {"fx-open": {"gloss", "entries", "senses", "stemA"}}


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
    """@AC-cross_tier_scan-1. Clean lower stores give no findings."""
    rep = run(tmp_path, BASE)
    assert rep.scanned == ["fx-open", "fx-a"]
    assert where(rep) == set()


def test_field_names_need_a_decision(tmp_path):
    """@AC-cross_tier_scan-6. Shared field names aren't exempted on their own."""
    rep = run(tmp_path, BASE, accepted={})
    assert ("fx-open", REL, 3) in where(rep)          # `senses` is also a key in fx-c's new record
    assert ("fx-open", REL, 1) in where(rep)          # `entries`: fx-c writes it, so it's fx-c's


def test_exact_value(tmp_path):
    """@AC-cross_tier_scan-2. A whole line equal to hidden material is a value match."""
    rep = run(tmp_path, with_files(**{"fx-open": {"fx-notes.md": "nothing here\nglossqy\n"}}))
    assert where(rep) == {("fx-open", "fx-notes.md", 2)}
    assert find(rep, "fx-open", "fx-notes.md", 2).matches == ("value",)


def test_a_restricted_id_inside_a_longer_line(tmp_path):
    """@AC-cross_tier_scan-3. A hidden id inside a longer line is a token match."""
    rep = run(tmp_path, with_files(**{"fx-open": {"fx-notes.md": "see stemB-s1 here\n"}}))
    f = find(rep, "fx-open", "fx-notes.md", 1)
    assert f.matches == ("token",) and f.hidden == ("fx-c",) and not f.accepted


def test_a_passage_split_across_lines(tmp_path):
    """@AC-cross_tier_scan-4. A wrapped five-word passage matches on its first line."""
    rep = run(tmp_path, with_files(**{"fx-open": {"fx-notes.md": "it said alpha beta gamma\ndelta epsilon, then\n"}}))
    f = find(rep, "fx-open", "fx-notes.md", 1)
    assert f.matches == ("passage",) and f.hidden == ("fx-a",)


def test_the_lower_store_cant_exempt_a_restricted_key_by_using_it(tmp_path):
    """@AC-cross_tier_scan-7. A lower store can't exempt a key by using it."""
    rep = run(tmp_path, with_files(**{"fx-open": {"fx-planted.yaml": "fxkeyqz: 1\n",
                                                  "fx-notes.md": "fxkeyqz\n"}}))
    assert {("fx-open", "fx-planted.yaml", 1), ("fx-open", "fx-notes.md", 1)} <= where(rep)


def test_every_hidden_tier_is_named_most_restrictive_first(tmp_path):
    """@AC-cross_tier_scan-8. Every hidden tier is named, most restrictive first."""
    # An fx-a passage and an fx-c id on one line: two tiers' material, most restrictive first.
    files = with_files(**{"fx-open": {"fx-notes.md": "alpha beta gamma delta epsilon zeta stemB-s1\n"}})
    f = find(run(tmp_path, files), "fx-open", "fx-notes.md", 1)
    assert f.hidden == ("fx-c", "fx-a")


def test_a_lower_stores_kit_folder_is_read(tmp_path):
    """@AC-cross_tier_scan-9. A lower store's kit folder is scanned."""
    rep = run(tmp_path, with_files(**{"fx-open": {".lectkit/fx-hidden.md": "glossqy\n"}}))
    assert ("fx-open", ".lectkit/fx-hidden.md", 1) in where(rep)


def test_accepting_one_match_doesnt_accept_another_on_the_line(tmp_path):
    """@AC-scan_review-3. An acceptance covers only its text and lower tier."""
    files = with_files(**{"fx-open": {"fx-notes.md": "glossqy and stemB here\n"}})
    rep = run(tmp_path, files, accepted={**FIELD_NAMES, "fx-open": FIELD_NAMES["fx-open"] | {"glossqy"}})
    assert ("fx-open", "fx-notes.md", 1) in where(rep)          # stemB is still open
    rep = run(tmp_path, files, accepted={**FIELD_NAMES,
                                         "fx-open": FIELD_NAMES["fx-open"] | {"glossqy", "stemB"}})
    assert ("fx-open", "fx-notes.md", 1) not in where(rep)
    # A decision for a tier covers the tiers that see it (fx-a sees fx-open), never one below.
    files = with_files(**{"fx-a": {"fx-a-notes.md": "glossqy\n"}})
    rep = run(tmp_path, files, accepted={**FIELD_NAMES, "fx-open": FIELD_NAMES["fx-open"] | {"glossqy"}})
    assert ("fx-a", "fx-a-notes.md", 1) not in where(rep)
    files = with_files(**{"fx-open": {"fx-notes.md": "glossqy\n"}})
    rep = run(tmp_path, files, accepted={**FIELD_NAMES, "fx-a": FIELD_NAMES["fx-a"] | {"glossqy"}})
    assert ("fx-open", "fx-notes.md", 1) in where(rep)


def test_a_decision_lives_with_the_material_it_is_about(tmp_path):
    """@AC-scan_review-1. fx-a's material matched in fx-open is decided in fx-a's store, and fx-c, which reads
    fx-a's store, honours it. fx-c's own accept file doesn't cover fx-a's material."""
    files = with_files(**{"fx-open": {"fx-notes.md": "see stemA-s2 here\n"}})
    reg, _, out = setup(tmp_path, files)
    kit = tmp_path / "stores" / "fx-a" / scan.ACCEPT_FILE
    kit.parent.mkdir(parents=True)
    kit.write_text(grant_yaml([(x, "fx-open", "shared") for x in
                               ("stemA-s2", *sorted(A_FIELD_NAMES["fx-open"]))]), encoding="utf-8")
    adb.build(reg, "fx-c", out)
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg, {"fx-c": FIELD_NAMES})
    assert ("fx-open", "fx-notes.md", 1) not in {(f.tier, f.rel, f.line) for f in rep.open_findings}
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg, {"fx-c": FIELD_NAMES | {"fx-open": {"stemA-s2"}}, "fx-a": {}})
    assert ("fx-open", "fx-notes.md", 1) in where(rep)


def test_a_changed_store_refuses_the_scan(tmp_path):
    """@AC-cross_tier_scan-12. A changed lower file refuses the scan."""
    reg, _, out = setup(tmp_path, BASE)
    (tmp_path / "stores" / "fx-open" / REL).write_text(OPEN_LEX + "# changed\n", encoding="utf-8")
    with adb.AudienceDB(out) as db, pytest.raises(scan.ScanError, match="changed since"):
        scan.scan(db, reg)


def test_a_changed_lower_kit_folder_also_refuses_the_scan(tmp_path):
    """@AC-cross_tier_scan-12. A changed lower kit folder refuses the scan."""
    reg, _, out = setup(tmp_path, BASE)
    kit = tmp_path / "stores" / "fx-open" / ".lectkit" / "x.md"
    kit.parent.mkdir(parents=True)
    kit.write_text("x\n", encoding="utf-8")
    with adb.AudienceDB(out) as db, pytest.raises(scan.ScanError, match="changed since"):
        scan.scan(db, reg)


def accept_in(tmp_path, tier, low, texts):
    kit = tmp_path / "stores" / tier / scan.ACCEPT_FILE
    kit.parent.mkdir(parents=True, exist_ok=True)
    kit.write_text(grant_yaml([(t, low, "field name") for t in sorted(texts)]), encoding="utf-8")


def test_decisions_are_read_from_the_stores(tmp_path):
    """@AC-scan_review-2. Each tier's own accept file decides for its material."""
    reg, _, out = setup(tmp_path, BASE)
    accept_in(tmp_path, "fx-c", "fx-open", {"gloss"})
    accept_in(tmp_path, "fx-a", "fx-open", {"gloss"})
    adb.build(reg, "fx-c", out)          # fx-a's kit folder is part of fx-a's store
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg)
    assert ("fx-open", REL, 5) not in where(rep)      # gloss accepted by both tiers
    assert ("fx-open", REL, 3) in where(rep)          # senses not


@pytest.mark.parametrize("body", [
    "- {text: x}\n", "a: 1\n",
    "- {text: x, tier: fx-open, reason: r, by: 'human:b', at: t}\n",          # the old row shape
    "grants:\n- {batch: b, to: fx-open, reason: english, by: 'human:b', at: t, items: [x]}\n",  # retired
    "fx-z: [x]\n",                                                              # an unknown tier
    "fx-open: [1]\n", "fx-open: x\n"])
def test_bad_accept_file(tmp_path, body):
    """@AC-cross_tier_scan-23. A malformed accept file is refused."""
    reg, _, _ = setup(tmp_path, BASE)
    f = tmp_path / "fx-accepted.yaml"
    f.write_text(body, encoding="utf-8")
    with pytest.raises(scan.ScanError):
        scan.load_accepted(f, reg)


@pytest.mark.parametrize("owner,grantee", [("fx-a", "fx-c"), ("fx-a", "fx-a"), ("fx-open", "fx-a")])
def test_a_grant_goes_only_to_a_tier_below(tmp_path, owner, grantee):
    """@AC-cross_tier_scan-27. A tier's grant or review names only a tier it sees."""
    reg, _, _ = setup(tmp_path, BASE)
    f = tmp_path / "fx-accepted.yaml"
    f.write_text(grant_yaml([("x", grantee, "r")]), encoding="utf-8")
    with pytest.raises(scan.ScanError):
        scan.load_accepted(f, reg, owner=owner)
    r = tmp_path / "fx-reviewed.yaml"
    r.write_text(review_yaml([{"tier": grantee, "rel": "x", "entry": "e", "matched": ["m"],
                               "nth": 1}]), encoding="utf-8")
    with pytest.raises(scan.ScanError):
        scan.load_reviews(r, reg, owner=owner)
    f.write_text(grant_yaml([("x", "fx-open", "r")]), encoding="utf-8")
    assert scan.load_accepted(f, reg, owner="fx-c") == {"fx-open": {"x"}}


def test_a_grant_to_a_tier_holds_for_every_tier_that_sees_it(tmp_path):
    """@AC-cross_tier_scan-28. What fx-c releases to fx-open, fx-a already sees, so it holds nothing in fx-a."""
    files = with_files(**{"fx-a": {"fx-a-notes.md": "nothing here\nglossqy\n"}})
    reg, _, out = setup(tmp_path, files)
    with adb.AudienceDB(out) as db:
        held = where(scan.scan(db, reg, {"fx-c": {}, "fx-a": A_FIELD_NAMES}))
        assert ("fx-a", "fx-a-notes.md", 2) in held
        granted = where(scan.scan(db, reg, {"fx-c": {"fx-open": {"glossqy"}}, "fx-a": A_FIELD_NAMES}))
    assert ("fx-a", "fx-a-notes.md", 2) not in granted


def test_cli(tmp_path, capsys):
    """@AC-cross_tier_scan-20, @AC-cross_tier_scan-21. The printed report names where, never what, and never goes lower."""
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
    """@AC-scan_review-4. A reviewed entry stays cleared."""
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    f = find(rep, "fx-open", "fx-notes.md", 1)
    assert not f.cleared
    review(reg, f)
    rep, _, _ = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    assert find(rep, "fx-open", "fx-notes.md", 1).reviewed
    assert where(rep) == set()


def test_moving_the_entry_keeps_the_review(tmp_path):
    """@AC-scan_review-5. A review follows its entry to another line."""
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    review(reg, find(rep, "fx-open", "fx-notes.md", 1))
    rep, _, _ = scan_with_reviews(tmp_path, notes("a new first line\nsee stemB-s1 here\n"))
    assert find(rep, "fx-open", "fx-notes.md", 2).reviewed


def test_changing_the_entry_needs_a_new_review(tmp_path):
    """@AC-scan_review-6. Changed lower text reopens the finding."""
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    review(reg, find(rep, "fx-open", "fx-notes.md", 1))
    rep, _, _ = scan_with_reviews(tmp_path, notes("see stemB-s1 there\n"))
    assert ("fx-open", "fx-notes.md", 1) in where(rep)


def test_a_new_hidden_match_on_the_entry_needs_a_new_review(tmp_path):
    """@AC-scan_review-8. A new hidden match reopens the finding."""
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    review(reg, find(rep, "fx-open", "fx-notes.md", 1))
    files = notes("see stemB-s1 here\n")
    files["fx-c"]["fx-c-more.yaml"] = "entries:\n- id: fxsee\n  w: see stemB-s1 here\n"
    rep, _, _ = scan_with_reviews(tmp_path, files)
    assert ("fx-open", "fx-notes.md", 1) in where(rep)


def test_the_same_text_in_another_file_isnt_covered(tmp_path):
    """@AC-scan_review-11. A review doesn't cover another file."""
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    review(reg, find(rep, "fx-open", "fx-notes.md", 1))
    files = notes("see stemB-s1 here\n")
    files["fx-open"]["fx-other.md"] = "see stemB-s1 here\n"
    rep, _, _ = scan_with_reviews(tmp_path, files)
    assert where(rep) == {("fx-open", "fx-other.md", 1)}


def test_a_review_names_a_person(tmp_path):
    """@AC-scan_review-12. A review needs a person and a reason."""
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    f = find(rep, "fx-open", "fx-notes.md", 1)
    with pytest.raises(scan.ScanError, match="person"):
        scan.record_review(reg, f, "fine", "agent:fx-model", "2026-01-01T00:00:00+00:00")
    with pytest.raises(scan.ScanError, match="reason"):
        scan.record_review(reg, f, " ", "human:fx-reviewer", "2026-01-01T00:00:00+00:00")


def test_review_cli(tmp_path, capsys):
    """@AC-scan_review-4, @AC-scan_review-16. review_finding.py records a review; an unknown id is refused."""
    import re as _re
    import review_finding
    import scan_tiers as cli
    _, reg_file, out = setup(tmp_path, notes("see stemB-s1 here\n"))
    kit = tmp_path / "stores" / "fx-c" / scan.ACCEPT_FILE
    kit.parent.mkdir(parents=True, exist_ok=True)
    kit.write_text(grant_yaml([(t, low, "field name") for low, ts in FIELD_NAMES.items()
                               for t in sorted(ts)]), encoding="utf-8")
    accept_in(tmp_path, "fx-a", "fx-open", A_FIELD_NAMES["fx-open"])
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
    """@AC-scan_review-9. A matched item moving tier reopens the finding."""
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
    """@AC-scan_review-7. A passage review covers every line it spans."""
    files = notes("it said alpha beta gamma\ndelta epsilon, then\n")
    rep, reg, store = scan_with_reviews(tmp_path, files)
    review(reg, find(rep, "fx-open", "fx-notes.md", 1))
    rep, _, _ = scan_with_reviews(tmp_path, notes("it said alpha beta gamma\ndelta epsilon, and more\n"))
    assert ("fx-open", "fx-notes.md", 1) in where(rep)       # line 2 changed under the passage


def test_a_copied_line_is_a_new_finding(tmp_path):
    """@AC-scan_review-10. A copied line is a new finding."""
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\n"))
    review(reg, find(rep, "fx-open", "fx-notes.md", 1))
    rep, _, _ = scan_with_reviews(tmp_path, notes("see stemB-s1 here\nsee stemB-s1 here\n"))
    assert where(rep) == {("fx-open", "fx-notes.md", 2)}


def test_ids_and_review_digests_are_keyed_by_the_scanning_tier(tmp_path):
    """@AC-scan_review-15. Finding ids are keyed."""
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
    """@AC-scan_review-14. Recording a review keeps the file valid."""
    rep, reg, store = scan_with_reviews(tmp_path, notes("see stemB-s1 here\nglossqy\n"))
    path = store / scan.REVIEW_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")   # flow style, no trailing newline
    review(reg, find(rep, "fx-open", "fx-notes.md", 1))
    review(reg, find(rep, "fx-open", "fx-notes.md", 2))
    assert len(scan.load_reviews(path, reg)) == 2


def test_prose_lines_arent_looked_for_inside_lines(tmp_path):
    """@AC-cross_tier_scan-5. Prose matches whole, not inside other lines."""
    files = with_files(**{"fx-c": {"fx-c-notes.md": "fxheadq rules\n"},
                          "fx-open": {"fx-notes.md": "the fxheadq rules apply here\n"}})
    rep = run(tmp_path, files)
    assert ("fx-open", "fx-notes.md", 1) not in where(rep)
    files["fx-open"]["fx-notes.md"] = "fxheadq rules\n"           # the whole line still matches
    assert ("fx-open", "fx-notes.md", 1) in where(run(tmp_path, files))


def test_a_tiers_grant_file_is_material_and_what_it_grants_is_released(tmp_path):
    """@AC-cross_tier_scan-11. fx-a's grant file is fx-a material like any other, and what it grants is
    released to fx-open by that same grant, so the granted line is accepted, not held."""
    files = with_files(**{"fx-a": {".lectkit/accepted_matches.yaml":
                                   grant_yaml([("fxkitq shared phrase line", "fx-open", "r")])},
                          "fx-open": {"fx-notes.md": "fxkitq shared phrase line\n"}})
    reg, _, out = setup(tmp_path, files)
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg, {"fx-c": FIELD_NAMES})      # fx-a's grants come from its store
    f = find(rep, "fx-open", "fx-notes.md", 1)
    assert "fx-a" in f.hidden and f.accepted


def test_recording_a_review_below_is_saved_with_its_material(tmp_path):
    """@AC-scan_review-13. A review is saved with the material it is about."""
    files = with_files(**{"fx-open": {"fx-notes.md": "see stemA-s2 here\n"}})   # fx-a material
    reg, _, out = setup(tmp_path, files)
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg, {"fx-c": FIELD_NAMES, "fx-a": A_FIELD_NAMES})
        f = find(rep, "fx-open", "fx-notes.md", 1)
        assert f.hidden == ("fx-a",)
        written = scan.record_review(reg, f, "shared", "human:fx-reviewer", "t", scanning="fx-c")
        assert [p.parts[-3] for p in written] == ["fx-a"]
        assert "fx-notes.md" not in written[0].read_text(encoding="utf-8")   # the path is a hash
        with pytest.raises(scan.ScanError, match="rebuild"):    # a review is fx-a material now
            scan.scan(db, reg, {"fx-c": FIELD_NAMES, "fx-a": A_FIELD_NAMES})
    adb.build(reg, "fx-c", out)
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg, {"fx-c": FIELD_NAMES, "fx-a": A_FIELD_NAMES})
    assert find(rep, "fx-open", "fx-notes.md", 1).reviewed
    text = written[0].read_text(encoding="utf-8")
    assert "stema" not in text.lower() and "id:" not in text.split("tier:")[0]


def test_other_kit_files_are_still_model_material(tmp_path):
    """@AC-cross_tier_scan-10. A higher tier's other kit files are its material."""
    files = with_files(**{"fx-a": {".lectkit/fx-a-note.md": "fxkitq phrase line\n"},
                          "fx-open": {"fx-notes.md": "fxkitq phrase line\n"}})
    assert ("fx-open", "fx-notes.md", 1) in where(run(tmp_path, files))


def test_decision_arguments_are_checked(tmp_path):
    """@AC-cross_tier_scan-23. Decisions in the wrong shape are refused."""
    reg, _, out = setup(tmp_path, BASE)
    with adb.AudienceDB(out) as db, pytest.raises(scan.ScanError, match="accepted must be"):
        scan.scan(db, reg, {"fx-open": {"gloss"}})


def test_text_held_at_two_tiers_names_both(tmp_path):
    """@AC-cross_tier_scan-8. No tier decides for another: the same text held at two tiers needs both decisions,
    since one spelling can carry a different meaning at each."""
    files = with_files(**{"fx-a": {"fx-a-notes.md": "fxsharedq line held twice\n"},
                          "fx-c": {"fx-c-notes.md": "intro\nfxsharedq line held twice\nmore\n"},
                          "fx-open": {"fx-notes.md": "fxsharedq line held twice\n"}})
    f = find(run(tmp_path, files), "fx-open", "fx-notes.md", 1)
    assert f.hidden == ("fx-c", "fx-a")


def test_a_tier_decides_which_of_its_files_arent_material(tmp_path):
    """@AC-cross_tier_scan-13. Only a higher tier excludes its own files."""
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
    """@AC-cross_tier_scan-17, @AC-cross_tier_scan-18. A term register is applied as rules; labels stay material."""
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
    """@AC-cross_tier_scan-14. Short structure values aren't material."""
    files = with_files(**{
        "fx-c": {".lectkit/structure.yaml": "fields: [status, type, tags]\n",
                 "fx-c-more.yaml": "entries:\n- id: fxs1\n  status: fxdraftq\n  w: fxkeepq\n",
                 "fx-c-note.md": "---\ntype: fxnoteq\ntitle: fxtitleq\n---\nbody\n"},
        "fx-open": {"fx-notes.md": "fxdraftq\nfxkeepq\ntype: fxnoteq\ntitle: fxtitleq\n"}})
    rep = run(tmp_path, files)
    lines = {f.line for f in rep.open_findings if f.rel == "fx-notes.md"}
    assert lines == {2, 4}     # the status value and the type line are structure; the rest isn't



def test_structure_fields_clear_only_short_values_under_their_own_key(tmp_path):
    """@AC-cross_tier_scan-15. Long structure values and unclosed frontmatter are material."""
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
    """@AC-cross_tier_scan-16. A lower store's structure list changes nothing."""
    files = with_files(**{
        "fx-open": {".lectkit/structure.yaml": "fields: [w]\n", "fx-notes.md": "w: glossqy\n"}})
    assert ("fx-open", "fx-notes.md", 1) in where(run(tmp_path, files))


def test_structure_and_exclusion_lists_are_digested(tmp_path):
    """@AC-cross_tier_scan-12. A changed structure list refuses the scan."""
    reg, _, out = setup(tmp_path, BASE)
    kit = tmp_path / "stores" / "fx-a" / ".lectkit" / "structure.yaml"
    kit.parent.mkdir(parents=True, exist_ok=True)
    kit.write_text("fields: [type]\n", encoding="utf-8")
    with adb.AudienceDB(out) as db, pytest.raises(scan.ScanError, match="changed since"):
        scan.scan(db, reg)


def test_a_missing_term_register_stops_the_scan(tmp_path):
    """@AC-cross_tier_scan-19. A missing term register stops the scan."""
    reg, reg_file, out = setup(tmp_path, BASE)
    reg_file.write_text(TERM_TIERS, encoding="utf-8")
    reg = tiers.load(reg_file)
    adb.build(reg, "fx-c", out)
    with adb.AudienceDB(out) as db, pytest.raises(scan.ScanError, match="missing"):
        scan.scan(db, reg)


def test_a_suffix_guard_is_part_of_a_rule(tmp_path):
    """@AC-cross_tier_scan-18. A suffix guard is a rule, not material."""
    files = with_files(**{
        "fx-c": {"knowledge/fx-c-terms.yaml":
                 "entries:\n- {id: t1, label: x, variants: [fxtermq], suffix_guard: '(?!-[a-z])'}\n"},
        "fx-open": {"fx-notes.md": "re.compile('[A-Z]')\n"}})
    reg, out = term_setup(tmp_path, files)
    with adb.AudienceDB(out) as db:
        assert "fx-c" not in db.model_tiers("(?!-[a-z])")


def test_a_term_registers_keys_are_its_format(tmp_path):
    """@AC-cross_tier_scan-18. A register's keys aren't material; its labels are."""
    files = with_files(**{
        "fx-c": {"knowledge/fx-c-terms.yaml": "entries:\n- {id: t1, fxregkeyq: x, label: fxlabelq phrase}\n"},
        "fx-open": {"fx-notes.md": "fxregkeyq\n"}})
    reg, out = term_setup(tmp_path, files)
    with adb.AudienceDB(out) as db:
        assert "fx-c" not in db.model_tiers("fxregkeyq")
        assert "fx-c" in db.model_tiers("fxlabelq phrase")


def test_cli_lists_accepted_on_request_and_refuses_what_it_cant_scan(tmp_path, capsys):
    """@AC-cross_tier_scan-22, @AC-cross_tier_scan-12, @AC-cross_tier_scan-23. Accepted
    findings are counted and shown with --show-accepted; a stale database or a bad accept
    file exits 3."""
    import scan_tiers as cli
    reg, reg_file, out = setup(tmp_path, BASE)
    kit = tmp_path / "stores" / "fx-c" / scan.ACCEPT_FILE
    kit.parent.mkdir(parents=True, exist_ok=True)
    kit.write_text(grant_yaml([(t, low, "field name") for low, ts in FIELD_NAMES.items()
                               for t in sorted(ts)]), encoding="utf-8")
    accept_in(tmp_path, "fx-a", "fx-open", A_FIELD_NAMES["fx-open"])
    adb.build(reg, "fx-c", out)
    args = ["--register", str(reg_file), "--db", str(out)]
    assert cli.main(args) == 0
    printed = capsys.readouterr().out
    assert "[ACCEPTED]" not in printed and "0 finding(s)" in printed
    assert " 0 accepted" not in printed
    assert cli.main(args + ["--show-accepted"]) == 0
    assert "[ACCEPTED]" in capsys.readouterr().out
    kit.write_text("- {text: x}\n", encoding="utf-8")      # fx-c's own kit folder: not stale
    assert cli.main(args) == 3
    kit.unlink()
    (tmp_path / "stores" / "fx-open" / REL).write_text(OPEN_LEX + "# changed\n", encoding="utf-8")
    assert cli.main(args) == 3


def test_a_term_match_can_be_accepted(tmp_path):
    """@AC-cross_tier_scan-17. A term match is accepted by the text the scan reports for it."""
    files = with_files(**{
        "fx-c": {"knowledge/fx-c-terms.yaml":
                 "tier: fx-c\nentries:\n- {id: t1, label: other, variants: [fxtermq]}\n"},
        "fx-open": {"fx-notes.md": "it says fxtermq here\n"}})
    reg, out = term_setup(tmp_path, files)
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg, {"fx-c": FIELD_NAMES, "fx-a": A_FIELD_NAMES})
        f = next(f for f in rep.open_findings if f.rel == "fx-notes.md")
        acc = {"fx-c": {**FIELD_NAMES, "fx-open": FIELD_NAMES.get("fx-open", set()) | {t for _, t in f.items}},
               "fx-a": A_FIELD_NAMES}
        rep = scan.scan(db, reg, acc)
    assert not [f for f in rep.open_findings if f.rel == "fx-notes.md"]


def test_granting_a_shared_list_releases_the_reference_too(tmp_path, monkeypatch):
    """@AC-cross_tier_scan-31. fx-a's grant file names a list; fx-open writing the same line isn't held."""
    from lectkit import shared_lists
    ld = tmp_path / "lists"; ld.mkdir()
    (ld / "fxwords-v1.txt").write_text("ordinaryqz\n", encoding="utf-8")
    monkeypatch.setattr(shared_lists, "LIST_DIR", ld)
    grant = "fx-open: ['list:fxwords-v1', gloss, entries, senses, stemA]\n"
    files = with_files(**{"fx-a": {".lectkit/accepted_matches.yaml": grant},
                          "fx-open": {"refs.md": "list:fxwords-v1\n"}})
    reg, _, out = setup(tmp_path, files)
    with adb.AudienceDB(out) as db:
        rep = scan.scan(db, reg, {"fx-c": FIELD_NAMES})
    assert ("fx-open", "refs.md", 1) not in where(rep)


def test_a_run_of_single_letters_is_never_a_token_match(tmp_path):
    """@AC-cross_tier_scan-34. Single-letter runs don't match as tokens; whole values still do."""
    files = with_files(**{"fx-c": {"fx-pairs.yaml": "pairs:\n- id: nipair\n  seq: n i\n"},
                          "fx-open": {"code.py": 'x = out.index(b"\n", i)\n', "pair.md": "n i\n"}})
    rep = run(tmp_path, files, accepted={**FIELD_NAMES, "fx-open": FIELD_NAMES["fx-open"] | {"pairs", "seq"}})
    assert ("fx-open", "code.py", 1) not in where(rep)
    assert ("fx-open", "pair.md", 1) in where(rep)


def test_hashes_and_date_times_are_format(tmp_path):
    """@AC-cross_tier_scan-35. The format mask takes out hashes, date-times and git timestamps only."""
    files = with_files(**{"fx-c": {"fx-nums.yaml": "nums:\n- id: fxn1\n  v: '0930'\n  w: fxzone\n"},
                          "fx-open": {"log.md": "author fx <fx@fx.test> 1794302574 +0930\n"
                                                "tree e4424073fae80d1c7d588c41c4cea9f8dc57d8a0 at 2026-11-10T09:15:00+10:00\n"
                                                "0930\n"
                                                "fxzone a579a65\n"}})
    acc = {**FIELD_NAMES, "fx-open": FIELD_NAMES["fx-open"] | {"nums", "v", "w"}}
    found = {(r, n) for t, r, n in where(run(tmp_path, files, accepted=acc)) if r == "log.md"}
    assert found == {("log.md", 3), ("log.md", 4)}


def test_a_passage_never_runs_across_table_cells(tmp_path):
    """@AC-cross_tier_scan-36. Cell borders break passages on both sides; a run inside a cell matches."""
    files = with_files(**{"fx-c": {"fx-table.md": "| fxvar | alpha beta gamma delta | eps zeta eta theta iota |\n"},
                          "fx-open": {"cross.md": "fxvar alpha beta gamma delta\n",
                                      "inside.md": "eps zeta eta theta iota\n",
                                      "cells.md": "| eps zeta | eta theta iota |\n"}})
    found = {r for t, r, n in where(run(tmp_path, files)) if r.endswith(".md") and r != "fx-notes.md"}
    assert found == {"inside.md"}
