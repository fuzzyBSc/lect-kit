"""The term-pattern gates in lectkit.scan never change which patterns match a line."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lectkit import scan  # noqa: E402

PATTERNS = [
    re.compile(r"(?<![^\W_])fxq(?![^\W_])", re.I),     # a literal between lookarounds
    re.compile(r"(?<![^\W_])kelvqz(?![^\W_])", re.I),  # matched by U+212A KELVIN SIGN
    re.compile(r"^fxhead", re.I),                      # an anchor
    re.compile(r"fx(?:aa|bb)qz"),                      # a branch: gated whole, not by literal
    re.compile(r"(fx)z\1"),                            # a group: never gated
    re.compile(r"(?i)fxflagqz"),                       # a global inline flag: never gated
    re.compile(r"Fxcase"),                             # case-sensitive literal
]
LINES = ["nothing", "an fxq here", "afxqb", "Kelvqz", "fxheadline", "xfxhead",
         "fxbbqz", "fxzfx", "FXFLAGQZ", "fxcase", "Fxcase now", "FXQ", ""]


def test_gated_matching_is_the_same_as_trying_every_pattern():
    alone, gates = scan._gates(PATTERNS)
    for line in LINES:
        want = {rx.pattern for rx in PATTERNS if rx.search(line)}
        tried = alone + [rx for g, ms in gates if g.search(line) for rx in ms]
        assert {rx.pattern for rx in tried if rx.search(line)} == want, line
    assert {rx.pattern for rx in alone} == {r"(fx)z\1", r"(?i)fxflagqz"}
