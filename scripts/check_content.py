"""Refuse language content, personal data and restricted terms in lect-kit.

Usage:
    python scripts/check_content.py [--deny FILE ...] [PATH ...]

Deny-lists are read only from paths given at run time (``--deny`` or the
LECT_KIT_DENY environment variable, separated by os.pathsep). They are never
copied, cached or logged, and a hit is reported by file and line only, never
by the matched text. A deny file is plain text (one term per line, ``#``
comments), JSON, or YAML (``.yaml``/``.yml``). In JSON and YAML only strings
under term keys (term, form, word, headword, lemma), variant keys (variant,
variants) or pattern keys (pattern, regex) count; bare lists count as terms,
and every other key (labels, notes, flags) is ignored. Pattern values are
case-insensitive regexes; each variant and term is matched as a whole word.
Text on both sides is NFC-normalised. A path that doesn't exist, or a file
that can't be decoded, is an error, never a silent skip; a directory is
expanded. A deny-list that doesn't exist or isn't UTF-8 stops the run, and a deny-list
folder is read as the .yaml, .yml and .json lists under it, outside hidden folders
(lectkit/denylist.py, shared with the hooks and the scan).

With no PATH, checks every file git tracks or would add. Exits 1 on any hit.
See docs/content_rules.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lectkit.denylist import (EDGE_L, EDGE_R, SKIP_SUFFIXES, load_deny, nfc,  # noqa: E402,F401
                              term_regex)
from lectkit.denylist import matchers as deny_matchers  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()

GENERIC = [
    ("honorific + name", re.compile(r"\b(Uncle|Auntie|Aunty|Elder) [A-Z][a-z]+")),
    ("archive-style identifier", re.compile(r"\b[Tt]ape[ _]?\d{3,5}[A-Z]?\b")),
    ("personal path", re.compile(r"[A-Za-z]:\\\\?Users\\\\?|/home/[a-z]+/|/Users/[a-z]+/")),
    ("email address", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")),
]
# The licence names its copyright holder; that is allowed.
EMAIL_ALLOW = re.compile(r"noreply@anthropic\.com")


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [ROOT / p for p in out.splitlines() if p]


def read_lines(f: Path) -> list[str] | None:
    """The file's lines, NFC-normalised, or None if it can't be decoded as text."""
    raw = f.read_bytes()
    for enc in ("utf-8-sig", "utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else ("utf-8-sig",):
        try:
            return nfc(raw.decode(enc)).splitlines()
        except UnicodeDecodeError:
            continue
    return None


def expand(paths: list[Path]) -> tuple[list[Path], list[Path]]:
    """Files to check, and the paths given that don't exist."""
    files, missing = [], []
    for p in paths:
        p = p.resolve()
        if p.is_dir():
            files += sorted(x for x in p.rglob("*") if x.is_file() and ".git" not in x.parts)
        elif p.is_file():
            files.append(p)
        else:
            missing.append(p)
    return files, missing


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--deny", action="append", default=[], type=Path)
    ap.add_argument("paths", nargs="*", type=Path)
    a = ap.parse_args(argv)

    deny_files = list(a.deny)
    env = os.environ.get("LECT_KIT_DENY")
    if env:
        deny_files += [Path(p) for p in env.split(os.pathsep) if p]
    matchers = deny_matchers(deny_files)

    if a.paths:
        files, missing = expand(a.paths)
    else:
        files, missing = tracked_files(), []
    hits = 0
    for m in missing:
        print(f"[ERROR] {m}: path does not exist")
        hits += 1
    checked = 0
    for f in files:
        if f == SELF or f.suffix.lower() in SKIP_SUFFIXES or not f.is_file():
            continue
        rel = f.relative_to(ROOT) if f.is_relative_to(ROOT) else f
        lines = read_lines(f)
        checked += 1
        if lines is None:
            print(f"[ERROR] {rel}: cannot be decoded as text, so it was not screened")
            hits += 1
            continue
        for n, line in enumerate(lines, 1):
            for label, rx in GENERIC:
                if rx.search(line) and not (label == "email address" and EMAIL_ALLOW.search(line)):
                    print(f"[ERROR] {rel}:{n}: {label}")
                    hits += 1
            if any(rx.search(line) for rx in matchers):
                print(f"[ERROR] {rel}:{n}: matches a supplied deny-list term")
                hits += 1

    if not deny_files:
        print("[NOTE] no deny-list supplied: generic checks only "
              "(see docs/content_rules.md)")
    print(f"{hits} hit(s) in {checked} file(s)")
    return 1 if hits else 0

if __name__ == "__main__":
    sys.exit(main())
