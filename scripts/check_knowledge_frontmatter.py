"""Check every markdown file in knowledge/ against lect-kit's OKF profile.

The profile is in knowledge/README.md ("Frontmatter"). Frontmatter is read strictly
(lectkit/yamlio.py), so a key given twice is an error. Exit 1 on any problem.

Usage: python scripts/check_knowledge_frontmatter.py
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lectkit import yamlio  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE = ROOT / "knowledge"

TYPES = {"Spec", "Procedure", "Tracker", "Directory Guide", "Design Note", "Decision"}
TAGS = {"corpus", "paradigm", "rendering", "practice", "classification", "exchange",
        "content", "provenance", "measurement", "process"}
STATUSES = {"draft", "stable", "deprecated"}
REQUIRED = ("type", "title", "description")
ALLOWED = set(REQUIRED) | {"tags", "status", "generated", "verified", "sources", "stale_after"}


def frontmatter(text: str):
    """Return the frontmatter mapping, None when there is none, or an error message."""
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    try:
        fm = yamlio.load(m.group(1))
    except yamlio.YamlError as e:
        if str(e).startswith("not valid YAML"):
            return "frontmatter isn't valid YAML"
        return f"frontmatter can't be read ({e})"
    if fm is None:
        return {}
    return fm if isinstance(fm, dict) else "frontmatter isn't a mapping of keys"


def is_datetime(v) -> bool:
    if isinstance(v, datetime):
        return v.tzinfo is not None
    try:
        return datetime.fromisoformat(str(v)).tzinfo is not None
    except ValueError:
        return False


def actor_event_errors(ev, key: str, human_only: bool) -> list[str]:
    errs = []
    if not isinstance(ev, dict) or set(ev) != {"by", "at"}:
        return [f"{key} entry must be {{by, at}}"]
    by = str(ev["by"])
    if not re.match(r"^(agent|human):\S", by):
        errs.append(f"{key}.by must start with agent: or human:")
    if human_only and not by.startswith("human:"):
        errs.append(f"{key}.by must be a human: actor")
    if not is_datetime(ev["at"]):
        errs.append(f"{key}.at must be an ISO 8601 datetime with an offset")
    return errs


def check(fm: dict) -> list[str]:
    errs = []
    for k in REQUIRED:
        if k not in fm:
            errs.append(f"missing {k}")
    for k in fm:
        if k not in ALLOWED:
            errs.append(f"unknown key {k}")
    if "type" in fm and not (isinstance(fm["type"], str) and fm["type"] in TYPES):
        errs.append(f"type {fm['type']!r} not in the profile")
    title = fm.get("title")
    if title is not None and (not isinstance(title, str) or title.endswith(".") or not title.strip()):
        errs.append("title must be a short phrase with no trailing full stop")
    desc = fm.get("description")
    if desc is not None:
        d = str(desc)
        if not d.endswith(".") or len(d) > 220 or re.search(r"\.\s+[A-Z]", d[:-1]):
            errs.append("description must be one sentence ending in a full stop, at most 220 characters")
    tags = fm.get("tags", [])
    if not isinstance(tags, list) or len(tags) > 4 or any(not isinstance(t, str) or t not in TAGS
                                                            for t in tags):
        errs.append("tags must be a list of at most four profile tags")
    if "status" in fm and not (isinstance(fm["status"], str) and fm["status"] in STATUSES):
        errs.append("status must be draft, stable or deprecated")
    if "generated" in fm:
        errs += actor_event_errors(fm["generated"], "generated", human_only=False)
    verified = fm.get("verified") or []
    if not isinstance(verified, list):
        errs.append("verified must be a list of {by, at}")
        verified = []
    for ev in verified:
        errs += actor_event_errors(ev, "verified", human_only=True)
    sources = fm.get("sources") or []
    if not isinstance(sources, list):
        errs.append("sources must be a list of {resource, id?}")
        sources = []
    for s in sources:
        if not isinstance(s, dict) or "resource" not in s or set(s) - {"resource", "id"}:
            errs.append("sources entries must be {resource, id?}")
    if "stale_after" in fm and not is_datetime(fm["stale_after"]):
        errs.append("stale_after must be an ISO 8601 datetime with an offset")
    return errs


def main() -> int:
    problems = 0
    files = sorted(KNOWLEDGE.rglob("*.md"))
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        fm = frontmatter(f.read_text(encoding="utf-8"))
        if fm is None:
            print(f"[ERROR] {rel}: no frontmatter")
            problems += 1
            continue
        if isinstance(fm, str):
            print(f"[ERROR] {rel}: {fm}")
            problems += 1
            continue
        for e in check(fm):
            print(f"[ERROR] {rel}: {e}")
            problems += 1
    print(f"{problems} problem(s) in {len(files)} file(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
