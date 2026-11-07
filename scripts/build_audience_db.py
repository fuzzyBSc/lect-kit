"""Build an audience's database (knowledge/spec_classification.md, "Audience database").

Usage:
    python scripts/build_audience_db.py --register REG --audience T --out FILE

Run where the audience's store and every store it sees are present. FILE is a SQLite
database holding readable material of every tier the audience reads. It must lie outside
every store in the register, and is never committed. Prints counts only. Errors name a
store and file, never their content. Exit 1 on any error.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lectkit import audience_db, layers, tiers  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--register", required=True)
    ap.add_argument("--audience", required=True)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    reg = tiers.load(a.register)
    if reg.problems:
        for p in reg.problems:
            print(f"[ERROR] register: {p}", file=sys.stderr)
        return 1
    try:
        rep = audience_db.build(reg, a.audience, a.out)
    except (audience_db.BuildError, layers.LayerError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"[ERROR] couldn't write the database ({e.__class__.__name__}); is it open?",
              file=sys.stderr)
        return 1
    print(f"[BUILT] {rep.audience} ({', '.join(rep.tiers)}): {rep.files} file(s), "
          f"{rep.source_values} source value(s), {rep.model_values} model value(s)")
    if rep.skipped_media:
        print(f"[NOTE] {rep.skipped_media} media file(s) hold no text and weren't read")
    return 0


if __name__ == "__main__":
    sys.exit(main())
