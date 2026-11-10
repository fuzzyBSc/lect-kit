"""The fast C parser reads a file exactly as the pure-Python one does (lectkit/yamlio.py).

The scan places every value by its line and every comment by its character span, so the
two parsers must agree on values, start lines and scalar spans, not only on data."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lectkit import yamlio  # noqa: E402

TEXT = """\
# head comment
fx: &a {k: "has # inside", n: 3}
again: *a
words: [yes, no, on, off, true, 2026-11-10]
block: |
  line one # not a comment
  line two
quoted: 'it''s'
list:
  - id: fxq   # trailing comment
    v: ~
  - plain
"""


class Pure(yaml.SafeLoader):
    pass


Pure.yaml_implicit_resolvers = yamlio.DataLoader.yaml_implicit_resolvers
Pure.yaml_constructors = dict(yamlio.DataLoader.yaml_constructors)


def _sig(n):
    if isinstance(n, yaml.ScalarNode):
        return (n.tag, n.start_mark.line, n.start_mark.index, n.end_mark.index, n.value)
    kids = [x for kv in n.value for x in kv] if isinstance(n, yaml.MappingNode) else n.value
    return (n.tag, n.start_mark.line, n.start_mark.index, tuple(_sig(k) for k in kids))


@pytest.mark.skipif(not getattr(yaml, "__with_libyaml__", False), reason="no libyaml here")
def test_the_c_parser_reads_a_file_as_the_pure_parser_does():
    assert issubclass(yamlio.DataLoader, yaml.CSafeLoader)
    assert yaml.load(TEXT, Loader=yamlio.DataLoader) == yaml.load(TEXT, Loader=Pure)
    assert _sig(yaml.compose(TEXT, Loader=yamlio.DataLoader)) == _sig(yaml.compose(TEXT, Loader=Pure))


def test_the_yaml_rules_hold_under_the_fast_parser():
    d = yamlio.load(TEXT)
    assert d["words"] == ["yes", "no", "on", "off", True, "2026-11-10"]
    with pytest.raises(yamlio.YamlError):
        yamlio.load("a: 1\na: 2\n")
    assert [ln for ln, _ in yamlio.comments(TEXT)] == [1, 10]
