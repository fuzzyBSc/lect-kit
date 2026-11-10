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
# What a deny-list folder is read as.
FOLDER_SUFFIXES = {".yaml", ".yml", ".json"}
# Per-entry options, read from the same mapping as the entry's values (the term registers
# these lists come from): `case_sensitive` true drops the case-insensitive flag for that
# entry's terms, variants and patterns; `suffix_guard` is a regex appended after each of
# that entry's variants, to rule out a look-alike. A pattern is used as written.
CASE_KEY, GUARD_KEY = "case_sensitive", "suffix_guard"
TRUE_TEXT = {"true", "yes", "on", "1"}
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


def _compile(src: str, case_sensitive: bool = False) -> re.Pattern:
    return re.compile(nfc(src), 0 if case_sensitive else re.I)


def _options(d: dict, inherited: tuple[bool, str]) -> tuple[bool, str]:
    """The case and guard options a mapping sets, falling back to its parent's."""
    case, guard = inherited
    lowered = {str(k).lower(): v for k, v in d.items()}
    if CASE_KEY in lowered:
        v = lowered[CASE_KEY]
        case = v is True or str(v).strip().lower() in TRUE_TEXT
    if GUARD_KEY in lowered and lowered[GUARD_KEY] is not None:
        guard = str(lowered[GUARD_KEY])
    return case, guard


def load_deny(path: Path) -> tuple[set[str], list[re.Pattern]]:
    """Terms and regexes from a deny file. In JSON or YAML, only values under term,
    variant or pattern keys count, so labels, notes and flags are not mistaken for terms.
    An entry's `case_sensitive` and `suffix_guard` options apply to its own values (see
    CASE_KEY); the returned terms are the case-insensitive ones."""
    text = path.read_text(encoding="utf-8-sig")
    terms: set[str] = set()
    regexes: list[re.Pattern] = []
    data = _structured(path, text)
    if data is not None:
        def walk(x, key=None, opts=(False, "")):
            if isinstance(x, dict):
                opts = _options(x, opts)
                for k, v in x.items():
                    walk(v, str(k).lower(), opts)
            elif isinstance(x, list):
                for v in x:
                    walk(v, key, opts)
            elif x is not None:
                x = str(x)
                case, guard = opts
                if key in REGEX_KEYS:
                    try:
                        regexes.append(_compile(x, case))
                    except re.error:
                        regexes.append(_compile(re.escape(x), case))
                elif key in VARIANT_KEYS:
                    try:
                        re.compile(guard)
                    except re.error:
                        raise SystemExit(f"[ERROR] deny file {path.name} has a suffix_guard "
                                         "that isn't a valid regular expression") from None
                    try:
                        regexes.append(_compile(rf"{EDGE_L}(?:{x}){EDGE_R}{guard}", case))
                    except re.error:
                        regexes.append(_compile(EDGE_L + re.escape(x) + EDGE_R + guard, case))
                elif key in TERM_KEYS or key is None:
                    if case:
                        if len(re.sub(r"\W", "", x)) >= 3:
                            regexes.append(_compile(EDGE_L + re.escape(nfc(x.strip())) + EDGE_R, True))
                    else:
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




def deny_files(paths) -> list[Path]:
    """The deny files named, with a folder read as the structured lists under it.

    Only .yaml, .yml and .json files count in a folder, outside hidden folders, so notes
    kept beside the lists can't become terms; a plain text list is named on its own.
    A path that doesn't exist, or a folder with no lists, stops the run. Errors name the
    file only, never its full path."""
    files: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            found = sorted(x for x in p.rglob("*")
                           if x.is_file() and x.suffix.lower() in FOLDER_SUFFIXES
                           and not any(part.startswith(".") for part in x.relative_to(p).parts))
            if not found:
                raise SystemExit(f"[ERROR] deny-list folder {p.name} holds no .yaml, .yml or .json list")
            files += found
        elif p.is_file():
            files.append(p)
        else:
            raise SystemExit(f"[ERROR] deny-list {p.name} does not exist")
    return files


def matchers(paths) -> list[re.Pattern]:
    """Every term and pattern in the given deny files and folders, ready to search lines with."""
    out: list[re.Pattern] = []
    for p in deny_files(paths):
        try:
            terms, regexes = load_deny(p)
        except UnicodeDecodeError:
            raise SystemExit(f"[ERROR] deny-list {p.name} is not UTF-8 text") from None
        out += [term_regex(t) for t in sorted(terms)] + regexes
    return out


def hits(lines, pats) -> list[int]:
    """Line numbers (from 1) whose NFC text matches any pattern."""
    return [n for n, line in enumerate(lines, 1) if any(r.search(nfc(line)) for r in pats)]
