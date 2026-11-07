"""Deny lists: terms and patterns a community supplies at run time, never stored here.

Shared by scripts/check_content.py (lect-kit's own content screen) and the hooks' check of
a tier's excluded files. See knowledge/content_procedure.md, "Checker behaviour".
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import yaml

TERM_KEYS = {"term", "terms", "form", "forms", "word", "words", "headword", "lemma"}
REGEX_KEYS = {"pattern", "patterns", "regex"}
# Alternatives matched as whole words, each read as a regex fragment (escaped if invalid).
VARIANT_KEYS = {"variant", "variants"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pyc"}
# Word edges that also hold where a term starts or ends with punctuation.
EDGE_L, EDGE_R = r"(?<!\w)", r"(?!\w)"


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _structured(path: Path, text: str):
    """The parsed deny file, or None when it is a plain list of terms.

    YAML is read with every scalar as a string, so values such as `no`, `on` or `1234`
    stay the text that was written instead of becoming booleans or numbers."""
    try:
        return json.loads(text)
    except ValueError:
        pass
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            return yaml.load(text, Loader=yaml.BaseLoader)
        except yaml.YAMLError:
            raise SystemExit(f"[ERROR] cannot parse deny file {path.name}")
    return None


def _compile(src: str) -> re.Pattern:
    return re.compile(nfc(src), re.I)


def load_deny(path: Path) -> tuple[set[str], list[re.Pattern]]:
    """Terms and regexes from a deny file. In JSON or YAML, only values under term,
    variant or pattern keys count, so labels, notes and flags are not mistaken for terms."""
    text = path.read_text(encoding="utf-8-sig")
    terms: set[str] = set()
    regexes: list[re.Pattern] = []
    data = _structured(path, text)
    if data is not None:
        def walk(x, key=None):
            if isinstance(x, dict):
                for k, v in x.items():
                    walk(v, str(k).lower())
            elif isinstance(x, list):
                for v in x:
                    walk(v, key)
            elif x is not None:
                x = str(x)
                if key in REGEX_KEYS:
                    try:
                        regexes.append(_compile(x))
                    except re.error:
                        regexes.append(_compile(re.escape(x)))
                elif key in VARIANT_KEYS:
                    try:
                        regexes.append(_compile(rf"{EDGE_L}(?:{x}){EDGE_R}"))
                    except re.error:
                        regexes.append(_compile(EDGE_L + re.escape(x) + EDGE_R))
                elif key in TERM_KEYS or key is None:
                    terms.add(x)
        walk(data)
    else:
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                terms.add(line)
    terms = {nfc(t.strip()).lower() for t in terms if len(re.sub(r"\W", "", t)) >= 3}
    return terms, regexes


def term_regex(term: str) -> re.Pattern:
    """A literal term matched as a whole word, whatever punctuation it holds."""
    return _compile(EDGE_L + re.escape(term) + EDGE_R)




def matchers(paths) -> list[re.Pattern]:
    """Every term and pattern in the given deny files, ready to search lines with."""
    out: list[re.Pattern] = []
    for p in paths:
        terms, regexes = load_deny(Path(p))
        out += [term_regex(t) for t in sorted(terms)] + regexes
    return out


def hits(lines, pats) -> list[int]:
    """Line numbers (from 1) whose NFC text matches any pattern."""
    return [n for n, line in enumerate(lines, 1) if any(r.search(nfc(line)) for r in pats)]
