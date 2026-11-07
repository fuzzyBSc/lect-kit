"""Refuse language content, personal data and restricted terms in lect-kit.

Usage:
    python scripts/check_content.py [--deny FILE ...] [PATH ...]

Deny-lists are read only from paths given at run time (``--deny`` or the
LECT_KIT_DENY environment variable, separated by os.pathsep). They are never
copied, cached or logged, and a hit is reported by file and line only, never
by the matched text. A deny file is plain text (one term per line, ``#``
comments) or JSON, where only strings under term keys (term, form, word,
headword, lemma) or pattern keys (pattern, regex) count; bare lists count as
terms. Pattern values are applied as case-insensitive regexes.

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
from pathlib import Path

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


TERM_KEYS = {"term", "terms", "form", "forms", "word", "words", "headword", "lemma"}
REGEX_KEYS = {"pattern", "patterns", "regex"}


def load_deny(path: Path) -> tuple[set[str], list[re.Pattern]]:
    """Terms and regexes from a deny file. In JSON, only values under term or
    pattern keys count, so labels and notes are not mistaken for terms."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    terms: set[str] = set()
    regexes: list[re.Pattern] = []
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    if data is not None:
        def walk(x, key=None):
            if isinstance(x, dict):
                for k, v in x.items():
                    walk(v, k.lower() if isinstance(k, str) else None)
            elif isinstance(x, list):
                for v in x:
                    walk(v, key)
            elif isinstance(x, str):
                if key in REGEX_KEYS:
                    try:
                        regexes.append(re.compile(x, re.I))
                    except re.error:
                        pass
                elif key in TERM_KEYS or key is None:
                    terms.add(x)
        walk(data)
    else:
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            m = re.match(r"^-?\s*(?:[\w-]+:\s*)?['\"]?([^'\"]+?)['\"]?$", line)
            if m:
                terms.add(m.group(1))
    terms = {t.strip().lower() for t in terms if len(re.sub(r"\W", "", t)) >= 3}
    return terms, regexes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--deny", action="append", default=[], type=Path)
    ap.add_argument("paths", nargs="*", type=Path)
    a = ap.parse_args()

    deny_files = list(a.deny)
    env = os.environ.get("LECT_KIT_DENY")
    if env:
        deny_files += [Path(p) for p in env.split(os.pathsep) if p]
    terms: set[str] = set()
    regexes: list[re.Pattern] = []
    for f in deny_files:
        t, r = load_deny(f)
        terms |= t
        regexes += r
    word_terms = {t for t in terms if re.fullmatch(r"[\w.\-' ]+", t)}

    files = [p.resolve() for p in a.paths] or tracked_files()
    hits = 0
    for f in files:
        if not f.is_file() or f == SELF or f.suffix in {".png", ".jpg", ".pyc"}:
            continue
        rel = f.relative_to(ROOT) if f.is_relative_to(ROOT) else f
        try:
            lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            for label, rx in GENERIC:
                m = rx.search(line)
                if m and not (label == "email address" and EMAIL_ALLOW.search(line)):
                    print(f"[ERROR] {rel}:{n}: {label}")
                    hits += 1
            if word_terms or regexes:
                low = line.lower()
                toks = set(re.findall(r"[\w.\-']+", low))
                if (toks & word_terms
                        or any(" " in t and t in low for t in word_terms)
                        or any(rx.search(line) for rx in regexes)):
                    print(f"[ERROR] {rel}:{n}: matches a supplied deny-list term")
                    hits += 1

    if not deny_files:
        print("[NOTE] no deny-list supplied: generic checks only "
              "(see docs/content_rules.md)")
    print(f"{hits} hit(s) in {len(files)} file(s)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
