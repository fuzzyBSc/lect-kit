"""Tests for scripts/check_content.py, on abstract terms only (lect id fx)."""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_content as cc  # noqa: E402

FX_DENY = """\
group: fx-a
items:
  - key: e1
    caption: an abstract caption naming nothing
    variants: [stemqa, stemqb, no, 1234]
    guard: true
    remark: free text that is never a term
  - key: e2
    caption: another
    pattern: 'sfxzz\\w*'
  - key: e3
    caption: unparseable variant
    variants: ['brk(']
"""


def matches(regexes, text):
    return any(r.search(text) for r in regexes)


def deny_file(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def test_yaml_keys(tmp_path):
    """@AC-content_checker-1, @AC-content_checker-2, @AC-content_checker-3, @AC-content_checker-4, @AC-content_checker-5. Structured deny-lists."""
    terms, regexes = cc.load_deny(deny_file(tmp_path, "fx-deny.yaml", FX_DENY))
    # Flags, captions, remarks, keys and the group name are not terms.
    assert terms == set()
    assert not matches(regexes, "frozen=True, check=True")
    assert not matches(regexes, "free text that is never a term")
    # Variants match as whole words, case-insensitively.
    assert matches(regexes, "a line with StemQA in it")
    assert not matches(regexes, "xstemqa")
    # YAML scalars stay the text written, not booleans or numbers.
    assert matches(regexes, "say no here")
    assert matches(regexes, "code 1234 here")
    # Patterns are regexes.
    assert matches(regexes, "sfxzzing")
    # An invalid fragment is matched literally rather than dropped.
    assert matches(regexes, "has brk( here")


def test_plain_text_list(tmp_path):
    """@AC-content_checker-6. A plain text deny-list."""
    terms, regexes = cc.load_deny(
        deny_file(tmp_path, "fx-deny.txt", "# comment\nstemqa\n\nab\nab:cd:ef\n"))
    assert terms == {"stemqa", "ab:cd:ef"}   # two-letter entries are too short to count
    assert regexes == []


def test_json_still_supported(tmp_path):
    """@AC-content_checker-7. A JSON deny-list."""
    terms, regexes = cc.load_deny(deny_file(
        tmp_path, "fx-deny.json",
        '{"entries": [{"term": "stemqa", "note": "ignored"}, {"pattern": "sfxzz"}]}'))
    assert terms == {"stemqa"}
    assert matches(regexes, "sfxzz")


@pytest.mark.parametrize("line", [
    "see stemqa.",            # full stop after the term
    "foo-stemqa compound",    # hyphenated compound
    "(stemqa)",
    "it's stemqa's",
    "a value ab:cd:ef here",  # a term holding non-word characters
])
def test_main_hits(tmp_path, capsys, line):
    """@AC-content_checker-8. Punctuation around a term; the term is never printed."""
    deny = deny_file(tmp_path, "fx-deny.txt", "stemqa\nab:cd:ef\n")
    target = tmp_path / "fx-sample.md"
    target.write_text(line + "\n", encoding="utf-8")
    assert cc.main(["--deny", str(deny), str(target)]) == 1
    out = capsys.readouterr().out.replace(str(tmp_path), "<tmp>")
    assert "fx-sample.md:1: matches a supplied deny-list term" in out
    assert "stemqa" not in out and "ab:cd:ef" not in out   # never print the term


def test_main_clean_and_word_edges(tmp_path):
    """@AC-content_checker-9. A term inside a longer word is not a hit."""
    deny = deny_file(tmp_path, "fx-deny.txt", "stemqa\n")
    target = tmp_path / "fx-sample.md"
    target.write_text("xstemqa stemqax\n", encoding="utf-8")
    assert cc.main(["--deny", str(deny), str(target)]) == 0


def test_main_normalises_unicode(tmp_path):
    """@AC-content_checker-10. NFC on both sides."""
    deny = deny_file(tmp_path, "fx-deny.txt", unicodedata.normalize("NFC", "stémqa") + "\n")
    target = tmp_path / "fx-sample.md"
    target.write_text(unicodedata.normalize("NFD", "the stémqa line") + "\n", encoding="utf-8")
    assert cc.main(["--deny", str(deny), str(target)]) == 1


def test_main_utf16_file_is_read(tmp_path):
    """@AC-content_checker-11. UTF-16 files are screened."""
    deny = deny_file(tmp_path, "fx-deny.txt", "stemqa\n")
    target = tmp_path / "fx-sample.txt"
    target.write_text("a stemqa line\n", encoding="utf-16")
    assert cc.main(["--deny", str(deny), str(target)]) == 1


def test_main_undecodable_file_is_an_error(tmp_path, capsys):
    """@AC-content_checker-12. Undecodable files are errors."""
    target = tmp_path / "fx-sample.bin"
    target.write_bytes(b"\x80\x81\x82 not text")
    assert cc.main([str(target)]) == 1
    assert "cannot be decoded" in capsys.readouterr().out


def test_main_directory_is_expanded(tmp_path):
    """@AC-content_checker-13. Directories are expanded."""
    deny = deny_file(tmp_path, "fx-deny.txt", "stemqa\n")
    d = tmp_path / "fx-dir"
    (d / "sub").mkdir(parents=True)
    (d / "sub" / "fx-sample.md").write_text("stemqa\n", encoding="utf-8")
    assert cc.main(["--deny", str(deny), str(d)]) == 1


def test_main_missing_path_is_an_error(tmp_path, capsys):
    """@AC-content_checker-14. Missing paths are errors."""
    assert cc.main([str(tmp_path / "fx-absent.md")]) == 1
    assert "does not exist" in capsys.readouterr().out


def test_unparseable_yaml_deny_list_stops_the_run(tmp_path):
    """@AC-content_checker-15. A YAML deny-list that isn't YAML stops the run by name."""
    deny = deny_file(tmp_path, "fx-deny.yaml", "variants: [stemqa\n  - : :\n")
    with pytest.raises(SystemExit) as exc:
        cc.load_deny(deny)
    assert "fx-deny.yaml" in str(exc.value)
    assert "stemqa" not in str(exc.value)


def test_deny_lists_from_environment(tmp_path, capsys, monkeypatch):
    """@AC-content_checker-16. LECT_KIT_DENY names deny-lists."""
    deny = deny_file(tmp_path, "fx-deny.txt", "stemqa\n")
    target = deny_file(tmp_path, "fx-sample.md", "a stemqa line\n")
    monkeypatch.setenv("LECT_KIT_DENY", str(deny))
    assert cc.main([str(target)]) == 1
    out = capsys.readouterr().out
    assert "fx-sample.md:1: matches a supplied deny-list term" in out
    assert "no deny-list supplied" not in out


def test_no_deny_list_notes_generic_checks_only(tmp_path, capsys, monkeypatch):
    """@AC-content_checker-17. Without a deny-list, a note says only generic checks ran."""
    monkeypatch.delenv("LECT_KIT_DENY", raising=False)
    target = deny_file(tmp_path, "fx-sample.md", "a clean line\n")
    assert cc.main([str(target)]) == 0
    out = capsys.readouterr().out
    assert "[NOTE] no deny-list supplied: generic checks only" in out
    assert "0 hit(s) in 1 file(s)" in out


# Built from pieces so this file's own source lines don't trip the generic checks.
@pytest.mark.parametrize("text, label", [
    ("Eld" + "er Stemqa", "honorific + name"),
    ("ta" + "pe 12345", "archive-style identifier"),
    ("C:" + "\\" + "Users" + "\\" + "fxa", "personal path"),
    ("/ho" + "me/fxa/notes", "personal path"),
    ("/Us" + "ers/fxa/notes", "personal path"),
    ("fx-a" + "@" + "example.org", "email address"),
])
def test_generic_checks(tmp_path, capsys, monkeypatch, text, label):
    """@AC-content_checker-18, @AC-content_checker-19, @AC-content_checker-20,
    @AC-content_checker-21. Generic checks need no deny-list."""
    monkeypatch.delenv("LECT_KIT_DENY", raising=False)
    target = deny_file(tmp_path, "fx-sample.md", f"see {text} here\n")
    assert cc.main([str(target)]) == 1
    out = capsys.readouterr().out
    assert f"fx-sample.md:1: {label}" in out
    assert text not in out


def test_attribution_address_is_allowed(tmp_path, monkeypatch):
    """@AC-content_checker-22. The commit attribution address isn't an email hit."""
    monkeypatch.delenv("LECT_KIT_DENY", raising=False)
    target = deny_file(tmp_path, "fx-sample.md", "by noreply" + "@" + "anthropic.com\n")
    assert cc.main([str(target)]) == 0


def test_images_and_compiled_files_are_skipped(tmp_path, capsys):
    """@AC-content_checker-23. Image and compiled files aren't screened."""
    deny = deny_file(tmp_path, "fx-deny.txt", "stemqa\n")
    png = deny_file(tmp_path, "fx-a.PNG", "stemqa\n")
    pyc = deny_file(tmp_path, "fx-a.pyc", "stemqa\n")
    assert cc.main(["--deny", str(deny), str(png), str(pyc)]) == 0
    assert "0 hit(s) in 0 file(s)" in capsys.readouterr().out


def test_checker_skips_its_own_source(capsys):
    """@AC-content_checker-24. The checker doesn't screen its own script."""
    assert cc.main([str(cc.SELF)]) == 0
    assert "0 hit(s) in 0 file(s)" in capsys.readouterr().out


def test_no_path_screens_files_git_would_add(tmp_path, capsys, monkeypatch):
    """@AC-content_checker-25. With no path, git's tracked and addable files are screened."""
    import subprocess
    repo = tmp_path / "fx-repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / ".gitignore").write_text("fx-ignored.md\n", encoding="utf-8")
    (repo / "fx-a.md").write_text("stemqa\n", encoding="utf-8")
    (repo / "fx-ignored.md").write_text("stemqa\n", encoding="utf-8")
    deny = deny_file(tmp_path, "fx-deny.txt", "stemqa\n")
    monkeypatch.setattr(cc, "ROOT", repo.resolve())
    assert cc.main(["--deny", str(deny)]) == 1
    out = capsys.readouterr().out
    assert "fx-a.md:1: matches a supplied deny-list term" in out
    assert "fx-ignored.md" not in out


def test_shared_helpers_give_matching_line_numbers(tmp_path):
    """@AC-content_checker-26. denylist.matchers and denylist.hits, used by the hooks."""
    from lectkit import denylist
    a = deny_file(tmp_path, "fx-a.txt", unicodedata.normalize("NFC", "stémqa") + "\n")
    b = deny_file(tmp_path, "fx-b.yaml", "pattern: 'sfxzz\\w*'\n")
    pats = denylist.matchers([a, str(b)])
    lines = ["clean", unicodedata.normalize("NFD", "the stémqa line"), "xstémqa", "SFXZZing"]
    assert denylist.hits(lines, pats) == [2, 4]


def test_invalid_pattern_is_matched_literally(tmp_path):
    """@AC-content_checker-5. An invalid pattern value is escaped, not dropped."""
    terms, regexes = cc.load_deny(deny_file(tmp_path, "fx-deny.yaml", "pattern: 'brk('\n"))
    assert terms == set()
    assert matches(regexes, "has BRK( here")


def test_a_deny_list_folder_reads_the_structured_lists_in_it(tmp_path, capsys, monkeypatch):
    """@AC-content_checker-27. A folder is read as its YAML and JSON lists, not its notes or hidden folders."""
    monkeypatch.delenv("LECT_KIT_DENY", raising=False)
    lists = tmp_path / "lists"
    (lists / "sub").mkdir(parents=True)
    (lists / ".hidden").mkdir()
    (lists / "a.yaml").write_text("items:\n  - term: stemqa\n", encoding="utf-8")
    (lists / "b.json").write_text('{"terms": [{"term": "stemqb"}]}', encoding="utf-8")
    (lists / "sub" / "c.yml").write_text("- stemqc\n", encoding="utf-8")
    (lists / "README.txt").write_text("plain words here\n", encoding="utf-8")
    (lists / "README.md").write_text("other plain words\n", encoding="utf-8")
    (lists / ".hidden" / "d.yaml").write_text("- stemqd\n", encoding="utf-8")
    target = tmp_path / "target.txt"
    target.write_text("stemqa\nstemqb\nstemqc\nstemqd\nplain words here\nother plain words\n",
                      encoding="utf-8")
    assert cc.main(["--deny", str(lists), str(target)]) == 1
    out = capsys.readouterr().out
    assert "3 hit(s) in 1 file(s)" in out
    assert all(f"target.txt:{n}" not in out for n in (4, 5, 6))


@pytest.mark.parametrize("make", ["missing", "not_utf8", "empty_folder"])
def test_a_deny_list_that_cant_be_read_stops_the_run(tmp_path, capsys, monkeypatch, make):
    """@AC-content_checker-28. A missing, undecodable or empty deny-list stops the run, named by file only."""
    monkeypatch.delenv("LECT_KIT_DENY", raising=False)
    deny = tmp_path / "fx-deny.txt"
    if make == "not_utf8":
        deny.write_bytes(b"stem\xe9qa\xff\n")
    elif make == "empty_folder":
        deny = tmp_path / "fx-lists"
        deny.mkdir()
        (deny / "notes.txt").write_text("stemqa\n", encoding="utf-8")
    target = tmp_path / "target.txt"
    target.write_text("nothing\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        cc.main(["--deny", str(deny), str(target)])
    message = str(e.value)
    assert message.startswith("[ERROR] deny-list")
    assert deny.name in message
    assert str(tmp_path) not in message
    assert "stem" not in message
    assert "hit(s)" not in capsys.readouterr().out


def test_the_shared_reader_expands_folders_and_refuses_undecodable_lists(tmp_path):
    """@AC-content_checker-29. The reader the hooks and scan use behaves like the checker."""
    from lectkit import denylist
    lists = tmp_path / "fx-registers"
    lists.mkdir()
    (lists / "a.yaml").write_text("items:\n  - term: stemqa\n", encoding="utf-8")
    pats = denylist.matchers([lists])
    assert denylist.hits(["x", "a stemqa line"], pats) == [2]
    bad = tmp_path / "fx-bad.yaml"
    bad.write_bytes(b"- stem\xe9qa\xff\n")
    with pytest.raises(SystemExit) as e:
        denylist.matchers([bad])
    assert str(e.value) == "[ERROR] deny-list fx-bad.yaml is not UTF-8 text"


def test_case_sensitive_entries(tmp_path):
    """@AC-content_checker-30. case_sensitive applies to one entry's terms, variants and patterns."""
    body = ("entries:\n"
            "  - {id: e1, variants: [StemQc], term: TermQd, pattern: SfxQe, case_sensitive: true}\n"
            "  - {id: e2, variants: [stemqf]}\n")
    terms, regexes = cc.load_deny(deny_file(tmp_path, "fx-case.yaml", body))
    assert terms == set()
    for hit in ("StemQc", "TermQd", "SfxQe", "STEMQF"):
        assert matches(regexes, hit), hit
    for miss in ("stemqc", "termqd", "sfxqe"):
        assert not matches(regexes, miss), miss


def test_case_sensitive_false_keeps_any_case(tmp_path):
    """@AC-content_checker-30. case_sensitive false is the default behaviour."""
    body = "entries:\n  - {id: e1, variants: [stemqh], term: termqi, case_sensitive: 'false'}\n"
    terms, regexes = cc.load_deny(deny_file(tmp_path, "fx-case.yaml", body))
    assert terms == {"termqi"}
    assert matches(regexes, "STEMQH")


def test_suffix_guard(tmp_path):
    """@AC-content_checker-31. A suffix_guard follows each variant; a pattern is used as written."""
    body = ("entries:\n"
            "  - {id: e1, variants: [stemqg, stemqj], suffix_guard: '(?!-[a-z])'}\n"
            "  - {id: e2, pattern: 'sfxqk', suffix_guard: '(?!-[a-z])'}\n")
    _, regexes = cc.load_deny(deny_file(tmp_path, "fx-guard.yaml", body))
    assert matches(regexes, "a stemqg here")
    assert matches(regexes, "a STEMQJ.")
    assert not matches(regexes, "a stemqg-ly look-alike")
    assert not matches(regexes, "a stemqj-ra look-alike")
    assert matches(regexes, "sfxqk-ly")
    # The guard is a rule, not a term.
    assert not matches(regexes, "(?!-[a-z])")


def test_invalid_suffix_guard_stops(tmp_path):
    """@AC-content_checker-31. An invalid guard stops the run, naming the file only."""
    body = "entries:\n  - {id: e1, variants: [stemqg], suffix_guard: '(?!'}\n"
    p = deny_file(tmp_path, "fx-badguard.yaml", body)
    with pytest.raises(SystemExit) as e:
        cc.load_deny(p)
    assert "fx-badguard.yaml" in str(e.value) and str(tmp_path) not in str(e.value)
    assert "stemqg" not in str(e.value)
