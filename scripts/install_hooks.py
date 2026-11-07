"""Install the lect-kit commit and push hooks into a store's checkout.

Usage:
    python scripts/install_hooks.py --register REG --tier L [--repo DIR] [--force]

Writes pre-commit and pre-push into the checkout's hooks folder (honouring
core.hooksPath). Each names this Python, this kit, the register and the tier by absolute
path. A hook that lect-kit didn't write is left alone unless --force is given
(knowledge/spec_classification.md, "Commit and push hooks"). Exit 0 when installed.
"""
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lectkit import tiers  # noqa: E402

MARK = "# written by lect-kit install_hooks.py"
HOOK = Path(__file__).resolve().parent / "lectkit_hook.py"


def hook_text(name: str, register: Path, tier: str) -> str:
    q = lambda p: shlex.quote(Path(p).as_posix())  # noqa: E731
    args = '"$@"' if name == "pre-push" else ""
    return (f"#!/bin/sh\n{MARK}\n"
            f"exec {q(sys.executable)} -E {q(HOOK)} {name} --register {q(register)} "
            f"--tier {shlex.quote(tier)} --repo \"$(git rev-parse --show-toplevel)\" {args}\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--register", required=True, type=Path)
    ap.add_argument("--tier", required=True)
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    reg = tiers.load(a.register)
    if reg.problems or a.tier not in reg.tiers:
        print("[ERROR] the register has problems or doesn't name that tier", file=sys.stderr)
        return 1
    store = reg.tiers[a.tier].store_path
    if store is None or store.resolve() != a.repo.resolve():
        print(f"[ERROR] this checkout isn't the store the register gives for {a.tier}",
              file=sys.stderr)
        return 1
    r = subprocess.run(["git", "-C", str(a.repo), "rev-parse", "--git-path", "hooks"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("[ERROR] not a git checkout", file=sys.stderr)
        return 1
    hooks_dir = Path(r.stdout.strip())
    hooks_dir = hooks_dir if hooks_dir.is_absolute() else (a.repo / hooks_dir)
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for name in ("pre-commit", "pre-push"):
        f = hooks_dir / name
        if f.exists() and MARK not in f.read_text(encoding="utf-8", errors="replace") and not a.force:
            print(f"[ERROR] {name} exists and lect-kit didn't write it; pass --force to replace it",
                  file=sys.stderr)
            return 1
    for name in ("pre-commit", "pre-push"):
        f = hooks_dir / name
        f.write_text(hook_text(name, a.register.resolve(), a.tier), encoding="utf-8", newline="\n")
        f.chmod(0o755)
        print(f"[INSTALLED] {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
