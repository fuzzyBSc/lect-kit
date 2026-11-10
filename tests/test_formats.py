"""Tests for lectkit.formats and schema-driven composing, on abstract fixtures only (lect id fx)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lectkit import formats, layers, tiers  # noqa: E402

FX_TIERS = """\
register: 1
tiers:
  - {id: fx-open, name: Open, sees: [], store: {path: stores/fx-open, remote: allowed}}
  - {id: fx-a, name: A, sees: [fx-open], store: {path: stores/fx-a, remote: allowed}}
"""
FX_LEXICON = {"format": "fx-lexicon", "files": ["lexicon/*.yaml"],
              "lists": {"entries": {"key": "lexeme_id"}, "entries/senses": {}}}
REL = "lexicon/fx-nouns.yaml"


@pytest.fixture
def reg(tmp_path):
    p = tmp_path / "fx-tiers.yaml"
    p.write_text(FX_TIERS, encoding="utf-8")
    r = tiers.load(p)
    assert r.problems == []
    return r


@pytest.fixture
def schema():
    return formats.parse(FX_LEXICON, "fx-lexicon.yaml")


def test_schema_identifier_joins_records(reg, schema):
    """@AC-formats-1"""
    lo = {"entries": [{"lexeme_id": "stemA", "senses": ["glossA1"]}]}
    hi = {"entries": [{"lexeme_id": "stemA", "senses": ["glossA2"]}]}
    c = layers.compose({"fx-open": lo, "fx-a": hi}, "fx-a", reg, schema)
    assert c.doc["entries"] == [{"lexeme_id": "stemA", "senses": ["glossA1", "glossA2"]}]
    added = [p for p, t in c.origin.items() if t == "fx-a"]
    assert added == [("entries", ("id", "stemA"), "senses", ("#", 1))]
    assert c.tier_of(("entries", ("id", "stemA"))) == "fx-open"


def test_unidentified_list_stacks_by_value(reg, schema):
    """@AC-formats-2"""
    lo = {"entries": [{"lexeme_id": "stemA", "senses": ["glossA1", "glossA3"]}]}
    hi = {"entries": [{"lexeme_id": "stemA", "senses": ["glossA3", "glossA2"]}]}
    c = layers.compose({"fx-open": lo, "fx-a": hi}, "fx-a", reg, schema)
    assert c.doc["entries"][0]["senses"] == ["glossA1", "glossA3", "glossA2"]


@pytest.mark.parametrize("doc", [
    {"entries": [{"senses": []}]},
    {"entries": [{"lexeme_id": "stemA"}, {"lexeme_id": "stemA"}]},
])
def test_identifier_required_and_unique(reg, schema, doc):
    """@AC-formats-3"""
    with pytest.raises(layers.LayerError, match="entries.*lexeme_id"):
        layers.compose({"fx-open": doc}, "fx-open", reg, schema)


def test_id_is_ordinary_under_schema(reg, schema):
    """@AC-formats-4"""
    lo = {"entries": [{"lexeme_id": "stemA", "id": 1}, {"lexeme_id": "stemB", "id": 1}]}
    hi = {"entries": [{"lexeme_id": "stemB", "senses": ["glossB1"]}]}
    c = layers.compose({"fx-open": lo, "fx-a": hi}, "fx-a", reg, schema)
    assert c.doc["entries"][1] == {"lexeme_id": "stemB", "id": 1, "senses": ["glossB1"]}


@pytest.mark.parametrize("doc", [
    {"lists": {"entries": {"key": "lexeme_id"}}},
    {"format": "fx", "lists": {1: {"key": "lexeme_id"}}},
    {"format": "fx", "lists": {"entries//x": {}}},
    {"format": "fx", "lists": {"entries": {"key": "lexeme id"}}},
    {"format": "fx", "lists": ["entries"]},
])
def test_malformed_schema(doc):
    """@AC-formats-5"""
    with pytest.raises(formats.FormatError, match="fx-bad.yaml"):
        formats.parse(doc, "fx-bad.yaml")


def test_schema_dir_and_patterns(tmp_path):
    """@AC-formats-5 @AC-formats-1"""
    (tmp_path / "a.yaml").write_text(yaml.safe_dump(FX_LEXICON), encoding="utf-8")
    (tmp_path / "b.yaml").write_text(
        yaml.safe_dump({"format": "fx-slots", "lists": {"*_slots": "name"}}), encoding="utf-8")
    s = formats.load_schemas(tmp_path)
    assert s["fx-slots"].key_for(("noun_slots",)) == "name"
    assert s["fx-slots"].key_for(("other",)) is None
    (tmp_path / "c.yaml").write_text(yaml.safe_dump(FX_LEXICON), encoding="utf-8")
    with pytest.raises(formats.FormatError, match="defined twice"):
        formats.load_schemas(tmp_path)


def test_kit_schemas_load():
    """@AC-formats-5"""
    s = formats.load_schemas()
    assert s and all(isinstance(v, formats.Schema) for v in s.values())


def test_project_map_is_layered(reg, schema):
    """@AC-formats-6"""
    lo = {"files": [{"path": REL, "format": "fx-lexicon"}]}
    hi = {"files": [{"path": "lexicon/fx-extra.yaml", "format": "fx-lexicon"}]}
    m = layers.compose({"fx-open": lo, "fx-a": hi}, "fx-a", reg, formats.MAP_SCHEMA).doc
    got = formats.resolve_map(m, {"fx-lexicon": schema})
    assert set(got) == {REL, "lexicon/fx-extra.yaml"}
    bad = {"files": [{"path": REL, "format": "fx-other"}]}
    with pytest.raises(layers.LayerError):
        layers.compose({"fx-open": lo, "fx-a": bad}, "fx-a", reg, formats.MAP_SCHEMA)


@pytest.mark.parametrize("doc,msg", [
    ({"files": [{"path": REL, "format": "fx-none"}]}, "no format 'fx-none'"),
    ({"files": [{"path": REL}]}, "path and a format"),
    ({"files": "x"}, "files list"),
])
def test_map_names_known_formats(schema, doc, msg):
    """@AC-formats-7"""
    with pytest.raises(formats.FormatError, match=msg):
        formats.resolve_map(doc, {"fx-lexicon": schema})
    assert formats.resolve_map(None, {}) == {}


def _stores(tmp_path, with_map=True):
    (tmp_path / "fx-tiers.yaml").write_text(FX_TIERS, encoding="utf-8")
    for t, doc in [("fx-open", {"entries": [{"lexeme_id": "stemA", "senses": ["glossA1"]}]}),
                   ("fx-a", {"entries": [{"lexeme_id": "stemA", "senses": ["glossA2"]}]})]:
        f = tmp_path / "stores" / t / REL
        f.parent.mkdir(parents=True)
        f.write_text(yaml.safe_dump(doc), encoding="utf-8")
    sd = tmp_path / "schemas"
    sd.mkdir()
    (sd / "fx-lexicon.yaml").write_text(yaml.safe_dump(FX_LEXICON), encoding="utf-8")
    if with_map:
        m = tmp_path / "stores" / "fx-open" / formats.MAP_REL
        m.parent.mkdir(parents=True)
        m.write_text(yaml.safe_dump({"files": [{"path": REL, "format": "fx-lexicon"}]}),
                     encoding="utf-8")
    return sd


def test_cli_uses_mapped_format(tmp_path, capsys):
    """@AC-formats-8"""
    import compose_layers
    sd = _stores(tmp_path)
    out = tmp_path / "out.yaml"
    rc = compose_layers.main(["--register", str(tmp_path / "fx-tiers.yaml"), "--audience",
                              "fx-a", "--rel", REL, "--out", str(out), "--schemas", str(sd)])
    assert rc == 0
    assert yaml.safe_load(out.read_text(encoding="utf-8"))["entries"] == [
        {"lexeme_id": "stemA", "senses": ["glossA1", "glossA2"]}]


def test_cli_refuses_unclaimed_file(tmp_path, capsys):
    """@AC-formats-8"""
    import compose_layers
    sd = _stores(tmp_path, with_map=False)
    f = tmp_path / "stores" / "fx-open" / "other" / "x.yaml"
    f.parent.mkdir(parents=True)
    f.write_text("a: 1\n", encoding="utf-8")
    rc = compose_layers.main(["--register", str(tmp_path / "fx-tiers.yaml"), "--audience",
                              "fx-a", "--rel", "other/x.yaml", "--schemas", str(sd)])
    assert rc == 1
    assert "no format claims it" in capsys.readouterr().err
    rc = compose_layers.main(["--register", str(tmp_path / "fx-tiers.yaml"), "--audience",
                              "fx-a", "--rel", REL, "--schemas", str(sd)])
    assert rc == 0


def test_kit_pattern_claims_file(schema):
    """@AC-formats-9"""
    assert formats.format_for(REL, {"fx-lexicon": schema}) is schema
    assert formats.format_for("lexicon\\fx-nouns.yaml", {"fx-lexicon": schema}) is schema
    assert formats.format_for("other/x.yaml", {"fx-lexicon": schema}) is None


def test_project_cant_remap_kit_file(schema):
    """@AC-formats-10"""
    other = formats.Schema("fx-other", {})
    sch = {"fx-lexicon": schema, "fx-other": other}
    with pytest.raises(formats.FormatError, match="fx-other.*fx-lexicon"):
        formats.format_for(REL, sch, {REL: other})
    assert formats.format_for(REL, sch, {REL: schema}) is schema
    assert formats.format_for("other/x.yaml", sch, {"other/x.yaml": other}) is other


def test_two_patterns_cant_claim_one_file(schema):
    """@AC-formats-11"""
    twin = formats.Schema("fx-twin", {}, ("lexicon/fx-*.yaml",))
    with pytest.raises(formats.FormatError, match="fx-lexicon, fx-twin"):
        formats.format_for(REL, {"fx-lexicon": schema, "fx-twin": twin})


@pytest.mark.parametrize("files", ["lexicon/*.yaml", ["/abs.yaml"], ["../up.yaml"], [""]])
def test_bad_file_patterns(files):
    """@AC-formats-5"""
    with pytest.raises(formats.FormatError, match="files"):
        formats.parse({"format": "fx", "files": files}, "fx.yaml")


def test_layout(tmp_path):
    """@AC-formats-12"""
    dirs = formats.load_layout()
    assert {"paradigm", "knowledge", "renderings"} <= {d["path"] for d in dirs}
    assert "paradigm" in formats.formatted_dirs() and "knowledge" not in formats.formatted_dirs()
    bad = tmp_path / "layout.yaml"
    bad.write_text("directories: [{holds: x}]\n", encoding="utf-8")
    with pytest.raises(formats.FormatError, match="path"):
        formats.load_layout(bad)


def test_check_formats(tmp_path, capsys):
    """@AC-formats-13"""
    import check_formats
    sd = tmp_path / "schemas"
    sd.mkdir()
    (sd / "fx.yaml").write_text(yaml.safe_dump(
        {"format": "fx-lexicon", "files": ["paradigm/lexicon-*.yaml"]}), encoding="utf-8")
    st = tmp_path / "store"
    for rel in ["paradigm/lexicon-a.yaml", "paradigm/mapped.yaml", "paradigm/loose.yaml"]:
        (st / rel).parent.mkdir(parents=True, exist_ok=True)
        (st / rel).write_text("x: 1\n", encoding="utf-8")
    (st / ".lectkit").mkdir()
    (st / formats.MAP_REL).write_text(yaml.safe_dump(
        {"files": [{"path": "paradigm/mapped.yaml", "format": "fx-lexicon"}]}), encoding="utf-8")
    assert check_formats.main(["--store", str(st), "--schemas", str(sd)]) == 1
    out = capsys.readouterr().out
    assert "paradigm/loose.yaml" in out and "lexicon-a" not in out and "mapped.yaml:" not in out
    (st / "paradigm/loose.yaml").unlink()
    assert check_formats.main(["--store", str(st), "--schemas", str(sd)]) == 0
