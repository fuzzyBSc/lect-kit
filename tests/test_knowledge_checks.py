"""Tests for the knowledge/ and schemes/ checkers, on small trees under tmp_path.

Covers scripts/check_knowledge_frontmatter.py, scripts/check_knowledge_refs.py and
scripts/check_identifiers.py. Never reads the real repository's knowledge/ or schemes/.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_identifiers as ci  # noqa: E402
import check_knowledge_frontmatter as kf  # noqa: E402
import check_knowledge_refs as kr  # noqa: E402

GOOD_FM = """\
---
type: Spec
title: Fixture spec
description: A fixture file that follows the profile.
tags: [process, content]
status: draft
generated: {by: agent:fx-model, at: 2026-11-07T19:00:00+10:00}
verified:
  - {by: human:project custodian, at: 2026-11-07T20:00:00+10:00}
sources:
  - {resource: examples/demo/fixtures/README.md}
  - {resource: examples/demo/README.md, id: fx-a}
stale_after: 2027-11-07T00:00:00+00:00
---

# Fixture spec
"""


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- frontmatter -------------------------------------------------------------------


@pytest.fixture
def fm_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(kf, "ROOT", tmp_path)
    monkeypatch.setattr(kf, "KNOWLEDGE", tmp_path / "knowledge")
    (tmp_path / "knowledge").mkdir()
    return tmp_path


def run_fm(capsys) -> tuple[int, str]:
    code = kf.main()
    return code, capsys.readouterr().out


def with_fm(body: str) -> str:
    return f"---\n{body}---\n\n# Fixture\n"


BASE = "type: Spec\ntitle: Fixture\ndescription: A fixture.\n"


def test_frontmatter_profile_passes(fm_tree, capsys):
    """@AC-knowledge_checks-1. A file that follows the profile passes."""
    write(fm_tree / "knowledge" / "spec_fx.md", GOOD_FM)
    code, out = run_fm(capsys)
    assert code == 0
    assert "[ERROR]" not in out
    assert "0 problem(s) in 1 file(s)" in out


def test_frontmatter_missing_block(fm_tree, capsys):
    """@AC-knowledge_checks-2. A file with no frontmatter fails."""
    write(fm_tree / "knowledge" / "fx.md", "# Fixture\n")
    code, out = run_fm(capsys)
    assert code == 1
    assert "[ERROR] knowledge/fx.md: no frontmatter" in out


def test_frontmatter_missing_required_keys(fm_tree, capsys):
    """@AC-knowledge_checks-3. Each missing required key is reported, empty block included."""
    write(fm_tree / "knowledge" / "fx.md", with_fm("status: draft\n"))
    write(fm_tree / "knowledge" / "fy.md", "---\n\n---\n")
    code, out = run_fm(capsys)
    assert code == 1
    for f in ("fx", "fy"):
        for k in ("type", "title", "description"):
            assert f"knowledge/{f}.md: missing {k}" in out


def test_frontmatter_unknown_key(fm_tree, capsys):
    """@AC-knowledge_checks-4. A key outside the profile is reported."""
    write(fm_tree / "knowledge" / "fx.md", with_fm(BASE + "colour: blue\n"))
    code, out = run_fm(capsys)
    assert code == 1
    assert "knowledge/fx.md: unknown key colour" in out


def test_frontmatter_bad_type(fm_tree, capsys):
    """@AC-knowledge_checks-5. A type outside the profile is reported."""
    write(fm_tree / "knowledge" / "fx.md",
          with_fm("type: Essay\ntitle: Fixture\ndescription: A fixture.\n"))
    code, out = run_fm(capsys)
    assert code == 1
    assert "type 'Essay' not in the profile" in out


@pytest.mark.parametrize("title", ["Fixture.", "'  '", "[a, b]"])
def test_frontmatter_bad_title(fm_tree, capsys, title):
    """@AC-knowledge_checks-6. A title with a full stop, blank or not text is reported."""
    write(fm_tree / "knowledge" / "fx.md",
          with_fm(f"type: Spec\ntitle: {title}\ndescription: A fixture.\n"))
    code, out = run_fm(capsys)
    assert code == 1
    assert "title must be a short phrase with no trailing full stop" in out


@pytest.mark.parametrize("desc", [
    "A fixture with no full stop",
    "A fixture. Then a second sentence.",
    "A " + "long " * 50 + "fixture.",
])
def test_frontmatter_bad_description(fm_tree, capsys, desc):
    """@AC-knowledge_checks-7. A description that isn't one short sentence is reported."""
    write(fm_tree / "knowledge" / "fx.md",
          with_fm(f"type: Spec\ntitle: Fixture\ndescription: {desc}\n"))
    code, out = run_fm(capsys)
    assert code == 1
    assert "description must be one sentence ending in a full stop" in out


