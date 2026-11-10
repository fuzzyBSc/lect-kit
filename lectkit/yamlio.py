"""Reading YAML data files without the surprises YAML 1.1 allows.

- A mapping that repeats a key is an error. Otherwise the last value silently wins, and a
  file can hide one of its own values.
- Only `true` and `false` are booleans. Words such as `yes`, `no`, `on` and `off` stay
  text: in a language's data they may be words.
- Dates and times stay text.
"""
from __future__ import annotations

import functools
import re

import yaml

# libyaml's parser when this PyYAML has it: the same YAML, about ten times faster. The
# resolvers and constructors below are Python either way, so what a file means is the same.
_BASE = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class YamlError(ValueError):
    pass


class DataLoader(_BASE):
    pass


# Rebuild the implicit resolvers without the YAML 1.1 bool words and timestamps.
DataLoader.yaml_implicit_resolvers = {
    ch: [(tag, rx) for tag, rx in rs if tag not in ("tag:yaml.org,2002:bool",
                                                       "tag:yaml.org,2002:timestamp")]
    for ch, rs in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
DataLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"))


def _mapping(loader: DataLoader, node: yaml.MappingNode, deep: bool = False):
    loader.flatten_mapping(node)
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            dup = key in seen
        except TypeError:
            raise YamlError(f"line {key_node.start_mark.line + 1}: a mapping key must be text "
                            f"or a number")
        if dup:
            raise YamlError(f"line {key_node.start_mark.line + 1}: duplicate key {key!r}")
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


DataLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load(text: str):
    try:
        return yaml.load(text, Loader=DataLoader)
    except yaml.YAMLError as e:
        raise YamlError(f"not valid YAML: {e.__class__.__name__}") from e


def load_file(path) -> object:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as e:
        raise YamlError(f"{path.name}: not UTF-8 text") from e
    return load(text)


SKIP_TAGS = {"tag:yaml.org,2002:null"}
ID_KEY = "id"


@functools.lru_cache(maxsize=64)
def _compose(text: str):
    """The node tree of one document. Cached by text, since a build reads each file's tree
    more than once; callers only read the tree."""
    try:
        return yaml.compose(text, Loader=DataLoader)
    except yaml.composer.ComposerError as e:
        if "single document" in str(e):
            raise YamlError("holds more than one YAML document") from e
        raise YamlError(f"not valid YAML: {e.__class__.__name__}") from e
    except yaml.YAMLError as e:
        raise YamlError(f"not valid YAML: {e.__class__.__name__}") from e


def source_items(text: str):
    """(line, kind, text, path) for every mapping key and scalar, as written in the file.

    `kind` is "key" or "scalar"; nulls are left out. `path` uses the same steps as
    lectkit.layers (mapping keys, ("id", value) for a list item with an id, ("#", index)
    otherwise), as text, so a composed value can be traced to the line that wrote it.
    An alias reuses content already written at its anchor, so that content is reported
    once, at the anchor's line, and not again at each alias (a recursive alias can't loop).
    Raises YamlError on anything that isn't one valid YAML document."""
    root = _compose(text)
    out = []
    seen: set[int] = set()

    def walk(node, path):
        if id(node) in seen:
            return              # an alias: its content is recorded once, at its anchor's line
        seen.add(id(node))
        if isinstance(node, yaml.MappingNode):
            for k, v in node.value:
                if not isinstance(k, yaml.ScalarNode):
                    raise YamlError(f"line {k.start_mark.line + 1}: a mapping key must be text "
                                    f"or a number")
                out.append((k.start_mark.line + 1, "key", k.value, path + (k.value,)))
                walk(v, path + (k.value,))
        elif isinstance(node, yaml.SequenceNode):
            for i, v in enumerate(node.value):
                step = ("#", i)
                if isinstance(v, yaml.MappingNode):
                    for k, x in v.value:
                        if isinstance(k, yaml.ScalarNode) and k.value == ID_KEY \
                                and isinstance(x, yaml.ScalarNode):
                            step = ("id", x.value)
                walk(v, path + (step,))
        elif isinstance(node, yaml.ScalarNode) and node.tag not in SKIP_TAGS:
            out.append((node.start_mark.line + 1, "scalar", node.value, path))

    if root is not None:
        walk(root, ())
    return out


def comments(text: str):
    """(line, text) for every comment, read outside the spans of scalars, so a `#` inside
    a quoted or block scalar is never taken for one."""
    root = _compose(text)
    spans = []

    def walk(node):
        if isinstance(node, yaml.ScalarNode):
            spans.append((node.start_mark.index, node.end_mark.index))
        elif isinstance(node, yaml.MappingNode):
            for k, v in node.value:
                walk(k)
                walk(v)
        elif isinstance(node, yaml.SequenceNode):
            for v in node.value:
                walk(v)

    if root is not None:
        walk(root)
    masked = list(text)
    for a, b in spans:
        for i in range(a, min(b, len(masked))):
            if masked[i] != "\n":
                masked[i] = " "
    out = []
    pos = 0
    for n, line in enumerate("".join(masked).split("\n"), 1):
        j = line.find("#")
        while j != -1 and j > 0 and not line[j - 1].isspace():
            j = line.find("#", j + 1)
        if j != -1:
            body = text[pos + j + 1: pos + len(line)].rstrip("\r")
            if body.strip():
                out.append((n, body))
        pos += len(line) + 1
    return out
