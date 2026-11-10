"""A tier's material, kept between screens (knowledge/spec_classification.md, "Proposal scan").

A higher tier never restates, so what a tier's material is depends on that tier's own store
alone. Working it out means parsing every file the tier holds, which is most of a screen's
cost, so the screening tier keeps it here and works it out again only when something it
depends on changes.

Where it lives. In the git folder of the tier that screens, which sees every tier it
caches, so no tier's material is written anywhere a lower tier reads. Never in a working
tree, and never in a lower store.

When it's used. Each entry carries a key: a digest of every input the material is computed
from - the tier's files by path and content, its kit settings, the register, lect-kit's
own code, schemas and lists, and the Python and Unicode versions that normalise text. An
entry is used only when its key equals the key computed now, so a stale entry is never
found; it is simply replaced. Nothing is cached about the tree being proposed, and the
matching itself is never cached.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import tempfile
import unicodedata
from pathlib import Path

from lectkit import audience_db, format_words, shared_lists

FORMAT = "1"
KIT_ROOT = Path(__file__).resolve().parent


def _digest_files(h, root: Path) -> None:
    if not root.is_dir():
        h.update(b"absent\0")
        return
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            h.update(p.relative_to(root).as_posix().encode("utf-8") + b"\0")
            h.update(hashlib.sha256(p.read_bytes()).digest())


def kit_digest() -> str:
    """lect-kit's code, the schemas its format words come from and its shared lists."""
    h = hashlib.sha256(FORMAT.encode())
    h.update(f"{sys.version}\0{unicodedata.unidata_version}\0".encode())
    _digest_files(h, KIT_ROOT)
    _digest_files(h, Path(format_words.SCHEMA_DIR))
    _digest_files(h, Path(shared_lists.LIST_DIR))
    return h.hexdigest()


class MaterialCache:
    def __init__(self, folder: Path, reg, audience: str, register_digest: str):
        self.folder = Path(folder)
        self.reg = reg
        self.audience = audience
        self.base = register_digest + "\0" + kit_digest()
        self._keys: dict[str, str] = {}      # a screen checks its stores didn't change

    def key(self, tier: str) -> str:
        if tier not in self._keys:
            self._keys[tier] = self._key(tier)
        return self._keys[tier]

    def _key(self, tier: str) -> str:
        store = self.reg.tiers[tier].store_path
        h = hashlib.sha256(self.base.encode())
        h.update(f"\0{tier}\0{tier == self.audience}\0".encode())
        h.update(audience_db.store_digest(tier, store, tier == self.audience).encode())
        for rel in (audience_db.EXCLUDE_FILE, audience_db.STRUCTURE_FILE):
            p = store / rel                  # read even when the kit folder isn't material
            h.update(hashlib.sha256(p.read_bytes()).digest() if p.is_file() else b"absent")
        return h.hexdigest()

    def _file(self, tier: str) -> Path:
        return self.folder / f"{hashlib.sha256(tier.encode()).hexdigest()[:16]}.json.gz"

    def get(self, tier: str):
        f = self._file(tier)
        if not f.is_file():
            return None
        try:
            doc = json.loads(gzip.decompress(f.read_bytes()))
        except (OSError, ValueError):
            return None                      # damaged: worked out again
        if doc.get("tier") != tier or doc.get("key") != self.key(tier):
            return None
        return [tuple(r) for r in doc["rows"]]

    def put(self, tier: str, rows) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        data = gzip.compress(json.dumps({"tier": tier, "key": self.key(tier),
                                         "rows": [list(r) for r in rows]}).encode("utf-8"))
        fd, tmp = tempfile.mkstemp(dir=self.folder, suffix=".part")
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, self._file(tier))