@pytest.mark.parametrize("tags", [
    "[process, content, corpus, paradigm, rendering]",
    "[process, fx-a]",
    "process",
])
def test_frontmatter_bad_tags(fm_tree, capsys, tags):
    """@AC-knowledge_checks-8. Too many tags, an unknown tag or a non-list is reported."""
    write(fm_tree / "knowledge" / "fx.md", with_fm(BASE + f"tags: {tags}\n"))
    code, out = run_fm(capsys)
    assert code == 1
    assert "tags must be a list of at most four profile tags" in out


def test_frontmatter_bad_status(fm_tree, capsys):
    """@AC-knowledge_checks-9. A status outside the three is reported."""
    write(fm_tree / "knowledge" / "fx.md", with_fm(BASE + "status: final\n"))
    code, out = run_fm(capsys)
    assert code == 1
    assert "status must be draft, stable or deprecated" in out


@pytest.mark.parametrize("generated, error", [
    ("{by: agent:fx, at: 2026-11-07T19:00:00+10:00, note: x}", "generated entry must be {by, at}"),
    ("fx", "generated entry must be {by, at}"),
    ("{by: fx, at: 2026-11-07T19:00:00+10:00}", "generated.by must start with agent: or human:"),
    ("{by: agent:fx, at: 2026-11-07T19:00:00}", "generated.at must be an ISO 8601 datetime with an offset"),
    ("{by: agent:fx, at: '2026-11-07T19:00:00'}", "generated.at must be an ISO 8601 datetime with an offset"),
    ("{by: agent:fx, at: not a time}", "generated.at must be an ISO 8601 datetime with an offset"),
])
def test_frontmatter_bad_generated(fm_tree, capsys, generated, error):
    """@AC-knowledge_checks-10. A malformed generated entry is reported."""
    write(fm_tree / "knowledge" / "fx.md", with_fm(BASE + f"generated: {generated}\n"))
    code, out = run_fm(capsys)
    assert code == 1
    assert error in out


def test_frontmatter_generated_as_quoted_text_passes(fm_tree, capsys):
    """@AC-knowledge_checks-10. A quoted datetime with an offset is accepted."""
    write(fm_tree / "knowledge" / "fx.md",
          with_fm(BASE + "generated: {by: 'human:fx', at: '2026-11-07T19:00:00+10:00'}\n"))
    code, out = run_fm(capsys)
    assert code == 0, out


def test_frontmatter_verified_by_agent(fm_tree, capsys):
    """@AC-knowledge_checks-11. Verified must be by a human actor."""
    write(fm_tree / "knowledge" / "fx.md",
          with_fm(BASE + "verified:\n  - {by: agent:fx, at: 2026-11-07T19:00:00+10:00}\n"))
    code, out = run_fm(capsys)
    assert code == 1
    assert "verified.by must be a human: actor" in out


@pytest.mark.parametrize("source", ["{id: fx-a}", "{resource: fx, note: x}", "fx"])
def test_frontmatter_bad_sources(fm_tree, capsys, source):
    """@AC-knowledge_checks-12. A source with no resource, an extra key or plain text."""
    write(fm_tree / "knowledge" / "fx.md", with_fm(BASE + f"sources:\n  - {source}\n"))
    code, out = run_fm(capsys)
    assert code == 1
    assert "sources entries must be {resource, id?}" in out


@pytest.mark.parametrize("value", ["2027-01-01", "2027-01-01T00:00:00"])
def test_frontmatter_bad_stale_after(fm_tree, capsys, value):
    """@AC-knowledge_checks-13. stale_after needs a time and an offset."""
    write(fm_tree / "knowledge" / "fx.md", with_fm(BASE + f"stale_after: {value}\n"))
    code, out = run_fm(capsys)
    assert code == 1
    assert "stale_after must be an ISO 8601 datetime with an offset" in out


