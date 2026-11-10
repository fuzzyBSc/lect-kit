"""Tests for lectkit.screening_scope, on abstract fixtures only (lect id fx)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lectkit import screening_scope, tiers  # noqa: E402

TERMS = "knowledge/fx-terms.yaml"


def check(files: dict[str, str], excluded=lambda rel: False) -> list[str]:
    return screening_scope.problems(list(files), files.__getitem__, {TERMS}, excluded)


def test_a_screening_only_tier_holds_no_prose():
    """@AC-cross_tier_scan-33. Comments, prose fields and notes are refused; matching data passes."""
    clean = {TERMS: "entries:\n- id: fxq\n  variants: [fxq]\n  pattern: fxq\n",
             "paradigm/fx.yaml": "words:\n- headword: fxq\n  gloss: hiddenqz\n",
             ".lectkit/accepted_matches.yaml": "# kit files are not checked\nfx-open: [x]\n",
             "README.md": "excluded by the tier\n"}
    assert check(clean, lambda rel: rel == "README.md") == []
    bad = check({TERMS: "entries:\n- id: fxq\n  variants: [fxq]\n  note: hiddenqz prose\n",
                 "paradigm/fx.yaml": "# hiddenqz ruling prose\nwords: []\n",
                 "knowledge/notes.md": "hiddenqz\n"})
    assert len(bad) == 3
    assert not any("hiddenqz" in p for p in bad)          # problems name places, never text


def test_the_register_marks_a_tier_screening_only(tmp_path):
    """@AC-cross_tier_scan-33. scope: screening in the register, and nothing else, sets it."""
    f = tmp_path / "fx-tiers.yaml"
    f.write_text("register: 1\ntiers:\n"
                 "  - {id: fx-open, name: Open, sees: [], store: {path: s/o, remote: allowed}}\n"
                 "  - {id: fx-c, name: C, sees: [fx-open], scope: screening,"
                 " store: {path: s/c, remote: none}}\n", encoding="utf-8")
    reg = tiers.load(f)
    assert reg.problems == [] and reg.tiers["fx-c"].screening_only
    assert not reg.tiers["fx-open"].screening_only
