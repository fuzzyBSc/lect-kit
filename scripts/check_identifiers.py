"""Check identifiers in schemes/ match [A-Za-z_-][A-Za-z0-9_-]* and are unique.

Checks each descriptor's `scheme` and every label `id`. Display fields (`code`, `name`)
may hold any text. Exit 1 on any problem.

Usage: python scripts/check_identifiers.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ID = re.compile(r"^[A-Za-z_-][A-Za-z0-9_-]*$")


def main() -> int:
    problems = 0
    files = sorted((ROOT / "schemes").glob("*.yaml"))
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        scheme = str(data.get("scheme", ""))
        if not ID.match(scheme):
            print(f"[ERROR] {rel}: scheme {scheme!r} is not a valid identifier")
            problems += 1
        seen = set()
        for i, label in enumerate(data.get("labels", []) or []):
            lid = str(label.get("id", ""))
            if not ID.match(lid):
                print(f"[ERROR] {rel}: label {i} id {lid!r} is not a valid identifier")
                problems += 1
            if lid in seen:
                print(f"[ERROR] {rel}: duplicate id {lid!r}")
                problems += 1
            seen.add(lid)
    print(f"{problems} problem(s) in {len(files)} file(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
