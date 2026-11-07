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
    terms, regexes = cc.load_deny(
        deny_file(tmp_path, "fx-deny.txt", "# comment\nstemqa\n\nab\nab:cd:ef\n"))
    assert terms == {"stemqa", "ab:cd:ef"}   # two-letter entries are too short to count
    assert regexes == []


def test_json_still_supported(tmp_path):
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
    deny = deny_file(tmp_path, "fx-deny.txt", "stemqa\nab:cd:ef\n")
    target = tmp_path / "fx-sample.md"
    target.write_text(line + "\n", encoding="utf-8")
    assert cc.main(["--deny", str(deny), str(target)]) == 1
    out = capsys.readouterr().out.replace(str(tmp_path), "<tmp>")
    assert "fx-sample.md:1: matches a supplied deny-list term" in out
    assert "stemqa" not in out and "ab:cd:ef" not in out   # never print the term


def test_main_clean_and_word_edges(tmp_path):
    deny = deny_file(tmp_path, "fx-deny.txt", "stemqa\n")
    target = tmp_path / "fx-sample.md"
    target.write_text("xstemqa stemqax\n", encoding="utf-8")
    assert cc.main(["--deny", str(deny), str(target)]) == 0


def test_main_normalises_unicode(tmp_path):
    deny = deny_file(tmp_path, "fx-deny.txt", unicodedata.normalize("NFC", "stémqa") + "\n")
    target = tmp_path / "fx-sample.md"
    target.write_text(unicodedata.normalize("NFD", "the stémqa line") + "\n", encoding="utf-8")
    assert cc.main(["--deny", str(deny), str(target)]) == 1


def test_main_utf16_file_is_read(tmp_path):
    deny = deny_file(tmp_path, "fx-deny.txt", "stemqa\n")
    target = tmp_path / "fx-sample.txt"
    target.write_text("a stemqa line\n", encoding="utf-16")
    assert cc.main(["--deny", str(deny), str(target)]) == 1


def test_main_undecodable_file_is_an_error(tmp_path, capsys):
    target = tmp_path / "fx-sample.bin"
    target.write_bytes(b"\x80\x81\x82 not text")
    assert cc.main([str(target)]) == 1
    assert "cannot be decoded" in capsys.readouterr().out


def test_main_directory_is_expanded(tmp_path):
    deny = deny_file(tmp_path, "fx-deny.txt", "stemqa\n")
    d = tmp_path / "fx-dir"
    (d / "sub").mkdir(parents=True)
    (d / "sub" / "fx-sample.md").write_text("stemqa\n", encoding="utf-8")
    assert cc.main(["--deny", str(deny), str(d)]) == 1


def test_main_missing_path_is_an_error(tmp_path, capsys):
    assert cc.main([str(tmp_path / "fx-absent.md")]) == 1
    assert "does not exist" in capsys.readouterr().out
