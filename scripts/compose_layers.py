"""Compose one layered file for one audience (knowledge/spec_classification.md, "Layered files").

Usage:
    python scripts/compose_layers.py --register REG --audience T --rel PATH [--out FILE] [--origin]

Reads PATH from the audience's own store and from every store its sees list names. PATH
must be relative and stay inside each store. Writes the composed YAML to --out or stdout.
With --origin, also prints the tier that added each record or value, one per line, to
stderr. Each readable store that is absent is reported and the exit code is 2, so an
incomplete view is never silent. Errors go to stderr; exit 1 on any error. Files are
read by lectkit.yamlio: a repeated key is an error, and yes/no/on/off and dates stay text.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path, PurePosixPath

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lectkit import layers, tiers, yamlio  # noqa: E402


def target(store: Path, rel: str) -> Path:
    r = PurePosixPath(rel.replace("\\", "/"))
    if not r.parts or r.is_absolute() or Path(rel).is_absolute() or ".." in r.parts:
        raise layers.LayerError(f"--rel {rel!r} must be a relative path inside the store")
    t = (store / Path(*r.parts)).resolve()
    if not t.is_relative_to(store.resolve()):
        raise layers.LayerError(f"--rel {rel!r} leaves the store")
    return t


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--register", required=True)
    ap.add_argument("--audience", required=True)
    ap.add_argument("--rel", required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--origin", action="store_true")
    a = ap.parse_args(argv)

    reg = tiers.load(a.register)
    if reg.problems:
        for p in reg.problems:
            print(f"[ERROR] register: {p}", file=sys.stderr)
        return 1
    try:
        found, absent = {}, []
        for t in layers.order(reg, a.audience):
            store = reg.tiers[t].store_path
            if store is None or not store.is_dir():
                absent.append(t)
                continue
            f = target(store, a.rel)
            if f.is_file():
                found[t] = yamlio.load_file(f)
        for t in absent:
            print(f"[ABSENT] {t}: store not on this machine; the view is incomplete",
                  file=sys.stderr)
        if not found:
            print(f"[ERROR] no readable store holds {a.rel}", file=sys.stderr)
            return 1
        composed = layers.compose(found, a.audience, reg)
    except (layers.LayerError, yamlio.YamlError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    text = yaml.safe_dump(composed.doc, sort_keys=False, allow_unicode=True)
    if a.out:
        a.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    if a.origin:
        for path, t in composed.origin.items():
            print(f"{t}\t{layers.where(path)}", file=sys.stderr)
    return 2 if absent else 0


if __name__ == "__main__":
    sys.exit(main())
