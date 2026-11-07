"""Scan every lower store in an audience's database for material its readers mustn't see.

Usage:
    python scripts/scan_tiers.py --register REG --db FILE [--out FILE] [--show-accepted]

Run inside the higher tier (knowledge/spec_classification.md, "Cross-tier scan"), on a
database built by build_audience_db.py. Each finding names a tier, file and line, and
never any text. Accepted matches are read from the scanning tier's own store, in
.lectkit/accepted_matches.yaml. --out may name a file under the scanning tier's own
.lectkit/ folder or outside every store, never in a lower one.

Exit 0: no unaccepted findings. 1: findings. 3: the scan couldn't run.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lectkit import audience_db, scan, tiers  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--register", required=True)
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--show-accepted", action="store_true")
    a = ap.parse_args(argv)
    reg = tiers.load(a.register)
    if reg.problems:
        for p in reg.problems:
            print(f"[ERROR] register: {p}", file=sys.stderr)
        return 3
    try:
        with audience_db.AudienceDB(a.db) as db:
            if a.out and not scan.report_path_allowed(reg, db.audience, a.out):
                print("[ERROR] a report can't be written into a lower tier's store",
                      file=sys.stderr)
                return 3
            store = reg.tiers[db.audience].store_path
            accepted = scan.load_accepted(store / scan.ACCEPT_FILE, reg)
            rep = scan.scan(db, reg, accepted)
    except (scan.ScanError, audience_db.BuildError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 3
    lines = []
    for f in rep.findings:
        if f.accepted and not a.show_accepted:
            continue
        mark = "ACCEPTED" if f.accepted else "MATCH"
        lines.append(f"[{mark}] {f.tier}: {f.rel}:{f.line}: {'/'.join(f.matches)} matches "
                     f"{', '.join(f.hidden)} material")
    n_acc = len(rep.findings) - len(rep.open_findings)
    lines.append(f"scanned {', '.join(rep.scanned) or 'no lower store'} from {rep.audience}: "
                 f"{len(rep.open_findings)} finding(s), {n_acc} accepted")
    text = "\n".join(lines) + "\n"
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 1 if rep.open_findings else 0


if __name__ == "__main__":
    sys.exit(main())
