"""Check that agent knowledge cites human sources that exist.

Every `knowledge/spec_*.md` and `knowledge/*_procedure.md` must cite at least one
`PRINCIPLES.md` section, and every `PRINCIPLES.md §N` cited anywhere in knowledge/
must exist. Every spec must name a `docs/` page, and that page must exist.

Usage: python scripts/check_knowledge_refs.py   (exit 1 on any problem)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTION = re.compile(r"^## (\d+)\.", re.M)
CITE = re.compile(r"`PRINCIPLES\.md`((?:[ ,]*(?:and )?§\d+)+)")


def main() -> int:
    sections = {int(n) for n in SECTION.findall((ROOT / "PRINCIPLES.md").read_text(encoding="utf-8"))}
    problems = 0
    for f in sorted((ROOT / "knowledge").glob("*.md")):
        text = f.read_text(encoding="utf-8")
        rel = f.relative_to(ROOT).as_posix()
        cited = {int(n) for m in CITE.finditer(text) for n in re.findall(r"§(\d+)", m.group(1))}
        for n in sorted(cited - sections):
            print(f"[ERROR] {rel}: cites PRINCIPLES.md §{n}, which doesn't exist")
            problems += 1
        must_cite = f.name.startswith("spec_") or f.name.endswith("_procedure.md")
        if must_cite and not cited:
            print(f"[ERROR] {rel}: cites no PRINCIPLES.md section")
            problems += 1
        if f.name.startswith("spec_"):
            docs = re.findall(r"`(docs/[^`]+\.md)`", text)
            if not docs:
                print(f"[ERROR] {rel}: names no docs/ page")
                problems += 1
            for d in docs:
                if not (ROOT / d).exists():
                    print(f"[ERROR] {rel}: names {d}, which doesn't exist")
                    problems += 1
    print(f"{problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
