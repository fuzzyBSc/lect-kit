"""Layered files: one file per tier at the same path, composed for one audience.

Carries out knowledge/spec_classification.md, "Layered files". Location decides the tier,
the register decides the order, and a higher layer only adds. The merge rule is the same
for every format.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from lectkit.tiers import Register

if TYPE_CHECKING:
    from lectkit.formats import Schema

ID = "id"
REPLACES = "replaces"

Path_ = tuple  # steps: a mapping key (str), ("id", value) or ("#", index)


class LayerError(ValueError):
    pass


def where(path: Path_) -> str:
    out = []
    for s in path:
        if isinstance(s, tuple):
            out.append(f"[{s[1]}]" if s[0] == "id" else f"[#{s[1]}]")
        else:
            out.append(str(s))
    return "/".join(out) or "<root>"


@dataclass
class Composed:
    doc: Any
    origin: dict[Path_, str] = field(default_factory=dict)

    def tier_of(self, path: Path_) -> str:
        """The tier that added the value at `path`: the nearest marked ancestor's."""
        for n in range(len(path), -1, -1):
            t = self.origin.get(tuple(path[:n]))
            if t is not None:
                return t
        raise LayerError(f"{where(path)}: no tier recorded")


def order(reg: Register, audience: str) -> list[str]:
    """The tiers an audience reads, each after every tier it sees."""
    if audience not in reg.tiers:
        raise LayerError(f"unknown tier {audience!r}")
    readable = [audience, *reg.tiers[audience].sees]
    rank = {t: i for i, t in enumerate(reg.tiers)}
    return sorted(readable, key=lambda t: (len(reg.tiers[t].sees), rank[t]))


def _key(schema: "Schema | None", path: Path_) -> str | None:
    """The field identifying records in the list at `path`: `id` with no schema, else the
    schema's identifier for that list, or None (the list stacks by value)."""
    if schema is None:
        return ID
    return schema.key_for(tuple(s for s in path if isinstance(s, str)))


def _olds(item: dict, path: Path_) -> list:
    olds = item.get(REPLACES, [])
    olds = olds if isinstance(olds, list) else [olds]
    for o in olds:
        if isinstance(o, bool) or not isinstance(o, (str, int)):
            raise LayerError(f"{where(path)}: {REPLACES} holds ids, as strings or integers")
    return olds


def _check_replaces(items: list, path: Path_, key: str) -> None:
    """No old id is still in use in the list, and none is claimed by two records."""
    live = {x[key] for x in items if isinstance(x, dict) and isinstance(x.get(key), (str, int))}
    claimed: set = set()
    for x in items:
        if isinstance(x, dict) and REPLACES in x:
            for o in _olds(x, path):
                if o in live:
                    raise LayerError(f"{where(path)}: {o!r} is listed under {REPLACES} but is "
                                     f"still in use")
                if o in claimed:
                    raise LayerError(f"{where(path)}: {o!r} is replaced by two records")
                claimed.add(o)


def _check_ids(node: Any, path: Path_, schema: "Schema | None" = None) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            _check_ids(v, path + (k,), schema)
    elif isinstance(node, list):
        key = _key(schema, path)
        seen: set = set()
        if key is not None:
            _check_replaces(node, path, key)
        for i, item in enumerate(node):
            if key is not None and isinstance(item, dict) and key in item:
                v = item[key]
                if isinstance(v, bool) or not isinstance(v, (str, int)):
                    raise LayerError(f"{where(path)}: an {key} must be a string or an integer")
                if v in seen:
                    raise LayerError(f"{where(path)}: duplicate {key} {v!r}")
                seen.add(v)
                _check_ids(item, path + (("id", v),), schema)
            else:
                if schema is not None and key is not None and isinstance(item, dict):
                    raise LayerError(f"{where(path)}: record #{i} has no {key}, which its "
                                     f"schema {schema.name!r} identifies it by")
                _check_ids(item, path + (("#", i),), schema)


def _same(a: Any, b: Any) -> bool:
    return type(a) is type(b) and a == b


def _merge(lower: Any, upper: Any, path: Path_, tier: str, origin: dict,
           schema: "Schema | None" = None) -> None:
    for k, v in upper.items():
        if k == REPLACES and path and isinstance(path[-1], tuple) and path[-1][0] == "id":
            raise LayerError(f"{where(path)}: a {tier} layer can't add {REPLACES} to a record "
                             f"a lower layer holds")
        if k not in lower:
            lower[k] = copy.deepcopy(v)
            origin[path + (k,)] = tier
        elif isinstance(lower[k], dict) and isinstance(v, dict):
            _merge(lower[k], v, path + (k,), tier, origin, schema)
        elif isinstance(lower[k], list) and isinstance(v, list):
            _merge_list(lower[k], v, path + (k,), tier, origin, schema)
        elif not _same(lower[k], v):
            raise LayerError(f"{where(path + (k,))}: a {tier} layer can't change a value "
                             f"a lower layer holds")


def _merge_list(lower: list, upper: list, path: Path_, tier: str, origin: dict,
                schema: "Schema | None" = None) -> None:
    key = _key(schema, path)
    by_id = {x[key]: x for x in lower if key and isinstance(x, dict) and key in x}
    renamed = {o: x for x in lower if key and isinstance(x, dict) for o in _olds(x, path)}
    for item in upper:
        if key and isinstance(item, dict) and key in item:
            i = item[key]
            target = by_id.get(i) or renamed.get(i)
            if target is not None:
                _merge(target, {k: v for k, v in item.items() if k != key},
                       path + (("id", target[key]),), tier, origin, schema)
            else:
                lower.append(copy.deepcopy(item))
                by_id[i] = lower[-1]
                origin[path + (("id", i),)] = tier
        elif not any(_same(item, x) for x in lower):
            lower.append(item)
            origin[path + (("#", len(lower) - 1),)] = tier


def compose(layers: dict[str, Any], audience: str, reg: Register,
            schema: "Schema | None" = None) -> Composed:
    """Compose one file for `audience` from {tier: document} for the tiers that hold it.

    With a schema, records in each list join on the field the schema names for it, and a
    list it gives no identifier stacks by value. Without one, records join on `id`."""
    tiers_in_order = order(reg, audience)
    unreadable = set(layers) - set(tiers_in_order)
    if unreadable:
        raise LayerError(f"layers from {', '.join(sorted(unreadable))} aren't readable by "
                         f"{audience!r}")
    out = Composed(doc=None)
    for t in tiers_in_order:
        if t not in layers:
            continue
        d = layers[t]
        _check_ids(d, (), schema)
        if out.doc is None:
            out.doc = copy.deepcopy(d)
            out.origin[()] = t
        elif isinstance(out.doc, dict) and isinstance(d, dict):
            _merge(out.doc, d, (), t, out.origin, schema)
        elif isinstance(out.doc, list) and isinstance(d, list):
            _merge_list(out.doc, d, (), t, out.origin, schema)
        elif not _same(out.doc, d):
            raise LayerError(f"the {t} layer isn't in the same form as the layers below it")
    if isinstance(out.doc, (dict, list)):
        _check_ids(out.doc, (), schema)   # the composed result obeys the same rules as each layer
    return out
