"""Reading YAML data files without the surprises YAML 1.1 allows.

- A mapping that repeats a key is an error. Otherwise the last value silently wins, and a
  file can hide one of its own values.
- Only `true` and `false` are booleans. Words such as `yes`, `no`, `on` and `off` stay
  text: in a language's data they may be words.
- Dates and times stay text.
"""
from __future__ import annotations

import re

import yaml


class YamlError(ValueError):
    pass


class DataLoader(yaml.SafeLoader):
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
