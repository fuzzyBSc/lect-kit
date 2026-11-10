"""File formats and their schemas (knowledge/spec_classification.md, "Formats and schemas").

A schema says, for each list in a format that holds records, which field identifies a
record. Composing a file under its schema joins a higher tier's record to the lower
tier's record with the same identifier. A list the schema doesn't name, or names with no
identifier, stacks by value. Each schema names the file name patterns that hold its
format: the kit's standard layout. A project adds formats for files the patterns don't
cover in .lectkit/formats.yaml, which is layered like any file and identified by path.
"""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

from lectkit import yamlio

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
MAP_REL = ".lectkit/formats.yaml"
_FIELD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class FormatError(ValueError):
    pass


@dataclass(frozen=True)
class Schema:
    """keys maps a list path, mapping keys joined by '/', to its identifying field or None."""
    name: str
    keys: dict[str, str | None] = field(default_factory=dict)
    files: tuple[str, ...] = ()

    def claims(self, rel: str) -> bool:
        return any(fnmatch.fnmatchcase(rel, pat) for pat in self.files)

    def key_for(self, list_path: tuple[str, ...]) -> str | None:
        """An exact list path wins; otherwise the first pattern (with *) that matches."""
        p = "/".join(list_path)
        if p in self.keys:
            return self.keys[p]
        for pat, k in self.keys.items():
            if "*" in pat and fnmatch.fnmatchcase(p, pat):
                return k
        return None


def parse(doc: object, source: str) -> Schema:
    if not isinstance(doc, dict) or not isinstance(doc.get("format"), str) or not doc["format"]:
        raise FormatError(f"{source}: a schema needs a format name")
    lists = doc.get("lists") or {}
    if not isinstance(lists, dict):
        raise FormatError(f"{source}: lists must be a mapping of list path to its rule")
    keys: dict[str, str | None] = {}
    for p, rule in lists.items():
        if not isinstance(p, str) or not p or any(not s for s in p.split("/")):
            raise FormatError(f"{source}: list path {p!r} must be text such as a/b")
        k = (rule or {}).get("key") if isinstance(rule, dict) or rule is None else rule
        if k is not None and (not isinstance(k, str) or not _FIELD.match(k)):
            raise FormatError(f"{source}: {p}: the identifier {k!r} isn't a field name")
        keys[p] = k
    files = doc.get("files", [])
    if not isinstance(files, list) or any(not isinstance(f, str) or not f or f.startswith("/")
                                          or ".." in f.split("/") for f in files):
        raise FormatError(f"{source}: files must be a list of relative path patterns")
    return Schema(doc["format"], keys, tuple(files))


def load_schemas(directory: Path = SCHEMA_DIR) -> dict[str, Schema]:
    out: dict[str, Schema] = {}
    for f in sorted(Path(directory).glob("*.yaml")):
        s = parse(yamlio.load_file(f), f.name)
        if s.name in out:
            raise FormatError(f"{f.name}: the format {s.name!r} is defined twice")
        out[s.name] = s
    return out


# The project map is a file like any other, so it has a schema of its own.
MAP_SCHEMA = Schema("format-map", {"files": "path"})


def resolve_map(doc: object, schemas: dict[str, Schema], source: str = MAP_REL) -> dict[str, Schema]:
    """{relative file path: Schema} from a composed project map."""
    if doc is None:
        return {}
    if not isinstance(doc, dict) or not isinstance(doc.get("files", []), list):
        raise FormatError(f"{source}: expected a files list")
    out: dict[str, Schema] = {}
    for row in doc.get("files", []):
        if not isinstance(row, dict) or not isinstance(row.get("path"), str) \
                or not isinstance(row.get("format"), str):
            raise FormatError(f"{source}: each file needs a path and a format")
        if row["format"] not in schemas:
            raise FormatError(f"{source}: {row['path']}: the kit has no format "
                              f"{row['format']!r}")
        out[row["path"].replace("\\", "/")] = schemas[row["format"]]
    return out


def format_for(rel: str, schemas: dict[str, Schema], mapped: dict[str, Schema] | None = None
               ) -> Schema | None:
    """The format of the store-relative file `rel`: the kit schema whose pattern claims it,
    else the project's own mapping, else None. A project can't give a file a different
    format from the one the kit's pattern names, and two kit patterns can't claim one file."""
    rel = rel.replace("\\", "/")
    kit = [s for s in schemas.values() if s.claims(rel)]
    if len(kit) > 1:
        raise FormatError(f"{rel}: claimed by more than one format: "
                          f"{', '.join(sorted(s.name for s in kit))}")
    own = (mapped or {}).get(rel)
    if kit and own is not None and own.name != kit[0].name:
        raise FormatError(f"{rel}: the project maps it to {own.name!r}, but the kit's layout "
                          f"puts it in {kit[0].name!r}")
    return kit[0] if kit else own


def unclaimed(store: Path, schemas: dict[str, Schema], mapped: dict[str, Schema] | None,
              dirs: list[str]) -> list[str]:
    """The YAML files under `dirs` in `store` that no format claims."""
    out = []
    for d in dirs:
        for f in sorted((Path(store) / d).rglob("*.yaml")):
            rel = f.relative_to(store).as_posix()
            if format_for(rel, schemas, mapped) is None:
                out.append(rel)
    return out


LAYOUT_FILE = Path(__file__).resolve().parent / "layout.yaml"


def load_layout(path: Path = LAYOUT_FILE) -> list[dict]:
    doc = yamlio.load_file(path)
    dirs = doc.get("directories") if isinstance(doc, dict) else None
    if not isinstance(dirs, list) or any(not isinstance(d, dict) or not isinstance(d.get("path"), str)
                                         for d in dirs):
        raise FormatError(f"{Path(path).name}: directories must be a list with a path each")
    return dirs


def formatted_dirs(layout: list[dict] | None = None) -> list[str]:
    """The standard directories whose every YAML file must have a format."""
    return [d["path"] for d in (layout if layout is not None else load_layout())
            if d.get("every_file_has_a_format")]
