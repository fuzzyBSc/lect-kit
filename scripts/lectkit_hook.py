"""Entry point for the hooks install_hooks.py writes (knowledge/spec_classification.md,
"Commit and push hooks").

Usage (called by git, not by hand):
    python scripts/lectkit_hook.py pre-commit --register REG --tier L --repo DIR
    python scripts/lectkit_hook.py pre-push --register REG --tier L --repo DIR REMOTE URL < updates

Exit 0 lets git go ahead; anything else refuses.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lectkit import hooks  # noqa: E402


def main(argv: list[str] | None = None, stdin=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("hook", choices=["pre-commit", "pre-push"])
    ap.add_argument("--register", required=True, type=Path)
    ap.add_argument("--tier", required=True)
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("rest", nargs="*")
    a = ap.parse_args(argv)
    say = lambda s: print(s, file=sys.stderr)  # noqa: E731
    if a.hook == "pre-commit":
        return hooks.pre_commit(a.register, a.tier, a.repo, say)
    remote = a.rest[0] if a.rest else ""
    return hooks.pre_push(a.register, a.tier, a.repo, remote,
                          (stdin or sys.stdin).read().splitlines(), say)


if __name__ == "__main__":
    sys.exit(main())
