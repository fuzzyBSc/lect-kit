"""Record a person's review of one scan finding, so it stays cleared while the entry doesn't change.

Usage, inside the higher tier:
    python scripts/review_finding.py --register REG --db FILE --id ID --reason TEXT --by human:NAME

ID is the finding id scan_tiers.py prints. The review is saved in the scanning tier's own
store, in .lectkit/reviewed_findings.yaml, against the lower entry's exact text and the
hidden items it matched (knowledge/spec_classification.md, "Cross-tier scan"). If the
entry or what it matches changes, the finding comes back for review. Exit 0 when recorded,
3 when it couldn't be.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lectkit import audience_db, scan, tiers  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--register", required=True)
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--id", required=True)
    ap.add_argument("--reason", required=True)
    ap.add_argument("--by", required=True)
    a = ap.parse_args(argv)
    reg = tiers.load(a.register)
    if reg.problems:
        print("[ERROR] the register has problems", file=sys.stderr)
        return 3
    try:
        with audience_db.AudienceDB(a.db) as db:
            store = reg.tiers[db.audience].store_path
            rep = scan.scan(db, reg, scan.load_accepted(store / scan.ACCEPT_FILE, reg),
                            scan.load_reviews(store / scan.REVIEW_FILE, reg))
        hits = [f for f in rep.findings if f.id == a.id]
        if not hits:
            print(f"[ERROR] no current finding has id {a.id}; scan again", file=sys.stderr)
            return 3
        if len(hits) > 1:
            print(f"[ERROR] more than one finding has id {a.id}; review can't tell them apart",
                  file=sys.stderr)
            return 3
        f = hits[0]
        if f.reviewed:
            print(f"[NOTE] {a.id} is already reviewed")
            return 0
        path = scan.record_review(store, f, a.reason, a.by,
                                  datetime.now(timezone.utc).isoformat(timespec="seconds"))
    except (scan.ScanError, audience_db.BuildError) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 3
    print(f"[REVIEWED] {a.id} {f.tier}: {f.rel}:{f.line}, recorded in "
          f"{path.relative_to(store).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