def test_frontmatter_subfolders_are_checked(fm_tree, capsys):
    """@AC-knowledge_checks-14. Files in folders under knowledge/ are checked."""
    write(fm_tree / "knowledge" / "fx-sub" / "fx.md", "# Fixture\n")
    code, out = run_fm(capsys)
    assert code == 1
    assert "[ERROR] knowledge/fx-sub/fx.md: no frontmatter" in out


# --- citations ---------------------------------------------------------------------


@pytest.fixture
def refs_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(kr, "ROOT", tmp_path)
    write(tmp_path / "PRINCIPLES.md",
          "# Principles\n\n## 1. First\n\nText.\n\n## 2. Second\n\n## 3. Third\n")
    write(tmp_path / "docs" / "fx_page.md", "# Fixture page\n")
    (tmp_path / "knowledge").mkdir()
    return tmp_path


def run_refs(capsys) -> tuple[int, str]:
    code = kr.main()
    return code, capsys.readouterr().out


def test_refs_spec_with_citation_and_docs_passes(refs_tree, capsys):
    """@AC-knowledge_checks-15. A spec citing an existing section and docs page passes."""
    write(refs_tree / "knowledge" / "spec_fx.md",
          "Carries out `PRINCIPLES.md` §1. People read `docs/fx_page.md`.\n")
    code, out = run_refs(capsys)
    assert code == 0
    assert out.strip() == "0 problem(s)"


def test_refs_missing_section(refs_tree, capsys):
    """@AC-knowledge_checks-16. A cited section that doesn't exist is reported."""
    write(refs_tree / "knowledge" / "README.md", "See `PRINCIPLES.md` §9.\n")
    code, out = run_refs(capsys)
    assert code == 1
    assert "[ERROR] knowledge/README.md: cites PRINCIPLES.md §9, which doesn't exist" in out


def test_refs_spec_and_procedure_must_cite(refs_tree, capsys):
    """@AC-knowledge_checks-17. A spec and a procedure that cite nothing are reported."""
    write(refs_tree / "knowledge" / "spec_fx.md", "People read `docs/fx_page.md`.\n")
    write(refs_tree / "knowledge" / "fx_procedure.md", "PRINCIPLES.md §1 without backticks.\n")
    code, out = run_refs(capsys)
    assert code == 1
    assert "knowledge/spec_fx.md: cites no PRINCIPLES.md section" in out
    assert "knowledge/fx_procedure.md: cites no PRINCIPLES.md section" in out


def test_refs_other_files_needn_t_cite(refs_tree, capsys):
    """@AC-knowledge_checks-18. A file that is neither spec nor procedure needn't cite."""
    write(refs_tree / "knowledge" / "fx_tracker.md", "Nothing cited here.\n")
    code, out = run_refs(capsys)
    assert code == 0, out


def test_refs_citation_lists_several_sections(refs_tree, capsys):
    """@AC-knowledge_checks-19. A list of sections is read whole."""
    write(refs_tree / "knowledge" / "fx_procedure.md",
          "Carries out `PRINCIPLES.md` §1, §2 and §4.\n")
    code, out = run_refs(capsys)
    assert code == 1
    assert "cites PRINCIPLES.md §4, which doesn't exist" in out
    assert "§1," not in out and "§2," not in out
    assert out.count("[ERROR]") == 1


def test_refs_spec_names_no_docs_page(refs_tree, capsys):
    """@AC-knowledge_checks-20. A spec must name a docs page."""
    write(refs_tree / "knowledge" / "spec_fx.md", "Carries out `PRINCIPLES.md` §1.\n")
    code, out = run_refs(capsys)
    assert code == 1
    assert "knowledge/spec_fx.md: names no docs/ page" in out


def test_refs_spec_names_missing_docs_page(refs_tree, capsys):
    """@AC-knowledge_checks-21. A docs page a spec names must exist."""
    write(refs_tree / "knowledge" / "spec_fx.md",
          "Carries out `PRINCIPLES.md` §1. See `docs/fx_absent.md`.\n")
    code, out = run_refs(capsys)
    assert code == 1
    assert "knowledge/spec_fx.md: names docs/fx_absent.md, which doesn't exist" in out


# --- identifiers -------------------------------------------------------------------


@pytest.fixture
def id_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(ci, "ROOT", tmp_path)
    (tmp_path / "schemes").mkdir()
    return tmp_path


def run_ids(capsys) -> tuple[int, str]:
    code = ci.main()
    return code, capsys.readouterr().out


