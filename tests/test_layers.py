"""Tests for lectkit.layers, on abstract fixtures only (lect id fx)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lectkit import layers, tiers  # noqa: E402

FX_TIERS = """\
register: 1
tiers:
  - {id: fx-open, name: Open, sees: [], store: {path: stores/fx-open, remote: allowed}}
  - {id: fx-a, name: A, sees: [fx-open], store: {path: stores/fx-a, remote: allowed}}
  - {id: fx-c, name: C, sees: [fx-open, fx-a], store: {path: stores/fx-c, remote: none}}
  - {id: fx-p, name: P, sees: [fx-open], store: {path: stores/fx-p, remote: none}}
  - {id: fx-q, name: Q, sees: [fx-open], store: {path: stores/fx-q, remote: none}}
"""
REL = "lexicon/fx-nouns.yaml"

OPEN = {"lect": "fx", "entries": [
    {"id": "stemA", "pos": "noun", "variants": ["stemA"],
     "senses": [{"id": "stemA-s1", "gloss": "glossA1"}]},
    {"id": "stemD", "pos": "noun", "senses": []},
]}
TIER_A = {"entries": [
    {"id": "stemA", "variants": ["stemAx"], "senses": [{"id": "stemA-s2", "gloss": "glossA2"}]},
    {"id": "stemB", "pos": "noun", "senses": [{"id": "stemB-s1", "gloss": "glossB1"}]},
]}
TIER_C = {"entries": [
    {"id": "stemB", "senses": [{"id": "stemB-s2", "gloss": "glossB2"}]},
]}
TIER_P = {"entries": [
    {"id": "stemA", "senses": [{"id": "stemA-s3", "gloss": "glossA3"}]},
]}


@pytest.fixture
def reg(tmp_path):
    p = tmp_path / "fx-tiers.yaml"
    p.write_text(FX_TIERS, encoding="utf-8")
    r = tiers.load(p)
    assert r.problems == []
    return r


def sense_ids(doc):
    return sorted(s["id"] for e in doc["entries"] for s in e["senses"])


def test_order_follows_sees(reg):
    assert layers.order(reg, "fx-c") == ["fx-open", "fx-a", "fx-c"]
    assert layers.order(reg, "fx-p") == ["fx-open", "fx-p"]


@pytest.mark.parametrize("audience, held, expect", [
    ("fx-open", ["fx-open"], ["stemA-s1"]),
    ("fx-a", ["fx-open", "fx-a"], ["stemA-s1", "stemA-s2", "stemB-s1"]),
    ("fx-c", ["fx-open", "fx-a", "fx-c"], ["stemA-s1", "stemA-s2", "stemB-s1", "stemB-s2"]),
    ("fx-p", ["fx-open", "fx-p"], ["stemA-s1", "stemA-s3"]),
])
def test_compose_per_audience(reg, audience, held, expect):
    all_layers = {"fx-open": OPEN, "fx-a": TIER_A, "fx-c": TIER_C, "fx-p": TIER_P}
    got = layers.compose({t: all_layers[t] for t in held}, audience, reg)
    assert sense_ids(got.doc) == expect


def test_location_decides_the_tier(reg):
    got = layers.compose({"fx-open": OPEN, "fx-a": TIER_A, "fx-c": TIER_C}, "fx-c", reg)
    e = ("entries",)
    assert got.tier_of(e + (("id", "stemA"),)) == "fx-open"
    assert got.tier_of(e + (("id", "stemA"), "senses", ("id", "stemA-s1"))) == "fx-open"
    assert got.tier_of(e + (("id", "stemA"), "senses", ("id", "stemA-s2"))) == "fx-a"
    assert got.tier_of(e + (("id", "stemB"),)) == "fx-a"
    assert got.tier_of(e + (("id", "stemB"), "senses", ("id", "stemB-s2"), "gloss")) == "fx-c"
    assert got.tier_of(e + (("id", "stemA"), "variants", ("#", 1))) == "fx-a"


def test_a_tier_field_is_not_read_as_the_tier(reg):
    forged = {"entries": [{"id": "stemA", "senses": [{"id": "stemA-s9", "tier": "fx-open"}]}]}
    got = layers.compose({"fx-open": OPEN, "fx-a": forged}, "fx-a", reg)
    assert got.tier_of(("entries", ("id", "stemA"), "senses", ("id", "stemA-s9"))) == "fx-a"


def test_input_order_doesnt_matter(reg):
    a = layers.compose({"fx-c": TIER_C, "fx-a": TIER_A, "fx-open": OPEN}, "fx-c", reg)
    b = layers.compose({"fx-open": OPEN, "fx-a": TIER_A, "fx-c": TIER_C}, "fx-c", reg)
    assert a.doc == b.doc


def test_lower_layer_is_untouched(reg):
    import copy
    before = copy.deepcopy(OPEN)
    layers.compose({"fx-open": OPEN, "fx-a": TIER_A}, "fx-a", reg)
    assert OPEN == before


def test_unreadable_layer_is_refused(reg):
    with pytest.raises(layers.LayerError, match="aren't readable"):
        layers.compose({"fx-open": OPEN, "fx-p": TIER_P}, "fx-q", reg)


@pytest.mark.parametrize("upper", [
    {"lect": "other"},                                         # changes a value
    {"entries": [{"id": "stemA", "pos": "verb"}]},             # changes a record's value
    {"entries": [{"id": "stemA", "senses": {"x": 1}}]},        # changes a value's form
    {"lect": 1},
])
def test_a_higher_layer_only_adds(reg, upper):
    with pytest.raises(layers.LayerError):
        layers.compose({"fx-open": OPEN, "fx-a": upper}, "fx-a", reg)


def test_restating_a_value_is_allowed(reg):
    got = layers.compose({"fx-open": OPEN, "fx-a": {"lect": "fx"}}, "fx-a", reg)
    assert got.doc["lect"] == "fx"


def test_bool_is_not_int(reg):
    with pytest.raises(layers.LayerError):
        layers.compose({"fx-open": {"n": 1}, "fx-a": {"n": True}}, "fx-a", reg)


def test_whole_file_form_must_match(reg):
    with pytest.raises(layers.LayerError, match="same form"):
        layers.compose({"fx-open": OPEN, "fx-a": [1, 2]}, "fx-a", reg)


@pytest.mark.parametrize("bad, msg", [
    ({"entries": [{"id": "x"}, {"id": "x"}]}, "duplicate"),
    ({"entries": [{"id": True}]}, "string or an integer"),
    ({"entries": [{"id": ["x"]}]}, "string or an integer"),
])
def test_ids_are_checked(reg, bad, msg):
    with pytest.raises(layers.LayerError, match=msg):
        layers.compose({"fx-open": bad}, "fx-open", reg)


def test_renamed_record_is_found_through_replaces(reg):
    base = {"entries": [{"id": "stemN", "replaces": ["stemOld"], "senses": []}]}
    upper = {"entries": [{"id": "stemOld", "senses": [{"id": "stemOld-s2", "gloss": "g"}]}]}
    got = layers.compose({"fx-open": base, "fx-a": upper}, "fx-a", reg)
    assert [e["id"] for e in got.doc["entries"]] == ["stemN"]
    assert sense_ids(got.doc) == ["stemOld-s2"]
    assert got.tier_of(("entries", ("id", "stemN"), "senses", ("id", "stemOld-s2"))) == "fx-a"


def test_an_old_id_replaced_twice_is_an_error(reg):
    base = {"entries": [{"id": "n1", "replaces": ["old"]}, {"id": "n2", "replaces": ["old"]}]}
    with pytest.raises(layers.LayerError, match="two records"):
        layers.compose({"fx-open": base, "fx-a": {"entries": [{"id": "old"}]}}, "fx-a", reg)


def test_plain_values_are_not_duplicated(reg):
    got = layers.compose({"fx-open": OPEN, "fx-a": {"entries": [{"id": "stemA",
                         "variants": ["stemA", "stemAy"]}]}}, "fx-a", reg)
    assert got.doc["entries"][0]["variants"] == ["stemA", "stemAy"]


def test_cli(tmp_path, capsys):
    import compose_layers as cli
    (tmp_path / "fx-tiers.yaml").write_text(FX_TIERS, encoding="utf-8")
    for t, d in {"fx-open": OPEN, "fx-a": TIER_A, "fx-c": TIER_C}.items():
        f = tmp_path / "stores" / t / REL
        f.parent.mkdir(parents=True)
        f.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")
    out = tmp_path / "fx-view.yaml"
    args = ["--register", str(tmp_path / "fx-tiers.yaml"), "--audience", "fx-c", "--rel", REL,
            "--out", str(out)]
    assert cli.main(args + ["--origin"]) == 0
    assert sense_ids(yaml.safe_load(out.read_text(encoding="utf-8"))) == [
        "stemA-s1", "stemA-s2", "stemB-s1", "stemB-s2"]
    assert "fx-c\tentries/[stemB]/senses/[stemB-s2]" in capsys.readouterr().err
    # An absent readable store makes the view incomplete, and says so.
    import shutil
    shutil.rmtree(tmp_path / "stores" / "fx-c")
    assert cli.main(args) == 2
    assert "[ABSENT] fx-c" in capsys.readouterr().err
    # --rel must stay inside the store.
    for rel in ("../fx-nouns.yaml", "/etc/fx.yaml", "a/../../x.yaml"):
        assert cli.main(["--register", str(tmp_path / "fx-tiers.yaml"), "--audience", "fx-a",
                         "--rel", rel]) == 1


# --- review findings ------------------------------------------------------------------

def test_a_higher_layer_cant_add_replaces_to_a_lower_record(reg):
    base = {"entries": [{"id": "x"}]}
    hijack = {"entries": [{"id": "x", "replaces": ["old"]}]}
    with pytest.raises(layers.LayerError, match="can't add replaces"):
        layers.compose({"fx-open": base, "fx-a": hijack}, "fx-a", reg)


@pytest.mark.parametrize("held", [["fx-open"], ["fx-open", "fx-a"]])
def test_replacing_an_id_still_in_use_is_an_error_in_any_layer(reg, held):
    docs = {"fx-open": {"entries": [{"id": "x"}, {"id": "n", "replaces": ["x"]}]},
            "fx-a": {"entries": []}}
    if held == ["fx-open", "fx-a"]:
        docs = {"fx-open": {"entries": [{"id": "x"}]},
                "fx-a": {"entries": [{"id": "n", "replaces": ["x"]}]}}
    with pytest.raises(layers.LayerError, match="still in use"):
        layers.compose({t: docs[t] for t in held}, held[-1], reg)


@pytest.mark.parametrize("value", [{"k": 1}, [["x"]], True])
def test_replaces_must_hold_ids(reg, value):
    with pytest.raises(layers.LayerError, match="holds ids"):
        layers.compose({"fx-open": {"entries": [{"id": "n", "replaces": value}]}}, "fx-open", reg)


def test_equal_root_scalars_and_lists(reg):
    assert layers.compose({"fx-open": "v", "fx-a": "v"}, "fx-a", reg).doc == "v"
    got = layers.compose({"fx-open": [{"id": "x"}], "fx-a": [{"id": "y"}]}, "fx-a", reg)
    assert got.doc == [{"id": "x"}, {"id": "y"}]
    assert got.tier_of((("id", "y"),)) == "fx-a"


def test_restated_mapping_without_id_isnt_duplicated(reg):
    got = layers.compose({"fx-open": {"notes": [{"k": 1}]}, "fx-a": {"notes": [{"k": 1}, {"k": 2}]}},
                         "fx-a", reg)
    assert got.doc["notes"] == [{"k": 1}, {"k": 2}]
    assert got.tier_of(("notes", ("#", 1))) == "fx-a"


def test_none_values(reg):
    assert layers.compose({"fx-open": {"a": None}, "fx-a": {"a": None}}, "fx-a", reg).doc == {"a": None}
    with pytest.raises(layers.LayerError):
        layers.compose({"fx-open": {"a": None}, "fx-a": {"a": "x"}}, "fx-a", reg)


def test_strict_yaml():
    from lectkit import yamlio
    assert yamlio.load("a: no\nb: on\nc: 2026-01-02\nd: true\n") == {
        "a": "no", "b": "on", "c": "2026-01-02", "d": True}
    with pytest.raises(yamlio.YamlError, match="duplicate key"):
        yamlio.load("a: 1\na: 2\n")
    with pytest.raises(yamlio.YamlError, match="not valid YAML"):
        yamlio.load("a: [1\n")


def test_cli_errors(tmp_path, capsys):
    import compose_layers as cli
    reg_file = tmp_path / "fx-tiers.yaml"
    reg_file.write_text(FX_TIERS, encoding="utf-8")
    f = tmp_path / "stores" / "fx-open" / REL
    f.parent.mkdir(parents=True)
    f.write_text("lect: fx\nlect: fy\n", encoding="utf-8")
    args = ["--register", str(reg_file), "--audience", "fx-open", "--rel", REL]
    assert cli.main(args) == 1
    cap = capsys.readouterr()
    assert "duplicate key" in cap.err and cap.out == ""     # errors never mix with the YAML
    f.write_bytes(b"\xff\xfe\x00bad")
    assert cli.main(args) == 1
    # Only an absent store would have held the file: an error, and it says which is absent.
    (tmp_path / "stores" / "fx-a").mkdir(parents=True)
    import shutil
    shutil.rmtree(tmp_path / "stores" / "fx-open")
    capsys.readouterr()
    assert cli.main(["--register", str(reg_file), "--audience", "fx-a", "--rel", REL]) == 1
    err = capsys.readouterr().err
    assert "[ABSENT] fx-open" in err and "no readable store holds" in err
