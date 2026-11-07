"""Check a project's tier register (knowledge/spec_classification.md, "Register file").

Usage: python scripts/check_tier_register.py REGISTER [--stores]

Prints each problem, then the closed pairs. With --stores, also checks each store that
is present on disk against its remote rule and lists stores that are absent; an absent
store is not a pass. Exit 1 on any problem.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lectkit import tiers  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("register")
    ap.add_argument("--stores", action="store_true", help="also check each store on disk")
    args = ap.parse_args(argv)

    reg = tiers.load(args.register)
    problems = list(reg.problems)
    absent: list[str] = []
    if args.stores and reg.problems:
        print("[NOTE] stores not checked: fix the register problems first")
    elif args.stores:
        store_problems, absent = tiers.check_stores(reg)
        problems += store_problems
    for p in problems:
        print(f"[ERROR] {p}")
    for t in absent:
        print(f"[ABSENT] {t}: store not on this machine; not checked")
    for a, b in reg.closed_pairs():
        print(f"[CLOSED] {a} / {b}")
    print(f"{len(problems)} problem(s) in {len(reg.tiers)} tier(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
