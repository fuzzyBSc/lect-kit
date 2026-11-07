"""Layered files: one file per tier at the same path, composed for one audience.

Carries out knowledge/spec_classification.md, "Layered files". Location decides the tier,
the register decides the order, and a higher layer only adds. The merge rule is the same
for every format.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from lectkit.tiers import Register

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


def _olds(item: dict, path: Path_) -> list:
    olds = item.get(REPLACES, [])
    olds = olds if isinstance(olds, list) else [olds]
    for o in olds:
        if isinstance(o, bool) or not isinstance(o, (str, int)):
            raise LayerError(f"{where(path)}: {REPLACES} holds ids, as strings or integers")
    return olds


def _check_replaces(items: list, path: Path_) -> None:
    """No old id is still in use in the list, and none is claimed by two records."""
    live = {x[ID] for x in items if isinstance(x, dict) and isinstance(x.get(ID), (str, int))}
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


def _check_ids(node: Any, path: Path_) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            _check_ids(v, path + (k,))
    elif isinstance(node, list):
        seen: set = set()
        _check_replaces(node, path)
        for i, item in enumerate(node):
            if isinstance(item, dict) and ID in item:
                v = item[ID]
                if isinstance(v, bool) or not isinstance(v, (str, int)):
                    raise LayerError(f"{where(path)}: an {ID} must be a string or an integer")
                if v in seen:
                    raise LayerError(f"{where(path)}: duplicate {ID} {v!r}")
                seen.add(v)
                _check_ids(item, path + (("id", v),))
            else:
                _check_ids(item, path + (("#", i),))


def _same(a: Any, b: Any) -> bool:
    return type(a) is type(b) and a == b


def _merge(lower: Any, upper: Any, path: Path_, tier: str, origin: dict) -> None:
    for k, v in upper.items():
        if k == REPLACES and path and isinstance(path[-1], tuple) and path[-1][0] == "id":
            raise LayerError(f"{where(path)}: a {tier} layer can't add {REPLACES} to a record "
                             f"a lower layer holds")
        if k not in lower:
            lower[k] = copy.deepcopy(v)
            origin[path + (k,)] = tier
        elif isinstance(lower[k], dict) and isinstance(v, dict):
            _merge(lower[k], v, path + (k,), tier, origin)
        elif isinstance(lower[k], list) and isinstance(v, list):
            _merge_list(lower[k], v, path + (k,), tier, origin)
        elif not _same(lower[k], v):
            raise LayerError(f"{where(path + (k,))}: a {tier} layer can't change a value "
                             f"a lower layer holds")


def _merge_list(lower: list, upper: list, path: Path_, tier: str, origin: dict) -> None:
    by_id = {x[ID]: x for x in lower if isinstance(x, dict) and ID in x}
    renamed = {o: x for x in lower if isinstance(x, dict) for o in _olds(x, path)}
    for item in upper:
        if isinstance(item, dict) and ID in item:
            i = item[ID]
            target = by_id.get(i) or renamed.get(i)
            if target is not None:
                _merge(target, {k: v for k, v in item.items() if k != ID}, path + (("id", target[ID]),),
                       tier, origin)
            else:
                lower.append(copy.deepcopy(item))
                by_id[i] = lower[-1]
                origin[path + (("id", i),)] = tier
        elif not any(_same(item, x) for x in lower):
            lower.append(item)
            origin[path + (("#", len(lower) - 1),)] = tier


def compose(layers: dict[str, Any], audience: str, reg: Register) -> Composed:
    """Compose one file for `audience` from {tier: document} for the tiers that hold it."""
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
        _check_ids(d, ())
        if out.doc is None:
            out.doc = copy.deepcopy(d)
            out.origin[()] = t
        elif isinstance(out.doc, dict) and isinstance(d, dict):
            _merge(out.doc, d, (), t, out.origin)
        elif isinstance(out.doc, list) and isinstance(d, list):
            _merge_list(out.doc, d, (), t, out.origin)
        elif not _same(out.doc, d):
            raise LayerError(f"the {t} layer isn't in the same form as the layers below it")
    if isinstance(out.doc, (dict, list)):
        _check_ids(out.doc, ())   # the composed result obeys the same rules as each layer
    return out
