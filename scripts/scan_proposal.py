"""Screen a lower store's staged tree for every higher tier on this machine.

Usage, from the lower store's checkout:
    python scripts/scan_proposal.py --register REG --tier L [--repo DIR]

The proposal is the whole staged tree (knowledge/spec_classification.md, "Proposal scan").
Each higher tier present screens it in its own process. Prints, per higher tier, its
outcome and, on a hold, the file and line in the proposed tree, and lists every higher
tier that is absent. On no match from every higher tier, writes an evidence record into
the lower store's git directory.

Hooks run locally, by someone who holds what they need, so every higher tier must screen
the tree: a higher store that is absent blocks, and no evidence is written.

Exit 0: no match from every higher tier. 1: a hold. 2: a higher tier wasn't screened.
3: the scan couldn't run.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lectkit import proposal  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--register", required=True, type=Path)
    ap.add_argument("--tier", required=True)
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    a = ap.parse_args(argv)
    try:
        res = proposal.run(a.register, a.tier, a.repo)
    except proposal.ProposalError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 3
    for v in res.verdicts:
        print(f"[{v['outcome'].upper()}] screened for {v['screened_for']}")
        for loc in v["locations"]:
            print(f"  {loc['rel']}:{loc['line']}: not allowed in {res.tier}")
    for g in res.gaps:
        print(f"[GAP] {g}: store not on this machine; not screened for it")
    if res.held:
        return 1
    if res.gaps or not res.verdicts:
        print("[BLOCKED] every higher tier must screen the tree; run this where their stores "
              "are present", file=sys.stderr)
        return 2
    f = proposal.write_evidence(a.repo, res)
    print(f"[EVIDENCE] tree {res.tree[:12]} recorded in the git directory ({f.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
