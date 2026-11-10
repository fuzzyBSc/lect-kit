"""Check that every file in a store's formatted directories has a format.

Usage:
    python scripts/check_formats.py --store DIR [--schemas DIR]

The directories come from the kit's standard layout (lectkit/layout.yaml). A file has a
format when a kit schema's file pattern claims it or the store's .lectkit/formats.yaml maps
it. Prints one [ERROR] line per unclaimed file and exits 1 if there are any. Reads only the
one store: the layered map from lower stores is the composer's concern.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lectkit import formats, yamlio  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--store", type=Path, required=True)
    ap.add_argument("--schemas", type=Path, default=formats.SCHEMA_DIR)
    a = ap.parse_args(argv)
    try:
        schemas = formats.load_schemas(a.schemas)
        m = a.store / formats.MAP_REL
        mapped = formats.resolve_map(yamlio.load_file(m), schemas) if m.is_file() else {}
        bad = formats.unclaimed(a.store, schemas, mapped, formats.formatted_dirs())
    except (formats.FormatError, yamlio.YamlError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    for rel in bad:
        print(f"[ERROR] {rel}: no format claims it")
    print(f"{len(bad)} file(s) without a format")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
