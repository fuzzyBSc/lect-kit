"""Check identifiers in schemes/ match [A-Za-z_-][A-Za-z0-9_-]* and are unique.

Checks each descriptor's `scheme` and every label `id`. Display fields (`code`, `name`)
may hold any text. Files are read strictly (lectkit/yamlio.py), so a repeated key is an
error and a word like `no` stays text. An identifier must be text: an empty one, or one
YAML reads as something else, is reported. Exit 1 on any problem.

Usage: python scripts/check_identifiers.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lectkit import yamlio  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ID = re.compile(r"[A-Za-z_-][A-Za-z0-9_-]*")


def valid(value) -> bool:
    return isinstance(value, str) and ID.fullmatch(value) is not None


def shown(value) -> str:
    return "''" if value is None else repr(value)


def main() -> int:
    problems = 0
    files = sorted((ROOT / "schemes").glob("*.yaml"))
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        try:
            data = yamlio.load_file(f)
        except yamlio.YamlError as e:
            print(f"[ERROR] {rel}: {e}")
            problems += 1
            continue
        data = {} if data is None else data
        if not isinstance(data, dict):
            print(f"[ERROR] {rel}: isn't a mapping of keys")
            problems += 1
            continue
        scheme = data.get("scheme")
        if not valid(scheme):
            print(f"[ERROR] {rel}: scheme {shown(scheme)} is not a valid identifier")
            problems += 1
        labels = data.get("labels") or []
        if not isinstance(labels, list):
            print(f"[ERROR] {rel}: labels must be a list")
            problems += 1
            continue
        seen = set()
        for i, label in enumerate(labels):
            if not isinstance(label, dict):
                print(f"[ERROR] {rel}: label {i} isn't a mapping of keys")
                problems += 1
                continue
            lid = label.get("id")
            if not valid(lid):
                print(f"[ERROR] {rel}: label {i} id {shown(lid)} is not a valid identifier")
                problems += 1
            elif lid in seen:
                print(f"[ERROR] {rel}: duplicate id {shown(lid)}")
                problems += 1
            else:
                seen.add(lid)
    print(f"{problems} problem(s) in {len(files)} file(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
