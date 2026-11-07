"""Screen one lower store's exported tree for one higher tier, and print a verdict.

Usage (run by scan_proposal.py, one process per higher tier):
    python scripts/screen_for_tier.py --register REG --tier T --lower L --export DIR --tree SHA

Prints exactly one JSON verdict on stdout and nothing else (knowledge/spec_classification.md,
"Proposal scan"). Any failure prints nothing on stdout and exits non-zero, so no partial
or free-text answer can cross back.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lectkit import proposal, tiers  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for a in ("--register", "--tier", "--lower", "--export", "--tree"):
        ap.add_argument(a, required=True)
    a = ap.parse_args(argv)
    try:
        reg = tiers.load(a.register)
        if reg.problems or a.lower not in reg.tiers[a.tier].sees:
            return 3
        v = proposal.screen(reg, a.tier, a.lower, Path(a.export), a.tree)
    except Exception:          # nothing but a verdict may leave this process
        return 3
    sys.stdout.write(json.dumps(v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