def test_identifiers_valid_pass(id_tree, capsys):
    """@AC-knowledge_checks-22. Valid scheme and label ids pass."""
    write(id_tree / "schemes" / "fx-a.yaml",
          "scheme: fx-a\nlabels:\n  - id: _stem-A1\n  - id: sfx_erg-1\n")
    write(id_tree / "schemes" / "fx-b.yaml", "scheme: fx_b\n")
    code, out = run_ids(capsys)
    assert code == 0
    assert "0 problem(s) in 2 file(s)" in out


def test_identifiers_display_fields_any_text(id_tree, capsys):
    """@AC-knowledge_checks-23. code and name may hold any text."""
    write(id_tree / "schemes" / "fx-a.yaml",
          "scheme: fx-a\nlabels:\n  - {id: fx-1, code: 'FX 1', name: 'Fixture one, (a)!'}\n")
    code, out = run_ids(capsys)
    assert code == 0, out


@pytest.mark.parametrize("body, shown", [
    ("scheme: 1fx\n", "'1fx'"),
    ("scheme: fx a\n", "'fx a'"),
    ("labels: []\n", "''"),
    ("", "''"),
])
def test_identifiers_bad_scheme(id_tree, capsys, body, shown):
    """@AC-knowledge_checks-24. An invalid or missing scheme id is reported."""
    write(id_tree / "schemes" / "fx-a.yaml", body)
    code, out = run_ids(capsys)
    assert code == 1
    assert f"[ERROR] schemes/fx-a.yaml: scheme {shown} is not a valid identifier" in out


def test_identifiers_bad_label(id_tree, capsys):
    """@AC-knowledge_checks-25. A label id with a space, or none, is reported by position."""
    write(id_tree / "schemes" / "fx-a.yaml",
          "scheme: fx-a\nlabels:\n  - id: fx-1\n  - id: fx 2\n  - code: FX3\n")
    code, out = run_ids(capsys)
    assert code == 1
    assert "schemes/fx-a.yaml: label 1 id 'fx 2' is not a valid identifier" in out
    assert "schemes/fx-a.yaml: label 2 id '' is not a valid identifier" in out


def test_identifiers_duplicate_label(id_tree, capsys):
    """@AC-knowledge_checks-26. A label id used twice is reported."""
    write(id_tree / "schemes" / "fx-a.yaml",
          "scheme: fx-a\nlabels:\n  - id: fx-1\n  - id: fx-2\n  - id: fx-1\n")
    code, out = run_ids(capsys)
    assert code == 1
    assert "schemes/fx-a.yaml: duplicate id 'fx-1'" in out
    assert "1 problem(s) in 1 file(s)" in out


# --- malformed input ----------------------------------------------------------------


def test_frontmatter_that_isnt_a_mapping_is_reported(fm_tree, capsys):
    """@AC-knowledge_checks-27. A list or unreadable YAML as frontmatter is an error, not a crash."""
    write(fm_tree / "knowledge" / "fx_list.md", "---\n- a\n- b\n---\n\n# Fixture\n")
    write(fm_tree / "knowledge" / "fx_broken.md", "---\ntitle: [unclosed\n---\n\n# Fixture\n")
    write(fm_tree / "knowledge" / "fx_good.md", GOOD_FM)
    code, out = run_fm(capsys)
    assert code == 1
    assert "knowledge/fx_list.md: frontmatter isn't a mapping of keys" in out
    assert "knowledge/fx_broken.md: frontmatter isn't valid YAML" in out
    assert "2 problem(s) in 3 file(s)" in out


def test_identifiers_must_be_text(id_tree, capsys):
    """@AC-knowledge_checks-28. Empty ids and ids YAML reads as booleans are reported; no stays text."""
    write(id_tree / "schemes" / "fx-a.yaml", "scheme:\nlabels:\n  - id:\n  - id: true\n  - id: no\n")
    code, out = run_ids(capsys)
    assert code == 1
    assert "schemes/fx-a.yaml: scheme '' is not a valid identifier" in out
    assert "schemes/fx-a.yaml: label 0 id '' is not a valid identifier" in out
    assert "schemes/fx-a.yaml: label 1 id True is not a valid identifier" in out
    assert "label 2" not in out
    assert "3 problem(s) in 1 file(s)" in out


