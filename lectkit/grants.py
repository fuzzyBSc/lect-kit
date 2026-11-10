"""A tier's grants, reviews and drafts, as plain lists per lower tier.

Project custodian's rulings, 2026-11-09 (knowledge/spec_classification.md, "Where a grant
lives", "Grants are plain lists"):

- A grant lives only in the granting (higher) tier's store and names only a tier below it.
- A file holds only what it releases or clears, under the tier it is for. Who approved it and
  when is the granting tier's commit, whose message the hook screens. A reason, a batch number
  or a date in the file would be prose and metadata that the screen then has to clear below.
- The files are screened as the tier's material like any other file. A text is granted only
  where the higher tier grants it: a grant to gyy-general releases nothing to lect-kit.

Shapes:

    # .lectkit/accepted_matches.yaml: what this tier releases, by the tier it goes to
    lect-kit: [and, tier, rules]
    gyy-general: [uncle fred reece glosses it]

    # .lectkit/reviewed_findings.yaml: lower lines a person cleared, as hashes and digests only
    gyy-general:
    - {rel: <sha256 of the path>, entry: <sha256>, matched: [<mac>], nth: 1}

    # .lectkit/proposed_grants.yaml: drafts awaiting approval, the shape of a grant file;
    # the scan doesn't read them as grants
    gyy-general: [x, y]
"""
from __future__ import annotations

from pathlib import Path

from lectkit import yamlio

ROW_KEYS = {"rel", "entry", "matched", "nth"}


class GrantError(ValueError):
    pass


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        doc = yamlio.load_file(path)
    except yamlio.YamlError:
        raise GrantError(f"{path.name} is not valid YAML") from None
    if doc is None:
        return {}
    if not isinstance(doc, dict) or any(k in doc for k in ("grants", "reviews", "drafts")):
        raise GrantError(f"{path.name} must map each lower tier to a plain list "
                         f"(lectkit/grants.py); the batch shape is retired")
    return doc


def _items(path: Path, doc: dict) -> dict[str, list[str]]:
    for tier, items in doc.items():
        if not isinstance(tier, str) or not isinstance(items, list) \
                or not all(isinstance(x, str) and x for x in items):
            raise GrantError(f"{path.name}: {tier!s} must hold a list of text")
    return doc


def load_grants(path: Path) -> dict[str, list[str]]:
    return _items(path, _load(path))


def load_drafts(path: Path) -> dict[str, list[str]]:
    return _items(path, _load(path))


def load_reviews(path: Path) -> dict[str, list[dict]]:
    doc = _load(path)
    for tier, rows in doc.items():
        ok = isinstance(tier, str) and isinstance(rows, list)
        for r in (rows if ok else []):
            ok = ok and isinstance(r, dict) and set(r) - {"id"} == ROW_KEYS \
                and isinstance(r["rel"], str) and isinstance(r["entry"], str) \
                and isinstance(r["matched"], list) and all(isinstance(m, str) for m in r["matched"]) \
                and isinstance(r["nth"], int) and not isinstance(r["nth"], bool) and r["nth"] >= 1
        if not ok:
            raise GrantError(f"{path.name}: {tier!s} must hold rows of {sorted(ROW_KEYS)} "
                             f"(an id is optional)")
    return doc


def dump(doc: dict) -> str:
    import yaml
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100)


def write(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".writing")
    tmp.write_text(dump(doc), encoding="utf-8")
    tmp.replace(path)
