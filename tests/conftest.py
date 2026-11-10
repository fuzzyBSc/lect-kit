"""Shared test setup.

Fixture stores use made-up formats. The kit's real schemas declare field names such as
`senses` and `gloss` as format words (lectkit/format_words.py), which would quietly
change what the older scan tests measure. So every test runs against an empty schema
folder unless it asks for the real one with the `kit_schemas` fixture.
"""
import pytest

from lectkit import format_words, shared_lists


@pytest.fixture(autouse=True)
def _no_kit_schemas(tmp_path_factory, monkeypatch, request):
    if "kit_schemas" in request.fixturenames:
        return
    monkeypatch.setattr(format_words, "SCHEMA_DIR", tmp_path_factory.mktemp("no-schemas"))
    monkeypatch.setattr(shared_lists, "LIST_DIR", tmp_path_factory.mktemp("no-lists"))


@pytest.fixture
def kit_schemas():
    return format_words.SCHEMA_DIR


def grant_yaml(rows, by=None, at=None):
    """Grant-file text from (text, to, reason) rows; the reason is the commit's, not the file's."""
    from lectkit import grants
    doc = {}
    for text, to, _reason in rows:
        doc.setdefault(to, []).append(text)
    return grants.dump(doc)


def review_yaml(rows, reason=None, by=None, at=None):
    """Review-file text from row mappings that carry their lower tier as `tier`."""
    from lectkit import grants
    doc = {}
    for r in rows:
        r = dict(r)
        doc.setdefault(r.pop("tier"), []).append(r)
    return grants.dump(doc)