def test_a_scheme_file_laid_out_wrongly_is_reported(id_tree, capsys):
    """@AC-knowledge_checks-29. Each malformed scheme file is reported, and the rest still checked."""
    write(id_tree / "schemes" / "fx-a.yaml", "- scheme: fx-a\n")
    write(id_tree / "schemes" / "fx-b.yaml", "scheme: fx-b\nlabels:\n  - fx-1\n  - id: fx-2\n")
    write(id_tree / "schemes" / "fx-c.yaml", "scheme: fx-c\nscheme: fx-d\n")
    write(id_tree / "schemes" / "fx-d.yaml", "scheme: [fx-d\n")
    write(id_tree / "schemes" / "fx-e.yaml", "scheme: fx-e\n")
    code, out = run_ids(capsys)
    assert code == 1
    assert "schemes/fx-a.yaml: isn't a mapping of keys" in out
    assert "schemes/fx-b.yaml: label 0 isn't a mapping of keys" in out
    assert "[ERROR] schemes/fx-c.yaml:" in out
    assert "[ERROR] schemes/fx-d.yaml: not valid YAML" in out
    assert "fx-e" not in out.replace("in 5 file(s)", "")
    assert "4 problem(s) in 5 file(s)" in out


def test_refs_subfolders_are_checked(refs_tree, capsys):
    """@AC-knowledge_checks-30. A spec in a subfolder of knowledge/ must cite a section too."""
    write(refs_tree / "knowledge" / "fx_sub" / "spec_fx.md", "People read `docs/fx_page.md`.\n")
    code, out = run_refs(capsys)
    assert code == 1
    assert "knowledge/fx_sub/spec_fx.md: cites no PRINCIPLES.md section" in out


@pytest.mark.parametrize("labels", ["5", "fxab", "{fx-1: a}"])
def test_labels_that_arent_a_list_are_reported(id_tree, capsys, labels):
    """@AC-knowledge_checks-31. Labels must be a list; anything else is reported once."""
    write(id_tree / "schemes" / "fx-a.yaml", f"scheme: fx-a\nlabels: {labels}\n")
    write(id_tree / "schemes" / "fx-b.yaml", "scheme: fx b\n")
    code, out = run_ids(capsys)
    assert code == 1
    assert out.count("schemes/fx-a.yaml:") == 1
    assert "schemes/fx-a.yaml: labels must be a list" in out
    assert "schemes/fx-b.yaml: scheme 'fx b' is not a valid identifier" in out


def test_only_valid_ids_are_compared_for_duplicates(id_tree, capsys):
    """@AC-knowledge_checks-32. Missing and non-text ids are reported once each, never as duplicates."""
    write(id_tree / "schemes" / "fx-a.yaml",
          "scheme: fx-a\nlabels:\n  - code: FX1\n  - code: FX2\n  - id: [fx-3]\n  - id: [fx-3]\n")
    code, out = run_ids(capsys)
    assert code == 1
    assert "duplicate" not in out
    assert "label 2 id ['fx-3'] is not a valid identifier" in out
    assert "4 problem(s) in 1 file(s)" in out


@pytest.mark.parametrize("body, error", [
    ("type: [Spec]\ntitle: Fixture\ndescription: A fixture.\n", "type ['Spec'] not in the profile"),
    (BASE + "status: [draft]\n", "status must be draft, stable or deprecated"),
    (BASE + "tags: [[process]]\n", "tags must be a list of at most four profile tags"),
    (BASE + "verified: 5\n", "verified must be a list of {by, at}"),
    (BASE + "sources: 5\n", "sources must be a list of {resource, id?}"),
])
def test_frontmatter_values_of_the_wrong_shape_are_reported(fm_tree, capsys, body, error):
    """@AC-knowledge_checks-33. A list or number where text or a list belongs is an error, not a crash."""
    write(fm_tree / "knowledge" / "fx_a.md", with_fm(body))
    write(fm_tree / "knowledge" / "fx_b.md", GOOD_FM)
    code, out = run_fm(capsys)
    assert code == 1
    assert f"[ERROR] knowledge/fx_a.md: {error}" in out
    assert "in 2 file(s)" in out


def test_frontmatter_is_read_strictly(fm_tree, capsys):
    """@AC-knowledge_checks-34. A key given twice is reported, not settled by keeping one."""
    write(fm_tree / "knowledge" / "fx_a.md", with_fm(BASE + "type: Decision\n"))
    code, out = run_fm(capsys)
    assert code == 1
    assert "knowledge/fx_a.md: frontmatter can't be read (line 4: duplicate key 'type')" in out
